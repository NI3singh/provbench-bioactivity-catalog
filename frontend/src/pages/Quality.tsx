import { useEffect, useState } from "react";
import { api } from "../api";
import { Bars, ErrorNote, Loading } from "../components/Bits";

export default function Quality() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => { api.qc().then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <ErrorNote msg={err} />;
  if (!d) return <Loading />;

  const m: Record<string, any> = {};
  d.metrics.forEach((r: any) => (m[r.curation_level] = r));
  const tauData = ["minimal", "maximal", "cross_source"].filter((k) => m[k]).map((k) => ({
    label: k, value: m[k].kendall_tau ?? 0, display: (m[k].kendall_tau ?? 0).toFixed(3),
  }));
  const maeData = ["minimal", "maximal", "cross_source"].filter((k) => m[k]).map((k) => ({
    label: k, value: m[k].mae_log ?? 0, display: (m[k].mae_log ?? 0).toFixed(2),
  }));

  return (
    <div>
      <h1 className="page-title">Data-quality report</h1>
      <p className="page-sub">
        Reproducing the analysis of <strong>Landrum &amp; Riniker (2024)</strong>: when the same compound is
        measured more than once, how well do the values agree — and does metadata-matched curation help?
        Higher Kendall&nbsp;τ and lower MAE mean better agreement.
      </p>

      <div className="banner mb">
        <strong>Key finding:</strong> combining measurements <em>across different upstream sources</em> is the
        noisiest regime, and requiring assays to match on metadata (“maximal” curation) measurably improves
        agreement — proof that <strong>assay metadata is the data-quality lever</strong>.
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2 className="section" style={{ marginTop: 0 }}>Agreement — Kendall τ (higher is better)</h2>
          <Bars data={tauData} />
        </div>
        <div className="card">
          <h2 className="section" style={{ marginTop: 0 }}>Disagreement — MAE in log units (lower is better)</h2>
          <Bars data={maeData} color="warn" />
        </div>
      </div>

      <h2 className="section">Full QC table</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>curation regime</th><th className="num">pairs</th><th className="num">Kendall τ</th>
              <th className="num">% &gt; 0.3 log</th><th className="num">% &gt; 1.0 log</th><th className="num">MAE (log)</th>
            </tr>
          </thead>
          <tbody>
            {d.metrics.map((r: any) => (
              <tr key={r.curation_level}>
                <td><strong>{r.curation_level}</strong></td>
                <td className="num">{r.n_pairs?.toLocaleString()}</td>
                <td className="num">{r.kendall_tau?.toFixed(3) ?? "—"}</td>
                <td className="num">{r.frac_gt_03 != null ? (r.frac_gt_03 * 100).toFixed(0) + "%" : "—"}</td>
                <td className="num">{r.frac_gt_10 != null ? (r.frac_gt_10 * 100).toFixed(0) + "%" : "—"}</td>
                <td className="num">{r.mae_log?.toFixed(3) ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid cols-3" style={{ marginTop: 18 }}>
        <div className="card">
          <h2 className="section" style={{ marginTop: 0 }}>Measurements by source</h2>
          <Bars color="indigo"
            data={d.by_source.map((s: any) => ({ label: s.source, value: s.n, display: s.n.toLocaleString() }))} />
        </div>
        <div className="card">
          <h2 className="section" style={{ marginTop: 0 }}>Flags caught (kept)</h2>
          <Bars color="warn"
            data={d.by_flag.map((s: any) => ({ label: s.flag, value: s.n, display: s.n.toLocaleString() }))} />
        </div>
        <div className="card">
          <h2 className="section" style={{ marginTop: 0 }}>Consensus agreement</h2>
          <Bars data={d.by_agreement.map((s: any) => ({ label: s.agreement, value: s.n, display: s.n.toLocaleString() }))} />
        </div>
      </div>
    </div>
  );
}
