import sys, os
sys.path.insert(0, os.getcwd())

from src.ingestion.parser import extract_functions
from src.ingestion.chunker import enrich_chunk

chunks = extract_functions("src/gemini_client.py")
print(f"Enriching first chunk: {chunks[0]['function_name']}")
print("Calling Gemini for summary...")

enriched = enrich_chunk(chunks[0], repo_url="test-repo")

print()
print("Function :", enriched["function_name"])
print("Summary  :", enriched["summary"])
print("Hash     :", enriched["file_hash"][:16], "...")
print("Embed len:", len(enriched["embed_text"]))
