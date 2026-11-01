"""EXTRA, NOT PART OF THE PASS MARK: Lenta with the fast engine and the causal forest trained on ALL of the 80% training part
(5.5 lakh rows, no 2-lakh cap). Same locked 20% test, same features (app's prepare), same random tie-break (seed 2027) and the
same 200 paired bootstrap resamples as Part B. Nothing is tuned on the test."""
import time

import numpy as np
import pandas as pd

import common
from lib import upload
import part_b

if __name__ == '__main__':
    X, y, t, desc = part_b.load('lenta')
    tr200, te = part_b.splits('lenta', y, t)
    rest = np.setdiff1d(np.arange(len(y)), te)                       # the whole 80% training part
    keep = np.r_[rest, te]
    raw = X.iloc[keep].assign(_arm=np.where(t[keep] == 1, 'treat', 'control'), _out=y[keep]).reset_index(drop=True)
    del X
    m = {'option': '_arm', 'control': 'control', 'outcome': '_out', 'id': None, 'features': [c for c in raw.columns if c not in ('_arm', '_out')],
         'labels': {}}
    prep = upload.prepare(raw, m); del raw
    D, feats, n = prep['data'], prep['features'], len(rest)
    Xtr, Xte = D[feats].iloc[:n].reset_index(drop=True), D[feats].iloc[n:].reset_index(drop=True)
    ytr, yte, ttr, tte = y[rest], y[te], t[rest], t[te]
    del prep, D
    out = {'note': 'EXTRA, not part of the pass mark', 'rows_train': int(n), 'rows_test': int(len(te)), 'secs': {}}
    scores = {}
    for name, f in [('Nudge fast engine (all 80%)', part_b.m_engine), ('econml CausalForestDML (all 80%)', part_b.m_causal_forest)]:
        p = part_b.SCORES / f"lenta_alltrain__{''.join(ch for ch in name if ch.isalnum())}.npy"
        t0 = time.time()
        scores[name] = np.load(p) if p.exists() else np.asarray(f(Xtr, ytr, ttr, Xte), float)
        np.save(p, scores[name]); out['secs'][name] = time.time() - t0; print(name, round(out['secs'][name]), 's', flush=True)
    for name in ['Nudge fast engine', 'econml CausalForestDML']:                 # the 2-lakh runs, for side-by-side
        scores[name + ' (2 lakh, Part B)'] = np.load(part_b.SCORES / f"lenta__{''.join(ch for ch in name if ch.isalnum())}.npy")
    perm = np.random.default_rng(part_b.SEED + 1).permutation(len(yte))
    yte, tte = yte[perm], tte[perm]; scores = {k: u[perm] for k, u in scores.items()}
    rng = np.random.default_rng(1); B = [rng.integers(0, len(yte), len(yte)) for _ in range(200)]
    rows = {}
    for k, u in scores.items():
        bq = [part_b.metrics(yte[i], tte[i], u[i])['qini'] for i in B]
        rows[k] = {'qini': part_b.metrics(yte, tte, u)['qini'], 'qini_low95': float(np.percentile(bq, 2.5)),
                   'qini_high95': float(np.percentile(bq, 97.5))}
        rows[k]['range_above_0'] = rows[k]['qini_low95'] > 0
        print(k, {a: round(b, 4) if isinstance(b, float) else b for a, b in rows[k].items()}, flush=True)
    out['methods'] = rows
    common.save('B_lenta_extra_alltrain', out)
