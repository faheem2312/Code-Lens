import sys
from unittest.mock import MagicMock

# Shim for ragas langchain import bug
sys.modules["langchain_community.chat_models.vertexai"] = MagicMock()

import os
import json
import mlflow
from datasets import Dataset
from dotenv import load_dotenv

# Load env variables using absolute path
env_path = os.path.join(os.getcwd(), ".env")
load_dotenv(env_path)

from src.query import query_codelens
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall


def run_rag_evaluation(
    repo_url: str = "https://github.com/pallets/itsdangerous",
    dataset_path: str = "evaluations/test_dataset.json",
) -> dict:
    """
    Runs evaluation on the CodeLens RAG system using Ragas metrics,
    and logs the evaluation run details to MLflow.
    """
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Test dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    evaluation_data = []

    print(f"🚀 Running CodeLens Q&A pipeline over {len(test_cases)} evaluation questions...")
    for idx, case in enumerate(test_cases):
        q = case["question"]
        gt = case["ground_truth"]

        print(f"  [{idx + 1}/{len(test_cases)}] Querying: '{q[:50]}...'")
        try:
            result = query_codelens(question=q, repo_url=repo_url, top_k=5)
            
            # Format contexts as list of strings (raw code contents)
            contexts = [chunk["content"] for chunk in result["chunks"]]
            
            evaluation_data.append({
                "question": q,
                "answer": result["answer"],
                "contexts": contexts,
                "ground_truth": gt,
            })
        except Exception as e:
            print(f"    ⚠️ Query pipeline failed on test case: {e}")
            continue

    if not evaluation_data:
        print("❌ No evaluation data collected. Evaluation aborted.")
        return {}

    # Convert evaluation list into HuggingFace dataset format for Ragas
    # Dict of lists format:
    dataset_dict = {
        "question": [item["question"] for item in evaluation_data],
        "answer": [item["answer"] for item in evaluation_data],
        "contexts": [item["contexts"] for item in evaluation_data],
        "ground_truth": [item["ground_truth"] for item in evaluation_data],
    }
    dataset = Dataset.from_dict(dataset_dict)

    print("🧠 Setting up Gemini wrappers for Ragas evaluation...")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    
    # Use configured Gemini model and embedding model for evaluation
    eval_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    eval_embed = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-2")
    evaluator_llm = ChatGoogleGenerativeAI(model=eval_model, google_api_key=google_api_key)
    evaluator_embeddings = GoogleGenerativeAIEmbeddings(model=eval_embed, google_api_key=google_api_key)
    
    ragas_llm = LangchainLLMWrapper(evaluator_llm)
    ragas_embeddings = LangchainEmbeddingsWrapper(evaluator_embeddings)

    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]

    print("⚡ Starting Ragas metrics computation...")
    eval_result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=ragas_llm,
        embeddings=ragas_embeddings,
    )


    # Convert EvaluationResult to standard dictionary (aggregating list of scores)
    scores_dict = {}
    for metric in metrics:
        name = metric.name
        try:
            val = eval_result[name]
            if isinstance(val, list):
                # Filter out None values
                clean_list = [v for v in val if v is not None]
                scores_dict[name] = sum(clean_list) / len(clean_list) if clean_list else 0.0
            else:
                scores_dict[name] = float(val)
        except (KeyError, ValueError, TypeError):
            pass

    print("\n================ EVALUATION SUMMARY ==================")
    for metric_name, score in scores_dict.items():
        print(f"  {metric_name.capitalize()}: {score:.4f}")
    print("======================================================")

    # Log to MLflow
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("codelens-rag-evaluation")
    
    try:
        with mlflow.start_run(run_name="ragas-evaluation"):
            mlflow.log_params({
                "repo_url": repo_url,
                "dataset_size": len(evaluation_data),
                "evaluator_llm": eval_model,
                "evaluator_embeddings": eval_embed,
            })
            
            # Log metrics to mlflow
            mlflow.log_metrics(scores_dict)
            print("✅ Evaluation results logged to MLflow successfully!")
    except Exception as e:
        print(f"  ⚠️ Logging evaluation results to MLflow failed: {e}")

    return scores_dict
