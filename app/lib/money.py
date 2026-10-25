"""Rupee maths shared by the Money page's two modes (X5 example and your data).

A 'curve' is a table with one row per share of customers contacted (best first) and the columns
    share, contacts, profit, low95, high95
for one way of ranking customers. Everything here works on such tables, so both modes behave the same way.
"""
import numpy as np
import pandas as pd

from lib import x5

STEP8_SCENARIOS = [('Base', 1.0, 1.0, 1.0), ('Margin halved', 0.5, 1.0, 1.0), ('Contact cost doubled', 1.0, 2.0, 1.0),
                   ('Model 30% too optimistic', 1.0, 1.0, 0.7), ('All three at once', 0.5, 2.0, 0.7)]


def every(c: pd.DataFrame, step: float) -> pd.DataFrame:
    """Keep only shares on a grid (0.05 = 5% steps, as Step 8's profit curve)."""
    return c[np.isclose(c.share / step, np.round(c.share / step))]


def best(c: pd.DataFrame) -> pd.Series:
    return c.loc[c.profit.idxmax()]


def within_budget(c: pd.DataFrame, cost: float, budget: float) -> pd.Series:
    """Most profitable row the budget can pay for (contacts x cost <= budget)."""
    ok = c[c.contacts * cost <= budget + 1e-9]
    return ok.loc[ok.profit.idxmax()]


# ---------- X5 example (pre-computed, measured on the locked 40,008) ----------
def x5_curves(margin, cost, base, factor=1.0) -> dict:
    return {m: x5.profit_curve(m, margin, cost, factor, base) for m in x5.METHODS}


def x5_stress(margin, cost, base) -> pd.DataFrame:
    """Step 8 stress test: keep the plan chosen under the base assumptions, then make each assumption worse.
    Compare that old plan with contacting everyone and with re-running the optimiser under the new numbers."""
    u = x5.profit_curve('uplift', margin, cost, base=base)
    j = u.profit.idxmax(); rows = []
    for name, mf, cf, f in STEP8_SCENARIOS:
        new = f * u.extra_buyers * margin * mf - u.contacts * cost * cf
        rows.append({'scenario': name, 'old plan': new[j], 'contact everyone': new.iloc[-1],
                     're-optimised plan': new.max(), 're-optimised share': u.share[new.idxmax()]})
    return pd.DataFrame(rows).set_index('scenario'), u.share[j]


def x5_ladder(margin, channels: dict, base) -> pd.DataFrame:
    """For each channel: best share to contact (5% steps, as Step 8), profit there, and what targeting saves."""
    rows = []
    for ch, cost in channels.items():
        c = every(x5.profit_curve('uplift', margin, cost, base=base), 0.05); b = best(c); a = c.iloc[-1]
        rows.append({'channel': ch, '₹ per contact': cost, 'best share': b.share, 'profit at best': b.profit,
                     'profit if contact all': a.profit, 'saved by targeting': b.profit - a.profit,
                     'contact spend avoided': (a.contacts - b.contacts) * cost})
    return pd.DataFrame(rows).set_index('channel')


# ---------- your data (from the Plan page, measured on its untouched 20%) ----------
def user_curves(C: pd.DataFrame, scale: float, cost: float, base: float, factor: float = 1.0) -> dict:
    """C = planner.curves(): extra outcome per customer vs contacting nobody, in outcome units, before contact costs.
    Profit for a base of customers = base x (scale x extra x factor - cost x share)."""
    out = {}
    for m in ['nudge', 'usual']:
        f = lambda col: base * (scale * factor * C[col] - cost * C.share)
        out[m] = pd.DataFrame({'share': C.share, 'contacts': C.share * base, 'profit': f(m),
                               'low95': f(f'{m}_low'), 'high95': f(f'{m}_high')})
    allc = out['nudge'].profit.iloc[-1]                                # random pick: share x contacting everyone
    out['random'] = pd.DataFrame({'share': C.share, 'contacts': C.share * base, 'profit': C.share * allc,
                                  'low95': np.nan, 'high95': np.nan})
    return out


def user_difference(C, row_a, row_b, scale, cost, base) -> tuple:
    """Nudge minus the usual approach at their budget rows. When both contact the same share, the paired range is exact."""
    d = row_a.profit - row_b.profit
    if np.isclose(row_a.share, row_b.share):
        r = C.loc[np.isclose(C.share, row_a.share)].iloc[0]
        return d, base * scale * r.diff_low, base * scale * r.diff_high
    return d, np.nan, np.nan


def user_stress(C, scale, cost, base, has_offer: bool) -> tuple:
    u = user_curves(C, scale, cost, base)['nudge']; j = u.profit.idxmax(); rows = []
    for name, mf, cf, f in STEP8_SCENARIOS:
        if has_offer and mf != 1.0:
            continue                       # with offers, profit already includes the margin: halving it needs a rebuild
        new = base * (scale * mf * f * C.nudge - cost * cf * C.share)
        rows.append({'scenario': name, 'old plan': new[j], 'contact everyone': new.iloc[-1],
                     're-optimised plan': new.max(), 're-optimised share': C.share[new.idxmax()]})
    return pd.DataFrame(rows).set_index('scenario'), u.share[j]


def user_ladder(C, scale, channels: dict, base) -> pd.DataFrame:
    rows = []
    for ch, cost in channels.items():
        c = user_curves(C, scale, cost, base)['nudge']; b = best(c); a = c.iloc[-1]
        rows.append({'channel': ch, '₹ per contact': cost, 'best share': b.share, 'profit at best': b.profit,
                     'profit if contact all': a.profit, 'saved by targeting': b.profit - a.profit,
                     'contact spend avoided': (a.contacts - b.contacts) * cost})
    return pd.DataFrame(rows).set_index('channel')
