"""Run-time change for a 1,00,000-row upload: the app as is (train + plan) vs with the candidate fix (train + cross-fitted
decision + plan). Three repeats each, nothing else running; medians reported."""
import time

import numpy as np

import common
from lib import planner, upload
import candidate_fix
import part_c

if __name__ == '__main__':
    p = part_c.build_files()['rows_1lakh'][0]; df = upload.read_csv(p.read_bytes())
    m = {**upload.guess_mapping(df), 'labels': {}}; prep = upload.prepare(df, m)
    offers = {o: {'type': 'Reminder (no offer)'} for o in prep['options']}; runs = {'current': [], 'fix': []}
    for i in range(3):
        t0 = time.time(); res = planner.train(prep, 150.0, 0.10, offers); planner.plan(res, prep, 150.0, 0.10)
        runs['current'].append(time.time() - t0)
        t0 = time.time(); res = planner.train(prep, 150.0, 0.10, offers)
        candidate_fix.decide_cv(res, prep, 150.0, {o: 0.10 for o in prep['options']}); planner.plan(res, prep, 150.0, 0.10)
        runs['fix'].append(time.time() - t0)
        print(i + 1, {k: round(v[-1], 1) for k, v in runs.items()}, flush=True)
    out = {k: {'median_s': float(np.median(v)), 'min_s': float(min(v)), 'max_s': float(max(v))} for k, v in runs.items()}
    out['extra_s'] = out['fix']['median_s'] - out['current']['median_s']
    common.save('F_timing_1lakh', out); print(out)
