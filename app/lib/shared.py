"""Work shared by every visitor on this server, for the built-in samples only.

Why: building a plan, its download list and its profit curves is CPU-heavy, and the free cloud slows down (throttles) apps that use a
lot of CPU. A built-in sample gives the same result for every visitor with the same settings, so it is computed once and reused.
Uploaded files are never shared: they stay in the visitor's own session.
"""
import threading

import streamlit as st

KEEP = {'plan': 2, 'extra': 16}          # trained plans are large (models + data); read-outs are small


@st.cache_resource(show_spinner=False)
def _store() -> dict:
    return {'guard': threading.Lock(), 'locks': {}, 'items': {'plan': {}, 'extra': {}}}


def get(kind: str, key, compute):
    """The shared result for this key; computed here (one visitor at a time) only if nobody has computed it yet."""
    s = _store()
    with s['guard']:
        lock = s['locks'].setdefault((kind, key), threading.Lock())
    with lock:                            # a second visitor waits for the first one instead of computing again
        items = s['items'][kind]
        if key not in items:
            items[key] = compute()
            while len(items) > KEEP[kind]:    # bounded memory: the oldest settings go first
                items.pop(next(iter(items)))
        return items[key]
