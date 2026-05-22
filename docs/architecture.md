# Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          INGEST                                  │
│                                                                  │
│   iTunes RSS ────┐                                               │
│   (best-effort)  │                                               │
│                  │                                               │
│   Google Play ───┼──►  normalize  ──►  dedupe  ──►  SQLite       │
│   scraper        │      (Review)        (by id)    data/reviews. │
│                  │                                       sqlite  │
│   Reddit JSON ───┘                                               │
│   (r/spotify,                                                    │
│    r/truespotify,                                                │
│    r/spotifypremium)                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       EMBED + CLUSTER                            │
│                                                                  │
│   sentence-transformers/all-MiniLM-L6-v2  (local, ~90MB)         │
│            ↓                                                     │
│   384-dim vectors, L2-normalized                                 │
│            ↓                                                     │
│   sklearn HDBSCAN                                                │
│   (min_cluster_size=5, euclidean on normalized = cosine)         │
│            ↓                                                     │
│   {cluster_id → [reviews]}, plus -1 noise bucket                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SYNTHESIZE  (the agent loop)                    │
│                                                                  │
│   for each cluster:                                              │
│      ┌──────────────────────────────────────────┐                │
│      │  prompt Gemini 2.5 Flash with            │                │
│      │  12-review sample + tool list            │                │
│      └────────────┬─────────────────────────────┘                │
│                   ▼                                              │
│      parse response:                                             │
│         · final JSON  → verify quotes against sources  → return  │
│         · tool call   → execute, append result, re-prompt        │
│         · INCOHERENT  → drop the cluster                         │
│                                                                  │
│   tools:                                                         │
│     - get_more_reviews(n)                                        │
│     - lookup_review(review_id)                                   │
│                                                                  │
│   max 3 tool calls per cluster                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RANK + RENDER                              │
│                                                                  │
│   score = severity × log(frequency + 1)                          │
│                                                                  │
│   sort, format as markdown  →  output/brief.md                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File map

| Module                         | What it does                          |
|--------------------------------|---------------------------------------|
| `feedback_agent/ingest/app_store.py`   | iTunes RSS fetcher (best-effort) |
| `feedback_agent/ingest/google_play.py` | Google Play reviews scraper |
| `feedback_agent/ingest/reddit.py`      | Reddit posts via public JSON |
| `feedback_agent/store.py`     | SQLite persistence + dedup            |
| `feedback_agent/embed.py`     | sentence-transformers wrapper         |
| `feedback_agent/cluster.py`   | HDBSCAN + grouping helper             |
| `feedback_agent/synth.py`     | Gemini agent loop (the main thing)    |
| `feedback_agent/brief.py`     | Markdown formatter                    |
| `scripts/run.py`              | Full pipeline orchestrator            |
| `scripts/ingest_only.py`      | Just the fetch step, for iteration    |
| `evals/run_eval.py`           | Clustering quality on labeled set     |
| `evals/labels.csv`            | 51 hand-labeled reviews               |

## Runtime cost

- Embedding: free (local)
- Clustering: free (local)
- Synthesis: ~1 Gemini call per cluster. With ~30 clusters on a typical week,
  well within the free tier (~1500 requests/day on 2.5 Flash as of mid-2026).
- Storage: SQLite file, ~5MB for a few weeks of accumulated reviews.
