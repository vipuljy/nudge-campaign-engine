"""C4: a 1,00,000-row upload, from the file's bytes to the plan on screen (read, guess, checks, prepare, fairness, train, plan),
timed on this laptop with nothing else running. Three repeats; the median is judged."""
import time

import numpy as np

import common
from lib import planner, upload
import part_c

if __name__ == '__main__':
    p = part_c.build_files()['rows_1lakh'][0]; raw = p.read_bytes(); runs = []
    for i in range(3):
        upload.read_csv.clear()                                   # no cache help between repeats
        t = {}; t0 = time.time()
        df = upload.read_csv(raw); t['read_s'] = time.time() - t0
        m = {**upload.guess_mapping(df), 'labels': {}}; upload.validate(df, m)
        t1 = time.time(); prep = upload.prepare(df, m); upload.fairness(prep['max_gap'], prep['min_group'], prep['n_control'])
        t['prepare_s'] = time.time() - t1
        t1 = time.time(); res = planner.train(prep, 150.0, 0.10, {o: {'type': 'Reminder (no offer)'} for o in prep['options']})
        t['train_s'] = time.time() - t1
        t1 = time.time(); planner.plan(res, prep, 150.0, 0.10); t['plan_s'] = time.time() - t1
        t['total_s'] = time.time() - t0; runs.append(t); print(i + 1, {k: round(v, 1) for k, v in t.items()}, flush=True)
    med = {k: float(np.median([r[k] for r in runs])) for k in runs[0]}
    common.save('C4_timing', {**med, 'runs': runs, 'rows': len(df), 'pass': med['total_s'] < 60})
    print('median', {k: round(v, 1) for k, v in med.items()}, 'PASS' if med['total_s'] < 60 else 'FAIL')
