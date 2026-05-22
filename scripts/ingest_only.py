"""Just the ingest step. Useful when iterating on clustering or synthesis
and you don't want to wait on the network every time."""
from dotenv import load_dotenv

from feedback_agent.ingest import fetch_app_store, fetch_google_play, fetch_reddit
from feedback_agent.store import save, count


def main():
    load_dotenv()
    rs = fetch_app_store(pages=5) + fetch_google_play(count=500) + fetch_reddit(pages=3)
    new = save(rs)
    print(f"fetched {len(rs)}, {new} new, db total: {count()}")


if __name__ == "__main__":
    main()
