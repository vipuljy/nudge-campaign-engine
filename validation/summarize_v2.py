"""Prints the development results of the v2 improvements (eval_v2 outputs) as compact tables."""
import sys

import common

R = lambda x: None if x is None else round(x, 3)


def show(name):
    r = common.load(name)
    if not r:
        return
    print(f'\n== {name}  scores {round(r["secs_scores"])} s {({k: round(v) for k, v in r["secs_by_model"].items()})}  app engine slope {({o: R(v) for o, v in r["slope_app_engine"].items()})}')
    for v, m in r['variants'].items():
        po = {o: (d['used'], R(d['test_qini']), R(d['slope_calibrated']), d['rank_unchanged'], 'signal' if d['reliable'] else 'NO signal')
              for o, d in m['per_option'].items()}
        oof = {o: {k: R(x) for k, x in d['oof_qini'].items()} | {'lo': R(d['oof_qini_used_low95'])} for o, d in m['oof_diag'].items()}
        e = m['measured_extra_per_customer']
        extra = f" A2 {R(m['A2_ratio'])} A1 {R(m['A1_spearman_used'])}" if 'A2_ratio' in m else ''
        print(f"  {v:22s} {m['recommended'][:34]:34s} contact {m['share_contacted']:.2f} measured {e[0]:+.3f} [{e[1]:+.3f},{e[2]:+.3f}]{extra}")
        print(f"      test: {po}")
        print(f"      OOF qini: {oof}  msg: {bool(m['message'])}")


if __name__ == '__main__':
    for n in sys.argv[1:]:
        show(n)
