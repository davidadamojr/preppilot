**Goal:** Design ongoing operational excellence — monitoring, maintenance, and learning loops.

**Prompt:**

You are implementing **production operations** for PrepPilot to ensure uptime, data integrity, and user trust.

### 🎯 Operational Objectives
1. Proactive detection of failures and anomalies.
2. Continuous learning from user behavior and adaptive outcomes.
3. Predictable data maintenance (freshness, ingredient decay, adaptation logs).

### 🧠 Core Systems
- **Monitoring & Alerting:**
  - Use Sentry or OpenTelemetry for backend errors.
  - Track frontend performance (Next.js Analytics, Vercel Speed Insights).
  - Set up uptime monitor (e.g., UptimeRobot or Healthchecks.io).

- **Cron & Background Tasks:**
  - Daily freshness decay task for fridge items.
  - Weekly summary email (adaptation success, time saved).
  - Cleanup job for expired user sessions and stale plans.

- **Metrics Collection:**
  - Track skipped vs adapted preps per user.
  - Time saved vs baseline (static planner).
  - Ingredient waste percentage.
  - PDF exports per week.

- **Data Backups:**
  - Automate Postgres backups via Supabase schedule.
  - Encrypt and store in offsite bucket (AWS S3 or Backblaze B2).

- **Incident Response:**
  - Slack or email alerts on API downtime or job failures.
  - Graceful fallback when adaptive engine fails (static plan recovery).

- **Continuous Improvement:**
  - Feed aggregated anonymized metrics back into adaptive model tuning.
  - Periodically retrain or recalibrate prep sequencing weights.

### 🔐 Security & Privacy
- Store only non-sensitive food and schedule data.
- Hash all user identifiers.
- GDPR-ready data export and deletion endpoints.

### ✅ Validation
Operational readiness is confirmed when:
- Failures auto-report to monitoring tools.
- Backups complete daily.
- Cron tasks execute on schedule.
- 99% uptime over 30-day rolling average.

---

### ✳️ Final Guidance for Claude Code
Deploy PrepPilot with the reliability of a production SaaS.  
Prioritize **simplicity, visibility, and safety** over complexity.  
Aim for one-command deploys, transparent monitoring, and graceful recovery.  
The system should feel calm and dependable — like the kitchen autopilot it powers.
