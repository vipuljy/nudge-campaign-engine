"""Makes the SYNTHETIC sample: a made-up random message test (X5 used an SMS) whose customers behave like the real X5 findings (Step 1 and Step 5).
Because we wrote the truth ourselves, the app can check how well the engine finds the customers who really respond.

Calibrated to the project's X5 results:
    buy rate without a message ~60%, average lift from the SMS +3.3 pts
    personas: nudgeable 17% (+6.4 pts), average 74% (+2.9 pts), loyal regular 9% (+1.2 pts)
    what they look like (Step 5 medians): nudgeable = older (59), newer card (193 days), use promo points (44%);
    loyal regulars = many bills and high spend, buy anyway.
    the top 10% of customers respond ~3.5x the average (+11.7 pts in Step 5), spread driven by recency and promo-point use.
Files: synthetic_x5_like.csv.gz (what a company would upload) and synthetic_truth.csv.gz (true persona and true uplift per
customer; never shown to the engine). Run:  python samples/make_synthetic.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

N, SEED = 200_000, 2026          # same size as the X5 experiment (200,039)
HERE = Path(__file__).resolve().parent
PERSONAS = {          # share, true lift (pts), buy rate without message
    'Nudgeable': (0.17, 6.4, 0.50),
    'Average': (0.74, 2.9, 0.60),
    'Loyal regular': (0.09, 1.2, 0.85),
}

rng = np.random.default_rng(SEED)
persona = rng.choice(list(PERSONAS), N, p=[v[0] for v in PERSONAS.values()])
P = pd.Series(persona)
pick = lambda d: P.map(d).values

# measures known before the SMS: each persona has its own typical values, with wide overlap (as in real data)
age = np.clip(rng.normal(pick({'Nudgeable': 58, 'Average': 45, 'Loyal regular': 47}), 11), 18, 90).round()
card_days = np.clip(rng.lognormal(np.log(pick({'Nudgeable': 200, 'Average': 520, 'Loyal regular': 700})), 0.6), 5, 2500).round()
bills_4m = rng.poisson(pick({'Nudgeable': 13, 'Average': 14, 'Loyal regular': 30}))
spend_4m = (bills_4m * rng.lognormal(np.log(pick({'Nudgeable': 350, 'Average': 420, 'Loyal regular': 450})), 0.35)).round()
uses_promo = rng.random(N) < pick({'Nudgeable': 0.44, 'Average': 0.13, 'Loyal regular': 0.10})
promo_points_30d = np.where(uses_promo, rng.gamma(2.0, 12.0, N), 0).round()
days_since_bill = np.clip(rng.exponential(pick({'Nudgeable': 9, 'Average': 7, 'Loyal regular': 3})), 0, 120).round()
gender = rng.choice(['F', 'M', 'U'], N, p=[0.48, 0.32, 0.20])

# true uplift: the persona's average lift, spread WITHIN each persona by recency and promo-point use (a positive multiplier),
# so that, as in real X5, the most responsive 10% respond about 3.5x the average. Rescaled so each persona hits its target exactly.
z = np.tanh((days_since_bill - 7) / 7) + np.tanh((promo_points_30d - 10) / 15)
z = (z - z.mean()) / z.std()
true_lift = pick({k: v[1] / 100 for k, v in PERSONAS.items()}) * np.exp(0.68 * z)
for k, v in PERSONAS.items():
    m = persona == k
    true_lift[m] *= (v[1] / 100) / true_lift[m].mean()
base = np.clip(pick({k: v[2] for k, v in PERSONAS.items()}) + 0.004 * (bills_4m - bills_4m.mean()), 0.05, 0.95)

sms = rng.random(N) < 0.5                                          # the random test: half get the message
bought = (rng.random(N) < np.clip(base + sms * true_lift, 0, 1)).astype(int)

ids = [f'S{i:06d}' for i in range(N)]
pd.DataFrame({'customer_id': ids, 'option': np.where(sms, 'Message', 'No message'), 'bought': bought, 'age': age.astype(int),
              'gender': gender, 'card_days': card_days.astype(int), 'bills_4m': bills_4m, 'spend_4m': spend_4m.astype(int),
              'promo_points_30d': promo_points_30d.astype(int), 'days_since_bill': days_since_bill.astype(int)}
             ).to_csv(HERE / 'synthetic_x5_like.csv.gz', index=False)
pd.DataFrame({'customer_id': ids, 'true_persona': persona, 'true_lift': true_lift.round(5)}).to_csv(HERE / 'synthetic_truth.csv.gz', index=False)

# calibration check
print(f'buy rate without message {bought[~sms].mean():.1%} | with message {bought[sms].mean():.1%} | lift {100 * (bought[sms].mean() - bought[~sms].mean()):+.2f} pts')
for k in PERSONAS:
    m = persona == k
    print(f'{k:14s} {m.mean():5.1%} of customers | true lift {100 * true_lift[m].mean():+.2f} pts | '
          f'measured lift {100 * (bought[m & sms].mean() - bought[m & ~sms].mean()):+.2f} pts')
top = np.sort(true_lift)[-N // 10:].mean()
print(f'true top 10%: +{100 * top:.1f} pts = {top / true_lift.mean():.1f}x the average')
