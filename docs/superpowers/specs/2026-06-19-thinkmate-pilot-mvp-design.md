# ThinkMate Pilot MVP Design

Date: June 19, 2026

## Purpose

Build the first real ThinkMate pilot platform. This is not a polished product launch. It is a research-pilot MVP that can run the approved CETL study with pseudonymous students, record defensible data, and export evidence for blinded scoring and analysis.

The first deployment target is GitHub plus Railway. Azure remains the preferred institutional destination later, but it is blocked until UAEU Azure subscription access is visible and approved.

## Non-Negotiable Scope

The MVP must support:

- Pseudonymous student access codes.
- Consent acceptance before any task begins.
- Two pilot courses: Engineering and Psychology.
- Two tasks per course.
- Crossover condition routing:
  - Sequence A: ThinkMate first, guided worksheet second.
  - Sequence B: guided worksheet first, ThinkMate second.
- ThinkMate Socratic chat flow.
- Non-AI guided worksheet flow.
- Turn-by-turn logging.
- Basic answer-leakage safeguard.
- PostgreSQL-backed persistence.
- Admin export to CSV/JSON for analysis and blinded scoring.
- Replaceable model adapter, starting with Hugging Face Inference API.

The MVP explicitly excludes:

- UAEU/Microsoft login.
- Azure deployment.
- Full instructor analytics dashboard.
- RAG/vector database.
- Arabic support.
- Advanced analytics charts.
- Payment/billing dashboards.

## Architecture

Use a simple three-part architecture:

1. React/Vite frontend.
2. FastAPI backend.
3. PostgreSQL database.

The backend owns all sensitive logic:

- access-code validation,
- consent records,
- task/condition routing,
- model calls,
- safeguard checks,
- logging,
- admin exports.

The frontend never contains model API keys or database credentials.

Railway hosts:

- the FastAPI backend,
- the PostgreSQL database,
- optionally the frontend if using a single full-stack deployment.

The frontend can also be deployed separately later through Vercel, Netlify, or GitHub Pages, but the first implementation should keep deployment simple.

## Model Adapter

The first model provider is Hugging Face Inference API. The code must be written so the provider can be changed later without rewriting the pilot logic.

Define one interface:

```text
generate_tutor_turn(context) -> TutorResponse
```

The initial provider implementation calls Hugging Face. Later providers can support Azure AI Foundry, Azure OpenAI, OpenAI API, Ollama, or another service.

If no Hugging Face token is configured, the backend must still run in demo mode using deterministic local Socratic responses. Demo mode is for development only and must be clearly reported by the health endpoint.

## Student Flow

1. Student opens the ThinkMate pilot URL.
2. Student enters an access code such as `ENG-A-014` or `PSY-B-021`.
3. Backend validates the code.
4. Student sees the consent page.
5. Student accepts consent.
6. Student sees available tasks.
7. Backend determines condition based on sequence and task number.
8. If the condition is ThinkMate, student completes a Socratic chat session.
9. If the condition is guided worksheet, student completes a structured non-AI worksheet.
10. Student submits the task.
11. Backend marks the session complete and stores all responses.

## Admin Flow

The first admin interface is deliberately simple:

- enter an admin password,
- view session counts,
- view completion status,
- download CSV/JSON exports.

The export must support:

- students/access-code table,
- sessions table,
- chat turns table,
- worksheet responses table,
- analysis-ready joined export with no real student names.

The export should include condition labels for research analysis. For blinded rater scoring, a separate anonymized export should hide condition and sequence.

## Data Model

Minimum tables:

- `students`
  - `id`
  - `access_code`
  - `course`
  - `sequence`
  - `created_at`

- `consents`
  - `id`
  - `student_id`
  - `accepted`
  - `accepted_at`
  - `consent_version`

- `tasks`
  - `id`
  - `course`
  - `task_number`
  - `title`
  - `scenario`
  - `worksheet_steps`

- `sessions`
  - `id`
  - `student_id`
  - `task_id`
  - `condition`
  - `status`
  - `started_at`
  - `completed_at`

- `turns`
  - `id`
  - `session_id`
  - `turn_number`
  - `role`
  - `content`
  - `move_type`
  - `paul_elder_target`
  - `bloom_level`
  - `safeguard_flag`
  - `created_at`

- `worksheet_responses`
  - `id`
  - `session_id`
  - `step_key`
  - `prompt`
  - `response`
  - `created_at`

## Socratic Logic

The first implementation should use a rule-based move sequence:

1. Clarify the claim.
2. Ask for evidence.
3. Surface an assumption.
4. Request a counter-view.
5. Ask for reflection/revision.

The LLM can phrase the question, but it must not decide the pedagogical sequence by itself.

Each tutor turn stores:

- intended move,
- Paul-Elder target,
- approximate Bloom level,
- safeguard status.

## Safeguard

The first safeguard is simple but explicit:

- block or rewrite direct answer-giving language,
- block final-solution phrasing,
- prefer questions over explanations,
- log every safeguard trigger.

If the generated model response fails the safeguard, the backend should use a safe fallback prompt such as:

```text
I cannot give the answer directly. What evidence or assumption would you examine next?
```

## Course Content

Seed content must include minimal Engineering and Psychology tasks so the app is usable immediately.

Engineering seed task example:

- design trade-off reasoning,
- safety/ethics implication,
- evidence and assumption review.

Psychology seed task example:

- methodological critique,
- argument strength,
- alternative interpretation.

The seed content is not the final approved course content. It is a working placeholder until the PI/Co-PI approve the actual pilot tasks.

## Deployment

The repository should be deployable from GitHub to Railway.

Required environment variables:

- `DATABASE_URL`
- `HF_API_TOKEN`
- `HF_MODEL`
- `ADMIN_PASSWORD`
- `APP_ENV`
- `CONSENT_VERSION`

The app must expose:

- `/health`
- `/api/auth/access-code`
- `/api/consent`
- `/api/tasks`
- `/api/sessions`
- `/api/dialogue/turn`
- `/api/worksheet/response`
- `/api/admin/summary`
- `/api/admin/export`

## Testing And Verification

Minimum verification before calling the MVP ready:

- backend starts locally,
- frontend builds,
- access code flow works,
- consent is required before task access,
- Task 1/Task 2 condition routing works for A and B sequences,
- ThinkMate chat logs turns,
- worksheet logs responses,
- admin export produces CSV/JSON,
- model adapter works in demo mode without secrets,
- app does not expose API keys in frontend code.

## Success Definition

The MVP is complete when a test student can:

1. enter an access code,
2. accept consent,
3. complete a ThinkMate task,
4. complete a guided worksheet task,
5. produce database records,
6. and an admin can export those records.

Production student use still requires UAEU ethics/data approval and approved deployment settings.
