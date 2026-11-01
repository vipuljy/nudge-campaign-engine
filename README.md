# Nudge: campaign targeting engine

**Contact the customers who buy *because of* your message, not the ones who would buy anyway.**

Companies spend on SMS, WhatsApp, calls, discounts and cashback, but much of it goes to customers who would buy anyway, and campaign
reports take credit for those sales. Nudge learns from one **randomised campaign test** who responds *because of* a contact (uplift
modelling), then decides whom to contact, with which option, for what budget in rupees, and proves the result against a control group.

- **Live app:** [uplift-engine.streamlit.app](https://uplift-engine.streamlit.app/): try *Plan my campaign* with a built-in sample, or upload your own test
- **Full write-up:** [`docs/PROJECT_PLAYBOOK.md`](docs/PROJECT_PLAYBOOK.md) · **Validation:** [`VALIDATION_REPORT_v2.md`](VALIDATION_REPORT_v2.md)

## Results at a glance
| What | Result |
|---|---|
| Effect of the message (X5 retail, 2 lakh customers, random test) | +3.3 pts of buying (95% range +2.9 to +3.8) |
| Best model vs first model (locked exam) | +27% Qini; top 10% respond 3.5x the average |
| Uplift vs the usual "likely buyer" list (20% contacted) | 177 vs 15 extra buyers per 10,000 |
| Rs20,000 WhatsApp budget per 1 lakh customers | Rs2.44 lakh extra profit with Nudge vs Rs3,300 with a likely-buyer list |
| A normal campaign report | overstates impact 8.6x |
| Without a random test (Dunnhumby) | two careful methods give +10.7% and -6.5% for the same campaign |

## Validation: does it work on any company's data?
Ten pass marks were written down **before** testing (`VALIDATION_PLAN.md`) and never changed. Tested on made-up data where the true
answer is known, 4 public uplift datasets (Criteo, Lenta, MegaFon, Hillstrom) against 5 methods including econml's causal forest,
16 messy upload files, and repeated runs.

| | Run 1 (app as it was) | Run 2 (improved engine, fresh data) |
|---|---|---|
| Tests passed | 3 of 10 | **9 of 10** |
| Plan profit vs the perfect plan, 50k-row files | 32-67% | **78-85%** |
| Plan profit vs the perfect plan, 2 lakh-row files | 85-86% | **91-95%** |
| "No effect" data: says "don't personalise" | 17 of 20 | **19 of 20** (20 of 20 with the final check) |
| Public data: share of the best method's Qini | 2 of 4 datasets within 10% | **3 of 4** (95-97%) |
| Bad uploads | 2 crashes | **0 crashes**, a plain message for every bad file |

The one failure is Lenta: its effect is tiny (+0.75 pts) and the "no reliable signal" rule refused to target, missing a weak real
gain. The same rule is why the app is right on 20 of 20 no-effect runs. Details, ranges and every number: `VALIDATION_REPORT.md`
(Run 1) and `VALIDATION_REPORT_v2.md` (Run 2 and the re-check); code in [`validation/`](validation).

## How it works
1. **Check the test is fair:** every customer measure must look alike between groups (a red light if options were not random).
2. **Rank customers by uplift:** three standard uplift learners (S, X and DR, LightGBM) vote; every customer is scored by models that never saw them (5-fold cross-fitting).
3. **Calibrate:** turn the ranking into an honest uplift size per customer (isotonic, order unchanged).
4. **No reliable signal?** If the ranking does not beat a random order on unseen customers, say so and use the simple plan.
5. **Choose the plan:** personalised plans vs "contact everyone" vs "contact nobody", valued in rupees after contact and offer costs (inverse propensity weighting).
6. **Final check:** report everything on an untouched 20%; if it does not confirm the personalised plan, recommend the simple plan.

## Use it on your own data
One row per customer from a **random test**:

| Column | What it is | Needed? |
|---|---|---|
| Option given | which option each customer got, at random; one value means "nothing" (control) | Yes |
| Outcome | bought 1/0, or amount spent, after the contact | Yes |
| Customer measures | anything known before the contact (visits, spend, city, age...) | Yes, at least 1 |
| Customer id | for the download | Optional |

About 1,000+ customers per option for any result; 50,000+ rows for strong plans. A 1 lakh-row file takes about 1-3 minutes.

## Repository map
| Folder | What is in it |
|---|---|
| `notebooks/` | Steps 0-12: data health, profiles, models, money, measurement, contrast case, validation; `nudge_engine.py` |
| `app/` | the Streamlit app: `views/` (pages), `lib/` (planner, robust engine, upload checks, AI analyst), `results/` (aggregates only) |
| `validation/` | validation code and summary results (`cache/*.json`, aggregates only) |
| `docs/` | the full project write-up |
| `.github/` | a job that visits the app every 8 hours so it never sleeps |

## Run it locally
```
cd app
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```
The AI analyst needs a free Groq key in `app/.streamlit/secrets.toml` (see `secrets.toml.example`); without it, the app answers with rules.

## Limits
- X5 is Russian retail; rupee values are illustrative assumptions (shown and editable in the app).
- Needs a random test; it will not learn causal effects from data where the company chose whom to target.
- Best send time is not tested; different contact costs per option in one upload are not supported yet.

## Licence
Code: MIT (see [LICENSE](LICENSE)). **Each dataset keeps its own licence and terms:** X5 RetailHero, the Starbucks rewards data,
the Hillstrom (MineThatData) e-mail test, Dunnhumby The Complete Journey, Criteo (CC BY-NC-SA 4.0), Lenta and MegaFon belong to their
owners. This repository contains only aggregated results from them, plus the public Hillstrom file and a synthetic sample.
