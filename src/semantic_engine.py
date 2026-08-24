import os
from functools import lru_cache

from .diff_parser import Hunk

W_SEMANTIC = 6.0
DRIFT_THRESHOLD = 0.45

_model = None


def _get_model():
    global _model
    if _model is None:
        if os.getenv("RISK_DISABLE_EMBEDDINGS") == "1":
            raise RuntimeError("embeddings disabled")
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def _mean_embedding(lines: list[str]):
    model = _get_model()
    cleaned = [line.strip() for line in lines if line.strip()]
    if not cleaned:
        return None
    return model.encode(cleaned, batch_size=32).mean(axis=0)


@lru_cache(maxsize=512)
def _cached_encode(text: str):
    model = _get_model()
    return tuple(model.encode([text])[0].tolist())


def hunk_semantic_shift(hunk: Hunk) -> float | None:
    try:
        old_emb = _mean_embedding(hunk.removed_lines)
        new_emb = _mean_embedding(hunk.added_lines)
    except RuntimeError:
        return None
    if old_emb is None or new_emb is None:
        return None
    dot = sum(a * b for a, b in zip(old_emb, new_emb))
    norm = (sum(a * a for a in old_emb) ** 0.5) * (sum(b * b for b in new_emb) ** 0.5)
    if norm == 0:
        return None
    return round(float(1.0 - dot / norm), 4)


def max_shift(files) -> float | None:
    shifts = [s for fd in files for h in fd.hunks if (s := hunk_semantic_shift(h)) is not None]
    return max(shifts) if shifts else None
