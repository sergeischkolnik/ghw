# Environments Configuration

## Overview

GHW Bot supports two separate environments:
- **Development** (`dev`): Local testing with isolated database
- **Production** (`production`): Render bot with real user data

Each environment uses a separate SQLite database to prevent data contamination.

---

## Environment Setup

### Local Development (Your Machine)

**Configuration:**
```env
ENVIRONMENT=dev
TELEGRAM_TOKEN=your_token_here
```

**Database:** `ghw-dev.db` (created automatically)

**Usage:**
```bash
# Run locally
python main.py

# Run dashboard locally
streamlit run dashboard_v2.py
```

**Default:** If `ENVIRONMENT` is not set, defaults to `dev`.

---

### Production (Render.com)

**Configuration:**
Render environment variable:
```
ENVIRONMENT=production
TELEGRAM_TOKEN=your_real_token_here
```

**Database:** `ghw.db` (synced to GitHub, shared with Streamlit Cloud)

**Behavior:**
- Bot saves data to `ghw.db`
- Streamlit Cloud dashboard reads from the same `ghw.db`
- Data is real user workflows

---

## Database Mapping

| Environment | Bot Database | Dashboard Database | Scope |
|-------------|-------------|-------------------|-------|
| **dev** | `ghw-dev.db` | `ghw-dev.db` | Local testing only |
| **production** | `ghw.db` | `ghw.db` | Real data, synced to GitHub |

---

## How to Set Up Production

### Step 1: Add Environment Variable to Render

1. Go to https://render.com → **ghw-bot** service
2. Click **Settings** (top right)
3. Scroll to **Environment**
4. Click **Add Environment Variable**
5. Key: `ENVIRONMENT`
6. Value: `production`
7. Click **Save**
8. Service will auto-redeploy

### Step 2: Verify

1. Check Render logs (should show `[DB] Environment: PRODUCTION, Database: ghw.db`)
2. Send test message to bot via Telegram
3. Wait 60 seconds
4. Check Streamlit Cloud dashboard for new entry

---

## Local Development Workflow

### First Time Setup

```bash
# 1. Clone repo (if needed)
git clone https://github.com/sergeischkolnik/ghw.git
cd ghw

# 2. Create virtual environment
python -m venv .venv

# 3. Activate venv
# On Windows:
.venv/Scripts/activate
# On Mac/Linux:
source .venv/bin/activate

# 4. Create .env file (IMPORTANT!)
echo "ENVIRONMENT=dev" > .env
echo "TELEGRAM_TOKEN=your_token_here" >> .env

# 5. Install dependencies
pip install -r requirements-bot.txt

# 6. Run bot
python main.py
```

### Testing

```bash
# Terminal 1: Run bot
python main.py
# Should show: [DB] Environment: DEV, Database: ghw-dev.db

# Terminal 2: Run dashboard (optional)
pip install -r requirements.txt
streamlit run dashboard_v2.py
# Should show at localhost:8501
```

### Important Notes

- **.env is NOT committed** to git (for security)
- `ghw-dev.db` is NOT committed (for cleanliness)
- Only `ghw.db` (production data) is committed in git
- Each developer has their own `ghw-dev.db` locally

---

## Environment Variables Reference

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `ENVIRONMENT` | No | `dev` | Set to `production` on Render |
| `TELEGRAM_TOKEN` | Yes | - | Get from @BotFather |
| `PORT` | No | `10000` | For health check server (Render sets this) |

---

## Troubleshooting

### Bot not using correct environment

Check logs:
- **Dev**: Should show `[DB] Environment: DEV, Database: ghw-dev.db`
- **Production**: Should show `[DB] Environment: PRODUCTION, Database: ghw.db`

### Dashboard not showing new data

1. **Local dev**: Dashboard reads from `ghw-dev.db`, bot writes to `ghw-dev.db` ✅
2. **Production**: Streamlit Cloud reads from committed `ghw.db`, but bot (Render) is writing to its own `ghw.db` ❌
   - **Solution**: Commit changes to `ghw.db` or set up automatic sync

### Missing .env file

Create it locally:
```bash
echo "ENVIRONMENT=dev" > .env
echo "TELEGRAM_TOKEN=your_token" >> .env
```

---

## Git Workflow

### For Developers

```bash
# Don't commit .env
git checkout -- .env.example

# Don't commit local dev database
echo "ghw-dev.db" >> .gitignore

# Only production database is committed
git add ghw.db
git commit -m "data: update production database"
```

### Files NOT Committed

- `.env` (contains sensitive tokens)
- `ghw-dev.db` (local testing data)
- `.venv/` (virtual environment)

### Files COMMITTED

- `ghw.db` (production database)
- `requirements.txt` and `requirements-bot.txt` (dependencies)
- All source code
