"""Builds the tables of the validation report from the cached aggregates (validation/cache/*.json). Pass marks as frozen in
VALIDATION_PLAN.md; this file only reads results and compares them with those marks."""
import pandas as pd

import common

SIZES = [5_000, 50_000, 200_000]
DATASETS = ['criteo10', 'lenta', 'megafon', 'hillstrom']


def f3(x):
    return f'{x:.3f}'


def part_a(run='A'):
    rows = []
    for n in SIZES:
        for arms in (2, 4):
            for outcome in ('binary', 'revenue'):
                r = common.load(f'{run}_{n}_{arms}arm_{outcome}' if run == 'A' else f'A_run2_{n}_{arms}arm_{outcome}')
                if not r:
                    continue
                a2 = r['A2'][r['judged_cost']] if run == 'A' else r['A2']
                row = {'rows': n, 'options': arms - 1, 'outcome': outcome,
                       'A1 Spearman': r['A1']['spearman'], 'A1 low95': r['A1']['low95'], 'A1 high95': r['A1']['high95'],
                       'A2 plan/oracle': a2['ratio'], 'A2 low95': a2['low95'], 'A2 high95': a2['high95'],
                       'plan chosen': a2['recommended'] if run == 'A' else r['recommended']}
                if run == 'A':
                    row['simple plan (truth)/oracle'] = a2['best_blanket_truth_ratio']
                    if arms == 2:
                        row['A2 at Rs1.02 (info)'] = r['A2']['contact Rs1.02']['ratio']
                rows.append(row)
    return pd.DataFrame(rows)


def null(run='A'):
    r = common.load('A3_null' if run == 'A' else 'A3_run2_null')
    if not r:
        return None
    runs = pd.DataFrame(r['runs'])
    k = int((~runs.personalise.astype(bool)).sum())
    from scipy.stats import beta
    n = len(runs); lo = beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0; hi = beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return {'runs': n, 'not_personalised': k, 'low95_rate': lo, 'high95_rate': hi, 'table': runs[['seed', 'personalise', 'recommended']]}


def part_b():
    out = {}
    for d in DATASETS:
        r = common.load(f'B_{d}')
        if not r or 'methods' not in r:
            continue
        t = pd.DataFrame({m: v for m, v in r['methods'].items()}).T
        out[d] = (r, t)
    return out


def b_marks(b):
    """B1: engine Qini range above 0 on every dataset with a real effect. B2: engine Qini >= 0.9 x best on >= 3 of 4."""
    rows = []
    for d, (r, t) in b.items():
        q = t['qini'].dropna().astype(float)
        e = t.loc['Nudge fast engine']; best = q.idxmax()
        real = r['ate_full']['low95'] > 0
        ens = t.loc['Nudge ensemble (thorough)']
        rows.append({'dataset': d, 'real effect (ATE range > 0)': real,
                     'ATE': r['ate_full']['ate'], 'ATE low95': r['ate_full']['low95'], 'ATE high95': r['ate_full']['high95'],
                     'engine Qini': e['qini'], 'low95': e['qini_low95'], 'high95': e['qini_high95'],
                     'B1 pass': (e['qini_low95'] > 0) if real else None,
                     'best method': best, 'best Qini': q.max(), 'engine / best': e['qini'] / q.max(),
                     'B2 within 10%': e['qini'] >= 0.9 * q.max(),
                     'ensemble / best (info)': ens['qini'] / q.max()})
    return pd.DataFrame(rows).set_index('dataset')
