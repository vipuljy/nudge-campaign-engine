"""Copies the validation AGGREGATES to app/results/validation_*.json (no rows, no local paths, no tracebacks)."""
import json

import common
import scorecard


def _clean(o):
    """Drop tracebacks and anything that looks like a local path."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items() if k not in ('traceback', 'guess_features')}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    if isinstance(o, str) and ('C:\\' in o or 'C:/' in o or '\\Users\\' in o):
        return o.split(' File ')[0][:200] if 'Error' in o else '[local path removed]'
    return o


def run():
    A = scorecard.part_a('A'); R2 = scorecard.part_a('run2')
    N1, N2 = scorecard.null('A'), scorecard.null('run2')
    out = {
        'part_a': {'run1_app_as_is': A.to_dict('records'), 'run2_candidate_fix_not_in_app': R2.to_dict('records'),
                   'null_run1': {k: v for k, v in N1.items() if k != 'table'} | {'runs_detail': N1['table'].to_dict('records')},
                   'null_run2': {k: v for k, v in N2.items() if k != 'table'} | {'runs_detail': N2['table'].to_dict('records')}},
        'part_b': {d: _clean({k: v for k, v in common.load(f'B_{d}').items() if k != 'checks'}) for d in scorecard.DATASETS},
        'part_b_run1_file_order': {d: {m: {k: v[k] for k in ('qini', 'qini_low95', 'qini_high95') if k in v}
                                       for m, v in common.load(f'B_{d}_run1_fileorder')['methods'].items()} for d in scorecard.DATASETS},
        'part_c': _clean(common.load('C_robustness')), 'part_c_pages': _clean(common.load('C_apptest')),
        'part_c4_timing': common.load('C4_timing'), 'part_d': common.load('D_stability'),
    }
    for k, v in out.items():
        p = common.RESULTS / f'validation_{k}.json'
        p.write_text(json.dumps(v, indent=1, default=common._default, ensure_ascii=False), encoding='utf-8')
        print(p.name, round(p.stat().st_size / 1024, 1), 'KB')


if __name__ == '__main__':
    run()
