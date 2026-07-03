import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.indexer import index_repository

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/ingest_repo.py <repo_path> <repo_url>")
        sys.exit(1)

    repo_path = sys.argv[1]
    repo_url  = sys.argv[2]
    summary   = index_repository(repo_path, repo_url)
    print(f"\nSummary: {summary}")