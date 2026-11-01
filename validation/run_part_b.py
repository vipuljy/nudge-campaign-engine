"""Part B driver: the four benchmarks in turn (Criteo waits for its download). Re-running skips methods already scored."""
import time
from pathlib import Path

import part_b

if __name__ == '__main__':
    t0 = time.time()
    crit = part_b.RAW / 'criteo' / 'criteo-research-uplift-v2.1.csv.gz'
    for name in ['hillstrom', 'megafon', 'lenta', 'criteo10']:
        if name == 'criteo10':
            while not (crit.exists() and crit.stat().st_size >= 311_422_618):
                time.sleep(20)
        t = time.time(); print(f'{name}...', flush=True)
        r = part_b.run(name, log=lambda s: print(s, flush=True))
        e = r['methods']['Nudge fast engine']
        best = max((v['qini'], m) for m, v in r['methods'].items() if v.get('qini') is not None)
        print(f"{name}: engine Qini {e['qini']:.4f} [{e['qini_low95']:.4f}, {e['qini_high95']:.4f}]; best {best[1]} {best[0]:.4f}; "
              f"{time.time() - t:.0f} s", flush=True)
    print(f'Part B done in {time.time() - t0:.0f} s')
