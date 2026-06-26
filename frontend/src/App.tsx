import { NavLink, Route, Routes } from "react-router-dom";
import Explorer from "./pages/Explorer";
import Quality from "./pages/Quality";
import Flagged from "./pages/Flagged";
import Catalog from "./pages/Catalog";
import Extract from "./pages/Extract";

export default function App() {
  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="brand">
            <span className="logo">◆</span>
            <span>ProvBench</span>
            <span className="tag">EGFR bioactivity · provenance-preserving</span>
          </div>
          <nav className="nav">
            <NavLink to="/" end>Explorer</NavLink>
            <NavLink to="/quality">Quality</NavLink>
            <NavLink to="/flagged">Flagged</NavLink>
            <NavLink to="/catalog">Catalog</NavLink>
            <NavLink to="/extract">Extract</NavLink>
          </nav>
        </div>
      </header>

      <main className="main">
        <Routes>
          <Route path="/" element={<Explorer />} />
          <Route path="/quality" element={<Quality />} />
          <Route path="/flagged" element={<Flagged />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/extract" element={<Extract />} />
        </Routes>
      </main>

      <footer className="footer">
        ProvBench · built by <a href="https://github.com/NI3singh">Nitin Singh</a> · data via ChEMBL ·
        curation &amp; QC after Landrum &amp; Riniker (2024)
      </footer>
    </div>
  );
}
