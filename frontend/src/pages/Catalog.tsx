import { useEffect, useState } from "react";
import { api } from "../api";
import { ErrorNote, Loading } from "../components/Bits";

export default function Catalog() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.catalog().then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <ErrorNote msg={err} />;
  if (!d) return <Loading />;

  const m = d.meta || {};
  const t = d.target || {};
  const hf = m.hf_url;
  const repo = "https://github.com/NI3singh/provbench-bioactivity-catalog";

  return (
    <div>
      <h1 className="page-title">Dataset catalog</h1>
      <p className="page-sub">
        The machine-readable “nutrition label”: what this dataset is, where it came from, and how to verify it.
        Metadata is emitted as <strong>Croissant v1.1</strong> with <strong>W3C PROV-O</strong> lineage.
      </p>

      <div className="grid cols-2">
        <div className="card accent-top">
          <h2 className="section" style={{ marginTop: 0 }}>{m.name || "provbench-egfr-bioactivity"}</h2>
          <dl className="kvs">
            <dt>Version</dt><dd>{m.version}</dd>
            <dt>Created</dt><dd>{m.created_at}</dd>
            <dt>Target</dt><dd>{t.pref_name} <span className="muted">({t.uniprot} · {t.chembl_id})</span></dd>
            <dt>Compounds</dt><dd>{m.n_compounds?.toLocaleString()}</dd>
            <dt>Consensus rows</dt><dd>{m.n_consensus_records?.toLocaleString()}</dd>
            <dt>Source records</dt><dd>{m.n_source_records?.toLocaleString()}</dd>
            <dt>License</dt><dd>{m.license}</dd>
            <dt>SHA-256</dt><dd className="mono small" style={{ wordBreak: "break-all" }}>{m.sha256_consensus}</dd>
          </dl>
        </div>

        <div className="card">
          <h2 className="section" style={{ marginTop: 0 }}>Upstream sources</h2>
          <p className="small muted">Genuine multi-source provenance — every record keeps its origin.</p>
          <div className="chip-list">
            {(m.sources || []).map((s: string) => <span key={s} className="badge src">{s}</span>)}
          </div>

          <h2 className="section">Machine-readable metadata</h2>
          <div className="row">
            {hf && <a className="btn ghost" href={`${hf}/resolve/main/croissant.json`} target="_blank" rel="noreferrer">Croissant v1.1 (enriched)</a>}
            {hf && <a className="btn ghost" href={`${hf}/resolve/main/provenance.json`} target="_blank" rel="noreferrer">PROV-O lineage</a>}
          </div>
          <p className="small muted mt">
            Note: HuggingFace also auto-generates a Croissant, but it only captures column types — ours adds
            assay/source provenance + lineage.
          </p>

          <h2 className="section">Links</h2>
          <div className="row">
            {hf && <a className="btn" href={hf} target="_blank" rel="noreferrer">HuggingFace dataset ↗</a>}
            <a className="btn ghost" href={repo} target="_blank" rel="noreferrer">GitHub repo ↗</a>
          </div>
        </div>
      </div>
    </div>
  );
}
