"""Nudge: the front door. Sets the look, lists the pages, and runs whichever page the visitor picked.
Run with:  streamlit run app.py   (from the app folder, inside app/.venv)"""
import streamlit as st

from lib import chat, ui

st.set_page_config(page_title='Nudge · campaign targeting engine', page_icon=':material/target:', layout='wide')
ui.apply_style()

pages = {
    '': [st.Page('views/home.py', title='Home', icon=':material/home:', default=True)],
    'Your campaign': [
        st.Page('views/plan.py', title='Plan my campaign', icon=':material/upload_file:'),
        st.Page('views/money.py', title='Money', icon=':material/currency_rupee:'),
        st.Page('views/prove.py', title='Prove it worked', icon=':material/verified:'),
    ],
    'About': [st.Page('views/built.py', title='How it was built', icon=':material/science:')],
}
page = st.navigation(pages)
KEYS = {'Home': 'home', 'Plan my campaign': 'plan', 'Money': 'money', 'Prove it worked': 'prove', 'How it was built': 'built'}
with st.container(key='phone_chat'):                 # phones: the sidebar is folded away, so offer the analyst here too
    phone_ask = st.button('Ask the AI analyst', icon=':material/forum:', key='phone_chat_btn', width='stretch')
if st.sidebar.button('Ask the AI analyst', icon=':material/forum:', type='primary', width='stretch') or phone_ask:
    try:
        chat.window(KEYS.get(page.title, 'home'))  # uses the numbers this page published when it was last drawn
    except Exception as e:                         # the AI analyst is optional: never break the page
        st.sidebar.caption(f':material/info: The AI analyst is unavailable right now ({type(e).__name__}).')
st.sidebar.caption('Questions about the numbers on screen, answered with citations.')
page.run()
