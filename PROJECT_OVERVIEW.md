# ThinkMate — Complete Project Overview

> Hand-off brief for an engineer/agent picking up this project. It describes what
> ThinkMate is, the full tech stack and architecture, the LLM layer, the user
> interface, where it is deployed, and how to run/test/ship it. No secrets are
> included — only the names of the variables that hold them.

Last updated: 2026-06-24.

---

## 1. What ThinkMate is

ThinkMate is a **deployed research-pilot web platform** for the UAE University
(UAEU) "Innovation in Teaching & Learning" project. It is **not primarily a
tutoring app — it is a controlled experiment** that asks:

> *When an AI tutor asks questions instead of giving answers, do capstone
> students reason more deeply than they do with a normal (non-AI) worksheet?*

It is a **within-subjects crossover study** for Mechanical/Aerospace Engineering
and Psychology capstone students:

- Each student does **two activities**. One is the **ThinkMate** condition (an AI
  Socratic tutor). The other is the **guided worksheet** condition (a non-AI
  control). The order (the A/B "sequence") is randomised per student.
- The AI tutor **never gives the answer** — it asks one short question at a time,
  anchored to the student's own project, and builds toward the student's *own*
  improved answer.
- Each student's reasoning is captured as a clean artifact and later scored by
  raters who are **blinded** to which condition produced it.

Audience: real capstone students, often on **phones** — mobile layout matters.

---

## 2. Where it lives (URLs & infrastructure)

| Thing | Value |
|---|---|
| Live app | https://thinkmate-app-production.up.railway.app |
| GitHub repo | https://github.com/shkhan321/thinkmate-platform (default branch `master`) |
| Hosting | Railway (project `thinkmate-platform`, service `thinkmate-app`, env `production`) |
| Database (prod) | Railway **PostgreSQL** |
| Database (local/dev) | **SQLite** file `thinkmate_dev.db` |
| Build/deploy | Railway builds the **Dockerfile** (`railway.json` → `"builder": "DOCKERFILE"`); deploy with the Railway CLI `railway up` |
| CI | GitHub Actions — `.github/workflows/thinkmate-ci.yml` (Backend API tests · Frontend tests · Container build) |
| Health check | `GET /health` |

Railway identifiers (from the maintainer's handoff): project `7f47d107-b1fb-4855-b6c4-d3666a44744e`,
app service `530c657e-ff34-4099-8a37-f4e7680dc609`, Postgres service `0f04cc93-5edb-41a3-b7f0-be21c96d5b1e`.

The **frontend is served same-origin by the backend** (FastAPI serves the built
Vite SPA from `frontend/dist`). There is no separate frontend host, so the app
does **not** need cross-origin CORS in production.

---

## 3. The LLM layer (the model behind it)

Provider chain, tried in order until one returns content:
**Gemini → Poe → Hugging Face → demo.**

| Aspect | Detail |
|---|---|
| Primary provider | **Google Gemini** (free tier), via its OpenAI-compatible endpoint |
| Gemini model / base | `GEMINI_MODEL=gemini-2.5-flash`, `GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`, auth `GEMINI_API_KEY` |
| Alternate provider | **Poe** — used automatically when Gemini is busy/unavailable, or alone if no Gemini key |
| Poe model / base | `POE_MODEL=GLM-5`, `POE_BASE_URL=https://api.poe.com/v1`, auth `POE_API_KEY` |
| Tertiary fallback | Hugging Face Inference (`HF_API_TOKEN`, `HF_MODEL=google/gemma-2-2b-it`) |
| Final fallback | **Demo mode** (canned Socratic questions) when no key is set — used by all tests |

Both Gemini and Poe are OpenAI-compatible, so they share one helper
(`_openai_chat`); `_chat` iterates the providers (`_chat_providers` defines the
order). Get a free Gemini key at <https://aistudio.google.com/apikey> and set
`GEMINI_API_KEY` as a Railway secret. Until that key is set, the app uses Poe.

Model history (why GLM-5): `Gemma-4-31B` returned empty content; `Gemma-3-27B`
worked then began timing out; **`GLM-5` was verified reliable (3/3 live calls)**
and gives the sharpest project-aware Socratic questions. Validate any Poe model
with several live calls before trusting it.

All model access goes through one adapter: **`backend/app/services/model_adapter.py`**
(`active_model_mode`, `generate_tutor_turn`, `generate_hint`,
`generate_session_summary`, `generate_reasoning_assessment`, with a shared
`_poe_chat` helper that retries once on transient timeout/5xx and falls back to
canned content on failure).

### What "the layer" actually is

The raw model just answers. ThinkMate wraps it in:

1. **Tutor rules** — a system prompt: never give the answer, ask one short
   question, anchor to the student's project (`SYSTEM_PROMPT` in `model_adapter.py`).
2. **Reasoning structure** — five Socratic moves mapped to Bloom + Paul-Elder
   (`backend/app/services/socratic.py`, `SOCRATIC_MOVES`):
   `clarification → evidence_probe → assumption_probe → counterview → reflection`.
3. **Reasoning-state engine** (`backend/app/services/reasoning_state.py`, v0.10.0)
   — each turn, a separate model call rates the student's reasoning across five
   dimensions (claim / evidence / assumptions / counterview / validation) and the
   tutor asks about the **weakest** one. Falls back to a deterministic ordered
   walk with no model. The assessment is stored per turn for research.
4. **Safeguard** (`backend/app/services/safeguard.py`) — post-processes every
   tutor reply; if it leaked an answer (blocklist) or is too long, it is replaced
   with a safe question. The model is never trusted alone.
5. **Hints** — optional fill-in-the-blank *frames* (never answers), on demand.

---

## 4. Tech stack

**Backend** (`backend/`, Python **3.12**):
fastapi 0.115.6 · uvicorn[standard] 0.34.0 · SQLAlchemy 2.0.36 · pydantic 2.10.4 ·
pydantic-settings 2.7.0 · httpx 0.28.1 · psycopg[binary] 3.2.3 (Postgres) ·
pytest 8.3.4. Entry point: `backend/app/main.py` (`app = create_app()`).

**Frontend** (`frontend/`, package manager **pnpm 11.8.0**):
React 19 · Vite 8 · TypeScript 6 · Tailwind CSS v4 · vitest. Build = `tsc && vite build`.

**Deploy**: multi-stage Dockerfile (node build stage → python runtime). Runtime
runs `uvicorn app.main:app` from `/app/backend`. `APP_ENV=production` is baked
into the image so production safety checks are on by default.

---

## 5. Repository structure

```
thinkmate-platform/
├── Dockerfile                 # build: node (vite build) → python runtime (uvicorn)
├── railway.json               # builder = DOCKERFILE, healthcheck = /health
├── nixpacks.toml              # fallback builder (has a [start] command); Docker is active
├── pytest.ini
├── README.md
├── CHANGELOG.md               # version history (keep updated)
├── CLAUDE_HANDOFF.md          # running maintainer log
├── PROJECT_OVERVIEW.md        # this file
├── .github/workflows/thinkmate-ci.yml
│
├── backend/
│   ├── requirements.txt
│   ├── Procfile
│   └── app/
│       ├── main.py            # create_app, /health, schema migrations, CORS, SPA mount
│       ├── config.py          # Settings (env vars, defaults)
│       ├── database.py        # engine/session, SQLite WAL+busy_timeout
│       ├── models.py          # ORM: Student, Consent, Task, PilotSession, Turn, WorksheetResponse, Feedback
│       ├── schemas.py         # Pydantic request/response models (with length caps)
│       ├── seed.py            # seed tasks + demo/pilot access codes; COMMON_STEPS
│       ├── api/               # FastAPI routers (one file per area)
│       │   ├── auth.py        # /api/auth/start, /api/auth/access-code
│       │   ├── consent.py     # /api/consent
│       │   ├── project.py     # /api/project
│       │   ├── tasks.py       # /api/tasks
│       │   ├── sessions.py    # /api/sessions (+ /complete /answer /state /summary)
│       │   ├── dialogue.py    # /api/dialogue/turn, /api/dialogue/hint  (ThinkMate only)
│       │   ├── worksheet.py   # /api/worksheet/response  (worksheet only)
│       │   ├── feedback.py    # /api/feedback
│       │   └── admin.py       # /api/admin/summary, /api/admin/export  (password-gated)
│       └── services/
│           ├── model_adapter.py    # all LLM calls (Poe / HF / demo) + assessment
│           ├── reasoning_state.py  # the reasoning-state engine (move policy)
│           ├── socratic.py         # SOCRATIC_MOVES, move_by_type, is_low_effort
│           ├── safeguard.py        # answer-leak guard on tutor replies
│           ├── routing.py          # condition_for(), balanced A/B randomisation, study IDs
│           ├── exports.py          # full + blinded research exports
│           ├── consent.py          # has_active_consent (withdrawal + version)
│           └── ratelimit.py        # admin endpoint rate limiter
│
└── frontend/
    ├── package.json · pnpm-lock.yaml · vite.config.ts · tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx           # React entry
        ├── App.tsx            # the whole student state machine (sign-in → review)
        ├── flow.ts            # stages, COURSES, REASONING_STEPS, coveredReasoning, helpers
        ├── api.ts             # typed fetch client (same-origin)
        ├── types.ts           # shared TS types (mirror the backend schemas)
        └── components/
            ├── Chat.tsx        # ThinkMate chat + live reasoning map
            ├── Worksheet.tsx   # guided worksheet (non-AI control)
            ├── ProjectIntake.tsx
            ├── Admin.tsx       # research/admin area (summary + export)
            ├── ui.tsx          # shared UI (Callout, PedagogyTags, ReasoningMap, Stepper, Tour)
            └── icons.tsx
```

---

## 6. Backend: API endpoints

All return JSON. Student endpoints require **consent** (except auth/consent
themselves); the consent check uses the latest decision and the current
`CONSENT_VERSION`.

| Method | Path | Body / Query | Purpose |
|---|---|---|---|
| POST | `/api/auth/start` | `{name, course}` | Name-based sign-in; assigns pseudonymous study ID + A/B sequence |
| POST | `/api/auth/access-code` | `{access_code}` | Legacy/admin login by study ID |
| POST | `/api/consent` | `{student_id, accepted}` | Record/withdraw consent |
| POST | `/api/project` | `{student_id, project_title, project_goal}` | Capture the student's capstone |
| GET | `/api/tasks` | `?student_id` | List the 2 activities (+ condition, completed, in_progress) |
| POST | `/api/sessions` | `{student_id, task_id}` | Start/reuse the session for a task |
| POST | `/api/sessions/{id}/complete` | — | Mark complete (idempotent) |
| POST | `/api/sessions/{id}/answer` | `{answer}` | Save the student's own final answer |
| GET | `/api/sessions/{id}/state` | — | Resume data (turns + worksheet answers) |
| GET | `/api/sessions/{id}/summary` | — | Takeaway: AI "thinking brief" (chat) or plain recap (worksheet) |
| POST | `/api/dialogue/turn` | `{session_id, content}` | One tutor exchange **(ThinkMate sessions only)** |
| POST | `/api/dialogue/hint` | `{session_id}` | Optional fill-in-the-blank starter **(ThinkMate only)** |
| POST | `/api/worksheet/response` | `{session_id, step_key, prompt, response}` | Save a worksheet step **(worksheet only)**; upserts |
| POST | `/api/feedback` | `{student_id, rating, comment?}` | 1–5 rating + optional comment |
| GET | `/api/admin/summary` | header `X-Admin-Password` | Row counts |
| GET | `/api/admin/export` | `?format=json\|csv&blinded=bool` + header | Research export (rate-limited) |
| GET | `/health` | — | Status, db, model mode/name |
| GET | `/{path}` | — | SPA fallback (serves the React app) |

### Data model (`models.py`)

- **Student** — `id`, `access_code` (study ID), `display_name` (real name),
  `course`, `sequence` (A/B), `project_title`, `project_goal`.
- **Consent** — `student_id`, `accepted`, `accepted_at`, `consent_version`.
- **Task** — `course`, `task_number` (1/2), `title`, `scenario`, `worksheet_steps` (JSON).
- **PilotSession** — `student_id`, `task_id`, `condition` (`thinkmate`/`worksheet`),
  `status`, `final_answer`. Unique on `(student_id, task_id)`.
- **Turn** — `session_id`, `turn_number`, `role` (`student`/`tutor`), `content`,
  `move_type`, `paul_elder_target`, `bloom_level`, `reasoning_state` (JSON,
  tutor-side), `safeguard_flag`. Unique on `(session_id, turn_number)`.
- **WorksheetResponse** — `session_id`, `step_key`, `prompt`, `response` (upsert per step).
- **Feedback** — `student_id`, `rating`, `comment`.

---

## 7. The website interface (student journey)

Single-page React app (`App.tsx`). Stages (`flow.ts` `StudentStage`):
`login → consent → project → tasks → active → wrapup → complete → review`,
plus a hidden **admin** view at URL hash `#admin`.

1. **Landing / Sign in** — branded hero, a "Why not just ChatGPT?" panel, and a
   form: **type your name + pick your course** (Engineering or Psychology). No
   password. A "Quick tour" dialog is available. Returning students resume by
   name + course.
2. **Consent** — short notice (discloses external-AI processing, that the name
   isn't sent to the model, and the right to withdraw); Agree / "I'd rather not
   take part".
3. **Project intake** — title + one or two lines on what they want to do. Every
   tutor question is anchored to this. Returning students skip it.
4. **Activities (tasks)** — two project-anchored reasoning lenses:
   *"Justify a key decision in your project"* and *"Stress-test your project"*.
   Each card shows its style and Done / In-progress / Continue state.
5. **Active activity** — one of two conditions:
   - **ThinkMate chat** (`Chat.tsx`): a chat with the tutor; a live **reasoning
     map** lights up the five thinking steps as the student demonstrates them; an
     optional "Stuck? see a suggested reply" hint; pedagogy chips (Bloom +
     Paul-Elder) with tooltips. Finish is gated until ≥1 exchange.
   - **Guided worksheet** (`Worksheet.tsx`): five fixed boxes (claim, evidence,
     assumption, counter-view, reflection) with example starters. **No AI** — this
     is the control condition; it never calls the model.
6. **Wrap-up** (ThinkMate only) — the student writes their **own** improved
   answer (saved as a clean scored artifact); skippable.
7. **Completion** — a **takeaway**: for chat, an AI "thinking brief" of the
   student's *own* reasoning to reuse in their capstone; for the worksheet, a
   plain non-AI recap. Copy + Download. Then a one-time 1–5 star feedback prompt.
8. **Review my work** — reopen a finished activity read-only.

Cross-cutting UX: mobile-first, content-before-sidebar on phones, solid sticky
header, draft persistence (localStorage) on refresh, browser-Back mapped to
in-app navigation, loading states on every async action, accessibility
(one `<h1>` per view, ARIA live regions, keyboard-operable course picker,
WCAG-AA text contrast, skip-link).

### Admin / research interface (`Admin.tsx`, `#admin`)

Password-gated (header `X-Admin-Password`, rate-limited). Shows row counts and
**Export JSON/CSV** with a **Blinded** toggle. Export buttons unlock only after a
successful summary load.

---

## 8. Research integrity & blinding (do not break these)

These rules are load-bearing for the study. Any change must preserve them:

- The **worksheet (control) never reaches the model** — `dialogue/turn` and
  `dialogue/hint` hard-reject any non-`thinkmate` session; `worksheet.py` and the
  worksheet summary path never call the model.
- The **A/B sequence is never sent to the browser** (not in any API response or
  TS type); tests assert it only from the DB.
- The **blinded export** (`exports.py`) contains the student's own reasoning only:
  independent **per-artifact** keys (a participant's two artifacts can't be
  paired), **hash-shuffled** order, no tutor text, no move tags, no condition
  field, no `reasoning_state`, empty sessions dropped.
- The **AI thinking brief** is built from the student's own messages only.
- **Access/study codes must not encode the A/B arm** (study IDs are random hex;
  demo codes are neutral).
- **Consent** gates all student endpoints; withdrawal is honoured (latest
  decision wins) and a `CONSENT_VERSION` change forces re-consent.

---

## 9. Configuration (environment variables)

Set in Railway for production; defaults in `backend/app/config.py`. **Never commit
secrets.**

| Variable | Prod value / note |
|---|---|
| `DATABASE_URL` | Railway Postgres URL (SQLite by default locally) |
| `APP_ENV` | `production` (baked into the Docker image; enables safety checks) |
| `ADMIN_PASSWORD` | secret; required (startup fails on a default in production) |
| `CONSENT_VERSION` | e.g. `v1-2026-06-19` |
| `SEED_DEMO_STUDENTS` | `false` in production (startup fails if true) |
| `PILOT_ACCESS_CODES` | `CODE:course:sequence;…` — use codes that do **not** embed A/B |
| `CORS_ORIGINS` | app URL ideally; `*`/empty in prod safely degrades to same-origin |
| `POE_API_KEY` | secret |
| `POE_MODEL` | `GLM-5` |
| `POE_BASE_URL` | `https://api.poe.com/v1` |
| `HF_API_TOKEN`, `HF_MODEL` | optional fallback provider |
| `admin_rate_limit_per_minute` | default 30 |

---

## 10. Run, test, build, deploy

```bash
# ---- Backend (Python 3.12) ----
python -m pip install -r backend/requirements.txt
python -m pytest backend/tests            # currently 54 tests, all green
uvicorn app.main:app --reload             # run from backend/ ; serves API (+ SPA if built)

# ---- Frontend (pnpm 11.8.0) ----
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm test                        # vitest (11 tests)
corepack pnpm build                       # tsc + vite build -> frontend/dist
corepack pnpm dev                         # local dev server (Vite)

# ---- Deploy to Railway (production) ----
railway up --service thinkmate-app --environment production --detach -y --message "…"
# verify:
#   GET https://thinkmate-app-production.up.railway.app/health   -> status ok
#   railway deployment list                                      -> newest = SUCCESS

# ---- CI status ----
gh run list --repo shkhan321/thinkmate-platform --limit 3
```

Notes:
- A local virtualenv `.venv-preview/` (gitignored) holds backend deps if the
  system Python lacks them: `./.venv-preview/Scripts/python.exe -m pytest backend/tests`.
- Railway does **not** auto-deploy on a GitHub merge here — deploy is triggered
  with `railway up`. CI builds the Dockerfile (the same artifact Railway ships).
- DB schema changes are hand-rolled idempotent `ALTER TABLE` adds in
  `ensure_schema_migrations()` (`main.py`) — works on SQLite and Postgres.

---

## 11. Current version & state

- **Live in production: v0.9.0** — pilot-readiness hardening (deploy config,
  blinded-export rework, consent withdrawal, security/concurrency/model-robustness,
  a11y). Verified live.
- **Built but not yet deployed: v0.10.0** — the **reasoning-state engine**
  (section 3). It is in the working tree, tested (54 backend tests green), pending
  an adversarial review and a deploy.
- Full history is in `CHANGELOG.md` (keep it updated each release).

Known residuals / TODO (intentional, see `CLAUDE_HANDOFF.md`):
- No per-participant session tokens (login is by name, by design) — endpoints
  trust client-supplied UUIDs; study IDs are high-entropy and non-enumerable.
- Safeguard is a broadened blocklist (could become a model-based classifier).
- Balanced randomisation is not fully atomic (self-correcting at pilot scale).
- A test smoke account named **"Deploy SmokeTest"** exists in the prod DB
  (consent withdrawn, no activity data) — safe to delete before the real pilot.

Roadmap candidates (not built): streaming tutor replies, cross-session skill
tracing, model-based safeguard/stuck-detector, multimodal (sketch/upload),
keepsake "reasoning portrait".

---

## 12. Conventions for an agent working here

- **Match the surrounding code**; small, focused changes. Backend is plain
  FastAPI + SQLAlchemy 2.0 style; frontend is function components + hooks.
- **Always run both test suites and the frontend build** before claiming done.
- **Verify mobile** for any UI change (students use phones).
- **Never** print/commit `POE_API_KEY`, `ADMIN_PASSWORD`, or any secret; never add
  `.env` files with secrets. `*.db`, `node_modules/`, `dist/`, `.venv*/` are gitignored.
- **Protect the study**: keep the worksheet AI-free, keep the A/B sequence off the
  wire, and keep the blinded export condition-free (section 8).
- For production behaviour changes: run tests → build → deploy (`railway up`) →
  check `/health` → click one student flow on the live URL.
