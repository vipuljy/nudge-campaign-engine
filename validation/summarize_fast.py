"""Compact print of eval_fast results."""
import sys

import common


def show(name, r=None):
    r = r or common.load(name)
    print(f'== {name}')
    for v, m in r['variants'].items():
        vc = m.get('vs_current'); a2 = m.get('A2_ratio')
        print(f"  {v:12s} {m['recommended'][:30]:30s} contact {m['share_contacted']:.2f} measured {m['measured_extra_per_customer']:+.3f}"
              + (f" vs current {vc[0]:+.3f} [{vc[1]:+.3f}, {vc[2]:+.3f}]" if vc else '') + (f" A2 {a2:.3f}" if a2 is not None else '')
              + (f" | signal_fired {m['signal_fired']} proof {None if not m['proof'] else (round(m['proof']['gain'], 3), round(m['proof']['low95'], 3), m['proof']['proven'])} guard {m['guard_switched']}" if vc else '')
              + f" | {m['secs_decision']:.0f}s")


if __name__ == '__main__':
    for n in sys.argv[1:]:
        show(n)
