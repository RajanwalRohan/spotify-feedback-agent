"""End-to-end pipeline. Fetch -> embed -> cluster -> synthesize -> render brief."""
from pathlib import Path

from dotenv import load_dotenv

from feedback_agent.ingest import fetch_app_store, fetch_google_play, fetch_reddit
from feedback_agent.store import save, load_all
from feedback_agent.embed import embed
from feedback_agent.cluster import cluster, group_by_cluster
from feedback_agent.synth import synthesize_all
from feedback_agent.brief import render_brief


def main():
    load_dotenv()

    print("fetching reviews...")
    rs = []
    rs += fetch_app_store(pages=5)
    print(f"  app store: {len(rs)}")
    n = len(rs)
    rs += fetch_google_play(count=500)
    print(f"  google play: {len(rs) - n}")
    n = len(rs)
    rs += fetch_reddit(pages=3)
    print(f"  reddit: {len(rs) - n}")
    new = save(rs)
    print(f"  {new} new rows persisted")

    reviews = load_all()
    print(f"\nclustering {len(reviews)} total reviews...")
    texts = [r["text"] for r in reviews]
    vecs = embed(texts)

    labels = cluster(vecs)
    groups = group_by_cluster(labels, reviews)
    real_clusters = {k: v for k, v in groups.items() if k != -1}
    noise_n = len(groups.get(-1, []))
    print(f"  {len(real_clusters)} clusters, {noise_n} reviews in noise bucket")

    print("\nsynthesizing...")
    syntheses = synthesize_all(groups)
    print(f"  {len(syntheses)} coherent themes")

    brief = render_brief(syntheses, total_reviews=len(reviews))
    out = Path("output/brief.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(brief, encoding="utf-8")
    print(f"\nwrote {out.resolve()}")


if __name__ == "__main__":
    main()
