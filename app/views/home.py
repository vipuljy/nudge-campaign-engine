"""Home: what Nudge does in 10 seconds. Headline, 4 measured results, the 3-step flow, and where to start.
All numbers are calculated from app/results (exported by notebook 11), not typed in."""
import streamlit as st

from lib import analyst, fmt, ui, x5

S = x5.summary()
A = x5.meta()['assumptions']
MARGIN, WHATSAPP = A['profit_per_purchase_rs']['value'], A['channels_rs_per_contact']['WhatsApp']['value']


def action_buttons(where: str) -> None:
    """The three ways in, as equal full-width buttons; 'Plan my campaign' is the primary one."""
    b1, b2, b3 = st.columns(3)
    if b1.button('Plan my campaign', type='primary', icon=':material/upload_file:', width='stretch', key=f'plan_{where}'):
        st.switch_page('views/plan.py')
    with b2.popover('Try a sample', icon=':material/play_circle:', width='stretch'):
        if st.button('Synthetic X5-like (shows targeting)', key=f'syn_{where}', width='stretch', type='primary'):
            st.session_state['use_sample'] = 'synthetic'
            st.switch_page('views/plan.py')
        st.caption('2,00,000 made-up customers calibrated to X5, with known true responders: the clearest demo.')
        if st.button('Hillstrom e-mail test (real, US)', key=f'hill_{where}', width='stretch'):
            st.session_state['use_sample'] = 'hillstrom'
            st.switch_page('views/plan.py')
        st.caption('64,000 real customers: shows Nudge refusing a personalised plan that does not pay.')
    if b3.button('See the X5 money example', icon=':material/currency_rupee:', width='stretch', key=f'money_{where}'):
        st.switch_page('views/money.py')


st.markdown(
    '<div class="hero"><h1>Spend your campaign budget on customers who buy <i>because</i> you contacted them.</h1>'
    '<p>Upload the results of a randomised campaign test. Nudge tells you whom to contact, with which offer and channel, '
    'what it returns in rupees, and how to prove it worked. Every number is measured on customers the model never saw.</p></div>',
    unsafe_allow_html=True)
action_buttons('top')

st.write('')
st.caption('Results from public campaign datasets')

# ---- 4 key numbers ----
d = x5.budget_difference(MARGIN, WHATSAPP, 20_000)
t10 = S['top10']
cj = x5.table('step10_careful').set_index('control group')['effect %']
naive = S['top30_by_uplift']['rate_contacted'] * 30_000
fair = (S['top30_by_uplift']['rate_contacted'] - S['top30_by_uplift']['rate_held_back']) * 30_000
up, usual = round(d['a'].profit, -2), round(d['b'].profit, -2)
X5_SOURCE = 'X5 RetailHero, Russia · random SMS test'

ui.kpi_grid([
    {'label': '₹20,000 WhatsApp budget', 'badge': f'≈{up / usual:.0f}× more profit',
     'value': f'{fmt.rs(up)} <span class="vs">vs {fmt.rs(usual)}</span>',
     'note': 'profit: Nudge vs the usual likely-buyer list', 'source': X5_SOURCE, 'tags': ('measured', 'assumed')},
    {'label': 'Usual campaign reports', 'value': f'{naive / fair:.1f}×',
     'note': 'overstate what the campaign really caused', 'source': X5_SOURCE, 'tags': ('measured',)},
    {'label': 'Top 10% picked by Nudge', 'value': f'{S["top10_vs_average"]:.1f}×',
     'note': 'more extra buying than the average customer', 'source': X5_SOURCE, 'tags': ('measured',)},
    {'label': 'Without a random test', 'value': f'{fmt.signed(cj.max(), 1, "%")} <span class="vs">vs</span> {fmt.signed(cj.min(), 1, "%")}',
     'note': 'two careful analyses of one campaign: opposite answers',
     'source': 'Dunnhumby Complete Journey, US · company chose targets', 'tags': ('measured',)},
])

with st.expander('How were these calculated?'):
    st.markdown(f"""
- **Measured** means counted on a random test: customers who got the message vs look-alikes who were randomly held back,
  on customers locked away while the model was built (X5: {fmt.count(S['exam_customers'])} of {fmt.count(S['experiment_customers'])}). **Assumed** marks business inputs you can change on the Money page.
- **{fmt.rs(up)} vs {fmt.rs(usual)} (≈{up / usual:.0f}× more profit):** the same ₹20,000 WhatsApp budget per 1 lakh customers,
  at ₹{MARGIN:.0f} profit per extra purchase (₹1,000 basket × 15% margin) and ₹{WHATSAPP} per message.
  Nudge contacts the {fmt.count(d['a'].contacts)} customers with the highest predicted *extra* buying;
  the usual approach picks those most likely to buy (they mostly buy anyway) and does best stopping at {fmt.count(d['b'].contacts)}.
  Difference {fmt.rs(d['difference'])}, 95% range {fmt.rs(d['low95'])} to {fmt.rs(d['high95'])} (paired bootstrap).
- **{naive / fair:.1f}× overstated:** messaging the top 30% of 1 lakh customers, {fmt.pct(S['top30_by_uplift']['rate_contacted'], 1)} bought,
  so a usual report credits the campaign with {fmt.count(round(naive, -1))} buyers. But {fmt.pct(S['top30_by_uplift']['rate_held_back'], 1)}
  of randomly held-back look-alikes bought anyway: the campaign caused only {fmt.count(round(fair, -1))}.
- **{S['top10_vs_average']:.1f}×:** in the top 10% by Nudge's ranking, the message raised buying by
  {fmt.pts(t10['rate_contacted'] - t10['rate_held_back'])}, against {fmt.pts(S['exam_lift'])} across all customers.
- **{fmt.signed(cj.max(), 1, '%')} vs {fmt.signed(cj.min(), 1, '%')}:** Dunnhumby Complete Journey (US), where the company chose whom to target.
  Two matched difference-in-differences analyses, each passing its placebo check, disagree in sign. With a random test there is one
  answer (X5: {fmt.pts(S['lift'])}, 95% range {fmt.pts(S['lift_low95'])} to {fmt.pts(S['lift_high95'], 2)}). This is why Nudge starts from a random test.
""")

# ---- 3 steps ----
st.subheader('How it works')
s1, s2, s3 = st.columns(3)
with s1:
    ui.step_card(1, 'Upload a test', 'A CSV from a randomised campaign: which option each customer got (one is "nothing"), '
                 'whether they bought, and what you knew about them before.')
with s2:
    ui.step_card(2, 'Plan', 'Whom to contact and with which option, the best share and budget in rupees, '
                 'compared with contacting everyone and with the usual approach. Download the target list.')
with s3:
    ui.step_card(3, 'Prove', 'A fair report against a control group, the control size you need, '
                 'and alarms that tell you when the model is going stale.')

action_buttons('bottom')

st.write('')
st.markdown('<p class="small-muted">Rupee values are illustrative: X5 is Russian retail, translated with stated Indian assumptions '
            '(₹1,000 basket × 15% margin; channel prices from 2026 Indian vendors). Only aggregated results are shown; '
            'no customer rows from X5, Starbucks or Complete Journey are included in this app.</p>', unsafe_allow_html=True)

try:
    analyst.publish('home', [])
except Exception:                      # the AI analyst is optional
    pass
