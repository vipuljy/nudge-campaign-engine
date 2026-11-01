"""RUN 2: the approved package as built into validation/app_v2 (the real app/ is untouched), on FRESH data.
Run with NUDGE_APP=validation/app_v2 NUDGE_RUN=run2 (results saved as validation/cache/run2_*.json; Run 1 is never overwritten).
Pass marks: VALIDATION_PLAN.md (unchanged); what is judged in Run 2: its section "Run 2 (decided 30 Oct 2026 ...)".
    a          Part A: 12 files, seeds original + 9000; the 2 lakh files also with 5 folds forced (accuracy cost of 3 folds)
    null       A3: seeds 9101-9120 (50k, 2-arm, yes/no, no effect, ₹1.02 per contact)
    b [names]  Part B: new split (seed 2036), fresh 10% Criteo sample (seed 2036); package + the Run 1 methods. NOT independent.
    d          Part D: 50k 2-arm yes/no (seed + 9000), the package retrained 5 times with only the models' seeds changed
    sample     the Hillstrom sample (range vs today's plan is in the report) and whether the existing caution message shows
    timing <cores> <rows>   upload -> plan through app_v2, process pinned to <cores> cores, peak memory"""
import sys
import threading
import time
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import common
from lib import planner, robust, thorough, upload
import part_a
import run_part_a
import synth

FRESH = 9000


# ---------------- Part A ----------------
def _offers(arms):
    return ({o: {'type': 'Discount', 'face': c['reward'], 'rate': 1.0} if c['reward'] else {'type': 'Reminder (no offer)'}
             for o, c in synth.OPTIONS_4.items()} if arms == 4 else {'Message': {'type': 'Reminder (no offer)'}})


def _used(P, ctrl, n):
    """The assignment the app recommends: the personalised plan, or the simple plan for everyone."""
    if P['personalise']:
        return np.asarray(P['rec'], dtype=object)
    return np.array([ctrl if P['blanket'] == 'Contact nobody' else P['best_opt']] * n, dtype=object)


def _spearman(a, b):
    return 0.0 if np.ptp(a) == 0 else float(spearmanr(a, b)[0])          # a constant ranking ("no reliable signal") counts as 0


def a_one(n, arms, outcome, seed, folds=None):
    df, truth, opts = synth.make(n, arms, outcome, seed)
    value = part_a.VALUE[outcome]; prep = upload.prepare(df, part_a.mapping(df, outcome))
    train_cost = 5.0 if arms == 2 else float(np.mean([c['contact'] for c in synth.OPTIONS_4.values()]))
    keep = robust.LARGE
    if folds == 5:
        robust.LARGE = 10 ** 12                                         # force 5 folds (for the 3 vs 5 folds comparison)
    try:
        t0 = time.time(); res = planner.train(prep, value, train_cost, _offers(arms)); secs = time.time() - t0
    finally:
        robust.LARGE = keep
    te = res['test']; tt = truth.loc[te.index]; ctrl = prep['control']
    out = {'n': n, 'arms': arms, 'outcome': outcome, 'seed': seed, 'train_secs': secs, 'folds': res['folds'], 'ranker': res['ranker'],
           'fallback_reason': res['fallback_reason'], 'n_test': len(te)}
    cost_sets = ({f'contact Rs{c:g}': {'Message': {'contact': c, 'reward': 0.0}} for c in (5.0, 1.02)} if arms == 2
                 else {'per-option costs': synth.OPTIONS_4})
    out['A2'] = {}
    for label, costs in cost_sets.items():
        contact = {o: costs[o]['contact'] for o in opts}
        P = planner.plan(res, prep, value, None, costs=contact)
        Pt = synth.true_profit(tt, opts, outcome, value, costs); use = _used(P, ctrl, len(te))
        r = part_a.plan_profit_ratio(use, Pt, ctrl)
        out['A2'][label] = {**r, 'personalise': bool(P['personalise']), 'recommended': P['recommended'], 'margin': P['margin'],
                            'share_contacted': float(np.mean(use != ctrl)), 'signal_message': P['signal_message'],
                            'signal': P['signal'], 'choice_values': P['choice_values']}
        if label in ('contact Rs5', 'per-option costs'):
            pred = P['pred']
    out['judged_cost'] = 'contact Rs5' if arms == 2 else 'per-option costs'
    eff = synth.true_effect_engine_units(tt, opts, outcome, value, res['rewards'], res['has_reward'])
    A, B = pred[opts].to_numpy(), eff[opts].to_numpy()
    avg = lambda i: np.mean([_spearman(A[i, j], B[i, j]) for j in range(len(opts))])
    lo, hi = common.boot_range(avg, len(A))
    out['A1'] = {'per_option': {o: _spearman(A[:, j], B[:, j]) for j, o in enumerate(opts)}, 'spearman': avg(np.arange(len(A))),
                 'low95': lo, 'high95': hi}
    return out


def run_a():
    for n in run_part_a.SIZES:
        for arms in (2, 4):
            for outcome in ('binary', 'revenue'):
                seed = run_part_a.seed_of(n, arms, outcome) + FRESH
                for folds in ([None, 5] if n == 200_000 else [None]):
                    name = f'A_{n}_{arms}arm_{outcome}' + ('_5folds' if folds == 5 else '')
                    if common.load(name):
                        continue
                    r = a_one(n, arms, outcome, seed, folds); common.save(name, r); j = r['A2'][r['judged_cost']]
                    print(name, r['folds'], 'folds', r['ranker'], '| A1', round(r['A1']['spearman'], 3), '| A2', round(j['ratio'], 3),
                          j['recommended'], f"| {r['train_secs']:.0f} s", flush=True)


def run_null():
    N = common.load('A3_null') or {'runs': []}
    for s in range(9101, 9121):
        if s in {r['seed'] for r in N['runs']}:
            continue
        df, truth, opts = synth.make(50_000, 2, 'binary', s, null=True)
        prep = upload.prepare(df, part_a.mapping(df, 'binary'))
        res = planner.train(prep, 150.0, 1.02, {'Message': {'type': 'Reminder (no offer)'}})
        P = planner.plan(res, prep, 150.0, 1.02); use = _used(P, prep['control'], len(res['test']))
        N['runs'].append({'seed': s, 'personalise': bool(P['personalise']), 'recommended': P['recommended'],
                          'signal_fired': P['signal_message'] is not None, 'share_contacted': float(np.mean(use != prep['control'])),
                          'true_profit_per_customer': float(-1.02 * np.mean(use != prep['control'])), 'signal': P['signal'],
                          'ranker': res['ranker'], 'folds': res['folds']})
        common.save('A3_null', N); print('null', s, P['recommended'], '| signal fired', P['signal_message'] is not None, flush=True)


# ---------------- Part B ----------------
class _Stub:                     # the package's ranking needs no option chances or costs for a Qini
    prop, tau = None, None


PACKAGE = {}


def m_package(Xtr, ytr, ttr, Xte):
    """The app's default ranking: RobustEngine (ensemble, cross-fitted, calibrated, whole-file signal rule) on the training rows.
    If the rule finds no reliable signal, the ranking is constant (the app does not rank); the raw ensemble is kept for information."""
    pool = Xtr.assign(_option=np.where(ttr == 1, 'treat', 'control'), _y=ytr.astype(float), _id=np.arange(len(ytr)).astype(str))
    prep = {'control': 'control', 'features': list(Xtr.columns), 'options': ['treat'], 'kind': 'binary'}
    eng = robust.RobustEngine(_Stub(), 'ensemble').fit(pool, prep, '_y', say=lambda m: print('   ', m, flush=True))
    s = np.mean([robust._rank01(np.mean([fm[p](Xte) for fm in eng.models['treat']], axis=0)) for p in robust.LEARNERS], axis=0)
    PACKAGE.update({'signal': eng.signal, 'diag': eng.diag, 'folds': eng.folds, 'ranker': eng.ranker, 'raw_ensemble': s})
    return eng._uplift(Xte)['treat'].values


def run_b(names):
    import part_b
    part_b.SEED = 2036
    part_b.SPLITS, part_b.SCORES = common.BENCH / 'splits_run2', common.BENCH / 'scores_run2'
    for p in (part_b.SPLITS, part_b.SCORES):
        p.mkdir(parents=True, exist_ok=True)

    def criteo10_2036():
        f = part_b.RAW / 'criteo' / 'criteo10_sample_seed2036.parquet'
        if f.exists():
            return pd.read_parquet(f)
        rng = np.random.default_rng(2036); parts = []
        for c in pd.read_csv(part_b.RAW / 'criteo' / 'criteo-research-uplift-v2.1.csv.gz', chunksize=1_000_000):
            parts.append(c[rng.random(len(c)) < 0.10])
        d = pd.concat(parts, ignore_index=True); d.to_parquet(f); return d
    part_b.criteo10 = criteo10_2036
    part_b.METHODS['Nudge package (app default)'] = m_package
    part_b.SIZED.append('Nudge package (app default)')
    for d in names or ['hillstrom', 'megafon', 'criteo10', 'lenta']:
        print(d, '...', flush=True)
        out = part_b.run(d, log=lambda s: print(s, flush=True))
        out['label'] = 'NOT INDEPENDENT: the default was chosen partly using these 4 datasets (new split seed 2036; fresh Criteo sample)'
        p = part_b.SCORES / f"{d}__package_raw_ensemble.npy"
        if PACKAGE:
            np.save(p, PACKAGE['raw_ensemble'])
            out['package'] = {k: v for k, v in PACKAGE.items() if k != 'raw_ensemble'}; PACKAGE.clear()
        common.save(f'B_{d}', out)


# ---------------- Part D ----------------
def run_d():
    n, arms, outcome = 50_000, 2, 'binary'
    df, truth, opts = synth.make(n, arms, outcome, run_part_a.seed_of(n, arms, outcome) + FRESH)
    prep = upload.prepare(df, part_a.mapping(df, outcome))
    res = planner.train(prep, 150.0, 5.0, {'Message': {'type': 'Reminder (no offer)'}})
    te = res['test']; orig = thorough._models; scores = {}
    for s in range(1, 6):                     # only the models' seeds change: LightGBM's random_state and the fold assignment
        def seeded(kind, m, s=s):
            mk, mr = orig(kind, m)
            return (lambda: mk().set_params(random_state=s)), (lambda: mr().set_params(random_state=s))
        thorough._models = seeded
        try:
            eng = robust.RobustEngine(res['fast_engine'], 'ensemble').fit(res['pool'], prep, '_y', seed=2028 + s)
        finally:
            thorough._models = orig
        scores[s] = eng._uplift(te)['Message'].values
        print('seed', s, 'signal', eng.signal, flush=True)
    k = int(round(0.2 * len(te)))

    def overlaps(idx):
        tops = {s: set(planner._desc(u[idx])[:k].tolist()) for s, u in scores.items()}
        return {(a, b): len(tops[a] & tops[b]) / k for a, b in combinations(scores, 2)}
    full = overlaps(np.arange(len(te))); rng = np.random.default_rng(1)
    boots = [np.mean(list(overlaps(rng.integers(0, len(te), len(te))).values())) for _ in range(200)]
    pairs = {f'{a}-{b}': v for (a, b), v in full.items()}
    out = {'n_test': len(te), 'top_k': k, 'pairs': pairs, 'average_overlap': float(np.mean(list(full.values()))),
           'average_low95': float(np.percentile(boots, 2.5)), 'average_high95': float(np.percentile(boots, 97.5)),
           'lowest_pair': min(pairs, key=pairs.get), 'lowest_overlap': float(min(pairs.values())),
           'pass': bool(np.mean(list(full.values())) >= 0.70), 'seed': run_part_a.seed_of(n, arms, outcome) + FRESH}
    common.save('D_stability', out); print(out)


# ---------------- Hillstrom sample ----------------
def run_sample():
    import apptest_page
    from nudge_engine import evaluate_policies
    S = upload.SAMPLES['hillstrom']; df = pd.read_csv(upload.SAMPLES_DIR / S['file'])
    prep = upload.prepare(df, {**S['mapping']}); value, cost = 0.15 * S['per_unit'], 0.01
    res = planner.train(prep, value, cost, {o: {'type': 'Reminder (no offer)'} for o in prep['options']})
    P = planner.plan(res, prep, value, cost); te, ctrl = res['test'], prep['control']; k = value
    use = _used(P, ctrl, len(te)); everyone = [P['best_opt']] * len(te)
    e = evaluate_policies(te, '_option', res['target'], {'app_v2': use, 'everyone': everyone, 'nobody': [ctrl] * len(te)},
                          res['engine'].prop, {o: cost / k for o in prep['options']}, n_boot=200, baseline='everyone')
    out = {'recommended': P['recommended'], 'share_contacted': float(np.mean(use != ctrl)), 'diff_blanket': P['diff']['blanket'],
           'app_v2_minus_everyone': [float((e.loc['app_v2', 'value_per_customer'] - e.loc['everyone', 'value_per_customer']) * k),
                                     float(e.loc['app_v2', 'vs_low95'] * k), float(e.loc['app_v2', 'vs_high95'] * k)],
           'note': "today's app recommends 'Contact everyone (Mens E-Mail)' on this sample (Run 1 / development)"}
    page = apptest_page.run_page('hillstrom_sample', df, sample='hillstrom')
    texts = ' '.join(str(x) for x in page.get('plan_texts', []))
    out['page_exceptions'] = sum(len(st.get('exceptions', [])) for _, st in page['stages'])
    out['caution_shown'] = any(w in texts for w in ('does not confirm it', 'the range includes zero', 'not a reliable gain'))
    out['caution_phrases'] = [w for w in ('does not confirm it', 'the range includes zero', 'not a reliable gain') if w in texts]
    out['page_harness_error'] = page.get('harness_error')
    common.save('sample_hillstrom', out); print(out)


# ---------------- timing (pinned cores) ----------------
def run_timing(cores, rows):
    import psutil
    if cores < psutil.cpu_count():
        psutil.Process().cpu_affinity(list(range(cores)))
    me = psutil.Process(); peak = [0]

    def watch():
        while True:
            peak[0] = max(peak[0], me.memory_info().rss); time.sleep(0.2)
    threading.Thread(target=watch, daemon=True).start()
    f = common.BENCH / 'partC' / ('rows_1lakh.csv' if rows == 100_000 else 'rows_2lakh.csv')
    raw = f.read_bytes(); cpu0, w0 = sum(me.cpu_times()[:2]), time.time(); t = {}
    t0 = time.time(); df = upload.read_csv(raw); m = {**upload.guess_mapping(df), 'labels': {}}; upload.validate(df, m)
    prep = upload.prepare(df, m); t['read_prepare_s'] = time.time() - t0
    msgs = []
    t0 = time.time(); res = planner.train(prep, 150.0, 0.10, {o: {'type': 'Reminder (no offer)'} for o in prep['options']},
                                          status=lambda s: msgs.append((round(time.time() - t0, 1), s)))
    t['train_s'] = time.time() - t0
    t0 = time.time(); planner.plan(res, prep, 150.0, 0.10); t['plan_s'] = time.time() - t0
    t['total_s'] = sum(t.values())
    out = common.load('timing') or {}
    out[f'{cores}cores_{rows}rows'] = {**t, 'peak_memory_mb': peak[0] / 1e6, 'avg_cores_busy': (sum(me.cpu_times()[:2]) - cpu0) / (time.time() - w0),
                                       'folds': res['folds'], 'ranker': res['ranker'], 'progress_messages': len(msgs),
                                       'first_messages': [m for _, m in msgs[:4]]}
    common.save('timing', out); print('RESULT', cores, rows, {k: round(v, 1) for k, v in t.items()}, round(peak[0] / 1e6), 'MB', flush=True)


if __name__ == '__main__':
    assert common.RUN == 'run2' and 'app_v2' in str(common.APP), 'run with NUDGE_APP=validation/app_v2 NUDGE_RUN=run2'
    w = sys.argv[1]
    {'a': run_a, 'null': run_null, 'd': run_d, 'sample': run_sample}.get(w, lambda: None)()
    if w == 'b':
        run_b(sys.argv[2:])
    elif w == 'timing':
        run_timing(int(sys.argv[2]), int(sys.argv[3]))
