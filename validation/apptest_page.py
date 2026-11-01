"""Part C, second layer: run the real Plan page headless (Streamlit AppTest) on a file, press "Build my plan" (and tick
"Train anyway" when the fairness light is red), and collect every error, warning and uncaught exception the page shows.
Run from app/ so the page's relative paths work."""
import os
import sys
import traceback

import pandas as pd

import common
from streamlit.testing.v1 import AppTest

ENTRY = str(common.APP / 'app.py')            # the real entry point, so st.navigation and page links work


def _texts(at):
    return {'errors': [e.value for e in at.error], 'warnings': [w.value for w in at.warning],
            'exceptions': [getattr(x, 'message', str(x)) + '\n' + '\n'.join(getattr(x, 'stack_trace', [])[-6:]) for x in at.exception]}


def run_page(name, df, sample=None):
    os.chdir(common.APP)
    out = {'file': name, 'stages': []}
    try:
        at = AppTest.from_file(ENTRY, default_timeout=900)
        at.session_state['data_src'] = {'name': f'{name}.csv', 'df': df, 'sample': sample}
        at.run(); at.switch_page('views/plan.py'); at.run(); out['stages'].append(('loaded', _texts(at)))
        if at.exception:
            return out
        box = [c for c in at.checkbox if 'Train anyway' in str(c.label)]
        if box:
            box[0].check(); at.run(); out['stages'].append(('train anyway ticked', _texts(at)))
        btn = [b for b in at.button if 'Build my plan' in str(b.label)]
        if not btn:
            out['stages'].append(('no build button (page stopped earlier)', {})); return out
        btn[0].click(); at.run(); out['stages'].append(('built (after rerun)', _texts(at)))
        out['success'] = [s.value for s in at.success][:3]
        out['markdown_count'] = len(at.markdown)
        out['plan_texts'] = [m.value for m in at.markdown] + [i.value for i in at.info]   # to check which messages show
        for page in ['views/money.py', 'views/prove.py']:              # the other pages that read the plan
            at.switch_page(page); at.run(); out['stages'].append((page, _texts(at)))
            btn = [b for b in at.button if any(w in str(b.label) for w in ('Measure', 'Build', 'Calculate', 'Run'))]
            if btn:
                btn[0].click(); at.run(); out['stages'].append((f'{page}: pressed "{btn[0].label}"', _texts(at)))
    except Exception as e:
        out['harness_error'] = f'{type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}'
    return out


if __name__ == '__main__':
    import part_c
    from lib import upload
    files = part_c.build_files()
    names = sys.argv[1:] or [k for k in files if k not in ('rows_10lakh',)]
    res = common.load('C_apptest') or {}
    for k in names:
        p = files[k][0]
        try:
            df = upload.read_csv(p.read_bytes())          # the page's own reader (run 1 used pandas' default reader)
        except Exception as e:
            res[k] = {'file': k, 'note': f'not readable by pandas ({type(e).__name__}); the page shows its read error before this point'}
            common.save('C_apptest', res); continue
        r = run_page(k, df); res[k] = r; common.save('C_apptest', res)
        exc = [s for s in r['stages'] if s[1].get('exceptions')]
        print(k, '| stages:', [s[0] for s in r['stages']], '| EXCEPTIONS:', len(exc), '| harness:', r.get('harness_error', '')[:200], flush=True)
