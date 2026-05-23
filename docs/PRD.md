# PRD: Customer Feedback Synthesis Agent

**Author:** Rohan Rajanwal
**Status:** Draft v1 - written before code
**Last updated:** 2026-05-21

## Problem

PMs are accountable for understanding what users are saying about the product. In practice that means someone - usually the PM, sometimes a researcher, often a TPM-shaped person who got drafted into it - spends 2-4 hours a week skimming app store reviews and Reddit threads, pulling representative quotes, and writing a brief that gets read in standup and forgotten.

The work has three problems:

1. It's expensive (PM hours), so it gets done irregularly or not at all.
2. It's biased - the synthesizer sees what they were already looking for. A theme that quietly grew 3x over the past month gets missed if nobody happened to scroll past it.
3. It's not verifiable - there's no way to tell if the brief reflects the actual review distribution or just the PM's priors.

A small agent can do most of the mechanical work - clustering, quote selection, severity scoring - and free the PM to do the judgment piece (what to fund, what to ignore). That's the wedge.

## Users

Primary: a single PM (me, in the test case) responsible for a consumer product with public review surfaces - app stores, subreddits, X. Wants a weekly digest they can skim in 5 minutes and trust.

Secondary: anyone on the team who reads the brief - eng leads who want to know if their area is generating complaints, exec sponsors who want a temperature check, designers looking for next-quarter problem areas.

## Goals

1. Replace the manual weekly synthesis with a brief that's at least as good - measured against a hand-labeled set.
2. Surface themes the PM would have missed. The agent has no prior - it should catch slow-burn patterns a human eye glosses over.
3. Stay cheap. Whole pipeline should run on free-tier APIs and a personal laptop.
4. Be explainable. Every cluster in the brief should link back to the raw reviews it came from.

## Non-goals

- Real-time alerting. Weekly is the cadence; spikes are out of scope for v1.
- Sentiment scoring as the headline. Sentiment alone is a known-thin signal - we care about *themes*, not net positivity.
- Multilingual. English reviews only for v1. Spotify has heavy international review volume; adding language detection is a v2 problem.
- Action recommendations beyond a one-line "suggested next step" per cluster. The agent is a synthesizer, not a roadmap.

## Solution outline

A four-stage pipeline:

**1. Ingest.** Pull recent reviews from three sources: iOS App Store (iTunes RSS), Google Play (scraper), and Reddit (r/spotify + a few adjacent subs, public JSON endpoint). Normalize to one schema, dedupe, persist to SQLite.

**2. Embed + cluster.** Embed each review with `sentence-transformers/all-MiniLM-L6-v2` (local, free). Cluster with HDBSCAN - picked over k-means because we don't know the number of themes ahead of time and we want to allow "noise" (reviews that don't belong to any theme).

**3. Synthesize.** For each cluster, send the cluster's reviews to Gemini 2.5 Flash with a structured prompt that asks for: theme name, one-line description, severity (1-5), frequency (count + % of corpus), 2-3 representative quotes, and a one-line suggested next step. The agent has a small tool surface - a function to fetch more reviews from a cluster, and one to look up the original review by ID - so it can dig deeper before committing to a synthesis.

**4. Rank + format.** Rank clusters by a simple weighted score (severity × log(frequency)). Format the top N into a markdown brief.

## Success metrics

- **Clustering recall** vs. hand-labeled set of 50 reviews across 6-8 known themes. Target: ≥80% of reviews land in the correct cluster (or the no-cluster bucket if they should).
- **Synthesis faithfulness**: each cluster's stated theme description must be supported by ≥2 of the cluster's actual reviews (manually scored on a 10-cluster sample).
- **Pipeline runtime**: < 5 min for ~1000 reviews on a personal laptop. (The point is that a PM should be able to re-run it without setting aside a block.)
- **Reading time on the brief**: target ≤ 5 min skim for the top 10 clusters.

## Risks

- **The clustering is meh.** Short reviews ("crashes when I skip songs") cluster badly with general-purpose embedders. Mitigation: experiment with a noise threshold; consider LLM-driven theme extraction as a fallback for the unclustered bucket.
- **Gemini free-tier rate limits.** Free tier on Gemini 2.5 Flash is generous but not infinite. Mitigation: batch cluster synthesis (one call per cluster, not per review), back off on 429s.
- **Quote selection is a trust surface.** If the agent fabricates or paraphrases a quote, the whole brief loses credibility. Mitigation: quotes must be returned with the original review ID and verified against the source before rendering.
- **Reddit volume is low.** r/spotify has maybe 10-50 relevant posts a week. Mitigation: combine with adjacent subs (r/truespotify, r/spotifypremium), and accept that App Store reviews carry most of the weight.

## Open questions

- Should the brief be email or markdown file? Markdown for v1; email is mechanical to add later.
- How do we handle reviews that mention competitors (Apple Music, YouTube Music)? Probably a separate cluster type - competitive intel - but punted for v1.
- Is HDBSCAN the right call long-term, or should we move to LLM-driven topic modeling? Eval will tell us.

## What v2 might look like

- Same pipeline pointed at a competitor's review corpus. Compare theme distributions. That's the competitive-intelligence extension.
- Slack delivery instead of markdown file.
- Trend detection - flag clusters that grew >50% week-over-week.
- A "drill down" mode: ask the agent a follow-up question about a specific cluster ("what platform are these users on?").
