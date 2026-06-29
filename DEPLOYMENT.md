# Deploying ProvBench for free

This deploys the whole stack on **free tiers**: Neon (Postgres), Render (static site +
web service), and HuggingFace (dataset hosting). Total cost: **$0**.

The design that makes "free + first-try" work: the heavy RDKit pipeline runs **once on
your machine** and writes results to Neon + HuggingFace. The deployed app is a **thin
read-only API + static site** with no RDKit, so it fits Render's 512 MB free tier with no
build risk.

```
LOCAL (one-time):  pipeline ──► Neon Postgres ──► Render API ──► Render static site
                            └─► HuggingFace dataset
```

---

## 0. Prerequisites

- A GitHub account (repo: `NI3singh/provbench-bioactivity-catalog`).
- A free [Neon](https://neon.tech) account.
- A free [Render](https://render.com) account.
- (Optional) A [HuggingFace](https://huggingface.co) account + **write** token — for dataset hosting.
- (Optional) A [Google Gemini](https://aistudio.google.com/apikey) API key — for the `/extract` demo.
- Python 3.13 (or 3.12) and Node 18+ locally.

---

## 1. Create the Neon database

1. Create a new Neon project (any region). It provisions in seconds.
2. On the project dashboard, copy the **connection string** (Connect → Connection string).
   It already includes SSL and looks like:
   ```
   postgresql://<user>:<password>@<endpoint>-pooler.<region>.aws.neon.tech/<db>?sslmode=require
   ```
   The **pooled** endpoint (host contains `-pooler`) works for both the local loader and the
   deployed API. Neon requires SSL — keep `?sslmode=require`.
3. Nothing else to configure — the loader (`s8`) creates all tables.

> Neon's free compute **auto-suspends after ~5 min idle** and **auto-resumes on the next
> connection** (sub-second), so there is no manual "unpause" step.

---

## 2. Run the pipeline locally (populates Neon + HuggingFace)

```bash
# from the repo root
python -m venv .venv
.venv/Scripts/activate            # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r pipeline/requirements.txt

cp .env.example .env              # then edit .env:
#   DATABASE_URL = your Neon connection string (keep ?sslmode=require)
#   HF_TOKEN     = your HuggingFace WRITE token   (only needed for --publish)

# Extract -> standardize -> harmonize -> flag -> QC -> metadata -> load Neon -> publish HF
python pipeline/run_all.py --load --publish
```

This pulls ~28k EGFR bioactivity records, curates them, loads the tables into Neon, and
(with `--publish`) pushes the dataset + enriched Croissant to HuggingFace.
Re-runs are cached; add `--force-extract` to re-hit the source APIs.

> If RDKit fails to install on Python 3.13, create a 3.12 venv instead — nothing else changes.
> The HuggingFace dataset is created under your **HF username's** namespace (set `HF_REPO_ID`
> in `.env` to override).

---

## 3. Deploy on Render (Blueprint)

1. Push this repo to GitHub.
2. Render Dashboard → **New → Blueprint** → connect the repo. Render reads `render.yaml`
   and creates **two services**: `provbench-web` (static) and `provbench-api` (web).
3. When prompted (or in each service's **Environment** tab) set the secrets on **provbench-api**:
   - `DATABASE_URL` = your Neon connection string (keep `?sslmode=require`).
   - `GEMINI_API_KEY` = your Gemini key (only needed for the Extract page).
   - `FRONTEND_URL` defaults to `https://provbench-web.onrender.com`; the API also allows
     any `*.onrender.com` origin via CORS, so this works even if the name differs.
4. Click **Apply / Deploy**. The static site builds and the API starts.
5. **Verify the URLs.** If Render appended a suffix to a service name (because the name was
   taken), the frontend still finds the API automatically (it reads the API host via
   `fromService`). If you ever hardcode URLs, update `VITE_API_URL` and redeploy the static site.

Visit the static site URL → the Explorer should load stats and compounds from Neon.

---

## 4. Keep it warm (optional but recommended)

Render free web services spin down after ~15 min idle (30–60 s cold start), and Neon compute
auto-suspends after ~5 min idle (but auto-resumes in <1 s). To avoid a recruiter hitting a
cold demo:

- A GitHub Action is included at `.github/workflows/keepalive.yml`. In the repo:
  **Settings → Secrets and variables → Actions → Variables → New variable**
  `API_URL = https://provbench-api.onrender.com` (your actual API URL). It pings every 3h.
- Or use a free uptime pinger (e.g. cron-job.org) against `<api>/health`.

---

## 5. Free-tier limits & gotchas

| Thing | Limit | Handling |
|---|---|---|
| Render web service | 512 MB RAM, sleeps after 15 min idle | API is thin (no RDKit); static homepage absorbs cold start; keep-alive warms it |
| Render static site | always-on, free | SPA rewrite to `index.html` via `_redirects` + `render.yaml` route |
| Neon Postgres | 0.5 GB storage, compute auto-suspends ~5 min idle | Curated dataset is a few MB; auto-resumes on connect (<1 s) |
| Neon SSL | required | connection string includes `?sslmode=require`; the API also sets `prepare_threshold=None` for poolers |
| HuggingFace dataset | free public hosting | `s9` pushes data + enriched Croissant (write token required) |

---

## 6. Local development

```bash
# Backend (needs .env with DATABASE_URL; GEMINI_API_KEY optional)
cd backend && python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (in another terminal)
cd frontend && npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev      # http://localhost:5173
```
