"""Part A: synthetic campaign tests with a KNOWN true effect for every customer.

Each customer has 10 numeric measures (x0..x9) and 2 text measures (region, joined_via). Without contact about 30% buy.
2-arm: one option, "Message"; true lift +4 pts on average, SD about 4 pts, set by x0, x1, x2 (with a bend and a step), so about
       16% of customers are put off by the contact (negative true effect).
4-arm: three options, each helping different customers:
       SMS reminder      +3 pts average, set by x0, x1          (SMS ₹0.10 per contact)
       WhatsApp reminder +4 pts average, set by x1, x2, region  (₹1.02 per contact)
       Discount Rs20     +8 pts average, set by x2, x6, region  (₹20 paid by every buyer who got it; sent by SMS ₹0.10)
Revenue outcome: buyers spend a basket of about ₹500 (larger for high x7, lognormal noise); the options change WHETHER people
buy, not how much, so the true extra revenue = extra buying chance x expected basket.
Options are given at random with equal shares. Returns the customer file (what a company would upload) and the truth.
"""
import numpy as np
import pandas as pd

OPTIONS_4 = {'SMS reminder': {'contact': 0.10, 'reward': 0.0},
             'WhatsApp reminder': {'contact': 1.02, 'reward': 0.0},
             'Discount Rs20': {'contact': 0.10, 'reward': 20.0}}
CONTROL = 'No message'


def _std(z):
    return (z - z.mean()) / z.std()


def make(n, arms=2, outcome='binary', seed=0, null=False):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 10))
    region = rng.choice(['north', 'south', 'east'], n, p=[0.4, 0.35, 0.25])
    via = rng.choice(['web', 'app', 'store', 'phone'], n)
    p0 = 1 / (1 + np.exp(-(-0.95 + 0.55 * X[:, 3] + 0.35 * X[:, 4] - 0.25 * X[:, 5] + 0.25 * (via == 'app'))))
    basket = 500 * np.exp(0.25 * X[:, 7]) / np.exp(0.25 ** 2 / 2)              # expected basket, average ₹500

    if arms == 2:
        z = {'Message': _std(X[:, 0] + 0.7 * np.tanh(2 * X[:, 1]) + 0.6 * (X[:, 2] > 0.5))}
        tau = {'Message': 0.04 + 0.04 * z['Message']}
    else:
        z = {'SMS reminder': _std(X[:, 0] + 0.5 * X[:, 1]),
             'WhatsApp reminder': _std(X[:, 1] + 0.8 * np.tanh(2 * X[:, 2]) + 0.5 * (region == 'north')),
             'Discount Rs20': _std(X[:, 2] + 0.7 * X[:, 6] + 0.6 * (region == 'south'))}
        tau = {'SMS reminder': 0.03 + 0.03 * z['SMS reminder'],
               'WhatsApp reminder': 0.04 + 0.04 * z['WhatsApp reminder'],
               'Discount Rs20': 0.08 + 0.06 * z['Discount Rs20']}
    if null:
        tau = {o: np.zeros(n) for o in tau}
    opts = list(tau)
    arm = rng.choice([CONTROL] + opts, n)
    p1 = {o: np.clip(p0 + tau[o], 0.002, 0.998) for o in opts}
    p_arm = p0.copy()
    for o in opts:
        p_arm = np.where(arm == o, p1[o], p_arm)
    bought = (rng.random(n) < p_arm).astype(int)
    df = pd.DataFrame(X, columns=[f'x{i}' for i in range(10)]).round(4)
    df.insert(0, 'customer_id', [f'C{seed:03d}{i:07d}' for i in range(n)])
    df['region'], df['joined_via'], df['option'] = region, via, arm
    if outcome == 'binary':
        df['bought'] = bought
    else:
        df['revenue'] = np.round(bought * basket * rng.lognormal(-0.4 ** 2 / 2, 0.4, n), 2)
    truth = pd.DataFrame({'p0': p0, 'basket': basket})
    for o in opts:
        truth[f'p1_{o}'] = p1[o]
        truth[f'lift_{o}'] = p1[o] - p0                                       # true extra buying chance
    return df, truth, opts


def true_profit(truth, opts, outcome, value, costs):
    """True extra profit (₹ per customer, vs no contact) of giving each option; costs[o] = {'contact', 'reward'}.
    value: ₹ per extra purchase (binary) or the margin share of extra revenue (revenue)."""
    out = {}
    for o in opts:
        extra = truth[f'lift_{o}'] * (value if outcome == 'binary' else value * truth.basket)
        out[o] = extra - costs[o]['reward'] * truth[f'p1_{o}'] - costs[o]['contact']
    return pd.DataFrame(out)


def true_effect_engine_units(truth, opts, outcome, value, rewards, has_reward):
    """True effect of each option in the units the engine learns (before contact cost):
    no offers: extra purchases (binary) or extra revenue; with an offer: ₹ profit after the offer cost paid by buyers."""
    out = {}
    for o in opts:
        lift = truth[f'lift_{o}']
        unit = lift if outcome == 'binary' else lift * truth.basket
        out[o] = unit * value - rewards.get(o, 0.0) * truth[f'p1_{o}'] if has_reward else unit
    return pd.DataFrame(out)
