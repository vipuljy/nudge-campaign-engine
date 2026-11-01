"""Part A runner: each synthetic file goes through the app's own upload and planner code; the plan is then scored with the TRUTH
on the untouched 20% (the planner's own test part)."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import common  # noqa: F401  (puts app/ first on the import path)
from common import Timer, boot_range
from lib import planner, upload
from nudge_engine import policy_value
import synth

VALUE = {'binary': 150.0, 'revenue': 0.30}          # ₹ per extra purchase / margin share of extra revenue


def mapping(df, outcome):
    return {'option': 'option', 'control': synth.CONTROL, 'outcome': 'bought' if outcome == 'binary' else 'revenue',
            'id': 'customer_id', 'features': [f'x{i}' for i in range(10)] + ['region', 'joined_via'], 'labels': {}}


def decide(res, prep, value, contact):
    """The decision rule of planner.plan (cautious vs fully personalised vs best simple plan, chosen on the 16% validation part),
    with a contact cost PER OPTION (the app sets one cost for all options). Uses the planner's own _policies and the engine's
    policy_value; returns the plan for the untouched 20%."""
    eng, ctrl, tg = res['engine'], prep['control'], res['target']
    k = res['fixed_scale'] or value
    oc = {o: contact[o] / k for o in prep['options']}
    eng.with_costs(oc, res['build'])
    best_opt = eng.predict(res['build']).drop(columns=ctrl).mean().idxmax()
    val, v = res['val'], {}
    for name, m in [('cautious', None), ('personal', 0)]:
        v[name] = policy_value(val, '_option', tg, planner._policies(res, prep, val, best_opt, m)['Nudge plan'], eng.prop, oc)
    for name, p in list(planner._policies(res, prep, val, best_opt).items())[2:]:
        v[name] = policy_value(val, '_option', tg, p, eng.prop, oc)
    margin = None if v['cautious'] >= v['personal'] else 0
    blanket = max([f'Contact everyone ({best_opt})', 'Contact nobody'], key=v.get)
    personalise = max(v['cautious'], v['personal']) > v[blanket]
    pol = planner._policies(res, prep, res['test'], best_opt, margin)
    recommended = 'Nudge plan' if personalise else blanket
    return {'rec': np.asarray(pol[recommended], dtype=object), 'nudge_rec': np.asarray(pol['Nudge plan'], dtype=object),
            'personalise': personalise, 'recommended': recommended,
            'best_opt': best_opt, 'margin': margin, 'blanket': blanket, 'val_values': v}


def plan_profit_ratio(assign, P, ctrl):
    """True profit of an assignment and of the oracle, per customer, with a bootstrap range of their ratio."""
    Pm = P.to_numpy(); cols = list(P.columns)
    got = np.array([Pm[i, cols.index(a)] if a != ctrl else 0.0 for i, a in enumerate(assign)])
    orc = np.maximum(Pm.max(axis=1), 0.0)
    ratio = got.sum() / orc.sum()
    lo, hi = boot_range(lambda i: got[i].sum() / orc[i].sum(), len(got))
    return {'ratio': ratio, 'low95': lo, 'high95': hi, 'plan_per_customer': got.mean(), 'oracle_per_customer': orc.mean()}


def run_one(n, arms, outcome, seed, costs_2arm=(5.0, 1.02)):
    df, truth, opts = synth.make(n, arms, outcome, seed)
    m = mapping(df, outcome); value = VALUE[outcome]
    checks = upload.validate(df, m)
    prep = upload.prepare(df, m)
    offers = ({o: {'type': 'Discount', 'face': c['reward'], 'rate': 1.0} if c['reward'] else {'type': 'Reminder (no offer)'}
               for o, c in synth.OPTIONS_4.items()} if arms == 4 else {'Message': {'type': 'Reminder (no offer)'}})
    train_cost = costs_2arm[0] if arms == 2 else float(np.mean([c['contact'] for c in synth.OPTIONS_4.values()]))
    with Timer() as tt:
        res = planner.train(prep, value, train_cost, offers)
    te = res['test']; tr_te = truth.loc[te.index]
    out = {'n': n, 'arms': arms, 'outcome': outcome, 'seed': seed, 'train_secs': tt.secs, 'n_test': len(te),
           'fairness': upload.fairness(prep['max_gap'], prep['min_group'], prep['n_control'])[0],
           'warnings': [msg for lvl, msg in checks]}

    # A1: ranking. Predicted value per option vs its true effect in the engine's own units
    eff = synth.true_effect_engine_units(tr_te, opts, outcome, value, res['rewards'], res['has_reward'])
    pred = res['engine'].predict(te)
    rho = {}
    for o in opts:
        a, b = pred[o].to_numpy(), eff[o].to_numpy()
        lo, hi = boot_range(lambda i: spearmanr(a[i], b[i])[0], len(a))
        rho[o] = {'spearman': spearmanr(a, b)[0], 'low95': lo, 'high95': hi}
    A, B = pred[opts].to_numpy(), eff[opts].to_numpy()
    avg = lambda i: np.mean([spearmanr(A[i, j], B[i, j])[0] for j in range(len(opts))])
    lo, hi = boot_range(avg, len(A))
    out['A1'] = {'per_option': rho, 'spearman': avg(np.arange(len(A))), 'low95': lo, 'high95': hi}

    # A2: plan quality, true profit of the app's plan / oracle
    cost_sets = ({f'contact Rs{c:g}': {'Message': {'contact': c, 'reward': 0.0}} for c in costs_2arm} if arms == 2
                 else {'per-option costs': synth.OPTIONS_4})
    out['A2'] = {}
    for label, costs in cost_sets.items():
        P = synth.true_profit(tr_te, opts, outcome, value, costs)
        contact = {o: costs[o]['contact'] for o in opts}
        D = decide(res, prep, value, contact)
        r = plan_profit_ratio(D['rec'], P, prep['control'])
        everyone = plan_profit_ratio([P.mean().idxmax()] * len(P), P, prep['control'])        # best single option, chosen with truth
        row = {**r, 'personalise': D['personalise'], 'recommended': D['recommended'], 'margin': D['margin'],
               'share_contacted': float(np.mean(D['rec'] != prep['control'])),
               'mix': pd.Series(D['rec']).value_counts(normalize=True).round(3).to_dict(),
               'best_blanket_truth_ratio': everyone['ratio']}
        if arms == 2 and label != 'per-option costs':           # the replica must match planner.plan exactly (uniform cost)
            Pp = planner.plan(res, prep, value, contact['Message'])
            row['matches_planner_plan'] = bool((np.asarray(Pp['rec'], dtype=object) == D['nudge_rec']).all()
                                               and Pp['recommended'] == D['recommended'] and Pp['margin'] == D['margin'])
        out['A2'][label] = row
    out['judged_cost'] = 'contact Rs5' if arms == 2 else 'per-option costs'
    return out


def run_null(seed, n=50_000, cost=1.02):
    df, truth, opts = synth.make(n, 2, 'binary', seed, null=True)
    m = mapping(df, 'binary')
    prep = upload.prepare(df, m)
    res = planner.train(prep, 150.0, cost, {'Message': {'type': 'Reminder (no offer)'}})
    P = planner.plan(res, prep, 150.0, cost)
    return {'seed': seed, 'personalise': bool(P['personalise']), 'recommended': P['recommended'], 'rec_share': P['rec_share'],
            'val_values': P['val_values'], 'fairness': upload.fairness(prep['max_gap'], prep['min_group'], prep['n_control'])[0]}
