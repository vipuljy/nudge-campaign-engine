"""Money: how many to contact, what to spend, what comes back in rupees.
Two modes: the X5 example (pre-computed, opens instantly) and your data (from the Plan page). Every profit is measured on
customers the model never saw; every business input is an assumption you can change."""
import numpy as np
import pandas as pd
import streamlit as st

from lib import analyst, charts, fmt, money, planner, ui, upload, x5
from nudge_engine import breakeven_uplift

A = x5.meta()['assumptions']
CH = {k: v['value'] for k, v in A['channels_rs_per_contact'].items()}
CH_SRC = {k: v['source'] for k, v in A['channels_rs_per_contact'].items()}
ss = st.session_state
plus = lambda v: ('+' if v >= 0 else '') + fmt.rs(v)

st.title('Money')
st.caption('How many to contact, what to spend, and what comes back in rupees: measured on a random test, priced with assumptions you control.')

has_plan = 'plan' in ss and 'current' in ss['plan']
mode = st.segmented_control('Results from', ['X5 example', 'Your data'], default='Your data' if has_plan else 'X5 example',
                            key='money_mode') or 'X5 example'
if mode == 'Your data' and not has_plan:
    st.info('Build a plan first: upload your test (or try a sample) on the Plan page, then come back here.', icon=':material/info:')
    st.page_link('views/plan.py', label='Go to Plan my campaign', icon=':material/upload_file:')
    st.stop()
X5_MODE = mode == 'X5 example'
RANKED = True

# ---------------- inputs ----------------
left, right = st.columns([1, 2.3], gap='large')
with left:
    with st.container(border=True):
        st.markdown(f'**Your assumptions** {ui.tag("assumed")}', unsafe_allow_html=True)
        if X5_MODE:
            basket = st.number_input('Average basket (₹)', 100, 100_000, int(A['basket_rs']['value']), 100)
            gm = st.number_input('Gross margin (%)', 1.0, 100.0, 100 * A['gross_margin']['value'], 1.0)
            k = basket * gm / 100
            st.caption(f'= **₹{k:,.0f} profit per extra purchase**')
            default_chan = 'WhatsApp'
        else:
            cur, res = ss['plan']['current'], ss['plan']['res']
            if res['has_reward']:
                k = cur['value']
                st.markdown(f"Profit per extra unit: **₹{k:,.2f}**")
                st.caption('Fixed at the value used to build the plan (offer costs are built in). Change it on the Plan page and rebuild.')
            else:
                k = st.number_input('Profit per extra purchase (₹)' if ss['plan']['prep']['kind'] == 'binary' else 'Profit per extra unit (₹)',
                                    0.01, 100_000.0, float(cur['value']), help='Starts from the Plan page.')
            default_chan = cur['channel'] if cur['channel'] in CH else 'Custom'
        chans = list(CH) + ['Custom']
        chan = st.selectbox('Channel', chans, index=chans.index(default_chan))
        cost = (st.number_input('Custom ₹ per contact', 0.0, 1000.0, float(ss['plan']['current']['cost']) if not X5_MODE else 1.0)
                if chan == 'Custom' else CH[chan])
        budget = st.number_input('Budget (₹)', 0, 100_000_000, 20_000, 5_000)
        base = st.number_input('Customers in your base', 1_000, 100_000_000,
                               100_000 if X5_MODE else int(round(len(ss['plan']['prep']['data']), -3)), 10_000)
        with st.popover('Where do these numbers come from?', icon=':material/info:'):
            st.markdown('\n'.join([f"- **Basket and margin:** {A['basket_rs']['source']}; {A['gross_margin']['source']}"] +
                                  [f'- **{c}, ₹{CH[c]}:** {CH_SRC[c]}' for c in CH]))

# ---------------- curves ----------------
if X5_MODE:
    C = money.x5_curves(k, cost, base)                                   # 1% steps
    C5 = {m: money.every(c, 0.05) for m, c in C.items()}                 # 5% steps, as Step 8's profit curve
    bd = x5.budget_difference(k, cost, budget, base=base)
    a, b, diff, dlo, dhi = bd['a'], bd['b'], bd['difference'], bd['low95'], bd['high95']
    nudge5 = C5['uplift']; source = 'X5 RetailHero, locked 40,008 customers (Russia; rupee values illustrative)'
else:
    res, prep, cur = ss['plan']['res'], ss['plan']['prep'], ss['plan']['current']
    store = ss['plan'].setdefault('curves', {}); ckey = (cur['value'], cur['cost'])    # the plan exactly as chosen on the Plan page
    if ckey not in store:
        with st.status('Measuring profit at every share contacted on your untouched 20%...', expanded=True) as box:
            store[ckey] = planner.curves(res, prep, cur['P'], status=box.write)
            box.update(label='Profit curves ready', state='complete', expanded=False)
        st.rerun()                                                    # redraw without the progress box
    Cu = store[ckey]; scale = res['fixed_scale'] or k; RANKED = Cu.attrs.get('ranked', True)
    C5 = money.user_curves(Cu, scale, cost, base)
    if not RANKED:
        C5 = {'plan': C5['nudge'], 'usual': C5['usual']}              # no ranking: the plan already is a random pick
    a, b = money.within_budget(C5['nudge' if RANKED else 'plan'], cost, budget), money.within_budget(C5['usual'], cost, budget)
    diff, dlo, dhi = money.user_difference(Cu, a, b, scale, cost, base)
    nudge5 = C5['nudge' if RANKED else 'plan']; source = f"{ss['plan']['source']}, untouched 20% ({fmt.count(len(res['test']))} customers)"
    P = cur['P']
    plan_txt = (f"Your plan from the Plan page: {'personalised' if P['personalise'] else P['recommended']}"
                f" (chosen at {fmt.cost(cur['cost'])} per contact). Who gets what stays as chosen there; changing the channel here only re-prices it.")
    if not RANKED:
        plan_txt += (' Nudge could not rank your customers reliably, so the plan has no ranking: with a smaller budget it picks customers '
                     'at random.')
best5, everyone = money.best(nudge5), nudge5.iloc[-1]
r100 = lambda v: round(v, -2) if abs(v) >= 1000 else v                # budget profits to the nearest ₹100, as Step 8's table
chan_label = chan if chan != 'Custom' else f'contacts at {fmt.cost(cost)}'
max_contacts = budget / cost if cost > 0 else np.inf
budget_share = min(1.0, max_contacts / base)

# ---------------- 1. the budget plan ----------------
with right:
    st.subheader(f'Your {fmt.rs(budget)} budget on {chan_label}')
    ratio = r100(a.profit) / r100(b.profit) if b.profit > 0 else None
    usual_curve = C['likely'] if X5_MODE else C5['usual']             # the usual list contacting as many customers as the Nudge plan
    same = usual_curve.loc[(usual_curve.share - a.share).abs().idxmin()]
    rng = f'range {fmt.rs(dlo)} to {fmt.rs(dhi)}' if not np.isnan(dlo) else 'range shown when both plans contact the same number'
    ui.kpi_grid([
        {'label': 'Contacts in the plan', 'value': fmt.count(round(a.contacts, -2) if a.contacts >= 1000 else a.contacts),
         'note': f"of {fmt.count(base)} customers, {'best first by Nudge' if RANKED else 'picked at random'}",
         'source': f'budget allows up to {fmt.count(min(max_contacts, base))}'},
        {'label': 'Nudge profit' if RANKED else 'Your plan', 'value': fmt.rs(r100(a.profit)), 'note': 'extra profit after contact costs',
         'source': f'range {fmt.rs(a.low95)} to {fmt.rs(a.high95)}' if not np.isnan(a.low95) else '', 'tags': ('measured', 'assumed')},
        {'label': 'Usual approach', 'value': fmt.rs(r100(b.profit)),
         'note': (f'same budget, likely buyers first ({fmt.count(round(b.contacts, -2) if b.contacts >= 1000 else b.contacts)} contacts)'
                  + (f"; spending it on the same {fmt.count(round(a.contacts, -2) if a.contacts >= 1000 else a.contacts)} contacts: "
                     f"{fmt.rs(r100(same.profit))}" if b.contacts < a.contacts else '')),
         'source': 'what most CRM teams do today', 'tags': ('measured', 'assumed')},
        ({'label': 'Nudge gains', 'value': plus(r100(diff)), 'note': 'more profit from the same budget', 'source': rng, 'tags': ('measured',),
          'badge': f'≈{ratio:.0f}× more profit' if ratio and ratio >= 2 else ''} if diff >= 0 else
         {'label': 'Nudge is behind', 'value': fmt.rs(r100(-diff)), 'note': 'less profit than the usual approach here', 'source': rng,
          'tags': ('measured',)}),
    ])
    first_step = nudge5.share[nudge5.share > 0].min() * base
    if max_contacts < 1:
        ui.decision(f'<b>This budget does not cover a single contact</b> at {fmt.cost(cost)}. Raise the budget or pick a cheaper channel.')
    elif a.contacts == 0 and max_contacts < first_step:
        ui.decision(f'<b>This budget covers {fmt.count(max_contacts)} contacts</b>, fewer than the smallest measured group '
                    f'({fmt.count(first_step)} customers, {first_step / base:.0%}). Raise the budget to at least {fmt.rs(first_step * cost)} to see a measured plan.')
    elif a.profit <= 0:
        ui.decision(f'<b>Do not spend this budget on {chan_label}.</b> At {fmt.cost(cost)} per contact and ₹{k:,.0f} profit per extra purchase, '
                    'no group of customers earns back its contact cost. Try a cheaper channel.')
    else:
        spare = best5.share * base * cost < budget and best5.share < budget_share
        who = 'all' if a.share >= 1 else ('ranked by Nudge' if RANKED else 'picked at random')
        ui.decision(f'With {fmt.rs(budget)} on {chan_label}, contact <b>{fmt.count(round(a.contacts, -2) if a.contacts >= 1000 else a.contacts)}</b> '
                    f'of {fmt.count(base)} customers{"" if who == "all" else " " + who}{" (all of them)" if who == "all" else ""}: '
                    f'<b>{fmt.rs(r100(a.profit))}</b> extra profit. '
                    + (f'The usual likely-buyer list cannot make money with this budget: its best choice is to contact nobody, and spending '
                       f'the budget on the same {fmt.count(round(a.contacts, -2) if a.contacts >= 1000 else a.contacts)} contacts it would make '
                       f'{fmt.rs(r100(same.profit))}.' if b.contacts == 0 else f'The usual likely-buyer list would make {fmt.rs(r100(b.profit))}.')
                    + ((f' <b>Here the usual list does better, by {fmt.rs(r100(-diff))}</b>'
                        + (': Nudge could not rank your customers reliably, so with a limited budget the likely-buyer list is the better pick.'
                           if not RANKED else
                           (f', but that is within the measured range ({fmt.rs(dlo)} to {fmt.rs(dhi)}), so treat the two as equal.'
                            if not np.isnan(dlo) and dlo < 0 < dhi else '.'))) if diff < -1 else '')
                    + (f' You do not need the whole budget: the most profitable plan contacts {best5.share:.0%} and costs '
                       f'{fmt.rs(best5.share * base * cost)}.' if spare else ''))
    st.caption(f'Measured on: {source}.' + ('' if X5_MODE else ' ' + plan_txt))

# ---------------- 2. without a budget limit ----------------
st.subheader('Without a budget limit')
ui.kpi_grid([
    {'label': 'Best share to contact', 'value': f'{best5.share:.0%}', 'note': f'{fmt.count(best5.contacts)} customers, best first',
     'source': 'in 5% steps' if X5_MODE else 'in 1% steps up to 10%, then 5%'},
    {'label': 'Profit at best share', 'value': fmt.rs(best5.profit), 'note': f'{chan_label} at {fmt.cost(cost)} per contact',
     'source': f'range {fmt.rs(best5.low95)} to {fmt.rs(best5.high95)}', 'tags': ('measured', 'assumed')},
    {'label': 'vs contacting everyone', 'value': plus(best5.profit - everyone.profit), 'note': 'saved by not contacting the rest',
     'source': f'everyone: {fmt.rs(everyone.profit)}', 'tags': ('measured',)},
    {'label': 'Contact spend avoided', 'value': fmt.rs((everyone.contacts - best5.contacts) * cost),
     'note': f'{fmt.count(everyone.contacts - best5.contacts)} contacts not sent', 'source': ''},
])
peak = max(abs(c.profit).max() for c in C5.values())
sc, unit = (1e5, '₹ lakh') if peak >= 1e5 else (1e3, '₹ thousand')
charts.show(charts.profit_curves(C5, best5.share, budget_share, sc, unit), width='stretch')
st.caption('Shaded bands: 95% ranges. A curve that rises and then falls means the last customers cost more to contact than they bring.')

with st.expander('How was this calculated?'):
    st.markdown(f"""
- **Measured, not predicted:** for each share contacted (best first), extra buyers = (buy rate of those contacted − buy rate of
  randomly held-back look-alikes) × group size, on customers the model never saw. Profit = extra buyers × ₹{k:,.0f} − contacts × {fmt.cost(cost)}.
- **Rankings:** Nudge ranks by predicted *extra* buying (uplift); the usual approach ranks by chance of buying when contacted (Step 5);
  random is the baseline.
- **Steps:** {'the profit curve and best share use 5% steps; the budget plan and the stress test use 1% steps, as in Step 8' if X5_MODE else 'measured every 1% up to 10% of customers, then every 5%'}.
- **Ranges:** {'200 bootstrap repeats (Step 8); the budget difference uses 300 paired repeats (same resampled customers for both lists)' if X5_MODE
              else '200 paired bootstrap repeats on your untouched 20%'}.
- **Scale:** results are for {fmt.count(base)} customers; contacts and profit grow in proportion.
""" + ('- **Offers are not added to the X5 curves:** X5 tested a plain SMS, so the extra buying an offer would cause is unknown. '
       'Use the Offers and Break-even tabs.' if X5_MODE else ''))

# ---------------- tabs ----------------
t1, t2, t3, t4 = st.tabs(['Channel ladder', 'Stress test', 'Offers', 'Break-even'])

with t1:
    lad = money.x5_ladder(k, CH, base) if X5_MODE else money.user_ladder(Cu, scale, CH, base)
    st.markdown('**Which channel, and how many to contact?** The pricier the contact, the more it pays to skip customers who would buy anyway.')
    charts.show(charts.grouped_bars(list(lad.index), {'Best plan (Nudge)': lad['profit at best'] / sc, 'Contact everyone': lad['profit if contact all'] / sc},
                                        unit, 'Profit by channel', colors={'Contact everyone': ui.COLORS['usual']}), width='stretch')
    show = lad.copy()
    show['best share'] = show['best share'].map('{:.0%}'.format)
    for c in ['profit at best', 'profit if contact all', 'saved by targeting', 'contact spend avoided']:
        show[c] = show[c].map(fmt.rs)
    TRUTH = None
    if not X5_MODE and upload.SAMPLES.get(ss['plan'].get('sample'), {}).get('truth'):
        tr = res['test'][['_id']].merge(upload.load_truth(ss['plan']['sample']), left_on='_id', right_on='customer_id', how='left')
        TRUTH = planner.true_ladder(res, prep, ss['plan']['current']['P'], tr.true_lift.values, k, CH, base)
    show['₹ per contact'] = show['₹ per contact'].map(fmt.cost)
    st.dataframe(show, width='stretch')
    if TRUTH is not None:
        st.markdown('**True result, known only here** (each customer\'s true response, following the plan\'s order):')
        st.table(pd.DataFrame({'true best share': TRUTH['true best share'].map('{:.0%}'.format),
                               'true profit at best': TRUTH['true profit at best'].map(fmt.rs),
                               'true saved by targeting': TRUTH['true saved by targeting'].map(fmt.rs)}))
        st.info('**Synthetic sample: read the true result.** The measured table comes from the untouched 20%, which is noisy on this '
                'sample: there the message happened to measure about +4.6 pts against a true +3.4 pts, which makes contacting everyone '
                'look better than it is. The true result uses each customer\'s known true response (possible only because the data are '
                'made up) and agree with the Plan page: targeting pays once contacts cost a few rupees.', icon=':material/science:')

with t2:
    stress, plan_share = money.x5_stress(k, cost, base) if X5_MODE else money.user_stress(Cu, scale, cost, base, res['has_reward'])
    st.markdown(f'**What if the assumptions are wrong?** The plan (contact the top {plan_share:.0%} via {chan_label}) is kept fixed while '
                'each assumption gets worse; then the optimiser is re-run with the bad numbers.')
    charts.show(charts.grouped_bars(list(stress.index), {'Old plan': stress['old plan'] / sc, 'Re-optimised plan': stress['re-optimised plan'] / sc,
                                                             'Contact everyone': stress['contact everyone'] / sc}, unit, 'Stress test'), width='stretch')
    s2 = stress.copy(); s2['re-optimised share'] = s2['re-optimised share'].map('{:.0%}'.format)
    for c in ['old plan', 'contact everyone', 're-optimised plan']:
        s2[c] = s2[c].map(fmt.rs)
    st.dataframe(s2, width='stretch')
    ok_re = (stress['re-optimised plan'] > 0).all(); ok_old = (stress['old plan'] >= stress['contact everyone'] - 1e-6).all()
    worst = stress.iloc[-1]
    st.markdown(f"- {'✅' if ok_re else '⚠️'} Re-running the optimiser {'keeps the plan profitable in every scenario' if ok_re else 'cannot keep every scenario profitable'}"
                f" (all three at once: contact {worst['re-optimised share']:.0%}, {fmt.rs(worst['re-optimised plan'])}).\n"
                f"- {'✅' if ok_old else '⚠️'} The old plan {'never does worse than contacting everyone' if ok_old else 'can do worse than contacting everyone'}.")
    if not X5_MODE and res['has_reward']:
        st.caption('Margin scenarios are left out: with offers, the margin is built into the plan. Change it on the Plan page and rebuild.')

with t3:
    st.markdown('**Which offer?** The offer that lifts buying most is not the one that earns most, because every buyer gets the reward, '
                'including those who would have bought anyway.')
    eco = x5.table('step8_offer_economics').set_index('offer'); lift = x5.table('step6_starbucks_offer_types').set_index('offer_type')
    names = {'informational': 'Reminder', 'discount': 'Discount', 'bogo': 'Free item (BOGO)'}
    fig = charts.grouped_bars([names[o] for o in eco.index], {'Extra gross profit': eco['extra gross profit ₹'], 'Reward cost': -eco['reward cost ₹'],
                                                             'Net extra profit': eco['net extra profit ₹']}, '₹ per customer offered',
                              'What each offer earns, costs and keeps', colors={'Extra gross profit': '#22C55E', 'Reward cost': '#EF4444',
                                                                               'Net extra profit': ui.COLORS['nudge']})
    charts.show(fig, width='stretch')
    tab = pd.DataFrame({'extra buying (pts)': lift.loc[eco.index, 'buy_lift_pts'].values, 'net extra profit per customer': eco['net extra profit ₹'].map(fmt.rs).values},
                       index=[names[o] for o in eco.index])
    st.dataframe(tab, width='stretch')
    sb = x5.table('step8_starbucks_budget').set_index('share offered').loc[0.4]
    st.markdown(f"- The free item lifts buying most ({lift.loc['bogo', 'buy_lift_pts']:.1f} pts) **and** keeps most profit, because a freebie "
                f"costs only its cost of goods; a plain reminder keeps {eco.loc['informational', 'net extra profit ₹'] / eco.loc['discount', 'net extra profit ₹']:.0%} "
                f"of the discount's profit at no reward cost.\n"
                f"- With an offer budget for 40% of customers, Nudge's ranking earns {fmt.rs(sb['engine ₹'])} vs {fmt.rs(sb['random ₹'])} per customer "
                f"for random picks ({plus(sb['engine gain ₹'])}, range {fmt.rs(sb['gain low95'])} to {fmt.rs(sb['gain high95'])}).")
    st.caption('Starbucks rewards test (simulated data released by Starbucks; Step 6 and 8). Rupees: price-level ₹70 per $ and 75% café margin '
               '(Costa Coffee India FY25). Assumed.')

with t4:
    st.markdown('**Would an untested offer pay for itself?** How much extra buying it must cause before its cost is covered. '
                'The cost is paid by every buyer who gets it, so customers who buy anyway make offers expensive.')
    b1, b2, b3 = st.columns(3)
    who = b1.radio('Customer', ['Regular (60% buy anyway)', 'Occasional (30%)', 'Lapsed (10%)', 'Custom'], index=0)
    p0 = {'Regular (60% buy anyway)': 0.6, 'Occasional (30%)': 0.3, 'Lapsed (10%)': 0.1}.get(who)
    if p0 is None:
        p0 = b1.slider('Buy anyway (%)', 0, 100, 40) / 100
    otype = b2.selectbox('Offer', list(planner.OFFER_TYPES), index=1)
    face = b2.number_input('Face value (₹)', 0.0, 100_000.0, 50.0, 10.0, disabled=otype == 'Reminder (no offer)')
    rate = 1.0
    if otype in ('Cashback', 'Wallet credit', 'Free item'):
        rate = b2.number_input({'Cashback': 'Share who redeem (%)', 'Wallet credit': 'Share who use it (%)', 'Free item': 'Cost of goods (% of value)'}[otype],
                               0.0, 100.0, 85.0 if otype == 'Free item' else 75.0, 5.0) / 100
    reward = 0.0 if otype == 'Reminder (no offer)' else face
    kw = dict(contact_cost=cost, reward=reward, reward_cost_share=rate if otype == 'Free item' else 1.0,
              redeem=rate if otype in ('Cashback', 'Wallet credit') else 1.0)
    need = float(breakeven_uplift(p0, k, **kw))
    with b3:
        if np.isinf(need):
            ui.kpi_grid([{'label': 'Needs', 'value': 'Never pays', 'note': 'the reward costs more than the profit per purchase', 'source': ''}])
        else:
            ui.kpi_grid([{'label': 'Needs', 'value': fmt.pts(need, 1), 'note': 'extra buying to break even', 'source': f'₹{k:,.0f} per purchase, {fmt.cost(cost)} per contact',
                          'tags': ('assumed',)}])
    S = x5.summary()
    st.markdown(f"For comparison (measured): the X5 SMS raised buying by **{fmt.pts(S['lift'])}**; Starbucks offers raised buying within 72 hours by "
                f"**{fmt.pts(lift['buy_lift_pts'].min() / 100)} to {fmt.pts(lift['buy_lift_pts'].max() / 100)}**.")
    with st.expander('Formula and Step 8 examples'):
        st.markdown('Extra profit = extra buying × profit per purchase − contact cost − reward cost × (buy anyway + extra buying). '
                    'Setting it to zero gives the extra buying needed: (contact cost + reward cost × buy anyway) ÷ (profit per purchase − reward cost).')
        st.dataframe(x5.table('step8_breakeven').set_index('customer').style.format('{:.1f} pts'), width='stretch')
        st.caption('Step 8: ₹150 profit per purchase, SMS ₹0.10 (WhatsApp reminder ₹1.02).')

# ---------------- facts for the AI analyst ----------------
try:                                   # the AI analyst is optional: it must never break the page
    ss['money_ctx'] = {'mode': mode, 'k': k, 'cost': cost, 'chan': chan, 'base': base}   # for budget what-ifs in the chat
    where = 'X5 example (pre-computed)' if X5_MODE else f"your data ({ss['plan']['source']})"
    SOURCE = 'X5 example (pre-computed, Russian retail)' if X5_MODE else ss['plan']['source']
    analyst.publish('money', [
        ('channel', f'Channel on the Money page: {chan_label}, costing {fmt.cost(cost)} per contact. Profit per extra purchase ₹{k:,.0f}. '
                    'To choose between channels, the channel ladder compares Email, SMS, WhatsApp and AI voice call.'),
        ('budget_plan', f'Money page, {where}, budget {fmt.rs(budget)} on {chan_label} for {fmt.count(base)} customers: ' + analyst.plain(ss.get('_decision'))
                        + f" Nudge {fmt.rs(r100(a.profit))}, usual approach {fmt.rs(r100(b.profit))}, difference {plus(r100(diff))}"
                        + (f' (range {fmt.rs(dlo)} to {fmt.rs(dhi)}).' if not np.isnan(dlo) else '.') + ' Measured; margin and costs assumed.'),
        ('assumptions', f'Assumed on the Money page: ₹{k:,.0f} profit per extra purchase; {chan_label} at {fmt.cost(cost)} per contact; base {fmt.count(base)} customers.'),
        ('best_share', f'Without a budget limit: best share to contact {best5.share:.0%} ({fmt.count(best5.contacts)} customers), profit '
                       f'{fmt.rs(best5.profit)} (range {fmt.rs(best5.low95)} to {fmt.rs(best5.high95)}); contacting everyone {fmt.rs(everyone.profit)}.'),
        *([('channel_ladder_true', 'TRUE channel results (known only because this sample is made up; not measured), following the plan\'s '
                                   'order: ' + '; '.join(f"{ch}: true best share {r['true best share']:.0%}, true saved by targeting "
                                                         f"{fmt.rs(r['true saved by targeting'])}" for ch, r in TRUTH.iterrows())
                                   + '. The measured channel ladder is noisy on this sample; prefer the true results.')] if TRUTH is not None else []),
        ('channel_ladder', 'Channel ladder (best share, profit at best, profit if contact all): ' + '; '.join(
            f"{ch} {fmt.cost(r['₹ per contact'])}: {r['best share']:.0%}, {fmt.rs(r['profit at best'])}, {fmt.rs(r['profit if contact all'])}" for ch, r in lad.iterrows())),
        ('stress', f'Stress test of the plan (contact the top {plan_share:.0%}): ' + '; '.join(
            f"{sc}: old plan {fmt.rs(r['old plan'])}, re-optimised {fmt.rs(r['re-optimised plan'])} at {r['re-optimised share']:.0%}, everyone {fmt.rs(r['contact everyone'])}"
            for sc, r in stress.iterrows())),
        ('breakeven', f'Break-even calculator: a {otype.lower()} worth ₹{face:,.0f} to a customer who buys anyway {p0:.0%} of the time needs '
                      + ('more than the profit per purchase: it never pays' if np.isinf(need) else f'{fmt.pts(need, 1)} of extra buying to pay for itself')
                      + f' (₹{k:,.0f} per purchase, {fmt.cost(cost)} per contact). For comparison the X5 SMS raised buying {fmt.pts(x5.summary()["lift"])}; '
                      f"Starbucks offers {fmt.pts(lift['buy_lift_pts'].min() / 100)} to {fmt.pts(lift['buy_lift_pts'].max() / 100)}."),
    ], source=SOURCE)
except Exception as e:
    st.caption(f':material/info: The AI analyst could not read this page ({type(e).__name__}); everything else on the page works.')
