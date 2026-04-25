"""LangGraph node implementations."""

from __future__ import annotations

from groq import GroqError, RateLimitError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.intent_classifier import classify_intent
from agents.llm import get_llm
from agents.prompts import SYSTEM_PROMPT
from config.settings import get_settings
from graph.state import HireGraphState
from guardrails.input_guard import run_input_guardrails
from guardrails.output_guard import run_output_guardrails, tool_observations_ground
from memory.session_memory import format_memory_block
from observability.token_tracker import record as token_record
from tools.github_tool import github_get_language_summary, github_get_repo_details, github_get_repos
from tools.rag_tool import search_knowledge_base
from tools.web_agent import search_web
from utils.logging import get_logger

logger = get_logger(__name__)


def _groq_fallback_message(exc: GroqError) -> str:
    """User-facing text plus CONFIDENCE so critic does not force retries on API errors."""
    if isinstance(exc, RateLimitError):
        body = (
            "The AI service hit a rate limit (quota or tokens per day). "
            "Please wait and try again, or review your Groq plan at "
            "https://console.groq.com/settings/billing if this happens often."
        )
    else:
        body = "The AI service returned an error. Please try again in a moment."
    logger.warning("llm groq error stage will use fallback: %s", exc)
    return f"{body}\n\nCONFIDENCE: 0.85"


def _invoke_tracked(llm, messages: list, stage: str):
    cin = sum(len(getattr(m, "content", "") or "") for m in messages)
    try:
        response = llm.invoke(messages)
    except GroqError as exc:
        return AIMessage(content=_groq_fallback_message(exc))
    cout = len((response.content or ""))
    token_record(stage, cin, cout)
    return response


def input_guard_node(state: HireGraphState) -> HireGraphState:
    logger.info("input_guard: query=%s...", state["query"][:60])
    result = run_input_guardrails(state["query"])

    if not result["allowed"]:
        return {
            **state,
            "guardrail_blocked": True,
            "final_response": {
                "answer": result["message"],
                "sources": [],
                "confidence": 0.0,
                "thoughts": [],
                "tool_calls": [],
                "iterations": 0,
                "blocked": True,
            },
        }

    return {
        **state,
        "query": result["query"],
        "guardrail_blocked": False,
    }


def classify_intent_node(state: HireGraphState) -> HireGraphState:
    intent, reason = classify_intent(state["query"])
    relaxed = intent == "casual"
    logger.info("intent=%s (%s) relaxed_critic=%s", intent, reason, relaxed)
    return {
        **state,
        "intent": intent,
        "intent_reason": reason,
        "relaxed_critic": relaxed,
        "thoughts": [f"Intent: {intent} ({reason})"],
    }


def memory_inject_node(state: HireGraphState) -> HireGraphState:
    """Build a single memory block: profile + summary + recent turns."""
    block = format_memory_block(
        conversation_history=list(state.get("conversation_history") or []),
        session_summary=state.get("session_summary") or "",
    )
    logger.info("memory_inject: context_chars=%s", len(block))
    return {
        **state,
        "memory_context": block,
    }


def supervisor_node(state: HireGraphState) -> HireGraphState:
    if state.get("guardrail_blocked"):
        return state

    llm = get_llm()
    iteration = state.get("iteration_count", 0)
    observations = state.get("tool_observations", [])
    intent = state.get("intent", "mixed")
    intent_reason = state.get("intent_reason", "")
    mem = state.get("memory_context", "")

    logger.info("supervisor iteration=%s intent=%s", iteration + 1, intent)

    obs_context = ""
    if observations:
        obs_context = "\n\nPrevious observations:\n" + "\n".join(f"- {o}" for o in observations[-3:])

    conv_context = ""
    history = state.get("conversation_history", [])
    if history:
        recent = history[-4:]
        conv_context = "\n\nConversation history:\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in recent
        )

    intent_hint = f"\nIntent classifier: {intent} ({intent_hint_text(intent)})."
    mem_block = f"\n\nSession & profile context (use for grounding when relevant):\n{mem[:6000]}\n"

    rc = int(state.get("rag_call_count") or 0)
    chunks = state.get("retrieved_chunks") or []
    rag_hint = ""
    if chunks:
        rag_hint = "\nIMPORTANT: Retrieved chunks are already in context below. You MUST choose ACTION: answer (not search_rag).\n"
    elif rc >= 1:
        rag_hint = "\nIMPORTANT: search_rag was already attempted. Do NOT choose search_rag again unless the previous attempt returned no usable text; prefer ACTION: answer.\n"

    prompt = f"""You are reasoning about how to answer this question about Vishnesh Vojjala.

Question: {state['query']}
{intent_hint}
Classifier note: {intent_reason}
{rag_hint}
{mem_block}
{obs_context}
{conv_context}

Decide your next action.

RULES:
- Greetings, casual messages, or simple questions → ACTION: answer immediately, no tools needed
- Questions about Vishnesh skills/projects/experience → use search_rag once if you have no observations yet
- Questions about GitHub repos/languages → use github_repos or github_languages
- Need fresh/world facts not in resume (news, current events, etc.) → web_search
- If previous observations already contain RAG or GitHub text sufficient to answer → ACTION: answer, do NOT call the same tool again

Available tools:
1. search_rag — search resume, projects, skills knowledge base
2. github_repos — get list of GitHub repositories
3. github_details — get details of a specific repo (provide repo_name)
4. github_languages — get programming language summary from GitHub
5. web_search — search the public web for recent or external facts (input: search query)
6. answer — use when you have enough info OR for simple/casual queries

Respond in this exact format:
THOUGHT: <your reasoning>
ACTION: <tool_name>
INPUT: <tool input or 'none'>"""

    response = _invoke_tracked(
        llm,
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)],
        "supervisor",
    )
    response_text = response.content
    logger.debug("supervisor raw: %s", response_text[:300])

    thought = ""
    action = "answer"
    action_input = "none"

    for line in response_text.split("\n"):
        if line.startswith("THOUGHT:"):
            thought = line.replace("THOUGHT:", "").strip()
        elif line.startswith("ACTION:"):
            action = line.replace("ACTION:", "").strip().lower()
        elif line.startswith("INPUT:"):
            action_input = line.replace("INPUT:", "").strip()

    return {
        **state,
        "thoughts": [f"Iteration {iteration + 1}: {thought}"],
        "iteration_count": iteration + 1,
        "_next_action": action,
        "_action_input": action_input,
    }


def intent_hint_text(intent: str) -> str:
    if intent == "resume":
        return "prefer search_rag for grounded facts"
    if intent == "github":
        return "prefer GitHub tools when relevant"
    if intent == "web":
        return "consider web_search for fresh/external facts"
    return "use best judgment"


def tool_executor_node(state: HireGraphState) -> HireGraphState:
    action = state.get("_next_action", "answer")
    action_input = state.get("_action_input", "none")

    logger.info("tool_executor: %s", action)

    observation = ""
    chunks = list(state.get("retrieved_chunks") or [])
    web_sources = list(state.get("web_sources") or [])
    rag_call_count = int(state.get("rag_call_count") or 0)

    if action == "search_rag":
        rag_call_count += 1
        search_query = action_input if action_input and action_input != "none" else state["query"]
        result = search_knowledge_base(search_query)
        if result["success"]:
            chunks = result["chunks"]
            observation = f"RAG retrieved {len(chunks)} chunks from {result['sources']}:\n"
            observation += "\n".join(f"  [{c['source']}] {c['content'][:200]}" for c in chunks[:3])
        else:
            observation = f"RAG search failed: {result['error']}"

    elif action == "github_repos":
        result = github_get_repos()
        if result["success"]:
            observation = f"GitHub repos ({result['total_repos']} total):\n"
            repo_lines = [
                f"  - {r['name']} ({r['language']}) updated {r['updated']}" for r in result["repos"][:5]
            ]
            observation += "\n".join(repo_lines)
        else:
            observation = f"GitHub API failed: {result['error']}"

    elif action == "github_details":
        repo_name = action_input if action_input != "none" else ""
        if repo_name:
            result = github_get_repo_details(repo_name)
            if result["success"]:
                observation = f"Repo {result['name']}: {result['description']}\n"
                observation += f"Languages: {result['languages']}\n"
                observation += f"README: {result['readme_preview'][:300]}"
            else:
                observation = f"Repo details failed: {result['error']}"
        else:
            observation = "No repo name provided"

    elif action == "github_languages":
        result = github_get_language_summary()
        if result["success"]:
            observation = "GitHub language summary:\n"
            observation += "\n".join(f"  {l['language']}: {l['bytes']} bytes" for l in result["languages"])
        else:
            observation = f"Language summary failed: {result['error']}"

    elif action == "web_search":
        q = action_input if action_input and action_input != "none" else state["query"]
        result = search_web(q)
        if result["success"]:
            observation = f"Web search results:\n{result['snippets']}"
            web_sources = [f"web:{s.get('title', '?')[:80]}" for s in result.get("sources") or []]
        else:
            observation = f"Web search failed: {result['error']}"

    else:
        observation = "No tool called — proceeding to answer"

    return {
        **state,
        "tool_observations": [observation],
        "retrieved_chunks": chunks,
        "web_sources": web_sources,
        "rag_call_count": rag_call_count,
    }


def answer_node(state: HireGraphState) -> HireGraphState:
    logger.info("answer_gen")
    llm = get_llm()

    observations = state.get("tool_observations", [])
    obs_text = "\n\n".join(observations) if observations else "No tool data retrieved"

    conv_history = state.get("conversation_history", [])
    conv_text = ""
    if conv_history:
        conv_text = "\n\nConversation context:\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in conv_history[-4:]
        )

    mem = state.get("memory_context", "")

    prompt = f"""Based on the retrieved information (if any), answer this question.

Question: {state['query']}

Memory / profile context (structured snapshot — may omit details; do not invent missing facts):
{mem[:4000]}

Retrieved Information:
{obs_text}
{conv_text}

Hard rules:
- Do NOT make up the interviewer's name or any personal fact about them. If they ask "what is my name?" and it is not explicitly in Recent dialogue as their own name, say you don't know their name and you only have Vishnesh's public materials.
- Vishnesh-specific claims must match the retrieved text; otherwise say the knowledge base doesn't contain that.
- Keep answers concise.

Provide a clear, professional answer. Mention which sources you used when applicable (resume, GitHub, web).
For web results, say they came from web search; do not label them as Vishnesh's resume.
End with: CONFIDENCE: <0.0-1.0>"""

    response = _invoke_tracked(
        llm,
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)],
        "answer_gen",
    )
    response_text = response.content

    confidence = 0.8
    lines = response_text.strip().split("\n")
    answer_lines = []
    for line in lines:
        if line.startswith("CONFIDENCE:"):
            try:
                confidence = float(line.replace("CONFIDENCE:", "").strip())
            except Exception:
                confidence = 0.8
        else:
            answer_lines.append(line)

    answer = "\n".join(answer_lines).strip()
    rag_sources = list({c["source"] for c in state.get("retrieved_chunks", [])})
    web_src = state.get("web_sources") or []
    sources = rag_sources + [w for w in web_src if w not in rag_sources]

    return {
        **state,
        "answer": answer,
        "confidence": confidence,
        "sources": sources,
    }


def critic_node(state: HireGraphState) -> HireGraphState:
    logger.info("critic")
    answer = state.get("answer", "")
    chunks = state.get("retrieved_chunks", [])
    confidence = state.get("confidence", 0.0)
    relaxed = state.get("relaxed_critic", False)
    obs = state.get("tool_observations", [])
    has_ground = tool_observations_ground(list(obs))

    result = run_output_guardrails(
        answer,
        chunks,
        confidence,
        relaxed=relaxed,
        has_tool_grounding=has_ground,
    )

    settings = get_settings()
    max_iter = settings.max_supervisor_iterations

    if not result["passed"]:
        logger.warning("critic failed: %s", result.get("reason"))
        if state.get("iteration_count", 0) >= max_iter:
            return {
                **state,
                "critic_passed": False,
                "needs_retry": False,
                "final_response": {
                    "answer": state.get(
                        "answer", "I could not find enough information to answer confidently."
                    ),
                    "sources": state.get("sources", []),
                    "confidence": state.get("confidence", 0.0),
                    "thoughts": state.get("thoughts", []),
                    "tool_calls": state.get("tool_observations", []),
                    "iterations": state.get("iteration_count", 0),
                    "blocked": False,
                },
            }
        return {
            **state,
            "critic_passed": False,
            "needs_retry": True,
        }

    thoughts = list(dict.fromkeys(state.get("thoughts", [])))
    tool_obs = state.get("tool_observations", [])

    final_response = {
        "answer": result["answer"],
        "sources": state.get("sources", []),
        "confidence": state.get("confidence", 0.0),
        "thoughts": thoughts,
        "tool_calls": tool_obs,
        "iterations": state.get("iteration_count", 0),
        "blocked": False,
    }

    return {
        **state,
        "critic_passed": True,
        "needs_retry": False,
        "final_response": final_response,
    }
