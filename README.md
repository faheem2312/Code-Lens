# CodeLens: AI-Powered Codebase Q&A & Hybrid Search

CodeLens is a semantic code search, retrieval, and question-answering system. It allows developers to index entire git repositories and ask natural language questions about the codebase structure, classes, and logic.

---

## 🚀 Key Features & Architecture

CodeLens uses a state-of-the-art hybrid RAG (Retrieval-Augmented Generation) pipeline:

```
                  ┌──────────────────────┐
                  │   Git Repository     │
                  └──────────┬───────────┘
                             │ (Clone)
                             ▼
                  ┌──────────────────────┐
                  │ Tree-Sitter Parser   │
                  └──────────┬───────────┘
                             │ (Extract Code Blocks)
                             ▼
                  ┌──────────────────────┐
                  │ Presidio Sanitizer   │
                  └──────────┬───────────┘
                             │ (PII Redacted)
                             ▼
        ┌────────────────────┴────────────────────┐
        ▼                                         ▼
┌──────────────┐                          ┌──────────────┐
│ Gemini Embed │                          │  Sparse FTS  │
└───────┬──────┘                          └──────┬───────┘
        │ (Dense Embedding)                      │ (Text Tokens)
        ▼                                        ▼
┌────────────────────────────────────────────────────────┐
│                   Supabase Database                    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│           Hybrid Search Retrieval (RRF Fusion)         │
└────────────────────────┬───────────────────────────────┘
                         │ (Top Candidates)
                         ▼
┌────────────────────────────────────────────────────────┐
│             Cohere Rerank (v4.0-pro)                   │
└────────────────────────┬───────────────────────────────┘
                         │ (Top Ranked Contexts)
                         ▼
┌────────────────────────────────────────────────────────┐
│             Gemini generation (Flash-Lite)             │
└────────────────────────────────────────────────────────┘
```

1. **Ingestion & AST Parsing**: Codebase repositories are cloned, scanned, and parsed using **Tree-sitter** (supporting `.py`, `.js`, and `.ts`) to extract logical code segments (functions/methods).
2. **Compliance Sanitizer**:
   - **PII Protection**: Uses **Presidio Analyzer & Anonymizer** to detect and redact sensitive entities (emails, keys, phones) before indexing or generation.
   - **Prompt Injection Defense**: Filters inputs against known prompt injection and jailbreak patterns.
3. **Observability**: Traces query performance, token usage, and latencies via **MLflow** and **Langfuse**.
4. **Hybrid Retrieval Pipeline**:
   - **Dense vector search**: Queries Supabase vector store (`pgvector`) using `gemini-embedding-2`.
   - **Sparse text search**: Triggers native Postgres **Full-Text Search (FTS)** matching tokens across content, function names, and summaries.
   - **Fusion & Rerank**: Combines sparse and dense search lists via **Reciprocal Rank Fusion (RRF)**, then reranks candidates using **Cohere** `rerank-v4.0-pro`.
5. **Generation**: Builds a context-aware system prompt and generates structured answers using **Gemini 3.1 Flash-Lite**.

---

## 🛠️ Getting Started

### 1. Installation
Clone the repository and set up a virtual environment:
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory (based on `.env.example`):
```env
# Gemini API Key
GOOGLE_API_KEY=your-api-key
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_EMBED_MODEL=gemini-embedding-2

# Supabase Credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Cohere API Key
COHERE_API_KEY=your-cohere-key
```

### 3. Run the FastAPI Application
Start the uvicorn development server:
```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```
* Access the Web UI: `http://127.0.0.1:8000/`
* Interactive API Docs: `http://127.0.0.1:8000/docs`

### 4. Run Automated Tests
```bash
python -m pytest -v tests/
```

### 5. Run RAG Quality Evaluations (Ragas)
Execute Ragas metrics (Faithfulness, Relevancy, Precision, Recall) and log results to MLflow:
```bash
python scripts/run_eval.py
```

---

## 🔮 Future Enhancements & Technical Roadmap

To further build out CodeLens, we are following a structured phase-by-phase implementation plan:

### Phase 1: Robustness, Optimization, & Quality (Completed)
* [x] **Database-Backed Hybrid Search**: Moved sparse search from in-memory python indexing (`rank-bm25`) to native Postgres Full-Text Search (FTS) to eliminate memory bottlenecks on larger codebases.
* [x] **Unit & Integration Tests**: Established comprehensive pytest suites covering parser, sanitization, compliance redaction, hybrid search, and FastAPI client routing.
* [x] **RAG Evaluation Suite**: Implemented test datasets, Gemini wrappers, and Ragas metrics computation logged directly to MLflow.

### Phase 2: Ingestion & Parsing Expansion (Completed)
* [x] **AST Node Expansion**: Parse entire classes, global constants, package imports, docstrings, and config files (JSON/YAML/TOML) in `parser.py` rather than just function definitions.
* [x] **Multi-Language Support**: Enable Tree-sitter and structural fallback configurations for Go, Rust, Java, C++, HTML, and CSS.
* [x] **HTML & CSS Landing Page Understanding**: Implement fallback text-structure parsing for `.html` and `.css` files. This allows CodeLens to answer layout, markup, and styling questions.
* [x] **AI Ingestion Summaries**: Enrich code chunk metadata and embeddings with AI logic summaries during ingestion.

### Phase 3: Code Semantics & Call-Graph Navigation
* [ ] **Symbol Call-Graph Indexing**: Trace how functions interact. If function A calls function B, store these relationships inside the database.
* [ ] **Context-Aware Retrieval**: Implement Parent-Child chunking relationships (retrieving precise functions, but displaying parent class/file context to the LLM) and Graph RAG expansions.

### Phase 4: Advanced Security & Guardrails
* [ ] **Secret Scanning**: Integrate TruffleHog/git-secrets in the ingestion process to block credentials from being uploaded.
* [ ] **Lightweight LLM Guardrails**: Replace regex sanitizers with a classifier model (like Llama Guard) to block advanced jailbreak attempts.

### Phase 5: Production Readiness & Ops
* [ ] **Docker Containers**: Deploy complete multi-container environments (FastAPI + local Postgres).
* [ ] **WebSocket Real-Time Logging**: Replace polling with a WebSocket connection to stream cloning and indexing logs to the user interface in real-time.

### Phase 6: User Management, Subscriptions, & Billing
* [ ] **Authentication & Authorization**: Implement user registration, secure login/signup sessions, and token-based API access control (JWT).
* [ ] **Payment Gateway Integration**: Integrate Stripe/PayPal subscription models to manage monthly API usage tiers and premium repository limits.
