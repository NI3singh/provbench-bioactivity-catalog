"""ProvBench API — thin, read-only FastAPI over the curated Postgres (Neon) tables,
plus one guarded LLM extraction endpoint. No RDKit here (it ran offline).

The root path serves a small self-contained landing page (mirrors the frontend's
scientific palette). Putting THIS url in a resume warms the API first; the "Open the
Explorer" button then wakes the static frontend — so both are live by the time anyone
clicks through (Render free tier spins services down when idle)."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

import db
from routers import catalog, compounds, extract, flags, qc


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db.pool.open(wait=False)
    except Exception as e:  # don't crash startup if the DB is briefly unreachable
        print("DB pool open warning:", e)
    yield
    try:
        db.pool.close()
    except Exception:
        pass


app = FastAPI(title="ProvBench API",
              description="Provenance-preserving multi-source bioactivity catalog.",
              version="1.0.0", lifespan=lifespan)

_frontend = os.getenv("FRONTEND_URL", "http://localhost:5173")
FRONTEND_PUBLIC = os.getenv("FRONTEND_URL", "https://provbench-web.onrender.com")
GITHUB_URL = os.getenv("GITHUB_URL", "https://github.com/NI3singh/provbench-bioactivity-catalog")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend, "http://localhost:5173", "http://localhost:3000",
                   "http://127.0.0.1:5173"],
    allow_origin_regex=r"https://.*\.onrender\.com",  # any Render static-site host
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compounds.router)
app.include_router(flags.router)
app.include_router(qc.router)
app.include_router(catalog.router)
app.include_router(extract.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/stats")
def stats():
    def n(sql):
        row = db.query_one(sql)
        return row["n"] if row else 0
    return {
        "compounds": n("select count(*) as n from compounds"),
        "source_records": n("select count(*) as n from source_records"),
        "consensus": n("select count(*) as n from consensus"),
        "flagged": n("select count(*) as n from source_records where validity_flag is not null"),
        "sources": db.query(
            "select source, count(*) as n from source_records group by source order by n desc"),
        "target": db.query_one("select * from targets limit 1"),
    }


@app.get("/", response_class=HTMLResponse, tags=["meta"])
def home():
    return (_LANDING_HTML
            .replace("__FRONTEND_URL__", FRONTEND_PUBLIC)
            .replace("__GITHUB_URL__", GITHUB_URL))


# ── Landing page ─────────────────────────────────────────────────────────────
# Self-contained mirror of the ProvBench frontend theme (frontend/src/index.css):
#   - light "scientific data" palette (--bg #f6f7f9 … --ink #16202e, teal --accent
#     #0f766e, --indigo #4338ca), system/Jakarta sans + JetBrains Mono.
#   - a clean white-greenish background (soft teal/green orbs + faint mesh + grid);
#     no drifting glyphs, no cursor interaction.
#   - a provenance-graph logo mark (many sources -> one consensus node).
#   - "Open the Explorer" + "Star on GitHub" CTAs and an animated star.
# Dependency-free except one Google-fonts link, so it ships with the backend.
_LANDING_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ProvBench API Live</title>
<meta name="description" content="The ProvBench API is live. Open the Explorer to browse a provenance-preserving, multi-source EGFR bioactivity catalog.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Crect width='48' height='48' rx='12' fill='%23ffffff'/%3E%3Crect x='1.5' y='1.5' width='45' height='45' rx='12.5' fill='none' stroke='%230f766e' stroke-opacity='0.5' stroke-width='1.5'/%3E%3Cg stroke='%230f766e' stroke-opacity='0.55' stroke-width='1.6'%3E%3Cpath d='M15 14 31 24'/%3E%3Cpath d='M15 24h16'/%3E%3Cpath d='M15 34 31 24'/%3E%3C/g%3E%3Ccircle cx='15' cy='14' r='3.1' fill='%234338ca'/%3E%3Ccircle cx='15' cy='24' r='3.1' fill='%230f766e'/%3E%3Ccircle cx='15' cy='34' r='3.1' fill='%234338ca'/%3E%3Ccircle cx='31' cy='24' r='4.4' fill='%230f766e'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg:          #f6f7f9;
    --panel:       #ffffff;
    --ink:         #16202e;
    --muted:       #64748b;
    --line:        #e4e8ee;
    --line-strong: #cbd5e1;
    --accent:      #0f766e;
    --accent-soft: #ccfbf1;
    --accent-ink:  #115e59;
    --accent-lt:   #0d9488;
    --indigo:      #4338ca;
    --slate:       #475569;
  }

  html { scroll-behavior: smooth; }
  html, body { overflow-x: hidden; }

  body {
    min-height: 100vh;
    background: var(--bg);
    color: var(--ink);
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    position: relative; padding: 48px 24px;
  }

  .atmosphere { position: fixed; inset: 0; z-index: 1; overflow: hidden; pointer-events: none; }
  .orb { position: absolute; border-radius: 50%; filter: blur(80px); will-change: transform; }
  .orb-teal   { width: 660px; height: 660px; background: rgba(15,118,110,0.10);  top: -200px; left: -220px; }
  .orb-indigo { width: 520px; height: 520px; background: rgba(16,185,129,0.06);  bottom: -160px; right: -180px; }
  .mesh { position: absolute; inset: 0; background: radial-gradient(60% 50% at 50% 42%, rgba(15,118,110,0.08), transparent 70%); }
  .grid {
    position: absolute; inset: 0; opacity: 0.5;
    background-image:
      linear-gradient(rgba(100,116,139,0.10) 1px, transparent 1px),
      linear-gradient(90deg, rgba(100,116,139,0.10) 1px, transparent 1px);
    background-size: 64px 64px;
    -webkit-mask-image: radial-gradient(ellipse 70% 60% at 50% 45%, black, transparent 75%);
    mask-image: radial-gradient(ellipse 70% 60% at 50% 45%, black, transparent 75%);
  }
  .watermark {
    position: absolute; top: 3rem; right: -1rem; line-height: 1; user-select: none;
    color: rgba(15,118,110,0.05); font-size: clamp(12rem, 28vw, 24rem);
    animation: floaty 7s ease-in-out infinite;
  }
  .backdrop {
    position: fixed; inset: 0; z-index: 2; pointer-events: none;
    background: radial-gradient(ellipse 54% 50% at 50% 50%, rgba(246,247,249,0.78), transparent 72%);
  }
  .grain::after {
    content: ''; position: fixed; inset: 0; z-index: 100; pointer-events: none; opacity: 0.5;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.025'/%3E%3C/svg%3E");
  }

  .wrap { position: relative; z-index: 10; width: 100%; max-width: 640px; text-align: center;
          display: flex; flex-direction: column; align-items: center; }

  .logo { display: inline-flex; align-items: center; gap: 11px; margin-bottom: 38px;
          text-decoration: none; user-select: none; }
  .logo svg { display: block; }
  .logo-name { font-weight: 800; font-size: 1.5rem; letter-spacing: -0.03em; color: var(--ink); white-space: nowrap; }
  .logo-name .b { color: var(--accent-ink); }

  .badge {
    display: inline-flex; align-items: center; gap: 9px; padding: 6px 14px; border-radius: 999px;
    border: 1px solid rgba(15,118,110,0.25); background: rgba(15,118,110,0.07); color: var(--accent-ink);
    font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500;
    letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 28px;
  }
  .ping { position: relative; display: inline-flex; height: 7px; width: 7px; }
  .ping .wave { position: absolute; inset: 0; border-radius: 999px; background: var(--accent); opacity: 0.75;
                animation: ping 1.6s cubic-bezier(0,0,0.2,1) infinite; }
  .ping .dot  { position: relative; display: inline-flex; height: 7px; width: 7px; border-radius: 999px; background: var(--accent); }

  h1 {
    font-weight: 800; font-size: clamp(2.7rem, 6.5vw, 4.6rem); line-height: 1.06;
    letter-spacing: -0.035em; color: var(--ink); text-wrap: balance; margin-bottom: 20px;
  }
  h1 .shimmer {
    background: linear-gradient(90deg, #0f766e 0%, #10b981 42%, #0d9488 60%, #0f766e 100%);
    background-size: 200% auto; -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent; animation: shimmer 4.5s linear infinite;
  }

  .subtitle {
    font-size: 1.0625rem; font-weight: 400; color: rgba(22,32,46,0.66); line-height: 1.7;
    max-width: 466px; margin: 0 auto 34px; text-wrap: balance;
  }
  .subtitle strong { color: var(--ink); font-weight: 600; }

  .rule { width: 100%; max-width: 280px; height: 1px; margin: 0 auto 34px;
          background: linear-gradient(90deg, transparent, rgba(15,118,110,0.45), transparent); }

  .actions { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; margin-bottom: 44px; }
  .btn {
    display: inline-flex; align-items: center; gap: 8px; text-decoration: none; border-radius: 12px;
    font-family: inherit; font-size: 0.92rem; font-weight: 600; padding: 12px 24px; cursor: pointer;
    transition: transform .2s ease, background .2s ease, border-color .2s ease, color .2s ease, box-shadow .2s ease;
  }
  .btn-primary { background: var(--accent); color: #fff; border: 1px solid var(--accent);
                 box-shadow: 0 2px 12px rgba(15,118,110,0.25); }
  .btn-primary:hover { background: var(--accent-lt); border-color: var(--accent-lt);
                       transform: translateY(-2px); box-shadow: 0 6px 22px rgba(15,118,110,0.38); }
  .btn-primary .arr { transition: transform .2s ease; }
  .btn-primary:hover .arr { transform: translateX(3px); }
  .btn-ghost { background: var(--panel); color: var(--slate); border: 1px solid var(--line-strong); }
  .btn-ghost:hover { border-color: rgba(15,118,110,0.35); color: var(--ink);
                     background: rgba(15,118,110,0.05); transform: translateY(-2px); }

  .note { font-size: 0.78rem; font-weight: 400; color: var(--muted); line-height: 1.7; max-width: 400px; }
  .note code { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--accent-ink); }

  @keyframes rise   { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
  .logo     { animation: rise .6s ease both .05s; }
  .badge    { animation: rise .6s ease both .14s; }
  h1        { animation: rise .6s ease both .22s; }
  .subtitle { animation: rise .6s ease both .32s; }
  .rule     { animation: rise .6s ease both .40s; }
  .actions  { animation: rise .6s ease both .46s; }
  .note     { animation: rise .6s ease both .54s; }

  @keyframes shimmer { from { background-position: -200% center; } to { background-position: 200% center; } }
  @keyframes ping    { 75%, 100% { transform: scale(2.4); opacity: 0; } }
  @keyframes floaty  { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }

  .star-anim { display: inline-block; vertical-align: -0.18em; width: 1.05em; height: 1.05em;
               animation: star-spin 3.5s ease-in-out infinite; filter: drop-shadow(0 0 3px rgba(15,118,110,0.5)); }
  @keyframes star-spin {
    0%   { transform: scale(1)   rotate(0deg);   filter: drop-shadow(0 0 2px rgba(15,118,110,0.4)); }
    25%  { transform: scale(1.35) rotate(72deg);  filter: drop-shadow(0 0 9px rgba(16,185,129,0.7)); }
    50%  { transform: scale(1)   rotate(144deg); filter: drop-shadow(0 0 2px rgba(15,118,110,0.4)); }
    75%  { transform: scale(1.35) rotate(216deg); filter: drop-shadow(0 0 9px rgba(16,185,129,0.7)); }
    100% { transform: scale(1)   rotate(360deg); filter: drop-shadow(0 0 2px rgba(15,118,110,0.4)); }
  }

  @media (max-width: 768px) { .watermark { display: none; } }
  @media (max-width: 480px) {
    .actions { flex-direction: column; align-items: stretch; width: 100%; max-width: 300px; }
    .btn { justify-content: center; }
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
  }
</style>
</head>
<body class="grain">

  <div class="atmosphere" aria-hidden="true">
    <div class="orb orb-teal"></div>
    <div class="orb orb-indigo"></div>
    <div class="mesh"></div>
    <div class="grid"></div>
    <div class="watermark">&#9001;</div>
  </div>
  <div class="backdrop" aria-hidden="true"></div>

  <main class="wrap">

    <a class="logo" href="__FRONTEND_URL__" aria-label="ProvBench home">
      <svg width="40" height="40" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <rect x="1.5" y="1.5" width="45" height="45" rx="12.5" fill="#ffffff" stroke="#0f766e" stroke-opacity="0.32" stroke-width="1.5"/>
        <circle cx="31" cy="24" r="8" fill="#0f766e" opacity="0.10"/>
        <g stroke="#0f766e" stroke-opacity="0.55" stroke-width="1.6" fill="none">
          <path d="M15 14 L31 24"/><path d="M15 24 L31 24"/><path d="M15 34 L31 24"/>
        </g>
        <circle cx="15" cy="14" r="3.1" fill="#4338ca"/>
        <circle cx="15" cy="24" r="3.1" fill="#0f766e"/>
        <circle cx="15" cy="34" r="3.1" fill="#4338ca"/>
        <circle cx="31" cy="24" r="4.6" fill="#0f766e"/>
      </svg>
      <span class="logo-name">Prov<span class="b">Bench</span></span>
    </a>

    <div class="badge">
      <span class="ping"><span class="wave"></span><span class="dot"></span></span>
      API Online
    </div>

    <h1>Thanks for<br><span class="shimmer">stopping by.</span></h1>

    <p class="subtitle">
      The <strong>ProvBench API</strong> is live, serving a provenance-preserving,
      multi-source EGFR bioactivity catalog. <strong>Open the Explorer</strong> to browse
      the data &mdash; every value traced back to its source &mdash; and if it helps you, a
      <svg class="star-anim" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-label="star">
        <defs><linearGradient id="sg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#10b981"/><stop offset="55%" stop-color="#0d9488"/><stop offset="100%" stop-color="#0f766e"/>
        </linearGradient></defs>
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="url(#sg)"/>
      </svg>
      on GitHub means a lot.
    </p>

    <div class="rule"></div>

    <div class="actions">
      <a class="btn btn-primary" href="__FRONTEND_URL__" target="_blank" rel="noopener">
        Open the Explorer
        <svg class="arr" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
          <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </a>
      <a class="btn btn-ghost" href="__GITHUB_URL__" target="_blank" rel="noopener">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" stroke="none" aria-hidden="true">
          <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
        </svg>
        Star on GitHub
      </a>
    </div>

    <p class="note">
      First visit? Render's free tier may take <code>~30s</code> to wake each service. This page means
      the API is up &mdash; the Explorer may need a few more seconds when you open it.
    </p>

  </main>

</body>
</html>
"""
