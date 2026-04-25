def check_hallucination(
    answer: str,
    retrieved_chunks: list[dict],
    relaxed: bool,
    has_tool_grounding: bool,
) -> dict:
    if relaxed:
        if len(answer.strip()) < 5:
            return {"passed": False, "reason": "empty_answer", "message": "Answer too short."}
        return {"passed": True}

    if has_tool_grounding:
        if len(answer.strip()) < 15:
            return {"passed": False, "reason": "empty_answer", "message": "Answer too short."}
        return {"passed": True}

    if not retrieved_chunks:
        return {
            "passed": False,
            "reason": "no_sources",
            "message": "I don't have enough information in my knowledge base to answer that confidently.",
        }

    if len(answer.strip()) < 20:
        return {
            "passed": False,
            "reason": "empty_answer",
            "message": "The answer generated was too short or empty.",
        }

    return {"passed": True}


def check_confidence(confidence: float, relaxed: bool) -> dict:
    if relaxed and confidence < 0.3:
        return {"passed": False, "reason": "low_confidence", "message": "Confidence too low."}
    if not relaxed and confidence < 0.5:
        return {
            "passed": False,
            "reason": "low_confidence",
            "message": "Confidence too low to return this answer reliably.",
        }
    return {"passed": True, "reason": ""}


def enforce_professional_tone(answer: str) -> str:
    blocked_phrases = [
        "as an ai language model",
        "i cannot",
        "i am not able to",
        "my training data",
        "as instructed",
    ]
    answer_lower = answer.lower()
    for phrase in blocked_phrases:
        if phrase in answer_lower:
            answer = answer.replace(phrase, "")

    return answer.strip()


def run_output_guardrails(
    answer: str,
    retrieved_chunks: list[dict],
    confidence: float,
    *,
    relaxed: bool = False,
    has_tool_grounding: bool = False,
) -> dict:
    """
    relaxed=True: skip requirement for retrieved chunks (casual paths).
    has_tool_grounding=True: RAG chunks optional if tools provided external text (web/GitHub/RAG retrieval text).
    """
    hallucination_check = check_hallucination(
        answer, retrieved_chunks, relaxed, has_tool_grounding
    )
    if not hallucination_check["passed"]:
        return hallucination_check

    confidence_check = check_confidence(confidence, relaxed)
    if not confidence_check["passed"]:
        return confidence_check

    clean_answer = enforce_professional_tone(answer)

    return {"passed": True, "answer": clean_answer}


def tool_observations_ground(observations: list[str]) -> bool:
    for o in observations:
        t = (o or "").strip()
        if len(t) < 45:
            continue
        if t.startswith("No tool called"):
            continue
        return True
    return False
