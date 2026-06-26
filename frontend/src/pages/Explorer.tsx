import { useEffect, useState } from "react";
import { api } from "../api";
import {
  AgreementBadge, Bars, ErrorNote, fmtNm, fmtP, FlagBadge, Loading, SourceBadge, truncate,
} from "../components/Bits";

export default function Explorer() {
  const [stats, setStats] = useState<any>(null);
  const [q, setQ] = useState("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [selected, setSelected] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);

  useEffect(() => {
    api.stats().then(setStats).catch(() => {});
    search("");
  }, []);

  async function search(query: string) {
    setLoading(true); setErr(""); setDetail(null); setSelected(null);
    try {
      setData(await api.compounds(query));
    } catch (e: any) {
      setErr(e.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function open(inchikey: string) {
    setSelected(inchikey); setDetail(null);
    try {
      setDetail(await api.compound(inchikey));
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <div>
      <h1 className="page-title">Provenance Explorer</h1>
      <p className="page-sub">
        Search a compound to see its <strong>consensus</strong> potency against EGFR — then expand the
        receipts to see <strong>every original measurement</strong>, where it came from, and how it was
        flagged. Nothing is hidden or deleted.
      </p>

      {stats && (
        <div className="grid cols-4 mb">
          <div className="card stat"><span className="num accent">{stats.compounds?.toLocaleString()}</span><span className="lbl">unique compounds</span></div>
          <div className="card stat"><span className="num">{stats.source_records?.toLocaleString()}</span><span className="lbl">original measurements</span></div>
          <div className="card stat"><span className="num">{stats.sources?.length}</span><span className="lbl">upstream sources</span></div>
          <div className="card stat"><span className="num">{stats.flagged?.toLocaleString()}</span><span className="lbl">flagged (kept, not deleted)</span></div>
        </div>
      )}

      <div className="row mb">
        <input
          className="input" placeholder="Search by InChIKey or SMILES substring…"
          value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search(q)}
          style={{ maxWidth: 460 }}
        />
        <button className="btn" onClick={() => search(q)}>Search</button>
        {q && <button className="btn ghost" onClick={() => { setQ(""); search(""); }}>Clear</button>}
      </div>

      {err && <ErrorNote msg={err} />}
      {loading ? <Loading /> : data && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>InChIKey</th><th>SMILES</th>
                <th className="num">consensus pAct</th><th className="num">potency</th>
                <th className="num">measurements</th><th className="num">sources</th><th>agreement</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((r: any) => (
                <tr className="clickable" key={r.inchikey} onClick={() => open(r.inchikey)}>
                  <td className="mono">{r.inchikey}</td>
                  <td className="mono muted">{truncate(r.std_smiles)}</td>
                  <td className="num">{fmtP(r.consensus_p_activity)}</td>
                  <td className="num">{fmtNm(r.consensus_value_nm)}</td>
                  <td className="num">{r.n_records_used}</td>
                  <td className="num">{r.n_sources}</td>
                  <td><AgreementBadge a={r.agreement} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <p className="small muted mt">{data.total?.toLocaleString()} compounds · click a row for the receipts</p>}

      {selected && (
        <div className="card accent-top mt" style={{ marginTop: 22 }}>
          {!detail ? <Loading /> : <Detail detail={detail} />}
        </div>
      )}
    </div>
  );
}

function Detail({ detail }: { detail: any }) {
  const c = detail.consensus;
  return (
    <div>
      <div className="spread">
        <h2 className="section" style={{ margin: 0 }}>Compound detail</h2>
        {c && <AgreementBadge a={c.agreement} />}
      </div>
      <div className="mono small muted">{detail.compound?.inchikey}</div>
      <div className="mono small mb" style={{ wordBreak: "break-all" }}>{detail.compound?.std_smiles}</div>

      {c && (
        <dl className="kvs mb">
          <dt>Consensus pActivity</dt><dd>{fmtP(c.consensus_p_activity)} <span className="muted">(median)</span></dd>
          <dt>Consensus potency</dt><dd>{fmtNm(c.consensus_value_nm)}</dd>
          <dt>Spread</dt><dd>{c.spread_log == null ? "—" : `${Number(c.spread_log).toFixed(2)} log units`}</dd>
          <dt>From</dt><dd>{c.n_records_used} exact measurements · {c.n_sources} source(s)</dd>
        </dl>
      )}

      <div className="flow mb">
        <span className="node">original records ({detail.n_records})</span>
        <span className="arrow">→</span>
        <span className="node">RDKit standardize · InChIKey</span>
        <span className="arrow">→</span>
        <span className="node">harmonize units → nM</span>
        <span className="arrow">→</span>
        <span className="node">median consensus</span>
      </div>

      <h2 className="section">The receipts — every original measurement</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>source</th><th>type</th><th className="num">value</th>
              <th className="num">pAct</th><th>status</th><th>assay / document</th>
            </tr>
          </thead>
          <tbody>
            {detail.records.map((r: any, i: number) => (
              <tr key={i}>
                <td><SourceBadge s={r.source} /></td>
                <td>{r.standard_type} <span className="muted">{r.standard_relation !== "=" ? r.standard_relation : ""}</span></td>
                <td className="num">{r.standard_value} {r.standard_units}</td>
                <td className="num">{fmtP(r.p_activity)}</td>
                <td>
                  <FlagBadge f={r.validity_flag} />
                  {r.flag_reason && <div className="small muted">{r.flag_reason}</div>}
                </td>
                <td className="small">
                  {r.source_url
                    ? <a href={r.source_url} target="_blank" rel="noreferrer">{r.assay_id || r.source_compound_id || "source"}</a>
                    : (r.assay_id || "—")}
                  {r.confidence_score != null && <span className="muted"> · conf {r.confidence_score}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
