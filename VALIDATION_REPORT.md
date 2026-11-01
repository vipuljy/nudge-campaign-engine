# Nudge validation report: Run 1 (the app exactly as it is)

Date: 29-30 Oct 2026. Plan and pass marks: `VALIDATION_PLAN.md` (frozen before any run; no mark was changed).
Code: `validation/*.py`, notebook `notebooks/12_validation.ipynb`, raw aggregates in `validation/cache/*.json`.
Environment: `validation/.venv` (Python 3.11.4, the app's `requirements.txt` plus econml 0.17.0; no app package version changed).

## 5-line summary
1. **The app does not pass yet: 3 of 10 tests pass** (C3, C4, D1). A1, A2, A3, B1 (Lenta only), B2, C1 and C2 fail.
2. On big files (2 lakh rows) the engine is good: its plans earn 85-86% of the best possible profit (truth known), well above the 70% mark.
3. On mid-size files (50k) it builds good targeting lists but often **picks the wrong plan**: one small 16% check slice decides, and it is too noisy.
4. On public data it is best on MegaFon, 94% of the best on Hillstrom and 76% on Criteo; on Lenta nothing works (no method beats random).
5. Two upload crashes and 5 unclear messages were found; each has a proposed fix below. A tested fix for point 3 (decide on 5 folds) is in section 3.

## 1. Scorecard (Run 1, the app as is)

| Part | Test | Pass mark | Result [95% range] | Verdict |
|---|---|---|---|---|
| A | A1 ranking vs truth | Spearman >= 0.5 on each 50k file | 0.633 [0.621, 0.646] / 0.483 [0.468, 0.500] / 0.474 [0.464, 0.484] / 0.429 [0.418, 0.439] | **FAIL** (1 of 4) |
| A | A2 plan profit vs oracle | >= 70% on each 50k and 2 lakh file | 50k: 32% / 59% / 66% / 67%; 2 lakh: 85% / 85% / 86% / 85% (ranges below) | **FAIL** (4 of 8: all 2 lakh pass, all 50k fail) |
| A | A3 null data (no effect) | "do not personalise" in >= 18 of 20 | 17 of 20 (85%, range 62% to 97%): 10 "contact nobody", 7 "contact everyone"; personalised on seeds 3, 7, 19 | **FAIL** |
| B | B1 engine beats random | Qini range above 0 on every dataset with a real effect | Criteo 0.0683 [0.0494, 0.0858]; Lenta -0.0012 [-0.0166, 0.0132]; MegaFon 0.2165 [0.2087, 0.2247]; Hillstrom 0.0636 [0.0354, 0.0941] | **FAIL** (Lenta) |
| B | B2 near the best method | engine Qini >= 0.9 x best on >= 3 of 4 | Criteo 76%; Lenta below 0; MegaFon 100% (best); Hillstrom 94% | **FAIL** (2 of 4) |
| C | C1 no crashes | 0 crashes | 2 crashes: blank option values; Money page on files under 1,500 rows | **FAIL** |
| C | C2 clear messages | every bad file gets a clear message | 5 files without a clear message (list in section 4) | **FAIL** |
| C | C3 non-random file flagged | red | red (largest gap 2.65 on the spend-like measure) | PASS |
| C | C4 speed | 1 lakh rows, upload to plan < 60 s | 17.0 s median of 3 (15.2 to 19.1) | PASS |
| D | D1 stability | top-20% overlap >= 70% | 81.9% [80.9%, 82.7%]; lowest pair 81.0% | PASS |

### Part A detail (synthetic files, true uplift known; seeds as in the plan)
| rows | options | outcome | A1 Spearman [95%] | A2 plan / oracle [95%] | plan chosen | simple plan / oracle (truth) |
|---|---|---|---|---|---|---|
| 5k | 1 | yes/no | 0.485 [0.433, 0.532] | 53% [46, 60] | Nudge plan | 25% |
| 5k | 1 | revenue | 0.532 [0.492, 0.570] | 32% [20, 42] | everyone | 32% |
| 5k | 3 | yes/no | 0.495 [0.465, 0.521] | 46% [44, 49] | everyone (SMS) | 53% |
| 5k | 3 | revenue | 0.217 [0.182, 0.253] | 54% [51, 57] | everyone (WhatsApp) | 54% |
| 50k | 1 | yes/no | **0.633** [0.621, 0.646] | 32% [29, 36] | everyone | 32% |
| 50k | 1 | revenue | 0.483 [0.468, 0.500] | 59% [57, 60] | Nudge plan | 34% |
| 50k | 3 | yes/no | 0.474 [0.464, 0.484] | 66% [65, 67] | Nudge plan | 53% |
| 50k | 3 | revenue | 0.429 [0.418, 0.439] | 67% [67, 68] | Nudge plan | 53% |
| 2 lakh | 1 | yes/no | 0.792 [0.788, 0.796] | **85%** [84, 85] | Nudge plan | 34% |
| 2 lakh | 1 | revenue | 0.789 [0.784, 0.793] | **85%** [84, 85] | Nudge plan | 34% |
| 2 lakh | 3 | yes/no | 0.691 [0.688, 0.693] | **86%** [86, 86] | Nudge plan | 54% |
| 2 lakh | 3 | revenue | 0.630 [0.626, 0.633] | **85%** [85, 86] | Nudge plan | 53% |

- 1-option files are judged at ₹5 per contact (fixed before the run; at ₹1.02 "contact everyone" already earns ~88% of the oracle by
  construction). At ₹1.02, for information: 77% / 87% / 88% / 88% / 90% / 93%.
- **Why A2 fails at 50k (diagnosis, `validation/diagnose_a.py`):** the engine's own personalised plans earn 59-72% of the oracle there,
  but the app picks between plans on a 16% slice (8,000 customers), which is too noisy. Example, 50k 1-option: the slice said
  "everyone" 50.4 vs "personalised" 49.4 (a coin toss); the truth is 32% vs 70%.

### Part B detail (public data; locked 20% test, seed 2026; training capped at 2 lakh rows as in the app)
| dataset | rows | treated | outcome rate | average effect [95%] | fairness light |
|---|---|---|---|---|---|
| Criteo (10% sample) | 13,98,073 | 85% | 4.69% | +1.01 pts [0.92, 1.10] | green |
| Lenta | 6,87,029 | 75% | 10.82% | +0.75 pts [0.59, 0.92] | **red** |
| MegaFon | 6,00,000 | 50% | 20.42% | +4.95 pts [4.75, 5.16] | green |
| Hillstrom (women's email vs none, visit) | 42,693 | 50% | 12.88% | +4.52 pts [3.89, 5.16] | green |

- Qini of every method is in `validation/cache/B_*.json`. Clear outside winner on Criteo: causal forest minus engine
  -0.0217 [-0.040, -0.002] (engine lower) → adding the causal forest is **proposed** (tested in Run 2 work), not done.
- The thorough ensemble (information only) would have passed B2: 95% / 15% / 96% / 96% of best.
- **Measurement note:** the Criteo file is sorted by treatment and the engine gives many customers the same score. I re-scored with a
  random tie-break: **Qini identical** (scikit-uplift groups ties); only top-k lifts moved slightly. No verdict changed.

### Lenta (information only; the engine's FAIL stays)
- Average effect +0.75 pts [0.59, 0.92] on 10.8% buying; test part [0.38, 1.13]. Split 75% treated / 25% control.
- Is any method's Qini range above 0? **No, none of the 6:** likely-buyer 0.0107 [-0.0017, 0.0214]; causal forest 0.0085
  [-0.0028, 0.0198]; ensemble 0.0016 [-0.0128, 0.0143]; R-learner -0.0007 [-0.0165, 0.0112]; fast engine -0.0012
  [-0.0166, 0.0132]; random -0.0121.
- **Extra, not part of the pass mark** (all 5,49,623 training rows, same test): fast engine 0.0108 [-0.0007, 0.0255] (101 s);
  causal forest 0.0095 [-0.003, 0.021] (6,582 s). More rows help, but still neither range is above 0.
- Why Lenta is hard:
  - **Tiny effect:** +0.75 pts on 10.8% buying, about one extra buyer per 133 messages; the differences between customers are smaller still.
  - **Weak and suspect features:** 193 measures, mostly noisy; two (`response_sms`, `response_viber`) look recorded after the campaign,
    which is why the app's own fairness check turns red.
  - **Noise:** only 25% control, so every "with vs without" comparison on a slice of customers is very uncertain.

## 2. Part C: what broke and proposed fixes (not applied; app code untouched)
| # | File | What happened | Proposed fix |
|---|---|---|---|
| 1 | missing values | **CRASH**: blank option cells become a "missing" option; LightGBM gets an empty table (`nudge_engine.py:99`) | `upload.validate/prepare`: drop rows with a blank option or outcome, and say how many |
| 2 | 500 rows (any file < 1,500 rows) | **CRASH** on the Money page: `round(500, -3) = 0` is below the box minimum 1,000 (`views/money.py:56`) | `max(1_000, ...)` for the default |
| 3 | outcome all zero | plan "contact nobody", no explanation | clear error: "Nobody in the file bought (outcome is always 0); nothing to learn from" |
| 4 | no control group | guessed option = `region`, control = "north"; plan built | require a control the user confirms; warn when the option column has no control-like value |
| 5 | duplicate ids | id not guessed (non-unique), so **`customer_id` was used as a measure**; no message | accept non-unique ids, warn "2,000 customers appear twice"; never use an id-like column as a measure |
| 6 | wrong / odd column names | outcome guessed as `post_campaign_spend` (an after-campaign column) | treat yes/no text columns as outcome candidates first; warn on names with "post"/"after" |
| 7 | semicolon-separated | "Choose the option column and the outcome column." | detect the separator |
| 8 | header only | same message | "The file has no rows" |
| 9 | (all) | tied scores keep file order in the planner's lists and curves | random tie-break |
| 10 | text columns | dropped columns shown in a caption only | name them in plain words ("not used: city (too many values), signup_date, notes") |

Fine as is: text columns, 95/5 split (warning: only 486 in control), non-random (red), 4 options, revenue, 10 lakh rows (capped at
2 lakh with a warning; 2.8 s read, 33 s train), not-a-CSV (clear read error). Page layer (Streamlit AppTest through `app.py`): only
crashes 1 and 2; 0 page exceptions on every other file.

## 3. Fix 1 tested: decide on 5 folds instead of one 16% slice (validation code only; Run 1 scorecard above unchanged)
**What it does:** today the app trains on 64%, picks the plan on a 16% slice and reports on the untouched 20%. The fix pools the
64% + 16%, splits it into 5 folds by customer, values every plan (each safety margin, everyone, nobody) on customers the model did
not see, and picks the best. Same untouched 20% for reporting. `validation/candidate_fix.py`; comparison `validation/compare_fix.py`
(one training per file, both rules on the same split, so the difference is only the rule).

### 3a. Original seeds (the Run 1 files), before → after
| rows | options | outcome | A1 current | A1 fix | A2 current (plan) | A2 fix (plan) | fix minus current, measured ₹/customer [95%] |
|---|---|---|---|---|---|---|---|
| 5k | 1 | yes/no | 0.485 [0.433, 0.532] | 0.562 [0.517, 0.601] | 53% [46, 60] (pers.) | 63% [57, 70] (pers.) | +1.52 [-1.83, +4.66] |
| 5k | 1 | revenue | 0.532 [0.492, 0.570] | 0.534 [0.492, 0.580] | 32% [20, 42] (everyone) | 32% [20, 42] (everyone) | 0 |
| 5k | 3 | yes/no | 0.495 [0.465, 0.521] | 0.502 [0.470, 0.528] | 46% [44, 48] (everyone) | 46% [44, 48] (everyone) | 0 |
| 5k | 3 | revenue | 0.217 [0.182, 0.253] | 0.243 [0.212, 0.277] | 54% [51, 57] (everyone) | 54% [51, 57] (everyone) | 0 |
| 50k | 1 | yes/no | **0.633** [0.621, 0.646] | **0.665** [0.651, 0.677] | 32% [29, 36] (everyone) | **73%** [71, 74] (pers.) | +2.86 [+1.00, +4.93] |
| 50k | 1 | revenue | 0.483 [0.468, 0.500] | **0.510** [0.494, 0.525] | 59% [57, 60] (pers.) | 63% [61, 65] (pers.) | -0.08 [-1.53, +1.34] |
| 50k | 3 | yes/no | 0.474 [0.464, 0.484] | **0.517** [0.508, 0.526] | 66% [65, 67] (pers.) | **75%** [74, 75] (pers.) | +0.59 [-1.72, +3.10] |
| 50k | 3 | revenue | 0.429 [0.418, 0.439] | 0.443 [0.429, 0.453] | 67% [67, 68] (pers.) | **73%** [72, 74] (pers.) | +0.50 [-1.95, +2.76] |
| 2 lakh | 1 | yes/no | 0.792 [0.788, 0.796] | 0.817 [0.813, 0.820] | 85% [84, 85] | 86% [86, 87] | -0.17 [-0.69, +0.27] |
| 2 lakh | 1 | revenue | 0.789 [0.784, 0.793] | 0.821 [0.816, 0.825] | 85% [84, 85] | 87% [87, 88] | -0.06 [-0.59, +0.52] |
| 2 lakh | 3 | yes/no | 0.691 [0.688, 0.693] | 0.749 [0.746, 0.752] | 86% [86, 86] | 90% [89, 90] | +0.40 [-0.43, +1.40] |
| 2 lakh | 3 | revenue | 0.630 [0.626, 0.633] | 0.673 [0.669, 0.676] | 85% [85, 86] | 88% [87, 88] | -0.04 [-1.16, +1.09] |

(A1 for the fix = Spearman of the final engine trained on the whole 80%; A2 = truth. "Measured" = on the untouched 20% only, so it is
noisy; the truth columns are the precise ones.)

### 3b. FRESH seeds (+7000, never used before), judged on the same marks
| rows | options | outcome | A1 current | A1 fix | A2 current (plan) | A2 fix (plan) | fix minus current, measured ₹/customer [95%] |
|---|---|---|---|---|---|---|---|
| 5k | 1 | yes/no | 0.384 [0.338, 0.433] | 0.406 [0.356, 0.453] | 42% [32, 50] (everyone) | 59% [52, 65] (pers.) | +2.38 [-1.60, +7.03] |
| 5k | 1 | revenue | 0.595 [0.554, 0.631] | 0.614 [0.575, 0.650] | 0% (nobody) | 70% [66, 74] (pers.) | -0.73 [-6.40, +7.25] |
| 5k | 3 | yes/no | 0.238 [0.202, 0.268] | 0.269 [0.235, 0.308] | 53% [50, 56] (everyone) | 57% [54, 60] (pers.) | +6.55 [-1.73, +14.59] |
| 5k | 3 | revenue | 0.452 [0.423, 0.479] | 0.466 [0.435, 0.496] | 43% [39, 48] (everyone) | 64% [61, 67] (pers.) | -6.56 [-14.72, +1.48] |
| 50k | 1 | yes/no | 0.611 [0.599, 0.623] | **0.657** [0.645, 0.669] | 34% [31, 37] (everyone) | **74%** [73, 76] (pers.) | +1.51 [+0.09, +2.93] |
| 50k | 1 | revenue | 0.614 [0.600, 0.629] | **0.592** [0.579, 0.605] | 32% [29, 36] (everyone) | 68% [67, 70] (pers.) | +0.44 [-1.57, +2.46] |
| 50k | 3 | yes/no | 0.435 [0.425, 0.446] | 0.475 [0.465, 0.485] | 69% [68, 70] (pers.) | **71%** [70, 72] (pers.) | -0.27 [-2.43, +1.86] |
| 50k | 3 | revenue | 0.435 [0.423, 0.446] | 0.469 [0.459, 0.480] | 71% [70, 72] (pers.) | **74%** [73, 75] (pers.) | +1.97 [-0.71, +4.83] |
| 2 lakh | 1 | yes/no | 0.796 [0.791, 0.800] | 0.824 [0.820, 0.828] | 83% [83, 84] | 86% [85, 86] | -0.00 [-0.51, +0.46] |
| 2 lakh | 1 | revenue | 0.763 [0.759, 0.769] | 0.811 [0.807, 0.815] | 78% [78, 79] | 86% [86, 87] | +0.22 [-0.46, +0.74] |
| 2 lakh | 3 | yes/no | 0.749 [0.747, 0.752] | 0.776 [0.774, 0.778] | 85% [85, 85] | 88% [88, 88] | +1.55 [+0.72, +2.54] |
| 2 lakh | 3 | revenue | 0.623 [0.619, 0.627] | 0.672 [0.668, 0.676] | 83% [83, 83] | 85% [85, 86] | -0.66 [-1.82, +0.39] |

Against the marks (fresh seeds, fix): **A1 still FAILS** (2 of 4 at 50k reach 0.5); **A2 still FAILS** (7 of 8: 50k revenue 68%).
Original seeds with the fix: A1 3 of 4, A2 7 of 8 (50k revenue 63%).

### 3c. Null test (no effect at all, ₹1.02 per contact), counted separately
| seeds | rule | "do not personalise" [95% range] | contact nobody | contact everyone | personalised (seeds) | true profit per customer (avg) |
|---|---|---|---|---|---|---|
| original 1-20 | current | 17 of 20 [62%, 97%] | 10 | 7 | 3 (3, 7, 19) | -₹0.42 |
| original 1-20 | fix | **16 of 20** [56%, 94%] | 12 | 4 | 4 (1, 3, 16, 19) | -₹0.29 |
| fresh 7101-7120 | current | 19 of 20 [75%, 100%] | 13 | 6 | 1 (7106) | -₹0.33 |
| fresh 7101-7120 | fix | **17 of 20** [62%, 97%] | 16 | 1 | 3 (7106, 7115, 7119) | -₹0.12 |

- **The null test did not improve** (your condition c): the fix says "contact nobody" more often and "contact everyone" much less
  (so it loses less money on null data), but it personalises on 1-2 more seeds. Fix 1 alone cannot pass A3. This is what the
  "no reliable signal" rule (improvement 5) targets.

### 3d. Where we already pass: not worse? (your condition d)
| check | current | fix | fix minus current [95%] |
|---|---|---|---|
| 2 lakh files (truth) | 78-86% of oracle | 85-90% | better on all 8 |
| Part B Hillstrom, planner path (Qini / plan) | 0.0521, everyone | 0.0588, everyone | plan identical |
| Part B MegaFon, planner path (Qini / measured ₹ per customer) | 0.2139, ₹11.63 | 0.2144, ₹11.67 | +0.04 [-0.30, +0.34] |
| Sample: synthetic X5-like (₹5 AI call) | Nudge plan, ₹1.59 [0.89, 2.47] | Nudge plan, ₹1.47 [0.73, 2.29] | -0.12 [-0.64, +0.42] |
| Sample: Hillstrom (Email ₹0.01, spend) | everyone (Men's), ₹12.65 [3.73, 22.57] | Nudge plan, ₹6.00 [-1.53, 14.79] | **-6.65 [-14.46, +0.06]** |

- **Worse on the Hillstrom sample** (measured on its 20% test; the range just touches 0). The fix personalises where "everyone"
  measured better; on the 20% test the engine's ranking is worse than random there (Qini below 0 for both rules), which is again
  a case for the "no reliable signal" check. Part B's own engine Qini cannot change (engine code untouched).

### 3e. Run time for a 1 lakh-row upload (your condition e)
Part C's 1 lakh-row file, train + plan, 3 repeats, nothing else running, this laptop (`validation/time_fix.py`):
current app **14.0 s** median (12.4 to 14.3); with the fix **39.5 s** (39.3 to 39.6): **+25.5 s**. Still under C4's 60 s.

**Verdict on fix 1:** clearly better plans at 50k and 2 lakh (truth), but the null test and the Hillstrom sample are not better, so
it is **not enough on its own**. It becomes part of the v2 package tested next (with the guard and the "no reliable signal" rule).

## 4. Download size and run time (this laptop, 12 cores)
- Downloads: 715 MB (Criteo 311, MegaFon 276, Lenta 145, Hillstrom 0.4); `data_benchmarks/` 892 MB in total (git-ignored).
- Run time: Part A 521 s; Part B 3,238 s (Lenta's causal forest alone 1,011 s); Part C function path ~1,294 s, page layer ~20 min;
  Lenta extra 6,683 s (causal forest on 5.5 lakh rows).

## 5. My own errors, found and corrected
- First Part A replica check compared the planner with itself; corrected before any result was used.
- My first "run 2" null test used ₹5 per contact instead of A3's ₹1.02, so it was not a valid A3 comparison; redone in section 3.
