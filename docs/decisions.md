# Decision log

Running notes on choices I made and why. Not exhaustive — just the ones I
expect someone reading the repo to wonder about.

## 1. Local embeddings, frontier LLM only for synthesis

Embedding ~1000 reviews with a paid API (OpenAI's `text-embedding-3-small` at
$0.02/1M tokens) is essentially free at this scale — maybe a penny. But
`sentence-transformers/all-MiniLM-L6-v2` runs locally, takes ~10 seconds for
1000 reviews on CPU, and the quality is genuinely fine for short review text.

Using a frontier LLM for the *synthesis* step is where the cost/quality
tradeoff actually matters — that's the reasoning-heavy bit where Gemini 2.5
Flash earns its keep. Free tier is enough at this volume (10s of clusters per
run, one call per cluster).

The general principle: pay for reasoning quality, not for tasks where a small
local model is equivalent. This is the kind of cost discipline that gets
asked about in PM interviews.

## 2. No LangChain (or similar framework)

The agent loop in `synth.py` is ~120 lines including comments. I can explain
every line. A LangChain version would have 1/3 the lines but introduce
abstractions (Chains, Tools, Agents, Callbacks) that obscure what's actually
happening — bad for debugging, worse for explaining in an interview.

For a portfolio piece where the point is to *demonstrate understanding of
agentic systems*, hiding the loop behind a framework defeats the purpose.

## 3. HDBSCAN over k-means

K-means needs a fixed k. With review streams you don't know how many themes
there are ahead of time, and the right answer changes week to week. HDBSCAN
finds clusters of variable size AND has a built-in noise bucket — reviews
that don't fit any theme just don't get clustered, instead of being forced
into the nearest one.

Using sklearn's built-in HDBSCAN (since 1.3) instead of the standalone
`hdbscan` package — one less dependency, fewer Windows install headaches.

## 4. App Store ingestion is best-effort, not load-bearing

Apple has been progressively breaking the public iTunes RSS reviews feed
since ~2022. As of May 2026, it still returns HTTP 200 for Spotify
(id=324684580) but with an empty `entries` array — no actual reviews. Tested
`app-store-scraper` as a fallback and it's unmaintained (pins broken
urllib3, doesn't import on Python 3.14).

The real options were:
- Roll a custom scraper against `amp-api.apps.apple.com` — requires a Bearer
  token scraped from the public webpage, brittle, would break the day Apple
  changes anything
- Use the App Store Connect API — requires an Apple Developer account ($99/yr)
  and is meant for first-party app owners
- Drop App Store as a source for v1 and document why

I went with option 3. The pipeline runs on Google Play (Android) + Reddit,
which together still give a fat enough corpus to find real themes. App Store
code stays in the repo so the feed lighting back up is a no-op fix. If
someone wants iOS data badly enough, the Connect API integration is a
straightforward extension.

This is the kind of "real engineering hits real-world API decay" story that
PM interviews actually like.

## 5. Reddit via public JSON, not PRAW

PRAW (the standard Reddit Python client) needs OAuth — register an app, get
a client ID/secret, manage tokens. For this scale (a few hundred posts a
week) Reddit's public `*.json` endpoints work fine if you set a polite User-
Agent and sleep between calls. One less credential to manage, one less thing
in `.env`.

If volume ever needed to scale up or we wanted comments not just posts, PRAW
becomes worth the setup.

## 6. Quote verification

The synthesis prompt asks Gemini to return verbatim quotes with the source
review ID. After parsing, `_verify_quotes` checks that the quoted text
actually appears in the cited review and drops any quote that doesn't.

This is the only AI-output trust check in the pipeline. Without it, a
hallucinated or paraphrased quote could end up in a PM brief and that's the
exact thing that kills credibility for these tools. Cheap to add, big
downside if missing.

## 7. Eval framework intentionally narrow

The eval (`evals/run_eval.py`) measures clustering quality — ARI,
homogeneity, purity against a hand-labeled set. It doesn't try to judge the
LLM synthesis output automatically.

I considered using an LLM-as-judge approach for synthesis quality but
decided against it for v1:
- LLM judges have known biases (length, hedging, agreement with stronger
  models) — adds noise without much signal at this scale
- Manual spot-checking 10 syntheses against the labeled set takes ~10 min
  and is more honest
- The eval doc in the brief output (TODO) is the place for that judgment

Initial run on the 51-review labeled set surfaced only 2 clusters with ARI
~0.003 — expected, because 51 reviews spread across 40 distinct themes is
genuinely sparse. The eval framework runs and produces real numbers; the
production pipeline (~1000 reviews) is where actual clustering quality will
show.

## 8. Why SQLite, not parquet/CSV

SQLite gives us cheap dedup (PRIMARY KEY on review id), incremental ingest
(re-run with no new rows added if nothing changed upstream), and easy
querying. Parquet is faster for ML workflows but worse for iteration. CSV
is fine for the eval labels (where the data is small and we want it human-
editable in a text editor) but bad for the main store.
