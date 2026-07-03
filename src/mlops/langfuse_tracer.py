import os
from dotenv import load_dotenv

load_dotenv()

_LANGFUSE_ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY")) and bool(os.getenv("LANGFUSE_SECRET_KEY"))

if _LANGFUSE_ENABLED:
    from langfuse import Langfuse, observe, propagate_attributes
    langfuse = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        base_url=os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
    )


def trace_query(fn, system_prompt: str, user_prompt: str, question: str, repo_url: str):
    if not _LANGFUSE_ENABLED:
        return fn(system_prompt, user_prompt)
    try:
        @observe(name="codelens-query", as_type="generation")
        def _traced():
            propagate_attributes(metadata={"repo_url": repo_url}, tags=["codelens"])
            return fn(system_prompt, user_prompt)
        return _traced()
    except Exception as e:
        print(f"  ⚠️ Langfuse tracing failed (non-critical): {e}")
        return fn(system_prompt, user_prompt)
