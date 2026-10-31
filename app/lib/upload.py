"""Reading, checking and preparing a campaign-test CSV for the engine.

The engine needs one row per customer contact with:
  option  : which option the customer got, assigned at random; one value is the control ("nothing")
  outcome : what happened afterwards (bought yes/no, or an amount spent)
  measures: what was known about the customer BEFORE the contact
  id      : optional customer id
"""
import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from nudge_engine import check_balance

MAX_ROWS = 200_000          # training sample cap (the size of the X5 experiment)
MIN_PER_OPTION = 1_000      # below this, per-customer estimates get noisy
SAMPLES_DIR = Path(__file__).resolve().parent.parent / 'samples'

ARM_HINTS = ('segment', 'treatment', 'arm', 'offer', 'option', 'variant', 'group', 'campaign', 'channel_sent', 'message')
CONTROL_HINTS = ('no ', 'no_', 'none', 'control', 'nothing', 'holdout', 'hold out', 'not ')
OUTCOME_HINTS = ('target', 'conversion', 'converted', 'bought', 'purchase', 'buy', 'spend', 'revenue', 'sales', 'amount',
                 'outcome', 'response', 'redeemed', 'clicked', 'opened', 'visit')   # strongest first
ID_HINTS = ('id', 'customer', 'client', 'user', 'member', 'account')


def _separator(data: bytes) -> str:
    """Comma, semicolon (European Excel), tab or pipe: whichever appears most in the header line."""
    line = data[:65536].split(b'\n', 1)[0].decode('utf-8', 'ignore')
    counts = {s: line.count(s) for s in (',', ';', '\t', '|')}
    return max(counts, key=counts.get) if max(counts.values()) else ','


@st.cache_data(show_spinner=False)
def read_csv(data: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(data), sep=_separator(data), compression='infer', low_memory=False)


YES_NO = {'yes': 1, 'y': 1, 'true': 1, 'no': 0, 'n': 0, 'false': 0}


def to_number(s: pd.Series) -> pd.Series:
    """Outcome as a number: 1/0, True/False and yes/no text (any case) become 1/0; anything else unreadable becomes missing."""
    if pd.api.types.is_bool_dtype(s) or pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors='coerce')
    t = s.astype(str).str.strip().str.lower()
    return pd.to_numeric(t.map(YES_NO).where(t.isin(YES_NO), s), errors='coerce')


def _is_yes_no(s: pd.Series) -> bool:
    v = s.dropna()
    return (not pd.api.types.is_numeric_dtype(s)) and len(v) > 0 and set(v.astype(str).str.strip().str.lower()) <= set(YES_NO)


def _id_like(df: pd.DataFrame, c) -> bool:
    """A customer id or a row number: named like an id ("customer_id", "ID", "Unnamed: 0") with mostly distinct values.
    Never a customer measure."""
    n = str(c).lower().strip()
    named = (re.search(r'(^|[^a-z])id([^a-z]|$)', n) is not None or n in ('customer', 'client', 'user', 'member', 'account')
             or n.startswith('unnamed'))
    return named and df[c].nunique() >= 0.5 * max(len(df), 1)


# Two built-in samples. Each says which column is which, which channel to start with, and how to explain itself.
SAMPLES = {
    'hillstrom': {
        'name': 'Hillstrom sample', 'file': 'hillstorm_no_indices.csv.gz', 'channel': 'Email',
        'mapping': {'option': 'segment', 'control': 'No E-Mail', 'outcome': 'spend', 'id': None,
                    'features': ['recency', 'history', 'mens', 'womens', 'zip_code', 'newbie', 'channel'],   # as in Step 7
                    'labels': {'recency': 'months since last purchase', 'history': 'spend in the past year ($)',
                               'mens': "bought men's items in the past year", 'womens': "bought women's items in the past year",
                               'zip_code': 'area', 'newbie': 'new customer (past 12 months)', 'channel': 'bought by (phone / web / both)'}},
        'note': ("**Sample: Hillstrom e-mail test** (MineThatData, public, real). 64,000 US customers were randomly sent a men's e-mail, "
                 "a women's e-mail or nothing; outcome = spend in the next 2 weeks, in US dollars."),
        'per_unit': 95.0,
        'per_unit_note': 'RBI reference rate ₹94.94 per US$ on 23 Oct 2026 (FBIL, via CEIC), rounded',
        'per_unit_link': 'https://www.ceicdata.com/en/india/foreign-exchange-rate-reserve-bank-of-india/foreign-exchange-rate-rbi-reference-rate-us-dollars',
    },
    'synthetic': {
        'name': 'Synthetic X5-like sample', 'file': 'synthetic_x5_like.csv.gz', 'truth': 'synthetic_truth.csv.gz', 'channel': 'Custom', 'custom_cost': 5.0,
        'cost_note': '1-minute AI voice call, ~₹5 per minute (Edesy, 2026)',
        'mapping': {'option': 'option', 'control': 'No message', 'outcome': 'bought', 'id': 'customer_id',
                    'features': ['age', 'gender', 'card_days', 'bills_4m', 'spend_4m', 'promo_points_30d', 'days_since_bill'],
                    'labels': {'age': 'age', 'gender': 'gender', 'card_days': 'days since loyalty card was issued',
                               'bills_4m': 'bills, last 4 months', 'spend_4m': 'spend, last 4 months (₹)',
                               'promo_points_30d': 'promo points used, last 30 days', 'days_since_bill': 'days since last bill'}},
        'note': ("**Synthetic, calibrated to real X5 findings.** 2,00,000 made-up customers (the size of the X5 experiment) in a random message test (X5 used an SMS), built to match two "
                 "results of the project: (1) the personas from Step 5: nudgeable 17% (+6.4 pts), average 74% (+2.9 pts), loyal regulars 9% "
                 "(+1.2 pts), with 60% buying anyway and +3.3 pts on average; (2) the top 10% respond about 3.5x the average (+11.7 pts, "
                 "Step 5), because response also varies within each persona with recency and promo-point use. Because the truth is known, "
                 "the page checks how well Nudge finds the real responders. Starts with a 1-minute AI voice call (₹5), where choosing "
                 "whom to call matters."),
    },
}


@st.cache_data(show_spinner=False)
def load_sample(key: str) -> pd.DataFrame:
    return pd.read_csv(SAMPLES_DIR / SAMPLES[key]['file'])


@st.cache_data(show_spinner=False)
def load_truth(key: str) -> pd.DataFrame:
    return pd.read_csv(SAMPLES_DIR / SAMPLES[key]['truth'])


def humanize(col: str) -> str:
    """Plain-language version of a column name: orders_90d -> 'orders, last 90 days'."""
    t = re.sub(r'[_\-]+', ' ', str(col)).strip().lower()
    t = re.sub(r'\b(\d+)\s?d\b', r', last \1 days', t)
    t = re.sub(r'\b(\d+)\s?m\b', r', last \1 months', t)
    t = re.sub(r'\b(\d+)\s?w\b', r', last \1 weeks', t)
    for a, b in [(r'\bn\b', 'number of'), (r'\bnum\b', 'number of'), (r'\bcnt\b', 'count'), (r'\bavg\b', 'average'),
                 (r'\bpct\b', '%'), (r'\bamt\b', 'amount'), (r'\bqty\b', 'quantity')]:
        t = re.sub(a, b, t)
    return re.sub(r'\s+,', ',', re.sub(r'\s+', ' ', t)).strip(' ,')


def _looks_like(name: str, hints) -> bool:
    n = name.lower()
    return any(h in n for h in hints)


def guess_mapping(df: pd.DataFrame) -> dict:
    """First guess of which column is which; the user confirms it in dropdowns."""
    cols = list(df.columns)
    small = [c for c in cols if 2 <= df[c].nunique(dropna=True) <= 10]

    def control_value(c, strict=True):
        vals = [str(v) for v in df[c].dropna().unique()]
        return next((v for v in vals if _looks_like(v + ' ', CONTROL_HINTS) or (not strict and v in ('0', 'False'))), None)
    # options are usually text labels: prefer a text column holding a control-like value ("No E-Mail"), then an option-like name
    score = lambda c: (2 * (control_value(c) is not None) + _looks_like(c, ARM_HINTS)
                       + (not pd.api.types.is_numeric_dtype(df[c])) + 0.5 * (control_value(c, False) is not None)
                       + 0.5 * (c.lower() in ARM_HINTS) - 0.1 * df[c].nunique())     # exact names and few values win ties
    ranked = sorted(small, key=lambda c: -score(c))
    option = ranked[0] if ranked else cols[0]
    control = control_value(option, False)              # no control-like value: left empty, the user must choose one
    # outcome: numbers or yes/no text ("Purchased?" = Yes/No), named like an outcome, strongest hint first
    numeric = [c for c in cols if c != option and (pd.api.types.is_numeric_dtype(df[c]) or _is_yes_no(df[c]))]
    hinted = [(min(i for i, h in enumerate(OUTCOME_HINTS) if h in c.lower()), c) for c in numeric if _looks_like(c, OUTCOME_HINTS)]
    outcome = min(hinted)[1] if hinted else (numeric[-1] if numeric else None)
    ids = ([c for c in cols if df[c].is_unique and _looks_like(c, ID_HINTS)]
           or [c for c in cols if _id_like(df, c) and not str(c).lower().startswith('unnamed')])
    cid = ids[0] if ids else None                       # an id may repeat (a customer in the file twice)
    features = [c for c in cols if c not in (option, outcome, cid) and not _looks_like(c, OUTCOME_HINTS) and not _id_like(df, c)]
    return {'option': option, 'control': control, 'outcome': outcome, 'id': cid, 'features': features}


def outcome_kind(s: pd.Series) -> str:
    """'binary' (bought yes/no) or 'amount' (money or quantity)."""
    v = pd.to_numeric(s, errors='coerce').dropna().unique()
    return 'binary' if len(v) and set(np.unique(v)).issubset({0, 1}) else 'amount'


def validate(df: pd.DataFrame, m: dict) -> list:
    """Checks before training. Returns [(level, message)] with level 'error' (cannot train) or 'warning'."""
    out = []
    if len(df) == 0:
        return [('error', 'The file has column names but no rows of data. Export the file again with the customer rows.')]
    if df.shape[1] < 3:
        return [('error', f'The file was read as {df.shape[1]} column{"" if df.shape[1] == 1 else "s"} only. It needs at least an option, '
                          'an outcome and one customer measure, each in its own column. Check that it is a CSV '
                          '(values separated by commas or semicolons).')]
    if m['option'] is None or m['outcome'] is None:
        return [('error', 'Choose the option column and the outcome column.')]
    if m['option'] == m['outcome']:
        return [('error', 'The option column and the outcome column must be different.')]
    blank = df[m['option']].isna() | (df[m['option']].astype(str).str.strip() == '')
    if blank.all():
        return [('error', f'"{m["option"]}" is empty in every row. Choose the column that says which option each customer got.')]
    if blank.any():
        out.append(('warning', f'{int(blank.sum()):,} rows have no value in "{m["option"]}" (which option the customer got) '
                               'and will be left out.'))
    opt = df.loc[~blank, m['option']].astype(str)
    if opt.nunique() > 10:
        out.append(('error', f'"{m["option"]}" has {opt.nunique()} different values. The option column should hold a few options '
                             '(for example "SMS", "discount", "nothing"), not a measure.'))
    if m['control'] is None or str(m['control']) not in set(opt):
        vals = ', '.join(f'"{v}"' for v in opt.unique()[:6])
        out.append(('error', f'Choose which value of "{m["option"]}" is the control group (customers who got nothing). '
                             f'Its values: {vals}. If every customer got some option, '
                             'the file has no control group and nobody can tell what the campaign caused.'))
    elif not (_looks_like(str(m['control']) + ' ', CONTROL_HINTS) or str(m['control']) in ('0', 'False')):
        out.append(('warning', f'Make sure "{m["control"]}" really means customers got nothing. If every customer got some option, '
                               'there is no control group and nobody can tell what the campaign caused.'))
    if opt.nunique() < 2:
        out.append(('error', 'The option column needs at least two values: one option and the control.'))
    y = to_number(df[m['outcome']])
    bad = y.isna().mean()
    if bad == 1:
        out.append(('error', f'The outcome "{m["outcome"]}" is not numeric. Use 1/0 for bought yes/no, or an amount.'))
    elif bad > 0:
        out.append(('warning', f'{bad:.1%} of rows have no usable outcome and will be left out.'))
    if bad < 1 and y.dropna().nunique() == 1:
        v = y.dropna().iloc[0]
        out.append(('error', f'The outcome "{m["outcome"]}" is {v:g} for every customer'
                             + (' (nobody bought)' if v == 0 else ' (everybody bought)' if v == 1 else '')
                             + '. With no difference between customers, there is nothing to learn about what the campaign changed. '
                               'Check that this is the right column and the right period.'))
    if not m['features']:
        out.append(('error', 'Choose at least one customer measure (known before the contact).'))
    if m['id'] and m['id'] in m['features']:
        out.append(('error', 'The id column cannot also be a customer measure.'))
    if m['id']:
        dup = df[m['id']].duplicated(keep=False)
        if dup.any():
            out.append(('warning', f'{df.loc[dup, m["id"]].nunique():,} customers appear more than once ({int(dup.sum()):,} rows). '
                                   'That is fine if they were contacted more than once; Nudge keeps all rows of a customer '
                                   'in the same part when it tests itself. If they are copies, remove them first.'))
    id_meas = [c for c in m['features'] if _id_like(df, c)]
    if id_meas:
        out.append(('warning', f'{", ".join(id_meas)} look{"s" if len(id_meas) == 1 else ""} like an id or a row number, '
                               'not a customer measure; it can only add noise. Remove it from the measures.'))
    for v, n in opt.value_counts().items():
        if n < MIN_PER_OPTION:
            out.append(('warning', f'Only {n:,} customer{"" if n == 1 else "s"} got "{v}". Under about {MIN_PER_OPTION:,} per option, '
                                   'per-customer estimates are noisy; the ranges shown will be wide.'))
    if len(df) > MAX_ROWS:
        out.append(('warning', f'The file has {len(df):,} rows. Training uses a random {MAX_ROWS:,} of them to stay fast; '
                               'the download still scores every row.'))
    # measures named exactly like an outcome (or 'post_...') are probably measured after the contact; 'spend_4m' is history, not an outcome
    leak = [c for c in m['features'] if c.lower().strip() in OUTCOME_HINTS or c.lower().startswith(('post', 'after'))]
    if leak:
        out.append(('warning', f'{", ".join(leak)} look like outcomes. Measures must be known before the contact, '
                               'otherwise the model learns from the answer.'))
    return out


def prepare(df: pd.DataFrame, m: dict) -> dict:
    """Clean table for the engine: option as text, outcome numeric, measures numeric (text columns with up to
    20 values become yes/no columns; others are left out and reported)."""
    d = df.copy()
    blank = d[m['option']].isna() | (d[m['option']].astype(str).str.strip() == '')
    d['_option'] = d[m['option']].astype(str).astype(object)   # plain Python text: pandas' Arrow text is slow to loop over
    d['_y'] = to_number(d[m['outcome']])
    d = d[d._y.notna() & ~blank].reset_index(drop=True)        # rows without an option or an outcome are left out (validate says so)
    d['_id'] = d[m['id']].astype(str) if m['id'] else (d.index + 1).astype(str)
    feats, dropped, readable = [], [], {}
    for c in m['features']:                          # internal names m0, m1, ... (LightGBM rejects symbols in names)
        s = d[c]
        if pd.api.types.is_bool_dtype(s) or pd.api.types.is_numeric_dtype(s):
            k = f'm{len(feats)}'; d[k] = s.astype('float32'); feats.append(k); readable[k] = (c, None)
        elif s.nunique() <= 20:
            for v in s.dropna().unique():
                k = f'm{len(feats)}'; d[k] = (s == v).astype('float32'); feats.append(k); readable[k] = (c, v)
        else:
            dropped.append(c)
    bal = check_balance(d, feats, '_option', str(m['control'])).abs()
    names = {c: m.get('labels', {}).get(c, humanize(c)) for c in m['features']}
    columns = readable                                                          # original column names: to read new files
    readable = {k: (names[c], v) for k, (c, v) in columns.items()}             # shown to people: plain-language names
    return {'data': d, 'features': feats, 'readable': readable, 'columns': columns, 'dropped': dropped, 'kind': outcome_kind(d._y),
            'control': str(m['control']), 'options': [o for o in d._option.unique() if o != str(m['control'])],
            'balance': bal, 'max_gap': float(bal.max().max()) if bal.size else 0.0,
            'min_group': int(d._option.value_counts().min()), 'n_control': int((d._option == str(m['control'])).sum()),
            'worst': (label(readable, bal.max(axis=1).idxmax()) if bal.size else None)}


def label(readable: dict, k: str) -> str:
    col, val = readable[k]
    return col if val is None else f'{col} = {val}'


def fairness(gap: float, min_group: int, n_control: int) -> tuple:
    """Traffic light for the random-test check: the largest standardised difference between an option group and the control.
    Even a perfect random split shows small gaps by chance, about sqrt(1/n1 + 1/n0) for groups of n1 and n0 customers,
    so small files get wider thresholds (at least 0.05 amber / 0.10 red, the usual rule for large files)."""
    noise = np.sqrt(1 / max(min_group, 1) + 1 / max(n_control, 1))
    amber, red = max(0.05, 3 * noise), max(0.10, 4 * noise)
    if gap < amber:
        return 'green', 'The groups look alike on every measure, as a random test should.', amber
    if gap < red:
        return 'amber', 'Small differences between groups. Usable, but check how the options were assigned.', amber
    return 'red', 'The groups differ before the campaign, so options were probably not given at random.', amber


def encode_like(prep: dict, df: pd.DataFrame) -> tuple:
    """Encode a new customer file (e.g. this month's customers) exactly like the build data, for the drift check.
    Returns the encoded measures and the list of original columns that are missing."""
    out, missing = {}, []
    for k, (col, val) in prep['columns'].items():
        if col not in df.columns:
            missing.append(col); continue
        out[k] = (pd.to_numeric(df[col], errors='coerce') if val is None else (df[col].astype(str) == str(val)).astype('float32'))
    return pd.DataFrame(out), sorted(set(missing))
