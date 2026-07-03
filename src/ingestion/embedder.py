"""
Embedding interface for CodeLens.
Uses gemini-embedding-2 via gemini_client.py.
"""
from src.gemini_client import embed_texts as _embed_texts
from src.gemini_client import embed_single as _embed_single
from src.gemini_client import EMBEDDING_DIM

__all__ = ["embed_texts", "embed_single", "EMBEDDING_DIM"]


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _embed_texts(texts)


def embed_single(text: str) -> list[float]:
    return _embed_single(text)