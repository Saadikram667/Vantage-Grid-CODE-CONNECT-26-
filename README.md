# Last Hour

Structure: `api/index.py` (FastAPI `app`), `api/engine.py` (priority engine), `templates/`, `vercel.json`, `requirements.txt`.

## Run locally
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python -m uvicorn api.index:app --reload      # http://127.0.0.1:8000

## Deploy to Vercel
    npm i -g vercel
    vercel login
    vercel --prod

Or push to GitHub and import the repo at vercel.com/new. No build settings are needed.

Note: registrations and check-ins live in memory, so serverless instances reset them. Swap `engine.HOUSEHOLDS` for a database (Vercel Postgres/KV) to persist.
