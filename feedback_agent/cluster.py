"""HDBSCAN. Picked over k-means because we don't know how many themes there are
and we want a 'noise' bucket for reviews that don't belong to any cluster."""
import numpy as np
from sklearn.cluster import HDBSCAN


def cluster(embeddings: np.ndarray, min_cluster_size: int = 5, min_samples: int = 2) -> np.ndarray:
    # embeddings are L2-normalized, so euclidean is monotonic with cosine — fine and faster
    h = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_method="eom",
    )
    return h.fit_predict(embeddings)


def group_by_cluster(labels: np.ndarray, reviews: list[dict]) -> dict[int, list[dict]]:
    groups: dict[int, list[dict]] = {}
    for label, r in zip(labels, reviews):
        groups.setdefault(int(label), []).append(r)
    return groups
