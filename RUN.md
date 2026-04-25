# HireGraph — run and use

## 1. Prerequisites

- Python 3.11+ recommended (project uses 3.12 in `venv/`)
- A Groq API key: https://console.groq.com/

## 2. Setup (first time)

```bash
cd /path/to/hiregraph
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium   # optional: for personal-site crawl during knowledge rebuild
```

Create your env file:

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here
```

### Knowledge index (profile JSON + FAISS)

**Option A — UI:** open the app and use **Rebuild index** (optional `X-Rebuild-Token` if `REBUILD_SECRET` is set in `.env`).

**Option B — Python:**

```bash
python -c "from knowledge.pipeline import build_knowledge_base; print(build_knowledge_base())"
```

Or vector store only:

```bash
python -c "from rag.vector_store import build_vector_store; build_vector_store()"
```

This writes `data/resume_profile.json`, `data/knowledge_meta.json`, and `vector_store/`. By default it also tries to crawl your public site (Playwright), writes `data/crawled_site.md`, and includes it in the index when present. Set `CRAWL_SITE_ON_BUILD=false` to skip the crawl (e.g. CI without Chromium).

## 3. Start the backend

```bash
cd /path/to/hiregraph
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Or:

```bash
./scripts/run_server.sh
```

- API: `http://localhost:8000`
- Health: `GET http://localhost:8000/health`
- UI: **`http://localhost:8000/`** (same origin as the API — required for streaming).

**Do not** open `ui/index.html` as a `file://` URL.

## 4. Use the UI

1. **Send** — ask questions; the graph uses RAG, GitHub tools, optional **web search** (install `duckduckgo-search`), and memory.
2. **New chat** — new `user_id` and fresh history for that id.
3. **Agent trace** — expand on an answer to see thoughts/tools.
4. **Rebuild index** — rebuilds `resume_profile.json` + FAISS + `last_built_at` (see status line above the chat).
5. **Last index build** — shown next to the rebuild controls (`GET /api/knowledge/status`).

## 5. API reference

| Endpoint | Purpose |
|----------|---------|
| `POST /ask/stream` | SSE chat (`query`, `user_id`) |
| `POST /ask`, `POST /ask/async` | JSON chat |
| `GET /api/knowledge/status` | `{ last_built_at, status, error }` |
| `POST /api/knowledge/rebuild` | Full rebuild; header `X-Rebuild-Token` if `REBUILD_SECRET` is set |
| `GET /api/observability/tokens` | Rough char counts per LLM stage |
| `GET /api/info` | App metadata |

## 6. Configuration highlights

| Variable | Purpose |
|----------|---------|
| `RAG_MAX_L2_DISTANCE` | Drop distant chunks (default ~2.2; raise if recall is low) |
| `RAG_TOP_K` | Chunks retrieved before distance filter |
| `SESSION_DB_PATH` | SQLite file for chat history (default `data/sessions.sqlite3`) |
| `MEMORY_MAX_TURNS` | Recent messages injected into memory block |
| `SUMMARY_REFRESH_MESSAGES` | When to compress chat into a rolling summary |
| `REBUILD_SECRET` | If set, rebuild endpoint requires header `X-Rebuild-Token` |
| `CRAWL_SITE_ON_BUILD` | `true` (default): crawl personal site before index build; `false` to skip |

## 7. Troubleshooting

| Issue | What to check |
|--------|----------------|
| UI network error | Server running? Using `http://localhost:8000/` not `file://` |
| LLM errors | `GROQ_API_KEY`, restart uvicorn |
| RAG empty / threshold | Raise `RAG_MAX_L2_DISTANCE` if good chunks are filtered out; lower it to drop weak matches |
| Web search | `pip install duckduckgo-search` (listed in `requirements.txt`) |
| GitHub tools | `GITHUB_TOKEN` optional |
| Rebuild 403 | Set `X-Rebuild-Token` to match `REBUILD_SECRET`, or clear `REBUILD_SECRET` for local dev |

Chat history is stored in **SQLite** (`SESSION_DB_PATH`), so it survives process restarts unless you delete the file.
