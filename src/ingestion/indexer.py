import os
import shutil
import subprocess
import tempfile
import stat
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from threading import Lock
from typing import Optional

from src.ingestion.parser      import extract_functions, SKIP_DIRS
from src.ingestion.chunker     import enrich_chunk
from src.ingestion.embedder    import embed_texts
from src.compliance.pii_detector import scan_for_pii, redact_pii
from src.compliance.secret_scanner import scan_and_redact_secrets
from src.utils import normalize_repo_url

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".json", ".yaml", ".yml", ".toml", ".md",
    ".go", ".java", ".rs", ".cpp", ".c", ".h"
}
BATCH_SIZE = 10


def safe_rmtree(path: str):
    """Recursively delete a directory, handling read-only files on Windows."""
    def remove_readonly(func, file_path, excinfo):
        try:
            os.chmod(file_path, stat.S_IWRITE)
            func(file_path)
        except Exception:
            pass  # ignore if it still fails

    if os.path.exists(path):
        shutil.rmtree(path, onerror=remove_readonly)



class IndexingTaskManager:
    def __init__(self):
        self._lock = Lock()
        self._tasks = {}  # repo_url -> {"status": "processing", "logs": [], "cancel_requested": bool}

    def start_task(self, repo_url: str):
        with self._lock:
            self._tasks[repo_url] = {
                "status": "processing",
                "logs": ["🚀 Initializing indexing task..."],
                "cancel_requested": False
            }

    def log(self, repo_url: str, message: str):
        with self._lock:
            if repo_url in self._tasks:
                self._tasks[repo_url]["logs"].append(message)
                try:
                    print(f"[{repo_url}] {message}")  # Console fallback
                except UnicodeEncodeError:
                    # Strip emojis or non-cp1252 characters for Windows console fallback
                    clean_msg = message.encode('ascii', errors='ignore').decode('ascii')
                    print(f"[{repo_url}] {clean_msg.strip()}")

    def is_cancelled(self, repo_url: str) -> bool:
        with self._lock:
            task = self._tasks.get(repo_url)
            if task:
                return task["cancel_requested"]
            return False

    def cancel_task(self, repo_url: str):
        with self._lock:
            if repo_url in self._tasks:
                self._tasks[repo_url]["cancel_requested"] = True
                self._tasks[repo_url]["status"] = "cancelling"
                self._tasks[repo_url]["logs"].append("⚠️ Cancel requested by user. Aborting...")

    def complete_task(self, repo_url: str, status: str = "completed"):
        with self._lock:
            if repo_url in self._tasks:
                self._tasks[repo_url]["status"] = status
                self._tasks[repo_url]["logs"].append(f"🏁 Task finished with status: {status.upper()}")

    def get_task_info(self, repo_url: str):
        with self._lock:
            return self._tasks.get(repo_url)


# Global task manager instance
task_manager = IndexingTaskManager()


def clone_repo(repo_url: str) -> str:
    """Clone a GitHub repo into temp directory and return the local path."""
    repo_name = repo_url.rstrip("/").split("/")[-1]
    temp_dir = tempfile.gettempdir()
    clone_path = os.path.join(temp_dir, f"codelens_{repo_name}")

    # Remove if exists
    if os.path.exists(clone_path):
        safe_rmtree(clone_path)

    task_manager.log(repo_url, f"📥 Cloning repository: {repo_url} ...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", repo_url, clone_path],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")

    task_manager.log(repo_url, "✅ Repository cloned successfully.")
    return clone_path


def get_existing_files_info(repo_url: str) -> dict[str, str]:
    result = (
        supabase.table("chunks")
        .select("file_path, file_hash")
        .eq("repo_url", repo_url)
        .execute()
    )
    return {row["file_path"]: row["file_hash"] for row in (result.data or [])}


def index_repository(repo_path: str, repo_url: str, user_email: Optional[str] = None) -> dict:
    repo_url = normalize_repo_url(repo_url)
    task_manager.log(repo_url, "🔍 Scanning codebase directories...")

    db_files = get_existing_files_info(repo_url)
    
    # Check if there are legacy absolute paths and purge them
    has_legacy_paths = any(os.path.isabs(p) or "temp" in p.lower() or "\\" in p for p in db_files.keys())
    if has_legacy_paths:
        task_manager.log(repo_url, "🧹 Legacy absolute paths detected. Purging old database chunks...")
        try:
            supabase.table("chunks").delete().eq("repo_url", repo_url).execute()
        except Exception as e:
            task_manager.log(repo_url, f"⚠️ Error purging legacy chunks: {e}")
        db_files = {}

    all_chunks: list[dict] = []
    scanned_paths = set()

    for file in Path(repo_path).rglob("*"):
        if task_manager.is_cancelled(repo_url):
            raise InterruptedError("Cancelled")
            
        if file.suffix not in SUPPORTED_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in file.parts):
            continue
            
        # Get relative path with forward slashes
        rel_path = str(file.relative_to(repo_path)).replace("\\", "/")
        scanned_paths.add(rel_path)
        
        chunks = extract_functions(str(file))
        # Override absolute paths with relative paths in chunks
        for chunk in chunks:
            chunk["file_path"] = rel_path
        all_chunks.extend(chunks)

    task_manager.log(repo_url, f"📦 Found {len(all_chunks)} logical function blocks across codebase.")

    # Track which files need to be deleted first
    paths_to_delete = set()
    enriched:     list[dict] = []
    skipped:      int        = 0
    pii_redacted: int        = 0

    total_chunks = len(all_chunks)
    task_manager.log(repo_url, f"🛡️ Scanning {total_chunks} blocks for PII and secrets...")

    for idx, chunk in enumerate(all_chunks, 1):
        if task_manager.is_cancelled(repo_url):
            raise InterruptedError("Cancelled")
            
        ec = enrich_chunk(chunk, repo_url)
        rel_path = ec["file_path"]

        # Check if file has changed
        if rel_path in db_files:
            if ec["file_hash"] == db_files[rel_path]:
                skipped += 1
                continue
            else:
                # File modified - mark for deletion of old chunks
                paths_to_delete.add(rel_path)

        # 1. PII Scan
        scan = scan_for_pii(ec["content"])
        if scan["has_pii"]:
            ec["content"]    = redact_pii(ec["content"])
            ec["embed_text"] = redact_pii(ec["embed_text"])
            pii_redacted += 1

        # 2. Secret & Credential Scan
        redacted_content, has_secrets, _ = scan_and_redact_secrets(ec["content"])
        if has_secrets:
            ec["content"]    = redacted_content
            ec["embed_text"] = redact_pii(redacted_content)

        enriched.append(ec)

        if idx % 50 == 0 or idx == total_chunks:
            task_manager.log(repo_url, f"  🛡️ Security scanned {idx}/{total_chunks} blocks...")

    # Handle deletions for modified files
    if paths_to_delete:
        task_manager.log(repo_url, f"🧹 Clearing old chunks for {len(paths_to_delete)} modified files...")
        for p in paths_to_delete:
            try:
                supabase.table("chunks").delete().eq("repo_url", repo_url).eq("file_path", p).execute()
            except Exception as e:
                task_manager.log(repo_url, f"⚠️ Error deleting chunks for {p}: {e}")

    # Handle deletions for deleted files
    deleted_paths = set(db_files.keys()) - scanned_paths
    if deleted_paths:
        task_manager.log(repo_url, f"🗑️ Purging {len(deleted_paths)} deleted files from database...")
        for p in deleted_paths:
            try:
                supabase.table("chunks").delete().eq("repo_url", repo_url).eq("file_path", p).execute()
            except Exception as e:
                task_manager.log(repo_url, f"⚠️ Error purging deleted file {p}: {e}")

    task_manager.log(repo_url, f"⏭️ Skipped {skipped} unchanged files | 🛡️ Redacted {pii_redacted} PII elements.")
    
    if not enriched:
        task_manager.log(repo_url, "✨ No new or changed chunks to embed.")
        # Increment repo count on user profile if this was first indexing of the repo
        if user_email:
            from src.api.auth import user_manager
            user_manager.add_user_repository(user_email, repo_url)
            if not db_files:
                user_manager.increment_repos_indexed(user_email)
            
        return {
            "total_found": len(all_chunks),
            "skipped": skipped,
            "indexed": 0,
            "pii_redacted": pii_redacted,
        }

    task_manager.log(repo_url, f"✨ Generating embeddings for {len(enriched)} new/modified chunks...")

    indexed = 0
    total_batches = (len(enriched) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(enriched), BATCH_SIZE):
        if task_manager.is_cancelled(repo_url):
            raise InterruptedError("Cancelled")
            
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
        task_manager.log(repo_url, f"  ⚡ Batch {i // BATCH_SIZE + 1} of {total_batches} indexed ({len(batch)} chunks)")

    task_manager.log(repo_url, f"🎉 Done! {indexed} chunks indexed successfully.")
    
    if user_email:
        from src.api.auth import user_manager
        user_manager.add_user_repository(user_email, repo_url)
        user_manager.increment_repos_indexed(user_email)

    return {
        "total_found":  len(all_chunks),
        "skipped":      skipped,
        "indexed":      indexed,
        "pii_redacted": pii_redacted,
    }


def clone_and_index(repo_url: str, user_email: Optional[str] = None) -> dict:
    """Clone a GitHub repo and index it — used by the API."""
    repo_url = normalize_repo_url(repo_url)
    task_manager.start_task(repo_url)
    repo_path = ""
    try:
        repo_path = clone_repo(repo_url)
        if task_manager.is_cancelled(repo_url):
            task_manager.complete_task(repo_url, "cancelled")
            return {"status": "cancelled"}

        result = index_repository(repo_path, repo_url, user_email)
        if task_manager.is_cancelled(repo_url):
            task_manager.complete_task(repo_url, "cancelled")
            return {"status": "cancelled"}

        task_manager.complete_task(repo_url, "completed")
        return result
    except Exception as e:
        if task_manager.is_cancelled(repo_url):
            task_manager.complete_task(repo_url, "cancelled")
            return {"status": "cancelled"}
        task_manager.log(repo_url, f"❌ Ingestion failed: {str(e)}")
        task_manager.complete_task(repo_url, "failed")
        raise e
    finally:
        # Clean up cloned repo from local storage
        if repo_path and os.path.exists(repo_path):
            safe_rmtree(repo_path)
            task_manager.log(repo_url, "🧹 Cleaned up temporary repository clone.")