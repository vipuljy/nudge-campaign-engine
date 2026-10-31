"""The robust ranking (validated in VALIDATION_REPORT_v2.md). Four rules, one sentence each:

1. Honest scores: the 80% (build + validation) is split into 5 folds by customer (3 folds above 1,50,000 rows, to stay fast); every
   customer is scored by models that never saw them, and the plan is chosen on those scores, not on one small slice.
2. Ensemble ranking: three standard uplift learners (S, X and DR, as in Step 4) each rank the customers and the ranks are averaged;
   if the ensemble fails for any reason, the fast engine (one DR model per option) is used instead.
3. Calibration: the ranking is turned into a predicted uplift size by matching measured lift in each tenth of customers (a monotone
   map, so the order of customers never changes).
4. No reliable signal: if no option's ranking beats a random order on customers the models had not seen (95% range of the Qini
   includes zero), nothing is personalised and Nudge says so in plain words.

RobustEngine has the same methods the planner and the pages use from NudgeEngine (predict, recommend, with_costs, prop, tau)."""
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.isotonic import IsotonicRegression

from lib import thorough
from nudge_engine import NudgeEngine

FOLDS, FOLDS_LARGE, LARGE = 5, 3, 150_000
LEARNERS = ['S-learner', 'X-learner', 'DR-learner']


# ---------- learners that keep their fitted models (same models and maths as thorough.METHODS) ----------
def _fit_s(mk, mr, X, t, y, e):
    m = mk().fit(X.assign(_t=t), y)
    return lambda Z: thorough._p(m, Z.assign(_t=1)) - thorough._p(m, Z.assign(_t=0))


def _fit_x(mk, mr, X, t, y, e):
    m1, m0 = mk().fit(X[t == 1], y[t == 1]), mk().fit(X[t == 0], y[t == 0])
    r1 = mr().fit(X[t == 1], y[t == 1] - thorough._p(m0, X[t == 1]))
    r0 = mr().fit(X[t == 0], thorough._p(m1, X[t == 0]) - y[t == 0])
    return lambda Z: e * r1.predict(Z) + (1 - e) * r0.predict(Z)


def _fit_dr(mk, mr, X, t, y, e):
    n = len(y); h = np.random.default_rng(0).permutation(n); A, B = h[:n // 2], h[n // 2:]; psi = np.zeros(n)
    for fi, pi in [(A, B), (B, A)]:                                    # cross-fitting
        Xf, tf, yf = X.iloc[fi], t[fi], y[fi]
        m1, m0 = mk().fit(Xf[tf == 1], yf[tf == 1]), mk().fit(Xf[tf == 0], yf[tf == 0])
        mu1, mu0 = thorough._p(m1, X.iloc[pi]), thorough._p(m0, X.iloc[pi])
        psi[pi] = mu1 - mu0 + t[pi] * (y[pi] - mu1) / e - (1 - t[pi]) * (y[pi] - mu0) / (1 - e)
    return mr().fit(X, psi).predict


FIT = {'S-learner': _fit_s, 'X-learner': _fit_x, 'DR-learner': _fit_dr}


def _fit_fast(X, t, y):
    d = X.assign(_option=np.where(t == 1, 'o', 'c'), _y=y.astype(float))
    eng = NudgeEngine(list(X.columns), '_option', 'c', '_y', margin=0).fit(d)
    return eng.tau['o'].predict


def _rank01(u):
    return rankdata(u) / len(u)


def _qini(y, t, u):
    p = np.random.default_rng(5).permutation(len(y))                  # ties in random order
    return thorough.qini(y[p].astype(float), t[p], u[p])


class Calibrator:
    """Score -> uplift size: isotonic fit of measured lift on the score's tenths (weighted by size), plus 1e-9 x scaled score, so the
    map is strictly increasing (no new ties, order unchanged)."""
    def fit(self, s, t, y, bins=10):
        q = pd.qcut(pd.Series(s).rank(method='first'), bins, labels=False).values
        xs, ys, ws = [], [], []
        for b in range(bins):
            m = q == b; a, c = y[m & (t == 1)], y[m & (t == 0)]
            if len(a) and len(c):
                xs.append(s[m].mean()); ys.append(a.mean() - c.mean()); ws.append(m.sum())
        self.iso = IsotonicRegression(out_of_bounds='clip').fit(xs, ys, sample_weight=ws)
        self.lo, self.hi = float(np.min(s)), float(np.max(s))
        return self

    def __call__(self, s):
        return self.iso.predict(np.clip(s, self.lo, self.hi)) + 1e-9 * (s - self.lo) / max(self.hi - self.lo, 1e-12)


class RobustEngine:
    """Cross-fitted, calibrated ranking per option, with the base (fast) engine kept for the option chances and as the fallback."""

    def __init__(self, base: NudgeEngine, ranker: str = 'ensemble'):
        self.base, self.ranker, self.prop, self.tau = base, ranker, base.prop, base.tau
        self.fallback_reason, self.margin_mult, self._cache = None, 0.0, []

    # ---- fitting ----
    def fit(self, pool: pd.DataFrame, prep: dict, target: str, say=None, n_boot=200, seed=2028):
        say = say or (lambda s: None)
        if self.ranker == 'ensemble':
            try:
                return self._fit(pool, prep, target, say, n_boot, seed)
            except Exception as e:                                    # any failure: the fast engine instead, said in words
                self.fallback_reason = f'{type(e).__name__}: {e}'[:200]
                say(f'The thorough ranking failed ({type(e).__name__}); using the fast engine instead.')
                self.ranker = 'fast'
        return self._fit(pool, prep, target, say, n_boot, seed)

    def _fit(self, pool, prep, target, say, n_boot, seed):
        ctrl, feats = prep['control'], prep['features']
        kind = prep['kind'] if target == '_y' else 'amount'
        self.ctrl, self.feats, self.options, self.pool_index = ctrl, feats, list(prep['options']), pool.index
        self.folds = FOLDS_LARGE if len(pool) > LARGE else FOLDS
        ids = pool['_id'].unique(); fold_of = pd.Series(np.random.default_rng(seed).permutation(len(ids)) % self.folds, index=ids)
        f = pool['_id'].map(fold_of).values
        self.models, self.cal, self.diag, oof = {}, {}, {}, {}
        for j, o in enumerate(self.options):
            parts = LEARNERS if self.ranker == 'ensemble' else ['fast']
            raw = {p: np.zeros(len(pool)) for p in parts}; self.models[o] = []
            for i in range(self.folds):
                say(f'Learning "{o}" (option {j + 1} of {len(self.options)}): part {i + 1} of {self.folds}'
                    + (' (3 learners)...' if self.ranker == 'ensemble' else '...'))
                trm = (f != i) & pool._option.isin([o, ctrl]).values
                X = pool.loc[trm, feats].reset_index(drop=True)
                t, y = (pool._option.values[trm] == o).astype(int), pool[target].values[trm].astype(float)
                if self.ranker == 'ensemble':
                    mk, mr = thorough._models(kind, len(y)); e = t.mean()
                    fitted = {p: FIT[p](mk, mr, X, t, y, e) for p in parts}
                else:
                    fitted = {'fast': _fit_fast(X, t, y)}
                held = pool.loc[f == i, feats]
                for p in parts:
                    raw[p][f == i] = fitted[p](held)
                self.models[o].append(fitted)
            if self.ranker == 'ensemble':                             # rank-average within each held-out fold
                score = np.zeros(len(pool))
                for i in range(self.folds):
                    m = f == i; score[m] = np.mean([_rank01(raw[p][m]) for p in parts], axis=0)
            else:
                score = raw['fast']
            say(f'Checking "{o}": does the ranking beat a random order on customers it had not seen?')
            m = pool._option.isin([o, ctrl]).values
            y, t, u = pool[target].values[m].astype(float), (pool._option.values[m] == o).astype(int), score[m]
            rng = np.random.default_rng(3); bq = []
            for _ in range(n_boot):
                i = rng.integers(0, len(y), len(y)); bq.append(_qini(y[i], t[i], u[i]))
            lo, hi = float(np.percentile(bq, 2.5)), float(np.percentile(bq, 97.5))
            self.cal[o] = Calibrator().fit(u, t, y)
            oof[o] = self.cal[o](score)
            self.diag[o] = {'qini': float(_qini(y, t, u)), 'qini_low95': lo, 'qini_high95': hi, 'reliable': bool(lo > 0),
                            'ate': float(y[t == 1].mean() - y[t == 0].mean())}
        self.signal = any(d['reliable'] for d in self.diag.values())
        if not self.signal:                                           # rule 4: no option has a signal -> no personal targeting
            oof = {o: np.full(len(pool), self.diag[o]['ate']) for o in self.options}
        self.oof = pd.DataFrame(oof, index=pool.index)
        self.oc = {o: 0.0 for o in self.options}
        return self

    # ---- scoring ----
    def _uplift(self, df):
        """Calibrated predicted uplift per option (before contact costs) for any frame of customers."""
        for d, out in self._cache:
            if d is df:
                return out
        out = {}
        for o in self.options:
            if not self.signal:
                out[o] = np.full(len(df), self.diag[o]['ate']); continue
            X = df[self.feats]
            if self.ranker == 'ensemble':                             # fold-averaged predictions, ranked within this frame
                s = np.mean([_rank01(np.mean([fm[p](X) for fm in self.models[o]], axis=0)) for p in LEARNERS], axis=0)
            else:
                s = np.mean([fm['fast'](X) for fm in self.models[o]], axis=0)
            out[o] = self.cal[o](s)
        out = pd.DataFrame(out, index=df.index)
        self._cache = ([(df, out)] + self._cache)[:3]
        return out

    def with_costs(self, option_cost: dict, df=None):
        self.oc = dict(option_cost)
        if df is not None:
            self.base.with_costs(option_cost, df)
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extra value per option after contact cost (engine units); the control column is 0."""
        P = self._uplift(df) - pd.Series(self.oc); P[self.ctrl] = 0.0
        return P

    def oof_predict(self) -> pd.DataFrame:
        P = self.oof - pd.Series(self.oc); P[self.ctrl] = 0.0
        return P

    def _rec(self, P, margin_mult):
        """A customer gets their personal best option only if it beats the best-on-average option (judged on the honest scores) by
        margin x that option's average effect; otherwise the best-on-average option (or nothing, if nothing pays on average)."""
        O = self.oof_predict(); default = O.mean().idxmax(); dflt_eff = abs(O.mean().drop(self.ctrl).max())
        best = P.idxmax(axis=1); adv = P.max(axis=1) - P[default]
        return best.where(adv > margin_mult * dflt_eff, default)

    def recommend(self, df: pd.DataFrame, margin_mult=None) -> pd.Series:
        return self._rec(self.predict(df), self.margin_mult if margin_mult is None else margin_mult)

    def recommend_oof(self, margin_mult) -> np.ndarray:
        return self._rec(self.oof_predict(), margin_mult).values
