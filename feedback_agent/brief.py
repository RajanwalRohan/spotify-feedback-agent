"""Markdown formatter for the weekly brief."""
import math
import datetime as dt


def _score(s: dict) -> float:
    # severity dominates, frequency breaks ties (log so a 200-review cluster isn't 40x a 5-review one)
    return s.get("severity", 0) * math.log(s.get("frequency_in_cluster", 1) + 1)


def render_brief(syntheses: list[dict], total_reviews: int) -> str:
    ranked = sorted(syntheses, key=_score, reverse=True)
    today = dt.date.today().isoformat()

    lines = [
        f"# Spotify Feedback Brief - {today}",
        "",
        f"_Synthesized from {total_reviews} reviews across App Store, Google Play, and Reddit._",
        f"_{len(ranked)} themes surfaced. Ranked by severity × log(mentions)._",
        "",
        "---",
        "",
    ]

    for i, s in enumerate(ranked, 1):
        lines.append(f"## {i}. {s.get('theme_name', '(unnamed)')}")
        lines.append("")
        lines.append(f"**Severity:** {s.get('severity', '?')}/5 · **Mentions in cluster:** {s.get('frequency_in_cluster', '?')}")
        lines.append("")
        desc = s.get("description", "")
        if desc:
            lines.append(desc)
            lines.append("")
        quotes = s.get("quotes", [])
        if quotes:
            lines.append("**What users are saying:**")
            lines.append("")
            for q in quotes:
                t = q.get("text", "").strip()
                if t:
                    lines.append(f"> {t}")
                    lines.append("")
        action = s.get("suggested_action", "")
        if action:
            lines.append(f"**Suggested next step:** {action}")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
