# CampusNexus - Project Plan

**Project Summary**
CampusNexus is a Django monolith that powers campus event management, feedback, dashboards and an AI chatbot assistant. This plan splits the repo into minimal, incremental tasks so a single developer can prepare a production-ready backend deploy (Railway) and an optional frontend split (Vercel) with minimal code changes and clear rollout milestones.

**High-level Architecture Recommendation**
- Backend: Railway hosting running Django with `gunicorn`. Use a managed Postgres database (Railway Postgres) for reliability and backups. Use S3-compatible storage (Cloudflare R2 / DigitalOcean Spaces / AWS S3) for media/static in production; locally keep files on disk.
  - Reasons: Railway provides easy Git-based deployments and environment management; Postgres is standard for Django; S3-compatible storage offloads large media files and integrates with `django-storages`.
- Frontend: If you plan to split, use Vercel with a Next.js front-end (recommended) pointing to the Railway API. If you do not split, keep Django templates and serve via Railway.
  - Reasons: Vercel is optimized for modern frontends and integrates easily with a separate frontend repo. Keeping templates avoids refactors and is okay for rapid delivery.

**Milestones**

Milestone 1 — Core API + Auth (ETA: 3 days)
- Tasks: env & settings hardening, `.env.example`, configure `DATABASE_URL`, add `Procfile`, export `app` from `wsgi.py`, add basic CI (lint + test), create local-dev docs.
- Issues: see `TASK-001`..`TASK-006` in `task-issues.md`.
- Acceptance: `main` passes CI; developer can run site locally and register/login.

Milestone 2 — Events/Feedback + Media (ETA: 4 days)
- Tasks: static + media configuration (`whitenoise` for static, optional `django-storages` for S3 when env present), ensure event banner generation path works, add sample tests for events and feedback, add CORS settings for frontend.
- Issues: `TASK-007`..`TASK-015`.
- Acceptance: Uploading media works locally; tests for event creation pass.

Milestone 3 — Chatbot + Dashboard + polish (ETA: 3 days)
- Tasks: finalize chatbot config (Gemini API key via env), add lightweight dashboard auth guards, fix UX bugs, add smoke tests, and document deploy.
- Issues: `TASK-016`..`TASK-025`.
- Acceptance: Chatbot can be enabled with `GEMINI_API_KEY` and basic dashboard pages load protected by login.

**QA & Acceptance Test Plan**
- Manual tests:
  - Local dev: follow `local-dev.md` to run the server; create an account and add an event and feedback.
  - Admin: log into admin and verify migrations and models.
- Automated tests (CI):
  - Unit tests for models (users/events/feedback).
  - API smoke tests: events list endpoint, homepage rendering.
  - Linting: ruff/flake8.

**Deliverables**
- `project-plan.md`, `task-issues.md`, `deploy/README.md` in repo root
- Minimal scaffolding: `.env.example`, `Procfile`, `build_files.sh`, CI workflow
- Small safe changes: export `app` in `wsgi.py`, append storage packages to `requirements.txt`

**Branch & PR policy**
- Branch format: `feature/ISSUE-<n>-short-title` or `fix/ISSUE-<n>-short-title`.
- Commit message: `ISSUE-<n>: short description`.
- PR title: `ISSUE-<n> - Short title` and include an acceptance checklist.

**Next steps**
1. Review `task-issues.md` and pick the first 1-2 issues to implement.
2. Create branches per the naming convention and open PRs with checklists.
3. Set `RAILWAY_API_KEY` and other secrets in the host after merging.
