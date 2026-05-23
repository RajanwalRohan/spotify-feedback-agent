"""The actual agent loop.

For each cluster, we send a sample of reviews to Gemini and ask for a structured
summary. The agent has two tools - get_more_reviews and lookup_review - so it
can dig in if the sample looks ambiguous.

The loop is intentionally manual (no langchain etc.) so the control flow is
obvious. Max 3 tool calls per cluster to keep latency and free-tier usage sane.
"""
import os
import json
import re
from typing import Any

import google.generativeai as genai


MODEL_NAME = "gemini-2.5-flash"
MAX_TOOL_CALLS = 3
SAMPLE_SIZE = 12   # how many reviews we send in the first pass
MORE_SIZE = 8      # how many we send if the agent asks for more


SYSTEM_PROMPT = """You are analyzing Spotify user reviews to produce a weekly brief for the PM team.

You'll be given a cluster of reviews that an embedding algorithm grouped together. Your job: identify the shared theme and write a short structured summary.

Tools available:
- get_more_reviews(n): fetch n more reviews from this cluster if the initial sample is ambiguous
- lookup_review(review_id): get the full text of one specific review

Use tools sparingly - only when the sample genuinely doesn't reveal the theme.

When you're ready, respond with ONLY valid JSON matching this schema (no markdown fences):
{
  "theme_name": "short noun phrase, 4-8 words",
  "description": "one sentence explaining what users are saying",
  "severity": 1-5 integer (1=minor annoyance, 5=churn/refund driver),
  "frequency_in_cluster": integer (how many reviews in the sample actually fit the theme),
  "quotes": [
    {"review_id": "appstore:...", "text": "exact verbatim quote, <=200 chars"}
  ],
  "suggested_action": "one sentence, a concrete next step a PM might take"
}

If the cluster is incoherent (no shared theme), respond with: {"theme_name": "INCOHERENT"}

To request a tool instead, respond with: {"tool": "get_more_reviews", "n": 5} or {"tool": "lookup_review", "review_id": "..."}
"""


def _format_reviews(reviews: list[dict]) -> str:
    out = []
    for r in reviews:
        rating = r.get("rating")
        rating_s = f"{rating}/5" if rating else "n/a"
        out.append(f"[{r['id']}] ({r['source']}, {rating_s}) {r['text'][:400]}")
    return "\n\n".join(out)


def _parse_json(text: str) -> dict | None:
    # gemini sometimes still wraps in ```json fences - strip them
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # try to find the first json object in the text
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None


def _verify_quotes(result: dict, all_reviews: list[dict]) -> dict:
    """Drop any quote whose text doesn't appear in the cited review."""
    if "quotes" not in result:
        return result
    by_id = {r["id"]: r["text"] for r in all_reviews}
    kept = []
    for q in result["quotes"]:
        src = by_id.get(q.get("review_id", ""))
        if src and q.get("text", "").strip().lower() in src.lower():
            kept.append(q)
    result["quotes"] = kept
    return result


def synthesize_cluster(cluster_reviews: list[dict], api_key: str | None = None) -> dict | None:
    """Run the agent loop on one cluster. Returns parsed result, or None on failure."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set - add it to .env")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_PROMPT)

    sample = cluster_reviews[:SAMPLE_SIZE]
    remaining = cluster_reviews[SAMPLE_SIZE:]
    history = [f"Cluster size: {len(cluster_reviews)} reviews. Sample:\n\n{_format_reviews(sample)}"]

    for step in range(MAX_TOOL_CALLS + 1):
        prompt = "\n\n".join(history)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        parsed = _parse_json(text)
        if not parsed:
            # one retry with a nudge
            history.append("Your previous response was not valid JSON. Reply with JSON only.")
            continue

        if "tool" in parsed:
            tool = parsed["tool"]
            if tool == "get_more_reviews" and remaining:
                n = min(int(parsed.get("n", MORE_SIZE)), len(remaining))
                more = remaining[:n]
                remaining = remaining[n:]
                history.append(f"More reviews:\n\n{_format_reviews(more)}")
                sample = sample + more
                continue
            if tool == "lookup_review":
                rid = parsed.get("review_id", "")
                hit = next((r for r in cluster_reviews if r["id"] == rid), None)
                if hit:
                    history.append(f"Full review {rid}:\n\n{hit['text']}")
                else:
                    history.append(f"Review {rid} not found.")
                continue
            # unknown tool - bail
            history.append("Unknown tool. Reply with the final JSON summary now.")
            continue

        if parsed.get("theme_name") == "INCOHERENT":
            return None
        return _verify_quotes(parsed, sample)

    return None


def synthesize_all(groups: dict[int, list[dict]], api_key: str | None = None) -> list[dict]:
    """Run synthesis over every non-noise cluster."""
    from tqdm import tqdm
    out = []
    # skip cluster -1 (HDBSCAN's noise bucket)
    keys = [k for k in groups if k != -1]
    for k in tqdm(keys, desc="synthesizing clusters"):
        result = synthesize_cluster(groups[k], api_key=api_key)
        if result:
            result["cluster_id"] = k
            out.append(result)
    return out
