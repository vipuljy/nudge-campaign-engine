"""Part C: bad and edge-case uploads through the app's real upload path, exactly as the Plan page calls it:
read_csv -> guess_mapping (the dropdown defaults) -> validate (stops on errors) -> prepare -> fairness (red needs "Train anyway")
-> train -> plan, then the Money page's curves, the download's target_list and the thorough mode.
Every step is wrapped: an exception is a CRASH (recorded with its traceback). Money inputs are the page defaults for an upload:
₹150 per extra purchase or a 15% margin on amounts, SMS ₹0.10 per contact, every option a reminder.
Files are written to data_benchmarks/partC (git-ignored)."""
import io
import time
import traceback

import numpy as np
import pandas as pd

import common
from common import BENCH
from lib import planner, thorough, upload
import synth

DIR = BENCH / 'partC'; DIR.mkdir(parents=True, exist_ok=True)
VALUE_BIN, MARGIN, COST = 150.0, 0.15, 0.10


def _base(n, seed, arms=2, outcome='binary'):
    df, truth, _ = synth.make(n, arms, outcome, seed)
    return df


def build_files():
    """name -> (csv bytes, what a careful user would correct in the dropdowns, or None, description)."""
    F = {}
    rng = np.random.default_rng(7)

    d = _base(20_000, 301)
    for c in [f'x{i}' for i in range(10)]:
        d.loc[rng.random(len(d)) < 0.15, c] = np.nan
    d.loc[rng.random(len(d)) < 0.05, 'region'] = np.nan
    d.loc[rng.random(len(d)) < 0.02, 'bought'] = np.nan
    d.loc[rng.random(len(d)) < 0.01, 'option'] = np.nan
    F['missing_values'] = (d, None, '15% of each measure missing, 5% of a text measure, 2% of outcomes, 1% of options blank')

    d = _base(20_000, 302)
    d['city'] = rng.choice([f'City{i}' for i in range(60)], len(d))
    d['gender'] = rng.choice(['M', 'F', 'Other'], len(d))
    d['tier'] = rng.choice(['1', '2', '3'], len(d)).astype(object)
    d['signup_date'] = pd.Timestamp('2025-01-01') + pd.to_timedelta(rng.integers(0, 600, len(d)), 'D')
    d['vip'] = rng.choice(['Yes', 'No'], len(d))
    d['notes'] = [f'note {i}' for i in range(len(d))]
    F['text_columns'] = (d, None, 'text measures: city (60 values), gender, tier as text, a date, Yes/No, free text')

    d = _base(20_000, 303)
    d.insert(0, 'Unnamed: 0', np.arange(len(d)))
    d = d.rename(columns={'option': 'Treatment Group', 'bought': 'Purchased?', 'x3': 'spend (₹) last-90d', 'x4': 'Orders 30D'})
    d['Treatment Group'] = d['Treatment Group'].map({'No message': 'Holdout', 'Message': 'Got SMS'})
    d['Purchased?'] = d['Purchased?'].map({1: 'yes', 0: 'no'})
    d['constant'] = 1.0
    d['empty'] = np.nan
    d['post_campaign_spend'] = d['spend (₹) last-90d'] + rng.normal(size=len(d))
    F['extra_wrong_names'] = (d, {'control': 'Holdout'}, 'index column, odd names, control called "Holdout", outcome as yes/no, '
                                                         'a constant and an empty column, an after-campaign column')

    F['extra_wrong_names_userfixed'] = (d, {'control': 'Holdout', 'outcome': 'Purchased?'},
                                        'the same file after the user picks the right outcome ("Purchased?", yes/no text) in the dropdown')

    d = _base(20_000, 304); d['bought'] = 0
    F['outcome_all_zero'] = (d, None, 'nobody bought anything')

    F['rows_500'] = (_base(500, 305), None, '500 rows')

    d = _base(10_000, 306)
    d['option'] = np.where(rng.random(len(d)) < 0.95, 'Message', 'No message')
    F['split_95_5'] = (d, None, '95% got the message, 5% control (about 500 people)')

    d = _base(20_000, 307)
    d['option'] = np.where(d['x3'] > d['x3'].median(), 'Message', 'No message')     # company targeted its top spenders
    F['non_random'] = (d, None, 'the message went to the top half by a spend-like measure (x3): NOT random')

    d = _base(20_000, 308)
    dup = d.sample(2_000, random_state=1).copy(); dup['option'] = rng.choice(['Message', 'No message'], len(dup))
    d = pd.concat([d, dup], ignore_index=True)
    F['duplicate_ids'] = (d, {'id': 'customer_id'}, '2,000 customers appear twice (10%)')

    d = _base(40_000, 309, arms=4)
    d['option'] = np.where((d.option == 'SMS reminder') & (rng.random(len(d)) < 0.5), 'Email reminder', d.option)
    F['options_4plus'] = (d, None, 'control + 4 options')

    F['revenue'] = (_base(20_000, 310, outcome='revenue'), None, 'outcome is revenue (₹ amount)')

    F['rows_10lakh'] = (_base(1_000_000, 311), None, '10,00,000 rows')
    F['rows_1lakh'] = (_base(100_000, 312), None, '1,00,000 rows (C4 timing)')

    # extras (not in the plan's list; reported for information)
    F['x_not_a_csv'] = (b'PK\x03\x04\x14\x00\x06\x00binary excel-like junk\x00\xff\xfe', None, 'an Excel/zip file renamed .csv')
    F['x_header_only'] = (b'customer_id,option,bought,x0\n', None, 'header row, no data')
    d = _base(5_000, 313)
    F['x_semicolon'] = (d.to_csv(index=False, sep=';').encode(), None, 'semicolon-separated (European Excel export)')
    d = _base(20_000, 314); d['option'] = 'Message'
    F['x_no_control'] = (d, None, 'everyone got the message (no control group)')

    out = {}
    for k, (d, fix, desc) in F.items():
        b = d if isinstance(d, bytes) else d.to_csv(index=False).encode()
        p = DIR / f'{k}.csv'
        if not p.exists():
            p.write_bytes(b)
        out[k] = (p, fix, desc)
    return out


def run_file(name, path, fix, desc, do_thorough=True):
    r = {'file': name, 'description': desc, 'mb': round(path.stat().st_size / 1e6, 1), 'steps': {}, 'messages': [], 'crash': None}
    step = 'read_csv'
    try:
        t0 = time.time()
        try:
            df = upload.read_csv(path.read_bytes())
        except Exception as e:                             # the page catches this and shows its own message
            r['messages'].append(('error', f'Could not read this file as a CSV ({type(e).__name__}). Save it as comma-separated '
                                           'text and try again.'))
            r['stopped_at'] = 'read (handled by the page)'; return r
        r['rows'], r['cols'] = len(df), df.shape[1]; r['steps']['read_s'] = time.time() - t0
        step = 'guess_mapping'; g = upload.guess_mapping(df)
        r['guess'] = {k: v for k, v in g.items() if k != 'features'}; r['guess_features'] = g['features']
        m = {**g, 'labels': {}}
        if fix:
            m.update(fix); r['user_fix'] = fix
            for key in ('id', 'outcome'):                    # the page drops the chosen column from the measures list
                if key in fix:
                    m['features'] = [c for c in m['features'] if c != fix[key]]
        step = 'validate'; checks = upload.validate(df, m)
        r['messages'] += checks
        if any(l == 'error' for l, _ in checks):
            r['stopped_at'] = 'validate (error shown)'; return r
        step = 'prepare'; t0 = time.time(); prep = upload.prepare(df, m); r['steps']['prepare_s'] = time.time() - t0
        r['dropped'] = prep['dropped']; r['kind'] = prep['kind']; r['options'] = prep['options']
        step = 'fairness'; light, reason, ok = upload.fairness(prep['max_gap'], prep['min_group'], prep['n_control'])
        r['fairness'] = {'light': light, 'reason': reason, 'max_gap': prep['max_gap'], 'worst': prep['worst'], 'threshold': ok}
        value = VALUE_BIN if prep['kind'] == 'binary' else MARGIN
        offers = {o: {'type': 'Reminder (no offer)'} for o in prep['options']}
        step = 'train'; t0 = time.time(); res = planner.train(prep, value, COST, offers); r['steps']['train_s'] = time.time() - t0
        step = 'plan'; t0 = time.time(); P = planner.plan(res, prep, value, COST); r['steps']['plan_s'] = time.time() - t0
        r['plan'] = {'recommended': P['recommended'], 'rec_share': P['rec_share'], 'ladder_ok': P['ladder_ok'],
                     'diff_vs_usual': P['diff']['usual'], 'n_test': P['n_test']}
        step = 'curves (Money page)'; t0 = time.time(); C = planner.curves(res, prep, P); r['steps']['curves_s'] = time.time() - t0
        step = 'target_list (download)'; T = planner.target_list(res, prep, value, P['margin']); r['target_rows'] = len(T)
        if do_thorough:
            step = 'thorough.run'; t0 = time.time(); th = thorough.run(prep, res); r['steps']['thorough_s'] = time.time() - t0
            r['thorough_winner'] = {o: v['winner'] for o, v in th.items()}
        r['stopped_at'] = 'finished (plan shown)'
    except Exception as e:
        r['crash'] = {'step': step, 'error': f'{type(e).__name__}: {e}', 'traceback': traceback.format_exc()[-2500:]}
        r['stopped_at'] = f'CRASH at {step}'
    return r


def run_all(names=None, log=print):
    files = build_files(); out = common.load('C_robustness') or {}
    for k, (p, fix, desc) in files.items():
        if (names and k not in names) or k in out:
            continue
        log(f'{k}...')
        r = run_file(k, p, fix, desc, do_thorough=k not in ('rows_10lakh', 'rows_1lakh'))
        out[k] = r; common.save('C_robustness', out)
        log(f"  {r['stopped_at']}; fairness {r.get('fairness', {}).get('light')}; messages {len(r['messages'])}")
    return out
