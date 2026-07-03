import sys, os
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
r  = sb.table("chunks").select("id").limit(1).execute()
print("✅ Supabase connected")
print("Rows in chunks table:", len(r.data))
