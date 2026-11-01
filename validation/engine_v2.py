"""Candidate engine v2 (validation code only; the app is NOT changed). Five improvements on top of the app's planner:

1. Cross-fitted decision: 5 folds over the 80% (build + validation). Every customer there gets an honest score from models that
   never saw them (out-of-fold, "OOF"); plans are chosen on those scores instead of one 16% slice.
2. Model choice: the ranking model is the fast engine (DR), the thorough ensemble (S + X + DR rank average) or the ensemble plus
   econml's causal forest.
3. Guard: on the OOF scores, Nudge's ranking is compared with the usual likely-buyer ranking (Qini); the better one is used.
4. Calibration: a monotone map from score to uplift size, fitted on OOF deciles (isotonic regression, plus a tiny strictly
   increasing term so no two scores tie): the ranking cannot change, but sizes match measured lift.
5. No reliable signal: if the ranking's OOF Qini 95% range includes 0, the option gets no personal targeting (its predicted
   uplift = its average effect); if no option has a signal, the plan is the best simple plan and the reason is said in words.
The untouched 20% (the planner's own test part) is used only for scoring.
"""
import os
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.isotonic import IsotonicRegression

import common  # noqa: F401
from lib import planner, thorough
from nudge_engine import NudgeEngine, evaluate_policies, policy_value

MARGINS = [0, 0.1, 0.25, 0.5, 1, 2]


def _q(y, t, u):
    """Qini area (the app's thorough.qini: works for yes/no and amounts), ties broken at random."""
    p = np.random.default_rng(5).permutation(len(y))
    return thorough.qini(y[p].astype(float), t[p], u[p])


# ---------------- rankers: fit on (X, t, y) of one option vs control, return raw scores for several frames ----------------
def r_fast(X, t, y, kind, outs):
    d = X.assign(_option=np.where(t == 1, 'o', 'c'), _y=y.astype(float))
    eng = NudgeEngine(list(X.columns), '_option', 'c', '_y', margin=0).fit(d)
    return [eng.tau['o'].predict(o) for o in outs]


def r_learners(X, t, y, kind, outs):
    """S, X, DR learners of thorough mode, raw predictions (ranked later)."""
    mk, mr = thorough._models(kind, len(y)); e = t.mean(); X = X.reset_index(drop=True)
    res = {}
    for m in ['S-learner', 'X-learner', 'DR-learner']:
        f = thorough.METHODS[m]
        res[m] = [f(mk, mr, X, t, y.astype(float), o.reset_index(drop=True), e) for o in outs]
    return res


def r_cf(X, t, y, kind, outs):
    from econml.dml import CausalForestDML
    from sklearn.dummy import DummyClassifier
    from sklearn.impute import SimpleImputer
    import lightgbm as lgb
    imp = SimpleImputer(strategy='median', keep_empty_features=True).fit(X)
    reg = lgb.LGBMRegressor(n_estimators=250, learning_rate=0.03, num_leaves=15, min_child_samples=300, subsample=0.8,
                            subsample_freq=1, colsample_bytree=0.7, reg_lambda=10.0, verbose=-1, random_state=2026)
    cf = CausalForestDML(model_y=reg, model_t=DummyClassifier(strategy='prior'), discrete_treatment=True, cv=2, n_estimators=200,
                         min_samples_leaf=50, n_jobs=int(os.environ.get('NUDGE_JOBS', -1)), random_state=2026).fit(y.astype(float), t, X=imp.transform(X))
    return [cf.effect(imp.transform(o)).ravel() for o in outs]


def r_likely(X, t, y, kind, outs):
    m = planner._usual_model(kind, int(t.sum())).fit(X[t == 1], y[t == 1])
    return [planner._score(m, o) for o in outs]


def _rank01(u):
    return rankdata(u) / len(u)


class Calibrator:
    """Score -> uplift size. Isotonic fit of measured lift on score deciles (OOF), plus 1e-9 x rank so the map is strictly
    increasing (no ties, ranking unchanged)."""
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


def scores(res, prep, rankers=('fast', 'ensemble', 'likely'), folds=5, seed=2028, log=None):
    """OOF scores on the 80% and fold-averaged scores on the test 20%, per option and ranker."""
    ctrl, feats, tg = prep['control'], prep['features'], res['target']
    kind = prep['kind'] if tg == '_y' else 'amount'
    pool = pd.concat([res['build'], res['val']]); te = res['test']
    ids = pool['_id'].unique(); fold_of = pd.Series(np.random.default_rng(seed).permutation(len(ids)) % folds, index=ids)
    f = pool['_id'].map(fold_of).values
    need = set(rankers) | ({'fast'} if 'ensemble_cf' in rankers else set())
    out, secs = {}, {}
    for o in prep['options']:
        S = {r: {'oof': np.zeros(len(pool)), 'test': np.zeros(len(te))} for r in ['fast', 'likely', 'cf']}
        L = {m: {'oof': np.zeros(len(pool)), 'test': np.zeros(len(te))} for m in ['S-learner', 'X-learner', 'DR-learner']}
        for i in range(folds):
            trm = (f != i) & pool._option.isin([o, ctrl]).values
            Xa, ta, ya = pool.loc[trm, feats], (pool._option.values[trm] == o).astype(int), pool[tg].values[trm].astype(float)
            outs = [pool.loc[f == i, feats], te[feats]]
            if 'fast' in need or 'ensemble_cf' in rankers:
                t0 = time.time(); a, b = r_fast(Xa, ta, ya, kind, outs); S['fast']['oof'][f == i] = a; S['fast']['test'] += b / folds
                secs['fast'] = secs.get('fast', 0) + time.time() - t0
            if 'ensemble' in need or 'ensemble_cf' in rankers:
                t0 = time.time(); r = r_learners(Xa, ta, ya, kind, outs)
                for m, (a, b) in r.items():
                    L[m]['oof'][f == i] = a; L[m]['test'] += b / folds
                secs['ensemble'] = secs.get('ensemble', 0) + time.time() - t0
            if 'ensemble_cf' in rankers:
                t0 = time.time(); a, b = r_cf(Xa, ta, ya, kind, outs); S['cf']['oof'][f == i] = a; S['cf']['test'] += b / folds
                secs['cf'] = secs.get('cf', 0) + time.time() - t0
            if 'likely' in need:
                t0 = time.time(); a, b = r_likely(Xa, ta, ya, kind, outs); S['likely']['oof'][f == i] = a; S['likely']['test'] += b / folds
                secs['likely'] = secs.get('likely', 0) + time.time() - t0
            if log:
                log(f'    option {o}: fold {i + 1}/{folds} done')
        res_o = {}
        if 'fast' in rankers:
            res_o['fast'] = S['fast']
        if 'likely' in rankers:
            res_o['likely'] = S['likely']
        ens_parts = ['S-learner', 'X-learner', 'DR-learner']
        if 'ensemble' in rankers or 'ensemble_cf' in rankers:
            # rank-average within each held-out fold (OOF) and within the test part, as thorough mode does
            def ens(parts):
                oof = np.zeros(len(pool))
                for i in range(folds):
                    m = f == i; oof[m] = np.mean([_rank01(P[m]) for P in parts['oof']], axis=0)
                return {'oof': oof, 'test': np.mean([_rank01(P) for P in parts['test']], axis=0)}
            base = {'oof': [L[m]['oof'] for m in ens_parts], 'test': [L[m]['test'] for m in ens_parts]}
            if 'ensemble' in rankers:
                res_o['ensemble'] = ens(base)
            if 'ensemble_cf' in rankers:
                res_o['ensemble_cf'] = ens({'oof': base['oof'] + [S['cf']['oof']], 'test': base['test'] + [S['cf']['test']]})
        out[o] = res_o
    return {'pool': pool, 'fold': f, 'scores': out, 'secs': secs, 'kind': kind}


def plan(res, prep, value, contact, sc, ranker='fast', guard=True, calibrate=True, signal=True, proof=False, n_boot=200):
    """The v2 plan from OOF scores. Returns the plan for the test part plus every diagnostic."""
    ctrl, tg = prep['control'], res['target']; pool, te = sc['pool'], res['test']
    k = res['fixed_scale'] or value; oc = {o: contact[o] / k for o in prep['options']}
    prop = res['engine'].prop; diag = {}
    pred_oof, pred_te = {}, {}
    for o in prep['options']:
        s = sc['scores'][o]; m = pool._option.isin([o, ctrl]).values
        y, t = pool[tg].values[m].astype(float), (pool._option.values[m] == o).astype(int)
        q = {r: _q(y, t, s[r]['oof'][m]) for r in s}
        use = ranker
        if guard and 'likely' in s and q['likely'] > q[ranker]:
            use = 'likely'
        rng = np.random.default_rng(3); bq = []
        u = s[use]['oof'][m]
        for _ in range(n_boot):
            i = rng.integers(0, len(y), len(y)); bq.append(_q(y[i], t[i], u[i]))
        lo, hi = float(np.percentile(bq, 2.5)), float(np.percentile(bq, 97.5))
        reliable = lo > 0
        ate = y[t == 1].mean() - y[t == 0].mean()
        if calibrate:
            cal = Calibrator().fit(u, t, y); po, pt = cal(s[use]['oof']), cal(s[use]['test'])
        else:
            po, pt = s[use]['oof'].copy(), s[use]['test'].copy()
        pred_oof[o], pred_te[o] = po, pt
        diag[o] = {'oof_qini': q, 'used': use, 'guard_switched': use != ranker, 'oof_qini_used_low95': lo, 'oof_qini_used_high95': hi,
                   'reliable': bool(reliable), 'ate_oof': float(ate)}
    # "no reliable signal": signal=True flattens each option without one (per option); signal='file' only when NO option has one
    none = not any(d['reliable'] for d in diag.values())
    for o in prep['options']:
        if (signal is True and not diag[o]['reliable']) or (signal == 'file' and none):
            pred_oof[o], pred_te[o] = np.full(len(pool), diag[o]['ate_oof']), np.full(len(te), diag[o]['ate_oof'])
        pred_oof[o], pred_te[o] = pred_oof[o] - oc[o], pred_te[o] - oc[o]
    P_oof = pd.DataFrame(pred_oof, index=pool.index); P_oof[ctrl] = 0.0
    P_te = pd.DataFrame(pred_te, index=te.index); P_te[ctrl] = 0.0
    default = P_oof.mean().idxmax(); dflt_eff = abs(P_oof.mean().drop(ctrl).max())

    def rec(P, mult):
        best = P.idxmax(axis=1); adv = P.max(axis=1) - P[default]
        return best.where(adv > mult * dflt_eff, default).values

    any_signal = any(d['reliable'] for d in diag.values()) or not signal
    cands = {}
    if any_signal:
        for mult in MARGINS:
            cands[f'margin x{mult}'] = policy_value(pool, '_option', tg, rec(P_oof, mult), prop, oc)
    best_opt = P_oof.drop(columns=ctrl).mean().idxmax()
    cands['everyone'] = policy_value(pool, '_option', tg, [best_opt] * len(pool), prop, oc)
    cands['nobody'] = policy_value(pool, '_option', tg, [ctrl] * len(pool), prop, oc)
    choice = max(cands, key=cands.get)
    simple = 'everyone' if cands['everyone'] >= cands['nobody'] else 'nobody'; proof_info = None
    if proof and choice.startswith('margin'):
        # burden of proof: personalise only if, on customers the models had not seen (OOF), the personalised plan beats the best
        # simple plan with a 95% range above zero (paired bootstrap); otherwise keep the simple plan
        e = evaluate_policies(pool, '_option', tg, {'pers': rec(P_oof, float(choice.split('x')[1])),
                                                    'simple': [best_opt if simple == 'everyone' else ctrl] * len(pool)},
                              prop, oc, n_boot=n_boot, seed=4, baseline='simple')
        proof_info = {'margin': choice, 'gain': float(e.loc['pers', 'vs_baseline'] * k), 'low95': float(e.loc['pers', 'vs_low95'] * k),
                      'high95': float(e.loc['pers', 'vs_high95'] * k), 'proven': bool(e.loc['pers', 'vs_low95'] > 0)}
        if not proof_info['proven']:
            choice = simple
    if choice.startswith('margin'):
        r = rec(P_te, float(choice.split('x')[1])); recommended = f'Nudge plan ({choice})'
    else:
        r = np.array([best_opt if choice == 'everyone' else ctrl] * len(te), dtype=object)
        recommended = f'Contact everyone ({best_opt})' if choice == 'everyone' else 'Contact nobody'
    message = None
    if signal and not any(d['reliable'] for d in diag.values()):
        message = ('No reliable signal: on customers the model had not seen, its ranking did not beat a random order '
                   '(the 95% range includes zero). So Nudge does not personalise and recommends the simple plan: '
                   f'{recommended.lower()}.')
    if proof_info and not proof_info['proven'] and message is None:
        message = ('Personalising was not clearly better than the simple plan on customers the model had not seen (the 95% range '
                   f'of the gain includes zero), so Nudge recommends the simple plan: {recommended.lower()}.')
    return {'rec': np.asarray(r, dtype=object), 'recommended': recommended, 'proof': proof_info, 'pred_test': P_te, 'diag': diag,
            'cand_values': {c: v * k for c, v in cands.items()}, 'message': message, 'any_signal': bool(any_signal)}
