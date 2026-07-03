import sys, os
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
r = sb.table("chunks").select("repo_url").execute()

# Get unique repo URLs
urls = list({row["repo_url"] for row in r.data})
print(f"Total chunks: {len(r.data)}")
print("Indexed repos:")
for u in urls:
    print(f"  {u}")
