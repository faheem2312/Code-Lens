import os
from src.ingestion.parser import extract_functions

def test_extract_functions_python():
    # Test on a known local python file (e.g., src/gemini_client.py)
    file_path = os.path.join("src", "gemini_client.py")
    chunks = extract_functions(file_path)
    
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    for chunk in chunks:
        assert "file_path" in chunk
        assert "function_name" in chunk
        assert "language" in chunk
        assert "start_line" in chunk
        assert "end_line" in chunk
        assert "content" in chunk
        assert chunk["language"] == "py"
        assert chunk["function_name"] != "anonymous"

def test_extract_html_css_config():
    # Test fallback parser on index.html
    html_path = os.path.join("static", "index.html")
    chunks = extract_functions(html_path)
    
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk["language"] == "html"
        assert "html-section" in chunk["function_name"]

def test_called_symbols_extraction():
    file_path = os.path.join("src", "query.py")
    chunks = extract_functions(file_path)
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert "called_symbols" in chunk
        assert "parent_symbol" in chunk
        assert isinstance(chunk["called_symbols"], list)

def test_extract_functions_unsupported_file():
    # Test on an unsupported file extension
    chunks = extract_functions("image.png")
    assert chunks == []

