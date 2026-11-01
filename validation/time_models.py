"""Model choice, run time and memory for a 1 lakh-row upload (Part C's rows_1lakh file: 2 arms, yes/no outcome), through the
v2 pipeline: planner.train (the app's split and engine) + 5-fold scores for the chosen model + the likely-buyer guard + the plan.
One model per process, so peak memory is that model's own. Run ALONE (no other job on the CPU).
    python validation/time_models.py <fast|ensemble|ensemble_cf> <threads> [rows=100000] [folds=5]
threads = 12 (this laptop) or 2 (Streamlit Community Cloud gives at most 2 cores and 2.7 GB of memory).
rows = 100000 (Part C's rows_1lakh) or 200000 (the first 2 lakh rows of Part C's rows_10lakh, saved once as rows_2lakh.csv).
The package timed: 5-fold (or 3-fold) scores + calibration + whole-file "no reliable signal" rule, no guard."""
import os
import sys
import threading
import time

model, threads = sys.argv[1], sys.argv[2]
rows = int(sys.argv[3]) if len(sys.argv) > 3 else 100_000; folds = int(sys.argv[4]) if len(sys.argv) > 4 else 5
os.environ['OMP_NUM_THREADS'] = threads; os.environ['NUDGE_JOBS'] = threads      # before LightGBM / joblib load

import psutil  # noqa: E402

if int(threads) < psutil.cpu_count():          # pin the process to N cores (LightGBM ignores OMP_NUM_THREADS on this laptop)
    psutil.Process().cpu_affinity(list(range(int(threads))))

import common  # noqa: E402
from lib import planner, upload  # noqa: E402
import engine_v2  # noqa: E402

peak = [0]


def watch():
    me = psutil.Process()
    while True:
        rss = me.memory_info().rss + sum(c.memory_info().rss for c in me.children(recursive=True) if c.is_running())
        peak[0] = max(peak[0], rss); time.sleep(0.2)


if __name__ == '__main__':
    threading.Thread(target=watch, daemon=True).start()
    me = psutil.Process(); cpu0 = sum(me.cpu_times()[:2]); wall0 = time.time()
    f = common.BENCH / 'partC' / ('rows_1lakh.csv' if rows == 100_000 else 'rows_2lakh.csv')
    if not f.exists():
        import pandas as pd
        pd.read_csv(common.BENCH / 'partC' / 'rows_10lakh.csv', nrows=rows).to_csv(f, index=False)
    df = upload.read_csv(f.read_bytes())
    t = {}; t0 = time.time()
    m = {**upload.guess_mapping(df), 'labels': {}}; prep = upload.prepare(df, m); t['read_prepare'] = time.time() - t0
    t0 = time.time(); res = planner.train(prep, 150.0, 0.10, {o: {'type': 'Reminder (no offer)'} for o in prep['options']})
    t['planner_train'] = time.time() - t0
    t0 = time.time(); planner.plan(res, prep, 150.0, 0.10); t['current_plan_step'] = time.time() - t0
    t0 = time.time(); sc = engine_v2.scores(res, prep, rankers=(model,), folds=folds, log=lambda m: print(time.strftime('%H:%M:%S'), m, flush=True)); t['scores_kfold'] = time.time() - t0
    t0 = time.time(); P = engine_v2.plan(res, prep, 150.0, {o: 0.10 for o in prep['options']}, sc, ranker=model, guard=False, signal='file'); t['plan'] = time.time() - t0
    t['current_app_total'] = t['read_prepare'] + t['planner_train'] + t['current_plan_step']
    t['v2_total'] = t['current_app_total'] + t['scores_kfold'] + t['plan']          # conservative: the app's own plan step stays
    cores_busy = (sum(me.cpu_times()[:2]) - cpu0) / (time.time() - wall0)
    out = common.load('T_models_1lakh') or {}
    out[f'{model}@{threads}threads_{rows}rows_{folds}folds'] = {'secs': t, 'secs_by_model': sc['secs'], 'peak_memory_mb': peak[0] / 1e6, 'rows': len(df), 'folds': folds,
                                 'recommended': P['recommended'], 'avg_cores_busy': cores_busy, 'pinned_cores': int(threads) < psutil.cpu_count()}
    common.save('T_models_1lakh', out); print('RESULT', model, threads, rows, folds, round(cores_busy, 1), 'cores busy', {k: round(v, 1) for k, v in t.items()}, round(peak[0] / 1e6), 'MB', flush=True)
