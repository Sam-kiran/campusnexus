# Task Issues

This file lists granular issues to split work into small tasks. Use the Branch & Commit conventions in `project-plan.md` and create one branch/PR per issue.

---

TASK-001: Add `.env.example` and `.gitignore` hygiene
- Description: Provide a clear `.env.example` for local dev and ensure `.gitignore` excludes `.env`, `db.sqlite3`, and media files.
- Implementation notes:
  - Files to change: add `.env.example` at repo root (already added), update `.gitignore`.
  - Example `.env.example` keys: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DEBUG`, `GEMINI_API_KEY`, AWS placeholders.
- Acceptance criteria:
  - `.env.example` exists and documents required env vars
  - `.gitignore` excludes `.env` and `db.sqlite3`
- Labels: `infra`, `docs`
- Size: small

TASK-002: Settings hardening - env-driven config
- Description: Move sensitive settings to env lookup and add `python-dotenv` support for local dev.
- Implementation notes:
  - Files: `campusnexus/settings.py`
  - Replace any hard-coded SECRET_KEY with `os.getenv('DJANGO_SECRET_KEY', 'dev-key')` and call `load_dotenv()` at top for local.
  - Ensure `DEBUG` uses env var.
- Acceptance criteria:
  - No hard-coded secrets in `settings.py`
  - Local dev works with `.env`
- Labels: `backend`, `security`
- Size: small

TASK-003: Ensure `DATABASE_URL` support and migrate check
- Description: Ensure settings use `DATABASE_URL` (via `django-environ` or `dj-database-url`) and CI runs `manage.py migrate` against sqlite.
- Implementation notes:
  - Files: `campusnexus/settings.py`, CI workflow
  - Use `django-environ` (already present) or `dj-database-url` if preferred.
- Acceptance:
  - Local dev runs with `DATABASE_URL=sqlite:///db.sqlite3`
  - CI runs migrations successfully
- Labels: `backend`, `infra`
- Size: small

TASK-004: Add `Procfile` and export `app` in WSGI
- Description: Add runtime `Procfile` and confirm `campusnexus/wsgi.py` exports `app` variable.
- Implementation notes:
  - Files: `Procfile` (added), `campusnexus/wsgi.py` (updated to export `app`)
- Acceptance:
  - `gunicorn campusnexus.wsgi:app` works locally
- Labels: `infra`
- Size: small

TASK-005: Append storage packages to `requirements.txt`
- Description: Ensure optional storage packages `django-storages` & `boto3` are present for S3 integration.
- Implementation notes:
  - Files: `requirements.txt` (appended)
- Acceptance:
  - `pip install -r requirements.txt` installs `django-storages` and `boto3`
- Labels: `infra`
- Size: small

TASK-006: Add `local-dev.md` documentation
- Description: Document steps to run the project locally from checkout.
- Implementation notes:
  - Files: `local-dev.md` (create)
  - Include exact commands for venv, pip, copying `.env.example`, migrate, runserver
- Acceptance:
  - A developer following the doc can run the app locally
- Labels: `docs`, `infra`
- Size: small

TASK-007: Configure static files & WhiteNoise
- Description: Ensure static files use WhiteNoise in production and `collectstatic` is configured.
- Implementation notes:
  - Files: `settings.py`, `build_files.sh` (created)
  - Add `whitenoise.middleware.WhiteNoiseMiddleware` in `MIDDLEWARE` and static config using `STATIC_ROOT`.
- Acceptance:
  - `python manage.py collectstatic` runs
  - Static files served by WhiteNoise when `DEBUG=0`
- Labels: `backend`, `infra`
- Size: small

TASK-008: Configure media for optional S3 storage
- Description: Add scaffolding for `django-storages` and S3-compatible storage. Only enable when AWS env vars present.
- Implementation notes:
  - Files: `settings.py` edits: detect `AWS_STORAGE_BUCKET_NAME` and configure `DEFAULT_FILE_STORAGE` accordingly.
- Acceptance:
  - Local dev uses filesystem storage if env is not provided
  - With S3 env set, uploads go to S3
- Labels: `backend`, `infra`
- Size: medium

TASK-009: Add CORS settings
- Description: Allow front-end origins via `django-cors-headers` config and document `CORS_ALLOWED_ORIGINS` in `.env.example`.
- Implementation notes:
  - Files: `settings.py`
- Acceptance:
  - Frontend at `http://localhost:3000` can hit API endpoints when configured
- Labels: `backend`, `infra`
- Size: small

TASK-010: Add simple API endpoints / DRF readiness
- Description: Identify missing DRF endpoints; add a minimal `api/` router and `events` list endpoint if not present.
- Implementation notes:
  - Files: new `api/` app or add `events/api.py` and `urls.py` route under `/api/`.
  - Prefer minimal approach: add `events/api.py` with a simple serializer and viewset for Event list.
- Acceptance:
  - `GET /api/events/` returns JSON list (status 200)
- Labels: `backend`, `enhancement`
- Size: medium

TASK-011: Add tests - users & events
- Description: Add minimal pytest tests for user creation and event list endpoint.
- Implementation notes:
  - Files: `users/tests/test_models.py`, `events/tests/test_api.py`
  - Use `pytest-django` fixtures and sqlite
- Acceptance:
  - Tests run in CI and pass
- Labels: `qa`, `backend`
- Size: medium

TASK-012: Lint and code style
- Description: Add ruff/flake8 config if missing and enforce in CI.
- Implementation notes:
  - Files: `.github/workflows/ci.yml` (already added), optionally `.ruff.toml`
- Acceptance:
  - Lint job runs and reports errors/warnings
- Labels: `qa`
- Size: small

TASK-013: Add banner generation smoke test and docs
- Description: Add a small management command or script to exercise `generate_event_banner_ai` so the team can verify Gemini integration.
- Implementation notes:
  - Files: `events/management/commands/test_banner.py` (small script), update `README.md` to document use
- Acceptance:
  - Running the command outputs a generated image file when `GEMINI_API_KEY` is set, otherwise falls back to local template
- Labels: `backend`, `qa`
- Size: small

TASK-014: Deploy docs - Railway & Vercel
- Description: Add `deploy/README.md` with step-by-step instructions.
- Implementation notes:
  - Files: `deploy/README.md` (created)
- Acceptance:
  - Developer follows doc and can link repo to Railway and deploy with minimal manual steps
- Labels: `docs`, `infra`
- Size: small

TASK-015: Add simple GitHub PR template
- Description: Add `.github/PULL_REQUEST_TEMPLATE.md` with checklist matching acceptance criteria.
- Implementation notes:
  - Files: create template file
- Acceptance:
  - PR created includes the checklist
- Labels: `infra`, `docs`
- Size: small

TASK-016: Ensure SECRET_KEY not hard-coded (critical)
- Description: If SECRET_KEY is hard-coded in `settings.py`, replace it with env lookup and add `python-dotenv` load.
- Implementation notes:
  - Files: `campusnexus/settings.py` (edits)
- Acceptance:
  - No production secrets in repo
- Labels: `critical`, `security`
- Size: small

TASK-017: Add Procfile-based deploy instructions
- Description: Document using `Procfile` and `build_files.sh` for Railway deploy.
- Implementation notes:
  - Files: `deploy/README.md` updates
- Acceptance:
  - Deploy doc includes commands to run migrations and set env
- Labels: `docs`, `infra`
- Size: small

TASK-018: Add CI secret guidance and deploy gating
- Description: Document required repo secrets for deploy (RAILWAY_API_KEY, DATABASE_URL, DJANGO_SECRET_KEY) and gate deploy job.
- Implementation notes:
  - Files: `project-plan.md`, `deploy/README.md`
- Acceptance:
  - CI `deploy` job only runs on `main` and uses placeholder for secrets
- Labels: `infra`, `docs`
- Size: small

TASK-019: Provide small accessibility/UX polish tasks
- Description: Identify 2-3 small UI improvements in templates (buttons, alt text for images, forms) and implement.
- Implementation notes:
  - Files: templates in `templates/` folder
- Acceptance:
  - Templates updated for accessible forms and images
- Labels: `frontend`, `enhancement`
- Size: medium

TASK-020: Final acceptance & smoke test
- Description: Run through `local-dev.md` and verify the app can create an event and feedback entry.
- Implementation notes:
  - Files: none
- Acceptance:
  - Documented smoke test passes
- Labels: `qa`
- Size: small

---

Notes:
- If any critical security issue (hardcoded secrets) is detected while implementing, create an immediate critical PR to replace secrets with env usage.
- Keep issue sizes conservative; break down larger ones into multiple smaller tasks if implementation grows.
