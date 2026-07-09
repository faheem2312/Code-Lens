import os
import shutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

from src.ingestion.parser      import extract_functions, SKIP_DIRS
from src.ingestion.chunker     import enrich_chunk
from src.ingestion.embedder    import embed_texts
from src.compliance.pii_detector import scan_for_pii, redact_pii

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts"}
BATCH_SIZE = 10


def clone_repo(repo_url: str) -> str:
    """Clone a GitHub repo into /tmp and return the local path."""
    repo_name = repo_url.rstrip("/").split("/")[-1]
    clone_path = f"/tmp/{repo_name}"

    # Remove if exists
    if os.path.exists(clone_path):
        shutil.rmtree(clone_path)

    print(f"  📥 Cloning {repo_url}...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", repo_url, clone_path],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")

    print(f"  ✅ Cloned to {clone_path}")
    return clone_path


def get_existing_hashes(repo_url: str) -> set[str]:
    result = (
        supabase.table("chunks")
        .select("file_hash")
        .eq("repo_url", repo_url)
        .execute()
    )
    return {row["file_hash"] for row in result.data}


def index_repository(repo_path: str, repo_url: str) -> dict:
    print(f"\n🔍 Scanning {repo_path}...")

    existing_hashes = get_existing_hashes(repo_url)
    all_chunks: list[dict] = []

    for file in Path(repo_path).rglob("*"):
        if file.suffix not in SUPPORTED_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in file.parts):
            continue
        chunks = extract_functions(str(file))
        all_chunks.extend(chunks)

    print(f"📦 Found {len(all_chunks)} functions across the repo")

    enriched:     list[dict] = []
    skipped:      int        = 0
    pii_redacted: int        = 0

    for chunk in all_chunks:
        ec = enrich_chunk(chunk, repo_url)

        if ec["file_hash"] in existing_hashes:
            skipped += 1
            continue

        scan = scan_for_pii(ec["content"])
        if scan["has_pii"]:
            ec["content"]    = redact_pii(ec["content"])
            ec["embed_text"] = redact_pii(ec["embed_text"])
            pii_redacted += 1

        enriched.append(ec)

    print(f"  ⏭️  Skipped {skipped} unchanged | 🛡️  Redacted {pii_redacted}")
    print(f"  ✨ Embedding {len(enriched)} new chunks...")

    indexed = 0
    for i in range(0, len(enriched), BATCH_SIZE):
        batch   = enriched[i : i + BATCH_SIZE]
        texts   = [c["embed_text"] for c in batch]
        vectors = embed_texts(texts)

        rows = [
            {
                "repo_url":      c["repo_url"],
                "file_path":     c["file_path"],
                "function_name": c["function_name"],
                "language":      c["language"],
                "start_line":    c["start_line"],
                "end_line":      c["end_line"],
                "content":       c["content"],
                "summary":       c["summary"],
                "file_hash":     c["file_hash"],
                "embedding":     vec,
            }
            for c, vec in zip(batch, vectors)
        ]

        supabase.table("chunks").insert(rows).execute()
        indexed += len(batch)
        print(f"    ✅ Batch {i // BATCH_SIZE + 1} — {len(batch)} chunks")

    print(f"\n🎉 Done! {indexed} chunks indexed.")
    return {
        "total_found":  len(all_chunks),
        "skipped":      skipped,
        "indexed":      indexed,
        "pii_redacted": pii_redacted,
    }


def clone_and_index(repo_url: str) -> dict:
    """Clone a GitHub repo and index it — used by the API."""
    repo_path = clone_repo(repo_url)
    try:
        result = index_repository(repo_path, repo_url)
    finally:
        # Clean up cloned repo from /tmp
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
            print(f"  🧹 Cleaned up {repo_path}")
    return result