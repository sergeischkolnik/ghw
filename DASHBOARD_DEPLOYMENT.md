# Deployment Guide: Bot + Dashboard

## Architecture

```
┌─────────────────────────────────────┐
│   GitHub Repository (ghw)           │
├─────────────────────────────────────┤
│ main.py               (Bot code)     │
│ dashboard_v2.py       (Dashboard UI) │
│ ghw.db                (SQLite data)  │
│                                     │
│ requirements.txt      (Bot deps)    │
│ requirements-dashboard.txt (UI deps)│
└─────────────────────────────────────┘
        ↓                    ↓
┌──────────────────┐  ┌──────────────────┐
│  Render.com      │  │ Streamlit Cloud  │
│  (Bot Polling)   │  │ (Dashboard UI)   │
└──────────────────┘  └──────────────────┘
```

## 1. Telegram Bot - Render.com Deployment

### Files Used
- `main.py` (bot code)
- `db.py` (database functions)
- `requirements.txt` (bot dependencies only)
- `Procfile` (tells Render how to run)

### Installation Steps in Render

1. Push code to GitHub with commit
2. Render watches repo, auto-detects `requirements.txt`
3. **Installs ONLY**: `python-telegram-bot`, `aiosqlite`, `python-dotenv`
4. Runs: `python -u main.py`
5. Bot connects to Telegram API and starts polling

### Key Files
```
requirements.txt (for Render)
├── python-telegram-bot==21.1
├── aiosqlite==0.21.0
└── python-dotenv==1.0.0
```

**Total install time**: ~20-30 seconds (fast, no pandas/plotly overhead)

---

## 2. Dashboard - Streamlit Cloud Deployment

### Files Used
- `dashboard_v2.py` (dashboard code)
- `ghw.db` (SQLite database with data)
- `requirements-dashboard.txt` (dashboard dependencies)

### Installation Steps in Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click **New app**
3. Select repo: `sergeischkolnik/ghw`
4. Main file path: `dashboard_v2.py`
5. Click **Advanced settings** ⚙️
6. Set **Requirements file** to: `requirements-dashboard.txt`
7. Click **Deploy**

### Key Files
```
requirements-dashboard.txt (for Streamlit Cloud)
├── streamlit>=1.32.0
├── plotly>=5.18.0
└── pandas>=2.1.0
```

**Total install time**: ~60-90 seconds (longer due to pandas/plotly build)

---

## 3. Testing Deployment Compatibility

### Test Bot Locally
```bash
# Ensure venv has bot deps only
pip install -q -r requirements.txt
python main.py
# Should start in <2 seconds
```

### Test Dashboard Locally
```bash
# Ensure venv has dashboard deps
pip install -q -r requirements-dashboard.txt
streamlit run dashboard_v2.py
# Should load at http://localhost:8501
```

### Test in CI/CD
Both deployment environments install from their respective requirements files:
- Render: `requirements.txt` (bot fast)
- Streamlit Cloud: `requirements-dashboard.txt` (dashboard full)

No file conflicts because each platform manages its own dependencies.

---

## 4. Troubleshooting

### Bot times out on Render
- ❌ Problem: `requirements.txt` has pandas/plotly (too slow)
- ✅ Solution: Keep `requirements.txt` bot-only (3 packages)
- 🔍 Check: `git show HEAD:requirements.txt` should only have telegram-bot, aiosqlite, dotenv

### Dashboard fails on Streamlit Cloud
- ❌ Problem: Using wrong requirements file
- ✅ Solution: Specify `requirements-dashboard.txt` in Advanced Settings
- 🔍 Check: Streamlit app's "Manage app" → "Settings" shows correct requirements file

### Database not loading in Streamlit
- ❌ Problem: `ghw.db` not tracked in git
- ✅ Solution: `git ls-files | grep ghw.db` should show the file
- 🔍 Check: File exists at `/mount/src/ghw/ghw.db` in Streamlit Cloud logs

---

## 5. Quick Deployment Checklist

### Before pushing to GitHub
- [ ] `requirements.txt` has ONLY bot dependencies (3 lines)
- [ ] `requirements-dashboard.txt` has dashboard dependencies (3 lines)
- [ ] `ghw.db` is committed (`git ls-files | grep ghw.db`)
- [ ] `main.py` has no syntax errors (`python -m py_compile main.py`)
- [ ] `dashboard_v2.py` works locally (`streamlit run dashboard_v2.py`)

### After git push
- [ ] Render auto-deploys and bot shows "running" (not "timed out")
- [ ] Streamlit Cloud imports `requirements-dashboard.txt` correctly
- [ ] Both services are "healthy" in their respective dashboards

---

## Summary

| Aspect | Render (Bot) | Streamlit (Dashboard) |
|--------|--------------|----------------------|
| Requirements file | `requirements.txt` | `requirements-dashboard.txt` |
| Build time | ~20-30s | ~60-90s |
| Packages | 3 (fast) | 3 (heavier) |
| Python version | 3.12 | 3.14+ |
| Data source | Telegram API | SQLite (ghw.db) |
| Deployment | Auto from GitHub | Manual via UI |
| Configuration | `Procfile` | Advanced Settings |

