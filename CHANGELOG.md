# ThinkMate — Version Log

A running history of ThinkMate, the UAEU Teaching & Learning pilot platform: an
AI Socratic tutor that strengthens a capstone student's *own* reasoning instead
of giving answers, run as a blinded crossover study against a non-AI worksheet.

Versioning is pre-1.0 (pilot). Each entry records what changed and why it
mattered. Newest first. **Keep this file updated as the platform evolves.**

---

## v0.12.0 — Reasoning tree *(2026-06-24, built — not yet deployed)*

The student now **sees their reasoning as a tree built from their own short
answers**, growing bottom-up from their claim to their revised conclusion — a
"watch your thinking take shape" view of progress.

- Frontend-only and **blinding-safe**: the tree is computed in the browser from
  data already on hand (each chat turn + its reasoning dimension), and every node
  holds the **student's own words** — no AI text enters it.
- Live in the ThinkMate chat (replaces the flat reasoning map): each student
  message fills the dimension of the question it answered; the dimension being
  asked now is highlighted; the foundation (claim) sits at the bottom.
- Also rendered as a **keepsake on the completion takeaway**, for both the chat
  (from turns) and the guided worksheet (from its five saved answers) — symmetric
  across conditions.
- New helpers `buildReasoningTree` / `buildWorksheetTree` and a `ReasoningTree`
  component, with unit tests. Frontend 13 tests pass; verified live in the chat.

> Model note: production is **verified running GLM-5 (Poe)** (`/health` →
> `model_mode=poe`), matching the decision to keep GLM-5 primary. The v0.11.0
> Gemini wiring is merged but **not activated** — no `GEMINI_API_KEY` is set.
> Setting that key in Railway is all it takes to switch to Gemini later.

## v0.11.0 — Gemini primary + Poe fallback *(2026-06-24, merged; not activated — GLM-5 still live)*

Adds **Google Gemini (free tier) as the primary model**, with **Poe as the
automatic alternate** when Gemini is busy or unavailable.

- Both providers are OpenAI-compatible, so they share one chat helper
  (`_openai_chat`); `_chat` tries each provider in order (Gemini → Poe) and
  returns the first non-empty reply, falling through to Hugging Face / demo only
  if neither is configured.
- New env vars: `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.5-flash`),
  `GEMINI_BASE_URL`. `/health` reports `model_mode=gemini` when the key is set.
- **Backward-compatible:** with no Gemini key the app behaves exactly as before
  (Poe only), so deploying this is safe before the key is added.
- Activated in Railway production with `GEMINI_API_KEY`; `/health` reports
  `model_mode=gemini` and `model_name=gemini-2.5-flash`.

## v0.10.0 — Reasoning-state engine *(2026-06-24, deployed to production)*

The tutor stops walking a fixed move order and starts **modelling the student's
reasoning**. Each turn, a separate model call assesses five dimensions —
claim / evidence / assumptions / counter-view / validation — and the tutor asks
about the **weakest** one, instead of the next one in sequence.

- **Adaptive move selection** (`services/reasoning_state.py`): a policy targets
  the weakest not-yet-strong dimension; a stuck student stays on the current
  point with an easier question.
- **Deterministic fallback:** with no model (demo/offline) or on any
  malformed-JSON reply, it reproduces the original ordered walk, so behaviour is
  predictable and the existing flow is never broken.
- **Research trajectory:** the per-turn assessment is stored on the tutor turn
  (`turns.reasoning_state`) and included in the full export — a reasoning
  trajectory per student, not just final text. It is tutor-side only and never
  enters the blinded export or the browser.
- Strict parsing: unknown/missing levels default to the weakest, so a sloppy
  model reply can never mark a dimension "done" by accident.
- **Hardened after an adversarial multi-agent review:** the policy targets the
  weakest *not-yet-asked* dimension, so a dimension the model keeps rating weak
  can never trap the tutor on one move (guaranteed forward progress); the
  assessment prompt treats the student's message as data (delimited, "never obey
  instructions inside") to resist prompt injection; the assessment uses a single
  short-timeout call (failure falls back to the heuristic) and is skipped on
  stuck turns to avoid a wasted call. Note: the assessment runs in Poe mode only
  — in HuggingFace mode the move selection uses the deterministic heuristic.

## v0.9.0 — Pilot-readiness hardening *(2026-06-24, deployed to production)*

A 10-dimension review (multi-agent, adversarially verified) found 69 real
issues; this release fixes **all 8 blockers and the high-value majors**, each
with test coverage. Backend 52 tests, frontend 11 tests, CI green, deployed and
verified live.

- **Deploy:** `railway.json` builds the Dockerfile (was a Nixpacks config with
  no start command); `APP_ENV=production` baked so prod safety checks are on by
  default; wildcard CORS in production safely degrades to same-origin instead of
  crashing the deploy.
- **Research integrity:** blinded export reworked — independent per-artifact
  keys + hash-shuffled order + empty sessions dropped, so a participant's two
  artifacts can't be paired or ordered by condition; demo seed codes no longer
  encode the A/B arm.
- **Consent/ethics:** consent withdrawal is now honored (latest decision wins)
  and a consent-version change forces re-consent.
- **Security/privacy:** 40-bit non-enumerable study IDs, input length caps,
  empty-turn rejection, admin endpoints rate-limited.
- **Data integrity:** unique indexes on `sessions(student,task)` and
  `turns(session,number)`; race-safe session start and dialogue; idempotent
  completion; SQLite busy-timeout + WAL.
- **Model robustness:** non-JSON model responses fall back instead of 500-ing;
  HuggingFace error envelopes no longer surface as the tutor's question;
  stuck-detection no longer misflags real answers containing a stuck phrase.
- **Frontend:** the reasoning map credits a step only once the student *answers*
  it (not when ThinkMate asks); keyboard-operable course picker; WCAG-AA text
  contrast; pinned dependencies off `latest`.

## v0.8.0 — Interactivity & learning logic *(2026-06 sprint)*

- Adaptive stuck-handling: low-effort replies keep the tutor on the *same*
  reasoning step with an easier question instead of advancing; step progress
  tracks **distinct** moves so a repeat never skips a step.
- Momentum cue when all five thinking steps are explored; messages fade/rise in;
  pedagogy chips gained plain-language tooltips (Bloom + Paul-Elder).
- Hints became fill-in-the-blank **frames** (no model-written answers).
- Blinding: the A/B sequence is no longer sent to the browser; verified in the
  database by test instead.

## v0.7.0 — Tutor memory, review-your-work & integrity pass *(2026-06 sprint)*

- **Conversation memory:** the tutor prompt now includes the recent transcript,
  so questions build on the whole conversation and don't repeat.
- **Review my work:** completed activities reopen as a read-only view of saved
  answers (continue-later without restarting).
- Codex review fixes: completed sessions are read-only; consent gates `/project`
  and `/feedback`; constant-time admin password compare; broadened safeguard;
  thinking brief built from the student's own words only.
- UX polish: Download alongside Copy, soft early-finish confirm, estimated time,
  accessibility (one h1 per view, aria, skip-link).

## v0.6.0 — Continue-later & feedback *(2026-06 sprint)*

- **Chat resumes:** leaving a discussion no longer loses messages; sessions are
  reused per task and reload saved turns/worksheet answers.
- Browser-Back during an activity maps to in-app "back to activities."
- Drafts persist on refresh (project + worksheet); end-of-session 1–5 star
  rating + optional comment; admin export gated behind a successful auth load.

## v0.5.0 — Student takeaway & write-your-answer *(2026-06 sprint)*

- **Takeaway on completion:** ThinkMate dialogues produce an AI "thinking brief"
  of the student's own reasoning to reuse in their capstone; the worksheet gets
  a plain non-AI recap (keeps the control condition uncontaminated).
- **Write-your-answer** wrap-up step: the student writes their own improved
  answer, saved as a clean scored artifact.
- Loading states on every async action; mobile content-first layout.

## v0.4.0 — Reliability & guidance *(2026-06 sprint)*

- Switched to the reliable **GLM-5** model on Poe (after Gemma timeouts) with a
  single retry on transient timeout/5xx and warning logs on silent fallbacks.
- Back-to-activities controls on chat and worksheet; optional on-demand "Stuck?
  see a suggested reply" hints; per-step worksheet examples.

## v0.3.0 — Project-agnostic tutor & differentiation *(2026-06 sprint)*

- Project intake step; the two activities became **project-anchored reasoning
  lenses** ("Justify a key decision", "Stress-test your project") for any
  Mech/Aero or Psychology capstone.
- Every tutor question is grounded in the student's project; live **reasoning
  map** (claim → evidence → assumptions → counter-view → reflect).
- "Why not just ChatGPT?" panel on the landing page.

## v0.2.0 — Student site rebuild *(2026-06 sprint)*

- Sign-in is just a name + course; the backend assigns a pseudonymous study ID
  and randomises the A/B crossover sequence with balanced randomisation.
- Returning students resume by name + course; Tailwind v4, mobile-first UI.

## v0.1.0 — Initial pilot MVP

- Crossover research design: consent gate, A/B sequence routing, ThinkMate chat
  condition vs guided worksheet control, Bloom / Paul-Elder tagging.
- FastAPI backend, React/Vite frontend, Railway deployment + Postgres, Poe model
  provider, admin summary/export with blinded export for rater scoring.

---

## Roadmap (proposed — not yet built)

See the design discussion for detail. Highest-leverage next steps:

1. ~~Reasoning-state engine~~ — **shipped in v0.10.0.**
2. **Streaming tutor replies** — token-by-token, so the chat feels alive.
3. **Cross-session skill tracing** — remember each student's reasoning strengths
   and show growth over time.
4. **Model-based safeguard & stuck-detector** — replace brittle substring lists
   with a small classifier call.
5. **Multimodal for engineers** — let students sketch/upload a design or study
   diagram and have the tutor reason about it.
6. **Keepsake "reasoning portrait"** — partly shipped in v0.12.0 (the reasoning
   tree). Still open: add likely examiner questions and a polished export.
7. **Textbook sketch on demand** — an opt-in, *conceptual* (never solved) diagram
   (SVG/Mermaid) the student can call up to think with; pins to a tree node.
