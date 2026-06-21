import logging

import httpx

from app.config import Settings

logger = logging.getLogger("thinkmate.model")


SYSTEM_PROMPT = (
    "You are ThinkMate, a Socratic tutor for a university capstone student. Your job is to "
    "strengthen the student's OWN thinking about their OWN project by asking one good question "
    "at a time. Rules you must follow:\n"
    "- Never give the answer, never write or rewrite the student's work, and never say whether "
    "they are right or wrong.\n"
    "- Ask exactly ONE short question, in simple, clear English (one or two sentences).\n"
    "- Build on the whole conversation so far. Do not repeat a question they have already answered.\n"
    "- Tune the question to the student's level. If they seem stuck or ask you for the answer, "
    "break the problem into a smaller, easier step instead of giving it away.\n"
    "- Always anchor the question to the student's specific project and to what they just said."
)


def _build_prompt(
    task_title: str,
    scenario: str,
    student_content: str,
    move: dict,
    project_title: str = "",
    project_goal: str = "",
    history: str = "",
) -> str:
    project_block = ""
    if project_title or project_goal:
        project_block = (
            f"Student's project: {project_title or 'not given'}\n"
            f"What the student wants to do: {project_goal or 'not given'}\n"
        )
    history_block = f"Conversation so far:\n{history}\n\n" if history.strip() else ""
    return (
        "You are ThinkMate, a Socratic tutor. Do not give direct answers. "
        "Ask one short, simple question that pushes the student's reasoning.\n\n"
        f"{project_block}"
        f"Activity: {task_title}\n"
        f"How this activity helps: {scenario}\n"
        f"Target move: {move['move_type']}\n"
        f"Paul-Elder target: {move['paul_elder_target']}\n\n"
        f"{history_block}"
        f"Student just said: {student_content}\n"
        "Your one short question (build on the conversation, do not repeat earlier questions):"
    )


def _extract_hf_text(payload) -> str:
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return str(first.get("generated_text") or first.get("summary_text") or "")
    if isinstance(payload, dict):
        return str(payload.get("generated_text") or payload.get("summary_text") or payload.get("error") or "")
    return ""


def _extract_chat_completion_text(payload) -> str:
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if isinstance(message, dict):
        return str(message.get("content") or "")
    return ""


def active_model_mode(settings: Settings) -> str:
    if settings.poe_api_key:
        return "poe"
    if settings.hf_api_token:
        return "huggingface"
    return "demo"


def active_model_name(settings: Settings) -> str:
    if active_model_mode(settings) == "poe":
        return settings.poe_model
    return settings.hf_model


def generate_tutor_turn(
    settings: Settings,
    task_title: str,
    scenario: str,
    student_content: str,
    move: dict,
    project_title: str = "",
    project_goal: str = "",
    history: str = "",
) -> str:
    prompt = _build_prompt(task_title, scenario, student_content, move, project_title, project_goal, history)

    if settings.poe_api_key:
        return _generate_poe_turn(settings, prompt, move)

    if not settings.hf_api_token:
        anchor = project_title.strip() or task_title
        return f"{move['prompt']} Tie your answer to your project: {anchor}."

    url = f"https://api-inference.huggingface.co/models/{settings.hf_model}"
    headers = {"Authorization": f"Bearer {settings.hf_api_token}"}
    try:
        response = httpx.post(
            url,
            headers=headers,
            json={"inputs": prompt, "parameters": {"max_new_tokens": 80, "temperature": 0.3}},
            timeout=30,
        )
        response.raise_for_status()
        text = _extract_hf_text(response.json()).strip()
        if text:
            if "Tutor question:" in text:
                text = text.split("Tutor question:", 1)[-1].strip()
            return text
        logger.warning("HF model %s returned empty content; using fallback question.", settings.hf_model)
    except httpx.HTTPError as error:
        logger.warning("HF model %s call failed (%s); using fallback question.", settings.hf_model, error)
    return f"{move['prompt']} What part of the scenario makes that reasoning stronger or weaker?"


def _poe_chat(settings: Settings, system: str, user: str, max_tokens: int, temperature: float, attempts: int = 2) -> str:
    """Call Poe's OpenAI-compatible chat endpoint with a small retry, since Poe
    models occasionally time out or return transient 5xx. Returns the message
    text, or '' if every attempt fails or comes back empty."""
    url = f"{settings.poe_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.poe_api_key}"}
    payload = {
        "model": settings.poe_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    for attempt in range(1, attempts + 1):
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            text = _extract_chat_completion_text(response.json()).strip()
            if text:
                return text
            logger.warning(
                "Poe model %s returned empty content (attempt %s/%s).",
                settings.poe_model, attempt, attempts,
            )
        except httpx.HTTPError as error:
            logger.warning(
                "Poe model %s call failed (attempt %s/%s): %s",
                settings.poe_model, attempt, attempts, error,
            )
    return ""


def _generate_poe_turn(settings: Settings, prompt: str, move: dict) -> str:
    text = _poe_chat(settings, SYSTEM_PROMPT, prompt, max_tokens=80, temperature=0.3)
    if text:
        return text
    logger.warning("Poe tutor turn fell back for model %s. Check POE_MODEL is valid and active.", settings.poe_model)
    return f"{move['prompt']} What part of the scenario makes that reasoning stronger or weaker?"


HINT_SYSTEM_PROMPT = (
    "You help a stuck university student answer ThinkMate's question about THEIR OWN capstone project. "
    "Give ONE short example reply (max two sentences, simple English) that shows the kind of answer "
    "expected and gives them a way to start. It is a model to adapt, not a final answer. "
    "Do not add commentary, headings, or quotation marks."
)

HINT_FALLBACK = (
    "Start with one clear sentence about your project, then add one reason or example. "
    "For instance: “I chose this because …, and … supports it.” Then make it your own."
)


def generate_hint(
    settings: Settings,
    question: str,
    project_title: str = "",
    project_goal: str = "",
    last_student_message: str = "",
) -> str:
    """Produce a short example reply to model HOW to answer the current question,
    so a confused student can move forward. Never a finished answer; a starter to
    adapt. Falls back to a generic sentence starter if no model is available."""
    user_prompt = (
        f"Student's project: {project_title or 'not given'}\n"
        f"What they want to do: {project_goal or 'not given'}\n"
        f"ThinkMate just asked: {question}\n"
        f"What the student last said: {last_student_message or '(nothing yet)'}\n"
        "Write one short example answer the student could adapt:"
    )

    if settings.poe_api_key:
        text = _poe_chat(settings, HINT_SYSTEM_PROMPT, user_prompt, max_tokens=90, temperature=0.4)
        if text:
            return text
        logger.warning("Poe hint fell back for model %s.", settings.poe_model)

    return HINT_FALLBACK


SUMMARY_SYSTEM_PROMPT = (
    "You write a short 'thinking brief' from a student's OWN words in a Socratic dialogue about their "
    "capstone project, so they can reuse it in their report. Use ONLY what the student said — never add "
    "new facts, opinions, or answers. Write in simple English using exactly these three labelled lines:\n"
    "Your claim: <one sentence>\n"
    "Your strongest points: <one short line, or two separated by '; '>\n"
    "To strengthen next: <one short line on what is still open, based on the questions asked>\n"
    "Keep the whole thing under 90 words. No preamble."
)


def generate_session_summary(
    settings: Settings,
    project_title: str,
    project_goal: str,
    transcript: str,
) -> str:
    """A short brief of the student's OWN reasoning from a ThinkMate dialogue,
    something they can keep and paste into their capstone. Reflects what they
    said; never adds content. Falls back to a gentle prompt if no model."""
    user_prompt = (
        f"Student's project: {project_title or 'not given'}\n"
        f"What they want to do: {project_goal or 'not given'}\n\n"
        f"Dialogue (S = student, T = tutor):\n{transcript}\n\n"
        "Write the student's thinking brief now:"
    )
    if settings.poe_api_key and transcript.strip():
        text = _poe_chat(settings, SUMMARY_SYSTEM_PROMPT, user_prompt, max_tokens=180, temperature=0.3)
        if text:
            return text
        logger.warning("Poe summary fell back for model %s.", settings.poe_model)
    return (
        "We could not build your brief automatically this time. "
        "Look back at your messages above and note your main claim, your best reason, "
        "and the one question you still need to answer."
    )
