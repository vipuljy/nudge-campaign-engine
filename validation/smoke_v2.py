"""Smoke test of the package as built into validation/app_v2 (run with NUDGE_APP=validation/app_v2). Development seeds only.
    1. 5k 4-arm file: train -> plan (per-option costs) -> curves -> target_list run, ranker = ensemble
    2. fallback: the ensemble is made to fail -> the fast engine is used and the reason is recorded
    3. equivalence: the 50k 2-arm binary DEV seed through app_v2 vs the development result (engine_v2, ensemble, whole-file rule)"""
import time

import numpy as np

import common
from lib import planner, robust, upload
import part_a
import run_part_a
import synth


def case(n, arms, outcome, seed, ranker='ensemble'):
    df, truth, opts = synth.make(n, arms, outcome, seed)
    value = part_a.VALUE[outcome]; prep = upload.prepare(df, part_a.mapping(df, outcome))
    if arms == 4:
        costs = synth.OPTIONS_4
        offers = {o: {'type': 'Discount', 'face': c['reward'], 'rate': 1.0} if c['reward'] else {'type': 'Reminder (no offer)'}
                  for o, c in costs.items()}
    else:
        costs = {'Message': {'contact': 5.0, 'reward': 0.0}}; offers = {'Message': {'type': 'Reminder (no offer)'}}
    contact = {o: costs[o]['contact'] for o in opts}
    t0 = time.time(); res = planner.train(prep, value, float(np.mean(list(contact.values()))), offers, status=print, ranker=ranker)
    P = planner.plan(res, prep, value, None, costs=contact); secs = time.time() - t0
    tt = truth.loc[res['test'].index]; Pt = synth.true_profit(tt, opts, outcome, value, costs)
    rec = np.asarray(P['rec'] if P['personalise'] else [P['best_opt'] if P['blanket'] != 'Contact nobody' else prep['control']] * len(tt), dtype=object)
    return res, P, prep, part_a.plan_profit_ratio(rec, Pt, prep['control']), secs


if __name__ == '__main__':
    res, P, prep, r, s = case(5000, 4, 'binary', 4242)
    print('1.', res['ranker'], res['folds'], 'folds |', P['recommended'], '| A2', round(r['ratio'], 3), '| signal', P['signal_message'], round(s), 's')
    C = planner.curves(res, prep, P); T = planner.target_list(res, prep, 150.0, P['margin'])
    print('   curves', C.shape, 'target list', T.shape, T.in_plan.value_counts().to_dict())

    orig = robust.FIT['X-learner']
    robust.FIT['X-learner'] = lambda *a, **k: (_ for _ in ()).throw(ValueError('forced failure for the test'))
    res2, P2, _, r2, _ = case(5000, 2, 'binary', 4243)
    robust.FIT['X-learner'] = orig
    print('2. fallback ->', res2['ranker'], '|', res2['fallback_reason'], '|', P2['recommended'])

    seed = run_part_a.seed_of(50000, 2, 'binary') + 8000
    res3, P3, _, r3, s3 = case(50000, 2, 'binary', seed)
    dev = common.load('V_dev_50000_2arm_binary')['variants']['ensemble/full']
    print('3. app_v2', P3['recommended'], 'A2', round(r3['ratio'], 3), f'({round(s3)} s) | development', dev['recommended'], 'A2', round(dev['A2_ratio'], 3))
