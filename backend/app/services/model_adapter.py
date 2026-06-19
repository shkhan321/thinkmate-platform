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


def generate_tutor_turn(settings: Settings, task_title: str, scenario: str, student_content: str, move: dict) -> str:
    if not settings.hf_api_token:
        return (
            f"{move['prompt']} In your answer, connect it to this task: "
            f"{task_title}."
        )

    prompt = _build_prompt(task_title, scenario, student_content, move)
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
