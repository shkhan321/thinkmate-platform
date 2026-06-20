# ThinkMate Pilot Platform

ThinkMate is a pilot platform for testing Socratic AI support in UAEU student projects. It is built for the approved CETL pilot, with simple name-based sign in, consent, two-course task routing, a ThinkMate chat condition, a guided worksheet condition, and research export tools.

This repository now contains a real pilot MVP, not only a project website.

## What The Pilot Does

- Students sign in with just their **name** and pick their **course** (Engineering or Psychology). No password.
- Each student is given a pseudonymous study ID (e.g. `ENG-7F3A2K`) and is randomised into a crossover sequence (A or B) using balanced randomisation, so the two arms stay even as students enrol.
- Returning students (same name + course) resume their existing study record, including their sequence and progress.
- Students accept the study consent, then **describe their own capstone project** (title + what they want to do). ThinkMate works for **any** Mech/Aero or Psychology capstone topic — it is not tied to a fixed scenario. Every Socratic question is anchored to the student's real project.
- The two activities are reasoning lenses on the student's own project ("Justify a key decision", "Stress-test your project"), which keeps them comparable for blinded scoring while accepting any topic.
- The platform routes each activity to either ThinkMate chat or the guided worksheet comparison based on the student's sequence.
- **How it differs from raw ChatGPT:** ThinkMate never gives the answer or writes the work. It runs a fixed pedagogical move sequence (clarify → evidence → assumptions → counter-view → reflect), grounds questions in the student's project, replies briefly in simple English, and shows a live "reasoning map" of how the student's thinking is building.
- ThinkMate asks Socratic questions and logs the dialogue; the worksheet condition logs structured student responses.
- The admin area shows a summary and exports JSON or CSV. The **blinded** export hides name, study ID, sequence, and condition so rubric scoring stays blind; the full export keeps the student name for the research team.
- The model layer runs in safe demo mode, or calls Poe (`POE_API_KEY` + `POE_MODEL`) or a Hugging Face model (`HF_API_TOKEN`).
- A legacy access-code sign in (`POST /api/auth/access-code`) is kept as an admin/testing backstop and for any pre-seeded `PILOT_ACCESS_CODES`.

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
For deployed one-service builds, leave `VITE_API_URL` empty so the browser calls the same Railway domain.

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
POE_API_KEY=<Poe API key, optional>
POE_MODEL=GLM-5
POE_BASE_URL=https://api.poe.com/v1
ADMIN_PASSWORD=<strong admin password>
APP_ENV=production
CONSENT_VERSION=v1-2026-06-19
SEED_DEMO_STUDENTS=false
PILOT_ACCESS_CODES=ENG-A-001:engineering:A;ENG-B-001:engineering:B;PSY-A-001:psychology:A;PSY-B-001:psychology:B
CORS_ORIGINS=https://<your-railway-app>.up.railway.app
```

Railway will use `nixpacks.toml` to install Python and frontend dependencies, build the frontend, and start FastAPI through `railway.json`.

For a real pilot, replace the sample `PILOT_ACCESS_CODES` value with the approved pseudonymous class list. Keep the format `ACCESS_CODE:course:sequence`, separated by semicolons. Use `SEED_DEMO_STUDENTS=false` so students cannot enter the demo codes.

## Docker Deployment

The repository also includes a Dockerfile for Docker-capable hosts such as a VPS.

```bash
docker build -t thinkmate-platform .
docker run --env-file .env.production -p 8000:8000 thinkmate-platform
```

Use PostgreSQL for production. SQLite is only for local development and technical testing.

See [Production Deployment Checklist](docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md) before giving students the live URL.

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
- Docker deployment path: included
- Actual cloud deployment: requires Railway project access and production secrets
