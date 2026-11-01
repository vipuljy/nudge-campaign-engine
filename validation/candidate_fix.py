"""CANDIDATE fix for the Part A failures, tested in validation code only (the app is NOT changed).

Problem found: at 50k rows the planner decides between plans on a 16% validation slice (8,000 customers). That slice is too noisy:
the personalised plan really earns ~70% of the oracle profit but the slice preferred "contact everyone" (32%).
Candidate: decide with 5-fold cross-fitting on the whole 80% (build + validation): train the engine on 4 folds, value every
candidate plan (each safety margin, everyone, nobody) on the 5th, add up over the 5 folds; the plan with the highest total wins.
The final engine is then trained on the whole 80% and applied with the chosen setting. The untouched 20% stays untouched.
Optional `min_gain`: personalise only if the winning personalised plan beats the best simple plan by this share of a contact's cost
(a guard against picking noise on data with no real differences)."""
import numpy as np
import pandas as pd

import common  # noqa: F401
from nudge_engine import NudgeEngine, policy_value


def decide_cv(res, prep, value, contact, folds=5, seed=2028, min_gain=0.0):
    ctrl, tg, feats = prep['control'], res['target'], prep['features']
    k = res['fixed_scale'] or value
    oc = {o: contact[o] / k for o in prep['options']}
    pool = pd.concat([res['build'], res['val']])
    ids = pool['_id'].unique(); rng = np.random.default_rng(seed)
    fold_of = pd.Series(rng.permutation(len(ids)) % folds, index=ids)
    f = pool['_id'].map(fold_of).values
    grid = NudgeEngine.MARGIN_GRID[:-1]                                  # inf = the best single option = 'everyone'
    tot = {}
    for i in range(folds):
        tr, ho = pool[f != i], pool[f == i]
        eng = NudgeEngine(feats, '_option', ctrl, tg, option_cost=oc, group='_id', margin=0).fit(tr)
        best = eng.predict(tr).drop(columns=ctrl).mean().idxmax()
        cands = {f'margin x{m}': eng.recommend(ho, margin_mult=m).values for m in grid}
        cands['everyone'] = np.array([best] * len(ho), dtype=object); cands['nobody'] = np.array([ctrl] * len(ho), dtype=object)
        for c, p in cands.items():
            tot[c] = tot.get(c, 0.0) + policy_value(ho, '_option', tg, p, eng.prop, oc) * len(ho)
    vals = pd.Series(tot) / len(pool) * k                                 # ₹ per customer
    simple = vals[['everyone', 'nobody']].idxmax()
    pers = vals.drop(['everyone', 'nobody']).idxmax()
    personalise = vals[pers] > vals[simple] + min_gain * np.mean(list(contact.values()))
    final = NudgeEngine(feats, '_option', ctrl, tg, option_cost=oc, group='_id', margin=0).fit(pool)
    te = res['test']
    if personalise:
        rec = final.recommend(te, margin_mult=float(pers.split('x')[1])).values; recommended = f'Nudge plan ({pers})'
    else:
        best = final.predict(pool).drop(columns=ctrl).mean().idxmax()
        rec = np.array([best if simple == 'everyone' else ctrl] * len(te), dtype=object)
        recommended = f'Contact everyone ({best})' if simple == 'everyone' else 'Contact nobody'
    return {'rec': rec, 'personalise': bool(personalise), 'recommended': recommended, 'cv_values': vals.round(3).to_dict(),
            'engine': final}
