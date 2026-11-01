# Nudge external validation: plan and pass marks

Written 29 Oct 2026, **before any validation run**. Pass marks are fixed here and will not be changed after seeing results.
If a test fails, the failure is reported as is, a fix is proposed, the test is re-run, and **both runs are logged** in VALIDATION_REPORT.md.

Rules: separate environment (`validation/.venv`); fixed seeds; every result with a 95% range (bootstrap, 200 repeats unless stated);
no raw rows of any dataset in `app/` or on GitHub (aggregates only, saved as `app/results/validation_*.json`); nothing pushed without OK;
secrets untouched. Work lives in `notebooks/12_validation.ipynb` plus small helpers in `validation/`.

What is tested: the **app's own code** (`app/lib/planner.py`, `app/lib/upload.py`, `app/nudge_engine.py`), so a pass means the
deployed app works, not just a notebook copy.

---

## Part A: known-truth test (synthetic data, true uplift known for every customer)

**Data.** 12 datasets: sizes 5,000 / 50,000 / 2,00,000 x 2-arm (control + 1 option) and 4-arm (control + 3 options) x binary
(bought yes/no) and revenue (amount) outcome. Customers have 10 numeric and 2 category measures. Planted effects, fixed before running:
- buy rate without contact about 30%; average true lift of the main option +4 pts (binary) or the same in revenue terms;
- lift varies between customers (standard deviation about 4 pts), driven by 3 of the measures;
- **about 15% of customers have a negative true effect** (contact makes them less likely to buy);
- 4-arm: the 3 options have different costs (₹0.10, ₹1.02 and a ₹20 offer paid by buyers) and different customers respond best to
  different options, so the best option varies by customer.
- Money for all Part A plans: ₹150 profit per extra purchase (binary) or 30% margin on extra revenue.

**Measured on the untouched 20% of each dataset, using the true values:**
- **A1 ranking:** Spearman rank correlation between predicted and true uplift. 2-arm: the option's uplift. 4-arm: the average of the
  three options' correlations. 95% range by bootstrap over customers.
- **A2 plan quality:** true profit of the plan the app chooses, divided by the true profit of the **oracle plan** (each customer gets
  the option with the highest true profit after costs, or nothing if none pays). 95% range by bootstrap.
- **A3 null test:** 20 datasets of 50,000 rows, 2-arm, binary, **no effect at all** (true uplift 0 for everyone), seeds 1 to 20,
  contact cost ₹1.02. Counted: runs in which the app's plan is "do not personalise" (a blanket plan or contact nobody).

**Pass marks**
| Test | Pass mark |
|---|---|
| A1 | at 50k rows, Spearman(predicted, true uplift) >= 0.5, on each of the four 50k datasets (point estimate) |
| A2 | the engine's plan captures >= 70% of the oracle plan's profit, on each 50k and 2 lakh dataset (point estimate); 5k is reported but not pass-marked |
| A3 | on NULL data, the engine says "do not personalise / blanket or no contact" in >= 18 of 20 runs |

---

## Part B: public benchmarks

**Data** (downloaded once with scikit-uplift's fetchers into `data_benchmarks/`, which is git-ignored):
| Dataset | Treatment | Outcome used |
|---|---|---|
| Criteo (10% sample) | treatment vs control | visit |
| Lenta | test vs control | response |
| MegaFon | treatment vs control | conversion |
| Hillstrom | women's e-mail vs no e-mail | visit |

X5 results already exist (Steps 3-9) and are reported alongside, not re-scored for the pass marks.

**Protocol, identical for every dataset and method:**
- A **locked 20% test set** (split stratified by treatment x outcome, seed 2026), touched only for the final scoring.
- All model choice uses only the other 80%. To keep the comparison fair and the run time reasonable, **every method trains on the same
  random 2,00,000 rows** of that 80% (or all of it if smaller).
- Methods: random order; treat-all; likely-buyer model (who buys when contacted, as in Step 5); **Nudge fast engine** (the app's
  default, doubly robust LightGBM); Nudge ensemble (S+X+DR rank average, the app's thorough mode); **econml CausalForestDML**;
  **econml R-learner** (NonParamDML with LightGBM).
- Reported on the locked test, each with a 95% range (bootstrap, paired across methods): Qini and AUUC (scikit-uplift definitions),
  real uplift in the top 10% and 30%, policy profit of contacting the top 30% (₹150 per extra purchase or visit-equivalent, ₹1.02 per
  contact: **assumed**), and calibration by decile (average predicted vs measured uplift) for methods that predict an uplift size.

**A dataset "has a real effect"** if its average treatment effect on the full dataset has a 95% range above zero (decided from the data
alone, before any model is scored).

**Pass marks**
| Test | Pass mark |
|---|---|
| B1 | on every dataset with a real effect, the engine (fast engine) beats random: Qini 95% range above 0 |
| B2 | the engine (fast engine) is within 10% of the best method or better (Qini >= 0.9 x best Qini on the locked test) on at least 3 of 4 datasets |

**B1 and B2 are judged on ONE metric only: Qini (AUUC) on the locked 20% test.** Uplift in the top 10% / 30%, policy profit and
calibration are reported for information only.

The ensemble is reported against the same marks for information. If an outside method clearly wins (its Qini range is above the
engine's), adding it to the ensemble is **proposed, not done**.

**Environment rule.** If installing econml would change ANY app package version, it is not changed: econml goes into a second
environment (`validation/.venv_econml`), and only the outside methods run there, on the same saved splits (row ids saved to disk).

---

## Part C: robustness of the app's upload path

The app's real functions are fed each file: `upload.read_csv`, `guess_mapping`, `validate`, `prepare`, `fairness`, then
`planner.train` and `planner.plan` when the file is usable.

Files: missing values; text and category columns; extra and wrongly named columns; outcome all zeros; a 500-row file; a 95/5 split;
a **non-random file** (treatment given to the top spenders); duplicate ids; 3+ options; a revenue outcome; 10 lakh rows.

**Pass marks**
| Test | Pass mark |
|---|---|
| C1 | 0 crashes (no unhandled error) across all files |
| C2 | every bad file gives a clear plain-English message (shown and judged in the report, file by file) |
| C3 | the non-random file is flagged red |
| C4 | a 1 lakh-row file goes from upload to plan in < 60 s on this laptop (train + plan, timed) |

---

## Part D: stability

The same dataset (Part A's 50k, 2-arm, binary) is trained 5 times, changing only the models' random seed (seeds 1 to 5, through the
engine's `model_params`); the train/test split stays the same, so all runs score the same customers.

| Test | Pass mark |
|---|---|
| D1 | top-20% target list overlap >= 70% between runs (the average over all 10 pairs of runs; the lowest pair is also reported) |

---

## Additions approved 29 Oct 2026 (before any run)
1. Part B pass marks use Qini on the locked 20% test only (written into Part B above).
2. Parts C and D are confirmed in scope with the pass marks above unchanged.
3. econml in a second environment if it would change any app package (written into Part B above).
4. Overnight run: Part C failures are logged with the exact error and a proposed fix; **no app code is changed** until reviewed.
   Progress after every finished step goes in `VALIDATION_PROGRESS.md`.

## Test details the plan left open, fixed by Claude overnight BEFORE any Part A-D run (29 Oct 2026)
These are conditions, not pass marks; each one picks the stricter or more faithful choice.
- **A2, 2-arm contact cost: ₹5 per contact** (a 1-minute AI call, as in the app's synthetic sample). Reason: with +4 pts average lift
  and ₹150 per purchase, at ₹1.02 contacting everyone already earns about 88% of the oracle by construction, so a 70% mark would
  not test targeting at all. ₹1.02 (WhatsApp) is reported next to it **for information only**. A3 (null) keeps ₹1.02 as written.
- **A2, 4-arm costs:** option A = SMS reminder (₹0.10 per contact); option B = WhatsApp reminder (₹1.02 per contact);
  option C = ₹20 discount paid by every buyer who got it, sent by SMS (₹0.10 per contact).
- **Different contact costs per option are not settable in the app** (one channel cost for all options). The 4-arm plans are
  therefore made with the planner's own functions (`planner.train` with the ₹20 offer, then the decision rule of `planner.plan`:
  cautious vs fully personalised vs best simple plan, chosen on the 16% validation slice), with each option's own contact cost.
  That 10-line decision rule is checked to give **identical** plans to `planner.plan` on the 2-arm datasets. The missing
  per-option cost setting is logged as an app weakness.
- **A1, 4-arm:** each option's predicted value is compared with its true effect in the engine's own units (₹ profit after the
  offer cost for C, extra purchases or revenue for A and B); contact costs do not change a ranking.
- **B, missing values:** the LightGBM-based methods (likely-buyer, engine, ensemble) take missing values natively; for the
  econml methods missing values are filled with the training median (econml's forest does not accept them).
- **B, ranking only:** the fast engine's ranking is its predicted uplift for the option (the safety margin does not change a ranking).
- **C:** besides the function path, the Plan page itself is run headless (Streamlit's AppTest) on each file where possible, to
  catch crashes in the page code too.

## Run 2 (decided 30 Oct 2026, BEFORE any Run 2 run): what is judged, and on what data
Pass marks are unchanged. Run 1's results stay exactly as recorded. Changes are only to WHAT is judged and to the labels:
- **What runs:** the approved package built into `validation/app_v2/` (the real `app/` is untouched): Part C's 10 fixes; plan chosen
  on 5-fold out-of-fold values over the 80% (3 folds when the training sample has more than 1,50,000 rows); ranking = the thorough
  ensemble (S, X and DR learners, rank average), with the fast engine as automatic fallback if the ensemble fails; decile calibration
  of scores to uplift sizes; whole-file "no reliable signal" rule. Dropped: guard, causal forest, burden of proof, per-option rule.
- **B1 and B2 wording:** in Run 2, "the engine" means **the app's default ranking (the ensemble package)**; the fast engine is
  reported for information. (Run 1 judged the fast engine, as written then.)
- **Part B Run 2 is labelled "not independent":** the default was chosen partly using these 4 datasets. A new 80/20 split
  (seed 2036) and a fresh 10% Criteo sample (seed 2036) are used, but the datasets are the same.
- **Independent evidence:** Part A on fresh seeds (original + 9000) and the null test on seeds 9101-9120, never used before.
- **Part A, A1 with the ensemble:** Spearman between the calibrated predicted value and the true effect (a ranking that the
  "no reliable signal" rule makes constant counts as 0, as in development).
- **Extra reports (not pass-marked):** the Hillstrom sample's result with its 95% range, and whether the app's existing caution
  message shows on it; on the 2 lakh files, A1/A2 with 3 folds vs 5 folds (the accuracy cost of the speed rule); timing on 2 pinned
  cores (budget set by the user: 1 lakh rows <= 3 minutes, peak memory < 2 GB).

## Deliverables
1. This plan (shown before running).
2. VALIDATION_REPORT.md: one scorecard (part, test, result with 95% range, pass/fail), a 5-line plain summary, and the fixes made
   (each failing run kept next to its re-run).
3. Aggregates in `app/results/validation_*.json` (a Validation section on "How it was built" only after OK).
4. A ranked list of bugs and weaknesses, by how much each matters to a real company.
