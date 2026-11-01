"""Writes notebooks/12_validation.ipynb: the readable front end of the validation. Each part explains what and why, runs its
driver if its cached results are missing, then shows the results against the frozen pass marks."""
import nbformat as nbf

C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))
code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# 12 · External validation of the Nudge engine and app

**Why:** Steps 1-10 validated Nudge on the data it was built with. This notebook tests it from the outside: on data where the
true answer is known (Part A), on four public uplift benchmarks against outside methods (Part B), on bad and unusual uploads
(Part C) and for stability (Part D). It tests the **app's own code** (`app/lib/planner.py`, `app/lib/upload.py`,
`app/nudge_engine.py`), so a pass means the deployed app works.

**Rules:** the pass marks were written in `VALIDATION_PLAN.md` before any run and are not changed. Fixed seeds. Every result has a
95% range (bootstrap, 200 repeats). Raw rows stay in `data_benchmarks/` (git-ignored); only aggregates are saved.

**How it runs:** the heavy work lives in small helper files in `validation/` (one per part). Each part below re-runs its helper
only if its cached results (`validation/cache/*.json`) are missing, so this notebook opens in seconds; delete the cache to re-run
from scratch (about 1.5 hours, mostly Part B's causal forest). Environment: `validation/.venv` (kernel "Nudge validation").""")

code("""import sys, json
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent / 'validation'))
import pandas as pd
pd.set_option('display.width', 220); pd.set_option('display.max_columns', 30); pd.set_option('display.precision', 3)
import common, scorecard""")

md("""## Part A · Known truth (synthetic customers)

**What:** 12 made-up campaign tests where we *planted* the true effect for every customer: 30% buy anyway, the message adds
+4 pts on average (SD 4 pts), about 16% are put off by it. 4-arm files have 3 options with different costs (SMS ₹0.10,
WhatsApp ₹1.02, a ₹20 discount paid by buyers), each helping different customers.

**Why:** on real data nobody knows each customer's true response, so we can only score rankings. Here we can check directly:
does the engine rank customers in the right order (A1, Spearman), and how much of the best possible profit does the app's plan
earn (A2, plan ÷ oracle)? A3 feeds it data with **no effect at all**: a good tool must then say "do not personalise".

Pass marks: A1 Spearman ≥ 0.5 on each 50k file; A2 ≥ 70% of oracle on each 50k and 2 lakh file; A3 ≥ 18 of 20.""")

code("""if not common.load('A3_null'):
    import runpy; runpy.run_path(str(common.ROOT / 'validation' / 'run_part_a.py'), run_name='__main__')
A = scorecard.part_a('A'); A""")

code("""a50, a2l = A[A.rows == 50_000], A[A.rows == 200_000]
print('A1 at 50k  :', 'PASS' if (a50['A1 Spearman'] >= 0.5).all() else 'FAIL', f"({(a50['A1 Spearman'] >= 0.5).sum()} of 4 files >= 0.5)")
print('A2 at 50k+ :', 'PASS' if (pd.concat([a50, a2l])['A2 plan/oracle'] >= 0.7).all() else 'FAIL',
      f"(50k: {(a50['A2 plan/oracle'] >= 0.7).sum()} of 4, 2 lakh: {(a2l['A2 plan/oracle'] >= 0.7).sum()} of 4)")
N = scorecard.null('A')
print(f"A3 null    : {'PASS' if N['not_personalised'] >= 18 else 'FAIL'} ({N['not_personalised']} of 20 'do not personalise'; "
      f"95% range of the rate {N['low95_rate']:.2f} to {N['high95_rate']:.2f})")
N['table'].T""")

md("""### Why Part A failed at 50k: the diagnosis

For each 50k file: the **true** share of the oracle profit that each plan the planner could choose would earn, and what the
16% validation slice (8,000 customers) said about it. The engine's personalised plans are close to 70% of the oracle, but the
slice is too noisy to pick between them and "contact everyone"; on the 2-arm binary file it picked "everyone" (32%) over a
personalised plan (70%).""")

code("""import diagnose_a, run_part_a
r = diagnose_a.candidates(50_000, 2, 'binary', run_part_a.seed_of(50_000, 2, 'binary'))
print('chosen by the app:', r.attrs['chosen'], '| learned margin', r.attrs['learned_margin']); r""")

md("""### Run 2: a candidate fix (tested here only, the app is NOT changed)

**Candidate:** decide between plans with 5-fold cross-fitting on the whole 80% instead of one 16% slice, and train the final
engine on the 80% (`validation/candidate_fix.py`). Settings were chosen on separate development seeds, then run **once** on the
official seeds. Both runs are kept.""")

code("""R2 = scorecard.part_a('run2')
if len(R2):
    cmp = A.merge(R2, on=['rows', 'options', 'outcome'], suffixes=(' run1', ' run2'))
    display(cmp[['rows', 'options', 'outcome', 'A1 Spearman run1', 'A1 Spearman run2', 'A2 plan/oracle run1', 'A2 plan/oracle run2',
                 'A2 low95 run2', 'A2 high95 run2', 'plan chosen run1', 'plan chosen run2']])
    N2 = scorecard.null('run2')
    if N2: print(f"A3 null run 2: {N2['not_personalised']} of {N2['runs']} 'do not personalise'")""")

md("""## Part B · Public benchmarks vs outside methods

**What:** Criteo (ads, 10% sample), Lenta (grocery SMS), MegaFon (telecom), Hillstrom (e-mail). Locked 20% test; every method
trains on the same 2 lakh rows of the rest. Methods: random order, likely-buyer model (the usual approach), the Nudge fast engine
(app default), the Nudge ensemble (thorough mode), econml's CausalForestDML and R-learner.

**Why:** a tool that only beats random proves little. Here it competes with well-known outside methods on data it never saw.

Pass marks (judged on Qini only): B1 engine Qini 95% range above 0 on every dataset with a real effect; B2 engine within 10% of
the best method on ≥ 3 of 4 datasets.""")

code("""B = scorecard.part_b()
marks = scorecard.b_marks(B); marks""")

code("""for d, (r, t) in B.items():
    print(f"\\n{d}: {r['description']}\\n  {r['rows_total']:,} rows; train {r['rows_train']:,}; locked test {r['rows_test']:,}; "
          f"treated {r['treated_share']:.0%}; outcome rate {r['outcome_rate']:.2%}; app fairness light: {r['fairness']} (largest gap {r['max_gap']:.3f})")
    cols = ['qini', 'qini_low95', 'qini_high95', 'auuc', 'top10_lift', 'top30_lift', 'profit_top30_per_customer', 'engine_minus_this_qini',
            'engine_minus_this_qini_low95', 'engine_minus_this_qini_high95']
    display(t[[c for c in cols if c in t]].drop(index='Treat everyone').astype(float).round(4))""")

code("""# calibration by decile (methods that predict an uplift size): average predicted vs measured uplift; slope 1 = well calibrated
for d, (r, t) in B.items():
    for m in ['Nudge fast engine', 'econml CausalForestDML', 'econml R-learner (NonParamDML)']:
        c = t.loc[m, 'calibration']
        print(f"{d:9s} {m:32s} slope {c['slope_measured_on_predicted']:+.2f}")""")

md("""## Part C · Bad and unusual uploads

**What:** 12 files from the plan's list plus 4 extras, each pushed through the app's real upload path (read, column guess,
checks, preparation, fairness light, train, plan, Money page curves, the download, thorough mode) and, as a second layer, through
the real pages run headless (Streamlit AppTest through `app.py`).

**Why:** real users upload messy files. The app must never crash, must say clearly what is wrong, and must refuse to pretend a
non-random file is a fair test. Pass marks: C1 0 crashes; C2 clear messages; C3 non-random file red; C4 1 lakh rows planned in < 60 s.
**No app code was changed**: failures are logged with a proposed fix for review.""")

code("""Cr = common.load('C_robustness')
rows = []
for k, v in Cr.items():
    rows.append({'file': k, 'what': v['description'], 'result': v['stopped_at'], 'fairness': (v.get('fairness') or {}).get('light'),
                 'plan': (v.get('plan') or {}).get('recommended'), 'messages': ' | '.join(f'{l}: {m}' for l, m in v['messages'])[:300],
                 'crash': (v['crash'] or {}).get('error')})
pd.DataFrame(rows).set_index('file')""")

code("""T = common.load('C_apptest') or {}
pd.DataFrame([{'file': k, 'stages': ' > '.join(s[0] for s in v.get('stages', [])),
               'page exceptions': sum(len(s[1].get('exceptions', [])) for s in v.get('stages', [])),
               'first exception': next((s[1]['exceptions'][0][:200] for s in v.get('stages', []) if s[1].get('exceptions')), None)}
              for k, v in T.items()]).set_index('file')""")

code("""t4 = common.load('C4_timing')
if t4: print(f"C4: 1,00,000 rows, upload to plan {t4['total_s']:.1f} s (read {t4['read_s']:.1f}, prepare {t4['prepare_s']:.1f}, "
             f"train {t4['train_s']:.1f}, plan {t4['plan_s']:.1f}) -> {'PASS' if t4['total_s'] < 60 else 'FAIL'}")""")

md("""## Part D · Stability

**What:** the same 50k file trained 5 times, changing only the models' random seed. **Why:** if the top-20% target list changed a
lot between runs, a marketing team could not trust it. Pass mark: average overlap ≥ 70%.""")

code("""D = common.load('D_stability')
print(f"D1: average top-20% overlap {D['average_overlap']:.3f} (95% range {D['average_low95']:.3f} to {D['average_high95']:.3f}); "
      f"lowest pair {D['lowest_pair']} {D['lowest_overlap']:.3f} -> {'PASS' if D['pass'] else 'FAIL'}")
pd.Series(D['pairs'], name='overlap').to_frame().T""")

md("""## Scorecard and what it means
See `VALIDATION_REPORT.md` for the scorecard, the plain summary, the Part C failure list with proposed fixes, and the ranked
list of weaknesses.""")

nb = nbf.v4.new_notebook(); nb['cells'] = C
nb['metadata']['kernelspec'] = {'name': 'nudge-validation', 'display_name': 'Nudge validation', 'language': 'python'}
nbf.write(nb, 'notebooks/12_validation.ipynb')
print('written notebooks/12_validation.ipynb')
