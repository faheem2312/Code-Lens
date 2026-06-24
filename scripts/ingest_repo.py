import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

result = supabase.table("chunks").select("id").limit(1).execute()
print("✅ Supabase connected:", result)