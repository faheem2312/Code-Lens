import sys, os
sys.path.insert(0, os.getcwd())

from src.ingestion.parser import extract_functions

chunks = extract_functions("src/gemini_client.py")
print(f"Found {len(chunks)} functions:")
for c in chunks:
    print(f"  {c['function_name']}  (lines {c['start_line']}-{c['end_line']})")
