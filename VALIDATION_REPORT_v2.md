# Nudge validation report: Run 2 (the approved package, on fresh data)

Date: 30-31 Oct 2026. Pass marks: `VALIDATION_PLAN.md` (unchanged since 29 Oct). What Run 2 judges was written into the plan
**before** running (section "Run 2 (decided 30 Oct 2026 ...)"). Run 1 (`VALIDATION_REPORT.md`) stays exactly as recorded.
Code under test: `validation/app_v2/` (a copy of the app with the approved changes). **The real `app/` is untouched.**
Driver: `validation/run2.py` + `validation/run2_all.sh`; results `validation/cache/run2_*.json`; log `validation/cache/run2_log.txt`.

## 5-line summary
1. **Run 2 passes 9 of 10 tests (Run 1: 3 of 10).** The one failure is B1: on Lenta the app said "no reliable signal", though its
   switched-off ranking would have beaten random on the test (the rule was too cautious there).
2. The independent check (fresh Part A seeds +9000, never used before) passes cleanly: at 50k rows plans earn 78-85% of the best
   possible profit (Run 1: 32-67%), at 2 lakh 91-95% (Run 1: 85-86%); on no-effect data the app declines to personalise 19 of 20 times.
3. Part B and Part C are **not independent** (the package was chosen and the fixes were built using these datasets and files), so
   their passes are weaker evidence than Part A's.
4. On a 2-core machine (like Streamlit's free cloud) a 1 lakh-row upload takes **61 s** to a plan (budget 3 min) with **0.43 GB**
   peak memory (budget 2 GB); on this laptop 59 s, which just passes C4's 60 s mark.
5. The Hillstrom sample is still slightly worse than "contact everyone" (-₹3.52 per customer, range -8.63 to +1.48), and the
   app's existing caution message does show on it.

## 1. Scorecard: Run 1 (app as it is) vs Run 2 (approved package)
| Part | Test (pass mark) | Run 1 [95% range] | Run 1 | Run 2 [95% range] | Run 2 |
|---|---|---|---|---|---|
| A | A1 ranking vs truth (Spearman >= 0.5 on each 50k file) | 0.633 / 0.483 / 0.474 / 0.429 | FAIL (1 of 4) | **0.789** [0.779, 0.797] / **0.792** [0.781, 0.801] / **0.706** [0.699, 0.714] / **0.518** [0.507, 0.527] | **PASS** (4 of 4) |
| A | A2 plan profit vs oracle (>= 70% on each 50k and 2 lakh file) | 50k 32 / 59 / 66 / 67%; 2 lakh 85 / 85 / 86 / 85% | FAIL (4 of 8) | 50k **85** [84, 86] / **82** [81, 83] / **78** [77, 79] / **80** [79, 80]%; 2 lakh **95 / 95 / 95 / 91%** | **PASS** (8 of 8) |
| A | A3 null data ("do not personalise" in >= 18 of 20) | 17 of 20 [62%, 97%] | FAIL | **19 of 20** [75%, 100%]: 18 contact nobody, 1 contact everyone, 1 personalised (seed 9104) | **PASS** |
| B | B1 beats random (Qini range > 0 on every dataset with a real effect) | Lenta -0.0012 [-0.0166, 0.0132] | FAIL | Lenta: "no reliable signal", no ranking (Qini 0) | **FAIL** |
| B | B2 within 10% of the best (on >= 3 of 4) | 2 of 4 | FAIL | **3 of 4**: Criteo 95%, MegaFon 97%, Hillstrom 96%; Lenta 0% | **PASS** (not independent) |
| C | C1 no crashes | 2 crashes | FAIL | **0** (function path and page; see note on the standby) | **PASS** (not independent) |
| C | C2 clear message for every bad file | 5 unclear | FAIL | every bad file gets a plain message (table in section 4) | **PASS** (not independent) |
| C | C3 non-random file flagged red | red | PASS | red (gap 2.65) | PASS |
| C | C4 1 lakh rows, upload to plan < 60 s on this laptop | 17.0 s | PASS | **58.8 s** (58.5 to 59.0) | PASS (narrowly) |
| D | D1 top-20% overlap >= 70% | 81.9% [80.9, 82.7] | PASS | **94.9%** [94.5, 95.4], lowest pair 94.6% (fresh seed 9022) | PASS |

What Run 2 runs (decided before running): Part C's 10 fixes; plan chosen on honest 5-fold scores of the 80% (3 folds above
1,50,000 rows); ensemble ranking (S + X + DR) with the fast engine as automatic fallback (it was never needed in Run 2); calibration;
whole-file "no reliable signal" rule. B1/B2 judge the app's default ranking (the package); the fast engine is reported for information.

## 2. Part A on fresh seeds (original + 9000): the independent check
| rows | options | outcome | A1 Run 1 | A1 Run 2 [95%] | A2 Run 1 (plan) | A2 Run 2 [95%] (plan, share contacted) |
|---|---|---|---|---|---|---|
| 5k | 1 | yes/no | 0.485 | 0.567 [0.532, 0.600] | 53% (pers.) | 63% [58, 67] (pers., 43%) |
| 5k | 1 | revenue | 0.532 | 0 (no signal) | 32% (everyone) | 0% (nobody: "no reliable signal") |
| 5k | 3 | yes/no | 0.495 | 0.268 [0.238, 0.300] | 46% (everyone) | 60% [57, 63] (pers., 97%) |
| 5k | 3 | revenue | 0.217 | 0.219 [0.182, 0.253] | 54% (everyone) | 55% [51, 58] (pers., 84%) |
| 50k | 1 | yes/no | 0.633 | **0.789** [0.779, 0.797] | 32% (everyone) | **85%** [84, 86] (pers., 60%) |
| 50k | 1 | revenue | 0.483 | **0.792** [0.781, 0.801] | 59% (pers.) | **82%** [81, 83] (pers., 63%) |
| 50k | 3 | yes/no | 0.474 | **0.706** [0.699, 0.714] | 66% (pers.) | **78%** [77, 79] (pers., 100%) |
| 50k | 3 | revenue | 0.429 | **0.518** [0.507, 0.527] | 67% (pers.) | **80%** [79, 80] (pers., 100%) |
| 2 lakh | 1 | yes/no | 0.792 | 0.927 [0.925, 0.928] | 85% | 95% [95, 95] |
| 2 lakh | 1 | revenue | 0.789 | 0.921 [0.919, 0.922] | 85% | 95% [95, 95] |
| 2 lakh | 3 | yes/no | 0.691 | 0.839 [0.837, 0.841] | 86% | 95% [94, 95] |
| 2 lakh | 3 | revenue | 0.630 | 0.782 [0.779, 0.785] | 85% | 91% [90, 91] |

- Run 1 and Run 2 use different seeds (Run 2's are new), so a row is the same kind of file, not the same file.
- 5k files are reported, not pass-marked. At 5k the package sometimes says "no reliable signal" (1 of 4); that is the intended
  behaviour on small, noisy files, but on 5k revenue it chose "contact nobody", which earns 0% of a real but small effect.
- 1-option files at ₹1.02 per contact (information): 86% / 89% (5k), 94% / 94% (50k), 97% / 97% (2 lakh).

### 3 folds vs 5 folds on the 2 lakh files (your condition 2: the accuracy cost of the speed rule)
| file | A1 3 folds | A1 5 folds | A2 3 folds | A2 5 folds | train time 3 / 5 folds (laptop) |
|---|---|---|---|---|---|
| 1 option, yes/no | 0.927 | 0.927 | 95.0% | 94.3% | 64 / 88 s |
| 1 option, revenue | 0.921 | 0.921 | 95.0% | 94.7% | 61 / 95 s |
| 3 options, yes/no | 0.839 | 0.838 | 94.5% | 94.0% | 148 / 196 s |
| 3 options, revenue | 0.782 | 0.779 | 90.5% | 90.6% | 131 / 193 s |
**No accuracy cost:** every difference is under 1 point (3 folds slightly ahead on 3 of 4), and 3 folds saves 25-40% of the time.

### Null test (seeds 9101-9120, no effect at all, ₹1.02 per contact)
- "No reliable signal" fired on 19 of 20 seeds: 18 "contact nobody", 1 "contact everyone" (seed 9115).
- Personalised once (seed 9104): its Qini range on the 80% was just above zero (lower end 0.00011), a chance pattern.
- Average true profit of the recommended plans: -₹0.07 per customer (every contact loses ₹1.02 here, so 0 is the best possible).
  Run 1's rule on its own seeds: -₹0.42.

## 3. Part B on public data: NOT INDEPENDENT
**Label: the default was chosen partly using these 4 datasets.** New 80/20 split (seed 2036) and a fresh 10% Criteo sample (seed
2036), but the same datasets. Treat these passes as weaker evidence than Part A.

| dataset | package Qini [95%] | best method (Qini) | package / best | fast engine (info) | B1 | B2 |
|---|---|---|---|---|---|---|
| Criteo | 0.0854 [0.0670, 0.1052] | likely-buyer 0.0901 | 95% | 0.0705 (78%) | pass | pass |
| Lenta | 0 ("no reliable signal") | ensemble, single fit, 0.0134 [0.0012, 0.0262] | 0% | 0.0055 [-0.0072, 0.0213] | **FAIL** | fail |
| MegaFon | 0.2077 [0.2012, 0.2146] | fast engine 0.2152 | 97% | 0.2152 (best) | pass | pass |
| Hillstrom | 0.0452 [0.0133, 0.0798] | causal forest 0.0474 | 96% | 0.0423 (89%) | pass | pass |

- **Lenta, in plain words:** on the 80% the package's own check found no signal (Qini range -0.0012 to 0.0003), so the app refuses
  to rank and recommends the simple plan. On this new split, one method's range on the test part ends just above zero (the single-fit
  ensemble, 0.0012), and a random order scored 0.0077 [-0.0033, 0.0183] on the same test, so the noise is about as large as the
  signal. Under the mark as written it is a FAIL (and see the next point: the rule was too cautious here).
- **For information, the package's own ranking before the rule switched it off** (same test, same bootstrap): Criteo 0.0854,
  MegaFon 0.2077, Hillstrom 0.0452 (identical: the rule did not fire there) and **Lenta 0.0177 [0.0057, 0.0301]: above zero, and the
  highest of all methods on this split.** So on Lenta the "no reliable signal" rule was **too cautious this time**: the check on the
  80% (Qini range -0.0012 to 0.0003) missed a weak signal that the 20% test shows. The rule may only use the 80% (using the test
  would flatter the result), so this is a real cost of the rule: on very weak signals it can switch off a ranking that would have
  helped a little. Without the rule, B1 and B2 would have passed on Lenta; I did not change anything after seeing this.
- Criteo's new 10% sample gets an **amber** fairness light (Run 1's sample: green): small chance differences in this draw.
- Calibration slope of the package (information; target 0.8-1.2): Criteo 1.07, MegaFon 1.05 (both in target); **Hillstrom 0.64
  (miss)**; Lenta n/a (no ranking). Rupee figures on the app's pages are measured on the untouched 20%, not predicted, so a slope miss
  changes the predicted per-customer lift in the download, not the money numbers shown.

## 4. Part C: bad files (the same files as Run 1, so NOT independent: the fixes were built against them)
| file | Run 1 | Run 2 |
|---|---|---|
| missing values | **crash** | warns "197 rows have no value in "option" ... will be left out" (+1.9% with no outcome); plan built |
| 500 rows | **crash** on the Money page | warnings: only 257 / 243 customers per option; plan built ("contact nobody"); Money page works |
| outcome all zero | "contact nobody", no message | error: "The outcome "bought" is 0 for every customer (nobody bought) ... nothing to learn" |
| no control group | plan built on `region` | error: "Choose which value of "region" is the control group ... Its values: north, east, south ..." |
| duplicate ids | id used as a measure, no message | warning: "2,000 customers appear more than once (4,000 rows) ..."; id kept out of the measures |
| odd column names | outcome guessed as `post_campaign_spend` | outcome guessed correctly ("Purchased?", yes/no text); row-number column not used |
| semicolon file | "Choose the option column ..." | read correctly; plan built |
| header only | "Choose the option column ..." | error: "The file has column names but no rows of data ..." |
| not a CSV | clear read error | same clear read error |
| text columns, 95/5 split, non-random (red), 4 options, revenue, 10 lakh rows | fine | fine (10 lakh: capped at 2 lakh with a warning) |

- Page layer (Streamlit AppTest through `app.py`): **0 exceptions on every file.** First attempt: 2 files (4 options, revenue) timed
  out after 900 s because **the laptop went into Modern Standby from 01:12 to 06:34** (Windows event log, Kernel-Power 506/507);
  re-run with the laptop awake: both built in normal time with 0 exceptions. Both attempts are kept
  (`run2_C_apptest_first_attempt_standby.json`, `run2_C_apptest.json`).

## 5. Hillstrom sample (your condition 1: no new rule, no tuning)
- The package's plan: personalised, contacting 96% (today's app: "contact everyone (Men's e-mail)").
- Measured on the sample's untouched 20%, vs contacting everyone: **-₹3.52 per customer** [-8.63, +1.48]; the range includes zero.
- **The existing caution message shows on the page**: "... the 5-fold check on the 80% preferred the personalised plan, but the
  untouched 20% does not confirm it, so treat it with caution and keep a control group." (checked in AppTest; 0 page exceptions).
- Why (from the data only): 578 buyers out of 64,000 (0.9%), top 10% of buyers hold 32% of spend, the test part has about 115
  buyers, and e-mail costs ₹0.01, so "everyone" is hard to beat and a few large orders decide any comparison.

## 6. Timing (upload to plan, Part C's files; nothing else running)
| setting | rows | today's app | Run 2 package | peak memory (package) | budget |
|---|---|---|---|---|---|
| 2 cores pinned (cloud-like; 1.5 cores busy measured) | 1 lakh | 16-21 s | **60.8 s** (5 folds) | **428 MB** | <= 180 s, < 2 GB: **met** |
| 2 cores pinned | 2 lakh | 29-30 s | **79.3 s** (3 folds) | 621 MB | met |
| this laptop, 12 cores (C4 harness, median of 3) | 1 lakh | 17.0 s | **58.8 s** | - | C4 < 60 s: met, narrowly |
| this laptop, 12 cores (single run) | 1 lakh | - | 62.5 s | 434 MB | - |

- Progress messages appear step by step ("Training the Nudge engine ...", "Learning "Message" (option 1 of 1): part 2 of 5 (3
  learners)...", "Checking ...: does the ranking beat a random order ...").
- The development prototype took longer (109 s / 180 s on 2 cores) than the built version (61 s / 79 s): the built version scores
  each held-out part once during training instead of also re-scoring the test part inside every fold.
- 12 cores is not faster than 2 here: the models are small, so threads add little.
- Streamlit Community Cloud gives up to 2 cores and 2.7 GB (its docs, "as of Feb 2024"); its cores may be slower than this laptop's,
  so the 3-minute budget has about 3x headroom at 1 lakh rows.

## 7. Known limits (honest list)
1. **Lenta (B1 FAIL):** the "no reliable signal" rule switched off the ranking, judging on the 80%; on the test part that ranking
   would have beaten random (0.0177 [0.0057, 0.0301]). The rule trades a little missed gain on very weak signals for safety on
   no-effect data (19 of 20 null runs correct).
2. **Hillstrom sample:** about ₹3.5 per customer behind "contact everyone" on its test part (range includes zero); a caution shows.
3. **Small files (5k):** often "no reliable signal"; on one 5k file that meant "contact nobody" while a small real effect existed.
4. **C4 passes by 1.2 s** on this laptop; slower machines will exceed 60 s (but stay well inside the 3-minute cloud budget).
5. **Part B and Part C are not independent evidence**; Part A (fresh seeds) and the null test are.
6. Calibration slope misses the 0.8-1.2 target on Hillstrom (0.64 here, 1.45-1.52 in development).
7. Per-option contact costs are still not settable on the page (logged feature gap; Part A used the planner's `costs=` argument).

## 8. My process errors in Run 2 (corrected, both attempts logged)
- The laptop slept during the page layer; two timeouts were the standby, not the app (re-run awake: 0 exceptions).
- In development, my first "2-thread" timings were invalid (LightGBM ignored the thread setting; 7.6 cores busy); all timings here
  pin the process to 2 cores and record the cores actually busy.

**Waiting for your OK before changing `app/`.** If approved: copy `validation/app_v2/` changes into `app/` (planner, robust, upload,
pages), re-run the app's own samples once, then deploy.

## 9. After Run 2 (1 Nov 2026): two app changes, and a re-check
Pass marks unchanged. Run 1 and Run 2 results above stay exactly as recorded.

**What changed in the app after Run 2, and why**
1. **Final check on the untouched 20%.** In the app, the Hillstrom sample's decision box said "contact 96%, personalised" while its lift
   ladder said "do not personalise". New rule, in one sentence: *if the untouched 20% shows the chosen personalised plan earning less
   than the simple plan, Nudge recommends the simple plan* (a last yes/no gate, like the K4 go/no-go check).
2. **Shared work for the built-in samples, and no repeated scoring.** After the merge the free cloud throttled the app (too much CPU).
   Cause: every click re-scored all rows for the download (about 20 s of CPU on the 2 lakh sample) and each visitor retrained the
   samples. Now each sample is trained once per server and shared; the download list and profit curves are computed once per setting.

**Re-check of the final-check rule** (same Part A files and null seeds as Run 2, through the changed app code; `validation/run_gate.py`,
results `validation/cache/gate_*.json`; run on a 2-core machine):

| Test | Run 2 | With the final check |
|---|---|---|
| A1, A2 on the 8 marked files (50k and 2 lakh) | A2 78-95%, A1 0.52-0.93 | identical (the rule never fired there) |
| A3 no-effect test, seeds 9101-9120 | 19 of 20 (seed 9104 personalised) | **20 of 20** (19 contact nobody, 1 everyone) |
| 5k files (not marked) | 63 / 0 / 60 / 55% | 63 / 0 / **54** / 55% (3-option file switched to the simple plan) |
| Hillstrom sample | personalised, -Rs3.52 per customer vs e-mail everyone | **e-mail everyone** (the measured better plan) |

Note: these seeds were already used in Run 2, so this is a re-check of the new rule, not fresh evidence.

**Speed after the sharing fix** (2-core machine, through the real pages): synthetic 2 lakh sample, first visitor about 1.5 min,
next visitors about 10 s; a later click on the Plan page 1.6 s (was about 20 s); Money page 14 s first, 0.3 s after.
