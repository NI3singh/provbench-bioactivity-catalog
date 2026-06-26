# ProvBench — a provenance-preserving, multi-source bioactivity catalog

> Drug-discovery ML lives or dies on data quality. The same compound, measured against the
> same protein, often disagrees by **>10×** across sources — and standard benchmarks have a
> documented history of *silently altered and fabricated* values. **ProvBench** is a small,
> rigorous answer: join bioactivity data from many upstream sources, **keep every original
> measurement linked to its origin**, flag the suspect ones (never delete them), and **prove
> with numbers** that the curation actually reduces noise.

🔗 **Live demo:** `https://provbench-web.onrender.com` · 🤗 **Dataset:** [`NI3singh/provbench-egfr-bioactivity`](https://huggingface.co/datasets/NI3singh/provbench-egfr-bioactivity) · 📦 **Deploy:** [DEPLOYMENT.md](./DEPLOYMENT.md)

*(Links go live after you run the one-time pipeline + deploy — see [DEPLOYMENT.md](./DEPLOYMENT.md).)*

---

## What it does

For one well-studied target (**EGFR**, UniProt `P00533`), ProvBench:

1. **Extracts** ~28k IC50/Ki measurements from **ChEMBL**, which aggregates them from **8 distinct
   upstream sources** (Scientific Literature, BindingDB, PubChem BioAssays, DrugMatrix, patents…).
2. **Standardizes** every structure with RDKit (desalt → neutralize → canonical) and joins
   compounds on the **standard InChIKey**.
3. **Harmonizes** units to nM / pActivity and computes a transparent **median consensus** per
   compound — while **preserving a link to every original record**.
4. **Flags** suspect values with a ChEMBL-style controlled vocabulary
   (*annotate, don't delete*): missing data, non-standard units, out-of-range, transcription errors.
5. **Quantifies quality** by reproducing the analysis of **Landrum & Riniker (2024)** — pairwise
   agreement under minimal vs. metadata-matched ("maximal") curation, plus a cross-source split.
6. **Emits machine-readable metadata**: **Croissant v1.1** (validated) with **W3C PROV-O** lineage,
   checksums, and versioning — the FAIR "nutrition label" for the dataset.

Everything is browsable in a small web app, and the dataset is published to HuggingFace.

---

## Results (from the live pipeline)

| | |
|---|---|
| Original measurements (link-preserved) | **28,689** |
| Unique compounds (standardized) | **15,507** |
| Consensus compound/target rows | **11,107** |
| Compounds with ≥2 measurements | **4,343** |
| Upstream sources represented | **8** |
| Flagged (kept, not deleted) | **2,658 (9.3%)** |

**Data-quality report (Kendall τ ↑ better, MAE ↓ better):**

| curation regime | Kendall τ | MAE (log) | reading |
|---|---|---|---|
| minimal (no metadata matching) | 0.372 | 0.948 | raw multi-assay noise |
| **maximal** (match assay metadata) | **0.401** | **0.883** | curation measurably helps |
| cross-source (different DBs) | 0.285 | 1.051 | **combining sources is noisiest** |

> The takeaway mirrors the literature: **assay metadata is the data-quality lever**, and naively
> pooling across sources is the worst thing you can do — which is exactly why provenance matters.

---

## Architecture — the offline/online split

The heavy chemistry runs **once, locally**; the deployed app is a thin read-only layer (no RDKit),
so it runs comfortably on free tiers and deploys on the first try.

```
  OFFLINE (local, Python 3.13 + RDKit)                ONLINE (Render, free)
  ┌───────────────────────────────────────┐          ┌──────────────────────────────┐
  ChEMBL API ─► extract ─► standardize ─►  │   load   │  React static site  ──fetch──►│
  (8 sources)   harmonize ─► flag ─► QC ─► ├─Supabase─┤  thin FastAPI  ──SQL──► Supabase
                  └─► Croissant + PROV-O   │          │  (+ guarded Gemini /extract)  │
                  └─► HuggingFace dataset  │          └──────────────────────────────┘
  └───────────────────────────────────────┘
```

---

## The web app (5 views)

- **Explorer** — search a compound → consensus potency + **"show the receipts"**: every original
  measurement, its source, its flag, and a link back to the source record.
- **Quality** — the Landrum–Riniker before/after charts + source / flag / agreement breakdowns.
- **Flagged** — browse every caught record and *why* it was flagged. Nothing is deleted.
- **Catalog** — the dataset "nutrition label": versions, checksum, license, sources, Croissant/PROV-O.
- **Extract** — paste assay text → an LLM extracts metadata, but **every field is gated**: it must
  cite an exact source span, pass unit/range checks, or be **rejected as a hallucination**.

### Anti-fabrication LLM module
The `/api/extract` endpoint never trusts the model. After Gemini returns structured fields, deterministic
guards (`backend/llm_guards.py`) enforce: (1) the cited `source_span` must be an exact substring of the
input, (2) units must be in a controlled vocabulary, (3) numeric values must be physically plausible,
(4) any field without evidence is dropped. Same verification discipline as the dataset curation —
pointed at messy free text.

---

## Reproduce locally

```bash
python -m venv .venv && .venv/Scripts/activate     # (source .venv/bin/activate on macOS/Linux)
pip install -r pipeline/requirements.txt
cp .env.example .env                                # add your SUPABASE_DB_URL (+ HF_TOKEN to publish)
python pipeline/run_all.py                          # extract → … → metadata (no DB needed)
python pipeline/run_all.py --load --publish         # also load Supabase + publish to HuggingFace
```

Full free deployment (Supabase + Render + HuggingFace): see **[DEPLOYMENT.md](./DEPLOYMENT.md)**.

---

## Tech stack

| Layer | Tech |
|---|---|
| Pipeline | Python 3.13, RDKit, ChEMBL REST, pandas, scipy, mlcroissant, prov |
| Database | Supabase (Postgres) |
| Backend | FastAPI, psycopg3, google-genai (Gemini) |
| Frontend | React + Vite + TypeScript (hand-rolled CSS, no framework bloat) |
| Deploy | Render (static site + web service), HuggingFace Datasets |

## Repo layout

```
pipeline/   s1..s9 — extract, standardize, harmonize, flag, QC, metadata, load, publish
backend/    thin read-only FastAPI + anti-fabrication LLM guards
frontend/   React/Vite app (Explorer, Quality, Flagged, Catalog, Extract)
render.yaml  one-click Blueprint   ·   DEPLOYMENT.md  free-tier guide
```

---

## Provenance & citations

- **ChEMBL** — Zdrazil et al., *Nucleic Acids Research* (2024). Data licensed CC BY-SA 3.0.
- **Curation / QC methodology** — Landrum & Riniker, *"Combining IC50 or Ki Values from Different
  Sources Is a Source of Significant Noise"*, *J. Chem. Inf. Model.* (2024),
  [10.1021/acs.jcim.4c00049](https://doi.org/10.1021/acs.jcim.4c00049).
- **Metadata** — MLCommons **Croissant v1.1**; W3C **PROV-O**.

Built by **[Nitin Singh](https://github.com/NI3singh)**.

## License

Code: MIT. Data: CC BY-SA 3.0 (inherited from ChEMBL); upstream sources attributed in the dataset card.
