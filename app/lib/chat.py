"""The AI analyst's chat window (opened from the sidebar on every page)."""
import streamlit as st

from lib import analyst

ss = st.session_state


def _ask(question: str, page: str) -> None:
    if not question.strip():
        return
    try:
        r = analyst.answer(question.strip(), page)
    except Exception as e:                                  # never break the page: say so and carry on
        r = {'text': "Sorry, I couldn't answer that just now. The page's numbers are unaffected; please try again.",
             'facts': [], 'unverified': [], 'claims': [], 'how': f'error ({type(e).__name__})'}
    ss.setdefault('analyst_chat', []).append({'q': question.strip(), 'a': r['text'], **r})


def _chip(page: str) -> None:
    """A starter question was picked: answer it, then clear the pick so it can be asked again."""
    q = ss.get(f'chips_{page}')
    if q:
        _ask(q, page)
    ss[f'chips_{page}'] = None


def _md(text: str) -> str:
    return text.replace('$', '\\$')                   # Streamlit reads $...$ as a maths formula


def _plain(text: str) -> str:
    """A fact shown exactly as written: characters Markdown would act on (lists, bold, tables, links, maths) are escaped."""
    return ''.join('\\' + ch if ch in '\\`*_{}[]<>#+-|!$~' else ch for ch in text)


@st.dialog('Ask the AI analyst', width='large')
def window(page: str) -> None:
    s = analyst.status()
    line = {'ai': f"AI answers (gpt-oss-120b via Groq, free) · {s.get('left')} of {analyst.PER_VISITOR} questions left this visit",
            'own key': 'AI answers with your own Groq key (this visit only)',
            'rules': f"Rule-based answers: {s.get('why', '')}. Add a key below for free-form questions."}[s['mode']]
    st.caption(line + ' · Answers use only the numbers on this page and the project results, and cite them.')

    st.pills('Try a question', analyst.STARTERS.get(page, []), key=f'chips_{page}', on_change=_chip, args=(page,),
             label_visibility='collapsed')                       # chips wrap onto new lines on narrow screens

    with st.form('ask', clear_on_submit=True, border=False):
        a, b = st.columns([5, 1])
        q = a.text_input('Your question', placeholder='e.g. I have ₹50,000, what should I do?', label_visibility='collapsed')
        if b.form_submit_button('Ask', type='primary', width='stretch'):
            with st.spinner('Thinking...'):
                _ask(q, page)

    for h in reversed(ss.get('analyst_chat', [])[-6:]):
        with st.container(border=True):
            st.markdown(f"**You:** {_md(h['q'])}")
            st.markdown(_md(h['a']))
            for c in h.get('claims', []):
                st.warning(f"Claim check: the answer {c}. Treat that part with care.", icon=':material/fact_check:')
            if h['unverified']:
                st.warning(f"Not found on screen: {', '.join(h['unverified'])}. It may be a calculation or a mistake; check before using it.",
                           icon=':material/warning:')
            if h['facts']:
                with st.expander(f"Numbers used ({len(h['facts'])})"):
                    for f in h['facts']:                       # one paragraph per fact: nothing can turn into an empty bullet
                        st.markdown(f"**{f['id']}** · {_plain(f['text'])}")
            st.caption(h['how'])

    c1, c2 = st.columns([3, 1])
    with c1.expander('Use your own Groq key (optional)'):
        k = st.text_input('Groq API key', type='password', value=ss.get('own_groq_key') or '',
                          help='Used only for this visit, never saved. Free at console.groq.com.')
        ss['own_groq_key'] = (k or '').strip() or None
    if c2.button('Clear chat', width='stretch'):
        ss['analyst_chat'] = []
        st.rerun(scope='fragment')
