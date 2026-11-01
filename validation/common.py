"""Shared set-up for the validation helpers: import the APP's code (not the notebook copy), fixed seeds, bootstrap ranges, saving."""
import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / os.environ.get('NUDGE_APP', 'app')     # NUDGE_APP=validation/app_v2 tests the fixed copy (the real app/ is untouched)
RUN = os.environ.get('NUDGE_RUN', '')                # NUDGE_RUN=run2: results saved as run2_<name>, so run 1 is never overwritten
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))                     # app/ first, so `lib.*` and `nudge_engine` are the deployed app's own files
warnings.filterwarnings('ignore')
import logging                                       # Streamlit's "no runtime" notices when lib.upload is used outside the app
import streamlit  # noqa: E402,F401  (import first: Streamlit sets its own log levels on import)
for name in ['streamlit', 'streamlit.runtime.caching.cache_data_api', 'streamlit.runtime.scriptrunner_utils.script_run_context']:
    logging.getLogger(name).setLevel(logging.ERROR)

CACHE = ROOT / 'validation' / 'cache'; CACHE.mkdir(parents=True, exist_ok=True)       # aggregates only
BENCH = ROOT / 'data_benchmarks'                                                       # raw rows and row-level scores (git-ignored)
RESULTS = APP / 'results'


def boot_range(stat, n, n_boot=200, seed=1):
    """95% range of stat(idx) over bootstrap resamples of n rows (stat takes an index array)."""
    rng = np.random.default_rng(seed)
    vals = np.array([stat(rng.integers(0, n, n)) for _ in range(n_boot)])
    return float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))


def save(name, obj):
    """Aggregates as JSON in validation/cache (copied to app/results at the end)."""
    p = CACHE / f'{RUN + "_" if RUN else ""}{name}.json'
    p.write_text(json.dumps(obj, indent=1, default=_default), encoding='utf-8')
    return p


def load(name):
    p = CACHE / f'{RUN + "_" if RUN else ""}{name}.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


class Timer:
    def __enter__(self):
        self.t = time.time(); return self

    def __exit__(self, *a):
        self.secs = time.time() - self.t
