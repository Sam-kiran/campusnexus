# Deploy Guide

This guide covers deploying the backend to Railway and optional frontend to Vercel.

## Railway (Backend)

1. Create a Railway project and connect this repository.
2. Add environment variables in Railway project settings (secrets):
   - `DJANGO_SECRET_KEY` - production secret
   - `DATABASE_URL` - Railway Postgres connection string
   - `GEMINI_API_KEY` - (optional) Gemini/GenAI key
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL` (optional for S3)
   - `DEBUG` = 0
3. Ensure Railway has a Postgres plugin added (Railway UI → Plugins → Postgres).
4. Build & Start
   - Railway will use the `Dockerfile` if present, or use the `Procfile` (`web` process). If your Railway project uses the repo build, ensure `build_files.sh` is executed during build (Railway / Dockerfile can call it).
5. Run migrations
   - From Railway Console or using Railway CLI: `railway run python manage.py migrate`.
6. Run collectstatic (if using WhiteNoise): `railway run python manage.py collectstatic --noinput`.

## Vercel (Frontend - Optional)

If you split a frontend (Next.js) to a separate repo, deploy to Vercel:
1. Create Vercel project and connect the frontend repo.
2. In Vercel project settings add env var `NEXT_PUBLIC_API_URL` pointing to the Railway app URL.
3. CORS: ensure backend `CORS_ALLOWED_ORIGINS` contains the Vercel domain.

## Quick Dev Deploy Tips
- Use Railway's GitHub integration to auto-deploy on merges to `main`.
- Keep secrets in Railway project settings, do not commit them.

## Rollback
- Railway supports rollback to previous deployment from the UI.

## Migrations on Deploy
- Railway can run release commands; otherwise run migrations from the Railway console after deploy.
