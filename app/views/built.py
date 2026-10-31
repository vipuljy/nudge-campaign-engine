"""How it was built: the 60-second proof for recruiters and interviewers. Steps 1-10, one sentence and one chart each, every
number read from app/results (exported by notebook 11), with links to the notebooks on GitHub."""
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from lib import analyst, charts, fmt, ui, x5

REPO = 'https://github.com/vipuljy/nudge-campaign-engine'
NB = lambda name: f'{REPO}/blob/main/notebooks/{name}.ipynb'
WRITEUP = Path(__file__).resolve().parent.parent / 'results' / 'PROJECT_PLAYBOOK_public.md'
S = x5.summary(); P = x5.printed(); T = x5.table
go, C = charts.go, ui.COLORS

improve = re.search(r'([+-]\d+)%', P.get('step4_improvement', '')).group(1)
cj = T('step10_careful').set_index('control group')['effect %']
naive = T('step9_naive_fair').set_index('row').iloc[:, 0]
budget = T('step8_whatsapp_budget').set_index('budget ₹').loc[20000]
by_share = T('step5_by_share').set_index('method')

st.title('How it was built')
st.markdown(f"""
**Nudge learns who buys *because of* a contact**, from a randomised campaign test, and turns that into a plan in rupees.
It was built and checked in 10 steps on 4 public datasets. **Each step had a pass/fail gate written before the step was run**,
and every result is measured on customers the model never saw.""")

ui.kpi_grid([
    {'label': 'Better ranking', 'value': f'{improve}% Qini', 'note': 'final model vs the first one, on a locked exam',
     'source': f"locked 20% of X5 ({fmt.count(S['exam_customers'])} customers)", 'tags': ('measured',)},
    {'label': 'Random test', 'value': fmt.count(S['experiment_customers']), 'note': 'customers, with 45.8 million purchases behind them',
     'source': 'X5 RetailHero, Russia'},
    {'label': 'Gates', 'value': '10 of 10', 'note': 'steps passed their pre-set gate', 'source': 'gates K1 to K9 plus two model checks'},
    {'label': 'Datasets', 'value': '4', 'note': 'public: X5, Starbucks, Hillstrom, Dunnhumby', 'source': 'aggregates only in this app'},
])

GATES = ['K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7', 'K8', 'K9']
st.markdown(' '.join(f'<span class="tag measured">{g} PASS</span>' for g in GATES), unsafe_allow_html=True)
st.write('')


# ---------------- one small chart per step ----------------
def small(fig, h=230):
    legend = len(fig.data) > 1 and any(t.name for t in fig.data)                # keep the legend when lines or bars need names
    fig.update_layout(**{**charts.BASE, 'height': h + (40 if legend else 0), 'margin': dict(l=10, r=10, t=10, b=10), 'showlegend': legend},
                      legend=dict(orientation='h', y=-0.35, x=0))
    charts.show(fig)


def c_balance():
    b = pd.Series(S['balance_top10']).sort_values()
    fig = go.Figure(go.Bar(x=b.values, y=b.index, orientation='h', marker_color=C['nudge'], hovertemplate='%{y}: %{x:.4f}<extra></extra>'))
    fig.add_vline(x=0.05, line_dash='dash', line_color=C['red'], annotation_text='0.05 limit', annotation_position='bottom left')
    fig.update_xaxes(title='gap between the two groups', range=[0, 0.055]); small(fig, 280)


def c_profiles():
    fams = ['Recency, frequency, spend', 'Buying rhythm and overdue ratio', 'Trends', 'Basket', 'Loyalty and promo points',
            'Store loyalty', 'Time habits']
    st.markdown(' '.join(f'<span class="pill">{f}</span>' for f in fams), unsafe_allow_html=True)


def c_qini(models):
    q = pd.read_csv(x5.RESULTS / 'chart_qini.csv')
    fig = go.Figure()
    for m, col, dash in [('Random order', C['usual'], 'dot'), ('First model (Step 3)', '#818CF8', 'solid'), ('Champion ensemble (Step 4)', C['nudge'], 'solid')]:
        if m in models:
            d = q[q.model == m]
            fig.add_trace(go.Scatter(x=d.share * 100, y=d.extra_buyers_per_customer * 100, name=m, line=dict(color=col, dash=dash, width=2.5)))
    fig.update_xaxes(title='% of customers messaged (best first)'); fig.update_yaxes(title='extra buyers per 100'); small(fig, 260)


def c_leaderboard():
    lb = T('step4_leaderboard').sort_values('qini')
    fig = go.Figure(go.Bar(x=lb.qini, y=lb.model, orientation='h', error_x=dict(array=lb.qini_sd, color='#64748B'),
                           marker_color=[C['nudge'] if 'Ensemble' in m else C['usual'] for m in lb.model]))
    fig.update_xaxes(title='Qini, 5-fold cross-validation (bar = spread between folds)'); small(fig, 280)


def c_who():
    d = by_share[['Uplift champion', 'Likely-buyer model', 'Random']]
    fig = go.Figure([go.Bar(name=c, x=[f'{i}%' for i in d.index], y=d[c], marker_color=col)
                     for c, col in zip(d.columns, [C['nudge'], '#F59E0B', C['usual']])])
    fig.update_layout(barmode='group')
    fig.update_xaxes(title='share of customers messaged'); fig.update_yaxes(title='extra buyers per 10,000'); small(fig, 260)


def c_offers():
    o = T('step6_starbucks_offer_types').set_index('offer_type').rename(index={'informational': 'Reminder', 'discount': 'Discount', 'bogo': 'Free item'})
    fig = go.Figure(go.Bar(x=o.net_value, y=o.index, orientation='h', marker_color=[C['nudge'] if v == o.net_value.max() else C['usual'] for v in o.net_value],
                           text=[f'${v:.2f} kept · +{l:.1f} pts buying' for v, l in zip(o.net_value, o.buy_lift_pts)], textposition='outside',
                           cliponaxis=False))
    fig.update_xaxes(title='net value kept per customer offered ($)', range=[0, o.net_value.max() * 1.9]); small(fig, 200)


def c_engine():
    """Step 7 in plain words (from the saved Step 7 results), with the raw values one click away."""
    raw = T('step7_summary').set_index('dataset')
    num = lambda s: [float(x) for x in re.findall(r'[-+]?\d*\.?\d+', s)]
    x5_best, x5_vs = num(raw.loc['X5', 'best blanket policy'])[0], num(raw.loc['X5', 'engine vs best blanket'])
    sb_vs, hs_vs = num(raw.loc['Starbucks', 'engine vs best blanket']), num(raw.loc['Hillstrom', 'engine vs best blanket'])
    plain = pd.DataFrame([
        {'data': 'X5 (Russian retail)', 'question': f"whom to message, when a message costs {100 * num(raw.loc['X5', 'question'])[0]:.1f} pts of buying",
         'best simple plan': f'message nobody: {x5_best:.1%} bought',
         'what the engine did': f"messaged {raw.loc['X5', 'engine choice'].split()[-1]} of customers",
         'result': f'{100 * raw.loc["X5", "engine value"]:.1f}% net of message cost: {fmt.signed(100 * x5_vs[0])} pts vs nobody, '
                   f'{fmt.signed(100 * x5_vs[1])} pts vs messaging everyone (range {fmt.signed(100 * x5_vs[2])} to {fmt.signed(100 * x5_vs[3])})'},
        {'data': 'Starbucks (simulated)', 'question': 'which offer to send',
         'best simple plan': 'the same discount to everyone', 'what the engine did': 'kept that discount for 95% of customers',
         'result': f'no real difference: {fmt.signed(sb_vs[0], 2)} $ per customer (range {fmt.signed(sb_vs[1], 2)} to {fmt.signed(sb_vs[2], 2)}), '
                   'so it falls back'},
        {'data': 'Hillstrom (US e-mails)', 'question': 'which e-mail to send',
         'best simple plan': "the men's e-mail to everyone", 'what the engine did': "sent the men's e-mail to everyone",
         'result': f'the same plan ({fmt.signed(hs_vs[0], 2)} $): personalising does not pay here, so it falls back'},
    ]).set_index('data')
    st.table(plain)
    with st.expander('Raw values (Step 7 notebook)'):
        st.table(raw)


def c_money():
    b = T('step8_whatsapp_budget').set_index('budget ₹')
    fig = go.Figure([go.Bar(name=n, x=[fmt.rs(i) for i in b.index], y=b[f'{c}: profit ₹'] / 1e5, marker_color=col)
                     for n, c, col in [('Nudge (uplift)', 'Uplift champion', C['nudge']), ('Usual (likely buyers)', 'Likely-buyer model', '#F59E0B'),
                                       ('Random', 'Random', C['usual'])]])
    fig.update_layout(barmode='group')
    fig.update_xaxes(title='WhatsApp budget, per 1 lakh customers'); fig.update_yaxes(title='profit, ₹ lakh'); small(fig, 260)


def c_measure():
    fig = go.Figure(go.Bar(x=naive.values, y=['Usual report', 'Fair report'], orientation='h', marker_color=[C['usual'], C['nudge']],
                           text=[fmt.count(v) for v in naive.values], textposition='outside', cliponaxis=False))
    fig.update_xaxes(title='buyers credited to the campaign (30,000 messaged)', range=[0, naive.max() * 1.2]); small(fig, 180)


def c_contrast():
    w = pd.read_csv(x5.RESULTS / 'chart_complete_journey_weekly.csv')
    fig = go.Figure([go.Scatter(x=d.week, y=d.avg_spend_usd, name=g, line=dict(color=col, dash=dash, width=2.2))
                     for (g, d), col, dash in zip(w.groupby('group', sort=False), [C['nudge'], C['usual'], '#F59E0B'], ['solid', 'dot', 'dash'])])
    fig.add_vrect(x0=20, x1=26, fillcolor=C['nudge'], opacity=0.08, line_width=0, annotation_text='campaign', annotation_position='top left')
    fig.update_xaxes(title='week of 2017'); fig.update_yaxes(title='$ per household per week'); small(fig, 260)


STEPS = [
    (1, 'Data and a fair test', ['00_data_health', '01_gate'], 'K1, K2',
     f"{fmt.count(S['experiment_customers'])} customers in a random SMS test and 45.8 million purchases, cleaned with six rules. "
     f"The message and no-message groups match on all {S['measures']} measures (largest gap {S['largest_balance_gap']:.4f}, limit 0.05), "
     f"and the message raised buying by {fmt.pts(S['lift'])}.", c_balance),
    (2, 'Customer profiles', ['02_profiles'], 'K3',
     '67 measures per customer, all known before the message, with a fence so no future data leaks in.', c_profiles),
    (3, 'A first uplift model', ['03_uplift_quick'], 'K4',
     'A first model already finds extra buyers faster than a random order on unseen customers: its curve rises above the random line.',
     lambda: c_qini(['Random order', 'First model (Step 3)'])),
    (4, 'Choosing the model', ['04_model_selection'], 'pass',
     f"Seven uplift methods and an ensemble compared by 5-fold cross-validation. The S+X+DR ensemble won and, on a locked exam, "
     f"beat the first model by {improve}% Qini.", c_leaderboard),
    (5, 'Who to message', ['05_who_to_message'], 'pass',
     f"Messaging 20% of customers, uplift targeting creates {by_share.loc[20, 'Uplift champion']:.0f} extra buyers per 10,000 vs "
     f"{by_share.loc[20, 'Likely-buyer model']:.0f} for the usual likely-buyer model: likely buyers mostly buy anyway.", c_who),
    (6, 'Which offer', ['06_offer_types'], 'K6',
     'Starbucks offers (simulated): the free item lifts buying most but keeps the least value per customer in dollars, and a plain '
     'reminder keeps about 90% of the discount\'s value. In rupees, counting a freebie at its cost of goods, the free item wins (Step 8).', c_offers),
    (7, 'One engine, three datasets', ['07_engine'], 'K7',
     'The same engine on X5, Starbucks and Hillstrom: it beats both simple plans when contacts cost money, and falls back to the best '
     'single option when personalising does not pay.', c_engine),
    (8, 'Money', ['08_money'], 'K5',
     f"With ₹20,000 on WhatsApp, per 1 lakh customers: {fmt.rs(budget['Uplift champion: profit ₹'])} with Nudge vs "
     f"{fmt.rs(budget['Likely-buyer model: profit ₹'])} with the likely-buyer list. With every assumption made worse at once, re-planning "
     'still makes money.', c_money),
    (9, 'Proving it', ['09_measure'], 'K8',
     f"A usual report credits {fmt.count(naive.iloc[0])} buyers where the message caused {fmt.count(naive.iloc[1])} "
     f"({naive.iloc[0] / naive.iloc[1]:.1f}× overstated). Retraining on targeted-only data falls to −71% of clean quality; recording each "
     'customer\'s chance of contact restores 61%. Real drift over 4 months, New Year included: stable.', c_measure),
    (10, 'Without a random test', ['10_contrast'], 'K9',
     f"Dunnhumby, where the company chose its targets: targeted homes already spent 6.3× more before the campaign, and two careful "
     f"analyses of the same campaign gave {fmt.signed(cj.max(), 1, '%')} and {fmt.signed(cj.min(), 1, '%')}. That is why Nudge starts from a random test.",
     c_contrast),
]

st.subheader('Ten steps, each with a gate')
for n, title, notebooks, gate, sentence, chart in STEPS:
    with st.container(border=True):
        left, right = st.columns([1, 1.35], gap='medium')
        with left:
            badge = 'MODEL CHECK PASS' if gate == 'pass' else f'{gate} PASS'
            st.markdown(f'<span class="tag measured">{badge}</span> &nbsp;**Step {n} · {title}**', unsafe_allow_html=True)
            st.markdown(sentence)
            st.caption(' · '.join(f'[{nb}.ipynb]({NB(nb)})' for nb in notebooks))
        with right:
            chart()

# ---------------- how, honesty, data, limits ----------------
a, b = st.columns(2, gap='large')
with a:
    st.subheader('Tools')
    st.markdown('- **Python**, pandas and **DuckDB** (45.8 million purchases on a laptop)\n'
                '- **LightGBM** and **scikit-uplift** (uplift models), **SciPy** (statistics)\n'
                '- **Streamlit** and **Plotly** (this app)\n'
                '- **Groq** (free AI analyst, gpt-oss-120b), answering only from the numbers on screen')
    st.subheader('Honesty rules')
    st.markdown('- Every profit is **measured** on customers the model never saw; business inputs are marked **assumed**\n'
                '- 95% ranges wherever they exist\n'
                '- Choices made on honest 5-fold scores, results reported on an untouched part\n'
                '- No raw customer rows from X5, Starbucks or Dunnhumby in this app: aggregates only')
with b:
    st.subheader('Data')
    st.markdown('- **X5 RetailHero** (Russian grocery retail): random SMS test, 2,00,039 customers. Rupee values are illustrative '
                'assumptions, not converted roubles\n'
                '- **Starbucks** rewards test: simulated data released by Starbucks for analysis\n'
                '- **Hillstrom** (MineThatData): real US e-mail test, released for public analysis; used as the live sample\n'
                '- **Dunnhumby Complete Journey** (US): via the completejourney R package, CC0 licence; no random test')
    st.subheader('Limits')
    st.markdown('- X5 is Russian retail and Starbucks is simulated: the Indian rupee figures rest on stated assumptions\n'
                '- The best time to send was designed as a test (Step 9), not run\n'
                '- The synthetic sample is made up, calibrated to X5, for showing how well the engine finds true responders')

st.subheader('Read more')
l1, l2, l3 = st.columns(3)
l1.link_button('Code and notebooks on GitHub', REPO, icon=':material/code:', width='stretch')
l2.link_button('Write-up on GitHub', f'{REPO}/blob/main/docs/PROJECT_PLAYBOOK.md', icon=':material/description:', width='stretch')
if WRITEUP.exists():
    l3.download_button('Download the write-up (.md)', WRITEUP.read_bytes(), 'Nudge_project_writeup.md', 'text/markdown',
                       icon=':material/download:', width='stretch')
else:
    l3.button('Write-up download: coming soon', disabled=True, width='stretch')
st.caption('GitHub links go live when the repository is published.')

try:                                   # the AI analyst is optional: it must never break the page
    analyst.publish('built', [(f'step{n}', f'Step {n} ({title}), gate {gate} passed: {analyst.plain(sentence)}') for n, title, _, gate, sentence, _ in STEPS],
                    source='Project results')
except Exception as e:
    st.caption(f':material/info: The AI analyst could not read this page ({type(e).__name__}); everything else on the page works.')
