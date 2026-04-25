import json
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.settings import get_settings
from graph.build import build_graph, run_agent
from graph.state import HireGraphState
from knowledge.pipeline import build_knowledge_base, get_knowledge_meta
from memory.session_memory import maybe_refresh_summary
from memory.store import get_session_store

app = FastAPI(title="HireGraph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    query: str
    user_id: str = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_placeholder():
    """Avoid noisy 404 in logs when Chrome DevTools probes this path."""
    return {}


@app.get("/api/info")
def api_info():
    return {
        "name": "HireGraph",
        "version": "1.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/api/knowledge/status")
def knowledge_status():
    return get_knowledge_meta()


@app.get("/api/observability/tokens")
def observability_tokens():
    """Rough character counts per LLM stage (chars_in / chars_out / calls)."""
    from observability.token_tracker import snapshot

    return snapshot()


@app.post("/api/knowledge/rebuild")
def knowledge_rebuild(x_rebuild_token: str | None = Header(None, alias="X-Rebuild-Token")):
    s = get_settings()
    if s.rebuild_secret:
        if not x_rebuild_token or x_rebuild_token != s.rebuild_secret:
            raise HTTPException(status_code=403, detail="Invalid or missing rebuild token")
    return build_knowledge_base()


@app.post("/ask/stream")
def ask_stream(req: AskRequest):
    user_id = req.user_id or str(uuid.uuid4())
    store = get_session_store()
    history = store.get_messages(user_id)
    summary = store.get_summary(user_id)

    def generate():
        graph = build_graph()
        initial_state: HireGraphState = {
            "query": req.query,
            "user_id": user_id,
            "conversation_history": history,
            "thoughts": [],
            "tool_observations": [],
            "iteration_count": 0,
            "answer": "",
            "confidence": 0.0,
            "sources": [],
            "critic_passed": False,
            "needs_retry": False,
            "final_response": {},
            "guardrail_blocked": False,
            "retrieved_chunks": [],
            "_next_action": "",
            "_action_input": "none",
            "intent": "",
            "intent_reason": "",
            "relaxed_critic": False,
            "memory_context": "",
            "session_summary": summary,
            "web_sources": [],
            "rag_call_count": 0,
        }

        from guardrails.input_guard import run_input_guardrails

        guard = run_input_guardrails(req.query)
        if not guard["allowed"]:
            data = json.dumps(
                {
                    "type": "final",
                    "result": {
                        "answer": guard["message"],
                        "sources": [],
                        "confidence": 1.0,
                        "thoughts": [],
                        "tool_calls": [],
                        "iterations": 0,
                        "blocked": True,
                    },
                    "user_id": user_id,
                }
            )
            yield f"data: {data}\n\n"
            return

        last_thought = None
        last_tool_snip = None
        for event in graph.stream(initial_state):
            for node_name, node_state in event.items():
                thoughts = node_state.get("thoughts", [])
                if thoughts:
                    t = thoughts[-1]
                    if t != last_thought:
                        last_thought = t
                        data = json.dumps({"type": "thought", "node": node_name, "content": t})
                        yield f"data: {data}\n\n"

                obs = node_state.get("tool_observations", [])
                if obs:
                    snip = obs[-1][:400] if obs[-1] else ""
                    if snip != last_tool_snip:
                        last_tool_snip = snip
                        data = json.dumps({"type": "tool", "node": node_name, "content": snip})
                        yield f"data: {data}\n\n"

                final = node_state.get("final_response", {})
                if final and final.get("answer"):
                    new_msgs = history + [
                        {"role": "user", "content": req.query},
                        {"role": "assistant", "content": final["answer"]},
                    ]
                    new_sum = maybe_refresh_summary(user_id, new_msgs, summary)
                    store.save_session(user_id, new_msgs, summary=new_sum)
                    data = json.dumps({"type": "final", "result": final, "user_id": user_id})
                    yield f"data: {data}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/ask")
def ask_sync(req: AskRequest):
    user_id = req.user_id or str(uuid.uuid4())
    store = get_session_store()
    history = store.get_messages(user_id)
    summary = store.get_summary(user_id)
    result = run_agent(
        req.query,
        user_id=user_id,
        conversation_history=history,
        session_summary=summary,
    )
    if result.get("answer") and not result.get("blocked"):
        new_msgs = history + [
            {"role": "user", "content": req.query},
            {"role": "assistant", "content": result["answer"]},
        ]
        new_sum = maybe_refresh_summary(user_id, new_msgs, summary)
        store.save_session(user_id, new_msgs, summary=new_sum)
    return {"result": result, "user_id": user_id}


@app.post("/ask/async")
async def ask_async(req: AskRequest):
    import asyncio

    user_id = req.user_id or str(uuid.uuid4())
    store = get_session_store()
    history = store.get_messages(user_id)
    summary = store.get_summary(user_id)

    result = await asyncio.to_thread(
        run_agent,
        req.query,
        user_id,
        history,
        summary,
    )
    if result.get("answer") and not result.get("blocked"):
        new_msgs = history + [
            {"role": "user", "content": req.query},
            {"role": "assistant", "content": result["answer"]},
        ]
        new_sum = maybe_refresh_summary(user_id, new_msgs, summary)
        store.save_session(user_id, new_msgs, summary=new_sum)
    return {"result": result, "user_id": user_id}


@app.get("/")
def root():
    return FileResponse("ui/index.html")


app.mount("/ui", StaticFiles(directory="ui"), name="ui")
