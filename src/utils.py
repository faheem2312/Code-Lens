def normalize_repo_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    
    # Handle accidental double-pasting (e.g. https://github.com/user/repohttps://github.com/user/repo)
    if url.count("https://") > 1:
        parts = [p for p in url.split("https://") if p]
        url = "https://" + parts[0]
    elif url.count("http://") > 1:
        parts = [p for p in url.split("http://") if p]
        url = "http://" + parts[0]

    if url.endswith(".git"):
        url = url[:-4]
    return url.rstrip("/")

