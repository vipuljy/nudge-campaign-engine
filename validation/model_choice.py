"""Improvement 2: which ranking model should be the default? Fast engine vs thorough ensemble (S + X + DR) vs ensemble + causal
forest (rank average of S, X, DR and CF). Same protocol as Part B: one fit on the training rows, scored once on the test.
    benchmarks : Part B's saved test scores (ensemble + CF = (3 x ensemble + rank(CF)) / 4, exactly the 4-way rank average)
    Part A     : DEVELOPMENT seeds (original + 8000, never used before), truth known: Spearman and Qini per option
    timing     : 1 lakh rows (run alone): fit + score time per model"""
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklift.metrics import qini_auc_score

import common
from lib import planner, thorough, upload
import engine_v2
import part_a
import part_b
import run_part_a
import synth

DEV = 8000
MODELS = ['fast', 'ensemble', 'ensemble_cf']


def bench(name):
    X, y, t, _ = part_b.load(name); tr, te = part_b.splits(name, y, t); yte, tte = y[te], t[te]
    ld = lambda m: np.load(part_b.SCORES / f"{name}__{''.join(ch for ch in m if ch.isalnum())}.npy")
    ens, cf = ld('Nudge ensemble (thorough)'), ld('econml CausalForestDML')
    S = {'fast': ld('Nudge fast engine'), 'ensemble': ens, 'ensemble_cf': (3 * ens + rankdata(cf) / len(cf)) / 4}
    perm = np.random.default_rng(part_b.SEED + 1).permutation(len(yte)); yte, tte = yte[perm], tte[perm]
    S = {k: v[perm] for k, v in S.items()}
    rng = np.random.default_rng(1); B = [rng.integers(0, len(yte), len(yte)) for _ in range(200)]
    out = {}
    for k, u in S.items():
        bq = [qini_auc_score(yte[i], u[i], tte[i]) for i in B]
        out[k] = {'qini': float(qini_auc_score(yte, u, tte)), 'low95': float(np.percentile(bq, 2.5)), 'high95': float(np.percentile(bq, 97.5))}
    best = max(v['qini'] for v in out.values())
    for v in out.values():
        v['share_of_best'] = v['qini'] / best if best > 0 else None
    return out


def synth_dev(n, arms, outcome, seed):
    df, truth, opts = synth.make(n, arms, outcome, seed)
    value = part_a.VALUE[outcome]; prep = upload.prepare(df, part_a.mapping(df, outcome))
    offers = ({o: {'type': 'Discount', 'face': c['reward'], 'rate': 1.0} if c['reward'] else {'type': 'Reminder (no offer)'}
               for o, c in synth.OPTIONS_4.items()} if arms == 4 else {'Message': {'type': 'Reminder (no offer)'}})
    res = planner.train(prep, value, 1.0, offers)
    pool, te, ctrl, tg = pd.concat([res['build'], res['val']]), res['test'], prep['control'], res['target']
    kind = prep['kind'] if tg == '_y' else 'amount'; feats = prep['features']
    eff = synth.true_effect_engine_units(truth.loc[te.index], opts, outcome, value, res['rewards'], res['has_reward'])
    out = {m: {'spearman': [], 'qini': [], 'secs': 0.0} for m in MODELS}
    perm = np.random.default_rng(2027).permutation(len(te))
    for o in opts:
        m = pool._option.isin([o, ctrl]).values
        X, t, y = pool.loc[m, feats], (pool._option.values[m] == o).astype(int), pool[tg].values[m].astype(float)
        t0 = time.time(); fast = engine_v2.r_fast(X, t, y, kind, [te[feats]])[0]; tf = time.time() - t0
        t0 = time.time(); L = engine_v2.r_learners(X, t, y, kind, [te[feats]]); tl = time.time() - t0
        t0 = time.time(); cf = engine_v2.r_cf(X, t, y, kind, [te[feats]])[0]; tc = time.time() - t0
        parts = [rankdata(L[k][0]) / len(te) for k in ['S-learner', 'X-learner', 'DR-learner']]
        S = {'fast': fast, 'ensemble': np.mean(parts, axis=0), 'ensemble_cf': np.mean(parts + [rankdata(cf) / len(te)], axis=0)}
        secs = {'fast': tf, 'ensemble': tl, 'ensemble_cf': tl + tc}
        mt = (te._option.values == o) | (te._option.values == ctrl); idx = perm[mt[perm]]
        yy, tt = te[tg].values[idx].astype(float), (te._option.values[idx] == o).astype(int)
        for k, u in S.items():
            out[k]['spearman'].append(float(spearmanr(u, eff[o].values)[0]))
            out[k]['qini'].append(float(qini_auc_score(yy, u[idx], tt) if kind == 'binary' else thorough.qini(yy, tt, u[idx])))
            out[k]['secs'] += secs[k]
    return {k: {'spearman': float(np.mean(v['spearman'])), 'qini': float(np.mean(v['qini'])), 'secs': v['secs']} for k, v in out.items()}


if __name__ == '__main__':
    what = sys.argv[1]
    if what == 'bench':
        for d in ['criteo10', 'lenta', 'megafon', 'hillstrom']:
            r = bench(d); common.save(f'M_bench_{d}', r)
            print(d, {k: (round(v['qini'], 4), round(v['share_of_best'] or 0, 3)) for k, v in r.items()}, flush=True)
    elif what == 'synth':
        for n in run_part_a.SIZES:
            for arms in (2, 4):
                for outcome in ('binary', 'revenue'):
                    name = f'M_dev_{n}_{arms}arm_{outcome}'
                    if common.load(name):
                        continue
                    r = synth_dev(n, arms, outcome, run_part_a.seed_of(n, arms, outcome) + DEV); common.save(name, r)
                    print(name, {k: (round(v['spearman'], 3), round(v['qini'], 4), round(v['secs'])) for k, v in r.items()}, flush=True)
