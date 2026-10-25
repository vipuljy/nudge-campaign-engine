"""Prove it worked: the fair report, the decision flip and control-group sizing (Step 9), for any buy rates.

Inputs are always the same few numbers measured on a random test:
    rc = outcome rate of customers who were contacted
    rh = outcome rate of look-alikes who were randomly held back
    se = standard error of (rc - rh)
"""
import numpy as np
import pandas as pd

from nudge_engine import min_detectable_lift, sample_size_per_group

CONTROL_SHARES = [0.01, 0.02, 0.05, 0.10, 0.20, 0.30]


def report(rc, rh, se, n, k, cost) -> dict:
    """A usual report credits every buyer who was contacted; a fair report subtracts those who would have bought anyway."""
    naive, fair = rc * n, (rc - rh) * n
    return {'naive': naive, 'fair': fair, 'fair_low': (rc - rh - 1.96 * se) * n, 'fair_high': (rc - rh + 1.96 * se) * n,
            'naive_profit': naive * k - n * cost, 'fair_profit': fair * k - n * cost,
            'fair_profit_low': (rc - rh - 1.96 * se) * n * k - n * cost, 'fair_profit_high': (rc - rh + 1.96 * se) * n * k - n * cost,
            'ratio': naive / fair if fair > 0 else np.inf}


def per_contact(rc, rh, se, k, cost) -> dict:
    """Profit per contact, as a usual report would claim it and as it really is (with 95% range)."""
    return {'naive': rc * k - cost, 'fair': (rc - rh) * k - cost,
            'low': (rc - rh - 1.96 * se) * k - cost, 'high': (rc - rh + 1.96 * se) * k - cost}


def control_table(base, p0, lift, k, cost) -> pd.DataFrame:
    """For each control share: how many held back, the smallest lift the campaign can detect (80% power), whether that catches
    a halving of the expected lift, and the profit given up by not contacting the control group."""
    rows = []
    for s in CONTROL_SHARES:
        nc = base * s
        mde = min_detectable_lift(base - nc, nc, p0)
        rows.append({'share': s, 'control': nc, 'mde': mde, 'catches_halving': mde <= lift / 2, 'cost': nc * (lift * k - cost)})
    return pd.DataFrame(rows)


def recommended_share(table: pd.DataFrame) -> float:
    """Smallest control share that still catches a halving of the lift (the Step 9 rule)."""
    ok = table[table.catches_halving]
    return float(ok.share.iloc[0]) if len(ok) else float(table.share.iloc[-1])


def pilot_size(p0, lift) -> int:
    """Customers per group (contacted and held back) to detect the expected lift 80% of the time."""
    return sample_size_per_group(p0, lift)
