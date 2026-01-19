**Goal:** Containerize, configure, and deploy PrepPilot across environments with automated CI/CD.

**Prompt:**

You are preparing **PrepPilot** for deployment — a full-stack web application built with Next.js (frontend) and FastAPI (backend), using Postgres (Supabase/Neon) for persistence.

### 🎯 Deployment Objectives
1. Reproducible, environment-agnostic builds.
2. Continuous deployment with minimal manual intervention.
3. Secure configuration of API keys, secrets, and environment variables.
4. Separation of staging and production environments.

### 🌍 Infrastructure Targets
- **Frontend:** Vercel  
- **Backend:** Fly.io or Render  
- **Database:** Supabase or Neon.tech (Postgres)

### 🧱 Deliverables
- **Dockerfiles** for both frontend and backend.
- **CI/CD pipeline:** GitHub Actions for build/test/deploy.
- **Environment config:** `.env.production`, `.env.staging` with secret management.
- **Health checks:** `/health` endpoint for backend, status badge for dashboard.

### 🧩 Deployment Steps
1. Build Docker images for backend and frontend.
2. Push to Fly.io registry and deploy via `fly deploy`.
3. Configure Postgres migrations automatically on deploy.
4. Use Vercel for frontend build + CDN caching.
5. Link backend API URL via Vercel environment variable.

### 🔒 Security
- Use HTTPS by default (auto TLS via Fly.io / Vercel).
- Restrict CORS to known origins.
- Encrypt secrets in GitHub Actions using OpenID Connect (no static secrets).

### 🧠 Observability (Baseline)
- Implement basic request logging and error tracking (Sentry, Logtail, or OpenTelemetry).
- Add runtime environment flag to logs (staging vs production).

### ✅ Validation
A successful deployment allows:  
- One-command rollout (`fly deploy`, `vercel --prod`).  
- Separate staging and production environments.  
- Visible health check on `/health` endpoint.
