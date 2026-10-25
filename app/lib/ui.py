"""Shared building blocks so every page looks the same: colours, number cards, tags, the 'Do this' box."""
import streamlit as st

# One accent (indigo) for Nudge; grey for the usual approach; green / amber / red only for verdicts.
COLORS = {'nudge': '#4338CA', 'usual': '#94A3B8', 'random': '#CBD5E1', 'accent_soft': '#EEF0FF',
          'green': '#15803D', 'amber': '#B45309', 'red': '#B91C1C', 'text': '#1E1B3A', 'muted': '#5B5A72'}

CSS = f"""
<style>
.block-container {{ padding-top: 2.2rem; max-width: 1180px; }}
/* number cards: one grid, so all cards share the same height; 4 across on wide screens, 2x2 on laptops (under ~1,040 px of content), 1 on phones */
.kpi-grid {{ container-type: inline-size; margin-bottom: 0.6rem; }}
.kpi-grid .cards {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.9rem; }}
@container (max-width: 1040px) {{ .kpi-grid .cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
@container (max-width: 520px) {{ .kpi-grid .cards {{ grid-template-columns: minmax(0, 1fr); }} }}
.kpi {{ container-type: inline-size; background: {COLORS['accent_soft']}; border-radius: 0.8rem; padding: 1rem 1.1rem 0.85rem;
        display: flex; flex-direction: column; min-width: 0; }}
.kpi .top {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.3rem 0.4rem; min-height: 1.4rem; }}
.kpi .label {{ font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: {COLORS['muted']}; }}
.kpi .badge {{ font-size: 0.72rem; font-weight: 700; color: white; background: {COLORS['nudge']}; padding: 0.1rem 0.5rem;
               border-radius: 1rem; white-space: nowrap; }}
.kpi .value {{ font-size: min(1.9rem, 12.5cqi); font-weight: 700; color: {COLORS['nudge']}; line-height: 1.2;
               white-space: nowrap; margin: 0.35rem 0 0.25rem; }}
.kpi .value .vs {{ font-size: 0.6em; font-weight: 500; color: {COLORS['muted']}; }}
.kpi .note {{ font-size: 0.92rem; color: {COLORS['text']}; flex-grow: 1; }}
.kpi .source {{ font-size: 0.76rem; color: {COLORS['muted']}; margin-top: 0.6rem; overflow-wrap: anywhere; }}
.tag {{ display: inline-block; font-size: 0.66rem; font-weight: 600; letter-spacing: 0.02em; padding: 0.05rem 0.45rem;
        border-radius: 1rem; margin-right: 0.25rem; vertical-align: middle; white-space: nowrap; }}
.tag.measured {{ background: #DCFCE7; color: {COLORS['green']}; }}
.tag.assumed {{ background: #FEF3C7; color: {COLORS['amber']}; }}
.hero h1 {{ font-size: 2.3rem; line-height: 1.2; margin-bottom: 0.3rem; }}
.hero p {{ font-size: 1.1rem; color: {COLORS['muted']}; max-width: 760px; }}
.step {{ border: 1px solid #E2E4F0; border-radius: 0.8rem; padding: 0.9rem 1rem; height: 100%; }}
.step .num {{ display: inline-block; width: 1.7rem; height: 1.7rem; border-radius: 50%; background: {COLORS['nudge']}; color: white;
              text-align: center; font-weight: 700; line-height: 1.7rem; margin-right: 0.5rem; }}
.step .title {{ font-weight: 700; font-size: 1.05rem; }}
.step .body {{ color: {COLORS['muted']}; font-size: 0.92rem; margin-top: 0.4rem; }}
.decision {{ border-left: 5px solid {COLORS['nudge']}; background: {COLORS['accent_soft']}; padding: 0.9rem 1.1rem; border-radius: 0.4rem; }}
.decision b.head {{ color: {COLORS['nudge']}; }}
.pill {{ display: inline-block; font-size: 0.8rem; padding: 0.1rem 0.55rem; margin: 0.1rem; border-radius: 1rem;
         background: #F1F5F9; color: {COLORS['text']}; }}
/* the analyst button at the top of each page shows on phones only (on laptops it sits in the sidebar) */
@media (min-width: 768px) {{ .st-key-phone_chat {{ display: none; }} }}
.small-muted {{ font-size: 0.82rem; color: {COLORS['muted']}; }}
</style>
"""


def apply_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def tag(kind: str) -> str:
    """'measured' = from the held-out random test; 'assumed' = rests on an adjustable business assumption."""
    return f'<span class="tag {kind}">{kind.upper()}</span>'


def kpi_grid(cards: list) -> None:
    """A row of number cards with equal heights. Each card is a dict:
    label (short, on top) | value (the big number, one line) | note (one line of explanation)
    source (small line at the bottom) | tags ('measured' / 'assumed') | badge (optional small pill next to the label)."""
    html = []
    for c in cards:
        badge = f'<span class="badge">{c["badge"]}</span>' if c.get('badge') else ''
        tags = ''.join(tag(t) for t in c.get('tags', ()))
        html.append(f'<div class="kpi"><div class="top"><span class="label">{c["label"]}</span>{badge}</div>'
                    f'<div class="value">{c["value"]}</div><div class="note">{c["note"]}</div>'
                    f'<div class="source">{tags} {c.get("source", "")}</div></div>')
    st.markdown(f'<div class="kpi-grid"><div class="cards">{"".join(html)}</div></div>', unsafe_allow_html=True)


def step_card(num: int, title: str, body: str) -> None:
    st.markdown(f'<div class="step"><span class="num">{num}</span><span class="title">{title}</span>'
                f'<div class="body">{body}</div></div>', unsafe_allow_html=True)


def decision(text: str) -> None:
    """Every page ends in a decision: the 'Do this' box. The sentence is also kept for the AI analyst's fact sheet."""
    st.session_state['_decision'] = text
    st.markdown(f'<div class="decision"><b class="head">Do this:</b> {text}</div>', unsafe_allow_html=True)


def coming_soon(what: str) -> None:
    st.info(f'This page is being rebuilt. Coming next: {what}', icon=':material/construction:')
