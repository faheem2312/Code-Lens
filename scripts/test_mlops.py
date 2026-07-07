import sys, os
sys.path.insert(0, os.getcwd())

from src.query import query_codelens

# Run a query to generate an MLflow run
result = query_codelens(
    question="How does token signing work?",
    repo_url="https://github.com/pallets/itsdangerous",
)
print(f"Query done — Latency: {result['latency_ms']}ms")
print("Now checking MLflow...")

import mlflow
mlflow.set_tracking_uri("mlruns")
client = mlflow.tracking.MlflowClient()
exp = client.get_experiment_by_name("codelens-rag")
runs = client.search_runs(exp.experiment_id, max_results=1)
run = runs[0]
print(f"\nLatest MLflow run:")
print(f"  Run ID    : {run.info.run_id[:8]}...")
print(f"  LLM model : {run.data.params.get('llm_model')}")
print(f"  Latency   : {run.data.metrics.get('latency_ms')}ms")
print(f"  Tokens    : {run.data.metrics.get('tokens_used')}")
print(f"  Rerank    : {run.data.metrics.get('top_rerank_score')}")
