"""Part A driver: 12 known-truth datasets + 20 null runs, cached as aggregates in validation/cache (re-run skips finished ones)."""
import sys
import time

import common
import part_a

SIZES = {5_000: 1, 50_000: 2, 200_000: 3}


def seed_of(n, arms, outcome):
    return SIZES[n] * 10 + arms + (0 if outcome == 'binary' else 100)


if __name__ == '__main__':
    t0 = time.time()
    for n in SIZES:
        for arms in (2, 4):
            for outcome in ('binary', 'revenue'):
                name = f'A_{n}_{arms}arm_{outcome}'
                if common.load(name):
                    continue
                t = time.time(); r = part_a.run_one(n, arms, outcome, seed_of(n, arms, outcome)); r['total_secs'] = time.time() - t
                common.save(name, r)
                a2 = r['A2'][r['judged_cost']]
                print(f"{name}: spearman {r['A1']['spearman']:.3f} [{r['A1']['low95']:.3f}, {r['A1']['high95']:.3f}] | "
                      f"plan/oracle {a2['ratio']:.3f} [{a2['low95']:.3f}, {a2['high95']:.3f}] ({a2['recommended']}) | {r['total_secs']:.0f} s",
                      flush=True)
    null = common.load('A3_null') or {'runs': []}
    done = {r['seed'] for r in null['runs']}
    for s in range(1, 21):
        if s in done:
            continue
        r = part_a.run_null(s); null['runs'].append(r); common.save('A3_null', null)
        print(f"null seed {s}: personalise={r['personalise']} -> {r['recommended']}", flush=True)
    print(f'Part A done in {time.time() - t0:.0f} s')
