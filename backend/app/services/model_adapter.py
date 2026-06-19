import httpx

from app.config import Settings


def _build_prompt(task_title: str, scenario: str, student_content: str, move: dict) -> str:
    return (
        "You are ThinkMate, a Socratic tutor. Do not give direct answers. "
        "Ask one concise question only.\n\n"
        f"Task: {task_title}\n"
        f"Scenario: {scenario}\n"
        f"Target move: {move['move_type']}\n"
        f"Paul-Elder target: {move['paul_elder_target']}\n"
        f"Student response: {student_content}\n"
        "Tutor question:"
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


def generate_tutor_turn(settings: Settings, task_title: str, scenario: str, student_content: str, move: dict) -> str:
    prompt = _build_prompt(task_title, scenario, student_content, move)

    if settings.poe_api_key:
        return _generate_poe_turn(settings, prompt, move)

    if not settings.hf_api_token:
        return (
            f"{move['prompt']} In your answer, connect it to this task: "
            f"{task_title}."
        )

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
    except httpx.HTTPError:
        pass
    return f"{move['prompt']} What part of the scenario makes that reasoning stronger or weaker?"


def _generate_poe_turn(settings: Settings, prompt: str, move: dict) -> str:
    url = f"{settings.poe_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.poe_api_key}"}
    try:
        response = httpx.post(
            url,
            headers=headers,
            json={
                "model": settings.poe_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are ThinkMate, a Socratic tutor. Ask one concise question only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 80,
            },
            timeout=30,
        )
        response.raise_for_status()
        text = _extract_chat_completion_text(response.json()).strip()
        if text:
            return text
    except httpx.HTTPError:
        pass
    return f"{move['prompt']} What part of the scenario makes that reasoning stronger or weaker?"
