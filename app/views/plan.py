"""Plan my campaign: upload a randomised test (or a sample) -> check it is fair -> train -> whom to contact, with which option
-> chosen on honest 5-fold scores of 80% of the file, proven on an untouched 20% -> download the target list. Optional thorough mode repeats Step 4."""
import copy
import math
import time

import numpy as np
import pandas as pd
import streamlit as st
from scipy.stats import norm, spearmanr

from lib import analyst, charts, fmt, planner, shared, thorough, ui, upload, x5

ASSUME = x5.meta()['assumptions']
CHANNELS = {k: v['value'] for k, v in ASSUME['channels_rs_per_contact'].items()}
ss = st.session_state


def _own_copy(res: dict) -> dict:
    """A visitor's own view of a shared plan: the engines hold settings each visitor changes (contact cost, safety margin)."""
    r = dict(res); eng = copy.copy(res['engine']); eng.base = copy.copy(res['engine'].base); eng._cache = []
    r['engine'], r['fast_engine'] = eng, eng.base
    return r


def use_sample(key: str) -> None:
    for k in ['plan', 'thorough_out']:
        ss.pop(k, None)
    ss['data_src'] = {'name': upload.SAMPLES[key]['name'], 'df': upload.load_sample(key), 'sample': key}


st.title('Plan my campaign')
try:
    analyst.publish('plan', [('state', 'No plan has been built yet on this page: the user still needs to upload a file or try a sample.')])
except Exception:                      # the AI analyst is optional
    pass
st.caption('Whom to contact, with which option, and what it earns: learned from your randomised test, proven on customers the model never saw.')

# ---------------- 1. data ----------------
if ss.get('use_sample'):
    use_sample(ss.pop('use_sample'))

if 'data_src' not in ss:
    c1, c2 = st.columns([1.3, 1])
    with c1:
        f = st.file_uploader('Upload a CSV from a randomised campaign test', type=['csv', 'gz'],
                             help='One row per customer: the option they got (one value = nothing), the outcome, and measures known before.')
        if f is not None:
            try:
                ss['data_src'] = {'name': f.name, 'df': upload.read_csv(f.getvalue()), 'sample': None}
                st.rerun()
            except Exception as e:
                st.error(f'Could not read this file as a CSV ({type(e).__name__}). Save it as comma-separated text and try again.')
    with c2:
        st.markdown('**Or try a sample**')
        if st.button('Hillstrom e-mail test (real, public)', icon=':material/play_circle:', type='primary', width='stretch'):
            use_sample('hillstrom'); st.rerun()
        if st.button('Synthetic X5-like test (shows targeting)', icon=':material/science:', width='stretch'):
            use_sample('synthetic'); st.rerun()
        st.caption('Hillstrom: 64,000 real customers. Synthetic: 2,00,000 made-up customers calibrated to the real X5 results, '
                   'with known true responders.')
    with st.expander('What should my file look like?'):
        st.markdown('One row per customer who was part of the test. Options must have been given **at random**.')
        st.dataframe(pd.DataFrame({'customer_id': ['C001', 'C002', 'C003', 'C004'], 'option': ['SMS', 'nothing', 'discount', 'SMS'],
                                   'bought': [1, 0, 1, 0], 'orders_last_90d': [4, 1, 7, 0], 'days_since_last_order': [6, 40, 3, 95],
                                   'city_tier': ['1', '2', '1', '3']}), hide_index=True)
        st.markdown('- **option**: what each customer got; one value means "nothing" (the control group)\n'
                    '- **outcome**: bought 1/0, or an amount spent, measured after the contact\n'
                    '- **measures**: anything known *before* the contact (history, tier, age...)\n'
                    '- **customer id**: optional; used for the download')
    st.stop()

src = ss['data_src']; df = src['df']; sample = upload.SAMPLES.get(src['sample'])
top = st.columns([3, 1])
top[0].markdown(f"**Data:** {src['name']} · {fmt.count(len(df))} rows · {df.shape[1]} columns")
if top[1].button('Use other data', icon=':material/swap_horiz:'):
    for k in ['data_src', 'plan', 'thorough_out']:
        ss.pop(k, None)
    st.rerun()
if sample:
    st.info(sample['note'], icon=':material/science:' if src['sample'] == 'synthetic' else ':material/dataset:')

# ---------------- 2. columns ----------------
guess = sample['mapping'] if sample else upload.guess_mapping(df)
cols = list(df.columns); key = f"{src['name']}_{len(df)}"
with st.expander('Columns: what each one means', expanded=not sample):
    a, b, c, d = st.columns(4)
    opt_col = a.selectbox('Option given', cols, index=cols.index(guess['option']), key=f'opt_{key}',
                          help='Which option each customer got, assigned at random.')
    values = [str(v) for v in df[opt_col].dropna().unique()][:50]
    ctrl = b.selectbox('Control value ("nothing")', values, placeholder='Choose the control value',   # no guess: the user must choose
                       index=values.index(str(guess['control'])) if guess['control'] is not None and str(guess['control']) in values else None,
                       key=f'ctrl_{key}_{opt_col}')
    out_choices = [x for x in cols if x != opt_col]
    outcome = c.selectbox('Outcome', out_choices, key=f'out_{key}',
                          index=out_choices.index(guess['outcome']) if guess['outcome'] in out_choices else 0,
                          help='Bought 1/0 or an amount, measured after the contact.')
    id_choices = ['(none)'] + [x for x in cols if x not in (opt_col, outcome)]
    cid = d.selectbox('Customer id (optional)', id_choices, key=f'id_{key}',
                      index=id_choices.index(guess['id']) if guess['id'] in id_choices else 0)
    feat_choices = [x for x in cols if x not in (opt_col, outcome, cid)]
    feats = st.multiselect('Customer measures (known before the contact)', feat_choices, key=f'feat_{key}',
                           default=[x for x in guess['features'] if x in feat_choices])
mapping = {'option': opt_col, 'control': ctrl, 'outcome': outcome, 'id': None if cid == '(none)' else cid, 'features': feats,
           'labels': guess.get('labels', {})}

checks = upload.validate(df, mapping)
if any(l == 'error' for l, _ in checks):                 # the file cannot be used: show only what stops it, not side warnings
    checks = [c for c in checks if c[0] == 'error']
for level, msg in checks:
    (st.error if level == 'error' else st.warning)(msg, icon=':material/error:' if level == 'error' else ':material/warning:')
if any(l == 'error' for l, _ in checks):
    st.stop()

prep = upload.prepare(df, mapping)
if prep['dropped']:
    st.caption(f"Not used as measures: {', '.join(prep['dropped'])}. They are text with more than 20 different values "
               "(such as free text, dates or cities), which the model cannot use as they are.")

# ---------------- 3. fairness ----------------
light, reason, ok_gap = upload.fairness(prep['max_gap'], prep['min_group'], prep['n_control'])
icon = {'green': ':material/check_circle:', 'amber': ':material/warning:', 'red': ':material/cancel:'}[light]
msg = (f"**Is the test fair? {('Yes' if light == 'green' else 'Mostly' if light == 'amber' else 'No')}.** {reason} "
       f"Largest gap between groups: {prep['max_gap']:.3f} on *{prep['worst']}* (under {ok_gap:.2f} is what chance alone gives at this size).")
{'green': st.success, 'amber': st.warning, 'red': st.error}[light](msg, icon=icon)
if light == 'red':
    cj = x5.table('step10_careful').set_index('control group')['effect %']
    st.markdown(f"""
**Why this matters.** If the company chose who got the campaign (often its best customers), those customers would have bought more
anyway, and any model learns that difference, not the campaign's effect. In Step 10 of this project (Dunnhumby, where the company chose
the targets), the targeted group already spent 6.3× more *before* the campaign, and two careful analyses of the same campaign gave
**{fmt.signed(cj.max(), 1, '%')}** and **{fmt.signed(cj.min(), 1, '%')}**: opposite answers, both confident.

**Do this instead: run a random pilot first.** Pick the customers you would contact, randomly hold back a share of them, run the campaign,
then upload that file here.""")
    st.page_link('views/prove.py', label='Size the pilot: control-group calculator', icon=':material/calculate:')
    if not st.checkbox('Train anyway (results may mislead)'):
        st.stop()

# ---------------- 4. money inputs ----------------
st.subheader('Your numbers')
m1, m2, m3 = st.columns(3)
if prep['kind'] == 'binary':
    value = m1.number_input('Profit per extra purchase (₹)', 1.0, 100_000.0, float(ASSUME['profit_per_purchase_rs']['value']), 10.0,
                            help='Default: ₹1,000 basket x 15% gross margin (Indian supermarket). Change it to yours.')
    unit_note = f'₹{value:,.0f} profit per extra purchase'
else:
    margin = m1.number_input('Profit margin on the amount (%)', 1.0, 100.0, 15.0, 1.0,
                             help='Share of each extra rupee of spend you keep as profit. Default 15% (Indian supermarket).')
    per_unit = m2.number_input('₹ per unit of the amount', 0.01, 10_000.0, float(sample.get('per_unit', 1.0)) if sample else 1.0,
                               help='1 if the amount is already in rupees. ' + (sample.get('per_unit_note', '') if sample else ''))
    value = margin / 100 * per_unit
    unit_note = f'{margin:.0f}% margin' + (f' × ₹{per_unit:g} per unit' if per_unit != 1 else '')
    if sample and sample.get('per_unit_note') and per_unit == sample['per_unit']:
        unit_note += f" ({sample['per_unit_note']})"
chan_list = list(CHANNELS) + ['Custom']
chan = m3.selectbox('Channel (cost per contact)', chan_list, index=chan_list.index(sample['channel']) if sample else 1, key=f'chan_{key}')
cost = (m3.number_input('Custom ₹ per contact', 0.0, 1000.0, float(sample.get('custom_cost', 1.0)) if sample else 1.0, key=f'cost_{key}')
        if chan == 'Custom' else CHANNELS[chan])
chan_txt = f"{chan} {fmt.cost(cost)} per contact" + (f" ({sample['cost_note']})" if sample and chan == 'Custom' and cost == sample.get('custom_cost') else '')
# how the decision box names the channel: the option is WHAT customers get, the channel is HOW (and what each contact costs)
chan_short = ('a 1-minute AI voice call' if sample and chan == 'Custom' and cost == sample.get('custom_cost')
              else 'a contact' if chan == 'Custom' else chan) + f' ({fmt.cost(cost)} each)'

with st.expander('Offer cost per option (if an option was a discount, cashback, wallet credit or free item)'):
    st.caption('A reminder costs only the contact. An offer is also paid to every buyer who got it, including those who would have bought anyway.')
    offers = {}
    for o in prep['options']:
        o1, o2, o3 = st.columns([1.2, 1, 1])
        t = o1.selectbox(f'"{o}" is a', list(planner.OFFER_TYPES), key=f'offer_{key}_{o}')
        if t == 'Reminder (no offer)':
            offers[o] = {'type': t}; continue
        face = o2.number_input('Face value (₹)', 0.0, 100_000.0, 50.0, 10.0, key=f'face_{key}_{o}')
        rate_label = {'Cashback': 'Share who redeem (%)', 'Wallet credit': 'Share who use it (%)', 'Free item': 'Cost of goods (% of value)'}
        rate = 100.0 if t == 'Discount' else o3.number_input(rate_label[t], 0.0, 100.0, 85.0 if t == 'Free item' else 75.0, 5.0,
                                                             key=f'rate_{key}_{o}')
        offers[o] = {'type': t, 'face': face, 'rate': rate / 100}
        o3.caption(f"Costs ₹{planner.reward_per_buyer(offers[o]):,.2f} per buyer ({planner.OFFER_TYPES[t]})") if t == 'Discount' else None
has_offer = any(planner.reward_per_buyer(v) > 0 for v in offers.values())
offer_note = '; '.join(f"{o}: {v['type'].lower()} ₹{planner.reward_per_buyer(v):,.2f} per buyer" for o, v in offers.items()
                       if planner.reward_per_buyer(v) > 0)
st.caption(f'{ui.tag("assumed")} {unit_note}; {chan_txt}' + (f'; {offer_note}' if offer_note else '') + '. '
           + ('Changing the margin or an offer needs a rebuild (offers are paid by buyers).' if has_offer
              else 'Change these any time: the plan updates without retraining.')
           + (f" Exchange-rate source: [CEIC]({sample['per_unit_link']}), [FBIL](https://www.fbil.org.in/)."
              if sample and sample.get('per_unit_link') and prep['kind'] != 'binary' and per_unit == sample['per_unit'] else ''),
           unsafe_allow_html=True)

# ---------------- 5. train ----------------
# the plan must be rebuilt when the data, the column choices or the offer costs change (and the margin, when offers are paid)
sig = (key, repr(mapping), repr(offers), value if has_offer else None)
if ss.get('plan', {}).get('sig') != sig:
    if 'plan' in ss:
        st.info('Your settings changed since the last plan. Rebuild to update it.', icon=':material/refresh:')
    est = planner.expected_seconds(len(prep['data']), len(prep['options']))
    lo = max(1, math.floor(0.8 * est / 60)); hi = max(lo + 1, math.ceil(1.6 * est / 60))
    parts = 3 if min(len(prep['data']), upload.MAX_ROWS) * 0.8 > 150_000 else 5
    st.caption(f":material/schedule: Building takes about **{lo}–{hi} minutes** for {fmt.count(len(prep['data']))} rows and "
               f"{len(prep['options'])} option{'' if len(prep['options']) == 1 else 's'}: three uplift models are trained on {parts} parts of the "
               'file, and the page shows each step while it works.'
               + (' This sample loads instantly if anyone has built it since the app last restarted.' if sample else ''))
    if st.button('Build my plan', type='primary', icon=':material/rocket_launch:'):
        with st.status('Building your plan...', expanded=True) as box:
            t0 = time.time()
            res = (_own_copy(shared.get('plan', repr(sig), lambda: planner.train(prep, value, cost, offers, status=box.write)))
                   if sample else planner.train(prep, value, cost, offers, status=box.write))
            box.update(label=(f"Done in {res['secs']:.0f} s" if time.time() - t0 > 3 else
                              'Ready: this sample was already built on the server'), state='complete', expanded=False)
        ss['plan'] = {'sig': sig, 'res': res, 'prep': prep, 'source': src['name'], 'sample': src['sample']}
        ss.pop('thorough_out', None); st.rerun()
    st.stop()

res = ss['plan']['res']
if res.get('fallback_reason'):
    st.warning('The thorough ranking could not run on this file, so the plan uses the fast engine instead '
               f"({res['fallback_reason']}).", icon=':material/warning:')
memo = ss['plan'].setdefault('memo', {})
if (value, cost) not in memo:
    with st.spinner('Updating the plan...'):
        memo[(value, cost)] = planner.plan(res, prep, value, cost)
P = memo[(value, cost)]
ss['plan']['current'] = {'value': value, 'cost': cost, 'unit_note': unit_note, 'channel': chan, 'chan_txt': chan_txt, 'P': P}

# ---------------- 6. decision ----------------
N = len(df); M = P['money']; per = 1000
mix = pd.Series(P['rec']).value_counts(normalize=True)
mix_txt = ', '.join(f'{o} to {v:.0%}' for o, v in mix.items() if o != prep['control'])
du, db = P['diff']['usual'], P['diff']['blanket']
R = P['recommended']; ru = P['vs_usual_all'][R]
rng_txt = lambda d: f"{fmt.rs(abs(d[0]) * per)} per 1,000 customers (95% range {fmt.rs(d[1] * per)} to {fmt.rs(d[2] * per)})"
st.subheader('Your plan')
if P.get('signal_message'):
    st.info(P['signal_message'], icon=':material/info:')
if P['personalise']:
    if db[0] >= 0:
        verdict = (f"earns {rng_txt(db)} more than <i>{P['blanket'].lower()}</i>: "
                   + ('proven.' if db[1] > 0 else 'ahead, but the range includes zero, so keep a control group to confirm.'))
    else:
        verdict = (f"earns {rng_txt(db)} less than <i>{P['blanket'].lower()}</i>: the 5-fold check on the 80% preferred the personalised plan, "
                   'but the untouched 20% does not confirm it, so treat it with caution and keep a control group.')
    ui.decision(f"Contact <b>{P['share']:.0%}</b> of customers (about {fmt.count(P['share'] * N)} of {fmt.count(N)}) by {chan_short}, with these options: {mix_txt}. "
                f"Leave the other {1 - P['share']:.0%} alone. On the untouched 20% this plan {verdict}")
elif P.get('audit_failed'):
    ui.decision((f"<b>Do not run this campaign at {fmt.cost(cost)} per contact.</b>" if P['blanket'] == 'Contact nobody' else
                 f"<b>Send {P['best_opt']} to everyone</b> by {chan_short}.")
                + f" The 5-fold check on the 80% preferred a personalised plan, but the final check on the untouched 20% did not confirm it: "
                f"it earned {rng_txt(db)} less than {P['blanket'].lower()}. So Nudge recommends the simple plan"
                + ('' if P['blanket'] == 'Contact nobody' else
                   f" ({fmt.rs(M.loc[R, 'extra_vs_nobody'] * per)} extra profit per 1,000 customers, measured on the untouched 20%)")
                + '. Keep a control group, and test personalising again when you have more data.')
elif P['blanket'] == 'Contact nobody':
    ui.decision(f"<b>Do not run this campaign at {fmt.cost(cost)} per contact.</b> No option earns back its cost. "
                'Try a cheaper channel above, or a cheaper offer.')
elif P['engine_simple']:
    ui.decision(f"<b>Send {P['best_opt']} to everyone</b> by {chan_short}. The engine found that personalising does not pay on this data: its learned "
                f"safety margin gives every customer the option that works best on average "
                f"({fmt.rs(M.loc[R, 'extra_vs_nobody'] * per)} extra profit per 1,000 customers, measured on the untouched 20%).")
elif db[0] < 0:
    ui.decision(f"<b>Send {P['best_opt']} to everyone</b> by {chan_short}. Nudge protected you from a <b>{fmt.rs(-db[0] * per)} loss per 1,000 customers</b> "
                f"by refusing a personalised plan that does not pay (measured on the untouched 20%; 95% range of the personalised plan vs "
                f"this one: {fmt.rs(db[1] * per)} to {fmt.rs(db[2] * per)}). Everyone gets the option that works best on average: "
                f"{fmt.rs(M.loc[R, 'extra_vs_nobody'] * per)} extra profit per 1,000 customers.")
else:
    ui.decision(f"<b>Send {P['best_opt']} to everyone</b> by {chan_short}. The personalised plan did not beat it on the 5-fold check. On the untouched "
                f"20% personalising would have changed profit by +{rng_txt(db)}: not a reliable gain, so Nudge keeps the simple plan.")
if P['personalise'] and not P['ladder_top']:
    st.warning('The lift ladder below is out of order (the "High" group did not respond more than "Low"). Treat the plan with caution.',
               icon=':material/warning:')
st.page_link('views/money.py', label='Set a budget on the Money page', icon=':material/currency_rupee:')

plus = lambda v: ('+' if v >= 0 else '') + fmt.rs(v)
LOCKED = f"measured on the untouched 20% ({fmt.count(P['n_test'])} customers)"
card3 = ({'label': 'vs usual approach', 'value': 'Same', 'note': 'at this share both contact the same customers; see Money for smaller budgets',
          'source': LOCKED} if P['rec_share'] in (0.0, 1.0) else
         {'label': 'vs usual approach', 'value': plus(ru[0] * per), 'note': 'per 1,000 customers, same number of contacts',
          'source': f"range {fmt.rs(ru[1] * per)} to {fmt.rs(ru[2] * per)}", 'tags': ('measured',)})
if P['personalise']:
    card4 = {'label': f"vs {P['blanket'].lower()}", 'value': plus(db[0] * per), 'note': 'per 1,000 customers',
             'source': f"range {fmt.rs(db[1] * per)} to {fmt.rs(db[2] * per)}", 'tags': ('measured',)}
elif P['engine_simple']:
    card4 = {'label': 'Personalising', 'value': 'Not chosen', 'note': 'the engine gave everyone the same option',
             'source': 'its learned safety margin found no reliable gain'}
else:
    card4 = {'label': 'Loss avoided' if db[0] < 0 else 'If personalised', 'value': fmt.rs(abs(db[0]) * per) if db[0] < 0 else plus(db[0] * per),
             'note': 'per 1,000 customers, by not personalising' if db[0] < 0 else 'per 1,000 customers: not a reliable gain',
             'source': f"range {fmt.rs(db[1] * per)} to {fmt.rs(db[2] * per)} (personalised minus simple)", 'tags': ('measured',)}
ui.kpi_grid([
    {'label': 'Contact', 'value': f"{P['rec_share']:.0%}", 'note': 'of customers', 'source': f"{fmt.count(P['rec_share'] * N)} of {fmt.count(N)}"},
    {'label': 'Extra profit', 'value': fmt.rs(M.loc[R, 'extra_vs_nobody'] * per), 'note': 'per 1,000 customers, vs contacting nobody',
     'source': unit_note, 'tags': ('measured', 'assumed')},
    card3, card4,
])

g1, g2 = st.columns(2)
with g1:
    order = ['Nudge plan', 'Usual approach', f"Contact everyone ({P['best_opt']})", 'Contact nobody']
    charts.show(charts.policy_bars(order, [M.loc[o, 'extra_vs_nobody'] * per for o in order], R, '₹ per 1,000 customers',
                                       'Extra profit vs contacting nobody (untouched 20%)'), width='stretch')
with g2:
    L = P['ladder']; unit = 'pts of buying' if prep['kind'] == 'binary' else '₹ per customer'
    avg = (prep['data'][prep['data']._option != prep['control']]._y.mean() - prep['data'][prep['data']._option == prep['control']]._y.mean())
    charts.show(charts.ladder(list(L.index), L.real_lift.tolist(), L.low95.tolist(), L.high95.tolist(), unit,
                                  avg * (100 if prep['kind'] == 'binary' else value),
                                  'Lift ladder: real lift by predicted group (untouched 20%)'), width='stretch')
    st.caption(('**In order:** customers Nudge rates highly really do respond more. The model works on your data.' if P['ladder_ok'] else
                '**Top group clearly ahead:** the customers Nudge rates highest respond most; the medium and low groups respond about the same.'
                if P['ladder_top'] else '**Out of order:** on your data the ranking does not hold up on unseen customers. Do not personalise.')
               + ' Bars are measured: contacted vs randomly held back, within each third.')

# ---------------- 7. personas ----------------
st.subheader('Who responds')
pc = st.columns(3)
lift_unit = (lambda v: fmt.pts(v / 100, 1)) if prep['kind'] == 'binary' else (lambda v: f"{fmt.rs(v)} per customer")
for col, t, title in zip(pc, ['High', 'Medium', 'Low'], ['High responders', 'Medium responders', 'Low responders']):
    p = P['personas'][t]
    with col.container(border=True):
        st.markdown(f"**{title}** · {p['share']:.0%} of customers")
        st.markdown(f"Real lift: **{lift_unit(p['lift'])}** (± {lift_unit(1.96 * p['se']).lstrip('+')})")
        if P['personalise']:
            st.markdown(f"In the plan: {p['contacted']:.0%} contacted" + (f", mostly {p['mix'].index[0]}" if p['contacted'] > 0 else ''))
        else:
            st.markdown('In the plan: ' + ('not contacted' if P['blanket'] == 'Contact nobody' else f"contacted ({P['best_opt']}, like everyone)"))
        st.markdown('\n'.join(f'- {w}' for w in p['traits']))
st.caption('Groups are thirds of the untouched 20%, ranked by predicted extra profit. Traits: the measures that set each group apart most.')

with st.expander('What each option does on average'):
    E = P['effects'].copy()
    E.columns = ['extra profit per customer (₹)', 'low 95%', 'high 95%', 'customers']
    st.dataframe(E.style.format({'extra profit per customer (₹)': '{:+.2f}', 'low 95%': '{:+.2f}', 'high 95%': '{:+.2f}', 'customers': '{:,.0f}'}))
    st.caption(f'Whole file, after {fmt.cost(cost)} per contact' + (' and offer costs' if has_offer else '') + '. Measured: option vs control group.')

# ---------------- 8. truth check (synthetic sample only) ----------------
if sample and sample.get('truth'):
    st.subheader('Truth check: did Nudge find the real responders?')
    st.caption('Only possible on the synthetic sample, where we wrote down each customer\'s true response. Nudge never saw it.')
    tr = res['test'][['_id']].merge(upload.load_truth(src['sample']), left_on='_id', right_on='customer_id', how='left')
    true_lift, persona = tr.true_lift.values, tr.true_persona.values
    gain = P['gain']; n = len(gain)
    top17 = planner._desc(gain)[:int(0.17 * n)]; bot9 = planner._desc(-gain)[:int(0.09 * n)]
    found_top = np.mean(persona[top17] == 'Nudgeable'); found_bot = np.mean(persona[bot9] == 'Loyal regular')
    contact = P['rec'] != prep['control'] if P['personalise'] else np.full(n, P['blanket'] != 'Contact nobody')
    true_profit = lambda sel: (true_lift[sel] * value - cost).sum() / n * per
    best = true_profit(true_lift * value > cost)
    usual_sel = np.zeros(n, bool); usual_sel[planner._desc(planner._score(res['usual'], res['test'][prep['features']]))[:int(contact.sum())]] = True
    ui.kpi_grid([
        {'label': 'Ranking quality', 'value': f'{spearmanr(gain, true_lift)[0]:.2f}', 'note': 'rank correlation with the true lift (1 = perfect)',
         'source': 'synthetic truth'},
        {'label': 'Top 17% by Nudge', 'value': f'{found_top:.0%}', 'note': 'are truly nudgeable (17% if picked at random)', 'source': 'synthetic truth'},
        {'label': 'Bottom 9% by Nudge', 'value': f'{found_bot:.0%}', 'note': 'are truly loyal regulars who buy anyway (9% at random)',
         'source': 'synthetic truth'},
        {'label': 'Of the best possible profit', 'value': f'{true_profit(contact) / best:.0%}' if best > 0 else 'n/a',
         'note': f'captured by the plan (usual approach: {true_profit(usual_sel) / best:.0%})' if best > 0 else 'no profitable contact exists',
         'source': 'best possible: contact only those whose true lift pays for the contact'},
    ])
    # true profit of each plan, known only because the truth is known, next to what the untouched 20% measured
    pols = planner.test_policies(res, prep, P); ctrl = prep['control']
    true_of = lambda a: ((np.asarray(a) != ctrl) * (true_lift * value - cost)).sum() / n * per
    TT = pd.DataFrame({'true profit per 1,000': {q: true_of(a) for q, a in pols.items()},
                       'measured on the untouched 20%': {q: M.loc[q, 'extra_vs_nobody'] * per for q in pols},
                       'customers contacted': {q: np.mean(np.asarray(a) != ctrl) for q, a in pols.items()}})
    st.markdown('**True profit of each plan** (only knowable here) next to what the untouched 20% measured:')
    st.table(TT.style.format({'true profit per 1,000': fmt.rs, 'measured on the untouched 20%': fmt.rs, 'customers contacted': '{:.0%}'}))
    te_ = res['test']; tg = te_[te_._option != ctrl]._y; cg = te_[te_._option == ctrl]._y
    m_lift = tg.mean() - cg.mean(); m_se = np.sqrt(tg.var() / len(tg) + cg.var() / len(cg)); t_lift = true_lift.mean()
    z = (m_lift - t_lift) / m_se; odds = 1 / max(2 * (1 - norm.cdf(abs(z))), 1e-6)
    plan_name = 'Nudge plan' if P['personalise'] else P['blanket']
    winner = TT['true profit per 1,000'].idxmax()
    if winner == plan_name:
        gap = TT.loc[plan_name, 'true profit per 1,000'] - TT.loc[P['blanket'], 'true profit per 1,000'] if P['personalise'] else None
        st.success(
            f"**The truth says the plan wins:** {fmt.rs(TT.loc[plan_name, 'true profit per 1,000'])} per 1,000 customers"
            + (f", against {fmt.rs(TT.loc[P['blanket'], 'true profit per 1,000'])} for {P['blanket'].lower()} (true difference {plus(gap)}). "
               f"The measured {plus(db[0] * per)} on the untouched 20% is measurement noise: its 95% range ({fmt.rs(db[1] * per)} to "
               f"{fmt.rs(db[2] * per)}) includes zero."
               + (f" The true difference even lies {'above' if gap > db[2] * per else 'below'} that range: the kind of miss a 95% range "
                  'makes about 1 time in 20.' if not db[1] * per <= gap <= db[2] * per else '') if P['personalise'] else '.')
            + f" The noise comes from the untouched 20% itself: there, the message measured {fmt.pts(m_lift, 2)} on average against a true "
            f"{fmt.pts(t_lift, 2)} ({abs(z):.1f} standard errors {'high' if z > 0 else 'low'}, about a 1-in-{odds:,.0f} draw). "
            + ('That flatters plans that contact more people, most of all contacting everyone.' if z > 0 else
               'That understates plans that contact more people.'), icon=':material/check_circle:')
    else:
        st.warning(f"**The truth says {winner.lower()} would earn more** ({fmt.rs(TT.loc[winner, 'true profit per 1,000'])} vs "
                   f"{fmt.rs(TT.loc[plan_name, 'true profit per 1,000'])} per 1,000 for the chosen plan). On real data this cannot be checked; "
                   'it is why a permanent control group matters.', icon=':material/warning:')
    mixt = pd.crosstab(pd.Series(P['tiers'], name='Nudge group'), pd.Series(persona, name='true persona'), normalize='index')
    st.markdown('**Who is in each Nudge group, really:**')
    st.table(mixt.reindex(['High', 'Medium', 'Low'])[['Nudgeable', 'Average', 'Loyal regular']].style.format('{:.0%}'))
    st.caption('Rows: Nudge\'s High / Medium / Low thirds on the untouched 20%. Columns: who they really are. '
               'A good ranking puts nudgeable customers in High and loyal regulars in Low.')

# ---------------- facts for the AI analyst ----------------
try:                                   # the AI analyst is optional: it must never break the page
    chan_name = chan_short.rsplit(' (', 1)[0]                     # e.g. 'a 1-minute AI voice call'
    need = cost / value                                            # extra buying a contact must cause to pay for itself
    f_ = 100 if prep['kind'] == 'binary' else value               # the ladder is in pts (yes/no outcome) or ₹ per customer (amounts)
    need_txt = fmt.pts(need, 2, sign=False) if prep['kind'] == 'binary' else f'{fmt.inr(cost, 2)} of extra profit before costs'
    reliable = lambda d: ('a reliable difference, the range is above zero' if d[1] > 0 else 'a reliable difference, the range is below zero'
                          if d[2] < 0 else 'NOT a reliable difference, the range includes zero')
    ladder_words = ('in order: high > medium > low' if P['ladder_ok'] else
                    'not fully in order: the high group responds most, while the medium and low groups respond about the same'
                    if P['ladder_top'] else 'out of order: the ranking does not hold up on unseen customers')
    F = [('decision', 'Plan page, recommended action: ' + analyst.plain(ss.get('_decision'))),
         ('channel', f"Channel on the Plan page: {chan_name}, costing {fmt.cost(cost)} per contact. Profit per extra purchase: "
                     f"{unit_note}. This is the only channel and cost used in this plan."),
         ('breakeven_contact', f"At {fmt.cost(cost)} per contact, a contact pays for itself only if it raises buying by at least {need_txt} "
                               f"({fmt.cost(cost)} ÷ {unit_note}). Each group against that line (real lift and its 95% range): "
                               + '; '.join(f"{g} {v:+.2f} (range {lo:+.2f} to {hi:+.2f}): "
                                           + ('above break-even, contacting pays' if lo > need * f_ else 'below break-even, contacting loses money'
                                              if hi < need * f_ else f"{'slightly above' if v > need * f_ else 'slightly below'} the line but its range "
                                              'includes it, so about break-even: contacting only breaks even')
                                           for g, v, lo, hi in zip(L.index, L.real_lift, L.low95, L.high95)) + '.'),
         ('fairness', analyst.plain(msg).replace('*', '')),
         ('assumptions', f'Assumed inputs on the Plan page: {unit_note}; {chan_txt}' + (f'; {offer_note}' if offer_note else '') + '.'),
         ('kpis', f"Plan page (measured on the untouched 20%, {fmt.count(P['n_test'])} customers): contact {P['rec_share']:.0%} of customers; "
                  f"extra profit {fmt.rs(M.loc[R, 'extra_vs_nobody'] * per)} per 1,000 customers vs contacting nobody; "
                  f"{'the recommended plan' if R != 'Nudge plan' else 'the Nudge plan'} earned {fmt.rs(abs(ru[0]) * per)} per 1,000 "
                  f"{'more' if ru[0] >= 0 else 'less'} than the usual approach (difference range {fmt.rs(ru[1] * per)} to {fmt.rs(ru[2] * per)}: "
                  f"{reliable(ru)}); the personalised plan earned {fmt.rs(abs(db[0]) * per)} per 1,000 {'more' if db[0] >= 0 else 'less'} than "
                  f"{P['blanket'].lower()} (difference range {fmt.rs(db[1] * per)} to {fmt.rs(db[2] * per)}: {reliable(db)})."),
         ('ladder', 'Lift ladder on the untouched 20% (real lift, ' + unit + '): ' +
                    ', '.join(f"{g} {v:+.2f} (range {lo:+.2f} to {hi:+.2f})" for g, v, lo, hi in zip(L.index, L.real_lift, L.low95, L.high95)) +
                    f'. Verdict: {ladder_words}.'),
         ('personas', 'Responder groups (thirds of the untouched 20%): ' + ' | '.join(
             f"{t}: real lift {lift_unit(P['personas'][t]['lift'])} (± {lift_unit(1.96 * P['personas'][t]['se']).lstrip('+')}); "
             + (f"in the plan {P['personas'][t]['contacted']:.0%} of this group contacted (= {P['personas'][t]['contacted'] * P['personas'][t]['share']:.0%} "
                f"of all customers); " if P['personalise'] else
                f"in the plan: {'nobody contacted' if P['blanket'] == 'Contact nobody' else 'contacted, like everyone'}; ")
             + 'traits: ' + '; '.join(P['personas'][t]['traits']) for t in ['High', 'Medium', 'Low'])),
         ('effects', f'Average effect of each option across ALL {fmt.count(len(df))} customers in the file (not only the untouched 20%), after costs: ' + '; '.join(
             f"{o} {plus(r['extra_value'])} per customer (range {fmt.rs(r['low95'])} to {fmt.rs(r['high95'])})" for o, r in P['effects'].iterrows()))]
    if sample and sample.get('truth'):
        F.append(('truth', f"Synthetic truth check on the untouched 20% (TRUE values, known only because the data are made up; not measured): ranking matches the true lift with rank correlation {spearmanr(gain, true_lift)[0]:.2f}; "
                           f"{found_top:.0%} of Nudge's top 17% are truly nudgeable (17% by chance); {found_bot:.0%} of the bottom 9% are truly "
                           f"loyal regulars (9% by chance); the plan captures {true_profit(contact) / best:.0%} of the best possible profit "
                           f"(usual approach {true_profit(usual_sel) / best:.0%}). TRUE profit (not measured) per 1,000 customers on the untouched 20%: "
                           + '; '.join(f"{q} {fmt.rs(v)}" for q, v in TT['true profit per 1,000'].items())
                           + f". The truth says the best of these plans is: {TT['true profit per 1,000'].idxmax()}."
                           + f" Why the untouched 20% is noisy: there, the measured average lift of the message was {fmt.pts(m_lift, 2)} while its "
                             f"true average lift was {fmt.pts(t_lift, 2)}; this is measurement noise, not a result to plan with."
                           if best > 0 else 'Synthetic truth check: no profitable contact exists.'))
    SOURCE = ({'synthetic': 'Synthetic X5-like sample (made-up data calibrated to X5)', 'hillstrom': 'Hillstrom sample (real, US e-mail test)'}
              .get(src['sample'], f"Your uploaded file ({src['name']})"))
    analyst.publish('plan', F, source=SOURCE)
except Exception as e:
    st.caption(f':material/info: The AI analyst could not read this page ({type(e).__name__}); everything else on the page works.')

# ---------------- 9. download ----------------
st.subheader('Download the target list')
tkey = ('target', value, cost)                   # scoring every row of the file is slow: once per setting, not on every click
if tkey not in memo:
    make = lambda: planner.target_list(res, prep, value, P['margin'])
    memo[tkey] = shared.get('extra', (repr(ss['plan']['sig']), 'target', value, cost), make) if src['sample'] else make()
T = memo[tkey].copy()
if not P['personalise']:
    T['in_plan'] = 'yes' if P['blanket'] != 'Contact nobody' else 'no'
    T['recommended_option'] = P['best_opt'] if P['blanket'] != 'Contact nobody' else prep['control']
st.dataframe(T.head(5), hide_index=True)
st.download_button('Download target list (CSV)', T.to_csv(index=False).encode(), 'nudge_target_list.csv', 'text/csv',
                   icon=':material/download:', type='primary')
st.caption(f"{fmt.count(len(T))} rows, {fmt.count((T.in_plan == 'yes').sum())} in the plan. Predicted extra profit is per customer, after contact cost."
           + ('' if P['personalise'] else ' The list follows the simple plan, not the personalised ranking.'))

with st.expander('How was this calculated?'):
    st.markdown(f"""
- **Two parts:** {fmt.count(P['n_choose'])} customers to learn from and to choose the plan (80%), {fmt.count(P['n_test'])} untouched
  until the end (20%). Every result above is measured on the untouched 20%, which played no part in any choice, so the winning plan's
  numbers are not flattered.{' Training used a random 2 lakh rows of your file.' if res['sampled'] else ''}
- **Honest scores:** the 80% is split into {P['folds']} parts by customer; each customer is scored by models trained on the other parts,
  so no customer is scored by a model that saw them.
- **Ranking:** {'three standard uplift learners (S, X and DR, as in Step 4) each rank the customers and the ranks are averaged' if P['ranker'] == 'ensemble' else 'the fast engine (one doubly robust model per option)'}.
  The ranking is turned into a predicted extra outcome per customer by matching the measured lift in each tenth of customers (the order
  of customers does not change).
- **No reliable signal:** if no option's ranking beats a random order on the honest scores (95% range of the Qini includes zero),
  Nudge does not personalise and says so.
- **Choosing the plan:** personalised plans (a customer gets their personal best option only when it beats the best-on-average option
  by a safety margin; several margins are tried) compete with the best simple plan (everyone, or nobody), all valued on the honest
  scores. The simple plan wins unless a personalised one earns more.
- **Final check:** if the untouched 20% shows the chosen personalised plan earning less than the simple plan, Nudge recommends the
  simple plan instead (a last yes/no gate, like a go/no-go check).
- **Usual approach:** a model of who buys when contacted (as in Step 5), contacting the same number of customers, most likely first.
- **Measured value of a plan:** customers whose random option matches the plan's choice are averaged, weighted by how likely that option
  was (inverse propensity weighting). 95% ranges: 200 bootstrap repeats, paired across plans.
- **Rupees:** {unit_note}, {chan_txt}{'; ' + offer_note if offer_note else ''} (assumptions you set above).
""")

# ---------------- 10. thorough mode ----------------
st.subheader('Thorough model check (optional)')
st.markdown('Repeats Step 4 of the project on your file: 5 uplift methods plus the S+X+DR ensemble, compared by 5-fold cross-validation, '
            'then the winner is scored once on the untouched 20% next to the fast engine. Takes about 30 seconds per option per 25,000 rows.')
if 'thorough_out' not in ss:
    if st.button('Run thorough check', icon=':material/science:'):
        with st.status('Comparing uplift methods...', expanded=True) as box:
            ss['thorough_out'] = thorough.run(prep, res, status=box.write)
            box.update(label='Thorough check done', state='complete', expanded=False)
        st.rerun()
else:
    for o, r in ss['thorough_out'].items():
        with st.container(border=True):
            g = r['gain_vs_fast']; lk = r['locked']
            win = lk.iloc[0]; proven = win.qini_low95 > 0
            st.markdown(f"**{o} vs {prep['control']}** · winner by cross-validation: **{r['winner']}** · {fmt.count(r['rows'])} build rows")
            a, b = st.columns([1.1, 1])
            cv = r['cv'].copy(); cv.columns = ['Qini', 'Qini spread', 'lift in top 10%', 'lift in top 30%']
            a.dataframe(cv.style.format('{:.4f}').highlight_max(subset=['Qini'], color='#EEF0FF'))
            lk2 = lk[['qini', 'qini_low95', 'qini_high95', 'top10_lift', 'top30_lift']].copy()
            lk2.columns = ['Qini (untouched 20%)', 'low 95%', 'high 95%', 'lift top 10%', 'lift top 30%']
            b.dataframe(lk2.style.format('{:.4f}'))
            if proven:
                b.success(f"The winner ranks customers better than random on unseen customers (range above zero). "
                          f"Versus the fast engine: {g[0]:+.4f} Qini (range {g[1]:+.4f} to {g[2]:+.4f}).", icon=':material/check_circle:')
            else:
                b.warning("On the untouched 20%, no method's ranking is proven better than random (the range includes zero). "
                          "Personalising by this option is not supported by your data.", icon=':material/warning:')
    st.caption('Qini: area between the model\'s gain curve and random ordering, per customer (higher = better; 0 = random). '
               'Lift in top k%: real extra outcome among the top k% the model ranks highest.')
