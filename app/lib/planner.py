"""Plan my campaign: learn and choose on 80% of the file (honest out-of-fold scores), report on an untouched 20%.

Why two parts: if the same customers were used both to choose between the personalised and the simple plan and to report
the result, the report would flatter the winner (the 'winner's curse'). So:
    80% (build 64% + validation 16%)  the ranking learns here; every customer is scored by models that never saw them (5 folds,
                      lib/robust.py), and those honest scores choose between personalised plans (several safety margins) and the
                      best simple plan (everyone / nobody). The fast engine and the usual approach learn on the 64%.
    test (20%)        untouched until the end; every number shown is measured here

Units: with reminders only, the engine learns in the file's own outcome units (bought 1/0, or amount) and rupees are applied
afterwards, so margin and contact-cost changes re-plan instantly. When an option carries an offer cost (discount, cashback,
wallet credit, free item), that cost is paid by every buyer who got it, so the engine learns profit in ₹ after offer costs;
changing the margin or an offer then needs a rebuild.
"""
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

from lib.robust import RobustEngine
from lib.upload import MAX_ROWS
from nudge_engine import NudgeEngine, average_effects, evaluate_policies, policy_value, split_by_group

# cost of an offer per buyer who uses it, as a share of its face value
MARGINS = [0, 0.1, 0.25, 0.5, 1, 2]          # safety margins tried by the plan choice (x the best option's average effect)
OFFER_TYPES = {'Reminder (no offer)': None, 'Discount': 'every buyer gets the full face value',
               'Cashback': 'face value x share who redeem', 'Wallet credit': 'face value x share who use it',
               'Free item': 'face value x cost of goods share'}


def _desc(score, seed=0):
    """Positions from highest to lowest score; customers with the same score come in random order (not file order, which can be
    sorted by option and would bias every 'top x%' figure)."""
    score = np.asarray(score, float); p = np.random.default_rng(seed).permutation(len(score))
    return p[np.argsort(-score[p], kind='stable')]


def reward_per_buyer(offer: dict) -> float:
    """₹ an option costs for each buyer who got it (0 for a reminder)."""
    if not offer or offer['type'] == 'Reminder (no offer)':
        return 0.0
    rate = 1.0 if offer['type'] == 'Discount' else offer['rate']
    return offer['face'] * rate


def _usual_model(kind: str, n: int):
    """The usual approach (Step 5): predict who buys when contacted. Same settings, with the leaf size scaled down for small files."""
    p = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=int(min(400, max(20, n // 100))),
             subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0, verbose=-1, random_state=42)
    return lgb.LGBMClassifier(**p) if kind == 'binary' else lgb.LGBMRegressor(**p)


def train(prep: dict, value_per_unit: float, cost: float, offers: dict, status=None, ranker: str = 'ensemble') -> dict:
    """Fit everything once. status(text) reports progress to the page. ranker: 'ensemble' (default) or 'fast'."""
    say = status or (lambda s: None)
    d, feats, ctrl = prep['data'].copy(), prep['features'], prep['control']
    rewards = {o: reward_per_buyer(offers.get(o)) for o in prep['options']}
    has_reward = any(r > 0 for r in rewards.values())
    if has_reward:      # profit in ₹ after the offer cost paid by every buyer who got an offer
        d['_v'] = d._y * value_per_unit - d._option.map(rewards).fillna(0.0) * (d._y > 0)
    target, scale = ('_v', 1.0) if has_reward else ('_y', None)
    pool = d.sample(MAX_ROWS, random_state=7) if len(d) > MAX_ROWS else d
    tr, te = split_by_group(pool, '_id', test_size=0.2, seed=2026)     # one customer never sits in two parts
    build, val = split_by_group(tr, '_id', test_size=0.2, seed=2027)
    t0 = time.time()
    say(f'Training the Nudge engine on {len(build):,} customers (one uplift model per option)...')
    eng = NudgeEngine(feats, '_option', ctrl, target, option_cost={o: cost / (scale or value_per_unit) for o in prep['options']},
                      group='_id').fit(build)
    say('Training the usual approach (who is most likely to buy when contacted)...')
    contacted = build[build._option != ctrl]
    usual = _usual_model(prep['kind'], len(contacted)).fit(contacted[feats], contacted._y)
    pool80 = pd.concat([build, val])
    rob = RobustEngine(eng, ranker).fit(pool80, prep, target, say)
    return {'engine': rob, 'fast_engine': eng, 'usual': usual, 'build': build, 'val': val, 'pool': pool80, 'test': te, 'target': target,
            'fixed_scale': scale, 'rewards': rewards, 'has_reward': has_reward, 'secs': time.time() - t0, 'sampled': len(pool) < len(d),
            'ranker': rob.ranker, 'fallback_reason': rob.fallback_reason, 'folds': rob.folds}


def _scale(res, value_per_unit):
    return res['fixed_scale'] or value_per_unit


def test_policies(res: dict, prep: dict, P: dict) -> dict:
    """The four plans compared on the Plan page, as chosen for the untouched 20% (for the synthetic truth check)."""
    return _policies(res, prep, res['test'], P['best_opt'], P['margin'])


def _policies(res, prep, df, best_opt, margin=None):
    """Nudge plan, the usual approach with the same number of contacts, contact everyone, contact nobody.
    margin=None uses the engine's learned safety margin; 0 means fully personalised."""
    eng, ctrl = res['engine'], prep['control']
    rec = eng.recommend(df, margin_mult=margin).values; n = len(df); k = int(round(np.mean(rec != ctrl) * n))
    order = _desc(_score(res['usual'], df[prep['features']]))
    usual = np.array([ctrl] * n, dtype=object); usual[order[:k]] = best_opt
    return {'Nudge plan': rec, 'Usual approach': usual, f'Contact everyone ({best_opt})': [best_opt] * n, 'Contact nobody': [ctrl] * n}


def plan(res: dict, prep: dict, value_per_unit: float, cost: float, costs: dict = None) -> dict:
    """Everything the page shows. Chosen on the honest (out-of-fold) scores of the 80%, measured on the untouched 20%. No training
    here. costs: optional contact cost per option (₹); by default every option costs `cost`."""
    eng, te, ctrl, tg = res['engine'], res['test'], prep['control'], res['target']
    k = _scale(res, value_per_unit); oc = {o: (costs or {}).get(o, cost) / k for o in prep['options']}
    eng.with_costs(oc, res['build'])
    O = eng.oof_predict(); best_opt = O.drop(columns=ctrl).mean().idxmax()   # best single option, judged on the honest scores

    # 1. decide on the 80%: personalised plans (each safety margin) vs the best simple plan, valued on customers no model had seen
    pool = res['pool']; v = {}
    if eng.signal:
        for mlt in MARGINS:
            v[f'margin x{mlt}'] = policy_value(pool, '_option', tg, eng.recommend_oof(mlt), eng.prop, oc)
    v[f'Contact everyone ({best_opt})'] = policy_value(pool, '_option', tg, [best_opt] * len(pool), eng.prop, oc)
    v['Contact nobody'] = policy_value(pool, '_option', tg, [ctrl] * len(pool), eng.prop, oc)
    blanket = max([f'Contact everyone ({best_opt})', 'Contact nobody'], key=v.get)
    pers = {c: x for c, x in v.items() if c.startswith('margin')}
    margin = float(max(pers, key=pers.get).split('x')[1]) if pers else 0.0
    personalise = bool(pers) and max(pers.values()) > v[blanket]
    eng.margin_mult = margin
    signal_message = None if eng.signal else (
        'No reliable signal: on customers the model had not seen, its ranking did not beat a random order (the 95% range includes '
        'zero). So Nudge does not personalise and recommends the simple plan: '
        + ('contact nobody.' if blanket == 'Contact nobody' else f'contact everyone with {best_opt}.'))

    # 2. report on the untouched test part
    pol = _policies(res, prep, te, best_opt, margin)
    rec = pol['Nudge plan']; pred = eng.predict(te); gain = pred.max(axis=1).values * k
    share = float(np.mean(rec != ctrl)); n = len(te)
    vs_usual = evaluate_policies(te, '_option', tg, pol, eng.prop, oc, n_boot=200, baseline='Usual approach')
    vs_blanket = evaluate_policies(te, '_option', tg, pol, eng.prop, oc, n_boot=200, baseline=blanket)
    money = vs_usual[['value_per_customer', 'low95', 'high95']] * k
    money['extra_vs_nobody'] = money.value_per_customer - money.loc['Contact nobody', 'value_per_customer']
    # differences: the point value is the direct difference of the two measured values; the bootstrap only gives the 95% range
    row = lambda t, q, base: [(t.loc[q, 'value_per_customer'] - t.loc[base, 'value_per_customer']) * k,
                              t.loc[q, 'vs_low95'] * k, t.loc[q, 'vs_high95'] * k]
    recommended = 'Nudge plan' if personalise else blanket
    tiers = pd.qcut(pd.Series(gain).rank(method='first'), 3, labels=['Low', 'Medium', 'High']).values
    ladder = _ladder(te, tiers, ctrl, prep['kind'], value_per_unit)
    return {'pred': pred, 'rec': rec, 'gain': gain, 'share': share, 'best_opt': best_opt, 'n_test': n, 'n_choose': len(pool),
            'margin': margin, 'choice_values': {c: x * k for c, x in v.items()}, 'signal_message': signal_message,
            'signal': dict(eng.diag), 'ranker': res['ranker'], 'folds': res['folds'],
            'money': money, 'blanket': blanket, 'personalise': personalise, 'recommended': recommended,
            'diff': {'usual': row(vs_usual, 'Nudge plan', 'Usual approach'), 'blanket': row(vs_blanket, 'Nudge plan', blanket)},
            'vs_usual_all': {q: row(vs_usual, q, 'Usual approach') for q in pol if q != 'Usual approach'},
            'rec_share': share if personalise else (0.0 if blanket == 'Contact nobody' else 1.0),
            'engine_simple': len(set(rec)) == 1, 'tiers': tiers, 'ladder': ladder,
            'ladder_ok': bool(ladder.real_lift['High'] > ladder.real_lift['Medium'] > ladder.real_lift['Low']),   # fully in order
            'ladder_top': bool(ladder.real_lift['High'] > max(ladder.real_lift['Medium'], ladder.real_lift['Low'])),   # top third ahead
            'personas': _personas(te, tiers, rec, prep, ctrl, prep['kind'], value_per_unit),
            'effects': average_effects(prep['data'].assign(**({'_v': prep['data']._y * value_per_unit - prep['data']._option.map(res['rewards'])
                                                                .fillna(0.0) * (prep['data']._y > 0)} if res['has_reward'] else {})),
                                       '_option', ctrl, tg, oc) * [k, k, k, 1]}


def plan_order(res: dict, prep: dict, P: dict) -> tuple:
    """The order in which the plan would contact the untouched 20% as the budget grows, and the option each customer would get."""
    eng, te, ctrl = res['engine'], res['test'], prep['control']
    best_opt, rec, n = P['best_opt'], np.asarray(P['rec'], dtype=object), len(te)
    pred = eng.predict(te)                                             # the same contact cost for every option: order unaffected
    if P['personalise']:
        inplan = rec != ctrl
        own = pred.to_numpy()[np.arange(n), pred.columns.get_indexer(rec)]
        order = np.r_[np.flatnonzero(inplan)[_desc(own[inplan])], np.flatnonzero(~inplan)[_desc(pred[best_opt].values[~inplan])]]
        give = np.where(inplan, rec, best_opt)
    elif P['recommended'] == 'Contact nobody':                         # nothing pays: show Nudge's ranking of the best single option
        order = _desc(pred[best_opt].values); give = np.full(n, best_opt, dtype=object)
    else:
        order = np.random.default_rng(11).permutation(n); give = np.full(n, best_opt, dtype=object)
    return order, give


def true_ladder(res: dict, prep: dict, P: dict, true_lift: np.ndarray, value: float, channels: dict, base: float) -> pd.DataFrame:
    """Synthetic sample only: the TRUE profit of following the plan's order, per channel, using each customer's known true lift.
    true_lift is in the same row order as the untouched 20%."""
    order, give = plan_order(res, prep, P)
    gain = np.where(give[order] != prep['control'], true_lift[order], 0.0); n = len(order)
    rows = []
    for ch, cost in channels.items():
        cum = np.r_[0, np.cumsum(gain * value - cost)] / n * base          # true profit when contacting the first k customers
        k = int(np.argmax(cum))
        rows.append({'channel': ch, 'true best share': k / n, 'true profit at best': cum[k], 'true profit if contact all': cum[-1],
                     'true saved by targeting': cum[k] - cum[-1]})
    return pd.DataFrame(rows).set_index('channel')


def curves(res: dict, prep: dict, P: dict, status=None) -> pd.DataFrame:
    """Measured extra outcome (vs contacting nobody) when contacting the top share of the untouched 20%, for the plan chosen on the
    Plan page and for the usual approach, with paired 95% ranges (100 bootstrap repeats). The plan decides the order and who gets what:
        personalised plan: its customers first (best first), each with the option the plan gave them; then the others,
                           with the best single option
        simple plan:       Nudge's ranking was not trusted, so no ranking: customers in random order, all with the best single option
    In target units without contact costs, so the Money page can apply any margin and channel cost instantly:
        profit per customer = scale x extra - cost x share."""
    say = status or (lambda s: None)
    eng, te, ctrl, tg = res['engine'], res['test'], prep['control'], res['target']
    best_opt, n = P['best_opt'], len(te)
    order, give = plan_order(res, prep, P)
    likely = _score(res['usual'], te[prep['features']]); rows = []
    grid = np.r_[np.arange(0, 0.1, 0.01), np.arange(0.1, 1.0001, 0.05)]          # 1% steps up to 10% (small budgets), then 5%
    for j, s in enumerate(np.round(grid, 2)):
        say(f'Measuring profit when contacting {s:.0%} of customers...')
        k = int(round(s * n)); a = np.array([ctrl] * n, dtype=object); b = a.copy()
        a[order[:k]] = give[order[:k]]
        b[_desc(likely)[:k]] = best_opt
        # 100 bootstrap repeats per point (not 200) keeps 30 points on 40,000 customers to about 20 seconds
        r = evaluate_policies(te, '_option', tg, {'nudge': a, 'usual': b, 'nobody': [ctrl] * n}, eng.prop, n_boot=100,
                              baseline='nobody', seed=j)
        d = evaluate_policies(te, '_option', tg, {'nudge': a, 'usual': b}, eng.prop, n_boot=100, baseline='usual', seed=j)
        v = r.value_per_customer
        rows.append({'share': s, 'nudge': v['nudge'] - v['nobody'], 'nudge_low': r.loc['nudge', 'vs_low95'],
                     'nudge_high': r.loc['nudge', 'vs_high95'], 'usual': v['usual'] - v['nobody'],
                     'usual_low': r.loc['usual', 'vs_low95'], 'usual_high': r.loc['usual', 'vs_high95'],
                     'diff': v['nudge'] - v['usual'], 'diff_low': d.loc['nudge', 'vs_low95'], 'diff_high': d.loc['nudge', 'vs_high95']})
    out = pd.DataFrame(rows)
    out.loc[0, out.columns[1:]] = 0.0                                  # contacting nobody: exactly zero extra
    out.attrs['ranked'] = P['personalise'] or P['recommended'] == 'Contact nobody'
    return out


def _score(model, X):
    return model.predict_proba(X)[:, 1] if hasattr(model, 'predict_proba') else model.predict(X)


def _lift(g: pd.DataFrame, ctrl: str):
    t, c = g[g._option != ctrl]._y, g[g._option == ctrl]._y
    if len(t) < 2 or len(c) < 2:
        return np.nan, np.nan
    return t.mean() - c.mean(), np.sqrt(t.var() / len(t) + c.var() / len(c))


def _ladder(te, tiers, ctrl, kind, k) -> pd.DataFrame:
    """Real lift in buying (contacted vs held back) in each third of the untouched 20%, ranked by Nudge's prediction.
    If the model works, High > Medium > Low."""
    rows = []
    for t in ['High', 'Medium', 'Low']:
        lift, se = _lift(te[tiers == t], ctrl)
        f = 100 if kind == 'binary' else k                         # points of buying, or ₹ per customer
        rows.append({'group': t, 'real_lift': lift * f, 'low95': (lift - 1.96 * se) * f, 'high95': (lift + 1.96 * se) * f})
    return pd.DataFrame(rows).set_index('group')


def _dir(a, b) -> str:
    return 'higher than' if a > b else 'lower than' if a < b else 'the same as'


def _personas(te, tiers, rec, prep, ctrl, kind, k) -> dict:
    """What each third looks like: the 3 measures that set it apart most from the other customers."""
    out = {}
    for t in ['High', 'Medium', 'Low']:
        sel = tiers == t; g, rest = te[sel], te[~sel]
        lift, se = _lift(g, ctrl)
        traits = []
        for f in prep['features']:
            a, b = g[f].astype(float), rest[f].astype(float)
            s = np.sqrt((a.var() + b.var()) / 2)
            if s > 0 and a.notna().any():
                traits.append((abs(a.mean() - b.mean()) / s, f, a, b))
        traits.sort(key=lambda x: -x[0])
        words = []
        for _, f, a, b in [x for x in traits if x[0] >= 0.1][:3]:     # only measures that really differ (0.1+ standard deviations)
            col, val = prep['readable'][f]
            if val is not None:
                words.append(f'{col} = {val}: {a.mean():.0%}, {_dir(a.mean(), b.mean())} the others ({b.mean():.0%})')
            elif set(a.dropna().unique()) | set(b.dropna().unique()) <= {0, 1}:   # a yes/no measure: show the share
                words.append(f'{col}: {a.mean():.0%}, {_dir(a.mean(), b.mean())} the others ({b.mean():.0%})')
            elif a.median() != b.median():
                words.append(f'{col}: median {a.median():,.4g}, {_dir(a.median(), b.median())} the others ({b.median():,.4g})')
            else:                                                  # e.g. mostly zeros: the median hides the difference
                words.append(f'{col}: average {a.mean():,.3g}, {_dir(a.mean(), b.mean())} the others ({b.mean():,.3g})')
        if not words:
            words = ['no measure sets this group clearly apart']
        mix = pd.Series(rec[sel]).value_counts(normalize=True)
        out[t] = {'share': float(sel.mean()), 'lift': lift * (100 if kind == 'binary' else k),
                  'se': se * (100 if kind == 'binary' else k), 'traits': words,
                  'contacted': float(np.mean(rec[sel] != ctrl)), 'mix': mix}
    return out


def target_list(res: dict, prep: dict, value_per_unit: float, margin=None) -> pd.DataFrame:
    """Recommendation for every row of the file (also rows outside the training sample)."""
    eng, d, ctrl = res['engine'], prep['data'], prep['control']
    pred = eng.predict(d); rec = eng.recommend(d, margin_mult=margin).values
    gain = pred.to_numpy()[np.arange(len(d)), pred.columns.get_indexer(rec)] * _scale(res, value_per_unit)
    return pd.DataFrame({'customer_id': d._id, 'recommended_option': rec,
                         'predicted_extra_profit_rs': np.round(gain, 2), 'in_plan': np.where(rec != ctrl, 'yes', 'no')})
