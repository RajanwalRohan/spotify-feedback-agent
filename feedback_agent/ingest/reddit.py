"""Reddit posts via the public .json endpoint. No auth needed, just a polite UA and slow polling."""
import time
import requests
from .app_store import Review


DEFAULT_SUBS = ["spotify", "truespotify", "spotifypremium"]


def fetch_reddit(subs: list[str] | None = None, pages: int = 4, user_agent: str = "spotify-feedback-agent/0.1") -> list[Review]:
    subs = subs or DEFAULT_SUBS
    headers = {"User-Agent": user_agent}
    out = []

    for sub in subs:
        after = None
        for _ in range(pages):
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=100"
            if after:
                url += f"&after={after}"

            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 429:
                # rate-limited, sleep and skip this sub
                time.sleep(5)
                break
            if r.status_code != 200:
                break

            data = r.json().get("data", {})
            children = data.get("children", [])
            if not children:
                break

            for c in children:
                p = c.get("data", {})
                title = p.get("title", "")
                selftext = p.get("selftext", "")
                # link posts have no body — skip, they're not feedback signal
                if not selftext.strip():
                    continue

                fullname = p.get("name", "")  # e.g. t3_abc123
                created = p.get("created_utc", 0)
                permalink = p.get("permalink", "")

                text = f"{title}\n\n{selftext}".strip()
                out.append(Review(
                    id=f"reddit:{fullname}",
                    source="reddit",
                    text=text,
                    rating=None,
                    created_at=str(created),
                    url=f"https://reddit.com{permalink}" if permalink else "",
                    raw=p,
                ))

            after = data.get("after")
            if not after:
                break
            # be polite
            time.sleep(2)

    return out


if __name__ == "__main__":
    rs = fetch_reddit(pages=1)
    print(f"got {len(rs)} posts")
    for r in rs[:3]:
        print(r.text[:100])
