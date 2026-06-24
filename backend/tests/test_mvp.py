import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.model_adapter import generate_tutor_turn
from app.services.routing import condition_for
from app.services.safeguard import apply_safeguard


def test_settings_ignore_frontend_only_env_keys(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("VITE_API_URL=http://localhost:8000\nADMIN_PASSWORD=admin-test\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.admin_password == "admin-test"


def make_client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'thinkmate_test.db'}",
        admin_password="admin-test",
        app_env="test",
        hf_api_token="",
        poe_api_key="",
        consent_version="test-consent-v1",
    )
    return TestClient(create_app(settings))


def _db_sequence(tmp_path, student_id):
    """Read a student's assigned A/B sequence straight from the database.
    The sequence is intentionally NOT exposed in student-facing API responses
    (it is randomisation metadata), so tests verify it server-side."""
    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{tmp_path / 'thinkmate_test.db'}")
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT sequence FROM students WHERE id = :id"), {"id": student_id}
            ).fetchone()
    finally:
        engine.dispose()
    return row[0] if row else None


def test_health_reports_demo_mode(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["model_mode"] == "demo"
    assert payload["database"] == "ok"


def test_health_reports_poe_mode_when_poe_key_is_configured(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'thinkmate_test.db'}",
        admin_password="admin-test",
        app_env="test",
        poe_api_key="test-poe-key",
        poe_model="GPT-4o-Mini",
    )
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_mode"] == "poe"
    assert payload["model_name"] == "GPT-4o-Mini"


def test_poe_adapter_uses_openai_compatible_chat_endpoint(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "What evidence would change your view?"}}]}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.services.model_adapter.httpx.post", fake_post)
    settings = Settings(poe_api_key="test-poe-key", poe_model="GPT-4o-Mini")

    text = generate_tutor_turn(
        settings,
        task_title="Wing Design Trade-Off",
        scenario="Choose between lighter and safer design.",
        student_content="Lighter is always better.",
        move={
            "move_type": "evidence",
            "paul_elder_target": "evidence",
            "prompt": "What evidence supports that claim?",
        },
    )

    assert text == "What evidence would change your view?"
    assert captured["url"] == "https://api.poe.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-poe-key"
    assert captured["json"]["model"] == "GPT-4o-Mini"
    assert captured["json"]["messages"][0]["role"] == "system"


def test_crossover_condition_routing():
    assert condition_for("A", 1) == "thinkmate"
    assert condition_for("A", 2) == "worksheet"
    assert condition_for("B", 1) == "worksheet"
    assert condition_for("B", 2) == "thinkmate"


def test_pilot_access_codes_can_be_seeded_without_demo_codes(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'thinkmate_test.db'}",
        admin_password="admin-test",
        app_env="test",
        hf_api_token="",
        consent_version="test-consent-v1",
        seed_demo_students=False,
        pilot_access_codes="ENG-A-099:engineering:A;PSY-B-099:psychology:B",
    )
    client = TestClient(create_app(settings))

    demo_login = client.post("/api/auth/access-code", json={"access_code": "ENG-DEMO-1"})
    assert demo_login.status_code == 404

    pilot_login = client.post("/api/auth/access-code", json={"access_code": "ENG-A-099"})
    assert pilot_login.status_code == 200
    assert pilot_login.json()["course"] == "engineering"
    assert _db_sequence(tmp_path, pilot_login.json()["student_id"]) == "A"


def test_name_login_creates_pseudonymous_student(tmp_path):
    client = make_client(tmp_path)

    response = client.post("/api/auth/start", json={"name": "Aisha Khalifa", "course": "engineering"})

    assert response.status_code == 200
    student = response.json()
    assert student["display_name"] == "Aisha Khalifa"
    assert student["course"] == "engineering"
    assert _db_sequence(tmp_path, student["student_id"]) in {"A", "B"}
    assert student["consent_accepted"] is False
    assert student["returning"] is False
    # Pseudonymous study ID is generated, not the name.
    assert student["access_code"].startswith("ENG-")
    assert "Aisha" not in student["access_code"]


def test_name_login_resumes_existing_student(tmp_path):
    client = make_client(tmp_path)

    first = client.post("/api/auth/start", json={"name": "  Omar  Said ", "course": "psychology"}).json()
    # Different spacing/case must resolve to the same student.
    second = client.post("/api/auth/start", json={"name": "omar said", "course": "psychology"}).json()

    assert second["student_id"] == first["student_id"]
    assert second["access_code"] == first["access_code"]
    assert _db_sequence(tmp_path, second["student_id"]) == _db_sequence(tmp_path, first["student_id"])
    assert second["returning"] is True
    assert first["access_code"].startswith("PSY-")


def test_name_login_requires_name_and_valid_course(tmp_path):
    client = make_client(tmp_path)

    assert client.post("/api/auth/start", json={"name": "   ", "course": "engineering"}).status_code == 422
    assert client.post("/api/auth/start", json={"name": "Sara", "course": "biology"}).status_code == 422


def test_name_login_balances_crossover_sequences(tmp_path):
    client = make_client(tmp_path)

    student_ids = [
        client.post("/api/auth/start", json={"name": f"Student {index}", "course": "engineering"}).json()["student_id"]
        for index in range(10)
    ]
    sequences = [_db_sequence(tmp_path, sid) for sid in student_ids]

    # Balanced randomisation keeps the two arms even across an even cohort.
    assert sequences.count("A") == 5
    assert sequences.count("B") == 5


def test_name_login_flows_through_consent_and_tasks(tmp_path):
    client = make_client(tmp_path)

    student = client.post("/api/auth/start", json={"name": "Mariam", "course": "engineering"}).json()
    student_id = student["student_id"]

    blocked = client.get("/api/tasks", params={"student_id": student_id})
    assert blocked.status_code == 403

    client.post("/api/consent", json={"student_id": student_id, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": student_id}).json()["tasks"]
    assert [task["task_number"] for task in tasks] == [1, 2]
    assert all(task["completed"] is False for task in tasks)

    # Completing a session is reflected in the task list.
    session = client.post("/api/sessions", json={"student_id": student_id, "task_id": tasks[0]["id"]}).json()
    client.post(f"/api/sessions/{session['id']}/complete")
    refreshed = client.get("/api/tasks", params={"student_id": student_id}).json()["tasks"]
    assert refreshed[0]["completed"] is True
    assert refreshed[1]["completed"] is False


def test_name_is_exported_but_hidden_when_blinded(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Hessa Noor", "course": "psychology"}).json()
    client.post("/api/consent", json={"student_id": student["student_id"], "accepted": True})

    full = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "false"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    names = {row.get("display_name") for row in full["students"]}
    assert "Hessa Noor" in names

    blinded = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "true"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    for row in blinded["students"]:
        assert "display_name" not in row
        assert "access_code" not in row
        assert "sequence" not in row


def test_project_intake_saves_and_grounds_tutor(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Layla", "course": "engineering"}).json()
    sid = student["student_id"]
    client.post("/api/consent", json={"student_id": sid, "accepted": True})

    saved = client.post(
        "/api/project",
        json={
            "student_id": sid,
            "project_title": "Solar-powered irrigation drone",
            "project_goal": "decide between two battery layouts",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["project_title"] == "Solar-powered irrigation drone"

    # Project comes back on the next sign in so intake can be skipped.
    again = client.post("/api/auth/start", json={"name": "Layla", "course": "engineering"}).json()
    assert again["project_title"] == "Solar-powered irrigation drone"
    assert again["project_goal"] == "decide between two battery layouts"


def test_project_requires_title_and_goal(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Noor", "course": "psychology"}).json()["student_id"]
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    assert client.post("/api/project", json={"student_id": sid, "project_title": "  ", "project_goal": "x"}).status_code == 422
    assert client.post("/api/project", json={"student_id": sid, "project_title": "x", "project_goal": "  "}).status_code == 422


def test_tutor_prompt_is_anchored_to_student_project():
    from app.services.model_adapter import _build_prompt

    prompt = _build_prompt(
        task_title="Justify a key decision in your project",
        scenario="Defend a choice.",
        student_content="I will use lithium cells.",
        move={"move_type": "evidence_probe", "paul_elder_target": "accuracy", "prompt": "What evidence?"},
        project_title="Solar irrigation drone",
        project_goal="choose a battery layout",
    )
    assert "Solar irrigation drone" in prompt
    assert "choose a battery layout" in prompt


def test_tutor_prompt_includes_conversation_history():
    from app.services.model_adapter import _build_prompt

    prompt = _build_prompt(
        task_title="Stress-test your project",
        scenario="Look for weak spots.",
        student_content="I think nylon is strong enough.",
        move={"move_type": "evidence_probe", "paul_elder_target": "accuracy", "prompt": "What evidence?"},
        project_title="Foldable drone arm",
        project_goal="pick a material",
        history="Student: I will use nylon.\nThinkMate: Why nylon over PLA?",
    )
    assert "Conversation so far" in prompt
    assert "Why nylon over PLA?" in prompt


def test_seed_tasks_are_project_agnostic(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Yousef", "course": "engineering"}).json()["student_id"]
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    titles = [t["title"] for t in client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]]
    assert titles == ["Justify a key decision in your project", "Stress-test your project"]


def test_project_is_exported_but_hidden_when_blinded(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Fatima", "course": "engineering"}).json()
    client.post("/api/consent", json={"student_id": student["student_id"], "accepted": True})
    client.post(
        "/api/project",
        json={"student_id": student["student_id"], "project_title": "Recycled composite panel", "project_goal": "test stiffness"},
    )

    full = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "false"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    assert any(s.get("project_title") == "Recycled composite panel" for s in full["students"])

    blinded = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "true"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    for row in blinded["students"]:
        assert "project_title" not in row
        assert "project_goal" not in row


def test_dialogue_hint_returns_a_starter(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Huda", "course": "engineering"}).json()
    sid = student["student_id"]
    client.post(
        "/api/project",
        json={"student_id": sid, "project_title": "Quiet drone propeller", "project_goal": "lower the noise"},
    )
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]
    client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "I will use a five-blade propeller."})

    hint = client.post("/api/dialogue/hint", json={"session_id": session_id})
    assert hint.status_code == 200
    assert len(hint.json()["hint"].strip()) > 0


def test_worksheet_steps_include_examples(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Rashid", "course": "engineering"}).json()["student_id"]
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    steps = tasks[0]["worksheet_steps"]
    assert all(step.get("example") for step in steps)


def test_thinkmate_session_summary_is_ai_kind(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Salim", "course": "engineering"}).json()
    sid = student["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "Quiet drone", "project_goal": "cut noise"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]
    client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "I will use five-blade props to cut noise."})
    client.post(f"/api/sessions/{session_id}/complete")

    summary = client.get(f"/api/sessions/{session_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["kind"] == "ai"
    assert len(summary.json()["summary"].strip()) > 0


def test_worksheet_session_summary_is_plain_recap_no_ai(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Dana", "course": "psychology"}).json()
    sid = student["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "Sleep study", "project_goal": "pick a method"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    ws = next(t for t in tasks if t["condition"] == "worksheet")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": ws["id"]}).json()["id"]
    client.post(
        "/api/worksheet/response",
        json={"session_id": session_id, "step_key": "claim", "prompt": "State your claim.", "response": "A diary study fits best."},
    )

    summary = client.get(f"/api/sessions/{session_id}/summary")
    assert summary.status_code == 200
    # The worksheet recap must be a plain echo of the student's own answer (no AI),
    # so the non-AI control condition stays uncontaminated.
    assert summary.json()["kind"] == "plain"
    assert "A diary study fits best." in summary.json()["summary"]


def test_student_final_answer_is_saved_and_returned_and_exported(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Tariq", "course": "engineering"}).json()
    sid = student["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "Quiet drone", "project_goal": "cut noise"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]
    client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "Five-blade props cut noise."})

    answer = client.post(
        f"/api/sessions/{session_id}/answer",
        json={"answer": "My answer: a five-blade propeller is the best trade-off for noise and thrust."},
    )
    assert answer.status_code == 200
    assert "five-blade" in answer.json()["final_answer"]

    # Empty answer is rejected so the student writes something or skips on the client.
    assert client.post(f"/api/sessions/{session_id}/answer", json={"answer": "   "}).status_code == 422

    summary = client.get(f"/api/sessions/{session_id}/summary").json()
    assert summary["final_answer"] and "five-blade" in summary["final_answer"]

    export = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "false"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    assert any("five-blade" in (s.get("final_answer") or "") for s in export["sessions"])


def test_scenario_text_is_condition_neutral(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Reem", "course": "engineering"}).json()["student_id"]
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    # A task can be delivered as either condition, so its scenario must not promise ThinkMate.
    for task in tasks:
        assert "ThinkMate" not in task["scenario"]


def test_session_is_reused_and_state_resumes(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Bilal", "course": "engineering"}).json()
    sid = student["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "Quiet drone", "project_goal": "cut noise"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")

    first = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()
    client.post("/api/dialogue/turn", json={"session_id": first["id"], "content": "Five blades cut noise."})

    # Starting the same task again returns the SAME session (no duplicate, no lost work).
    again = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()
    assert again["id"] == first["id"]

    state = client.get(f"/api/sessions/{first['id']}/state").json()
    assert state["condition"] == "thinkmate"
    assert len(state["turns"]) == 2  # student + tutor
    assert any("Five blades" in t["content"] for t in state["turns"])

    # The task now reports as in progress so the card can say "Continue".
    refreshed = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm_now = next(t for t in refreshed if t["id"] == tm["id"])
    assert tm_now["in_progress"] is True
    assert tm_now["completed"] is False


def test_worksheet_state_resumes(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Mona", "course": "psychology"}).json()
    sid = student["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "Sleep study", "project_goal": "pick a method"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    ws = next(t for t in tasks if t["condition"] == "worksheet")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": ws["id"]}).json()["id"]
    client.post(
        "/api/worksheet/response",
        json={"session_id": session_id, "step_key": "claim", "prompt": "State your claim.", "response": "Diary study."},
    )

    state = client.get(f"/api/sessions/{session_id}/state").json()
    assert len(state["worksheet_responses"]) == 1
    assert state["worksheet_responses"][0]["response"] == "Diary study."


def test_feedback_is_saved_validated_and_exported(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Hala", "course": "engineering"}).json()
    sid = student["student_id"]
    client.post("/api/consent", json={"student_id": sid, "accepted": True})

    ok = client.post("/api/feedback", json={"student_id": sid, "rating": 5, "comment": "Made me think harder."})
    assert ok.status_code == 200
    assert ok.json()["rating"] == 5

    # Rating is bounded.
    assert client.post("/api/feedback", json={"student_id": sid, "rating": 9}).status_code == 422
    assert client.post("/api/feedback", json={"student_id": sid, "rating": 0}).status_code == 422

    full = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "false"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    assert any(f["rating"] == 5 and f["comment"] == "Made me think harder." for f in full["feedback"])

    blinded = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "true"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    # Ratings still export when blinded, but free-text comments are withheld.
    assert any(f["rating"] == 5 for f in blinded["feedback"])
    assert all(f["comment"] is None for f in blinded["feedback"])


def test_worksheet_session_cannot_get_ai_hint(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Adib", "course": "engineering"}).json()["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    ws = next(t for t in tasks if t["condition"] == "worksheet")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": ws["id"]}).json()["id"]
    # The non-AI control must never reach the model, even via /dialogue/hint.
    assert client.post("/api/dialogue/hint", json={"session_id": session_id}).status_code == 400


def test_completed_session_is_read_only(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Wael", "course": "engineering"}).json()["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]
    client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "A claim."})
    client.post(f"/api/sessions/{session_id}/complete")

    # After completion the artifact is locked.
    assert client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "more"}).status_code == 409
    assert client.post(f"/api/sessions/{session_id}/answer", json={"answer": "x"}).status_code == 409


def test_worksheet_response_upserts_no_duplicates(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Huda2", "course": "psychology"}).json()["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    ws = next(t for t in tasks if t["condition"] == "worksheet")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": ws["id"]}).json()["id"]
    client.post("/api/worksheet/response", json={"session_id": session_id, "step_key": "claim", "prompt": "P", "response": "first"})
    client.post("/api/worksheet/response", json={"session_id": session_id, "step_key": "claim", "prompt": "P", "response": "second"})

    rows = client.get(f"/api/sessions/{session_id}/state").json()["worksheet_responses"]
    claim_rows = [r for r in rows if r["step_key"] == "claim"]
    assert len(claim_rows) == 1
    assert claim_rows[0]["response"] == "second"


def test_blinded_export_does_not_leak_condition(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Lina", "course": "engineering"}).json()["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "Secret project", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]
    client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "My reasoning here."})

    blinded = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "true"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    # No condition tells: no turns table, no move metadata, no condition field.
    assert "turns" not in blinded
    assert "scoring_artifacts" in blinded
    blob = json.dumps(blinded)
    assert "thinkmate" not in blob and "worksheet" not in blob
    assert "move_type" not in blob and "paul_elder" not in blob
    # The student's reasoning is present for scoring.
    assert any("My reasoning here." in a["reasoning"] for a in blinded["scoring_artifacts"])
    # Per-artifact (not per-student) key, so even one student's single artifact
    # carries an independent key and the cohort list cannot be joined to it.
    assert all(a["key"].startswith("A") for a in blinded["scoring_artifacts"])
    assert all("key" not in row for row in blinded["students"])


def test_blinded_artifacts_cannot_be_paired_to_a_participant(tmp_path):
    client = make_client(tmp_path)

    # Two students, each producing BOTH a ThinkMate and a worksheet artifact.
    for name in ("Aliyah", "Bushra"):
        student = client.post("/api/auth/start", json={"name": name, "course": "engineering"}).json()
        sid = student["student_id"]
        client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
        client.post("/api/consent", json={"student_id": sid, "accepted": True})
        tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
        tm = next(t for t in tasks if t["condition"] == "thinkmate")
        ws = next(t for t in tasks if t["condition"] == "worksheet")
        tm_session = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]
        client.post("/api/dialogue/turn", json={"session_id": tm_session, "content": f"{name} chat reasoning."})
        ws_session = client.post("/api/sessions", json={"student_id": sid, "task_id": ws["id"]}).json()["id"]
        client.post(
            "/api/worksheet/response",
            json={"session_id": ws_session, "step_key": "claim", "prompt": "P", "response": f"{name} worksheet answer."},
        )

    blinded = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "true"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()

    artifacts = blinded["scoring_artifacts"]
    keys = [a["key"] for a in artifacts]
    # One independent key per artifact: 2 students x 2 artifacts = 4 distinct keys.
    assert len(artifacts) == 4
    assert len(set(keys)) == 4
    # No key is shared between two artifacts, so a participant's two artifacts
    # cannot be linked, and the cohort list exposes no joinable key.
    assert all("key" not in row for row in blinded["students"])
    assert "engineering" in {row["course"] for row in blinded["students"]}


def test_production_rejects_demo_seeding(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'p.db'}",
        admin_password="strong-pass",
        app_env="production",
        seed_demo_students=True,
    )
    with pytest.raises(RuntimeError, match="SEED_DEMO_STUDENTS"):
        create_app(settings)


def test_production_rejects_default_admin_password(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'thinkmate_test.db'}",
        admin_password="change-me",
        app_env="production",
        hf_api_token="",
    )

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        create_app(settings)


def test_access_code_consent_and_session_routing(tmp_path):
    client = make_client(tmp_path)

    login = client.post("/api/auth/access-code", json={"access_code": "ENG-DEMO-1"})
    assert login.status_code == 200
    student = login.json()
    assert student["course"] == "engineering"
    assert _db_sequence(tmp_path, student["student_id"]) == "A"
    # The access code itself must not encode the crossover sequence.
    assert "-A-" not in student["access_code"] and "-B-" not in student["access_code"]
    assert student["consent_accepted"] is False

    blocked = client.get("/api/tasks", params={"student_id": student["student_id"]})
    assert blocked.status_code == 403

    consent = client.post(
        "/api/consent",
        json={"student_id": student["student_id"], "accepted": True},
    )
    assert consent.status_code == 200
    assert consent.json()["accepted"] is True

    tasks = client.get("/api/tasks", params={"student_id": student["student_id"]})
    assert tasks.status_code == 200
    task_payload = tasks.json()["tasks"]
    assert [task["task_number"] for task in task_payload] == [1, 2]
    assert task_payload[0]["condition"] == "thinkmate"
    assert task_payload[1]["condition"] == "worksheet"

    session = client.post(
        "/api/sessions",
        json={"student_id": student["student_id"], "task_id": task_payload[0]["id"]},
    )
    assert session.status_code == 200
    assert session.json()["condition"] == "thinkmate"


def test_dialogue_demo_mode_logs_turns_and_uses_questions(tmp_path):
    client = make_client(tmp_path)
    student_id = client.post("/api/auth/access-code", json={"access_code": "ENG-DEMO-1"}).json()["student_id"]
    client.post("/api/consent", json={"student_id": student_id, "accepted": True})
    task_id = client.get("/api/tasks", params={"student_id": student_id}).json()["tasks"][0]["id"]
    session_id = client.post("/api/sessions", json={"student_id": student_id, "task_id": task_id}).json()["id"]

    turn = client.post(
        "/api/dialogue/turn",
        json={"session_id": session_id, "content": "My claim is that a lighter wing is always better."},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["tutor_turn"]["role"] == "tutor"
    assert "?" in payload["tutor_turn"]["content"]
    assert payload["tutor_turn"]["move_type"] == "clarification"

    summary = client.get("/api/admin/summary", headers={"X-Admin-Password": "admin-test"})
    assert summary.status_code == 200
    assert summary.json()["turns"] == 2


def test_is_low_effort_detection():
    from app.services.socratic import is_low_effort

    assert is_low_effort("idk") is True
    assert is_low_effort("I don't know") is True
    assert is_low_effort("just tell me the answer") is True
    assert is_low_effort("no") is True
    assert is_low_effort("I will use nylon because it is tougher than PLA.") is False
    assert is_low_effort("Use nylon") is False
    # A substantive answer that merely CONTAINS a stuck phrase is not low effort.
    assert is_low_effort("This will help me decide between two materials so I can finish the analysis.") is False
    assert is_low_effort("I am not sure yet, but I think nylon works because it resists fatigue.") is False
    # An explicit give-up appeal is low effort even inside a longer message.
    assert is_low_effort("I thought about it for a while but honestly just tell me the answer please.") is True


def test_non_json_model_response_falls_back_instead_of_500(monkeypatch):
    import json as _json

    class BadBodyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            # A 200 OK whose body is not JSON (e.g. an upstream HTML error page).
            raise _json.JSONDecodeError("Expecting value", "<html>", 0)

    monkeypatch.setattr(
        "app.services.model_adapter.httpx.post", lambda *args, **kwargs: BadBodyResponse()
    )
    settings = Settings(poe_api_key="test-poe-key", poe_model="GPT-4o-Mini")

    text = generate_tutor_turn(
        settings,
        task_title="Stress-test your project",
        scenario="Look for weak spots.",
        student_content="I think nylon is strong enough.",
        move={"move_type": "evidence", "paul_elder_target": "evidence", "prompt": "What evidence supports that?"},
    )
    # No exception, and a safe Socratic fallback is returned.
    assert "?" in text
    assert "scenario" in text.lower()


def test_hf_error_envelope_is_not_shown_as_a_question():
    from app.services.model_adapter import _extract_hf_text

    # HF returns a 200 with an error envelope for cold/loading models. It must
    # not become the tutor's question.
    assert _extract_hf_text({"error": "Model is currently loading"}) == ""
    assert _extract_hf_text({"generated_text": "What evidence supports that?"}) == "What evidence supports that?"


def test_stuck_reply_stays_on_same_reasoning_step(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Zaid", "course": "engineering"}).json()["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]

    first = client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "I will use a five-blade prop."})
    assert first.json()["tutor_turn"]["move_type"] == "clarification"

    # A stuck reply keeps the tutor on the same step instead of advancing.
    stuck = client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "idk"})
    assert stuck.json()["tutor_turn"]["move_type"] == "clarification"

    # A substantive reply then advances to the next step.
    nxt = client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "Five blades give smoother thrust at low speed."})
    assert nxt.json()["tutor_turn"]["move_type"] == "evidence_probe"


def test_reasoning_policy_targets_weakest_then_falls_back_to_sequence():
    from app.services.reasoning_state import assess_reasoning_state, select_move

    # Model assessment: the claim is already clear but evidence is missing, so the
    # tutor should jump to the evidence move rather than re-asking to clarify.
    state = {
        "dimensions": {
            "claim": "clear",
            "evidence": "missing",
            "assumptions": "hidden",
            "counterview": "ignored",
            "validation": "absent",
        }
    }
    assert select_move(state, ["clarification"], stuck=False)["move_type"] == "evidence_probe"
    # A stuck reply stays on the most recent move instead of advancing.
    assert select_move(state, ["evidence_probe"], stuck=True)["move_type"] == "evidence_probe"

    # With no model, the heuristic reproduces the original ordered walk.
    offline = Settings(poe_api_key="")
    s0 = assess_reasoning_state(offline, "P", "G", "", "hello", moves_used=[])
    assert s0["source"] == "heuristic"
    assert select_move(s0, [], stuck=False)["move_type"] == "clarification"
    s1 = assess_reasoning_state(offline, "P", "G", "", "hello", moves_used=["clarification"])
    assert select_move(s1, ["clarification"], stuck=False)["move_type"] == "evidence_probe"


def test_reasoning_assessment_drives_the_move_and_is_stored(tmp_path, monkeypatch):
    # The model rates the claim clear but evidence missing.
    assessment = (
        '{"claim":"clear","evidence":"missing","assumptions":"hidden",'
        '"counterview":"ignored","validation":"absent"}'
    )

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": assessment}}]}

    monkeypatch.setattr("app.services.model_adapter.httpx.post", lambda *a, **k: FakeResp())
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'thinkmate_test.db'}",
        admin_password="admin-test",
        app_env="test",
        poe_api_key="test-poe-key",
        poe_model="GPT-4o-Mini",
        consent_version="test-consent-v1",
    )
    client = TestClient(create_app(settings))
    student = client.post("/api/auth/start", json={"name": "Reema", "course": "engineering"}).json()
    sid = student["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]

    turn = client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "My claim is clearly stated."})
    assert turn.status_code == 200
    # Adaptive: claim is strong, so the tutor goes straight to evidence (not clarify).
    assert turn.json()["tutor_turn"]["move_type"] == "evidence_probe"

    full = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "false"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    tutor_turns = [t for t in full["turns"] if t["role"] == "tutor"]
    assert tutor_turns and tutor_turns[0]["reasoning_state"]["dimensions"]["evidence"] == "missing"

    # The assessment is research metadata and must NOT enter the blinded export.
    blinded = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "true"},
        headers={"X-Admin-Password": "admin-test"},
    ).json()
    assert "reasoning_state" not in json.dumps(blinded)


def test_reasoning_policy_always_moves_forward_even_if_a_dimension_stays_weak():
    from app.services.reasoning_state import select_move

    # A dimension that the model keeps rating sub-strong must NOT trap the tutor:
    # once its move was asked, the tutor advances to the next weak dimension.
    state = {"dimensions": {
        "claim": "vague", "evidence": "weak", "assumptions": "hidden",
        "counterview": "ignored", "validation": "absent",
    }}
    assert select_move(state, [], stuck=False)["move_type"] == "clarification"
    assert select_move(state, ["clarification"], stuck=False)["move_type"] == "evidence_probe"
    assert select_move(state, ["clarification", "evidence_probe"], stuck=False)["move_type"] == "assumption_probe"
    # Once every move has been asked, it closes on reflection (never re-loops).
    everything = ["clarification", "evidence_probe", "assumption_probe", "counterview", "reflection"]
    assert select_move(state, everything, stuck=False)["move_type"] == "reflection"


def test_reasoning_policy_all_strong_and_edge_cases():
    from app.services.reasoning_state import assess_reasoning_state, select_move

    all_strong = {"dimensions": {
        "claim": "clear", "evidence": "strong", "assumptions": "surfaced",
        "counterview": "engaged", "validation": "present",
    }}
    assert select_move(all_strong, ["clarification"], stuck=False)["move_type"] == "reflection"
    # Stuck with no prior moves must not index off the end — returns the weakest.
    s = assess_reasoning_state(Settings(poe_api_key=""), "P", "G", "", "hi", moves_used=[])
    assert select_move(s, [], stuck=True)["move_type"] == "clarification"
    # Heuristic terminal state: every move used -> reflection.
    done = assess_reasoning_state(
        Settings(poe_api_key=""), "P", "G", "", "hi",
        moves_used=["clarification", "evidence_probe", "assumption_probe", "counterview", "reflection"],
    )
    assert select_move(done, ["clarification", "evidence_probe", "assumption_probe", "counterview", "reflection"], stuck=False)["move_type"] == "reflection"


def test_normalize_coerces_unknown_and_missing_to_weakest():
    from app.services.reasoning_state import _normalize

    state = _normalize({"claim": "CLEAR", "counterview": "banana"})
    dims = state["dimensions"]
    assert dims["claim"] == "clear"          # case-insensitive recognised value
    assert dims["counterview"] == "ignored"  # unknown -> weakest
    assert dims["evidence"] == "missing"     # missing -> weakest
    assert state["source"] == "model"
    # Nested {"dimensions": {...}} shape is also accepted.
    nested = _normalize({"dimensions": {"evidence": "strong"}})
    assert nested["dimensions"]["evidence"] == "strong"


def test_parse_assessment_json_handles_bad_and_fenced_replies():
    from app.services.model_adapter import _parse_assessment_json

    assert _parse_assessment_json("the student seems to be doing fine") is None
    assert _parse_assessment_json('{"claim": "clear",') is None  # truncated
    fenced = _parse_assessment_json('```json\n{"claim": "clear"}\n```')
    assert fenced == {"claim": "clear"}
    # A single-object array is leniently unwrapped to the object.
    assert _parse_assessment_json('[{"claim": "vague"}]')["claim"] == "vague"


def test_worksheet_session_never_triggers_a_model_call(tmp_path, monkeypatch):
    calls = {"n": 0}

    def counting_post(*args, **kwargs):
        calls["n"] += 1
        raise AssertionError("the control condition must never call the model")

    monkeypatch.setattr("app.services.model_adapter.httpx.post", counting_post)
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'thinkmate_test.db'}",
        admin_password="admin-test",
        app_env="test",
        poe_api_key="test-poe-key",
        consent_version="test-consent-v1",
    )
    client = TestClient(create_app(settings))
    sid = client.post("/api/auth/start", json={"name": "Wadima", "course": "engineering"}).json()["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    ws = next(t for t in tasks if t["condition"] == "worksheet")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": ws["id"]}).json()["id"]

    client.post(
        "/api/worksheet/response",
        json={"session_id": session_id, "step_key": "claim", "prompt": "P", "response": "My answer."},
    )
    # A dialogue turn on a worksheet session is rejected before any assessment.
    assert client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "hello"}).status_code == 400
    assert calls["n"] == 0


def test_live_tutor_advances_across_turns_when_a_dimension_stays_weak(tmp_path, monkeypatch):
    # The assessor keeps the claim sub-strong every turn; the tutor must still
    # advance instead of repeating 'clarification' forever.
    assessment = (
        '{"claim":"vague","evidence":"weak","assumptions":"hidden",'
        '"counterview":"ignored","validation":"absent"}'
    )

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": assessment}}]}

    monkeypatch.setattr("app.services.model_adapter.httpx.post", lambda *a, **k: FakeResp())
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'thinkmate_test.db'}",
        admin_password="admin-test",
        app_env="test",
        poe_api_key="test-poe-key",
        poe_model="GPT-4o-Mini",
        consent_version="test-consent-v1",
    )
    client = TestClient(create_app(settings))
    sid = client.post("/api/auth/start", json={"name": "Salma", "course": "engineering"}).json()["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]

    moves = []
    for _ in range(3):
        r = client.post(
            "/api/dialogue/turn",
            json={"session_id": session_id, "content": "I think my chosen design is the right one for these reasons."},
        )
        moves.append(r.json()["tutor_turn"]["move_type"])
    # Distinct, advancing moves — no infinite loop on 'clarification'.
    assert moves == ["clarification", "evidence_probe", "assumption_probe"]


def test_migration_adds_reasoning_state_column(tmp_path):
    from sqlalchemy import create_engine, inspect, text
    from app.main import ensure_schema_migrations

    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE turns (id TEXT PRIMARY KEY, session_id TEXT, turn_number INTEGER, "
                "role TEXT, content TEXT)"
            ))
        ensure_schema_migrations(engine)
        cols = {c["name"] for c in inspect(engine).get_columns("turns")}
    finally:
        engine.dispose()
    assert "reasoning_state" in cols


def test_safeguard_replaces_direct_answer():
    result = apply_safeguard("The answer is to choose the cheapest design.")

    assert result.flagged is True
    assert "cannot give the answer directly" in result.content.lower()
    assert "?" in result.content


def test_consent_withdrawal_is_honored(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Maitha", "course": "engineering"}).json()
    sid = student["student_id"]

    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    assert client.get("/api/tasks", params={"student_id": sid}).status_code == 200

    # A later decline withdraws the earlier acceptance — access is revoked.
    client.post("/api/consent", json={"student_id": sid, "accepted": False})
    assert client.get("/api/tasks", params={"student_id": sid}).status_code == 403
    again = client.post("/api/auth/start", json={"name": "Maitha", "course": "engineering"}).json()
    assert again["consent_accepted"] is False


def test_consent_version_change_forces_reconsent(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'thinkmate_test.db'}"
    base = dict(database_url=db_url, admin_password="admin-test", app_env="test", hf_api_token="", poe_api_key="")

    v1 = TestClient(create_app(Settings(consent_version="consent-v1", **base)))
    student = v1.post("/api/auth/start", json={"name": "Khalid", "course": "engineering"}).json()
    sid = student["student_id"]
    v1.post("/api/consent", json={"student_id": sid, "accepted": True})
    assert v1.get("/api/tasks", params={"student_id": sid}).status_code == 200

    # The approved consent text changes mid-pilot: the old acceptance is stale,
    # so the student must re-consent before continuing.
    v2 = TestClient(create_app(Settings(consent_version="consent-v2", **base)))
    again = v2.post("/api/auth/start", json={"name": "Khalid", "course": "engineering"}).json()
    assert again["student_id"] == sid
    assert again["consent_accepted"] is False
    assert v2.get("/api/tasks", params={"student_id": sid}).status_code == 403


def test_effective_cors_falls_back_to_same_origin_in_production():
    from app.main import effective_cors_origins

    prod_wildcard = Settings(app_env="production", admin_password="strong", cors_origins="*")
    assert effective_cors_origins(prod_wildcard) == []

    prod_empty = Settings(app_env="production", admin_password="strong", cors_origins="")
    assert effective_cors_origins(prod_empty) == []

    prod_explicit = Settings(app_env="production", admin_password="strong", cors_origins="https://thinkmate.example")
    assert effective_cors_origins(prod_explicit) == ["https://thinkmate.example"]

    # Local development keeps the convenient wildcard.
    dev = Settings(app_env="development", cors_origins="*")
    assert effective_cors_origins(dev) == ["*"]


def test_safeguard_flags_recommendations_but_allows_questions():
    # New recommendation phrasings are caught.
    assert apply_safeguard("You could use carbon fibre for the wing.").flagged is True
    assert apply_safeguard("I would go with the lithium cells.").flagged is True
    # A legitimate Socratic question is NOT flagged (the over-broad
    # "the answer to" pattern was removed).
    result = apply_safeguard("What is the answer to your first assumption?")
    assert result.flagged is False
    assert result.content == "What is the answer to your first assumption?"


def test_student_transcript_excludes_tutor_turns():
    from types import SimpleNamespace

    from app.api.sessions import student_transcript

    turns = [
        SimpleNamespace(role="student", content="I will use nylon."),
        SimpleNamespace(role="tutor", content="Why nylon over PLA?"),
        SimpleNamespace(role="student", content="Nylon is tougher."),
    ]
    transcript = student_transcript(turns, final_answer="Nylon, for toughness.")
    assert "Why nylon over PLA?" not in transcript
    assert "I will use nylon." in transcript
    assert "Nylon is tougher." in transcript
    assert "S (final answer): Nylon, for toughness." in transcript


def test_study_id_is_high_entropy_and_arm_neutral(tmp_path):
    client = make_client(tmp_path)
    student = client.post("/api/auth/start", json={"name": "Noura", "course": "engineering"}).json()
    code = student["access_code"]
    assert code.startswith("ENG-")
    # 5 random bytes -> 10 hex chars after the prefix, and no A/B arm marker.
    random_part = code.split("-", 1)[1]
    assert len(random_part) == 10
    assert "-A-" not in code and "-B-" not in code


def test_free_text_length_is_capped(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Salem", "course": "engineering"}).json()["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]

    # An absurdly long message is rejected before it reaches the DB or the model.
    huge = "x" * 7000
    assert client.post("/api/dialogue/turn", json={"session_id": session_id, "content": huge}).status_code == 422
    # An empty message is rejected (no wasted model call).
    assert client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "   "}).status_code == 422


def test_admin_endpoint_is_rate_limited(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'thinkmate_test.db'}",
        admin_password="admin-test",
        app_env="test",
        poe_api_key="",
        admin_rate_limit_per_minute=3,
    )
    client = TestClient(create_app(settings))

    # Wrong-password attempts are throttled: after the limit, 429 instead of 401.
    statuses = [
        client.get("/api/admin/summary", headers={"X-Admin-Password": "wrong"}).status_code
        for _ in range(5)
    ]
    assert statuses[:3] == [401, 401, 401]
    assert 429 in statuses[3:]


def _read_completed_at(tmp_path, session_id):
    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{tmp_path / 'thinkmate_test.db'}")
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT completed_at FROM sessions WHERE id = :id"), {"id": session_id}
            ).fetchone()
    finally:
        engine.dispose()
    return row[0] if row else None


def test_complete_session_is_idempotent(tmp_path):
    client = make_client(tmp_path)
    sid = client.post("/api/auth/start", json={"name": "Idem", "course": "engineering"}).json()["student_id"]
    client.post("/api/project", json={"student_id": sid, "project_title": "P", "project_goal": "G"})
    client.post("/api/consent", json={"student_id": sid, "accepted": True})
    tasks = client.get("/api/tasks", params={"student_id": sid}).json()["tasks"]
    tm = next(t for t in tasks if t["condition"] == "thinkmate")
    session_id = client.post("/api/sessions", json={"student_id": sid, "task_id": tm["id"]}).json()["id"]
    client.post("/api/dialogue/turn", json={"session_id": session_id, "content": "A claim."})

    first = client.post(f"/api/sessions/{session_id}/complete")
    assert first.status_code == 200 and first.json()["status"] == "complete"
    completed_at_first = _read_completed_at(tmp_path, session_id)

    # Re-completing must not overwrite the original completion timestamp.
    second = client.post(f"/api/sessions/{session_id}/complete")
    assert second.status_code == 200 and second.json()["status"] == "complete"
    assert _read_completed_at(tmp_path, session_id) == completed_at_first


def test_unique_data_integrity_indexes_exist(tmp_path):
    make_client(tmp_path)  # boots the app, which runs the schema migrations
    from sqlalchemy import create_engine, inspect

    engine = create_engine(f"sqlite:///{tmp_path / 'thinkmate_test.db'}")
    try:
        inspector = inspect(engine)
        session_indexes = {idx["name"]: idx["unique"] for idx in inspector.get_indexes("sessions")}
        turn_indexes = {idx["name"]: idx["unique"] for idx in inspector.get_indexes("turns")}
    finally:
        engine.dispose()
    # One canonical session per (student, task); unique turn ordering per session.
    assert session_indexes.get("uq_session_student_task")
    assert turn_indexes.get("uq_turn_session_number")


def test_worksheet_response_and_exports(tmp_path):
    client = make_client(tmp_path)
    student_id = client.post("/api/auth/access-code", json={"access_code": "ENG-DEMO-2"}).json()["student_id"]
    client.post("/api/consent", json={"student_id": student_id, "accepted": True})
    worksheet_task = client.get("/api/tasks", params={"student_id": student_id}).json()["tasks"][0]
    assert worksheet_task["condition"] == "worksheet"
    session_id = client.post(
        "/api/sessions",
        json={"student_id": student_id, "task_id": worksheet_task["id"]},
    ).json()["id"]

    response = client.post(
        "/api/worksheet/response",
        json={
            "session_id": session_id,
            "step_key": "claim",
            "prompt": "State your claim.",
            "response": "The design should prioritize reliability.",
        },
    )
    assert response.status_code == 200

    exported = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "false"},
        headers={"X-Admin-Password": "admin-test"},
    )
    assert exported.status_code == 200
    assert exported.json()["worksheet_responses"][0]["response"] == "The design should prioritize reliability."

    blinded = client.get(
        "/api/admin/export",
        params={"format": "json", "blinded": "true"},
        headers={"X-Admin-Password": "admin-test"},
    )
    assert "access_code" not in blinded.json()["students"][0]
    assert "sequence" not in blinded.json()["students"][0]

    csv_export = client.get(
        "/api/admin/export",
        params={"format": "csv", "blinded": "false"},
        headers={"X-Admin-Password": "admin-test"},
    )
    assert csv_export.status_code == 200
    rows = list(csv.DictReader(io.StringIO(csv_export.text)))
    assert rows[0]["course"] == "engineering"
