"""Fair before/after test of the candidate fix (validation code only; the app is NOT changed).

For every file the planner is trained ONCE (same 64/16/20 split); then both decision rules are applied to the same customers:
    current : the app's rule (planner.plan's decision on the 16% validation slice; replica verified identical to planner.plan)
    fix     : candidate_fix.decide_cv (5-fold cross-fitted decision on the 80%, final engine trained on the 80%)
Both are scored on the same untouched 20%: with the TRUTH where it is known (synthetic files), and always with measured values
(the app's own policy scoring, paired bootstrap 95% ranges), plus the ranking's Qini per option (random tie-break)."""
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklift.metrics import qini_auc_score

import common
from lib import planner, thorough, upload
from nudge_engine import evaluate_policies
import candidate_fix
import part_a
import run_part_a
import synth

FRESH = 7000                          # fresh seeds = original seed + 7000 (never used before); fresh null seeds 7101..7120


def kind_of(rec_name):
    return 'nobody' if rec_name == 'Contact nobody' else 'everyone' if rec_name.startswith('Contact everyone') else 'personalised'


def _qini(te, prep, eng):
    """Average over options of sklift's Qini (option vs control) on the untouched 20%, ties broken at random."""
    ctrl = prep['control']; pred = eng.predict(te); qs = []
    perm = np.random.default_rng(2027).permutation(len(te))
    for o in prep['options']:
        s = (te._option.values == o) | (te._option.values == ctrl); idx = perm[s[perm]]
        y, u, t = te._y.values[idx], pred[o].values[idx], (te._option.values[idx] == o).astype(int)
        # sklift's Qini needs a yes/no outcome; for amounts the app's own Qini area (thorough.qini) is used
        qs.append(qini_auc_score(y, u, t) if prep['kind'] == 'binary' else thorough.qini(y.astype(float), t, u))
    return float(np.mean(qs))


def both_rules(prep, value, contact, offers, train_cost):
    res = planner.train(prep, value, train_cost, offers)
    t0 = time.time(); C = part_a.decide(res, prep, value, contact); tc = time.time() - t0
    t0 = time.time(); F = candidate_fix.decide_cv(res, prep, value, contact); tf = time.time() - t0
    rules = {'current': {'rec': C['rec'], 'recommended': C['recommended'], 'engine': res['engine'], 'decide_s': tc},
             'fix': {'rec': F['rec'], 'recommended': F['recommended'], 'engine': F['engine'], 'decide_s': tf}}
    # measured (not truth) on the untouched 20%: extra profit per customer vs contacting nobody, and fix minus current
    te, ctrl, tg = res['test'], prep['control'], res['target']; k = res['fixed_scale'] or value
    oc = {o: contact[o] / k for o in prep['options']}; prop = res['engine'].prop; n = len(te)
    for r in rules.values():
        e = evaluate_policies(te, '_option', tg, {'plan': r['rec'], 'nobody': [ctrl] * n}, prop, oc, n_boot=200, baseline='nobody')
        r['measured_extra_per_customer'] = [(e.loc['plan', 'value_per_customer'] - e.loc['nobody', 'value_per_customer']) * k,
                                            e.loc['plan', 'vs_low95'] * k, e.loc['plan', 'vs_high95'] * k]
        r['share_contacted'] = float(np.mean(np.asarray(r['rec']) != ctrl)); r['kind'] = kind_of(r['recommended'])
        r['qini'] = _qini(te, prep, r['engine'])
    d = evaluate_policies(te, '_option', tg, {'fix': rules['fix']['rec'], 'current': rules['current']['rec']}, prop, oc,
                          n_boot=200, baseline='current')
    diff = [(d.loc['fix', 'value_per_customer'] - d.loc['current', 'value_per_customer']) * k, d.loc['fix', 'vs_low95'] * k,
            d.loc['fix', 'vs_high95'] * k]
    return res, rules, diff


def synth_file(n, arms, outcome, seed, null=False):
    df, truth, opts = synth.make(n, arms, outcome, seed, null=null)
    value = part_a.VALUE[outcome]; prep = upload.prepare(df, part_a.mapping(df, outcome))
    if arms == 4:
        costs = synth.OPTIONS_4
        offers = {o: {'type': 'Discount', 'face': c['reward'], 'rate': 1.0} if c['reward'] else {'type': 'Reminder (no offer)'}
                  for o, c in costs.items()}
    else:
        c = 1.02 if null else 5.0                                   # A3 is defined at ₹1.02; A2 2-arm is judged at ₹5
        costs = {'Message': {'contact': c, 'reward': 0.0}}; offers = {'Message': {'type': 'Reminder (no offer)'}}
    contact = {o: costs[o]['contact'] for o in opts}
    res, rules, diff = both_rules(prep, value, contact, offers, float(np.mean(list(contact.values()))))
    te = res['test']; tt = truth.loc[te.index]
    out = {'n': n, 'arms': arms, 'outcome': outcome, 'seed': seed, 'null': null, 'measured_fix_minus_current': diff}
    P = synth.true_profit(tt, opts, outcome, value, costs)
    eff = synth.true_effect_engine_units(tt, opts, outcome, value, res['rewards'], res['has_reward'])
    for name, r in rules.items():
        row = {k: r[k] for k in ('recommended', 'kind', 'share_contacted', 'measured_extra_per_customer', 'qini', 'decide_s')}
        if null:
            Pm = P.to_numpy(); cols = list(P.columns)
            row['true_profit_per_customer'] = float(np.mean([Pm[i, cols.index(a)] if a != prep['control'] else 0.0
                                                             for i, a in enumerate(r['rec'])]))
        else:
            row['A2'] = part_a.plan_profit_ratio(r['rec'], P, prep['control'])
            pred = r['engine'].predict(te); A, B = pred[opts].to_numpy(), eff[opts].to_numpy()
            avg = lambda i: np.mean([spearmanr(A[i, j], B[i, j])[0] for j in range(len(opts))])
            lo, hi = common.boot_range(avg, len(A))
            row['A1'] = {'spearman': avg(np.arange(len(A))), 'low95': lo, 'high95': hi}
        out[name] = row
    return out


def run_seeds(label, offset, null_seeds, log=print):
    """All 12 Part A files and a 20-run null test, both rules. label: 'original' (offset 0) or 'fresh' (offset 7000)."""
    for n in run_part_a.SIZES:
        for arms in (2, 4):
            for outcome in ('binary', 'revenue'):
                name = f'F_{label}_{n}_{arms}arm_{outcome}'
                if common.load(name):
                    continue
                r = synth_file(n, arms, outcome, run_part_a.seed_of(n, arms, outcome) + offset); common.save(name, r)
                log(f"{name}: current {r['current']['A2']['ratio']:.3f} ({r['current']['kind']}) -> fix {r['fix']['A2']['ratio']:.3f} "
                    f"({r['fix']['kind']}); spearman {r['current']['A1']['spearman']:.3f} -> {r['fix']['A1']['spearman']:.3f}")
    name = f'F_{label}_null'; N = common.load(name) or {'runs': []}
    for s in null_seeds:
        if s in {x['seed'] for x in N['runs']}:
            continue
        r = synth_file(50_000, 2, 'binary', s, null=True); N['runs'].append(r); common.save(name, N)
        log(f"{name} seed {s}: current {r['current']['kind']} -> fix {r['fix']['kind']}")


def app_sample(key, log=print):
    """The app's built-in samples through the same comparison (page defaults: synthetic = AI call ₹5, ₹150 per purchase;
    Hillstrom = e-mail ₹0.01, 15% margin x ₹95 per $)."""
    S = upload.SAMPLES[key]; df = pd.read_csv(upload.SAMPLES_DIR / S['file'])
    m = {**S['mapping'], 'labels': S['mapping'].get('labels', {})}
    prep = upload.prepare(df, m)
    value, cost = (150.0, S['custom_cost']) if key == 'synthetic' else (0.15 * S['per_unit'], 0.01)
    contact = {o: cost for o in prep['options']}
    res, rules, diff = both_rules(prep, value, contact, {o: {'type': 'Reminder (no offer)'} for o in prep['options']}, cost)
    out = {'sample': key, 'value_per_unit': value, 'cost': cost, 'measured_fix_minus_current': diff}
    if key == 'synthetic':
        te = res['test']; tl = te[['_id']].merge(pd.read_csv(upload.SAMPLES_DIR / S['truth']), left_on='_id', right_on='customer_id',
                                                 how='left').true_lift.values
        orc = np.maximum(tl * value - cost, 0).sum()
    for name, r in rules.items():
        row = {k: r[k] for k in ('recommended', 'kind', 'share_contacted', 'measured_extra_per_customer', 'qini', 'decide_s')}
        if key == 'synthetic':
            got = ((np.asarray(r['rec']) != prep['control']) * (tl * value - cost))
            row['true_profit_per_1000'] = float(got.sum() / len(tl) * 1000); row['true_share_of_oracle'] = float(got.sum() / orc)
            row['true_spearman'] = float(spearmanr(r['engine'].predict(te)['Message'], tl)[0])
        out[name] = row
    common.save(f'F_sample_{key}', out); log(f"sample {key}: {out['current']['recommended']} -> {out['fix']['recommended']}")
    return out


def benchmark_planner(name, log=print):
    """Part B's Hillstrom and MegaFon through the app's planner path (whole file uploaded; ₹150 per visit/conversion, ₹1.02 per
    contact as in Part B). Part B's own engine Qini cannot change (the engine code is untouched); this checks the plan path."""
    import part_b
    X, y, t, desc = part_b.load(name)
    raw = X.assign(_arm=np.where(t == 1, 'treat', 'control'), _out=y)
    m = {'option': '_arm', 'control': 'control', 'outcome': '_out', 'id': None, 'features': list(X.columns), 'labels': {}}
    prep = upload.prepare(raw, m); del raw, X
    res, rules, diff = both_rules(prep, 150.0, {'treat': 1.02}, {'treat': {'type': 'Reminder (no offer)'}}, 1.02)
    out = {'dataset': name, 'measured_fix_minus_current': diff,
           **{k: {x: r[x] for x in ('recommended', 'kind', 'share_contacted', 'measured_extra_per_customer', 'qini', 'decide_s')}
              for k, r in rules.items()}}
    common.save(f'F_bench_{name}', out); log(f"benchmark {name}: qini {out['current']['qini']:.4f} -> {out['fix']['qini']:.4f}")
    return out
