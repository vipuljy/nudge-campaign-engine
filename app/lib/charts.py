"""Plotly charts in the app's colours, so every page's charts look alike."""
import plotly.graph_objects as go
import streamlit as st

from lib.ui import COLORS

def show(fig, width='stretch') -> None:
    """Draw a chart without Plotly's floating toolbar. Its title is written above it as text, so it wraps on a phone."""
    title = fig.layout.title.text
    if title:
        st.markdown(f'**{title}**'); fig.update_layout(title=None, margin=dict(t=10))
    st.plotly_chart(fig, width=width, config={'displayModeBar': False})


def _pad(values, share=0.22):
    """Axis range with room for the value labels written outside the bars."""
    v = [x for x in values if x == x]
    lo, hi = min(0, min(v)), max(0, max(v)); pad = (hi - lo) * share or 1
    return [lo - (pad if lo < 0 else 0), hi + (pad if hi > 0 else 0)]


BASE = dict(template='plotly_white', margin=dict(l=10, r=10, t=40, b=10), height=320,
            font=dict(family='sans-serif', size=13, color=COLORS['text']), showlegend=False)


def ladder(groups, values, low, high, unit: str, average: float = None, title: str = ''):
    """Real lift in the High / Medium / Low thirds, with 95% ranges. A working model shows a falling staircase."""
    fig = go.Figure(go.Bar(x=groups, y=values, marker_color=[COLORS['nudge'], '#818CF8', COLORS['usual']],
                           error_y=dict(type='data', symmetric=False, array=[h - v for h, v in zip(high, values)],
                                        arrayminus=[v - l for v, l in zip(values, low)], color='#64748B', thickness=1.2),
                           text=[f'{v:+.2f}' for v in values], textposition='outside', cliponaxis=False,
                           hovertemplate='%{x}: %{y:.2f} ' + unit + '<extra></extra>'))
    if average is not None:
        fig.add_hline(y=average, line_dash='dot', line_color='#64748B', annotation_text='average', annotation_position='top left')
    fig.add_hline(y=0, line_color='#CBD5E1')
    fig.update_layout(**BASE, title=title, yaxis_title=unit, yaxis_range=_pad(list(values) + list(high) + list(low) + ([average] if average else [])))
    return fig


def policy_bars(names, values, highlight: str, unit: str, title: str = ''):
    """Horizontal bars, one per policy; the recommended one in the accent colour."""
    colors = [COLORS['nudge'] if n == highlight else COLORS['usual'] for n in names]
    fig = go.Figure(go.Bar(y=names, x=values, orientation='h', marker_color=colors, text=[f'{v:,.0f}' for v in values],
                           textposition='outside', cliponaxis=False, hovertemplate='%{y}: %{x:,.0f} ' + unit + '<extra></extra>'))
    fig.add_vline(x=0, line_color='#CBD5E1')
    fig.update_layout(**{**BASE, 'height': 60 + 48 * len(names)}, title=title, xaxis_title=unit, yaxis=dict(autorange='reversed'),
                      xaxis_range=_pad(values, 0.3))
    return fig


LINE = {'uplift': COLORS['nudge'], 'nudge': COLORS['nudge'], 'plan': COLORS['nudge'], 'likely': '#F59E0B', 'usual': '#F59E0B', 'random': '#94A3B8'}
NAMES = {'uplift': 'Nudge (uplift)', 'nudge': 'Nudge (uplift)', 'plan': 'Your plan (no ranking)', 'likely': 'Usual approach (likely buyers)',
         'usual': 'Usual approach (likely buyers)', 'random': 'Random pick'}


def profit_curves(curves: dict, best_share: float, budget_share: float = None, scale: float = 1e5, unit: str = '₹ lakh'):
    """Profit (y) by share of customers contacted (x) for each ranking, with shaded 95% ranges; best point circled;
    dotted line where the budget runs out."""
    fig = go.Figure()
    for m, c in curves.items():
        x = c.share * 100
        if c.low95.notna().any():
            fig.add_trace(go.Scatter(x=list(x) + list(x[::-1]), y=list(c.high95 / scale) + list(c.low95[::-1] / scale), fill='toself',
                                     fillcolor=LINE[m], opacity=0.12, line=dict(width=0), hoverinfo='skip', showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=c.profit / scale, mode='lines', name=NAMES[m], line=dict(color=LINE[m], width=2.5 if m in ('uplift', 'nudge', 'plan') else 2,
                                 dash='dot' if m == 'random' else 'solid'),
                                 hovertemplate='%{x:.0f}% contacted: %{y:.2f} ' + unit + '<extra>' + NAMES[m] + '</extra>'))
    first = next(iter(curves.values())); b = first.loc[(first.share - best_share).abs().idxmin()]
    fig.add_trace(go.Scatter(x=[b.share * 100], y=[b.profit / scale], mode='markers', name='best share',
                             marker=dict(size=14, color='rgba(0,0,0,0)', line=dict(color=COLORS['nudge'], width=2.5)), hoverinfo='skip'))
    if budget_share is not None and budget_share < 1:
        fig.add_vline(x=budget_share * 100, line_dash='dash', line_color=COLORS['muted'],
                      annotation_text='budget runs out', annotation_position='top')
    fig.add_hline(y=0, line_color='#CBD5E1')
    fig.update_layout(**{**BASE, 'height': 380, 'showlegend': True}, legend=dict(orientation='h', y=-0.22),
                      xaxis_title='% of customers contacted (best first)', yaxis_title=f'profit, {unit}', title='Profit by how many you contact')
    return fig


def grouped_bars(categories, series: dict, unit: str, title: str = '', colors: dict = None, hlines=()):
    """Several bars per category (e.g. old plan / re-optimised / everyone per scenario)."""
    fig = go.Figure()
    for i, (name, vals) in enumerate(series.items()):
        fig.add_trace(go.Bar(name=name, x=categories, y=vals, marker_color=(colors or {}).get(name, [COLORS['nudge'], '#818CF8', COLORS['usual']][i % 3]),
                             hovertemplate='%{x}: %{y:,.2f} ' + unit + '<extra>' + name + '</extra>'))
    fig.add_hline(y=0, line_color='#94A3B8')
    for y, label, color in hlines:                                   # alarm lines, e.g. PSI 0.1 watch / 0.25 retrain
        fig.add_hline(y=y, line_dash='dash', line_color=color, annotation_text=label, annotation_position='top left')
    fig.update_layout(**{**BASE, 'height': 360, 'showlegend': True}, barmode='group', legend=dict(orientation='h', y=-0.25),
                      yaxis_title=unit, title=title)
    return fig
