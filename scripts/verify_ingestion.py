import sys, os
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
r  = sb.table("chunks").select("id, function_name, file_path, summary").limit(5).execute()
print(f"Total chunks in DB: checking...")
count = sb.table("chunks").select("id", count="exact").execute()
print(f"Total: {count.count}")
print()
print("Sample chunks:")
for row in r.data:
    print(f"  {row['function_name']}  →  {row['file_path']}")
    print(f"  Summary: {row['summary'][:80]}")
    print()
