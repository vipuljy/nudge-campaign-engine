"""Diagnosis of the Part A failures (no app change): for a dataset, the TRUE profit share of the oracle earned by every plan the
planner could have picked (each safety margin, fully personalised, everyone, nobody), and what the validation slice preferred."""
import numpy as np
import pandas as pd

import common  # noqa: F401
from lib import planner, upload
from nudge_engine import NudgeEngine, policy_value
import part_a
import synth


def candidates(n, arms, outcome, seed, contact=None, null=False, engine_params=None, tau_leaf=None):
    df, truth, opts = synth.make(n, arms, outcome, seed, null=null)
    value = part_a.VALUE[outcome]; m = part_a.mapping(df, outcome)
    prep = upload.prepare(df, m)
    if arms == 4:
        costs = synth.OPTIONS_4
        offers = {o: {'type': 'Discount', 'face': c['reward'], 'rate': 1.0} if c['reward'] else {'type': 'Reminder (no offer)'}
                  for o, c in costs.items()}
        train_cost = float(np.mean([c['contact'] for c in costs.values()]))
    else:
        c = 5.0 if contact is None else contact
        costs = {'Message': {'contact': c, 'reward': 0.0}}; offers = {'Message': {'type': 'Reminder (no offer)'}}; train_cost = c
    res = planner.train(prep, value, train_cost, offers)
    if engine_params is not None or tau_leaf is not None:           # candidate engine settings, same splits
        res['engine'] = _Engine(prep['features'], '_option', prep['control'], res['target'],
                                option_cost=res['engine'].option_cost, group='_id', model_params=engine_params or {},
                                tau_leaf=tau_leaf).fit(res['build'])
    te = res['test']; P = synth.true_profit(truth.loc[te.index], opts, outcome, value, costs)
    eng = res['engine']; k = res['fixed_scale'] or value
    oc = {o: costs[o]['contact'] / k for o in opts}; eng.with_costs(oc, res['build'])
    best_opt = eng.predict(res['build']).drop(columns=prep['control']).mean().idxmax()
    rows = []
    for mm in NudgeEngine.MARGIN_GRID:
        r_te = eng.recommend(te, margin_mult=mm).values; r_va = eng.recommend(res['val'], margin_mult=mm).values
        rows.append({'plan': f'margin x{mm}', 'truth_ratio': part_a.plan_profit_ratio(r_te, P, prep['control'])['ratio'],
                     'val_value': policy_value(res['val'], '_option', res['target'], r_va, eng.prop, oc) * k,
                     'share': float(np.mean(r_te != prep['control']))})
    for name, a in [(f'everyone ({best_opt})', best_opt), ('nobody', prep['control'])]:
        rows.append({'plan': name, 'truth_ratio': part_a.plan_profit_ratio([a] * len(te), P, prep['control'])['ratio'],
                     'val_value': policy_value(res['val'], '_option', res['target'], [a] * len(res['val']), eng.prop, oc) * k,
                     'share': float(a != prep['control'])})
    out = pd.DataFrame(rows).set_index('plan')
    out.attrs['learned_margin'] = eng.margin_mult if hasattr(eng, 'margin_mult') else None
    D = part_a.decide(res, prep, value, {o: costs[o]['contact'] for o in opts})
    out.attrs['chosen'] = D['recommended'] + ('' if not D['personalise'] else f" (margin {'learned' if D['margin'] is None else 0})")
    pred = eng.predict(te)
    from scipy.stats import spearmanr
    eff = synth.true_effect_engine_units(truth.loc[te.index], opts, outcome, value, res['rewards'], res['has_reward'])
    out.attrs['spearman'] = float(np.mean([spearmanr(pred[o], eff[o])[0] for o in opts])) if not null else None
    return out


class _Engine(NudgeEngine):
    """Candidate: the same engine with a different leaf size for the final uplift model (the app fixes it at 600)."""
    def __init__(self, *a, tau_leaf=None, **kw):
        super().__init__(*a, **kw); self.tau_leaf = tau_leaf

    def fit(self, df):
        if self.margin == 'auto':
            return super().fit(df)
        return self._fit(df)

    def _fit(self, df):
        if self.tau_leaf is None:
            return super()._fit(df)
        import nudge_engine as ne
        orig = ne._reg
        leaf = self.tau_leaf
        def reg(**kw):
            if kw.get('min_child_samples') == 600:
                kw['min_child_samples'] = leaf
            return orig(**kw)
        ne._reg = reg
        try:
            return super()._fit(df)
        finally:
            ne._reg = orig
