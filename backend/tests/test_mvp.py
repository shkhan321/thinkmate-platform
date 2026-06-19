import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
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
        consent_version="test-consent-v1",
    )
    return TestClient(create_app(settings))


def test_health_reports_demo_mode(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["model_mode"] == "demo"
    assert payload["database"] == "ok"


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

    demo_login = client.post("/api/auth/access-code", json={"access_code": "ENG-A-001"})
    assert demo_login.status_code == 404

    pilot_login = client.post("/api/auth/access-code", json={"access_code": "ENG-A-099"})
    assert pilot_login.status_code == 200
    assert pilot_login.json()["course"] == "engineering"
    assert pilot_login.json()["sequence"] == "A"


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

    login = client.post("/api/auth/access-code", json={"access_code": "ENG-A-001"})
    assert login.status_code == 200
    student = login.json()
    assert student["course"] == "engineering"
    assert student["sequence"] == "A"
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
    student_id = client.post("/api/auth/access-code", json={"access_code": "ENG-A-001"}).json()["student_id"]
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


def test_safeguard_replaces_direct_answer():
    result = apply_safeguard("The answer is to choose the cheapest design.")

    assert result.flagged is True
    assert "cannot give the answer directly" in result.content.lower()
    assert "?" in result.content


def test_worksheet_response_and_exports(tmp_path):
    client = make_client(tmp_path)
    student_id = client.post("/api/auth/access-code", json={"access_code": "ENG-B-001"}).json()["student_id"]
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
