# spotify-feedback-agent

Pulls Spotify reviews from Google Play and Reddit (and App Store when Apple's RSS feed cooperates — see [decisions.md](docs/decisions.md)), clusters them into themes, and uses Gemini to write a weekly PRD-style brief of what users are actually complaining about.

I built this because PMs spend a lot of their week doing this kind of synthesis by hand — skimming reviews, eyeballing patterns, copy-pasting quotes into a doc. Wanted to see how much of that an agent could do without losing the nuance.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
# paste your Gemini key into .env
python -m scripts.run
```

The first run downloads the embedding model (~90MB) and pulls a few hundred recent reviews. End-to-end takes about 3-4 min on my laptop. Output lands in `output/brief.md`.

## What's in here

- `feedback_agent/ingest/` — three review sources (App Store, Google Play, Reddit), normalized to one schema
- `feedback_agent/embed.py` — sentence-transformers, runs locally
- `feedback_agent/cluster.py` — HDBSCAN
- `feedback_agent/synth.py` — the Gemini agent loop that writes the brief
- `feedback_agent/brief.py` — formats the final markdown
- `docs/PRD.md` — the PRD I wrote before any code
- `docs/architecture.md` — pipeline diagram + file map
- `docs/decisions.md` — why I made the choices I made
- `evals/` — hand-labeled set + eval script

## Why these choices

Embeddings stay local (sentence-transformers) — they don't need frontier reasoning and paying per-call to embed thousands of reviews adds up. Gemini gets used only for the synthesis step where the reasoning quality actually matters. Whole pipeline runs on the Gemini free tier.

No LangChain. Direct API calls. The agent loop is ~80 lines and I can explain every one of them.

More detail in [docs/decisions.md](docs/decisions.md).
