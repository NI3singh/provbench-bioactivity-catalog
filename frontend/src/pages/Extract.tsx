import { useState } from "react";
import { api } from "../api";

const EXAMPLE = `Compound 12a inhibited EGFR kinase with an IC50 of 3.4 nM in a cell-based assay,
showing comparable potency to gefitinib (IC50 = 2 nM). The Ki against wild-type EGFR was 0.8 nM.
The compound was tested in human A431 cells.`;

export default function Extract() {
  const [text, setText] = useState(EXAMPLE);
  const [res, setRes] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function run() {
    setLoading(true); setErr(""); setRes(null);
    try { setRes(await api.extract(text)); }
    catch (e: any) { setErr(e.message); }
    finally { setLoading(false); }
  }

  return (
    <div>
      <h1 className="page-title">Guarded extraction <span className="muted" style={{ fontSize: 15, fontWeight: 500 }}>· LLM + anti-fabrication</span></h1>
      <p className="page-sub">
        An LLM (Gemini) extracts assay metadata from free text — but it is <strong>never trusted directly</strong>.
        Every field must cite an <strong>exact source span</strong> from the passage; units are validated and values
        range-checked; anything unsupported is <strong>rejected as a possible hallucination</strong>. This is the same
        verification discipline applied to the curated dataset, pointed at messy literature text.
      </p>

      <textarea className="input" value={text} onChange={(e) => setText(e.target.value)} />
      <div className="row mt">
        <button className="btn" onClick={run} disabled={loading}>{loading ? "Extracting…" : "Extract & verify"}</button>
        <button className="btn ghost" onClick={() => setText(EXAMPLE)}>Reset example</button>
      </div>

      {err && (
        <div className="notice mt">
          {err}
          <div className="small mt" style={{ color: "inherit" }}>
            The server needs a <code>GEMINI_API_KEY</code> configured for this endpoint.
          </div>
        </div>
      )}

      {res && (
        <div className="mt">
          <div className="banner mb">
            Gemini returned <strong>{res.n_returned}</strong> field(s) →
            <strong> {res.n_kept}</strong> verified,
            <strong> {res.n_flagged}</strong> flagged,
            <strong> {res.n_rejected}</strong> rejected. Model: <code>{res.model}</code>
          </div>

          <Section title={`✓ Verified (${res.extracted.length})`} subtitle="span found in text; unit & range OK">
            {res.extracted.map((f: any, i: number) => <FieldRow key={i} f={f} kind="ok" text={text} />)}
            {!res.extracted.length && <Empty />}
          </Section>

          <Section title={`⚠ Flagged (${res.flagged.length})`} subtitle="span found, but unit/range looks off">
            {res.flagged.map((f: any, i: number) => <FieldRow key={i} f={f} kind="flag" text={text} />)}
            {!res.flagged.length && <Empty />}
          </Section>

          <Section title={`✕ Rejected (${res.rejected.length})`} subtitle="no exact source span — treated as fabrication">
            {res.rejected.map((f: any, i: number) => (
              <div className="card mb" key={i} style={{ borderLeft: "3px solid var(--bad)" }}>
                <div className="row spread">
                  <strong>{f.field || "(unnamed)"}</strong>
                  <span className="badge weak">rejected</span>
                </div>
                <div className="small">value: <code>{String(f.value)}</code>{f.unit ? <> · unit: <code>{f.unit}</code></> : null}</div>
                <div className="small muted">claimed span: “{f.source_span || "—"}” · {f.reason}</div>
              </div>
            ))}
            {!res.rejected.length && <Empty />}
          </Section>
        </div>
      )}
    </div>
  );
}

function Section({ title, subtitle, children }: any) {
  return (
    <div className="mb">
      <h2 className="section spread" style={{ marginBottom: 8 }}>
        <span>{title}</span><span className="muted small" style={{ fontWeight: 500 }}>{subtitle}</span>
      </h2>
      {children}
    </div>
  );
}

function Empty() { return <div className="small muted">none</div>; }

function FieldRow({ f, kind, text }: { f: any; kind: "ok" | "flag"; text: string }) {
  return (
    <div className="card mb" style={{ borderLeft: `3px solid ${kind === "ok" ? "var(--ok)" : "var(--warn)"}` }}>
      <div className="row spread">
        <strong>{f.field}</strong>
        {f.flag ? <span className="badge moderate">{f.flag}</span> : <span className="badge ok">verified</span>}
      </div>
      <div className="small">value: <code>{String(f.value)}</code>{f.unit ? <> · unit: <code>{f.unit}</code></> : null}</div>
      <div className="small muted">source span: <Highlighted text={text} span={f.source_span} /></div>
    </div>
  );
}

function Highlighted({ text, span }: { text: string; span: string }) {
  if (!span) return <em>—</em>;
  const idx = text.toLowerCase().indexOf(span.toLowerCase());
  if (idx < 0) return <>“{span}”</>;
  return (
    <>
      …{text.slice(Math.max(0, idx - 15), idx)}
      <span className="hl">{text.slice(idx, idx + span.length)}</span>
      {text.slice(idx + span.length, idx + span.length + 15)}…
    </>
  );
}
