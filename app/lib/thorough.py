"""Thorough mode: Step 4 repeated on the uploaded file.

For each option vs the control: 5 uplift methods + the S+X+DR rank-average ensemble, compared by 5-fold cross-validation
on the build part (64% of the file); the winner is then trained on all of it and scored ONCE on the untouched 20%, next to the fast engine.
Same methods and settings as notebook 04, generalised so they work for yes/no outcomes (classifiers) and amounts (regressors);
leaf sizes shrink for small files so the trees can still split.
"""
import time

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.model_selection import KFold, StratifiedKFold


# ---------- scores that work for yes/no and for amounts ----------
def qini(y, t, u) -> float:
    """Area between the model's Qini curve and the random line, per customer. Higher = better ranking; 0 = random."""
    o = np.argsort(-u, kind='stable'); y, t = y[o], t[o]; n = len(y)
    nt, nc = np.cumsum(t), np.cumsum(1 - t)
    q = np.cumsum(y * t) - np.cumsum(y * (1 - t)) * np.divide(nt, nc, out=np.zeros(n), where=nc > 0)
    return float(q.mean() / n - q[-1] / n / 2)


def lift_at(y, t, u, k) -> float:
    """Real lift (contacted minus held back) among the top k share by the model's ranking."""
    top = u >= np.quantile(u, 1 - k)
    a, b = y[top & (t == 1)], y[top & (t == 0)]
    return float(a.mean() - b.mean()) if len(a) and len(b) else np.nan


# ---------- the Step 4 learners ----------
def _models(kind, n):
    c = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=int(min(400, max(20, n // 200))), subsample=0.8,
             subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0, verbose=-1, random_state=42)
    r = dict(n_estimators=200, learning_rate=0.03, num_leaves=15, min_child_samples=int(min(800, max(40, n // 100))), subsample=0.8,
             subsample_freq=1, colsample_bytree=0.7, reg_lambda=10.0, verbose=-1, random_state=42)
    outcome = (lambda: lgb.LGBMClassifier(**c)) if kind == 'binary' else (lambda: lgb.LGBMRegressor(**c))
    return outcome, (lambda: lgb.LGBMRegressor(**r))


def _p(m, X):
    return m.predict_proba(X)[:, 1] if hasattr(m, 'predict_proba') else m.predict(X)


def t_learner(mk, mr, Xtr, t, y, Xte, e):
    return _p(mk().fit(Xtr[t == 1], y[t == 1]), Xte) - _p(mk().fit(Xtr[t == 0], y[t == 0]), Xte)


def s_learner(mk, mr, Xtr, t, y, Xte, e):
    m = mk().fit(Xtr.assign(_t=t), y)
    return _p(m, Xte.assign(_t=1)) - _p(m, Xte.assign(_t=0))


def x_learner(mk, mr, Xtr, t, y, Xte, e):
    m1, m0 = mk().fit(Xtr[t == 1], y[t == 1]), mk().fit(Xtr[t == 0], y[t == 0])
    r1 = mr().fit(Xtr[t == 1], y[t == 1] - _p(m0, Xtr[t == 1]))       # contacted: actual - predicted without
    r0 = mr().fit(Xtr[t == 0], _p(m1, Xtr[t == 0]) - y[t == 0])       # held back: predicted with - actual
    return e * r1.predict(Xte) + (1 - e) * r0.predict(Xte)


def dr_learner(mk, mr, Xtr, t, y, Xte, e):
    n = len(y); h = np.random.default_rng(0).permutation(n); A, B = h[:n // 2], h[n // 2:]; psi = np.zeros(n)
    for fi, pi in [(A, B), (B, A)]:                                    # cross-fitting
        Xf, tf, yf = Xtr.iloc[fi], t[fi], y[fi]
        m1, m0 = mk().fit(Xf[tf == 1], yf[tf == 1]), mk().fit(Xf[tf == 0], yf[tf == 0])
        mu1, mu0 = _p(m1, Xtr.iloc[pi]), _p(m0, Xtr.iloc[pi])
        psi[pi] = mu1 - mu0 + t[pi] * (y[pi] - mu1) / e - (1 - t[pi]) * (y[pi] - mu0) / (1 - e)
    return mr().fit(Xtr, psi).predict(Xte)


def transformed_outcome(mk, mr, Xtr, t, y, Xte, e):
    """Class transformation, generalised: regress y x (t - e) / (e (1 - e)), whose average is the uplift."""
    return mr().fit(Xtr, y * (t - e) / (e * (1 - e))).predict(Xte)


METHODS = {'T-learner': t_learner, 'S-learner': s_learner, 'X-learner': x_learner, 'DR-learner': dr_learner,
           'Class transformation': transformed_outcome}
ENSEMBLE = 'Ensemble S+X+DR'


def _ensemble(preds):
    return np.mean([rankdata(preds[m]) / len(preds[m]) for m in ['S-learner', 'X-learner', 'DR-learner']], axis=0)


def _all(mk, mr, Xtr, t, y, Xte, e):
    p = {name: f(mk, mr, Xtr, t, y, Xte, e) for name, f in METHODS.items()}
    p[ENSEMBLE] = _ensemble(p)
    return p


def _metrics(y, t, u):
    return {'qini': qini(y, t, u), 'top10_lift': lift_at(y, t, u, 0.1), 'top30_lift': lift_at(y, t, u, 0.3)}


def run(prep: dict, res: dict, status=None, folds=5) -> dict:
    """Leaderboard per option (cross-validated on the 80%) and the winner vs the fast engine on the locked 20%."""
    say = status or (lambda s: None)
    ctrl, feats, kind = prep['control'], prep['features'], prep['kind']
    tr, te, eng = res['build'], res['test'], res['engine']
    out = {}
    for o in prep['options']:
        t0 = time.time()
        a = tr[tr._option.isin([o, ctrl])]; Xa, ta, ya = a[feats], (a._option == o).astype(int).values, a._y.values.astype(float)
        e = ta.mean(); mk, mr = _models(kind, int(len(a) * (folds - 1) / folds))
        split = (StratifiedKFold(folds, shuffle=True, random_state=42).split(Xa, ta * 2 + (ya > 0)) if kind == 'binary'
                 else KFold(folds, shuffle=True, random_state=42).split(Xa))
        rows = []
        for i, (f_tr, f_te) in enumerate(split):
            say(f'Option "{o}": fold {i + 1} of {folds} (6 methods)...')
            p = _all(mk, mr, Xa.iloc[f_tr], ta[f_tr], ya[f_tr], Xa.iloc[f_te], e)
            rows += [{'method': m, **_metrics(ya[f_te], ta[f_te], u)} for m, u in p.items()]
        cv = pd.DataFrame(rows).groupby('method').agg(qini=('qini', 'mean'), qini_sd=('qini', 'std'),
                                                       top10_lift=('top10_lift', 'mean'), top30_lift=('top30_lift', 'mean'))
        cv = cv.sort_values('qini', ascending=False); winner = cv.index[0]

        say(f'Option "{o}": training the winner ({winner}) on all build data and scoring the locked 20%...')
        b = te[te._option.isin([o, ctrl])]; Xb, tb, yb = b[feats], (b._option == o).astype(int).values, b._y.values.astype(float)
        mk, mr = _models(kind, len(a))
        if winner == ENSEMBLE:
            u_win = _ensemble({m: METHODS[m](mk, mr, Xa, ta, ya, Xb, e) for m in ['S-learner', 'X-learner', 'DR-learner']})
        else:
            u_win = METHODS[winner](mk, mr, Xa, ta, ya, Xb, e)
        u_fast = eng.tau[o].predict(Xb)                                 # the fast engine's own ranking for this option
        rng = np.random.default_rng(1); B = [rng.integers(0, len(yb), len(yb)) for _ in range(200)]
        locked = []
        for name, u in [(f'Winner: {winner}', u_win), ('Fast engine (DR, default)', u_fast)]:
            bq = [qini(yb[i], tb[i], u[i]) for i in B]
            locked.append({'model': name, **_metrics(yb, tb, u), 'qini_low95': np.percentile(bq, 2.5), 'qini_high95': np.percentile(bq, 97.5)})
        d = [qini(yb[i], tb[i], u_win[i]) - qini(yb[i], tb[i], u_fast[i]) for i in B]
        out[o] = {'cv': cv, 'winner': winner, 'locked': pd.DataFrame(locked).set_index('model'),
                  'gain_vs_fast': (float(np.mean(d)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))),
                  'rows': len(a), 'secs': time.time() - t0}
    return out
