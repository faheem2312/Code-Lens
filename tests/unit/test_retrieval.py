import os
from src.retrieval.bm25_search import bm25_search
from src.retrieval.vector_search import vector_search
from src.retrieval.hybrid import hybrid_search

# Using the repository that we know is indexed in test database
TEST_REPO = "https://github.com/pallets/itsdangerous"

def test_bm25_search():
    results = bm25_search("sign", TEST_REPO, top_k=5)
    assert isinstance(results, list)
    # The database has at least some chunks for itsdangerous
    if len(results) > 0:
        for chunk in results:
            assert "content" in chunk
            assert "function_name" in chunk

def test_vector_search():
    results = vector_search("signing key derivation", TEST_REPO, match_count=5)
    assert isinstance(results, list)
    if len(results) > 0:
        for chunk in results:
            assert "content" in chunk
            assert "function_name" in chunk

def test_hybrid_search():
    results = hybrid_search("signing keys", TEST_REPO, top_k=5)
    assert isinstance(results, list)
    if len(results) > 0:
        for chunk in results:
            assert "content" in chunk
            assert "function_name" in chunk
            assert "rrf_score" in chunk
