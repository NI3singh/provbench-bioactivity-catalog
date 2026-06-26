import { useEffect, useState } from "react";
import { api } from "../api";
import { ErrorNote, fmtP, Loading, SourceBadge, truncate } from "../components/Bits";

export default function Flagged() {
  const [d, setD] = useState<any>(null);
  const [type, setType] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => { load(type); }, [type]);
  async function load(t: string) {
    setD(null); setErr("");
    try { setD(await api.flags(t)); } catch (e: any) { setErr(e.message); }
  }

  return (
    <div>
      <h1 className="page-title">Flagged records — annotate, don’t delete</h1>
      <p className="page-sub">
        Every suspect measurement is <strong>kept</strong> and labelled with a reason (mirroring ChEMBL’s
        <code> DATA_VALIDITY_COMMENT</code> vocabulary). Curating data should never mean silently dropping it.
      </p>

      {err && <ErrorNote msg={err} />}
      {!d ? <Loading /> : (
        <>
          <div className="chip-list mb">
            <button className={`badge pill`} onClick={() => setType("")}
              style={{ cursor: "pointer", outline: type === "" ? "2px solid var(--accent)" : "none" }}>
              all ({d.total?.toLocaleString()})
            </button>
            {d.breakdown.map((b: any) => (
              <button key={b.validity_flag} className="badge flag" style={{ cursor: "pointer", outline: type === b.validity_flag ? "2px solid var(--accent)" : "none" }}
                onClick={() => setType(b.validity_flag)}>
                {b.validity_flag} ({b.n.toLocaleString()})
              </button>
            ))}
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>source</th><th>InChIKey</th><th>type</th>
                  <th className="num">value</th><th className="num">pAct</th><th>flag &amp; reason</th>
                </tr>
              </thead>
              <tbody>
                {d.items.map((r: any, i: number) => (
                  <tr key={i}>
                    <td><SourceBadge s={r.source} /></td>
                    <td className="mono small">{r.inchikey}</td>
                    <td>{r.standard_type}</td>
                    <td className="num">{r.standard_value ?? "—"} {r.standard_units}</td>
                    <td className="num">{fmtP(r.p_activity)}</td>
                    <td>
                      <span className="badge flag">{r.validity_flag}</span>
                      {r.flag_reason && <div className="small muted">{r.flag_reason}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small muted mt">showing {d.items.length} of {d.total?.toLocaleString()} flagged records</p>
        </>
      )}
    </div>
  );
}
