"""Scores the v2 pipeline (engine_v2) on a file, with ablations, on the planner's untouched 20%:
    for ranker in (fast, ensemble):  full v2 | without guard | without "no signal" rule;  fast also without calibration
Measured on the test part: Qini of the ranking actually used, calibration slope by decile (calibrated vs raw), whether the
ranking changed (Spearman raw vs calibrated = 1), measured profit vs contacting nobody, and the truth where known.
Development data: Part A seeds +8000, the benchmarks' existing split, the app's samples. (Final confirmation = Run 2, other seeds.)"""
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklift.metrics import qini_auc_score

import common
from lib import planner, thorough, upload
from nudge_engine import evaluate_policies
import engine_v2
import part_a
import run_part_a
import synth

DEV = 8000


def _test_metrics(res, prep, sc, P, contact, value, ranker):
    te, ctrl, tg = res['test'], prep['control'], res['target']; k = res['fixed_scale'] or value
    kind = sc['kind']; perm = np.random.default_rng(2027).permutation(len(te)); out = {'per_option': {}}
    for o in prep['options']:
        used = P['diag'][o]['used']; raw = sc['scores'][o][used]['test']; cal = P['pred_test'][o].values + contact[o] / k
        mt = (te._option.values == o) | (te._option.values == ctrl); idx = perm[mt[perm]]
        y, t = te[tg].values[idx].astype(float), (te._option.values[idx] == o).astype(int)
        q = float(qini_auc_score(y, raw[idx], t) if kind == 'binary' else thorough.qini(y, t, raw[idx]))
        same_rank = bool(np.allclose(spearmanr(raw, cal)[0], 1.0)) if np.ptp(cal) > 0 else None
        out['per_option'][o] = {'used': used, 'test_qini': q, 'rank_unchanged': same_rank,
                                'slope_calibrated': _slope(y, t, cal[idx]), 'reliable': P['diag'][o]['reliable']}
    oc = {o: contact[o] / k for o in prep['options']}; n = len(te)
    e = evaluate_policies(te, '_option', tg, {'plan': P['rec'], 'nobody': [ctrl] * n}, res['engine'].prop, oc, n_boot=200, baseline='nobody')
    out['measured_extra_per_customer'] = [(e.loc['plan', 'value_per_customer'] - e.loc['nobody', 'value_per_customer']) * k,
                                          e.loc['plan', 'vs_low95'] * k, e.loc['plan', 'vs_high95'] * k]
    out['recommended'] = P['recommended']; out['message'] = P['message']
    out['share_contacted'] = float(np.mean(P['rec'] != ctrl))
    return out


def _slope(y, t, u, bins=10):
    if np.ptp(u) == 0:
        return None
    q = pd.qcut(pd.Series(u).rank(method='first'), bins, labels=False).values; xs, ys = [], []
    for b in range(bins):
        m = q == b; a, c = y[m & (t == 1)], y[m & (t == 0)]
        if len(a) and len(c):
            xs.append(u[m].mean()); ys.append(a.mean() - c.mean())
    return float(np.polyfit(xs, ys, 1)[0]) if np.std(xs) > 0 else None


def evaluate(prep, value, contact, offers, truth_fn=None, rankers=('fast', 'ensemble'), log=None):
    res = planner.train(prep, value, float(np.mean(list(contact.values()))), offers)
    t0 = time.time(); sc = engine_v2.scores(res, prep, rankers=tuple(rankers) + ('likely',), log=log); t_sc = time.time() - t0
    out = {'secs_scores': t_sc, 'secs_by_model': sc['secs'], 'variants': {}}
    # raw fast-engine calibration (before): the app's engine as is, trained on build, on the test part
    te, ctrl, tg = res['test'], prep['control'], res['target']; perm = np.random.default_rng(2027).permutation(len(te))
    k = res['fixed_scale'] or value; out['slope_app_engine'] = {}
    for o in prep['options']:
        mt = (te._option.values == o) | (te._option.values == ctrl); idx = perm[mt[perm]]
        u = res['engine'].tau[o].predict(te[prep['features']])
        out['slope_app_engine'][o] = _slope(te[tg].values[idx].astype(float), (te._option.values[idx] == o).astype(int), u[idx])
    for r in rankers:
        vs = {'full': {}, 'no_guard': {'guard': False}, 'no_signal_rule': {'signal': False}}
        if r == 'fast':
            vs['no_calibration'] = {'calibrate': False}
        for v, kw in vs.items():
            P = engine_v2.plan(res, prep, value, contact, sc, ranker=r, **kw)
            m = _test_metrics(res, prep, sc, P, contact, value, r)
            m['oof_diag'] = P['diag']
            if truth_fn:
                m.update(truth_fn(res, P))
            out['variants'][f'{r}/{v}'] = m
    return out


def synth_case(n, arms, outcome, seed, null=False, evaluator=None):
    df, truth, opts = synth.make(n, arms, outcome, seed, null=null)
    value = part_a.VALUE[outcome]; prep = upload.prepare(df, part_a.mapping(df, outcome))
    if arms == 4:
        costs = synth.OPTIONS_4
        offers = {o: {'type': 'Discount', 'face': c['reward'], 'rate': 1.0} if c['reward'] else {'type': 'Reminder (no offer)'}
                  for o, c in costs.items()}
    else:
        c = 1.02 if null else 5.0
        costs = {'Message': {'contact': c, 'reward': 0.0}}; offers = {'Message': {'type': 'Reminder (no offer)'}}
    contact = {o: costs[o]['contact'] for o in opts}

    def truth_fn(res, P):
        te = res['test']; tt = truth.loc[te.index]; Pt = synth.true_profit(tt, opts, outcome, value, costs)
        r = part_a.plan_profit_ratio(P['rec'], Pt, prep['control'])
        eff = synth.true_effect_engine_units(tt, opts, outcome, value, res['rewards'], res['has_reward'])
        rho = float(np.mean([spearmanr(P['pred_test'][o], eff[o])[0] if np.ptp(P['pred_test'][o].values) > 0 else 0.0 for o in opts]))  # no ranking = 0
        return {'A2_ratio': r['ratio'], 'A2_low95': r['low95'], 'A2_high95': r['high95'], 'true_per_customer': r['plan_per_customer'],
                'A1_spearman_used': rho}
    return (evaluator or evaluate)(prep, value, contact, offers, truth_fn)


def bench_case(name, evaluator=None):
    import part_b
    X, y, t, _ = part_b.load(name)
    raw = X.assign(_arm=np.where(t == 1, 'treat', 'control'), _out=y)
    m = {'option': '_arm', 'control': 'control', 'outcome': '_out', 'id': None, 'features': list(X.columns), 'labels': {}}
    prep = upload.prepare(raw, m); del raw, X
    return (evaluator or evaluate)(prep, 150.0, {'treat': 1.02}, {'treat': {'type': 'Reminder (no offer)'}}, log=lambda s: print(s, flush=True))


def sample_case(key, evaluator=None):
    S = upload.SAMPLES[key]; df = pd.read_csv(upload.SAMPLES_DIR / S['file'])
    prep = upload.prepare(df, {**S['mapping']})
    value, cost = (150.0, S['custom_cost']) if key == 'synthetic' else (0.15 * S['per_unit'], 0.01)
    return (evaluator or evaluate)(prep, value, {o: cost for o in prep['options']}, {o: {'type': 'Reminder (no offer)'} for o in prep['options']})


if __name__ == '__main__':
    what = sys.argv[1]
    if what == 'bench':
        for d in sys.argv[2:] or ['hillstrom', 'megafon', 'criteo10', 'lenta']:
            if common.load(f'V_bench_{d}'):
                continue
            print(d, '...', flush=True); common.save(f'V_bench_{d}', bench_case(d))
    elif what == 'samples':
        for s in ['synthetic', 'hillstrom']:
            if not common.load(f'V_sample_{s}'):
                common.save(f'V_sample_{s}', sample_case(s)); print('sample', s, flush=True)
    elif what == 'synth':
        for n in run_part_a.SIZES:
            for arms in (2, 4):
                for outcome in ('binary', 'revenue'):
                    name = f'V_dev_{n}_{arms}arm_{outcome}'
                    if not common.load(name):
                        common.save(name, synth_case(n, arms, outcome, run_part_a.seed_of(n, arms, outcome) + DEV)); print(name, flush=True)
        N = common.load('V_dev_null') or {'runs': []}
        for s in range(8101, 8121):
            if s not in {r['seed'] for r in N['runs']}:
                r = synth_case(50_000, 2, 'binary', s, null=True); r['seed'] = s; N['runs'].append(r); common.save('V_dev_null', N)
                print('null', s, {v: x['recommended'] for v, x in r['variants'].items()}, flush=True)
