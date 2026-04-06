# Render Polling Runbook

## Objective
Keep the Telegram polling bot alive in Render and recover automatically from transient errors.

## What Was Hardened
- Added strict startup validation for `TELEGRAM_TOKEN` and `DATABASE_URL`.
- Added polling supervisor loop with exponential backoff restart (5s -> 60s).
- Added missing PostgreSQL query helpers used by `/export_workflows`.
- Aligned deployment metadata:
  - `render.yaml` now declares `DATABASE_URL` and `TELEGRAM_TOKEN`.
  - `Procfile` set to `web: python -u main.py`.

## Required Render Configuration
1. Service type: Web service
2. Build command: `bash build.sh`
3. Start command: `python -u main.py`
4. Environment variables:
   - `TELEGRAM_TOKEN`
   - `DATABASE_URL`

## Expected Healthy Logs
On startup you should see:
- `Validating environment variables`
- `Database initialized successfully`
- `Health check server started on port ...`
- `Bot is starting polling supervisor`
- `Entering polling mode`

If polling drops, you should see:
- `Polling error: ...`
- `Restarting polling in X seconds...`

## Validation Steps After Deploy
1. Open Render logs and confirm startup sequence above.
2. Call `/health` on the service URL and confirm HTTP 200.
3. Send `/start` to the Telegram bot.
4. Complete a sample workflow.
5. Optionally run `/export_workflows all 10` and verify JSON export succeeds.

## Failure Triage
- Missing `DATABASE_URL`: startup fails fast with explicit error.
- Missing `TELEGRAM_TOKEN`: startup fails fast with explicit error.
- Postgres connectivity issue: startup fails in DB init step.
- Telegram transient API/network issue: supervisor loop retries automatically.
