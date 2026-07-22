import sys
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def migrate():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set in the environment.")
        return

    # Loop over pooler hosts to automatically find the project's region
    poolers = [
        "aws-0-ap-south-1.pooler.supabase.com",
        "aws-0-ap-southeast-1.pooler.supabase.com",
        "aws-0-us-east-1.pooler.supabase.com",
        "aws-0-us-west-1.pooler.supabase.com",
        "aws-0-eu-central-1.pooler.supabase.com",
    ]

    conn = None
    for host in poolers:
        print(f"Trying pooler host: {host}...")
        try:
            url = f"postgresql://postgres.bbuzhlhydjarhcktwhdy:MANsuri%40%23123@{host}:6543/postgres"
            conn = psycopg2.connect(url, connect_timeout=5)
            print(f"✅ Connected to pooler: {host}!")
            break
        except Exception as e:
            if "tenant/user" not in str(e):
                print(f"Connection failed: {e}")
            else:
                print(f"Tenant not found in this region.")

    if not conn:
        print("❌ Could not connect to any pooler host.")
        return

    try:
        cursor = conn.cursor()

        sql = """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            tier TEXT DEFAULT 'free',
            repos_indexed INT DEFAULT 0,
            repo_limit INT DEFAULT 3,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
        );
        """
        cursor.execute(sql)
        conn.commit()
        print("Users table created successfully in Supabase Postgres!")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error running migration: {e}")


if __name__ == "__main__":
    migrate()
