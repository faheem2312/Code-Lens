import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

GEMINI_MODEL       = os.getenv("GEMINI_MODEL",       "gemini-3.1-flash-lite")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL",  "gemini-embedding-2")
EMBEDDING_DIM      = int(os.getenv("EMBEDDING_DIM",   "768"))


def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        clean_msg = msg.encode('ascii', errors='ignore').decode('ascii')
        print(clean_msg.strip())


def generate_text(system_prompt: str, user_prompt: str) -> tuple[str, int]:
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1500,
                ),
            )
            text   = response.text or ""
            tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens = getattr(response.usage_metadata, "total_token_count", 0) or 0
            return text, tokens
        except Exception as e:
            if attempt < 2:
                wait = (attempt + 1) * 15
                safe_print(f"  ⚠️ Gemini generate error, retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise


def generate_text_stream(system_prompt: str, user_prompt: str):
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    try:
        response = client.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=1500,
            ),
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        safe_print(f"  ⚠️ Gemini generate stream error: {e}")
        raise


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = []
    for i, text in enumerate(texts):
        for attempt in range(3):
            try:
                prefixed = f"task:code retrieval | {text}"
                result   = client.models.embed_content(
                    model=GEMINI_EMBED_MODEL,
                    contents=prefixed,
                    config=types.EmbedContentConfig(
                        output_dimensionality=EMBEDDING_DIM,
                    ),
                )
                vectors.append(result.embeddings[0].values)
                time.sleep(0.7)  # 100 RPM = 1 per 0.6s, 0.7s is safe
                break
            except Exception as e:
                if attempt < 2:
                    wait = (attempt + 1) * 40
                    safe_print(f"  ⚠️ Embedding rate limit, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise
    return vectors


def embed_single(text: str) -> list[float]:
    prefixed = f"task:search query | {text}"
    result   = client.models.embed_content(
        model=GEMINI_EMBED_MODEL,
        contents=prefixed,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return result.embeddings[0].values


def summarize_function(chunk: dict) -> str:
    prompt = (
        f"In one sentence, describe what this function does.\n"
        f"File: {chunk['file_path']}\n"
        f"Function: {chunk['function_name']}\n\n"
        f"Code:\n{chunk['content'][:1500]}\n\n"
        f"Reply with ONLY the one-sentence description."
    )
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0, max_output_tokens=120),
            )
            return (response.text or "No summary available.").strip()
        except Exception as e:
            if attempt < 2:
                wait = (attempt + 1) * 10
                safe_print(f"  ⚠️ Summary error, retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                return f"Function {chunk['function_name']} in {chunk['file_path']}"
