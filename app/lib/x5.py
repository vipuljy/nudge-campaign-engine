"""Pre-computed X5 results (exported by notebooks/11_export_results.ipynb) and the rupee maths on top of them.

The export saved, for every 1% of customers contacted (best first) and 3 rankings (uplift, likely-buyer, random),
how many contacts and how many extra buyers the locked exam measured, per 1 lakh customers.
Profit is then  extra buyers x profit per purchase - contacts x cost per contact,  so any margin or channel cost
can be tried instantly without retraining.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

RESULTS = Path(__file__).resolve().parent.parent / 'results'
METHODS = {'uplift': 'Nudge (uplift)', 'likely': 'Usual approach (likely buyers)', 'random': 'Random pick'}


@st.cache_data
def curves() -> pd.DataFrame:
    return pd.read_csv(RESULTS / 'x5_curves.csv')


@st.cache_data
def boots() -> dict:
    with np.load(RESULTS / 'x5_boots.npz') as z:
        return {k: z[k] for k in z.files}


@st.cache_data
def summary() -> dict:
    return json.loads((RESULTS / 'x5_summary.json').read_text(encoding='utf-8'))


@st.cache_data
def meta() -> dict:
    return json.loads((RESULTS / 'meta.json').read_text(encoding='utf-8'))


@st.cache_data
def table(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / 'tables' / f'{name}.csv')


def profit_curve(method: str, margin: float, cost: float, uplift_factor: float = 1.0, base: float = 100_000) -> pd.DataFrame:
    """Measured profit at each share contacted, with the 95% range from the Step 8 bootstrap, for a customer base of `base`.
    uplift_factor < 1 shrinks the measured extra buyers (stress test: 'the model is 30% too optimistic')."""
    f = base / 100_000
    c = curves()[lambda d: d.method == method].reset_index(drop=True).copy()
    c[['contacts', 'extra_buyers']] *= f
    c['profit'] = uplift_factor * c.extra_buyers * margin - c.contacts * cost
    b = boots()
    pb = (uplift_factor * b[f'{method}_extra'] * margin - b[f'{method}_contacts'] * cost) * f
    c['low95'], c['high95'] = np.percentile(pb, 2.5, axis=0), np.percentile(pb, 97.5, axis=0)
    return c


def budget_plan(method: str, margin: float, cost: float, budget: float, base: float = 100_000) -> pd.Series:
    """Most profitable share the budget can pay for (contacts x cost <= budget), as in Step 8."""
    c = profit_curve(method, margin, cost, base=base)
    ok = c[c.contacts * cost <= budget + 1e-9]
    return ok.loc[ok.profit.idxmax()]


def budget_difference(margin: float, cost: float, budget: float, a: str = 'uplift', b: str = 'likely', base: float = 100_000) -> dict:
    """Profit of plan a minus plan b for the same budget, with a 95% range from the paired bootstrap
    (both rankings re-scored on the same resampled customers)."""
    pa, pb = budget_plan(a, margin, cost, budget, base), budget_plan(b, margin, cost, budget, base)
    bt, f = boots(), base / 100_000
    da = bt[f'{a}_paired_extra'][:, int(pa.name)] * f * margin - pa.contacts * cost
    db = bt[f'{b}_paired_extra'][:, int(pb.name)] * f * margin - pb.contacts * cost
    lo, hi = np.percentile(da - db, [2.5, 97.5])
    return {'a': pa, 'b': pb, 'difference': pa.profit - pb.profit, 'low95': lo, 'high95': hi}


@st.cache_data
def printed() -> dict:
    """Results that exist only as printed sentences in notebooks 04-09, kept word for word."""
    return json.loads((RESULTS / 'printed_results.json').read_text(encoding='utf-8'))
