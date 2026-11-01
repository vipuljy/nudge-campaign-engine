"""Part D: stability. Part A's 50k 2-arm binary file; the planner's own split (same build / test customers every run);
the engine retrained 5 times with only the models' random seed changed (model_params random_state 1..5).
Top-20% target list = the 20% of test customers with the highest predicted extra value. Overlap = share of one list in the other."""
from itertools import combinations

import numpy as np

import common
from lib import planner, upload
from nudge_engine import NudgeEngine
import part_a
import run_part_a
import synth


def run():
    n, arms, outcome = 50_000, 2, 'binary'
    df, truth, opts = synth.make(n, arms, outcome, run_part_a.seed_of(n, arms, outcome))
    prep = upload.prepare(df, part_a.mapping(df, outcome))
    res = planner.train(prep, 150.0, 5.0, {'Message': {'type': 'Reminder (no offer)'}})
    build, te = res['build'], res['test']
    scores = {}
    for s in range(1, 6):
        eng = NudgeEngine(prep['features'], '_option', prep['control'], '_y', group='_id', margin=0,
                          model_params={'random_state': s}).fit(build)
        scores[s] = eng.tau['Message'].predict(te[prep['features']])
    k = int(round(0.2 * len(te)))

    def overlaps(idx):
        # positions within the (re)sample, so a customer drawn twice counts as two places, as in the full list
        tops = {s: set(np.argsort(-u[idx], kind='stable')[:k].tolist()) for s, u in scores.items()}
        return {(a, b): len(tops[a] & tops[b]) / k for a, b in combinations(scores, 2)}

    full = overlaps(np.arange(len(te)))
    rng = np.random.default_rng(1); boots = []
    for _ in range(200):
        boots.append(np.mean(list(overlaps(rng.integers(0, len(te), len(te))).values())))
    pairs = {f'{a}-{b}': v for (a, b), v in full.items()}
    out = {'n_test': len(te), 'top_k': k, 'pairs': pairs, 'average_overlap': float(np.mean(list(full.values()))),
           'average_low95': float(np.percentile(boots, 2.5)), 'average_high95': float(np.percentile(boots, 97.5)),
           'lowest_pair': min(pairs, key=pairs.get), 'lowest_overlap': float(min(pairs.values())),
           'pass': bool(np.mean(list(full.values())) >= 0.70)}
    common.save('D_stability', out)
    return out


if __name__ == '__main__':
    r = run()
    print(f"D1 average top-20% overlap {r['average_overlap']:.3f} [{r['average_low95']:.3f}, {r['average_high95']:.3f}]; "
          f"lowest pair {r['lowest_pair']} {r['lowest_overlap']:.3f}; pass={r['pass']}")
