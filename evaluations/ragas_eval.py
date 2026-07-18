import sys
import os
sys.path.insert(0, os.getcwd())

from src.mlops.evaluator import run_rag_evaluation

if __name__ == "__main__":
    run_rag_evaluation()
