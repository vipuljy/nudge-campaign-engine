"""Prove it worked: report the campaign fairly (contacted vs randomly held back), size the control group, and keep proving it
(the Step 9 playbook with its evidence and alarms). Ends with a summary to paste for the boss."""
import numpy as np
import pandas as pd
import streamlit as st

from lib import analyst, charts, fmt, prove, ui, upload, x5
from nudge_engine import drift_report

A = x5.meta()['assumptions']
CH = {k: v['value'] for k, v in A['channels_rs_per_contact'].items()}
S = x5.summary()
ss = st.session_state
plus = lambda v: ('+' if v >= 0 else '') + fmt.rs(v)

st.title('Prove it worked')
st.caption('What the campaign really caused, how big a control group you need, and how to keep proving it month after month.')

has_plan = 'plan' in ss and 'current' in ss['plan']
mode = st.segmented_control('Results from', ['X5 example', 'Your data'], default='Your data' if has_plan else 'X5 example',
                            key='prove_mode') or 'X5 example'
if mode == 'Your data' and not has_plan:
    st.info('Build a plan first on the Plan page, then come back here.', icon=':material/info:')
    st.page_link('views/plan.py', label='Go to Plan my campaign', icon=':material/upload_file:')
    st.stop()
X5_MODE = mode == 'X5 example'


def rates(df, ctrl):
    t, c = df[df._option != ctrl]._y.astype(float), df[df._option == ctrl]._y.astype(float)
    return t.mean(), c.mean(), np.sqrt(t.var() / len(t) + c.var() / len(c))


def weeks(w: int) -> str:
    return f'{w} week' if w == 1 else f'{w} weeks'


def per_contact_txt(name: str, cost: float) -> str:
    """'WhatsApp at ₹1.02 per contact', but a label that already holds its cost ('contacts at ₹5') is not repeated."""
    return name if '₹' in name else f'{name} at {fmt.cost(cost)} per contact'


def hold_txt(c):
    """Holding back costs profit, unless an average contact earns less than its own cost."""
    return f'costs about {fmt.rs(c)}' if c >= 0 else f'saves about {fmt.rs(-c)} (an average contact earns less than its cost)'


# ================= 1. the fair report =================
st.subheader('1 · Report the campaign fairly')
st.markdown('A usual report credits the campaign with **every** customer who bought after being contacted. Many of them would have '
            'bought anyway. A fair report subtracts what randomly held-back look-alikes did.')
if X5_MODE:
    groups = {'Top 30% by Nudge (Step 9)': S['top30_by_uplift'], 'Top half by Nudge': S['top_half'], 'Bottom half by Nudge': S['bottom_half']}
    c1, c2, c3, c4 = st.columns(4)
    gname = c1.selectbox('Customers contacted', list(groups))
    g = groups[gname]
    n = c2.number_input('How many were contacted', 1_000, 10_000_000, int(round(g['share'] * 100_000, -3)), 1_000)
    k = c3.number_input('Profit per extra purchase (₹)', 1.0, 100_000.0, float(A['profit_per_purchase_rs']['value']), 10.0)
    chan = c4.selectbox('Channel', list(CH), index=1)
    cost = CH[chan]; binary = True
    rc, rh, se = g['rate_contacted'], g['rate_held_back'], g['se_lift']
    what = f"{gname.replace(' (Step 9)', '')}, via {chan}"
    source = 'X5 RetailHero, locked 40,008 customers'
else:
    res, prep, cur = ss['plan']['res'], ss['plan']['prep'], ss['plan']['current']
    P, te, ctrl = cur['P'], res['test'], prep['control']
    binary, k, cost = prep['kind'] == 'binary', cur['value'], cur['cost']
    chan = cur['channel'] if cur['channel'] != 'Custom' else f'contacts at {fmt.cost(cost)}'
    if P['recommended'] == 'Contact nobody':
        st.info('Your plan is to contact nobody, so there is no campaign to report. Change the channel or offer on the Plan page.',
                icon=':material/info:')
        st.stop()
    mask = (P['rec'] != ctrl) if P['personalise'] else np.ones(len(te), bool)
    rc, rh, se = rates(te[mask], ctrl)
    n = int(round(P['rec_share'] * len(prep['data'])))
    what = 'the customers in your Nudge plan' if P['personalise'] else f"everyone, with {P['best_opt']}"
    source = f"{ss['plan']['source']}, untouched 20% ({fmt.count(len(te))} customers)"
    st.caption(f"Your plan: contact {fmt.count(n)} customers ({what}); {cur['unit_note']}; {cur.get('chan_txt', chan)}.")

R = prove.report(rc, rh, se, n, k, cost)
if binary:
    cards = [{'label': 'Usual report claims', 'value': f"{fmt.count(round(R['naive'], -1))} buyers", 'note': 'everyone who bought after being contacted',
              'source': f"{fmt.pct(rc, 1)} of those contacted bought", 'tags': ('measured',)},
             {'label': 'The campaign caused', 'value': f"{fmt.count(round(R['fair'], -1))} buyers", 'note': 'beyond what held-back look-alikes did',
              'source': f"range {fmt.count(R['fair_low'])} to {fmt.count(R['fair_high'])}; {fmt.pct(rh, 1)} of held-back bought anyway", 'tags': ('measured',)}]
else:
    cards = [{'label': 'Usual report claims', 'value': fmt.rs(rc * n * k), 'note': 'profit on all spend after contact', 'source': '', 'tags': ('measured',)},
             {'label': 'The campaign caused', 'value': fmt.rs((rc - rh) * n * k), 'note': 'profit beyond held-back look-alikes',
              'source': f"range {fmt.rs((rc - rh - 1.96 * se) * n * k)} to {fmt.rs((rc - rh + 1.96 * se) * n * k)}", 'tags': ('measured',)}]
cards += [{'label': 'Overstated by', 'value': f"{R['ratio']:.1f}×" if np.isfinite(R['ratio']) else 'all of it',
           'note': 'how much a usual report exaggerates', 'source': source, 'tags': ('measured',)},
          {'label': 'Real profit', 'value': fmt.rs(R['fair_profit']), 'note': f"after contact costs; a usual report says {fmt.rs(R['naive_profit'])}",
           'source': f"range {fmt.rs(R['fair_profit_low'])} to {fmt.rs(R['fair_profit_high'])}", 'tags': ('measured', 'assumed')}]
ui.kpi_grid(cards)

st.markdown('**When the usual report changes the decision.** Profit per contact, as a usual report would claim it and as it really is:')
if X5_MODE:
    flip_chan = st.selectbox('Channel for this comparison', list(CH), index=3, key='flip_chan')
    fc = CH[flip_chan]
    flip = {'Top half (high uplift)': prove.per_contact(S['top_half']['rate_contacted'], S['top_half']['rate_held_back'], S['top_half']['se_lift'], k, fc),
            'Bottom half (low uplift)': prove.per_contact(S['bottom_half']['rate_contacted'], S['bottom_half']['rate_held_back'], S['bottom_half']['se_lift'], k, fc)}
    low_name = 'Bottom half (low uplift)'
else:
    flip_chan, fc = chan, cost
    flip = {f'{t} responders (third)': prove.per_contact(*rates(te[P['tiers'] == t], ctrl), k, fc) for t in ['High', 'Low']}
    low_name = 'Low responders (third)'
F = pd.DataFrame(flip).T
st.dataframe(pd.DataFrame({'usual report says': F.naive.map(lambda v: fmt.inr(v, 2)), 'really earns': F.fair.map(lambda v: fmt.inr(v, 2)),
                           'range': [f'{fmt.inr(l, 2)} to {fmt.inr(h, 2)}' for l, h in zip(F.low, F.high)]}), width='stretch')
lo = flip[low_name]
verdict = 'a loss' if lo['high'] < 0 else 'break-even at best' if lo['low'] <= 0 else 'much less than claimed'
st.markdown(f"Contacting the **{low_name.lower()}** via {flip_chan} looks like **{fmt.inr(lo['naive'], 2)} profit per contact**; it really earns "
            f"**{fmt.inr(lo['fair'], 2)}** (range {fmt.inr(lo['low'], 2)} to {fmt.inr(lo['high'], 2)}): {verdict}. "
            'Trusting the usual report, a company would scale up a campaign that does not pay.')

# ================= 2. control group =================
st.subheader('2 · How big a control group?')
st.markdown('Hold back a random share of the customers you would contact. Too small, and real changes hide in the noise; '
            'too big, and you give up profit. The rule from Step 9: the smallest share that still spots the lift halving.')
if X5_MODE or not binary:
    p0_def, lift_def = S['buy_rate_held_back'], S['lift']
    if not X5_MODE:
        st.caption('Your outcome is an amount, and this calculator works with buy rates, so it starts from the X5 values. Set your own.')
else:
    d = prep['data']; p0_def = d[d._option == ctrl]._y.mean(); lift_def = d[d._option != ctrl]._y.mean() - p0_def
d1, d2, d3, d4 = st.columns(4)
base = d1.number_input('Customers per campaign', 1_000, 100_000_000, 100_000 if X5_MODE else max(1_000, n), 10_000)
p0 = d2.number_input('Buy rate without contact (%)', 0.1, 99.9, round(100 * p0_def, 1), 0.5) / 100
lift = d3.number_input('Expected lift (pts)', 0.1, 50.0, round(100 * max(lift_def, 0.001), 2), 0.1) / 100
weekly = d4.number_input('Customers contacted per week', 100, 10_000_000, 10_000, 1_000)
CT = prove.control_table(base, p0, lift, k, cost)
rec_share = prove.recommended_share(CT)
share = st.select_slider('Control share', options=prove.CONTROL_SHARES, value=rec_share, format_func=lambda s: f'{s:.0%}')
row = CT.set_index('share').loc[share]
ui.kpi_grid([
    {'label': 'Hold back', 'value': fmt.count(row.control), 'note': f'customers ({share:.0%}) each campaign',
     'source': f'recommended: {rec_share:.0%}', 'badge': 'recommended' if share == rec_share else ''},
    {'label': 'Smallest lift it can spot', 'value': fmt.pts(row.mde, 2, sign=False), 'note': '80% of the time, at 95% confidence',
     'source': f'expected lift {fmt.pts(lift, 2, sign=False)}'},
    {'label': 'Catches the lift halving?', 'value': 'Yes' if row.catches_halving else 'No',
     'note': f'needs to spot {fmt.pts(lift / 2, 2, sign=False)} or less', 'source': 'Step 9 rule'},
    {'label': 'Cost of holding back' if row.cost >= 0 else 'Holding back saves', 'value': fmt.rs(abs(row.cost)),
     'note': 'profit given up by not contacting them' if row.cost >= 0 else 'an average contact earns less than its cost',
     'source': f'₹{k:,.0f} per purchase, {fmt.cost(cost)} per contact', 'tags': ('assumed',)},
])
mcol, pcol = st.columns([1.4, 1])
with mcol:
    shares = np.linspace(0.005, 0.3, 60)
    mde_curve = [100 * prove.min_detectable_lift(base * (1 - s), base * s, p0) for s in shares]
    fig = charts.go.Figure(charts.go.Scatter(x=shares * 100, y=mde_curve, mode='lines', line=dict(color=ui.COLORS['nudge'], width=2.5),
                                             hovertemplate='%{x:.1f}% held back: spots %{y:.2f} pts<extra></extra>'))
    fig.add_hline(y=100 * lift / 2, line_dash='dash', line_color=ui.COLORS['muted'], annotation_text='half the expected lift', annotation_position='top right')
    fig.add_vline(x=share * 100, line_dash='dot', line_color=ui.COLORS['nudge'])
    fig.update_layout(**charts.BASE, title='Smallest lift you can spot, by control size', xaxis_title='control group, % of customers',
                      yaxis_title='pts', yaxis_range=[0, max(5, 1.2 * 100 * lift)])
    charts.show(fig, width='stretch')
with pcol:
    pilot = prove.pilot_size(p0, lift)
    st.markdown(f"**Running a first pilot?** To detect a {fmt.pts(lift, 2, sign=False)} lift you need **{fmt.count(pilot)} customers in each group** "
                f"(contacted and held back): {fmt.count(2 * pilot)} in total, about **{weeks(int(np.ceil(2 * pilot / weekly)))}** at "
                f"{fmt.count(weekly)} contacts a week.")
    st.caption('Checked in Step 9: ' + x5.printed().get('step9_formula_vs_simulation', ''))
ui.decision(f"Hold back a random <b>{rec_share:.0%}</b> ({fmt.count(base * rec_share)} of {fmt.count(base)}) on every campaign, and report "
            f"contacted vs held back. It spots a {fmt.pts(CT.set_index('share').loc[rec_share].mde, 2, sign=False)} change and "
            f"{hold_txt(CT.set_index('share').loc[rec_share].cost)} per campaign.")

# ================= 3. keep proving it =================
st.subheader('3 · Keep proving it')
st.caption('The Step 9 playbook. Tick what you already do (ticks are only for this session).')
PLAYBOOK = [  # full text from notebook 09
    ('Permanent control group', 'Hold back a random 10% (bases near 1 lakh) or 2% (near 10 lakh) every campaign.', 'Proves the profit; catches a halving of lift.'),
    ('Explore and record', 'Targeting keeps ~20% randomness and records each customer chance (or a random slice of ~30,000+).',
     'Clean data to retrain; targeted-only data makes the model worse than random.'),
    ('Report fairly', 'Always contacted vs control: extra buyers, extra profit, 95% range.', 'Naive reports overstate ~9x and can make a losing campaign look profitable.'),
    ('Drift alarm', 'Monthly PSI on every customer measure vs the build period.', 'Amber 0.1-0.25 watch; red over 0.25 retrain; festive months shift behaviour.'),
    ('Lift-ladder alarm', 'Each campaign: real lift in top / middle / bottom thirds.', 'Top third under 1.5x average or out of order: retrain.'),
    ('Retrain', 'Quarterly on exploration data (weighted by recorded chance), or at once on a red alarm.', 'Re-run the Step 4 model check before switching.'),
    ('Send-time test', 'Once: control / morning / evening / when due, ~10-17k per group.', 'Adds the best time to send.'),
]
done = 0
for i, (what_, how, why) in enumerate(PLAYBOOK):
    with st.container(border=True):
        tick, body = st.columns([0.06, 0.94])
        done += tick.checkbox(what_, key=f'pb_{i}', label_visibility='collapsed')
        body.markdown(f'**{what_}.** {how} *Why:* {why}')
        if what_ == 'Explore and record':
            with body.expander('Evidence (Step 9)'):
                ex = x5.table('step9_exploration').set_index('training data'); rc_ = x5.table('step9_recorded_chance').set_index('row')
                names = ['Clean random test', 'Targeted only (top 30% messaged)', 'Random slice 5%', 'Random slice 10%', 'Random slice 20%',
                         'Random slice 30%', 'Random slice 50%']
                vals = list(ex['% of clean-test quality']) + list(rc_['% of clean-test quality'].iloc[:2])
                charts.show(charts.policy_bars(names + ['Targeted, chance ignored', 'Targeted, chance recorded and used'], vals,
                                                   'Targeted, chance recorded and used', '% of clean-test model quality',
                                                   'Retraining after a targeted campaign'), width='stretch')
                st.caption(x5.printed().get('step9_targeted_only_cost', ''))
        if what_ == 'Drift alarm':
            with body.expander('Evidence (Step 9)' if X5_MODE else 'Check this month\'s customers', expanded=not X5_MODE):
                if X5_MODE:
                    D = x5.table('step9_drift').set_index('row')
                    charts.show(charts.grouped_bars(list(D.index), {c: D[c] for c in D.columns}, 'PSI vs build period',
                                                        'Real drift over 4 months, New Year included',
                                                        hlines=[(0.1, 'watch', ui.COLORS['amber']), (0.25, 'retrain', ui.COLORS['red'])]), width='stretch')
                    st.caption(f'Largest PSI {D.values.max():.3f}: green, stable. ' + x5.printed().get('step9_drift_alarm_calibration', ''))
                else:
                    f = st.file_uploader("Upload this month's customers (same measure columns; option and outcome not needed)", type=['csv', 'gz'], key='drift_file')
                    if f is not None:
                        new, missing = upload.encode_like(prep, upload.read_csv(f.getvalue()))
                        if missing:
                            st.error(f"These measures are missing from the file: {', '.join(missing)}.", icon=':material/error:')
                        else:
                            DR = drift_report(res['build'], new, list(new.columns))
                            DR.index = [upload.label(prep['readable'], i) for i in DR.index]
                            worst = DR.psi.max(); light = 'red' if worst > 0.25 else 'amber' if worst > 0.1 else 'green'
                            {'green': st.success, 'amber': st.warning, 'red': st.error}[light](
                                f"**{ {'green': 'Stable', 'amber': 'Watch', 'red': 'Retrain'}[light] }.** Largest PSI {worst:.3f} on *{DR.psi.idxmax()}* "
                                "(under 0.1 stable, 0.1-0.25 watch, over 0.25 retrain).")
                            st.dataframe(DR.head(10).style.format({'psi': '{:.3f}'}), width='stretch')
                            ss['plan']['drift'] = (light, worst)
        if what_ == 'Lift-ladder alarm':
            with body.expander('Evidence' + (' (Step 9)' if X5_MODE else ': your plan')):
                if X5_MODE:
                    L = x5.table('step9_lift_ladder').set_index('third')['real lift (pts)']
                    vals, labels, avg = L.values[::-1], ['Top third', 'Middle third', 'Bottom third'], 100 * S['lift']
                    charts.show(charts.ladder(labels, list(vals), list(vals), list(vals), 'pts of buying', 1.5 * avg,
                                                  'Lift ladder (dotted line: alarm at 1.5x the average)'), width='stretch')
                    ok = vals[0] >= 1.5 * avg and vals[0] > vals[1] > vals[2]
                else:
                    L = P['ladder']; unit = 'pts of buying' if binary else '₹ per customer'
                    avg = (prep['data'][prep['data']._option != ctrl]._y.mean() - prep['data'][prep['data']._option == ctrl]._y.mean()) * (100 if binary else k)
                    charts.show(charts.ladder(list(L.index), L.real_lift.tolist(), L.low95.tolist(), L.high95.tolist(), unit, 1.5 * avg,
                                                  'Lift ladder (dotted line: alarm at 1.5x the average)'), width='stretch')
                    vals = L.real_lift.values; ok = vals[0] >= 1.5 * avg and vals[0] > vals[1] > vals[2]
                st.markdown('✅ Healthy: the top third responds most and clears the alarm line.' if ok else
                            '⚠️ Alarm: the top third is under 1.5× the average or the ladder is out of order. Investigate and retrain.')
        if what_ == 'Send-time test':
            with body.expander('How many customers (Step 9)'):
                st.dataframe(x5.table('step9_send_time').set_index('difference between send times to detect (pts)'), width='stretch')
st.progress(done / len(PLAYBOOK), text=f'{done} of {len(PLAYBOOK)} practices in place')

# ================= 4. summary for the boss =================
st.subheader('Copy summary for my boss')
if X5_MODE:
    L = x5.table('step9_lift_ladder').set_index('third')['real lift (pts)']
    lad_vals = list(L.values[::-1]); lad_ok = bool(lad_vals[0] >= 1.5 * 100 * S['lift'] and lad_vals[0] > lad_vals[1] > lad_vals[2])
    drift_txt = f"customer behaviour stable over 4 months (largest drift {x5.table('step9_drift').set_index('row').values.max():.3f}, green)"
else:
    L = P['ladder'].real_lift; lad_vals = list(np.round(L.values, 2)); lad_ok = bool(L['High'] > L['Medium'] > L['Low'])
    dl = ss['plan'].get('drift')
    drift_txt = (f"customer behaviour {'stable' if dl[0] == 'green' else 'shifting: watch' if dl[0] == 'amber' else 'shifted: retrain'} "
                 f"(largest drift {dl[1]:.3f}, {dl[0]})") if dl else "drift not checked yet (upload this month's customers above)"
unit_l = 'pts' if binary else '₹'
caused = (f"{fmt.count(round(R['fair'], -1))} extra buyers" if binary else 'extra sales') + f" and {fmt.rs(R['fair_profit'])} extra profit after contact costs"
claimed = (f"{fmt.count(round(R['naive'], -1))} buyers and " if binary else '') + fmt.rs(R['naive_profit'])
rec_row = CT.set_index('share').loc[rec_share]
summary = '\n'.join([
    f"1. What we did: contacted {fmt.count(n)} customers ({what}), chosen by Nudge, and randomly held back look-alikes as a control group.",
    f"2. What it caused: {caused} (95% range {fmt.rs(R['fair_profit_low'])} to {fmt.rs(R['fair_profit_high'])}). "
    f"A usual report would have claimed {claimed}" + (f", {R['ratio']:.1f}× too much." if np.isfinite(R['ratio']) else '.'),
    f"3. Control group: hold back {rec_share:.0%} ({fmt.count(base * rec_share)} of {fmt.count(base)}) on every campaign; it spots a "
    f"{fmt.pts(rec_row.mde, 2, sign=False)} change and {hold_txt(rec_row.cost)} per campaign.",
    f"4. Model health: real lift by group (top / middle / bottom) {' / '.join(f'{v:.2f}' for v in lad_vals)} {unit_l}, "
    f"{'in order' if lad_ok else 'OUT OF ORDER'}; {drift_txt}.",
    "5. Next: keep the control group on every campaign, keep a random exploration slice, and retrain quarterly or as soon as an alarm turns red."
    if lad_ok else "5. Next: investigate and retrain before the next campaign (re-run the model check), and keep the control group meanwhile.",
])
st.code(summary, language=None, wrap_lines=True)
st.caption(f'Copy with the button at the top right of the box. Numbers measured on: {source}; rupee values rest on your assumptions above.')

# ---------------- facts for the AI analyst ----------------
try:                                   # the AI analyst is optional: it must never break the page
    SOURCE = 'X5 example (pre-computed, Russian retail)' if X5_MODE else ss['plan']['source']
    analyst.publish('prove', [
        ('channel', f"Channel on the Prove page: {per_contact_txt(chan, cost)} for the fair report; "
                    f"the decision-flip table uses {per_contact_txt(flip_chan, fc)}."),
        ('fair_report', f"Prove page ({'X5 example' if X5_MODE else 'your data'}), contacting {fmt.count(n)} customers ({what}): "
                        + (f"a usual report claims {fmt.count(round(R['naive'], -1))} buyers, the campaign caused {fmt.count(round(R['fair'], -1))} "
                           f"(range {fmt.count(R['fair_low'])} to {fmt.count(R['fair_high'])}); " if binary else '')
                        + f"overstated {R['ratio']:.1f}×; real profit {fmt.rs(R['fair_profit'])} (range {fmt.rs(R['fair_profit_low'])} to "
                        f"{fmt.rs(R['fair_profit_high'])}) vs {fmt.rs(R['naive_profit'])} claimed. Measured."),
        ('flip', f'Decision flip via {flip_chan}: ' + '; '.join(f"{g}: usual report says {fmt.inr(r['naive'], 2)} per contact, really "
                                                           f"{fmt.inr(r['fair'], 2)} (range {fmt.inr(r['low'], 2)} to {fmt.inr(r['high'], 2)})" for g, r in flip.items())),
        ('control_group', f"Control group (recommended): hold back {rec_share:.0%} of the customers contacted ({fmt.count(base * rec_share)} of "
                          f"{fmt.count(base)}) on every campaign. Smallest change in lift this control group can detect: "
                          f"{fmt.pts(CT.set_index('share').loc[rec_share].mde, 2, sign=False)}. Holding back {hold_txt(CT.set_index('share').loc[rec_share].cost)} "
                          f"per campaign. Inputs: buy rate without contact {fmt.pct(p0, 1)}; expected lift from the campaign {fmt.pts(lift, 2, sign=False)}. "
                          f"A first pilot needs {fmt.count(pilot)} customers per group (contacted and held back) to detect the expected "
                          f"{fmt.pts(lift, 2, sign=False)} lift."),
        ('ladder', f"Lift ladder (top / middle / bottom third): {' / '.join(f'{v:.2f}' for v in lad_vals)} {unit_l}, "
                   f"{'in order' if lad_ok else 'out of order'}. Alarm if the top third is under 1.5× the average or the order breaks."),
        ('drift', drift_txt[0].upper() + drift_txt[1:] + '. PSI under 0.1 is stable, 0.1-0.25 watch, over 0.25 retrain.'),
        ('boss_summary', 'Summary for the boss: ' + ' '.join(summary.splitlines())),
    ], source=SOURCE)
except Exception as e:
    st.caption(f':material/info: The AI analyst could not read this page ({type(e).__name__}); everything else on the page works.')
