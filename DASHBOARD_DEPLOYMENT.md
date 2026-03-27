# Dashboard Deployment Guide

## Local Testing

```bash
streamlit run dashboard_v2.py
```

Then open http://localhost:8501

## Streamlit Cloud Deployment

The dashboard is ready to deploy to Streamlit Cloud (free tier). Steps:

1. Go to https://streamlit.io/cloud
2. Click "New app"
3. Connect your GitHub repo (`sergeischkolnik/ghw`)
4. Configure:
   - **Repository**: sergeischkolnik/ghw
   - **Branch**: main
   - **Main file path**: `dashboard_v2.py`
5. In **Advanced settings**:
   - Set **Python version**: 3.11
   - Set **Requirements file**: `requirements-dashboard.txt`
6. Click "Deploy"

## Data Source

The dashboard reads from:
- `ghw.db` (local SQLite database)
- Tables: `taller_outputs`, `servicio_outputs`

**Note**: In Streamlit Cloud, the database won't be automatically synced. You'll need to either:
- A) Upload `ghw.db` to GitHub (if not sensitive)
- B) Modify dashboard to connect to a cloud database (PostgreSQL, etc.)
- C) Generate test data in cloud environment

Currently, the dashboard will show an empty state on Streamlit Cloud until a database is provided.

## Alternatives

If you want live data in the cloud:
- Option 1: Commit `ghw.db` to git (simple but not ideal for large files)
- Option 2: Connect to a cloud PostgreSQL database instead of SQLite
- Option 3: Use Streamlit's cloud database support (managed by Streamlit)
