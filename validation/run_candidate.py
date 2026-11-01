"""Score the candidate fix exactly like Part A (same files, same split, same truth). Usage:
    python validation/run_candidate.py dev       development seeds (choose settings here; never the official seeds)
    python validation/run_candidate.py official  run 2 on the official Part A seeds (once), saved as A_run2_*.json"""
import sys

import numpy as np
from scipy.stats import spearmanr

import common
from lib import planner, upload
import candidate_fix
import part_a
import run_part_a
import synth


def evaluate(n, arms, outcome, seed, null=False, min_gain=0.0, contact_2arm=5.0):
    df, truth, opts = synth.make(n, arms, outcome, seed, null=null)
    value = part_a.VALUE[outcome]; prep = upload.prepare(df, part_a.mapping(df, outcome))
    if arms == 4:
        costs = synth.OPTIONS_4
        offers = {o: {'type': 'Discount', 'face': c['reward'], 'rate': 1.0} if c['reward'] else {'type': 'Reminder (no offer)'}
                  for o, c in costs.items()}
    else:
        costs = {'Message': {'contact': contact_2arm, 'reward': 0.0}}; offers = {'Message': {'type': 'Reminder (no offer)'}}
    contact = {o: costs[o]['contact'] for o in opts}
    res = planner.train(prep, value, float(np.mean(list(contact.values()))), offers)
    D = candidate_fix.decide_cv(res, prep, value, contact, min_gain=min_gain)
    te = res['test']; tt = truth.loc[te.index]
    out = {'n': n, 'arms': arms, 'outcome': outcome, 'seed': seed, 'null': null, 'recommended': D['recommended'],
           'personalise': D['personalise'], 'cv_values': D['cv_values']}
    if not null:
        P = synth.true_profit(tt, opts, outcome, value, costs)
        out['A2'] = part_a.plan_profit_ratio(D['rec'], P, prep['control'])
        eff = synth.true_effect_engine_units(tt, opts, outcome, value, res['rewards'], res['has_reward'])
        pred = D['engine'].predict(te)
        A, B = pred[opts].to_numpy(), eff[opts].to_numpy()
        avg = lambda i: np.mean([spearmanr(A[i, j], B[i, j])[0] for j in range(len(opts))])
        lo, hi = common.boot_range(avg, len(A))
        out['A1'] = {'spearman': avg(np.arange(len(A))), 'low95': lo, 'high95': hi}
    return out


if __name__ == '__main__':
    mode = sys.argv[1]; mg = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    if mode == 'dev':
        for arms, outcome in [(2, 'binary'), (2, 'revenue'), (4, 'binary'), (4, 'revenue')]:
            r = evaluate(50_000, arms, outcome, 900 + arms * 10 + (outcome == 'revenue'), min_gain=mg)
            print(f"dev 50k {arms}-arm {outcome}: spearman {r['A1']['spearman']:.3f}, plan/oracle {r['A2']['ratio']:.3f} "
                  f"({r['recommended']})", flush=True)
        k = sum(not evaluate(50_000, 2, 'binary', 500 + s, null=True, min_gain=mg)['personalise'] for s in range(1, 21))
        print(f'dev null: "do not personalise" in {k} of 20 (min_gain {mg})', flush=True)
    else:
        for n in run_part_a.SIZES:
            if n == 5_000:
                continue
            for arms in (2, 4):
                for outcome in ('binary', 'revenue'):
                    name = f'A_run2_{n}_{arms}arm_{outcome}'
                    if common.load(name):
                        continue
                    r = evaluate(n, arms, outcome, run_part_a.seed_of(n, arms, outcome), min_gain=mg); common.save(name, r)
                    print(f"{name}: spearman {r['A1']['spearman']:.3f} [{r['A1']['low95']:.3f}, {r['A1']['high95']:.3f}], "
                          f"plan/oracle {r['A2']['ratio']:.3f} [{r['A2']['low95']:.3f}, {r['A2']['high95']:.3f}] ({r['recommended']})", flush=True)
        null = common.load('A3_run2_null') or {'runs': []}
        for s in range(1, 21):
            if s in {r['seed'] for r in null['runs']}:
                continue
            r = evaluate(50_000, 2, 'binary', s, null=True, min_gain=mg); null['runs'].append(r); common.save('A3_run2_null', null)
            print(f"null seed {s}: {r['recommended']}", flush=True)
