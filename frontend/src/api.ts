let _raw = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
// Render's `fromService host` provides a bare hostname; add the scheme if missing.
if (_raw && !/^https?:\/\//i.test(_raw)) _raw = "https://" + _raw;
const BASE = _raw;

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error((detail as any).detail || `${r.status} ${r.statusText}`);
  }
  return r.json();
}

export const api = {
  base: BASE,
  stats: () => get<any>("/api/stats"),
  compounds: (q: string, page = 1) =>
    get<any>(`/api/compounds?q=${encodeURIComponent(q)}&page=${page}`),
  compound: (inchikey: string) => get<any>(`/api/compounds/${encodeURIComponent(inchikey)}`),
  flags: (type = "", page = 1) =>
    get<any>(`/api/flags?type=${encodeURIComponent(type)}&page=${page}`),
  qc: () => get<any>("/api/qc"),
  catalog: () => get<any>("/api/catalog"),
  extract: (text: string) => post<any>("/api/extract", { text }),
};
