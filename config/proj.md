# HireGraph: Codebase Architecture Assessment

This analysis is specific to the actual codebase (`config/settings.py` and associated context), focusing on concrete implementation details, module structures, data flows, LLM orchestration, and architectural decisions.

---

## 1. High-Level Architecture

HireGraph is architected as a modular, environment-driven backend platform for automated recruitment and knowledge management. Its primary pillars are:

- **Centralized Configuration Management:** All operational (and secret) parameters are loaded from environment variables by a singleton `Settings` Python class at runtime.
- **Retrieval-Augmented Generation (RAG) Engine:** Semantic search over knowledge stores via FAISS enables LLMs to answer with domain-relevant context.
- **Session/Memory Management:** Stateful, persistent session and dialogue logs are maintained in an SQLite database, driving conversation continuity and historical analytics.
- **LLM Integration Layer:** Communication with Groq (default) or pluggable LLMs, with all credentials and model choices managed through config.
- **Automated Knowledge Ingestion:** Optional web crawling (Playwright-based) populates the knowledge base, gated by configuration and secrets.
- **Secure, Reproducible Deployments:** All customizations are exposed through environment variables; no hardcoded secrets or paths.

---

## 2. Module-Wise Breakdown

### `config/settings.py`

- **Settings Singleton:**  
  - Encapsulates *all* runtime configuration: API keys, model choices, retrieval thresholds, database paths, log level, memory windows, admin secrets, ingestion toggles.
  - Fields include (`groq_api_key`, `groq_model`, `rag_namespace`, `rag_top_k`, `rag_max_l2_distance`, `session_db_path`, `memory_max_turns`, `summary_refresh_messages`, `rebuild_secret`, `crawl_site_on_build`, etc.).
  - Environment is loaded on demand; no centralized state file.
  - The constructor dynamically parses and type-casts environment (os.getenv with defaults).
  - Wrapped with an LRU cache so the singleton is globally accessible with stable values during a process lifetime.

### RAG/FAISS Engine (implied by context, not shown)

- Handles document ingestion, chunking, and vector search by namespace with top-K and distance filtering.
- Uses settings: `rag_namespace`, `rag_top_k`, `rag_max_l2_distance`.

### LLM Driver (integrates Groq, OpenAI, config-driven)

- Configurability for the target LLM via `groq_model`, with secrets held in env.
- Abstracted API usage; easily swappable models.

### SQLite Session Store

- All session and interaction logs are persisted at the file path referenced by `session_db_path`.
- Context windows (`memory_max_turns`), summarization refreshes, and interaction logs are available for prompt injection and reporting.

### Crawler/Knowledge Ingestion (conditional)

- Playwright-based optional site crawling, toggled by `crawl_site_on_build` and protected by `rebuild_secret`.
- Ingested/crawled documents get added to the FAISS index.

---

## 3. End-to-End Request Flow

1. **Startup:**  
   - On app startup, environment variables are loaded (`dotenv`, then `Settings` singleton instantiation). All operational configuration is set.

2. **User Request / Input:**  
   - UI, CLI, or API receives a user (recruiter, HR) query or command.

3. **Session Management:**  
   - The user's session and conversation are restored or initialized from the SQLite3 database.

4. **Knowledge Retrieval:**  
   - If a retrieval is triggered, a FAISS search is done:
     - Uses `settings.rag_namespace`, `settings.rag_top_k`, `settings.rag_max_l2_distance`.
     - Sources: previously uploaded documents, crawled data (if enabled), or other indexed knowledge.

5. **LLM Context Preparation:**  
   - The LLM prompt is constructed from user query, retrieved document chunks, and context window (`memory_max_turns`).

6. **LLM Inference:**  
   - The chosen LLM is contacted using credentials and model from settings.
   - Results (answers/summaries) are computed.

7. **Response & Logging:**  
   - LLM outputs are logged in session DB.
   - If message count exceeds `summary_refresh_messages`, a summarization operation is triggered, clearing historical context and storing summaries.

8. **Admin Actions (Optional):**  
   - Re-indexing or knowledge base building can be invoked via secret-protected endpoints and environment-driven triggers.

---

## 4. LLM Integration Flow

- **Model Choices:**  
  - Controlled by `groq_model` (e.g., "llama-3.1-8b-instant"), defaulted and overrideable.
- **API Keys:**  
  - All API keys (Groq, OpenAI, Github) are env-driven. Keys never hardcoded.
- **Invocation:**  
  - Payload consists of user query + top relevant FAISS chunks + session context window.
- **Output:**  
  - Generated answers (or summaries) are returned and logged.

---

## 5. Tools and Data Flow

- **Settings Loader:**  
  - Loads all configuration from env on each cold start. Cached singleton for dependency injection.
- **FAISS:**  
  - Used for knowledge indexing and retrieval via vector similarity.
- **SQLite:**  
  - Persists all session, interaction, and memory data (`data/sessions.sqlite3` by default).
- **Playwright:**  
  - Optionally used (if enabled) for crawling websites to ingest knowledge.
- **Environment Variables:**  
  - Single source of configuration truth (see `config/settings.py` for full field list).

---

## 6. Design Decisions

- **All-Env Configuration:**  
  - Maximizes deployability, secret security, and environment isolation.
- **Centralized Settings Singleton:**  
  - Easier DI, testability, modification, and code clarity.
- **Persistent SQLite Session DB:**  
  - Enables context continuity, reporting, analytics, and summary refreshes with minimal ops overhead.
- **Pluggable LLM Layer:**  
  - LLMs and models can be swapped by simply setting config. No code changes needed.
- **RAG with Strict Namespacing:**  
  - Each run isolates context by namespace, allowing segmented KBs by team, project, or customer.
- **Automated Ingestion with Safety:**  
  - Site crawling and KB rebuilds are disabled by default, require secrets to avoid accidental/hostile rebuilds.

---

## 7. Possible Improvements

1. **Typed Settings with Validation:**  
   - Employ [pydantic](https://docs.pydantic.dev/) or [dynaconf](https://www.dynaconf.com/) for type-safety, validation, and default schema for all configuration.
2. **Settings Reload/HMR:**  
   - Support for monitoring env changes and live reload (for long-running services).
3. **Secrets Management:**  
   - Integrate with Vault, AWS Secrets Manager, or Kubernetes secrets for even stronger key management, especially in production.
4. **Session Store Abstraction:**  
   - Allow modular DB backend (Postgres, cloud DBs) for scale beyond local SQLite.
5. **Modular LLM/Vector Store Drivers:**  
   - Allow plugin-style registry for additional LLM providers and vector DBs (Qdrant, Pinecone, etc.).
6. **Fine-Grained Logging/Tracing:**  
   - Improve debugability with structured logs and request tracing.
7. **Enhanced Testing of Settings:**  
   - Unit and integration tests to catch misconfigured or missing ENV vars at CI time.

---

For concrete field lists and configuration details, directly review `config/settings.py` (maintainer reference implementation). Further architectural evolutions are best driven by specific HR workflow and scale requirements.