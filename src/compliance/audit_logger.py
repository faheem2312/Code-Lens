import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)


def log_audit_event(event: dict) -> None:
    try:
        supabase.table("audit_logs").insert(event).execute()
    except Exception as e:
        print(f"  Warning: Audit log failed (non-critical): {e}")
