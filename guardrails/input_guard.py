import re

BLOCKED_PATTERNS = [
    r"ignore previous instructions",
    r"forget your instructions",
    r"reveal your system prompt",
    r"you are now",
    r"act as if",
    r"pretend you are",
    r"bypass",
    r"jailbreak",
]

VISHNESH_KEYWORDS = [
    "vishnesh", "he", "his",
    "experience", "project", "skill", "background",
    "work", "built", "developed", "education",
    "kafka", "node", "angular", "python", "react",
    "langgraph", "langchain", "docker", "aws",
    "kore", "zendesk", "github", "leetcode",
    "backend", "frontend", "agent", "rag",
    "intern", "developer", "engineer", "degree",
    "certification", "achievement",
    "tell me about", "explain",
]


def check_scope(query: str) -> dict:
    query_lower = query.lower()

    for keyword in VISHNESH_KEYWORDS:
        # Use word boundary for short words to avoid substring matches
        if len(keyword.split()) == 1 and len(keyword) <= 4:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, query_lower):
                return {"allowed": True, "redirect": False}
        else:
            if keyword in query_lower:
                return {"allowed": True, "redirect": False}

    return {
        "allowed": True,
        "redirect": True,
        "message": f"I'm focused on Vishnesh's experience. Let me answer this in that context: {query}"
    }
def check_prompt_injection(query: str) -> dict:
    query_lower = query.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, query_lower):
            return {
                "allowed": False,
                "reason": "prompt_injection",
                "message": "That type of instruction isn't something I can follow. Feel free to ask about Vishnesh's experience or skills."
            }
    return {"allowed": True}


def run_input_guardrails(query: str) -> dict:
    # Greetings: allow through — intent classifier + graph route them as casual (persona LLM path)
    # Step 1 — injection check
    injection_check = check_prompt_injection(query)
    if not injection_check["allowed"]:
        return injection_check

    # Step 2 — scope check (informational only — do NOT replace the user's words)
    scope_check = check_scope(query)

    return {
        "allowed": True,
        "redirect": scope_check.get("redirect", False),
        # Always pass the original query into the graph. Replacing it with a long
        # "let me answer in context" string pollutes history and causes hallucinations.
        "query": query,
    }
