"""v2 with the FAST engine only (the proposed app default): the variants needed for the proposal, on DEVELOPMENT data only.
    current   : the app's rule today (planner's 16% slice; per-option costs via part_a.decide)
    v2_5f     : 5-fold decision + guard + calibration + "no reliable signal" rule
    v2_5f_proof: the same + burden of proof (personalise only if the OOF gain over the best simple plan has a 95% range above 0)
    v2_3f_proof: the same with 3 folds (cheaper)
Each v2 variant is compared with `current` on the planner's untouched 20% (paired bootstrap); truth where known.
Development data: Part A seeds +8000 (null 8101-8120), the app's samples, the benchmarks through the planner path."""
import os
import sys
import time

import numpy as np

import common
from lib import planner  # noqa: F401
from nudge_engine import evaluate_policies
import engine_v2
import eval_v2
import part_a
import run_part_a

VARIANTS = os.environ.get('EVAL_VARIANTS', 'fast')     # 'proposal' = the candidate package (results saved with prefix P_)


def evaluate(prep, value, contact, offers, truth_fn=None, log=None):
    res = planner.train(prep, value, float(np.mean(list(contact.values()))), offers)
    te, ctrl, tg = res['test'], prep['control'], res['target']; k = res['fixed_scale'] or value
    oc = {o: contact[o] / k for o in prep['options']}
    plans, secs, out = {}, {}, {'variants': {}}
    t0 = time.time(); D = part_a.decide(res, prep, value, contact); secs['current'] = time.time() - t0
    plans['current'] = {'rec': np.asarray(D['rec'], dtype=object), 'recommended': D['recommended'], 'message': None}
    if VARIANTS == 'proposal':        # the candidate package: whole-file "no signal" rule, calibration, with / without the guard
        t0 = time.time(); sc = engine_v2.scores(res, prep, rankers=('fast', 'ensemble', 'likely'), folds=5); ts = time.time() - t0
        for r in ('fast', 'ensemble'):
            for g in (True, False):
                name = f'{r}_file' + ('' if g else '_noguard')
                t0 = time.time(); plans[name] = engine_v2.plan(res, prep, value, contact, sc, ranker=r, guard=g, signal='file')
                secs[name] = sc['secs'].get(r, 0) + sc['secs'].get('likely', 0) + time.time() - t0
    else:
      for folds in (5, 3):
        t0 = time.time(); sc = engine_v2.scores(res, prep, rankers=('fast', 'likely'), folds=folds); ts = time.time() - t0
        for proof in ((False, True) if folds == 5 else (True,)):
            name = f'v2_{folds}f' + ('_proof' if proof else '')
            t0 = time.time(); P = engine_v2.plan(res, prep, value, contact, sc, ranker='fast', proof=proof)
            secs[name] = ts + time.time() - t0; plans[name] = P
    n = len(te)
    e = evaluate_policies(te, '_option', tg, {**{v: P['rec'] for v, P in plans.items()}, 'nobody': [ctrl] * n}, res['engine'].prop, oc,
                          n_boot=200, baseline='current')
    for v, P in plans.items():
        m = {'recommended': P['recommended'], 'share_contacted': float(np.mean(P['rec'] != ctrl)), 'secs_decision': secs[v],
             'measured_extra_per_customer': float((e.loc[v, 'value_per_customer'] - e.loc['nobody', 'value_per_customer']) * k),
             'message': P.get('message')}
        if v != 'current':
            m['vs_current'] = [float(e.loc[v, x] * k) for x in ('vs_baseline', 'vs_low95', 'vs_high95')]
            m['signal_fired'] = bool(P['message'] and P['message'].startswith('No reliable signal'))
            m['proof'] = P.get('proof'); m['proof_fired'] = bool(P.get('proof') and not P['proof']['proven'])
            m['guard_switched'] = {o: d['guard_switched'] for o, d in P['diag'].items()}
            m['reliable'] = {o: d['reliable'] for o, d in P['diag'].items()}
        if truth_fn:
            try:
                m.update(truth_fn(res, P))
            except KeyError:                                    # current rule: no calibrated predictions -> A2 only
                m.update({x: y for x, y in truth_fn(res, {**P, 'pred_test': res['engine'].predict(te)}).items() if x.startswith('A2')})
        out['variants'][v] = m
    return out


def synthetic_sample_truth():
    """The app's synthetic X5-like sample WITH its truth file (true lift per customer): true profit of each plan on the planner's
    untouched 20%, at the sample's own ₹150 per purchase and ₹5 per AI call; oracle = contact exactly those whose true lift pays."""
    import pandas as pd
    from lib import upload
    S = upload.SAMPLES['synthetic']; df = pd.read_csv(upload.SAMPLES_DIR / S['file'])
    lift = pd.read_csv(upload.SAMPLES_DIR / S['truth']).set_index('customer_id')['true_lift']
    lift.index = lift.index.astype(str)
    prep = upload.prepare(df, {**S['mapping']}); value, cost = 150.0, S['custom_cost']

    def truth_fn(res, P):
        te = res['test']; gain = lift.reindex(te['_id'].values).values * value - cost
        contact = np.asarray(P['rec']) != prep['control']; oracle = np.maximum(gain, 0).mean()
        rng = np.random.default_rng(1); B = [rng.integers(0, len(te), len(te)) for _ in range(200)]
        rb = [(contact[i] * gain[i]).mean() / np.maximum(gain[i], 0).mean() for i in B]
        return {'A2_ratio': float((contact * gain).mean() / oracle), 'A2_low95': float(np.percentile(rb, 2.5)),
                'A2_high95': float(np.percentile(rb, 97.5)), 'true_per_customer': float((contact * gain).mean())}
    return evaluate(prep, value, {o: cost for o in prep['options']}, {o: {'type': 'Reminder (no offer)'} for o in prep['options']}, truth_fn)


if __name__ == '__main__':
    what = sys.argv[1]
    if what == 'samples':
        for s in ['hillstrom', 'synthetic']:
            if not common.load(f'E_sample_{s}'):
                common.save(f'E_sample_{s}', eval_v2.sample_case(s, evaluate)); print('sample', s, flush=True)
    elif what == 'synthetic_truth':
        if not common.load('E_sample_synthetic_truth'):
            common.save('E_sample_synthetic_truth', synthetic_sample_truth()); print('synthetic truth', flush=True)
    elif what == 'bench':
        for d in sys.argv[2:] or ['hillstrom', 'megafon', 'criteo10', 'lenta']:
            if not common.load(f'E_bench_{d}'):
                common.save(f'E_bench_{d}', eval_v2.bench_case(d, evaluate)); print('bench', d, flush=True)
    elif what == 'null':
        N = common.load('E_dev_null') or {'runs': []}
        for s in range(8101, 8121):
            if s not in {r['seed'] for r in N['runs']}:
                r = eval_v2.synth_case(50_000, 2, 'binary', s, null=True, evaluator=evaluate); r['seed'] = s
                N['runs'].append(r); common.save('E_dev_null', N)
                print('null', s, {v: x['recommended'] for v, x in r['variants'].items()}, flush=True)
    elif what == 'synth':
        for n in run_part_a.SIZES:
            for arms in (2, 4):
                for outcome in ('binary', 'revenue'):
                    name = f'E_dev_{n}_{arms}arm_{outcome}'
                    if not common.load(name):
                        r = eval_v2.synth_case(n, arms, outcome, run_part_a.seed_of(n, arms, outcome) + eval_v2.DEV, evaluator=evaluate)
                        common.save(name, r)
                        print(name, {v: (x['recommended'][:22], round(x.get('A2_ratio', np.nan), 3)) for v, x in r['variants'].items()}, flush=True)
