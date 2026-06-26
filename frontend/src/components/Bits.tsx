export function Loading() {
  return <div className="loading">Loading…</div>;
}

export function ErrorNote({ msg }: { msg: string }) {
  return (
    <div className="notice">
      {msg}
      <div className="small mt" style={{ color: "inherit" }}>
        If this persists, the API may be waking from sleep (free tier) — retry in ~30s.
      </div>
    </div>
  );
}

export function AgreementBadge({ a }: { a?: string }) {
  const cls =
    a === "strong" ? "strong" : a === "moderate" ? "moderate" : a === "weak" ? "weak" : "single";
  return <span className={`badge ${cls}`}>{a || "single"}</span>;
}

export function SourceBadge({ s }: { s: string }) {
  return <span className="badge src">{s}</span>;
}

export function FlagBadge({ f }: { f?: string | null }) {
  if (!f) return <span className="badge ok">OK</span>;
  return <span className="badge flag">{f}</span>;
}

export function fmtP(p?: number | null) {
  return p == null ? "—" : Number(p).toFixed(2);
}

export function fmtNm(v?: number | null) {
  if (v == null) return "—";
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + " mM";
  if (v >= 1000) return (v / 1000).toFixed(2) + " µM";
  return Number(v).toPrecision(3) + " nM";
}

export function truncate(s: string, n = 42) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n) + "…" : s;
}

type BarDatum = { label: string; value: number; display?: string };
export function Bars({ data, color }: { data: BarDatum[]; color?: string }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="bars">
      {data.map((d, i) => (
        <div className="bar-row" key={i}>
          <div className="bl" title={d.label}>{d.label}</div>
          <div className="bar-track">
            <div
              className={`bar-fill ${color || ""}`}
              style={{ width: `${Math.max(2, (100 * d.value) / max)}%` }}
            />
          </div>
          <div className="bv">{d.display ?? d.value}</div>
        </div>
      ))}
    </div>
  );
}
