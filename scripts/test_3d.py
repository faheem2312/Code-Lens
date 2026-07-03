import sys, os
sys.path.insert(0, os.getcwd())

from src.ingestion.embedder import embed_single, embed_texts

print("Testing embed_single...")
vec = embed_single("def authenticate_user(token): pass")
print(f"  Dimension : {len(vec)}")
print(f"  First 5   : {[round(v,4) for v in vec[:5]]}")

print()
print("Testing embed_texts (batch of 3)...")
vecs = embed_texts([
    "def login(user, password): pass",
    "def logout(session): pass",
    "def reset_password(email): pass",
])
print(f"  Batch size    : {len(vecs)}")
print(f"  Each dimension: {len(vecs[0])}")
print("  All dims match:", all(len(v) == 768 for v in vecs))
