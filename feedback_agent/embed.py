"""Local embeddings. all-MiniLM-L6-v2 is small (~90MB), fast, and good enough for short reviews."""
from sentence_transformers import SentenceTransformer
import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    m = _get_model()
    # normalize so euclidean distance ~ cosine distance downstream
    return m.encode(texts, show_progress_bar=True, normalize_embeddings=True)
