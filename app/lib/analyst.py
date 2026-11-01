"""AI analyst: answers questions about the numbers on screen and the project's methods, and nothing else.

How it stays honest:
  1. Each page publishes a FACT SHEET: short sentences with the numbers it shows ("[F3] Nudge profit ... ₹2.44 lakh").
  2. The model gets only the fact sheet + a methods note, must cite facts like [F3], and must say "I don't know from this data"
     when the facts do not answer the question.
  3. After the answer, every number in it is checked against the fact sheet; numbers that are not there are flagged.
Free provider: Groq (OpenAI's open-weight gpt-oss-120b, then gpt-oss-20b as backup). No key or no quota: rule-based answers.
The key is read from Streamlit secrets or the GROQ_API_KEY environment variable, never from the code.
"""
import datetime as dt
import os
import re

import requests
import streamlit as st

from lib import fmt, x5

URL = 'https://api.groq.com/openai/v1/chat/completions'
# (model, daily request cap for the app's shared key: 80% of Groq's free 1,000 requests a day; Groq also allows ~8,000 tokens a minute)
MODELS = [('openai/gpt-oss-120b', 800), ('openai/gpt-oss-20b', 800)]
NAMES = {'openai/gpt-oss-120b': 'gpt-oss-120b', 'openai/gpt-oss-20b': 'gpt-oss-20b, the smaller backup model'}
PER_VISITOR = 30                                                                  # questions per browser session
NOT_KNOWN = "I don't know from this data."

METHODS = """Methods and terms (plain words):
- Uplift: the extra chance that a customer buys BECAUSE of a contact, compared with not contacting them. Nudge ranks customers by uplift,
  not by how likely they are to buy; likely buyers often buy anyway, so contacting them wastes money.
- Random test: some customers get an option at random, others (the control group) get nothing. Only this shows what a campaign caused.
  Without it, the company usually targets its best customers, who would buy more anyway, and any analysis can mislead.
- Fair report vs usual report: a usual report credits the campaign with every buyer who was contacted; a fair report subtracts what
  randomly held-back look-alikes did.
- Nudge engine: one doubly robust (DR) uplift model per option, using LightGBM with cross-fitting. It gives a customer their personal best
  option only when that clearly beats the best option on average (a safety margin learned from the data).
- Plan choice: the file is split into 80% and an untouched 20%. On the 80%, every customer is scored by models that never saw them
  (5 folds), and those honest scores choose between personalised plans and the best simple plan (contact everyone or nobody). If the
  ranking does not beat a random order there, Nudge says "no reliable signal" and keeps the simple plan. If the untouched 20% then shows the
  personalised plan earning less than the simple plan, Nudge recommends the simple plan (a final yes/no check). Every number shown is measured on the untouched 20%,
  so the winner is not flattered. If personalising does not pay, Nudge keeps the simple plan (the safe fallback).
- Usual approach: a model of who is most likely to buy when contacted (the common CRM practice), contacting the same number of customers.
- Measured vs assumed: measured numbers are counted on customers the model never saw; assumed numbers are business inputs
  (profit per purchase, cost per contact, offer costs) that the user can change.
- 95% range: the result would fall in this range in 95 out of 100 repeats of the test (bootstrap).
- Qini: how much better a ranking finds extra buyers than a random order (area between its gain curve and random). Higher is better; 0 is random.
- Lift ladder: real lift in the top, middle and bottom thirds as ranked by the model; a working model shows top > middle > bottom.
- Offer costs: a discount or cashback is paid to EVERY buyer who gets it, including those who would have bought anyway; that is why
  discounting everyone is usually unprofitable. Break-even = how much extra buying an offer must cause to pay for its cost.
- Control group size: the smallest share that still detects the lift halving (80% power, 95% confidence).
- Drift (PSI): how much customers' measures moved since the model was built. Under 0.1 stable, 0.1-0.25 watch, over 0.25 retrain.
- Retrain rule: retrain quarterly on exploration data (a random slice, weighted by each customer's recorded chance of contact), or at once
  when an alarm turns red (drift over 0.25, or the lift ladder out of order), and re-run the model check before switching models.
- Data: X5 RetailHero (Russian retail, rupee values are illustrative assumptions), Starbucks (simulated), Hillstrom (US e-mail test),
  Dunnhumby Complete Journey (US, no random test). The synthetic sample is made up, calibrated to X5 results."""

RULES = f"""You are Nudge's analyst for a marketing / CRM manager in India. Answer ONLY from the FACTS and the methods note.
Rules:
- Use only numbers that appear in the FACTS. Do not invent, estimate or recompute numbers. Cite every number with its fact id in square
  brackets, exactly like [F3].
- Definitions of terms (uplift, Qini, PSI, lift ladder...) come from the methods note: use it to explain them.
- Say only what the facts say about each dataset (for example, X5 tested an SMS, nothing else).
- Never state a comparison, ranking, order or label (for example "in order", "top > middle > bottom", "best", "clearly") unless a fact
  states it in those terms. If a fact says two groups respond about the same, say so.
- Name a channel only with the cost a fact gives it (for example "WhatsApp at ₹1.02"). Never attach a cost to a channel unless one fact
  pairs them. The channel used on the user's page is in the fact that says "Channel on the ... page".
- Say a value is above, below or about a threshold, or that a difference is reliable, only if a fact says so; when a fact says a
  difference is not reliable (its range includes zero), say that and do not call either side better.
- Describe the user's plan only with facts from its own data source, never with the X5 example's numbers.
- If asked what a specific channel costs and the page does not use that channel, say so and name the one it does use (from the
  "Channel on the ... page" fact); do not answer with another dataset's cost. When asked which channel to use, compare the channels in
  the channel-ladder fact.
- If a synthetic truth-check fact exists, also say what the truth shows, next to what was measured.
- Every fact starts with its data source (X5 example, synthetic sample, Hillstrom sample, the user's uploaded file, Starbucks, Dunnhumby).
  Say which data your numbers come from, every time.
- If neither the FACTS nor the methods note answer the question, reply exactly: "{NOT_KNOWN}" and then say in one sentence what the user could look at instead.
- Plain words, no jargon unless asked; rupees in Indian style (₹2.44 lakh). At most 120 words. End with one clear recommendation when relevant.
- Say whether a number is measured or assumed when it matters.
- If the question names an amount (budget, cost, margin) different from the one in the FACTS, say which amount the facts are for and
  tell the user to set their amount on the page to see the measured result; do not scale the numbers yourself."""

STARTERS = {
    'home': ['What does Nudge do?', 'Why do usual reports overstate results?', 'What does uplift mean?'],
    'plan': ['Whom should I contact?', 'Is my test fair?', 'Why not contact everyone?', 'What does the lift ladder show?'],
    'money': ['I have ₹50,000, what should I do?', 'Why not discount everyone?', 'Which channel should I use?', 'What if my margin is half?'],
    'prove': ['How big should my control group be?', 'What do I tell my boss?', 'When should I retrain?', 'What does PSI mean?'],
    'built': ['How was this validated?', 'What does Qini mean?', 'Why is a random test needed?'],
}


# ---------- fact sheets ----------
def project_facts() -> list:
    """Headline results of the project, always available (measured on the X5 locked exam unless stated)."""
    S = x5.summary(); cj = x5.table('step10_careful').set_index('control group')['effect %']
    d = x5.budget_difference(150, 1.02, 20_000)
    t30 = S['top30_by_uplift']; naive, fair = t30['rate_contacted'] * 30_000, (t30['rate_contacted'] - t30['rate_held_back']) * 30_000
    return [
        ('x5_lift', f"X5 random SMS test ({fmt.count(S['experiment_customers'])} customers): the message raised buying from "
                    f"{fmt.pct(S['buy_rate_held_back'], 1)} to {fmt.pct(S['buy_rate_messaged'], 1)}, {fmt.pts(S['lift'])} "
                    f"(95% range {fmt.pts(S['lift_low95'])} to {fmt.pts(S['lift_high95'], 2)}). Measured."),
        ('x5_budget', f"X5, ₹20,000 WhatsApp budget per 1 lakh customers (₹150 profit per purchase, ₹1.02 per message, assumed): "
                      f"Nudge {fmt.rs(round(d['a'].profit, -2))} vs usual likely-buyer list {fmt.rs(round(d['b'].profit, -2))}; difference "
                      f"{fmt.rs(d['difference'])} (95% range {fmt.rs(d['low95'])} to {fmt.rs(d['high95'])}). Measured."),
        ('x5_naive', f"X5: messaging the top 30% of 1 lakh, a usual report credits {fmt.count(round(naive, -1))} buyers but the message caused "
                     f"{fmt.count(round(fair, -1))}: overstated {naive / fair:.1f}×. Measured."),
        ('x5_top10', f"X5: the top 10% by Nudge respond {S['top10_vs_average']:.1f}× the average customer. Measured."),
        ('contrast', f"Dunnhumby Complete Journey (no random test, company chose targets): two careful analyses of one campaign gave "
                     f"{fmt.signed(cj.max(), 1, '%')} and {fmt.signed(cj.min(), 1, '%')}, opposite answers."),
        ('x5_control', 'X5 control-group rule (Step 9): for a base of 1 lakh customers, hold back 10% (10,000) on every campaign; it detects '
                       'a change of 1.44 pts and costs about ₹48,800 per campaign in profit given up; for 10 lakh customers 1-2% is enough.'),
        ('offers', 'Starbucks offers (simulated, café 75% margin, assumed ₹70 per $): net extra profit per customer offered: reminder ₹194, '
                   'discount ₹201, free item ₹258. The free item wins because it costs only its cost of goods.'),
    ]


def plain(html: str) -> str:
    """HTML from the page -> plain sentence for the fact sheet."""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html or '')).strip()


def publish(page: str, facts: list, source: str = '') -> None:
    """Called by each page with [(key, sentence), ...] describing what it shows right now. `source` names the data
    (e.g. 'Synthetic X5-like sample'); it is written at the start of every fact so answers can say where numbers come from."""
    st.session_state.setdefault('facts', {})[page] = [(k, f'{source}: {t}' if source else t) for k, t in facts]
    st.session_state['facts_page'] = page


def fact_sheet(page: str) -> list:
    """Numbered facts for the current page first, then the project headlines."""
    page_facts = st.session_state.get('facts', {}).get(page, [])
    seen, out = set(), []
    for key, text in page_facts + project_facts():
        if key not in seen:
            seen.add(key); out.append({'id': f'F{len(out) + 1}', 'key': key, 'text': text})
    return out


# ---------- number check ----------
NUM = re.compile(r'(?<![\w\[])([−-]?)₹?\s?(\d[\d,]*(?:\.\d+)?)\s?(lakh|crore|%|pts|×|k(?![a-z]))?', re.I)


def numbers(text: str) -> list:
    """Every number in a text, as (shown text, value, precision). '₹2.44 lakh' -> (…, 244000, 1000): the shown digits are exact to
    ±half of their last place. Citations like [F3], short list numbers and years are ignored."""
    out = []
    text = re.sub(r'[\s    ]+', ' ', text)                        # odd spaces count as one normal space
    text = re.sub(r'95\s?%\s?(range|confidence)', r'\1', text, flags=re.I)   # '95% range' is a phrase, not a claim
    for m in NUM.finditer(re.sub(r'\[F\d+\]', '', text)):
        sign, digits, unit = m.groups()
        raw = digits.replace(',', '')
        try:
            v = float(raw)
        except ValueError:
            continue
        mult = {'lakh': 1e5, 'crore': 1e7, 'k': 1e3}.get((unit or '').lower(), 1)
        if (unit is None and v <= 10 and '.' not in raw) or (unit is None and 2015 <= v <= 2035):
            continue
        place = 10 ** -len(raw.split('.')[1]) if '.' in raw else 10 ** (len(raw) - len(raw.rstrip('0')) if raw.rstrip('0') else 0)
        out.append((m.group(0).strip(), (-v if sign else v) * mult, min(place * mult / 2, max(0.05 * v * mult, 0.005))))   # round numbers (1,000) are not always rounded figures: allowance at most 5%
    return out


def check_numbers(answer: str, facts: list, question: str = '') -> list:
    """Numbers in the answer that no fact (or the question) rounds to, at the precision the answer shows them."""
    known = [v for f in facts for _, v, _ in numbers(f['text'])] + [v for _, v, _ in numbers(question)]
    return [shown for shown, v, tol in numbers(answer) if not any(abs(abs(v) - abs(k)) <= tol + 1e-9 for k in known)]


SOURCES = ['x5', 'synthetic', 'hillstrom', 'uploaded', 'your file', 'your data', 'starbucks', 'dunnhumby', 'complete journey']
IN_ORDER = re.compile(r'\bin order\b|top\s*>\s*middle\s*>\s*bottom|high\s*>\s*medium\s*>\s*low|clear(?:ly)?\s+(?:lift\s+)?ladder'
                      r'|ladder\s+(?:is\s+)?(?:healthy|in order|clear)|falling staircase', re.I)


def _channel_name(word: str) -> str:
    w = word.lower()
    return 'WhatsApp' if 'whatsapp' in w else 'SMS' if w == 'sms' else 'Email' if 'mail' in w else 'AI voice call'


def _channel_costs(text: str, clause: bool = False) -> list:
    """(channel, rupee amount) pairs: in an answer, written close together ('₹5 per WhatsApp message', 'WhatsApp at ₹1.02');
    in a fact (clause=True), anywhere in the same clause, since facts state them carefully."""
    pairs = []
    parts = re.split(r'[;|]|\.\s', text) if clause else re.split(r'(?<=[.!?])\s+|;', text)   # never pair across sentences
    for part in parts:
        for m in re.finditer(r'whatsapp|\bsms\b|e-?mail|(?:ai\s+)?voice call|\bcalls?\b', part, re.I):
            window = part if clause else part[max(0, m.start() - 28):m.end() + 28]
            for a in re.finditer(r'₹\s?(\d[\d,]*(?:\.\d+)?)' + ('' if clause else r'\s?(?:per|each|/|a\b)'), window):
                pairs.append((_channel_name(m.group(0)), float(a.group(1).replace(',', ''))))
    return pairs


def check_claims(answer: str, facts: list) -> list:
    """Claims in the answer that the facts do not support: a cost given to the wrong channel, a lift ladder called 'in order' when
    the page says otherwise, and numbers given without saying which data they come from."""
    issues, text = [], normalise(answer)
    known = {pair for f in facts for pair in _channel_costs(f['text'], clause=True)}
    for ch, amt in _channel_costs(text):
        if not any(c == ch and abs(a - amt) < 0.006 for c, a in known):
            issues.append(f'"₹{amt:g}" is not the cost of {ch} in the facts')
    ladder = ' '.join(f['text'] for f in facts if 'ladder' in f['key'] or 'Lift ladder' in f['text'])
    if IN_ORDER.search(text) and ladder and not re.search(r'(?<!out of )\bin order\b', ladder):
        issues.append('calls the lift ladder "in order", but the page does not')
    whole = [f for f in facts if 'not only the untouched 20%' in f['text']]
    scoped = [f for f in facts if f not in whole]
    for sentence in re.split(r'(?<=[.!?])\s+|\n+|;', text):        # clause by clause
        if re.search(r'untouched\s*20', sentence, re.I):
            for shown, v, tol in numbers(sentence):
                in_whole = any(abs(abs(v) - abs(k)) <= tol + 1e-9 for f in whole for _, k, _ in numbers(f['text']))
                in_scoped = any(abs(abs(v) - abs(k)) <= tol + 1e-9 for f in scoped for _, k, _ in numbers(f['text']))
                if in_whole and not in_scoped:
                    issues.append(f'says "untouched 20%" for {shown}, which is measured on the whole file')
                    break
    used = facts_used(text, facts); low = text.lower()
    SRC = {'your uploaded file': r'uploaded file|your file', 'the synthetic sample': r'synthetic', 'the Hillstrom sample': r'hillstrom',
           'the X5 example': r'\bx5\b'}
    fact_src = ' '.join(f['text'].split(':')[0].lower() for f in used) + (' x5' if any(f['key'].startswith('x5_') for f in used) else '')
    for name, pat in SRC.items():
        if re.search(pat, low) and not re.search(pat, fact_src):
            if name == 'the X5 example' and 'calibrated to x5' in fact_src:
                continue                                           # 'synthetic, calibrated to X5' is the synthetic sample, fine
            issues.append(f'says the numbers come from {name}, but the facts it used come from: '
                          f"{'; '.join(sorted({f['text'].split(':')[0] for f in used})) or 'no fact'}")
    x5_only = [f for f in used if f['key'].startswith('x5_') or f['key'] in ('offers', 'contrast')]
    if x5_only and re.search(r'\b(this|your|the) plan\b', low) and 'x5' not in low:
        issues.append("describes this plan with the X5 example's numbers")
    if re.search(r'usual|likely.buyer', low) and not any(re.search(r'usual|likely.buyer', f['text'], re.I) for f in used):
        issues.append('talks about the usual approach, but none of the facts it used covers it')
    return issues


def check_truth_labels(answer: str, facts: list) -> list:
    """On the synthetic sample, true values (known only because the data are made up) must not be called 'measured'."""
    truth = next((f['text'] for f in facts if f['key'] == 'truth'), '')
    if not truth:
        return []
    true_vals = [v for _, v, _ in numbers(truth.split('TRUE profit')[-1])] if 'TRUE profit' in truth else []
    others = [v for f in facts if f['key'] != 'truth' for _, v, _ in numbers(f['text'])]
    only_true = [v for v in true_vals if abs(v) >= 10 and not any(abs(v - o) < 0.5 for o in others)]
    for sentence in re.split(r'(?<=[.!?])\s+', answer):
        if re.search(r'(?<!not )\bmeasured\b', sentence.lower()) and any(abs(v - t) <= tol for _, v, tol in numbers(sentence) for t in only_true):
            return ['calls a synthetic TRUE value "measured" (true values are known only because the data are made up)']
    return []


def app_notes(question: str, answer: str, facts: list, page: str) -> str:
    """Short notes the app adds from the page's own facts, for two known failure types of language models:
    a question about a channel the page does not use, and plan comparisons on the synthetic sample without the truth."""
    notes, q = [], question.lower()
    channel = next((f['text'] for f in facts if f['key'] == 'channel'), '')
    asked = {_channel_name(m.group(0)) for m in re.finditer(r'whatsapp|\bsms\b|e-?mail|(?:ai\s+)?voice call|\bcalls?\b', q, re.I)}
    page_chan = channel.split('page:')[-1] if 'page:' in channel else ''
    for ch in asked:
        if page_chan and ch.lower() not in page_chan.lower() and not (ch == 'AI voice call' and 'call' in page_chan.lower()):
            notes.append(f"This page's plan does not use {ch}; it uses {page_chan.strip().split('. Profit')[0].rstrip('.')}.")
    truth = next((f for f in facts if f['key'] == 'truth'), None)
    if truth and re.search(r'better|beat|\bvs\b|versus|compare|outperform|win', q) and not re.search(r'\btrue\b|truth', answer.lower()):
        best = re.search(r'the best of these plans is: ([^.]+)', truth['text'])
        vals = re.search(r'TRUE profit \(not measured\) per 1,000 customers on the untouched 20%: ([^.]+)', truth['text'])
        if best and vals:
            notes.append(f"Synthetic truth check (true values, known only because the data are made up): {vals.group(1)}; "
                         f"the truth says the best plan is {best.group(1)}. [{truth['id']}]")
    return ''.join(f'\n\n**Note added by the app from this page\'s facts:** {n}' for n in notes)


def with_source(answer: str, facts: list) -> str:
    """Every answer with numbers says which data they come from: if the model did not, add it from the facts it used."""
    if not numbers(answer) or any(w in answer.lower() for w in SOURCES):
        return answer
    srcs = []
    for f in facts_used(answer, facts):
        s = f['text'].split(':')[0] if ':' in f['text'][:90] else ('X5 example' if f['key'].startswith('x5_') else '')
        if s and s not in srcs:
            srcs.append(s)
    return (f"*Data: {'; '.join(srcs)}.*\n\n" if srcs else '') + answer


def normalise(answer: str) -> str:
    """Some models write citations as 【F3】, [​F3] (invisible zero-width space) or [F3, F5]: turn them into [F3] [F5]."""
    a = re.sub('[​‌‍⁠﻿]', '', answer).replace('【', '[').replace('】', ']')
    return re.sub(r'\[(F\d+(?:\s*[,;]\s*F\d+)+)\]', lambda m: ' '.join(f'[{x.strip()}]' for x in re.split(r'[,;]', m.group(1))), a)


def facts_used(answer: str, facts: list) -> list:
    """Facts behind an answer: the ones it cites, then the fewest further facts that explain its remaining numbers
    (models sometimes forget to cite). A fact is added only if it explains a number no chosen fact explains."""
    nums = [(v, tol) for _, v, tol in numbers(answer) if abs(v) >= 10]
    explains = lambda f: {i for i, (v, tol) in enumerate(nums) if any(abs(abs(v) - abs(k)) <= tol + 1e-9 for _, k, _ in numbers(f['text']))}
    chosen = cited(answer, facts); covered = set().union(*[explains(f) for f in chosen]) if chosen else set()
    while True:
        best = max((f for f in facts if f not in chosen), key=lambda f: len(explains(f) - covered), default=None)
        if best is None or not explains(best) - covered:
            break
        chosen.append(best); covered |= explains(best)
    return [f for f in facts if f in chosen]


def cited(answer: str, facts: list) -> list:
    ids = set(re.findall(r'\[(F\d+)\]', normalise(answer)))
    return [f for f in facts if f['id'] in ids]


# ---------- the free provider, with limits ----------
@st.cache_resource
def _shared_usage() -> dict:
    """One counter for all visitors of this app (resets at midnight UTC or when the app restarts)."""
    return {'day': None, 'calls': {m: 0 for m, _ in MODELS}, 'tokens': {m: 0 for m, _ in MODELS}}


def _usage():
    u = _shared_usage(); today = dt.datetime.now(dt.timezone.utc).date()
    if u['day'] != today:
        u.update(day=today, calls={m: 0 for m, _ in MODELS}, tokens={m: 0 for m, _ in MODELS})
    return u


def app_key():
    try:
        k = st.secrets.get('GROQ_API_KEY')
    except Exception:                                                   # no secrets file: fine
        k = None
    return k or os.environ.get('GROQ_API_KEY')


def status() -> dict:
    """What the analyst can use right now, for the panel's status line."""
    own = st.session_state.get('own_groq_key')
    asked = st.session_state.get('analyst_asked', 0); u = _usage()
    free = [m for m, cap in MODELS if u['calls'][m] < cap]
    if own:
        return {'mode': 'own key', 'left': None}
    if not app_key():
        return {'mode': 'rules', 'why': 'no AI key is set for this app', 'left': PER_VISITOR - asked}
    if asked >= PER_VISITOR:
        return {'mode': 'rules', 'why': f'you have used your {PER_VISITOR} questions for this visit', 'left': 0}
    if not free:
        return {'mode': 'rules', 'why': "today's free AI quota for this app is used up", 'left': PER_VISITOR - asked}
    return {'mode': 'ai', 'model': free[0], 'left': PER_VISITOR - asked}


def _ask_groq(messages: list, key: str, models: list) -> tuple:
    last = None
    for model in models:
        try:
            r = requests.post(URL, headers={'Authorization': f'Bearer {key}'}, timeout=30,
                              json={'model': model, 'messages': messages, 'temperature': 0, 'max_tokens': 1200,
                                    'reasoning_effort': 'low'})      # a reasoning model: thinks briefly, then answers
        except requests.RequestException as e:
            last = f'network error ({type(e).__name__})'; continue
        if r.status_code == 200:
            j = r.json()
            return j['choices'][0]['message']['content'].strip(), model, j.get('usage', {}).get('total_tokens', 0)
        last = 'busy or quota reached, try again in a minute' if r.status_code == 429 else 'key rejected' if r.status_code in (401, 403) else f'error {r.status_code}'
        if r.status_code in (401, 403):
            break
    raise RuntimeError(last or 'no model available')


def answer(question: str, page: str) -> dict:
    """Answer a question about the current page. Returns text, the facts cited, unverified numbers, and how it was answered."""
    facts = fact_sheet(page); s = status()
    extra = what_if(question)                                       # e.g. "₹50,000 on WhatsApp": computed now from measured curves
    if extra:
        facts = [{'id': 'F0', 'key': 'what_if', 'text': extra}] + facts
    if s['mode'] in ('ai', 'own key'):
        sheet = '\n'.join(f"[{f['id']}] {f['text']}" for f in facts)
        hist = st.session_state.get('analyst_chat', [])[-2:]
        messages = ([{'role': 'system', 'content': f'{RULES}\n\n{METHODS}\n\nFACTS (what the user sees now):\n{sheet}'}]
                    + [m for h in hist for m in ({'role': 'user', 'content': h['q']}, {'role': 'assistant', 'content': h['a']})]
                    + [{'role': 'user', 'content': question}])
        own = st.session_state.get('own_groq_key'); u = _usage()
        models = [m for m, _ in MODELS] if own else [m for m, cap in MODELS if u['calls'][m] < cap]
        try:
            text, model, used = _ask_groq(messages, own or app_key(), models)
            raw = normalise(text)                                    # the model's own words: checked before the app adds anything
            claims = check_claims(raw, facts) + check_truth_labels(raw, facts)
            text = with_source(raw, facts) + app_notes(question, raw, facts, page)
            if not own:
                u['calls'][model] += 1; u['tokens'][model] += used
                st.session_state['analyst_asked'] = st.session_state.get('analyst_asked', 0) + 1
            return {'text': text, 'facts': facts_used(text, facts), 'unverified': check_numbers(raw, facts, question),
                    'claims': claims,
                    'how': f"AI ({NAMES.get(model, model)}, via Groq)"}
        except RuntimeError as e:
            note = f'AI unavailable ({e}); answered by rules'
    else:
        note = f"answered by rules ({s['why']})"
    text, keys = rule_answer(question, facts)
    return {'text': text, 'facts': [f for f in facts if f['key'] in keys], 'unverified': [], 'claims': [], 'how': note}


# ---------- what-if: a budget named in the question, computed from the measured curves ----------
CHANNEL_WORDS = {'whatsapp': 'WhatsApp', 'sms': 'SMS', 'e-mail': 'Email', 'email': 'Email', 'call': 'AI voice call', 'voice': 'AI voice call'}


def asked_amount(question: str):
    """Largest rupee amount in a question: '₹50,000', '50k', '2 lakh'. None if there is none."""
    q = question.lower().replace(',', '')
    vals = [float(m) * 1e3 for m in re.findall(r'(\d+(?:\.\d+)?)\s?k\b', q)]
    vals += [v for _, v, _ in numbers(question) if v >= 1000]
    return max(vals) if vals else None


def what_if(question: str):
    """If the question names a budget, compute the plan for it with the Money page's own maths (instant, no AI)."""
    amount = asked_amount(question)
    if amount is None:
        return None
    from lib import money                                           # here, to keep other pages light
    ctx = st.session_state.get('money_ctx', {})
    chans = {k: v['value'] for k, v in x5.meta()['assumptions']['channels_rs_per_contact'].items()}
    named = next((c for w, c in CHANNEL_WORDS.items() if w in question.lower()), None)
    if named:
        chan, cost = named, chans[named]
    elif ctx:                                                       # the channel and cost on the Money page right now
        chan, cost = (ctx['chan'] if ctx['chan'] != 'Custom' else f"contacts at {fmt.cost(ctx['cost'])}"), ctx['cost']
    else:
        chan, cost = 'WhatsApp', chans['WhatsApp']
    k, base = ctx.get('k', 150.0), ctx.get('base', 100_000)
    plan = st.session_state.get('plan', {})
    if ctx.get('mode') == 'Your data' and plan.get('curves'):
        cur = plan['current']; Cu = plan['curves'].get((cur['value'], cur['cost']))
        if Cu is not None:
            scale = plan['res']['fixed_scale'] or k; C = money.user_curves(Cu, scale, cost, base)
            a, b = money.within_budget(C['nudge'], cost, amount), money.within_budget(C['usual'], cost, amount)
            same = C['usual'].loc[(C['usual'].share - a.share).abs().idxmin()]
            return (f"Computed now with the Money page's maths from your data ({plan['source']}, untouched 20%): {fmt.rs(amount)} on {chan} "
                    f"({fmt.cost(cost)} per contact, ₹{k:,.0f} per purchase, base {fmt.count(base)} customers): Nudge contacts {fmt.count(a.contacts)}, "
                    f"profit {fmt.rs(round(a.profit, -2))}; the usual approach's best use of the budget makes {fmt.rs(round(b.profit, -2))} "
                    f"({fmt.count(b.contacts)} contacts), and on the same {fmt.count(a.contacts)} contacts it makes {fmt.rs(round(same.profit, -2))}. "
                    "Measured; costs assumed.")
    d = x5.budget_difference(k, cost, amount, base=base)
    return (f"Computed now with the Money page's maths from the measured X5 curves: {fmt.rs(amount)} on {chan} ({fmt.cost(cost)} per contact, "
            f"₹{k:,.0f} profit per extra purchase, base {fmt.count(base)} customers): contact {fmt.count(round(d['a'].contacts, -2))} ranked by "
            f"Nudge, profit {fmt.rs(round(d['a'].profit, -2))} (range {fmt.rs(d['a'].low95)} to {fmt.rs(d['a'].high95)}); usual likely-buyer "
            f"list {fmt.rs(round(d['b'].profit, -2))}; difference {fmt.rs(d['difference'])} (range {fmt.rs(d['low95'])} to {fmt.rs(d['high95'])}). "
            'Measured; profit per purchase and contact cost assumed.')


# ---------- rule-based fallback ----------
def definitions() -> dict:
    """The methods note as {term: full definition}, continuation lines included."""
    out = {}
    for block in ('\n' + METHODS).split('\n- ')[1:]:
        term, _, body = ' '.join(l.strip() for l in block.splitlines()).partition(':')
        out[term.strip()] = f'{term.strip()}: {body.strip()}'
    return out


TERMS = [  # words in a "what does X mean?" question -> methods term, and the page facts that show it
    (['uplift'], 'Uplift', []), (['qini'], 'Qini', []), (['psi', 'drift'], 'Drift (PSI)', ['drift']),
    (['ladder'], 'Lift ladder', ['ladder']), (['control group', 'control'], 'Control group size', ['control_group', 'x5_control']),
    (['random test', 'random'], 'Random test', ['fairness']), (['measured', 'assumed'], 'Measured vs assumed', []),
    (['range', 'confidence'], '95% range', []), (['fallback', 'validation', 'untouched'], 'Plan choice', ['decision']),
    (['break-even', 'breakeven', 'break even'], 'Offer costs', ['breakeven']), (['retrain'], 'Retrain rule', ['drift', 'ladder']),
    (['usual report', 'fair report', 'overstate'], 'Fair report vs usual report', ['fair_report', 'x5_naive']),
    (['engine', 'doubly robust'], 'Nudge engine', []),
]

INTENTS = [  # checked in this order: (name, words, page facts in priority order, project facts if the page has none, methods term, lead)
    ('boss', ['boss', 'manager', 'summary', 'tell my', 'tell the'], ['boss_summary', 'fair_report'], ['x5_naive', 'x5_control'], None,
     'A summary you can share:'),
    ('control', ['control group', 'control', 'hold back', 'holdout', 'how big', 'sample size', 'pilot'], ['control_group'], ['x5_control'],
     'Control group size', 'Control group:'),
    ('retrain', ['retrain', 'stale', 'drift', 'psi', 'alarm', 'model health', 'out of date'], ['drift', 'ladder'], [], 'Retrain rule',
     'When to retrain:'),
    ('fair', ['fair', 'random', 'balanced', 'balance', 'biased', 'trust'], ['fairness'], ['x5_lift', 'contrast'], 'Random test',
     'Is the test fair?'),
    ('report', ['overstate', 'usual report', 'naive', 'claimed', 'exaggerat'], ['fair_report'], ['x5_naive'], 'Fair report vs usual report',
     'Why usual reports overstate results:'),
    ('offer', ['discount', 'offer', 'cashback', 'free item', 'coupon', 'wallet', 'voucher', 'bogo'], ['breakeven', 'effects'], ['offers'],
     'Offer costs', 'Why offers are expensive:'),
    ('budget', ['budget', 'what should i do', 'how much should', 'spend', 'invest'], ['budget_plan', 'best_share'], ['x5_budget'], None,
     'For your budget:'),
    ('stress', ['margin', 'half', 'what if', 'worse', 'stress', 'double', 'wrong'], ['stress'], [], None, 'If the assumptions are worse:'),
    ('everyone', ['everyone', 'all customers', 'contact all', 'why not contact', 'whole list'], ['kpis', 'decision', 'best_share'],
     ['x5_budget'], 'Plan choice', 'Why not contact everyone?'),
    ('channel', ['channel', 'whatsapp', 'sms', 'email', 'e-mail', 'call'], ['channel_ladder', 'best_share'], [], None, 'Which channel:'),
    ('who', ['whom', 'who should', 'who to', 'target', 'persona', 'responders', 'which customers', 'who responds'], ['decision', 'personas'],
     ['x5_top10'], None, 'Whom to contact:'),
    ('ladder', ['ladder', 'model work', 'does the model'], ['ladder'], [], 'Lift ladder', 'Does the model work on this data?'),
    ('validated', ['validat', 'how was', 'built', 'tested', 'proof', 'trustworthy', 'accurate'], ['truth', 'ladder', 'step1', 'step4'],
     ['x5_lift', 'x5_top10', 'x5_naive'], 'Plan choice', 'How it was checked:'),
]


def rule_answer(question: str, facts: list) -> tuple:
    """A plain answer built only from the fact sheet and the methods note (no AI): the current page's facts first."""
    q = ' ' + question.lower() + ' '; by_key = {f['key']: f for f in facts}; defs = definitions()
    bullet = lambda f: f"- {f['text']} [{f['id']}]"
    if 'what_if' in by_key:                                          # a budget was named: answer with the computed plan
        return f"For {fmt.rs(asked_amount(question))}:\n{bullet(by_key['what_if'])}", ['what_if']
    if any(w in q for w in ['what does', 'what is', 'what are', ' mean', 'explain', 'define']):
        for words, term, keys in TERMS:
            if any(w in q for w in words):
                shown = [by_key[k] for k in keys if k in by_key][:1]
                return defs[term] + (f'\n\nOn this page:\n{bullet(shown[0])}' if shown else ''), [f['key'] for f in shown]
        if 'nudge' in q:
            return ('Nudge learns from a random campaign test who buys because of a contact, then plans whom to contact, with which '
                    'option, for what budget, and how to prove it worked. Every number is measured on customers the model never saw.'), []
    for name, words, page_keys, project_keys, term, lead in INTENTS:
        if any(w in q for w in words):
            hits = [by_key[k] for k in page_keys if k in by_key][:2] or [by_key[k] for k in project_keys if k in by_key][:2]
            text = lead + '\n' + '\n'.join(bullet(f) for f in hits) if hits else ''
            if term and (not hits or name in ('everyone', 'retrain')):
                text += ('\n\n' if text else '') + defs[term]
            if text:
                return text, [f['key'] for f in hits]
    return (f'{NOT_KNOWN} Rule-based answers cover budgets, fairness, offers, whom to contact, channels, control groups, model health '
            'and the meaning of terms. Add a free Groq key for other questions.'), []
