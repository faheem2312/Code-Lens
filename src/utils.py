def normalize_repo_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    return url.rstrip("/")
