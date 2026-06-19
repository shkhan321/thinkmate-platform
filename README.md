# ThinkMate Pilot Platform

ThinkMate is a pilot platform for testing Socratic AI support in UAEU student projects. It is built for the approved CETL pilot, with pseudonymous access codes, consent, two-course task routing, a ThinkMate chat condition, a guided worksheet condition, and research export tools.

This repository now contains a real pilot MVP, not only a project website.

## What The Pilot Does

- Students enter a study access code such as `ENG-A-001` or `PSY-B-001`.
- Students accept the study consent before seeing tasks.
- Each student gets two tasks from their course.
- The platform automatically routes each task to either ThinkMate chat or guided worksheet comparison.
- ThinkMate asks Socratic questions and logs the dialogue.
- The worksheet condition logs structured student responses.
- The admin area shows a summary and exports JSON or CSV data.
- The model layer can run in safe demo mode or call a Hugging Face hosted model when `HF_API_TOKEN` is set.

## Local Backend

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/health`.

## Local Frontend

In a second terminal:

```powershell
cd frontend
pnpm install
pnpm dev
```

Open the local frontend URL shown by Vite. The frontend uses `VITE_API_URL=http://localhost:8000` by default.

## One-Service Production Build

The backend can serve the built frontend from `frontend/dist`. For a local production-style check:

```powershell
cd frontend
pnpm build
cd ..\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

## Railway Deployment

Use Railway with one web service and one PostgreSQL database.

Set these Railway variables:

```text
DATABASE_URL=<Railway PostgreSQL connection string>
HF_API_TOKEN=<Hugging Face token, optional for demo mode>
HF_MODEL=google/gemma-2-2b-it
ADMIN_PASSWORD=<strong admin password>
APP_ENV=production
CONSENT_VERSION=v1-2026-06-19
```

Railway will use `nixpacks.toml` to install Python and frontend dependencies, build the frontend, and start FastAPI through `railway.json`.

## Pilot Safety Note

This platform is ready for controlled technical testing. Before real student use, the consent text, retention policy, access-code list, data export handling, and model settings must match UAEU ethics and data-governance approval.

## Test Commands

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -v
cd frontend
pnpm test
pnpm build
```

## Status

- Backend API: implemented
- Student pilot flow: implemented
- ThinkMate chat and demo/Hugging Face model adapter: implemented
- Guided worksheet condition: implemented
- Admin summary/export: implemented
- Railway deployment configuration: included
- Actual cloud deployment: requires Railway project access and production secrets
