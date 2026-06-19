# ThinkMate Production Deployment Checklist

Use this checklist before giving students a live ThinkMate URL.

## 1. Choose Hosting

Recommended simple path:

- Railway web service from this GitHub repo.
- Railway PostgreSQL database.
- Hugging Face token only if you want the hosted model enabled.

Other workable path:

- Any Docker-capable host or VPS, including Hostinger VPS.
- Managed PostgreSQL or a PostgreSQL container with backups.

GitHub Pages alone is not enough because ThinkMate needs a backend and database.

## 2. Required Environment Variables

Set these on the hosting platform:

```text
DATABASE_URL=<postgres connection string>
ADMIN_PASSWORD=<strong private password>
APP_ENV=production
CONSENT_VERSION=v1-2026-06-19
SEED_DEMO_STUDENTS=false
PILOT_ACCESS_CODES=<approved pseudonymous code list>
CORS_ORIGINS=https://<live-app-domain>
HF_MODEL=google/gemma-2-2b-it
HF_API_TOKEN=<optional Hugging Face token>
POE_API_KEY=<optional Poe API key>
POE_MODEL=GPT-4o-Mini
POE_BASE_URL=https://api.poe.com/v1
```

`PILOT_ACCESS_CODES` format:

```text
ENG-A-001:engineering:A;ENG-B-001:engineering:B;PSY-A-001:psychology:A;PSY-B-001:psychology:B
```

Do not put student names, IDs, emails, or phone numbers in this variable.

## 3. Data And Ethics Gate

Before real student use, confirm:

- UAEU ethics/data approval covers the pilot wording and logging.
- Consent text matches the approved protocol.
- Access codes are pseudonymous.
- `SEED_DEMO_STUDENTS=false` is set.
- Admin password is not the default.
- Export files are stored only in approved research-team storage.
- Retention and deletion plan is documented.

## 4. Deployment Checks

After deployment, open:

```text
https://<live-app-domain>/health
```

Expected production response:

- `status` is `ok`.
- `app_env` is `production`.
- `database` is `ok`.
- `model_mode` is `demo` or `huggingface`, depending on whether `HF_API_TOKEN` is set.

Then test one A-sequence code and one B-sequence code:

- Sequence A Task 1 should route to ThinkMate.
- Sequence B Task 1 should route to worksheet.
- Admin summary should count sessions.
- Admin export should download JSON or CSV.

## 5. Docker Host Path

For a Docker-capable host:

```bash
docker build -t thinkmate-platform .
docker run --env-file .env.production -p 8000:8000 thinkmate-platform
```

Use PostgreSQL in production. SQLite is only for local development and technical testing.
