"""Part B: public uplift benchmarks, the same protocol for every dataset and method.

1. Locked 20% test (stratified by treatment x outcome, seed 2026); row numbers saved in data_benchmarks/splits.
2. Every method trains on the same random 2,00,000 rows of the other 80% (all of it if smaller).
3. Features are encoded once with the app's own upload.prepare (text columns with up to 20 values become yes/no columns).
4. Scored once on the locked test: Qini and AUUC (scikit-uplift), real uplift in the top 10% / 30%, profit of contacting the top
   30%, calibration by decile; 95% ranges from a paired bootstrap (the same 200 resamples for every method).
Row-level scores are saved only under data_benchmarks/ (git-ignored); the cache keeps aggregates.
"""
import time

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklift.datasets import fetch_hillstrom, fetch_lenta, fetch_megafon
from sklift.metrics import qini_auc_score, uplift_auc_score

import common
from common import BENCH
from lib import planner, thorough, upload
from nudge_engine import NudgeEngine

RAW, SPLITS, SCORES = BENCH / 'raw', BENCH / 'splits', BENCH / 'scores'
for p in (SPLITS, SCORES):
    p.mkdir(parents=True, exist_ok=True)
TRAIN_ROWS, SEED = 200_000, 2026
VALUE, CONTACT = 150.0, 1.02            # ₹ per extra purchase / visit-equivalent, ₹ per contact (WhatsApp): ASSUMED
HILLSTROM_FEATURES = ['recency', 'history', 'mens', 'womens', 'zip_code', 'newbie', 'channel']    # as in Step 7


def load(name):
    """(features DataFrame, outcome 0/1, treated 0/1, description). Data stays in data_benchmarks/raw."""
    h = str(RAW)
    if name == 'criteo10':
        d = criteo10()
        X, y, t = d[[f'f{i}' for i in range(12)]], d.visit, d.treatment
        desc = ('Criteo (ads): 10% random sample (seed 2026) of the official 13.98M-row file; treatment = could be shown ads; '
                'outcome = site visit')
    elif name == 'lenta':
        b = fetch_lenta(data_home=h)
        X, y, t = b.data, b.target, (b.treatment == 'test').astype(int)
        desc = 'Lenta (Russian grocery): SMS vs no SMS; outcome = came and bought (response_att)'
    elif name == 'megafon':
        b = fetch_megafon(data_home=h)
        X, y, t = b.data, b.target, (b.treatment == 'treatment').astype(int)
        desc = 'MegaFon (telecom, synthetic-like features X_1..X_50): treatment vs control; outcome = conversion'
    elif name == 'hillstrom':
        b = fetch_hillstrom(target_col='visit', data_home=h)
        keep = b.treatment.isin(['Womens E-Mail', 'No E-Mail'])
        X, y, t = b.data[keep][HILLSTROM_FEATURES], b.target[keep], (b.treatment[keep] == 'Womens E-Mail').astype(int)
        desc = "Hillstrom: women's e-mail vs no e-mail; outcome = site visit in 2 weeks"
    X = X.reset_index(drop=True); y = np.asarray(y).astype(int); t = np.asarray(t).astype(int)
    return X, y, t, desc


def criteo10():
    """scikit-uplift's Criteo links are dead (404, 29 Oct 2026), so the official file from Criteo's Hugging Face page
    (criteo/criteo-uplift, criteo-research-uplift-v2.1.csv.gz) is read in chunks and a 10% random sample kept (seed 2026)."""
    f = RAW / 'criteo' / 'criteo10_sample.parquet'
    if f.exists():
        return pd.read_parquet(f)
    rng = np.random.default_rng(SEED); parts = []
    for c in pd.read_csv(RAW / 'criteo' / 'criteo-research-uplift-v2.1.csv.gz', chunksize=1_000_000):
        parts.append(c[rng.random(len(c)) < 0.10])
    d = pd.concat(parts, ignore_index=True); d.to_parquet(f)
    return d


def splits(name, y, t):
    """Locked test and training sample, saved once and re-used (so any method can be re-run on the same rows)."""
    f = SPLITS / f'{name}.npz'
    if f.exists():
        z = np.load(f); return z['train'], z['test']
    idx = np.arange(len(y))
    rest, test = train_test_split(idx, test_size=0.2, stratify=t * 2 + y, random_state=SEED)
    train = np.sort(np.random.default_rng(SEED).choice(rest, min(TRAIN_ROWS, len(rest)), replace=False))
    np.savez(f, train=train, test=np.sort(test))
    return splits(name, y, t)


def ate(y, t):
    d = y[t == 1].mean() - y[t == 0].mean()
    se = np.sqrt(y[t == 1].var() / (t == 1).sum() + y[t == 0].var() / (t == 0).sum())
    return {'ate': d, 'low95': d - 1.96 * se, 'high95': d + 1.96 * se}


# ---------------- the methods ----------------
def _lgb_reg():          # nuisance model for the econml methods: the engine's own outcome-model settings
    return lgb.LGBMRegressor(n_estimators=250, learning_rate=0.03, num_leaves=15, min_child_samples=300, subsample=0.8,
                             subsample_freq=1, colsample_bytree=0.7, reg_lambda=10.0, verbose=-1, random_state=SEED)


def m_likely(Xtr, ytr, ttr, Xte):
    """The usual approach (Step 5 / the app's planner): who buys when contacted."""
    m = planner._usual_model('binary', int(ttr.sum())).fit(Xtr[ttr == 1], ytr[ttr == 1])
    return m.predict_proba(Xte)[:, 1]


def m_engine(Xtr, ytr, ttr, Xte):
    """The app's fast engine: NudgeEngine (doubly robust, LightGBM, 2-fold cross-fitting), its predicted uplift for the option."""
    d = Xtr.assign(_option=np.where(ttr == 1, 'treat', 'control'), _y=ytr.astype(float))
    eng = NudgeEngine(list(Xtr.columns), '_option', 'control', '_y', margin=0).fit(d)
    return eng.tau['treat'].predict(Xte)


def m_ensemble(Xtr, ytr, ttr, Xte):
    """The app's thorough mode ensemble: S + X + DR learners, rank-averaged (same settings as app/lib/thorough.py)."""
    mk, mr = thorough._models('binary', len(ytr))
    e = ttr.mean(); Xtr = Xtr.reset_index(drop=True)
    p = {m: thorough.METHODS[m](mk, mr, Xtr, ttr, ytr.astype(float), Xte, e) for m in ['S-learner', 'X-learner', 'DR-learner']}
    return thorough._ensemble(p)


def _impute(Xtr, Xte):
    imp = SimpleImputer(strategy='median', keep_empty_features=True).fit(Xtr)
    return imp.transform(Xtr), imp.transform(Xte)


def m_causal_forest(Xtr, ytr, ttr, Xte):
    """econml CausalForestDML. Known chance of treatment (a random test): DummyClassifier(prior); outcome model LightGBM."""
    from econml.dml import CausalForestDML
    A, B = _impute(Xtr, Xte)
    cf = CausalForestDML(model_y=_lgb_reg(), model_t=DummyClassifier(strategy='prior'), discrete_treatment=True, cv=2,
                         n_estimators=200, min_samples_leaf=50, n_jobs=-1, random_state=SEED)
    cf.fit(ytr.astype(float), ttr, X=A)
    return cf.effect(B).ravel()


def m_r_learner(Xtr, ytr, ttr, Xte):
    """econml NonParamDML (the R-learner): residual-on-residual with a LightGBM final model."""
    from econml.dml import NonParamDML
    A, B = _impute(Xtr, Xte)
    final = lgb.LGBMRegressor(n_estimators=250, learning_rate=0.03, num_leaves=15, min_child_samples=300, subsample=0.8,
                              subsample_freq=1, colsample_bytree=0.7, reg_lambda=10.0, verbose=-1, random_state=SEED)
    r = NonParamDML(model_y=_lgb_reg(), model_t=DummyClassifier(strategy='prior'), model_final=final, discrete_treatment=True,
                    cv=2, random_state=SEED)
    r.fit(ytr.astype(float), ttr, X=A)
    return r.effect(B).ravel()


METHODS = {'Likely-buyer model': m_likely, 'Nudge fast engine': m_engine, 'Nudge ensemble (thorough)': m_ensemble,
           'econml CausalForestDML': m_causal_forest, 'econml R-learner (NonParamDML)': m_r_learner}
SIZED = ['Nudge fast engine', 'econml CausalForestDML', 'econml R-learner (NonParamDML)']   # predict an uplift SIZE (calibration)


# ---------------- scoring ----------------
def lift_top(y, t, u, k):
    top = np.argsort(-u, kind='stable')[:int(round(k * len(u)))]
    a, b = y[top][t[top] == 1], y[top][t[top] == 0]
    return a.mean() - b.mean() if len(a) and len(b) else np.nan


def metrics(y, t, u):
    l30 = lift_top(y, t, u, 0.3)
    return {'qini': qini_auc_score(y, u, t), 'auuc': uplift_auc_score(y, u, t), 'top10_lift': lift_top(y, t, u, 0.1),
            'top30_lift': l30, 'profit_top30_per_customer': 0.3 * (l30 * VALUE - CONTACT)}


def calibration(y, t, u, bins=10):
    q = pd.qcut(pd.Series(u).rank(method='first'), bins, labels=False)
    rows = []
    for b in range(bins):
        s = q.values == b
        rows.append({'decile': bins - b, 'predicted': float(u[s].mean()),
                     'measured': float(y[s & (t == 1)].mean() - y[s & (t == 0)].mean())})
    c = pd.DataFrame(rows).sort_values('decile')
    slope = float(np.polyfit(c.predicted, c.measured, 1)[0]) if c.predicted.std() > 0 else np.nan
    return {'by_decile': c.to_dict('records'), 'slope_measured_on_predicted': slope}


def run(name, methods=None, n_boot=200, log=print):
    out = common.load(f'B_{name}') or {}
    X, y, t, desc = load(name)
    tr, te = splits(name, y, t)
    keep = np.r_[tr, te]
    mapping = {'option': '_arm', 'control': 'control', 'outcome': '_out', 'id': None, 'features': list(X.columns), 'labels': {}}
    raw = X.iloc[keep].assign(_arm=np.where(t[keep] == 1, 'treat', 'control'), _out=y[keep]).reset_index(drop=True)
    out.update({'dataset': name, 'description': desc, 'rows_total': len(y), 'rows_train': len(tr), 'rows_test': len(te),
                'treated_share': float(t.mean()), 'outcome_rate': float(y.mean()), 'ate_full': ate(y, t), 'ate_test': ate(y[te], t[te]),
                'checks': upload.validate(raw, mapping)})
    del X
    prep = upload.prepare(raw, mapping)
    out['fairness'] = upload.fairness(prep['max_gap'], prep['min_group'], prep['n_control'])[0]
    out['max_gap'] = prep['max_gap']; out['features_used'] = len(prep['features']); out['features_dropped'] = prep['dropped']
    D = prep['data']; feats = prep['features']; ntr = len(tr)
    Xtr, Xte = D[feats].iloc[:ntr].reset_index(drop=True), D[feats].iloc[ntr:].reset_index(drop=True)
    ytr, yte = y[tr], y[te]; ttr, tte = t[tr], t[te]
    assert (D._y.values[:ntr] == ytr).all() and (D._y.values[ntr:] == yte).all()
    del raw, prep, D

    scores = {'Random order': np.random.default_rng(SEED).random(len(te))}
    out.setdefault('secs', {})
    for m, f in METHODS.items():
        if methods and m not in methods:
            continue
        p = SCORES / f"{name}__{''.join(ch for ch in m if ch.isalnum())}.npy"
        if p.exists():
            scores[m] = np.load(p); continue
        log(f'  {name}: {m}...'); t0 = time.time()
        scores[m] = np.asarray(f(Xtr, ytr, ttr, Xte), float); np.save(p, scores[m])
        out['secs'][m] = time.time() - t0; log(f'    {out["secs"][m]:.0f} s')
        common.save(f'B_{name}', out)
    for m in METHODS:                                          # pick up methods scored in an earlier run
        p = SCORES / f"{name}__{''.join(ch for ch in m if ch.isalnum())}.npy"
        if m not in scores and p.exists():
            scores[m] = np.load(p)

    # Ties: a method can give many customers exactly the same score (31% of Criteo's test rows for the fast engine), and sorting
    # then keeps them in file order. Criteo's file is ordered by treatment, so file order would bias the score. Run 2 onwards: the
    # test rows are shuffled once (seed 2027, the same for every method), so ties are broken at random. Run 1 kept file order.
    perm = np.random.default_rng(SEED + 1).permutation(len(yte))
    yte, tte = yte[perm], tte[perm]; scores = {m: u[perm] for m, u in scores.items()}
    out['tie_break'] = 'random: test rows shuffled once (seed 2027) before scoring'
    # point values, then a paired bootstrap: the same resamples for every method
    log(f'  {name}: scoring {len(scores)} rankings, {n_boot} bootstrap repeats...')
    pts = {m: metrics(yte, tte, u) for m, u in scores.items()}
    rng = np.random.default_rng(1); B = [rng.integers(0, len(yte), len(yte)) for _ in range(n_boot)]
    boots = {m: pd.DataFrame([metrics(yte[i], tte[i], u[i]) for i in B]) for m, u in scores.items()}
    table = {}
    for m in scores:
        row = {}
        for k, v in pts[m].items():
            row[k] = v; row[k + '_low95'] = float(np.nanpercentile(boots[m][k], 2.5)); row[k + '_high95'] = float(np.nanpercentile(boots[m][k], 97.5))
        if m != 'Nudge fast engine' and 'Nudge fast engine' in scores:
            d = boots['Nudge fast engine'].qini - boots[m].qini
            row['engine_minus_this_qini'] = pts['Nudge fast engine']['qini'] - pts[m]['qini']
            row['engine_minus_this_qini_low95'] = float(np.percentile(d, 2.5)); row['engine_minus_this_qini_high95'] = float(np.percentile(d, 97.5))
        if m in SIZED:
            row['calibration'] = calibration(yte, tte, scores[m])
        table[m] = row
    a = ate(yte, tte)
    table['Treat everyone'] = {'qini': None, 'note': 'no ranking (Qini undefined; same as random order)',
                               'profit_all_per_customer': a['ate'] * VALUE - CONTACT,
                               'profit_top30_per_customer': None}
    out['methods'] = table
    common.save(f'B_{name}', out)
    return out
