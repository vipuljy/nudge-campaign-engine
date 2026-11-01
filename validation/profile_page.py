"""Diagnosis only: why the Plan page is slow with the robust engine. Counts and times RobustEngine scoring calls during one page
build (AppTest), and records which page lines call them. Run with NUDGE_APP=validation/app_v2 NUDGE_RUN=diag."""
import collections
import sys
import time
import traceback

import common
from lib import robust, upload
import apptest_page

calls = collections.Counter(); secs = collections.Counter(); misses = [0]
orig = robust.RobustEngine._uplift


def timed(self, df):
    hit = any(d is df for d, _ in self._cache)
    t0 = time.time(); out = orig(self, df); dt = time.time() - t0
    where = next((f'{f.filename.split(chr(92))[-1]}:{f.lineno} {f.name}' for f in reversed(traceback.extract_stack()[:-1])
                  if 'views' in f.filename), 'not from a page')
    calls[where] += 1; secs[where] += dt; misses[0] += not hit
    return out


robust.RobustEngine._uplift = timed

if __name__ == '__main__':
    name = sys.argv[1]
    df = upload.read_csv((common.BENCH / 'partC' / f'{name}.csv').read_bytes())
    t0 = time.time(); r = apptest_page.run_page(name, df); print('page', round(time.time() - t0), 's', r.get('harness_error', '')[:100])
    for w, c in calls.most_common(15):
        print(f'{c:5d} calls {secs[w]:8.1f} s  {w}')
    print('cache misses', misses[0])
