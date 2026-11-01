"""Download the four public uplift benchmarks once (scikit-uplift fetchers) into data_benchmarks/raw (git-ignored).
Prints the size on disk and the time taken. Run from the repo root."""
import time
from pathlib import Path

from sklift.datasets import fetch_criteo, fetch_hillstrom, fetch_lenta, fetch_megafon

RAW = Path('data_benchmarks/raw'); RAW.mkdir(parents=True, exist_ok=True)
t0 = time.time()
for name, f in [('hillstrom', lambda: fetch_hillstrom(data_home=str(RAW))),
                ('megafon', lambda: fetch_megafon(data_home=str(RAW))),
                ('lenta', lambda: fetch_lenta(data_home=str(RAW))),
                ('criteo10', lambda: fetch_criteo(data_home=str(RAW), percent10=True))]:
    t = time.time(); b = f()
    print(f'{name}: {len(b.data):,} rows x {b.data.shape[1]} columns, {time.time() - t:.0f} s', flush=True)
size = sum(p.stat().st_size for p in RAW.rglob('*') if p.is_file())
print(f'TOTAL on disk: {size / 1e6:,.0f} MB; {time.time() - t0:.0f} s')
for p in sorted(RAW.rglob('*')):
    if p.is_file():
        print(f'  {p.stat().st_size / 1e6:8.1f} MB  {p}')
