# Deploying ProvBench for free

This deploys the whole stack on **free tiers**: Supabase (Postgres), Render (static
site + web service), and HuggingFace (dataset hosting). Total cost: **$0**.

The design that makes "free + first-try" work: the heavy RDKit pipeline runs **once on
your machine** and writes results to Supabase + HuggingFace. The deployed app is a
**thin read-only API + static site** with no RDKit, so it fits Render's 512 MB free tier
with no build risk.

```
LOCAL (one-time):  pipeline ──► Supabase Postgres ──► Render API ──► Render static site
                            └─► HuggingFace dataset
```

---

## 0. Prerequisites

- A GitHub account (repo already pushed to `NI3singh/provbench-bioactivity-catalog`).
- A free [Supabase](https://supabase.com) account.
- A free [Render](https://render.com) account.
- (Optional) A [HuggingFace](https://huggingface.co) account + write token — for dataset hosting.
- (Optional) A [Google Gemini](https://aistudio.google.com/apikey) API key — for the `/extract` demo.
- Python 3.13 (or 3.12) and Node 18+ locally.

---

## 1. Create the Supabase database

1. Create a new Supabase project (any region close to you). Wait for it to provision.
2. Go to **Project Settings → Database → Connection string → "Connection pooling"**.
   Copy the **pooler** URI. It looks like:
   ```
   postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```
   - **Port 5432** = *Session* pooler — use this for the local data load (it supports `COPY`).
   - **Port 6543** = *Transaction* pooler — use this for the deployed API.
   > ⚠️ Do **not** use the direct `db.<ref>.supabase.co` host — it is IPv6-only and Render can't reach it.
3. There is nothing to click for the schema — the loader (`s8`) creates all tables.

---

## 2. Run the pipeline locally (populates Supabase + HuggingFace)

```bash
# from the repo root
python -m venv .venv
.venv/Scripts/activate            # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r pipeline/requirements.txt

cp .env.example .env              # then edit .env:
#   SUPABASE_DB_URL = the Session pooler URI (port 5432)
#   HF_TOKEN        = your HuggingFace write token   (only needed for --publish)

# Extract -> standardize -> harmonize -> flag -> QC -> metadata -> load Supabase -> publish HF
python pipeline/run_all.py --load --publish
```

This pulls ~28k EGFR bioactivity records, curates them, loads the tables into Supabase,
and (with `--publish`) pushes the dataset + enriched Croissant to HuggingFace.
Re-runs are cached; add `--force-extract` to re-hit the source APIs.

> If RDKit fails to install on Python 3.13, create a 3.12 venv instead — nothing else changes.

---

## 3. Deploy on Render (Blueprint)

1. Push this repo to GitHub (already done).
2. Render Dashboard → **New → Blueprint** → connect the repo. Render reads `render.yaml`
   and creates **two services**: `provbench-web` (static) and `provbench-api` (web).
3. When prompted (or in each service's **Environment** tab) set the secrets:
   - On **provbench-api**:
     - `SUPABASE_DB_URL` = the **Transaction** pooler URI (port **6543**).
     - `GEMINI_API_KEY` = your Gemini key (only needed for the Extract page).
   - `FRONTEND_URL` defaults to `https://provbench-web.onrender.com`; the API also allows
     any `*.onrender.com` origin via CORS, so this works even if the name differs.
4. Click **Apply / Deploy**. The static site builds and the API starts.
5. **Verify the URLs.** If Render appended a suffix to a service name (because the name was
   taken), the frontend still finds the API automatically (it reads the API host via
   `fromService`). If you ever hardcode URLs, update `VITE_API_URL` and redeploy the static site.

Visit the static site URL → the Explorer should load stats and compounds from Supabase.

---

## 4. Keep it warm (optional but recommended)

Free tiers sleep: Render web services spin down after ~15 min idle (30–60 s cold start),
and Supabase projects pause after **7 idle days**. To avoid a recruiter hitting a cold/paused
demo:

- A GitHub Action is included at `.github/workflows/keepalive.yml`. In the repo:
  **Settings → Secrets and variables → Actions → Variables → New variable**
  `API_URL = https://provbench-api.onrender.com` (your actual API URL). It pings every 3h.
- Or use a free uptime pinger (e.g. cron-job.org) against `/<api>/health`.

---

## 5. Free-tier limits & gotchas

| Thing | Limit | Handling |
|---|---|---|
| Render web service | 512 MB RAM, sleeps after 15 min idle | API is thin (no RDKit); static homepage absorbs cold start; keep-alive warms it |
| Render static site | always-on, free | SPA rewrite to `index.html` via `_redirects` + `render.yaml` route |
| Supabase DB | 500 MB, pauses after 7 idle days | Curated dataset is a few MB; keep-alive prevents pause |
| Supabase pooler | use pooler host (IPv4) | API sets `prepare_threshold=None` for the transaction pooler |
| HuggingFace dataset | free public hosting | `s9` pushes data + enriched Croissant |

---

## 6. Local development

```bash
# Backend (needs .env with SUPABASE_DB_URL; GEMINI_API_KEY optional)
cd backend && python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (in another terminal)
cd frontend && npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev      # http://localhost:5173
```
