# ThinkMate Claude Handoff

Last updated: 2026-06-19

## Latest Change — Project-Agnostic + LLM Differentiation (2026-06-19)

ThinkMate is no longer tied to fixed scenarios (it used to be wing-design specific). It now works for **any** Mech/Aero or Psychology capstone:

- After consent, a **project intake** step asks the student their project title and what they want to do (`POST /api/project`; stored as `project_title` / `project_goal` on `students`). Returning students skip it.
- The two seed activities are now **project-anchored reasoning lenses** ("Justify a key decision in your project", "Stress-test your project") — same Paul-Elder dimensions for blinded-scoring comparability, any topic. `seed_database` now **updates** existing task rows so deployed DBs pick up the new wording.
- Every tutor question is **grounded in the student's project** (project title + goal are passed into the model prompt in `model_adapter.py`).
- The tutor system prompt now enforces **brief, simple English, one short question, never answer, never write the student's work, always anchor to their project**.
- New frontend: a **project intake screen**, a live **"reasoning map"** in the chat (claim → evidence → assumptions → counter-view → reflect, lighting up as the dialogue progresses — the "simple graph"), the project shown in the chat, and a "Why not just ChatGPT?" panel on the landing.
- New columns `project_title`, `project_goal` added via the same idempotent startup migration; included in the full admin export, hidden in the blinded export.
- Tests: backend 22 passed, frontend 11 passed.

## Latest Change — Student Site Rebuild (2026-06-19)

The student website was fully rebuilt for a simpler, more professional experience:

- **Sign in is now just a name + course pick** (no access codes for students). The backend assigns a pseudonymous study ID (e.g. `ENG-7F3A2K`) and randomises the crossover sequence (A/B) with balanced randomisation. Endpoint: `POST /api/auth/start` with `{name, course}`.
- Returning students (same name + course, case/space-insensitive) resume their existing record.
- The crossover research design is unchanged: consent gate, Sequence A/B routing, ThinkMate vs guided worksheet, Bloom/Paul-Elder tagging, blinded export.
- **Privacy/blinding preserved:** the student name is saved and included in the full admin export, but the blinded export still hides name, study ID, sequence, and condition for blinded rubric scoring.
- New UI uses Tailwind CSS v4, is mobile-first, and keeps a discreet "Research team" link to the admin area.
- `display_name` column added to `students`; an idempotent startup migration (`ensure_schema_migrations` in `backend/app/main.py`) adds it to existing databases (Postgres + SQLite).
- The legacy `POST /api/auth/access-code` path is kept as an admin/testing backstop.
- Tasks list now reports per-task `completed` status so the UI can show "Done".
- **Live AI fix:** `POE_MODEL` was `Gemma-4-31B`, which is not a working Poe model (returns empty content), so the tutor was silently serving canned fallback questions. Changed to **`Gemma-3-27B`** (verified to return real Socratic questions) and added warning logs in `model_adapter.py` when the model returns empty/errors, so this can never fail silently again. To validate a Poe model before deploying, send one `chat/completions` call and confirm non-empty content.

## Current State

ThinkMate is a deployed student pilot platform for the UAEU Teaching and Learning proposal.

- Local repo folder: `C:\Users\shkhan\OneDrive - UAE University\Codex Space\Teaching and Learning proposal\thinkmate-platform`
- GitHub repo: `https://github.com/shkhan321/thinkmate-platform`
- Live app: `https://thinkmate-app-production.up.railway.app`
- Current branch: `master`
- Latest important commit: `84dd00a feat: improve student pilot experience`
- GitHub CI status at handoff: passing

The app currently has:

- React/Vite frontend
- FastAPI backend
- Railway deployment
- Railway Postgres database
- Poe model provider configured through Railway variables
- Student access-code flow
- Consent screen
- Task selection
- ThinkMate chat condition
- Guided worksheet condition
- Admin summary/export area
- Quick Tour and clearer student UI

## Railway

Railway is already linked in this folder.

- Railway workspace: `shkhan321's Projects`
- Railway project: `thinkmate-platform`
- Project ID: `7f47d107-b1fb-4855-b6c4-d3666a44744e`
- Environment: `production`
- Environment ID: `033085e1-cedd-4f06-b0bd-61e4bd9aab61`
- App service: `thinkmate-app`
- App service ID: `530c657e-ff34-4099-8a37-f4e7680dc609`
- Database service: `Postgres`
- Database service ID: `0f04cc93-5edb-41a3-b7f0-be21c96d5b1e`
- Latest deployment at handoff: `dec96f2b-64f7-410d-aaee-9133e6a787ae`

Important Railway variables already set:

- `DATABASE_URL`
- `APP_ENV=production`
- `ADMIN_PASSWORD`
- `CONSENT_VERSION=v1-2026-06-19`
- `SEED_DEMO_STUDENTS=false`
- `PILOT_ACCESS_CODES`
- `CORS_ORIGINS=*`
- `POE_API_KEY`
- `POE_MODEL=Gemma-3-27B` (was `Gemma-4-31B`, which is not a working Poe model — it returned empty responses, so the tutor silently used fallback questions. `Gemma-3-27B` is verified to return real Socratic questions.)
- `POE_BASE_URL=https://api.poe.com/v1`

Do not print, commit, or copy API keys into files. If the Poe key must be changed, set it through Railway secrets, preferably by stdin or Railway UI.

## Main Commands

Open PowerShell in the repo:

```powershell
cd "C:\Users\shkhan\OneDrive - UAE University\Codex Space\Teaching and Learning proposal\thinkmate-platform"
git pull origin master
```

Check current deployment:

```powershell
railway whoami
railway status
railway service status --service thinkmate-app --json
railway domain list --service thinkmate-app --json
```

Run frontend checks:

```powershell
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm test
corepack pnpm build
cd ..
```

Run backend checks:

```powershell
python -m pip install -r backend\requirements.txt
python -m pytest backend\tests
```

If the system Python is missing dependencies, use the bundled Codex Python:

```powershell
& "C:\Users\shkhan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest backend\tests
```

Deploy to Railway:

```powershell
railway up --service thinkmate-app --environment production --detach --json -y --message "Describe the change"
```

Check live health:

```powershell
Invoke-RestMethod -Uri "https://thinkmate-app-production.up.railway.app/health" | ConvertTo-Json -Depth 5
```

View Railway logs:

```powershell
railway logs --service thinkmate-app --latest --lines 200
```

Check GitHub CI:

```powershell
gh run list --repo shkhan321/thinkmate-platform --limit 3
```

## Current Verification Evidence

At handoff, these checks passed:

- Frontend tests: `8 passed`
- Frontend production build: passed
- Backend tests: `11 passed`
- GitHub CI: success for `84dd00a feat: improve student pilot experience`
- Railway service: `SUCCESS`, not stopped
- Live `/health`: `status=ok`, `database=ok`, `model_mode=poe`, `model_name=Gemma-3-27B`
- Live mobile UI check: no horizontal overflow
- Live student flow check with sample code `ENG-B-001`: access code to task list works

## Important Weak Points

Do not miss these:

1. The current access codes are still sample pilot codes:
   - `ENG-A-001`
   - `ENG-B-001`
   - `PSY-A-001`
   - `PSY-B-001`

2. Before real students use the platform, replace `PILOT_ACCESS_CODES` in Railway with approved pilot codes.

3. The consent and task text are still pilot/MVP wording. Sanan may want final approved wording before student use.

4. Do not expose the Poe API key. It is already stored in Railway. If it was pasted in chat elsewhere, rotate it later.

5. Keep API keys out of GitHub. Never add `.env` files with secrets.

6. If changing the UI, verify mobile layout. Students may use phones.

7. If changing production behavior, run tests, build, deploy, then check the live Railway URL.

## Architecture Pointers

Frontend:

- Main app: `frontend/src/App.tsx`
- Styling: `frontend/src/styles.css`
- UI flow helpers: `frontend/src/flow.ts`
- Frontend tests: `frontend/src/flow.test.ts`, `frontend/src/api.test.ts`

Backend:

- FastAPI app: `backend/app/main.py`
- Settings/env vars: `backend/app/config.py`
- Poe/Hugging Face/demo model adapter: `backend/app/services/model_adapter.py`
- Routes: `backend/app/api/`
- Data models: `backend/app/models.py`
- Seed task/access-code logic: `backend/app/seed.py`
- Backend tests: `backend/tests/test_mvp.py`

Deployment:

- Dockerfile: `Dockerfile`
- Railway config: `railway.json`
- Nixpacks config remains in repo, but Railway is building from Dockerfile.

## Suggested Next Work

Most useful next steps:

1. Replace sample access codes with real approved group codes.
2. Finalize consent text and task wording.
3. Add a small instructor-facing pilot checklist page or document.
4. Add a clearer admin export guide.
5. Add reset/remove-test-data procedure before real pilot.

## Takeover Rule

Before claiming work is complete:

1. Run frontend tests and build.
2. Run backend tests.
3. Push to GitHub.
4. Confirm GitHub CI passes.
5. Deploy with Railway.
6. Check `/health`.
7. Click through at least one student flow on the live URL.

