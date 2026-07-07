import sys, os
sys.path.insert(0, os.getcwd())

from src.query import query_codelens

result = query_codelens(
    question="How does signing work?",
    repo_url="https://github.com/pallets/itsdangerous",
)

print("=" * 60)
print("ANSWER:")
print(result["answer"])
print()
print("SOURCES:")
for s in result["sources"]:
    print(f"  - {s}")
print()
print(f"Latency : {result['latency_ms']}ms")
print(f"Tokens  : {result['tokens']}")
print(f"Chunks  : {len(result['chunks'])}")
