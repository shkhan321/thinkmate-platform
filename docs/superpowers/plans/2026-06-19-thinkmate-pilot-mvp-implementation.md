# ThinkMate Pilot MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deployable research-pilot MVP with pseudonymous access codes, consent, crossover routing, ThinkMate chat, guided worksheet, PostgreSQL logging, Hugging Face model adapter, and admin export.

**Architecture:** React/Vite frontend talks to a FastAPI backend. The backend owns access-code validation, consent, routing, model calls, safeguards, logging, and exports. PostgreSQL is used in deployment, while SQLite is allowed for local development through the same SQLAlchemy models.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic, httpx, pytest, React, TypeScript, Vite, Railway-compatible environment variables.

---

## File Structure

- Create `backend/requirements.txt`: backend runtime and test dependencies.
- Create `backend/app/main.py`: FastAPI app entrypoint and router registration.
- Create `backend/app/config.py`: environment-backed settings.
- Create `backend/app/database.py`: SQLAlchemy engine/session setup.
- Create `backend/app/models.py`: database tables.
- Create `backend/app/schemas.py`: API request/response models.
- Create `backend/app/seed.py`: seed access codes and course tasks.
- Create `backend/app/services/routing.py`: crossover condition logic.
- Create `backend/app/services/socratic.py`: move sequence and metadata.
- Create `backend/app/services/safeguard.py`: answer-leakage checks.
- Create `backend/app/services/model_adapter.py`: Hugging Face adapter plus deterministic demo mode.
- Create `backend/app/services/exports.py`: CSV/JSON export builders.
- Create `backend/app/api/*.py`: auth, consent, tasks, sessions, dialogue, worksheet, admin.
- Create `backend/tests/*.py`: focused backend tests.
- Create `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`.
- Create `frontend/src/*`: React app, API client, typed state, pages, and components.
- Create `railway.json`: backend deployment command.
- Modify `.env.example`: document required environment variables.
- Modify `README.md`: add local run and Railway deployment instructions.

## Task 1: Backend Foundation

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_health.py`

- [ ] Step 1: Add backend dependencies.

```text
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
pydantic==2.10.4
pydantic-settings==2.7.0
python-dotenv==1.0.1
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.25.0
```

- [ ] Step 2: Create settings with `DATABASE_URL`, `HF_API_TOKEN`, `HF_MODEL`, `ADMIN_PASSWORD`, `APP_ENV`, and `CONSENT_VERSION`.

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./thinkmate_dev.db"
    hf_api_token: str = ""
    hf_model: str = "google/gemma-2-2b-it"
    admin_password: str = "change-me"
    app_env: str = "development"
    consent_version: str = "v1-2026-06-19"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] Step 3: Create SQLAlchemy engine/session and declarative base.
- [ ] Step 4: Define tables for students, consents, tasks, sessions, turns, and worksheet responses.
- [ ] Step 5: Create `/health` returning app environment, database status, model provider mode, and consent version.
- [ ] Step 6: Add `test_health.py` verifying `/health` returns `200`.
- [ ] Step 7: Run `python -m pytest backend/tests/test_health.py -v`.
- [ ] Step 8: Commit foundation.

## Task 2: Seed Data And Routing

**Files:**
- Create: `backend/app/seed.py`
- Create: `backend/app/services/routing.py`
- Create: `backend/tests/test_routing.py`
- Modify: `backend/app/main.py`

- [ ] Step 1: Seed access codes for Engineering and Psychology with both A and B sequences.

```python
SEED_STUDENTS = [
    {"access_code": "ENG-A-001", "course": "engineering", "sequence": "A"},
    {"access_code": "ENG-B-001", "course": "engineering", "sequence": "B"},
    {"access_code": "PSY-A-001", "course": "psychology", "sequence": "A"},
    {"access_code": "PSY-B-001", "course": "psychology", "sequence": "B"},
]
```

- [ ] Step 2: Seed two Engineering tasks and two Psychology tasks with scenario and worksheet steps.
- [ ] Step 3: Implement `condition_for(sequence, task_number)`:

```python
def condition_for(sequence: str, task_number: int) -> str:
    if sequence == "A":
        return "thinkmate" if task_number == 1 else "worksheet"
    if sequence == "B":
        return "worksheet" if task_number == 1 else "thinkmate"
    raise ValueError("sequence must be A or B")
```

- [ ] Step 4: Add startup seed initialization that inserts records only if missing.
- [ ] Step 5: Add tests for A/B routing and invalid sequence.
- [ ] Step 6: Run `python -m pytest backend/tests/test_routing.py -v`.
- [ ] Step 7: Commit seed/routing.

## Task 3: Student Access, Consent, Tasks, And Sessions API

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/consent.py`
- Create: `backend/app/api/tasks.py`
- Create: `backend/app/api/sessions.py`
- Create: `backend/tests/test_student_flow.py`
- Modify: `backend/app/main.py`

- [ ] Step 1: Define request/response schemas for access-code login, consent, task list, session start, and session complete.
- [ ] Step 2: Implement `POST /api/auth/access-code`.
- [ ] Step 3: Implement `POST /api/consent`.
- [ ] Step 4: Implement `GET /api/tasks?student_id={student_id}`, requiring accepted consent.
- [ ] Step 5: Implement `POST /api/sessions` to create a session with condition from crossover routing.
- [ ] Step 6: Implement `POST /api/sessions/{session_id}/complete`.
- [ ] Step 7: Test that task access is blocked before consent and allowed after consent.
- [ ] Step 8: Test that session conditions match A/B sequence.
- [ ] Step 9: Run `python -m pytest backend/tests/test_student_flow.py -v`.
- [ ] Step 10: Commit student flow API.

## Task 4: ThinkMate Chat, Model Adapter, And Safeguard

**Files:**
- Create: `backend/app/services/socratic.py`
- Create: `backend/app/services/safeguard.py`
- Create: `backend/app/services/model_adapter.py`
- Create: `backend/app/api/dialogue.py`
- Create: `backend/tests/test_dialogue.py`
- Modify: `backend/app/main.py`

- [ ] Step 1: Implement the five Socratic moves: clarify claim, evidence, assumption, counter-view, reflection.
- [ ] Step 2: Implement direct-answer safeguard that flags phrases such as `the answer is`, `you should write`, `final answer`, and `in conclusion`.
- [ ] Step 3: Implement deterministic demo model response when `HF_API_TOKEN` is empty.
- [ ] Step 4: Implement Hugging Face API call when `HF_API_TOKEN` is present.
- [ ] Step 5: Implement `POST /api/dialogue/turn` to store student turn, generate tutor turn, safeguard it, and store tutor turn.
- [ ] Step 6: Test demo-mode chat returns a question and logs two turns.
- [ ] Step 7: Test safeguard fallback replaces direct-answer text.
- [ ] Step 8: Run `python -m pytest backend/tests/test_dialogue.py -v`.
- [ ] Step 9: Commit dialogue/model/safeguard.

## Task 5: Guided Worksheet And Admin Export API

**Files:**
- Create: `backend/app/api/worksheet.py`
- Create: `backend/app/services/exports.py`
- Create: `backend/app/api/admin.py`
- Create: `backend/tests/test_exports.py`
- Modify: `backend/app/main.py`

- [ ] Step 1: Implement `POST /api/worksheet/response`.
- [ ] Step 2: Implement `GET /api/admin/summary` guarded by `X-Admin-Password`.
- [ ] Step 3: Implement `GET /api/admin/export?format=json|csv&blinded=true|false`.
- [ ] Step 4: JSON export returns students, sessions, turns, and worksheet responses.
- [ ] Step 5: CSV export returns analysis-ready rows.
- [ ] Step 6: Blinded export hides access code, sequence, and condition.
- [ ] Step 7: Test admin password rejection and successful export.
- [ ] Step 8: Run `python -m pytest backend/tests/test_exports.py -v`.
- [ ] Step 9: Commit worksheet/admin export.

## Task 6: Frontend MVP

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/styles.css`

- [ ] Step 1: Create Vite React TypeScript app files without adding extra UI libraries.
- [ ] Step 2: Build screens for access code, consent, task list, ThinkMate chat, worksheet, completion, and admin export.
- [ ] Step 3: Store only the current `student_id` in browser state; do not store API keys or admin password persistently.
- [ ] Step 4: Show a visible banner when backend reports demo model mode.
- [ ] Step 5: Run `npm install` inside `frontend`.
- [ ] Step 6: Run `npm run build`.
- [ ] Step 7: Commit frontend MVP.

## Task 7: Deployment Configuration And Docs

**Files:**
- Create: `railway.json`
- Modify: `.env.example`
- Modify: `README.md`
- Create: `backend/Procfile`

- [ ] Step 1: Add Railway backend start command.

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "deploy": {
    "startCommand": "cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
  }
}
```

- [ ] Step 2: Document required Railway variables.
- [ ] Step 3: Document local backend run command.
- [ ] Step 4: Document local frontend run command.
- [ ] Step 5: Document pilot-safety note: production student use requires UAEU ethics/data approval.
- [ ] Step 6: Run full backend tests.
- [ ] Step 7: Run frontend build.
- [ ] Step 8: Commit deployment docs.

## Task 8: Final Verification

**Files:**
- Modify as needed only if verification fails.

- [ ] Step 1: Run `python -m pytest backend/tests -v`.
- [ ] Step 2: Run `npm run build` in `frontend`.
- [ ] Step 3: Start backend locally and verify `/health`.
- [ ] Step 4: Exercise one A-sequence and one B-sequence test flow through API or UI.
- [ ] Step 5: Confirm admin JSON export contains records.
- [ ] Step 6: Confirm no frontend file contains `HF_API_TOKEN`, `DATABASE_URL`, or a hard-coded real secret.
- [ ] Step 7: Commit any verification fixes.

## Spec Coverage

- Pseudonymous access codes: Tasks 2, 3, 6.
- Consent gate: Tasks 3, 6.
- Two courses and two tasks: Task 2.
- Crossover routing: Tasks 2, 3.
- ThinkMate chat: Task 4.
- Guided worksheet: Task 5.
- Turn logging: Task 4.
- Safeguard: Task 4.
- PostgreSQL persistence: Tasks 1, 7.
- Admin exports: Task 5.
- Replaceable model adapter: Task 4.
- Railway/GitHub deployability: Task 7.
