"""iTunes RSS pull for App Store reviews.

Note (2026-05): Apple has been progressively breaking this endpoint. It still
responds 200 but often returns an empty feed (no `entry` array) — see
docs/decisions.md for the longer story and why we're keeping this code in place
anyway. If RSS comes back, this works; if not, the pipeline runs on Google Play
+ Reddit and logs a warning.
"""
import requests
import warnings
from dataclasses import dataclass


@dataclass
class Review:
    id: str
    source: str
    text: str
    rating: int | None
    created_at: str
    url: str
    raw: dict


def fetch_app_store(app_id: str = "324684580", pages: int = 10, country: str = "us") -> list[Review]:
    out = []
    empty_responses = 0
    for page in range(1, pages + 1):
        url = (
            f"https://itunes.apple.com/{country}/rss/customerreviews"
            f"/page={page}/id={app_id}/sortby=mostrecent/json"
        )
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            break

        data = r.json()
        entries = data.get("feed", {}).get("entry", []) or []
        # first entry on page 1 is the app metadata, not a review
        if page == 1 and entries:
            entries = entries[1:]

        if not entries:
            empty_responses += 1
            break

        for e in entries:
            try:
                rid = e["id"]["label"]
                title = e.get("title", {}).get("label", "")
                body = e.get("content", {}).get("label", "")
                rating_raw = e.get("im:rating", {}).get("label")
                rating = int(rating_raw) if rating_raw else None
                created = e.get("updated", {}).get("label", "")
                review_url = e.get("link", {}).get("attributes", {}).get("href", "")
            except (KeyError, TypeError):
                continue

            text = f"{title}\n\n{body}".strip() if title else body
            if not text:
                continue

            out.append(Review(
                id=f"appstore:{rid}",
                source="appstore",
                text=text,
                rating=rating,
                created_at=created,
                url=review_url,
                raw=e,
            ))

    if not out and empty_responses:
        warnings.warn(
            "iTunes RSS returned no review entries — Apple has been intermittently "
            "shutting this feed down. See docs/decisions.md."
        )
    return out


if __name__ == "__main__":
    rs = fetch_app_store(pages=2)
    print(f"got {len(rs)} reviews")
    for r in rs[:3]:
        print(r.rating, "-", r.text[:80])
