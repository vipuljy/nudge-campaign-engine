"""Driver for the fair before/after test of the candidate fix. Re-running skips finished items.
    python validation/run_compare_fix.py   (original seeds, fresh seeds, the app's samples, Hillstrom + MegaFon via the planner)"""
import compare_fix as cf


def log(s):
    print(s, flush=True)


if __name__ == '__main__':
    cf.run_seeds('original', 0, range(1, 21), log)
    cf.run_seeds('fresh', cf.FRESH, range(7101, 7121), log)
    import common
    for k in ['synthetic', 'hillstrom']:
        if not common.load(f'F_sample_{k}'):
            cf.app_sample(k, log)
    for d in ['hillstrom', 'megafon']:
        if not common.load(f'F_bench_{d}'):
            cf.benchmark_planner(d, log)
    log('done')
