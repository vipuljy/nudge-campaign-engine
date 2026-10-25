"""
nudge_engine.py: a reusable next-best-offer engine (Nudge project).

Works on ANY dataset in one standard shape: one row per customer contact, with
    features : columns describing the customer BEFORE the contact
    arm      : which option they got; one value is the control (e.g. 'none'), assigned at random
    value    : the outcome to maximise, already net of any cost paid per use (e.g. spend minus reward)
    option_cost : optional fixed cost per contact for each option (e.g. {'email': 0.02})
    group    : optional id, so one customer never sits in both the build and the test half

Steps:  check_balance -> average_effects -> NudgeEngine.fit -> recommend -> evaluate_policies
Measure: sample_size_per_group, min_detectable_lift (control groups) -> psi, drift_report (staleness alarms)
Money:  offer_profit, breakeven_uplift (rupees per customer) -> profit_curve -> budget_plan (whom to contact for a budget)
Method: one doubly robust (DR) uplift model per option vs the control (LightGBM inside), plus a
        safety margin learned from the data: the engine personalises only where it reliably pays.
"""
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.model_selection import GroupShuffleSplit, KFold


# ---------- 1. checks ----------
def std_diff(a, b):
    a, b = pd.Series(a).dropna().astype(float), pd.Series(b).dropna().astype(float)
    s = np.sqrt((a.var() + b.var()) / 2)
    return 0.0 if s == 0 else (a.mean() - b.mean()) / s


def check_balance(df, features, arm, control):
    """Fairness check: each option vs control on pre-contact features. All under 0.05 = random."""
    c = df[df[arm] == control]
    return pd.DataFrame({a: {f: std_diff(df.loc[df[arm] == a, f], c[f]) for f in features}
                         for a in pd.unique(df[arm]) if a != control})


def average_effects(df, arm, control, value, option_cost=None):
    """Average extra value of each option vs control (after its fixed cost), with a 95% range."""
    option_cost = option_cost or {}
    c = df.loc[df[arm] == control, value].astype(float); rows = []
    for a in pd.unique(df[arm]):
        if a == control: continue
        g = df.loc[df[arm] == a, value].astype(float)
        d = g.mean() - c.mean() - option_cost.get(a, 0.0); se = np.sqrt(g.var() / len(g) + c.var() / len(c))
        rows.append({'option': a, 'extra_value': d, 'low95': d - 1.96 * se, 'high95': d + 1.96 * se, 'rows': len(g)})
    return pd.DataFrame(rows).set_index('option').sort_values('extra_value', ascending=False)


def split_by_group(df, group, test_size=0.2, seed=2026):
    """Split so that each group (e.g. customer) is entirely in one half."""
    tr, te = next(GroupShuffleSplit(1, test_size=test_size, random_state=seed).split(df, groups=df[group]))
    return df.iloc[tr].copy(), df.iloc[te].copy()


# ---------- 2. the engine ----------
def _reg(**kw):
    p = dict(n_estimators=250, learning_rate=0.03, num_leaves=15, min_child_samples=300, subsample=0.8,
             subsample_freq=1, colsample_bytree=0.7, reg_lambda=10.0, verbose=-1, random_state=42)
    p.update(kw); return lgb.LGBMRegressor(**p)


class NudgeEngine:
    """Predicts the extra value of every option for every customer and recommends the best one."""
    MARGIN_GRID = [0, 0.1, 0.25, 0.5, 1, 2, np.inf]   # multiples of the best option's average effect

    def __init__(self, features, arm, control, value, option_cost=None, group=None, margin='auto', model_params=None):
        self.features, self.arm, self.control, self.value = features, arm, control, value
        self.option_cost = dict(option_cost or {})
        self.group, self.margin, self.params = group, margin, model_params or {}

    def fit(self, df):
        """margin='auto': first learn, on two halves of df, how much better a personal choice must look
        before it overrides the best-on-average option (0 = always personalise, inf = never)."""
        if self.margin == 'auto':
            scores = []
            for seed in [11, 12]:
                if self.group:
                    a_, b_ = split_by_group(df, self.group, 0.5, seed)
                else:
                    a_ = df.sample(frac=0.5, random_state=seed); b_ = df.drop(a_.index)
                sub = NudgeEngine(self.features, self.arm, self.control, self.value, self.option_cost, margin=0,
                                  model_params=self.params)._fit(a_)
                scores.append([policy_value(b_, self.arm, self.value, sub.recommend(b_, margin_mult=m).values, sub.prop,
                                            self.option_cost) for m in self.MARGIN_GRID])
            self.margin_scores = pd.Series(np.mean(scores, axis=0), index=self.MARGIN_GRID)
            self.margin_mult = self.margin_scores.idxmax()
        else:
            self.margin_mult = self.margin
        return self._fit(df)

    def _fit(self, df):
        X, A, Y = df[self.features], df[self.arm].values, df[self.value].values.astype(float)
        self.options = [a for a in pd.unique(A) if a != self.control]
        self.prop = {a: (A == a).mean() for a in list(self.options) + [self.control]}   # chance of each option
        self.tau = {}
        for a in self.options:                                   # one DR uplift model per option
            m = (A == a) | (A == self.control); Xa, ya, ta = X[m], Y[m], (A[m] == a).astype(int)
            e = self.prop[a] / (self.prop[a] + self.prop[self.control])
            psi = np.zeros(len(ya))
            for tr, te in KFold(2, shuffle=True, random_state=0).split(Xa):            # cross-fitting
                m1 = _reg(**self.params).fit(Xa.iloc[tr][ta[tr] == 1], ya[tr][ta[tr] == 1])
                m0 = _reg(**self.params).fit(Xa.iloc[tr][ta[tr] == 0], ya[tr][ta[tr] == 0])
                mu1, mu0 = m1.predict(Xa.iloc[te]), m0.predict(Xa.iloc[te])
                psi[te] = mu1 - mu0 + ta[te] * (ya[te] - mu1) / e - (1 - ta[te]) * (ya[te] - mu0) / (1 - e)
            self.tau[a] = _reg(**{**self.params, 'min_child_samples': 600}).fit(Xa, psi)
        p = self.predict(df)
        self.default = p.mean().idxmax()                           # best option on average (may be the control)
        self.default_effect = abs(p.mean().drop(self.control).max()) if self.options else 0.0
        return self

    def with_costs(self, option_cost, df):
        """Apply a (new) fixed cost per contact and re-pick the best-on-average option, without refitting."""
        self.option_cost = dict(option_cost)
        p = self.predict(df); self.default = p.mean().idxmax()
        self.default_effect = abs(p.mean().drop(self.control).max()) if self.options else 0.0
        return self

    def predict(self, df):
        """Predicted extra value of each option (after its fixed cost) vs doing nothing."""
        out = pd.DataFrame({a: self.tau[a].predict(df[self.features]) - self.option_cost.get(a, 0.0) for a in self.options},
                           index=df.index)
        out[self.control] = 0.0
        return out

    def recommend(self, df, margin_mult=None):
        """Start from the best-on-average option; switch to a customer's personal best only when it is
        predicted to beat the default by more than the safety margin."""
        m = self.margin_mult if margin_mult is None else margin_mult
        p = self.predict(df); best = p.idxmax(axis=1); adv = p.max(axis=1) - p[self.default]
        return best.where(adv > m * self.default_effect, self.default)


# ---------- 3. scoring a policy offline ----------
def _prep(df, arm, value, prop, option_cost=None):
    option_cost = option_cost or {}
    a = df[arm].values
    y = df[value].values.astype(float) - pd.Series(a).map(lambda k: option_cost.get(k, 0.0)).values
    w = 1.0 / pd.Series(a).map(prop).values.astype(float)
    codes = {k: i for i, k in enumerate(pd.unique(a))}
    ac = np.array([codes[k] for k in a])                        # integer codes: fast comparisons
    return a, ac, codes, y, w


def _value(ac, y, w, ch, idx):
    if isinstance(ch, str) and ch == 'LOGGED':                  # the random policy that generated the data
        return y[idx].mean()
    hit = (ac[idx] == ch[idx]).astype(float)                      # rows where the random option = the policy's choice
    return (hit * w[idx] * y[idx]).sum() / (hit * w[idx]).sum()   # self-normalised inverse propensity weighting


def _encode(chosen, codes):
    return chosen if isinstance(chosen, str) else np.array([codes.get(c, -1) for c in np.asarray(chosen)])


def policy_value(df, arm, value, chosen, prop, option_cost=None):
    """What a policy would earn per customer, judged on random-assignment data."""
    a, ac, codes, y, w = _prep(df, arm, value, prop, option_cost)
    return _value(ac, y, w, _encode(chosen, codes), np.arange(len(a)))


def evaluate_policies(df, arm, value, policies, prop, option_cost=None, n_boot=200, seed=1, baseline=None):
    """Score several policies with 95% ranges, and each one against a baseline policy (paired bootstrap).
    A policy is a list/array of chosen options per row, or 'LOGGED' for the experiment's own random policy."""
    a, ac, codes, y, w = _prep(df, arm, value, prop, option_cost)
    P = {k: _encode(v, codes) for k, v in policies.items()}
    rng = np.random.default_rng(seed); n = len(a); B = [rng.integers(0, n, n) for _ in range(n_boot)]
    boots = {k: np.array([_value(ac, y, w, ch, b) for b in B]) for k, ch in P.items()}
    rows = []
    for name, ch in P.items():
        r = {'policy': name, 'value_per_customer': _value(ac, y, w, ch, np.arange(n)),
             'low95': np.percentile(boots[name], 2.5), 'high95': np.percentile(boots[name], 97.5)}
        if baseline is not None and name != baseline:
            d = boots[name] - boots[baseline]
            r.update({'vs_baseline': d.mean(), 'vs_low95': np.percentile(d, 2.5), 'vs_high95': np.percentile(d, 97.5)})
        mix = pd.Series(a if isinstance(ch, str) else np.asarray(policies[name])).value_counts(normalize=True)
        r['mix'] = ', '.join(f'{k} {100 * v:.0f}%' for k, v in mix.head(4).items()); rows.append(r)
    return pd.DataFrame(rows).set_index('policy')


# ---------- 4. money: rupees, profit curves and budgets ----------
def offer_profit(p_base, uplift, margin, contact_cost=0.0, reward=0.0, reward_cost_share=1.0, redeem=1.0):
    """Expected extra profit from giving ONE customer an option.
    p_base: chance they buy anyway | uplift: extra buy chance the option causes | margin: profit per purchase
    reward: value given to every buyer who uses it (discount, cashback, credit, freebie)
    reward_cost_share: what the reward really costs you per rupee of face value (1 for a discount, COGS share for a freebie)
    redeem: share of buyers who actually use it (1 for an instant discount, about 0.7-0.8 for cashback)."""
    p_base, uplift = np.asarray(p_base, float), np.asarray(uplift, float)
    p_new = np.clip(p_base + uplift, 0, 1)
    return uplift * margin - contact_cost - reward * reward_cost_share * redeem * p_new


def breakeven_uplift(p_base, margin, contact_cost=0.0, reward=0.0, reward_cost_share=1.0, redeem=1.0):
    """Smallest uplift (extra buy chance) an option needs to pay for itself. Solves offer_profit = 0."""
    r = reward * reward_cost_share * redeem
    p_base = np.asarray(p_base, float)
    return np.where(margin > r, (contact_cost + r * p_base) / max(margin - r, 1e-9), np.inf)


def profit_curve(score, treated, outcome, value_per_unit, contact_cost, shares=None, scale=1.0, n_boot=0, seed=1):
    """MEASURED profit of contacting the top share of customers by score, on a randomized test.
    extra units in the group = (treated rate - control rate) x group size; profit = extra units x value - contacts x cost.
    scale converts the test size to a business size (e.g. 100000 / len(test) = per 1 lakh customers).
    With n_boot > 0, adds 95% ranges (bootstrap)."""
    score, t, y = np.asarray(score, float), np.asarray(treated, int), np.asarray(outcome, float)
    n = len(score); order = np.argsort(-score, kind='stable'); t, y = t[order], y[order]
    shares = np.round(np.arange(0, 1.0001, 0.05), 2) if shares is None else np.asarray(shares)
    ks = np.clip(np.round(shares * n).astype(int), 0, n)

    def _calc(w):
        ct, cc = np.cumsum(w * t), np.cumsum(w * (1 - t)); yt, yc = np.cumsum(w * y * t), np.cumsum(w * y * (1 - t))
        out = []
        for k in ks:
            if k == 0: out.append((0.0, 0.0)); continue
            i = k - 1; size = w[:k].sum()
            lift = yt[i] / max(ct[i], 1e-9) - yc[i] / max(cc[i], 1e-9)
            extra = lift * size * scale; out.append((extra, extra * value_per_unit - size * scale * contact_cost))
        return np.array(out)

    base = _calc(np.ones(n))
    res = pd.DataFrame({'share': shares, 'contacts': ks * scale, 'extra_units': base[:, 0], 'profit': base[:, 1]})
    if n_boot:
        rng = np.random.default_rng(seed)
        boots = np.array([_calc(np.bincount(rng.integers(0, n, n), minlength=n).astype(float))[:, 1] for _ in range(n_boot)])
        res['low95'], res['high95'] = np.percentile(boots, 2.5, axis=0), np.percentile(boots, 97.5, axis=0)
    return res


def budget_plan(curve, budget, contact_cost):
    """Best row of a profit curve that the budget can pay for (contacts x cost <= budget)."""
    ok = curve[curve.contacts * contact_cost <= budget + 1e-9]
    return ok.loc[ok.profit.idxmax()]


# ---------- 5. measurement: control groups, sample size, drift ----------
def _z(alpha, power):
    from scipy.stats import norm
    return norm.ppf(1 - alpha / 2) + norm.ppf(power)


def sample_size_per_group(base_rate, lift, alpha=0.05, power=0.8):
    """Customers needed in EACH group (contacted and held back) to detect a given lift in buy rate.
    base_rate: buy rate without contact (e.g. 0.60) | lift: extra buy rate to detect (e.g. 0.02 = 2 points)."""
    p1, p2 = base_rate, base_rate + lift
    return int(np.ceil(_z(alpha, power) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / lift ** 2))


def min_detectable_lift(n_contacted, n_control, base_rate, alpha=0.05, power=0.8):
    """Smallest lift (in buy rate) a test of this size can reliably detect."""
    return _z(alpha, power) * np.sqrt(base_rate * (1 - base_rate) * (1 / n_control + 1 / n_contacted))


def psi(expected, actual, bins=10):
    """Population stability index: how much a measure's distribution moved (build customers vs new ones).
    Rule of thumb: under 0.1 stable, 0.1-0.25 watch, over 0.25 shifted (retrain)."""
    e, a = pd.Series(expected).dropna().astype(float), pd.Series(actual).dropna().astype(float)
    if e.nunique() <= bins:
        cats = np.union1d(e.unique(), a.unique())
        pe, pa = e.value_counts(normalize=True).reindex(cats, fill_value=0), a.value_counts(normalize=True).reindex(cats, fill_value=0)
    else:
        edges = np.unique(np.quantile(e, np.linspace(0, 1, bins + 1))); edges[0], edges[-1] = -np.inf, np.inf
        pe = pd.cut(e, edges).value_counts(normalize=True, sort=False); pa = pd.cut(a, edges).value_counts(normalize=True, sort=False)
    pe, pa = np.clip(pe.values, 1e-4, None), np.clip(pa.values, 1e-4, None)
    return float(np.sum((pa - pe) * np.log(pa / pe)))


def drift_report(build_df, new_df, features, bins=10):
    """PSI for every feature with a traffic light."""
    r = pd.DataFrame({'psi': [psi(build_df[f], new_df[f], bins) for f in features]}, index=features).sort_values('psi', ascending=False)
    r['status'] = np.select([r.psi > 0.25, r.psi > 0.1], ['red: retrain', 'amber: watch'], 'green: stable')
    return r
