"""Evaluation script. Two automated checks:

1. Adjusted Rand Index - how well do the predicted clusters match the labeled
   themes overall? 1.0 is perfect, ~0 is random.
2. Cluster purity - within each predicted cluster, what fraction of reviews
   share the modal expected theme? 1.0 means every predicted cluster is
   internally consistent (even if the algorithm split one theme into multiple).

We deliberately don't try to LLM-judge the synthesis here - that's a manual
spot-check pass on the generated brief vs. the labels, documented in the README.
"""
import csv
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import adjusted_rand_score, homogeneity_score

from feedback_agent.embed import embed
from feedback_agent.cluster import cluster, group_by_cluster


LABELS_PATH = Path(__file__).parent / "labels.csv"


def load_labels() -> tuple[list[str], list[str]]:
    texts, themes = [], []
    with open(LABELS_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts.append(row["review_text"])
            themes.append(row["expected_theme"])
    return texts, themes


def purity(predicted: np.ndarray, expected: list[str]) -> float:
    correct = 0
    total = 0
    for c in set(predicted):
        if c == -1:
            continue  # don't count noise bucket
        members = [expected[i] for i, p in enumerate(predicted) if p == c]
        if not members:
            continue
        modal = Counter(members).most_common(1)[0][1]
        correct += modal
        total += len(members)
    return correct / total if total else 0.0


def main():
    texts, expected = load_labels()
    print(f"loaded {len(texts)} labeled reviews, {len(set(expected))} unique themes")

    vecs = embed(texts)
    # tighter min_cluster_size for the small labeled set
    predicted = cluster(vecs, min_cluster_size=2, min_samples=1)

    n_clusters = len({p for p in predicted if p != -1})
    n_noise = int((predicted == -1).sum())
    print(f"\npredicted {n_clusters} clusters, {n_noise} in noise bucket")

    ari = adjusted_rand_score(expected, predicted)
    homo = homogeneity_score(expected, predicted)
    pur = purity(predicted, expected)

    print(f"\nadjusted rand index : {ari:.3f}   (1.0 = perfect, ~0 = random)")
    print(f"homogeneity         : {homo:.3f}   (1.0 = each cluster has one theme)")
    print(f"purity              : {pur:.3f}   (fraction in modal theme of their cluster)")

    print("\nper-cluster theme distribution:")
    groups = group_by_cluster(predicted, [{"theme": e} for e in expected])
    for cid in sorted(groups.keys()):
        if cid == -1:
            continue
        themes = [r["theme"] for r in groups[cid]]
        counts = Counter(themes).most_common()
        head = ", ".join(f"{t}={n}" for t, n in counts[:3])
        print(f"  cluster {cid:>2}: {head}")


if __name__ == "__main__":
    main()
