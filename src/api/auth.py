import hashlib
import hmac
import os
import json
import base64
import time
from typing import Optional

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "codelens-super-secret-key-2026")
ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 86400  # 24 hours


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with SHA256 and a random salt."""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return base64.b64encode(salt + pwd_hash).decode("utf-8")


def verify_password(password: str, hashed_password_str: str) -> bool:
    """Verify password against salted PBKDF2 hash string."""
    try:
        decoded = base64.b64decode(hashed_password_str.encode("utf-8"))
        salt = decoded[:16]
        stored_hash = decoded[16:]
        computed_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(stored_hash, computed_hash)
    except Exception:
        return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _base64url_decode(data_str: str) -> bytes:
    padding = '=' * (4 - (len(data_str) % 4))
    return base64.urlsafe_b64decode((data_str + padding).encode('utf-8'))


def create_access_token(data: dict, expires_in: int = TOKEN_EXPIRE_SECONDS) -> str:
    """Create signed HMAC-SHA256 JWT token."""
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in

    header_b64 = _base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload).encode("utf-8"))

    to_sign = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), to_sign, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode signed JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        to_sign = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), to_sign, hashlib.sha256).digest()
        actual_sig = _base64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


# Supabase-backed User Database Manager with In-Memory Fallback
class UserManager:
    def __init__(self):
        self._in_memory_users = {}
        self._in_memory_user_repos = {}

    def register_user(self, email: str, password: str, full_name: str = "") -> dict:
        email_clean = email.strip().lower()
        
        user_id = f"usr_{hashlib.md5(email_clean.encode()).hexdigest()[:10]}"
        user_record = {
            "user_id": user_id,
            "email": email_clean,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "tier": "free",
            "repos_indexed": 0,
            "repo_limit": 3,
        }

        use_in_memory = True
        if supabase:
            try:
                # Check for existing email first in Supabase
                existing = supabase.table("users").select("*").eq("email", email_clean).execute()
                if existing.data:
                    raise ValueError("Email is already registered.")
                
                # Insert into Supabase
                supabase.table("users").insert(user_record).execute()
                use_in_memory = False
            except Exception as e:
                if "relation \"users\" does not exist" in str(e).lower() or "cache" in str(e).lower():
                    # Graceful fallback to in-memory for tests or un-migrated setups
                    use_in_memory = True
                else:
                    raise e

        if use_in_memory:
            if email_clean in self._in_memory_users:
                raise ValueError("Email is already registered.")
            self._in_memory_users[email_clean] = user_record
            
        return user_record

    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        email_clean = email.strip().lower()
        
        if supabase:
            try:
                res = supabase.table("users").select("*").eq("email", email_clean).execute()
                if res.data:
                    user = res.data[0]
                    if verify_password(password, user["password_hash"]):
                        return user
                    return None
            except Exception:
                pass

        user = self._in_memory_users.get(email_clean)
        if user and verify_password(password, user["password_hash"]):
            return user
        return None

    def get_user(self, email: str) -> Optional[dict]:
        email_clean = email.strip().lower()
        if supabase:
            try:
                res = supabase.table("users").select("*").eq("email", email_clean).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        return self._in_memory_users.get(email_clean)

    def update_tier(self, email: str, tier: str) -> Optional[dict]:
        email_clean = email.strip().lower()
        repo_limit = 999999 if tier == "pro" else 3
        if supabase:
            try:
                res = supabase.table("users").update({"tier": tier, "repo_limit": repo_limit}).eq("email", email_clean).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass

        user = self._in_memory_users.get(email_clean)
        if user:
            user["tier"] = tier
            user["repo_limit"] = repo_limit
            return user
        return None

    def increment_repos_indexed(self, email: str) -> Optional[dict]:
        email_clean = email.strip().lower()
        if supabase:
            try:
                res = supabase.table("users").select("repos_indexed").eq("email", email_clean).execute()
                if res.data:
                    curr = res.data[0].get("repos_indexed", 0)
                    res2 = supabase.table("users").update({"repos_indexed": curr + 1}).eq("email", email_clean).execute()
                    if res2.data:
                        return res2.data[0]
            except Exception:
                pass

        user = self._in_memory_users.get(email_clean)
        if user:
            user["repos_indexed"] = user.get("repos_indexed", 0) + 1
            return user
        return None

    def add_user_repository(self, email: str, repo_url: str):
        email_clean = email.strip().lower()
        use_in_memory = True
        
        if supabase:
            try:
                res = supabase.table("users").select("user_id").eq("email", email_clean).execute()
                if res.data:
                    uid = res.data[0]["user_id"]
                    link_res = supabase.table("user_repositories").select("*").eq("user_id", uid).eq("repo_url", repo_url).execute()
                    if not link_res.data:
                        supabase.table("user_repositories").insert({"user_id": uid, "repo_url": repo_url}).execute()
                    use_in_memory = False
            except Exception:
                use_in_memory = True

        if use_in_memory:
            if email_clean not in self._in_memory_user_repos:
                self._in_memory_user_repos[email_clean] = []
            if repo_url not in self._in_memory_user_repos[email_clean]:
                self._in_memory_user_repos[email_clean].append(repo_url)

    def get_user_repositories(self, email: str) -> list[str]:
        email_clean = email.strip().lower()
        if supabase:
            try:
                res = supabase.table("users").select("user_id").eq("email", email_clean).execute()
                if res.data:
                    uid = res.data[0]["user_id"]
                    links_res = supabase.table("user_repositories").select("repo_url").eq("user_id", uid).execute()
                    return [r["repo_url"] for r in (links_res.data or [])]
            except Exception:
                pass
        return self._in_memory_user_repos.get(email_clean, [])

    def delete_user_repository(self, email: str, repo_url: str):
        email_clean = email.strip().lower()
        use_in_memory = True
        if supabase:
            try:
                res = supabase.table("users").select("user_id").eq("email", email_clean).execute()
                if res.data:
                    uid = res.data[0]["user_id"]
                    supabase.table("user_repositories").delete().eq("user_id", uid).eq("repo_url", repo_url).execute()
                    use_in_memory = False
            except Exception:
                use_in_memory = True
        if use_in_memory:
            if email_clean in self._in_memory_user_repos:
                if repo_url in self._in_memory_user_repos[email_clean]:
                    self._in_memory_user_repos[email_clean].remove(repo_url)


user_manager = UserManager()
