# Nudge: campaign targeting engine

**Contact the customers who buy *because of* your message, not the ones who would buy anyway.**

Nudge learns from a randomised campaign test who responds to a contact (uplift modelling), then plans whom to contact, with which
offer and channel, for what budget in rupees, and how to prove it worked. Every result is measured on customers the model never saw.

- **Live app:** [uplift-engine.streamlit.app](https://uplift-engine.streamlit.app/) (try the synthetic sample on *Plan my campaign*)
- **How it was built:** 10 steps, each with a pass/fail gate set in advance; see [`notebooks/`](notebooks) and the
  [project write-up](docs/PROJECT_PLAYBOOK.md)

## Run it locally
```
cd app
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```
The AI analyst needs a free Groq key in `app/.streamlit/secrets.toml` (see `secrets.toml.example`); without it, the app answers with rules.

## Licence
Code: MIT (see [LICENSE](LICENSE)). **Each dataset keeps its own licence and terms:** X5 RetailHero, the Starbucks rewards data,
the Hillstrom (MineThatData) e-mail test and Dunnhumby The Complete Journey belong to their owners. This repository contains only
aggregated results from X5, Starbucks and Complete Journey, plus the public Hillstrom file and a synthetic sample.

*A fuller README comes with the final write-up.*
