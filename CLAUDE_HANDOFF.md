# ThinkMate Claude Handoff

Last updated: 2026-06-24

## Latest Change — Pilot-readiness pass: blockers + majors (2026-06-24)

A full multi-agent review (10 dimensions, adversarial verification) found 8 blockers
and 26 majors. This pass fixed every blocker and the high-value majors, with tests for
each. Backend 52 passed, frontend 11 passed, build clean, live flow verified.

Deployment / config:
- **railway.json now builds the Dockerfile** (was NIXPACKS, whose `nixpacks.toml` had no
  start command — the deploy could fail to boot). `nixpacks.toml` is kept as a complete
  fallback (added `[start]`). CI builds the same Dockerfile it now ships.
- **Production safety is fail-closed:** `Dockerfile` bakes `APP_ENV=production`, so admin
  password / demo-seed / CORS checks are on by default in any deployed image.
- **CORS no longer crashes a live deploy:** wildcard/empty `CORS_ORIGINS` in production is
  downgraded to same-origin only (the SPA is same-origin) with a warning, instead of the
  hard RuntimeError that would have crashed the current Railway config. `effective_cors_origins()`.

Research integrity (blinding):
- **Blinded export reworked:** each session is an independently-keyed artifact (`A0001…`,
  not per-student), emitted in a hash-shuffled order, with empty sessions dropped — a rater
  can no longer pair a participant's two artifacts or recover task order/condition.
- **Demo seed codes no longer encode the arm** (`ENG-DEMO-1` not `ENG-A-001`).

Consent / ethics:
- **Withdrawal is honored and version is checked:** new `services/consent.has_active_consent`
  uses the student's LATEST consent decision (a later decline withdraws), and re-prompts when
  `consent_version` changes. Wired into all five gates.

Security / privacy:
- Study IDs are now 40-bit (`token_hex(5)`), so the unauthenticated access-code lookup is not
  enumerable. Free-text fields are length-capped in schemas (DoS/cost). Empty dialogue turns
  rejected. Admin endpoints rate-limited (`services/ratelimit`, app-scoped, students unaffected).

Data integrity / concurrency:
- Unique indexes on `sessions(student_id, task_id)` and `turns(session_id, turn_number)` (added
  in `ensure_schema_migrations`, best-effort on pre-existing dupes). `start_session` and
  `dialogue_turn` handle the race via IntegrityError. `complete_session` is idempotent (no
  `completed_at` overwrite). SQLite `busy_timeout=5000` + WAL.

Model robustness:
- A 200-OK-but-non-JSON model response now falls back instead of 500-ing the student
  (`ValueError` caught in `_poe_chat`/HF). HF `{"error": …}` envelopes no longer surface as the
  tutor's question. `is_low_effort` no longer misflags substantive answers that merely contain a
  stuck phrase (length-gated).

Frontend:
- **Reasoning map / finish-gate credit a step only once the student ANSWERS it** (a student turn
  follows the tutor move), not when ThinkMate asks — a defensible, control-comparable measure.
- `completeAndReturn` now has the `pending` guard and a non-blocking task refresh (a refresh
  failure no longer blocks completion or invites re-submit).
- Course picker is keyboard-operable (arrow keys + roving tabindex). Low-contrast `text-slate-400`
  body/hint text raised to `text-slate-500` (WCAG AA). Frontend deps pinned off `latest`.

Documented residuals (NOT changed — architectural / design-inherent, acceptable for a pilot):
- No per-participant session tokens (IDOR) — conflicts with the "login by just name" requirement;
  mitigated by unguessable UUIDs + high-entropy study IDs + admin rate-limit.
- Safeguard is still a blocklist (broadened) — a rubric/LLM judge is the real fix.
- Balanced randomisation and returning-student matching are not fully atomic — minimisation is
  self-correcting and `busy_timeout` helps at pilot scale.
- Worksheet vs chat artifacts remain structurally distinguishable (design-inherent); keying and
  ordering tells are removed.

OUTSTANDING for the operator: optionally set `CORS_ORIGINS` to the real app URL in Railway (else it
logs a warning and serves same-origin only). Replace `PILOT_ACCESS_CODES` with approved codes that
do NOT embed A/B. Run tests → deploy → check `/health` → click one live student flow.

## Latest Change — UX polish round (2026-06-19)

Applied a QA suggestions list (kept what helps, declined what doesn't):

- **Download** button (alongside Copy) on the completion + review takeaways (saves answer + brief as .txt).
- **Soft early-finish confirm** in the chat: finishing with fewer than 3 of 5 thinking steps asks "finish anyway?" (the ≥1-exchange hard gate stays).
- **Estimated time** ("≈ 10–15 min") on activity cards.
- **Accurate resume hint** on consent: "sign in with the same name and course to continue" (the saved-work code is not a login credential).
- **Project-aware worksheet claim hint** ("For my project (X), I decided to …").
- A11y: decorative icons `aria-hidden`, one `<h1>` per view (sr-only), skip-link raised above the sticky header.
- Tests: backend 37 passed, frontend 11 passed.

**Declined (with reason):** dark mode (large effort, low pilot value), a 404 page (N/A for a routerless SPA), message editing/regenerate (would corrupt the per-turn research log). Worksheet auto-save was already shipped. The full holistic cross-activity dashboard is deferred — the tasks screen + per-activity "Review my work" already cover reviewing both.

## Latest Change — Codex review fixes (2026-06-19)

Ran a full read-only review with the local **Codex CLI (gpt-5.5, xhigh)** ("full DNA" prompt). Applied the high-value, safe findings:

- **Research integrity:** `/api/dialogue/hint` now rejects non-ThinkMate sessions (the non-AI worksheet control can no longer reach the model via hints). Blinded export redesigned — it now emits **condition-free normalized `scoring_artifacts`** (the student's own reasoning only, with a blinded `P#` key, no tutor text / move tags / condition field / `turns` table), so raters can't infer condition. Full (non-blinded) export keeps everything for analysis and now also includes `final_answer` + feedback in CSV.
- **Data integrity:** completed sessions are **read-only** (dialogue turn / worksheet response / answer endpoints return 409 after completion); worksheet responses **upsert** by `(session, step)` (no duplicate rows). The completed activity card now shows only "Review my work" (no "Open again").
- **Consent/privacy:** consent now gates `/api/project` and `/api/feedback` too (backend defense-in-depth). Consent screen discloses external-AI processing and that the name isn't sent. Production startup now **fails if `SEED_DEMO_STUDENTS` is true**.
- **Security:** admin password compared with `secrets.compare_digest` (constant-time).
- **Safeguard** broadened (more answer-giving phrases + max-length cap). **A11y:** error Callout `role="alert"`, chat log `aria-live`, labelled chat/worksheet/wrap-up textareas. **Runtime:** Nixpacks aligned to Python 3.12.
- Tests: backend 37 passed, frontend 11 passed.

**Flagged for your decision (NOT changed — architecture / REC calls):**
1. **No real participant auth** — endpoints trust `student_id`/`session_id` from the browser (UUIDs aren't guessable, but there's no ownership check). A token/cookie session would fix it but adds friction to the "just name" login. I can implement signed participant tokens if you want.
2. **Admin auth** is a single static header password (no rate-limit/audit) — fine for a small pilot; upgrade if data sensitivity grows.
3. **Adaptive tutor** — still a fixed move sequence (now with memory). A rubric-based student-state scorer (claim/evidence/assumptions/constraints/validation/risk) is the biggest next upgrade.
4. **Migrations** are hand-rolled `ALTER TABLE` (fine now; Alembic later). Railway builds via Nixpacks (not the Dockerfile, which CI builds) — document or switch.

## Latest Change — Tutor memory + Review-your-work (2026-06-19)

Researched proven Socratic-tutor patterns (adaptive scaffolding, never-answer, thinking-partner-with-memory) and strengthened the build:

- **Conversation memory:** the tutor prompt now includes the recent transcript (`dialogue.py` passes `history`), so questions build on the whole conversation and don't repeat. System prompt strengthened: adapt to the student's level, scaffold a smaller question if they're stuck or ask for the answer, never give it.
- **Review your work (continue-later):** completed activities now have a **"Review my work"** button that opens a read-only view of the saved answer + brief (or worksheet answers) without restarting — built on `GET /api/sessions/{id}/state` + `/summary`. `tasks` now returns `session_id` per task. Browser-back guard extended to the review screen.
- Resume of in-progress chats/worksheets and drafts (from earlier passes) already cover "continue later"; this adds re-reading finished work.
- Reviewed by the local **Codex CLI** (`codex exec review`, gpt-5.5) — see notes below.
- Tests: backend 32 passed, frontend 11 passed.

## Latest Change — Cancel on Edit Project (2026-06-19)

Minor QA follow-up. Of the four items reported, three were already fixed in the previous build (verified): mobile chat now sits **above** the thinking map (chat-first), tab order is Skip → header → form (not form→footer→header), and the homepage footer has **no** research-team link. The one genuinely open item is fixed:

- **Edit Project now has a Cancel** (only in edit mode — never on the first, required intake). Cancel returns to the activities list and **discards the unsaved draft** so the saved project is unchanged.
- Tests: backend 31 passed, frontend 11 passed.

## Latest Change — QA round 2 (mobile, drafts, back button, admin) (2026-06-19)

Second external QA report. Frontend-only fixes:

- **Header is now solid** (`bg-white`, not translucent) so content can't ghost through the sticky header on scroll (the "header covers the prompt on mobile" report).
- **Project text persists on refresh** before "Start thinking" (localStorage draft, restored on load, cleared on save) — makes "saved automatically" true. Same draft persistence added to the **worksheet** (typed answers survive refresh / browser Back).
- **Browser Back during an activity** now maps to in-app "back to activities" via a `popstate` guard, instead of leaving the SPA to a blank page.
- **Admin:** Export JSON/CSV are disabled until a successful "Load summary" (auth); changing the password re-locks them. Admin heading is now an `<h1>`.
- **Research/admin is no longer advertised to students:** the footer link is gone; the team reaches it via the URL hash **`.../#admin`** (still password-gated).
- **Not changed (by design):** unknown routes return 200 with the app — standard single-page-app fallback; there are no shareable sub-routes to 404 on.
- Tests: backend 31 passed, frontend 11 passed.

## Latest Change — End-of-session feedback (2026-06-19)

- Simple **feedback step on the completion screen**: a 1–5 star rating + an optional one-line comment, asked once (a `localStorage` flag per student stops re-prompting). New `feedback` table, `POST /api/feedback`, included in the admin export (ratings always; free-text comments only in the non-blinded export).
- Tests: backend 31 passed, frontend 11 passed.

## Latest Change — External QA report fixes (2026-06-19)

Addressed an external QA/UX report (another agent). Fixes:

- **CRITICAL — chat now resumes.** Was: leaving a discussion lost all messages and started a new session. Now `start_session` reuses the student's existing session per task; new `GET /api/sessions/{id}/state` returns saved turns + worksheet answers; the chat reloads them on open. Activity cards show **"In progress" / "Continue discussion"** (`tasks.in_progress`). `backToActivities` refreshes the task list.
- **Empty discussion can't be "finished":** Finish is disabled until at least one exchange.
- **Tour dialog a11y:** closes on Escape, traps Tab focus, returns focus to the trigger.
- **Research-team link hidden once a student is signed in** (only shows on the landing).
- **Edit project** button on the activities screen (returns to a pre-filled intake).
- Course-options note on sign-in; "Skip to main content" link; mobile "Step N of 5" indicator; "study ID" already renamed earlier.
- Already-fixed earlier (the report tested an older build): copy "Copied!" feedback, AI "thinking…" indicator, mobile content-first layout.
- Worksheet still persists on submit (not per-field); its guard is the Back-confirm. Per-field worksheet autosave is a possible future improvement.
- Tests: backend 30 passed, frontend 11 passed.

## Latest Change — Reviewer pass: write-your-answer + mobile + fixes (2026-06-19)

External-reviewer walkthrough of the whole student flow, then fixes:

- **Write-your-answer step** after a ThinkMate chat (new `wrapup` stage): the student writes their own improved answer; it is saved (`POST /api/sessions/{id}/answer`, new `sessions.final_answer` column) and **leads the takeaway** ("Your answer" above the AI brief). Makes "build toward YOUR answer" active, and gives researchers a clean scored artifact (in export + fed into the AI brief). Skippable.
- **Bug fixed:** Activity 1's seed scenario promised "ThinkMate will question your reasoning…" even when that activity is delivered as the non-AI worksheet (sequence B). Scenarios are now condition-neutral.
- **Mobile:** chat & worksheet now render the conversation/boxes **before** the sidebar (`order` utilities), so the input is above the fold on phones (it was below before).
- Tasks screen now explains the two activity styles + a "Start here" cue on the first one.
- Course-aware project placeholders (Psychology vs Engineering); worksheet now shows the student's project; worksheet Back warns before discarding typed answers.
- Consent: renamed "study ID" → "saved-work code"; added a respectful "I'd rather not take part" decline path.
- Note: the Codex runtime lost backend deps mid-session; local server now runs from `.venv-preview` (gitignored). Update `.claude/launch.json` runtimeExecutable if it moves.
- Tests: backend 28 passed, frontend 11 passed.

## Latest Change — Student takeaway + loading states (2026-06-19)

First-principles UX pass. The core gap: a student finished an activity and walked away with **nothing usable** (data was saved only for researchers).

- **Takeaway on completion** (`GET /api/sessions/{id}/summary`): for a ThinkMate dialogue, an **AI "thinking brief"** of the student's OWN reasoning (claim / strongest points / what to strengthen) they can copy into their capstone. For the worksheet it is a **plain non-AI recap** of their own answers — deliberately no AI, so the non-AI control condition stays uncontaminated (`kind: "ai" | "plain"`). Completion screen shows it with a Copy button + loading/error states.
- **Loading states** added to every async student action (sign in, consent, save project, start activity) via a shared `pending` flag — prevents double-submits and the "is it broken?" feeling on slow networks.
- Fixed a project-agnostic copy leftover (chat empty-state example no longer mentions "design").
- Tests: backend 26 passed, frontend 11 passed.

## Latest Change — Reliable model (GLM-5) + Poe retry (2026-06-19)

- `POE_MODEL` is now **`GLM-5`**. `Gemma-3-27B` became unreliable on Poe (consistent read-timeouts → tutor fell back to canned questions). Reliability test (3 calls each, live key): **GLM-5 3/3**, GLM-4.6 3/3, Gemini-2.5-Flash 3/3, GPT-4o-Mini 3/3; **Gemma-3-27B 0/3 (timeouts)**, Claude-Haiku-3.5 0/3 (500), GLM-4-Plus 404. GLM-5 also gives the sharpest project-aware Socratic questions.
- `model_adapter.py` now calls Poe through a shared `_poe_chat` helper with a **single retry** on transient timeout/5xx (used by both tutor turns and hints).
- **Lesson:** validate a Poe model with *several* live calls (not one) before trusting it — Poe bots can be intermittently unavailable. Health only reports config, never a real call.
- Tests: backend 24 passed, frontend 11 passed.

## Latest Change — Back navigation + "Stuck?" hints (2026-06-19)

- Both the worksheet and the ThinkMate chat now have a **Back to activities** control (previously a student could get stuck inside an activity).
- A confused student can ask for help: the chat has an optional **"Stuck? See a suggested reply"** button (`POST /api/dialogue/hint`) that returns a short *example to adapt* — a starter grounded in the student's project, never a finished answer (`generate_hint` in `model_adapter.py`, with a generic sentence-starter fallback). Hints are on-demand only (no token cost unless used) and are not logged as dialogue turns.
- Each worksheet step now carries an `example` sentence-starter, shown as the textarea placeholder and a "Stuck? e.g. …" hint line (added to `COMMON_STEPS`; picked up by the seed upsert).
- Tests: backend 24 passed, frontend 11 passed.

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
- `POE_MODEL=GLM-5` (history: `Gemma-4-31B` returned empty content; `Gemma-3-27B` worked then started timing out; `GLM-5` is verified reliable 3/3 and gives the sharpest Socratic questions.)
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
- Live `/health`: `status=ok`, `database=ok`, `model_mode=poe`, `model_name=GLM-5`
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

## Iteration — 2026-06-23: interactivity, learning logic, fresh Codex pass

Goal this round: make the tool more interactive and stronger for learning, then
re-review the full DNA with Codex (gpt-5.5) and apply the findings I agree with.

Interactivity + learning (this round's design pass):
- Adaptive stuck handling: `is_low_effort()` in `services/socratic.py` detects
  "idk / not sure / one-word filler" replies; `api/dialogue.py` then keeps the
  tutor on the SAME reasoning step and asks an easier question (model gets a
  `stuck` flag) instead of advancing. Step progress now tracks DISTINCT moves so
  a repeat never skips a step.
- Momentum cue: when all five thinking steps are explored, the chat shows an
  "All five thinking steps explored" note and the Finish button becomes primary.
- New messages fade/rise in (`tm-rise`); pedagogy chips now have hover tooltips
  explaining Bloom + Paul-Elder in plain words.

Codex review applied (agreed items):
- Hints are now fill-in-the-blank FRAMES (no model-written answers).
- Safeguard catches more recommendation phrasings ("you could use", "go with the", etc.).
- Thinking brief is built from the student's OWN words only (tutor turns excluded).
- A/B `sequence` is no longer sent to the browser (blinding); tests verify it via the DB.
- Production startup now fails on wildcard CORS.
- a11y: course picker is a radiogroup, transcript uses role="log" + aria-relevant, feedback textarea labelled.

Deferred (documented, NOT done) — most are user decisions or bigger changes:
- Auth model (Codex #5/#6): student endpoints authorize by raw session_id and
  name-login can collide. This CONFLICTS with the user's explicit "login by just
  name" requirement — left as-is; user to decide if a low-friction verifier is wanted.
- Server-side completion validation (#4) + "finish without writing" (#16): would
  change completion UX; not changed without the user.
- Concurrency hardening (#11 atomic randomisation, #14/#15 unique constraints): low
  real risk for a small sequential pilot; needs migrations.
- Reasoning-map "done on ask vs answer" deep fix (#3): partially mitigated by the
  distinct-move logic above; full fix needs backend current-move state.
- Log hint exposure (#9), normalise blinded export shapes (#10), confirm modal (#20).

Environment note: the user's global `claude-mem@thedotmack` plugin worker is broken
(SessionStart "Failed to start worker") and was blocking the Read/Edit tools this
session; edits were applied via Python through Bash instead. User may want to
reinstall or disable that plugin.

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

