from src.ingestion.parser import extract_functions

chunks = extract_functions("src/ingestion/parser.py")
for c in chunks:
    print(f"Found: {c['function_name']} ({c['start_line']}-{c['end_line']})")