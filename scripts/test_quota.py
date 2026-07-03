import sys, os
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv
load_dotenv()

from src.gemini_client import summarize_function

test_chunk = {
    "file_path": "test.py",
    "function_name": "test_function",
    "language": "py",
    "content": "def test_function(x):\n    return x * 2"
}

summary = summarize_function(test_chunk)
print("✅ Quota available!")
print("Summary:", summary)
