# Operations Check-in — live dashboard (Railway)

A small web service that serves the **Store Health** + **Client Churn** dashboard, querying
the Icarus MariaDB **live** on each load (10-min cache). Per-user login. No Mac, no Claude
session, no weekly hook — it's always current.

- `Store Health` — active stores per media buyer, tenure, recent €/day vs the €1,000/day rule.
- `Client Churn` — this year's client churn per buyer, from `monday_activity_log`
  (`type='Churned Client'`), **auto-deduplicated** by client + date.

## Files
`app.py` (FastAPI + login) · `data.py` (DB queries) · `render.py` (HTML) ·
`gen_password.py` (make account hashes) · `Dockerfile` · `railway.json` · `.env.example`

## One-time setup

### 1. Create a read-only database user (recommended)
The service only runs `SELECT`s. Give it a read-only account so a leak can't change data:
```sql
CREATE USER 'ops_dashboard'@'%' IDENTIFIED BY 'a-strong-password';
GRANT SELECT ON icarus_db_01.* TO 'ops_dashboard'@'%';
```

### 2. Make your login accounts
Run locally (needs nothing but Python):
```bash
python3 gen_password.py kyra
```
It prints a `USERS={...}` line. Repeat per teammate and merge into one JSON object.

### 3. Deploy to Railway
Either connect this folder as a GitHub repo in the Railway dashboard, or from the CLI:
```bash
cd ops-dashboard-railway
railway login
railway init          # create a new project
railway up            # build + deploy the Dockerfile
```

### 4. Set the service Variables (Railway → your service → Variables)
```
DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE   # use the read-only user
SESSION_SECRET      # openssl rand -hex 32
USERS               # the merged JSON from step 2
COOKIE_SECURE=true
```
Then open the Railway URL, sign in, and you're live. Generate a domain under
Settings → Networking if you want a nicer URL.

## Local test
```bash
cp .env.example .env      # fill in real values; COOKIE_SECURE=false for http
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

## Notes
- **Impact-Call flags are intentionally not here** — those come from Fathom/Monday curation,
  not the database, so they can't be live. Keep the flagged view in the Claude-updated artifact.
- Health check: `/healthz` (unauthenticated, returns `ok`).
- Never commit `.env`. Secrets live in Railway Variables only.
