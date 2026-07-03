import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

from src.ingestion.parser import extract_functions
from src.ingestion.chunker import enrich_chunk
from src.ingestion.embedder import embed_texts
from src.compliance.pii_detector import scan_for_pii, redact_pii

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts"}
BATCH_SIZE = 50  # embed 50 chunks per API call


def get_existing_hashes(repo_url: str) -> set[str]:
    """Fetch already-indexed file hashes to skip unchanged files."""
    result = supabase.table("chunks")\
        .select("file_hash")\
        .eq("repo_url", repo_url)\
        .execute()
    return {row["file_hash"] for row in result.data}


def index_repository(repo_path: str, repo_url: str):
    print(f"\n🔍 Scanning {repo_path}...")

    existing_hashes = get_existing_hashes(repo_url)
    all_chunks = []

    # Walk every file in the repo
    for file in Path(repo_path).rglob("*"):
        if file.suffix not in SUPPORTED_EXTENSIONS:
            continue
        if any(p in file.parts for p in ["node_modules", ".git", "venv", "__pycache__"]):
            continue

        chunks = extract_functions(str(file))
        all_chunks.extend(chunks)

    print(f"📦 Found {len(all_chunks)} functions across the repo")

    # Enrich, filter, batch
    enriched, skipped = [], 0
    for chunk in all_chunks:
        ec = enrich_chunk(chunk, repo_url)

        # Skip if already indexed (same hash)
        if ec["file_hash"] in existing_hashes:
            skipped += 1
            continue

        # Compliance: scan and redact PII
        scan = scan_for_pii(ec["content"])
        if scan["has_pii"]:
            print(f"⚠️  PII detected in {ec['file_path']}:{ec['function_name']} — redacting")
            ec["content"]    = redact_pii(ec["content"])
            ec["embed_text"] = redact_pii(ec["embed_text"])

        enriched.append(ec)

    print(f"⏭️  Skipped {skipped} unchanged chunks")
    print(f"✨ Embedding {len(enriched)} new chunks...")

    # Batch embed
    for i in range(0, len(enriched), BATCH_SIZE):
        batch = enriched[i:i + BATCH_SIZE]
        texts = [c["embed_text"] for c in batch]
        vectors = embed_texts(texts)

        rows = []
        for chunk, vector in zip(batch, vectors):
            rows.append({
                "repo_url":      chunk["repo_url"],
                "file_path":     chunk["file_path"],
                "function_name": chunk["function_name"],
                "language":      chunk["language"],
                "start_line":    chunk["start_line"],
                "end_line":      chunk["end_line"],
                "content":       chunk["content"],
                "summary":       chunk["summary"],
                "file_hash":     chunk["file_hash"],
                "embedding":     vector,
            })

        supabase.table("chunks").insert(rows).execute()
        print(f"  ✅ Indexed batch {i // BATCH_SIZE + 1}")

    print(f"\n🎉 Done! {len(enriched)} chunks indexed into Supabase.")