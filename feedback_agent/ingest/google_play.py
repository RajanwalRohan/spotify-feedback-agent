"""Google Play reviews via google-play-scraper."""
from google_play_scraper import reviews, Sort
from .app_store import Review


def fetch_google_play(app_id: str = "com.spotify.music", count: int = 500, lang: str = "en", country: str = "us") -> list[Review]:
    result, _ = reviews(
        app_id,
        lang=lang,
        country=country,
        sort=Sort.NEWEST,
        count=count,
    )

    out = []
    for r in result:
        text = r.get("content") or ""
        if not text.strip():
            continue
        rid = r.get("reviewId", "")
        out.append(Review(
            id=f"googleplay:{rid}",
            source="googleplay",
            text=text,
            rating=r.get("score"),
            created_at=str(r.get("at", "")),
            url="",  # Google Play doesn't expose per-review urls
            raw=r,
        ))
    return out


if __name__ == "__main__":
    rs = fetch_google_play(count=20)
    print(f"got {len(rs)} reviews")
    for r in rs[:3]:
        print(r.rating, "-", r.text[:80])
