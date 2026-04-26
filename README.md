# HireGraph

Agentic AI interview assistant that answers questions about Vishnesh Vojjala using RAG, GitHub integration, web search, and conversational memory.

## Architecture

- **Backend:** Python / FastAPI / LangGraph
- **LLM:** Groq (llama-3.1-8b-instant)
- **Vector Store:** FAISS with sentence-transformers embeddings
- **Session Store:** SQLite
- **Frontend:** Single-page HTML/CSS/JS chat interface
- **Deployment:** AWS EC2 + NGINX + systemd

## Quick Start

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY
python -c "from knowledge.pipeline import build_knowledge_base; print(build_knowledge_base())"
uvicorn main:app --port 8000
# Open http://localhost:8000
```

## How It Works

```
User Query → Input Guard → Intent Classifier → Memory Inject
  → Supervisor (LLM) ⇄ Tools (RAG / GitHub / Web Search)
  → Answer Generator (LLM) → Critic → Response
```

1. **Input Guard** — Blocks prompt injection attempts
2. **Intent Classifier** — Keyword-based routing (casual, resume, github, web, mixed)
3. **Memory Inject** — Loads structured profile + session summary + recent turns
4. **Supervisor** — LLM decides which tool to call (search_rag, github_repos, github_details, github_languages, web_search, or answer)
5. **Tool Executor** — Runs the selected tool and returns observations
6. **Answer Generator** — LLM produces grounded answer with confidence score
7. **Critic** — Validates quality; retries if confidence is low or answer is ungrounded

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/ask/stream` | POST | SSE streaming chat |
| `/ask` | POST | Synchronous chat |
| `/ask/async` | POST | Async chat |
| `/health` | GET | Health check |
| `/api/knowledge/status` | GET | Index build status |
| `/api/knowledge/rebuild` | POST | Rebuild knowledge index |
| `/api/observability/tokens` | GET | LLM usage stats |
| `/api/info` | GET | App metadata |

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API key for LLM inference |
| `GITHUB_TOKEN` | No | GitHub personal access token |
| `GITHUB_USERNAME` | No | GitHub username (default: vishneshv) |
| `REBUILD_SECRET` | No | Protect the rebuild endpoint |
| `GROQ_MODEL` | No | LLM model (default: llama-3.1-8b-instant) |
| `RAG_TOP_K` | No | Chunks retrieved per query (default: 6) |
| `RAG_MAX_L2_DISTANCE` | No | Max FAISS L2 distance threshold (default: 2.2) |
| `CRAWL_SITE_ON_BUILD` | No | Crawl personal site during index build (default: true) |

## Tech Stack

| Technology | Role |
|---|---|
| FastAPI + Uvicorn | HTTP API server |
| LangGraph | Multi-node agent orchestration |
| LangChain + langchain-groq | LLM integration (Groq) |
| FAISS | Local vector similarity search |
| sentence-transformers | Embeddings (all-MiniLM-L6-v2) |
| PyGithub | GitHub API integration |
| duckduckgo-search | Web search tool |
| Playwright | Personal site crawler |
| SQLite | Session persistence |

## Project Structure

```
├── main.py                  # FastAPI app + all endpoints
├── config/settings.py       # Env-driven configuration singleton
├── graph/                   # LangGraph pipeline (state, nodes, routing, build)
├── agents/                  # LLM client, prompts, intent classifier
├── tools/                   # RAG, GitHub, web search integrations
├── rag/                     # Document loader, embeddings, FAISS store, retriever
├── guardrails/              # Input (injection) and output (hallucination) guards
├── knowledge/               # Knowledge base build pipeline
├── memory/                  # Session store, memory formatting, site crawler
├── observability/           # Token/character usage tracking
├── utils/                   # Logging and retry utilities
├── data/                    # Resume, projects, skills, profile JSON, SQLite DB
├── ui/index.html            # Single-page chat interface
└── scripts/                 # Server launcher and smoke test
```
