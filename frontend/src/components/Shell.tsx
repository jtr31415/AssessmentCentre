import { Link, Outlet, useLocation } from "react-router-dom";
import CandidateNav from "./CandidateNav";
import AdminNav from "./AdminNav";

const CANDIDATE_ROUTES = ["/dashboard", "/book", "/questions"];
const ADMIN_ROUTES = ["/admin", "/admin/slots", "/admin/questions", "/admin/activity", "/admin/config"];

function useSubNav(pathname: string): "candidate" | "admin" | "none" {
  if (CANDIDATE_ROUTES.includes(pathname)) return "candidate";
  // Admin routes — use startsWith for the /admin prefix, but exclude /admin/login
  if (pathname === "/admin/login") return "none";
  if (ADMIN_ROUTES.includes(pathname)) return "admin";
  return "none";
}

export default function Shell() {
  const { pathname } = useLocation();
  const navKind = useSubNav(pathname);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* ── Org Header ── */}
      <header className="bg-white border-b border-brand-hair">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <div className="text-[10px] uppercase font-bold tracking-[0.2em] text-brand-muted">
              Nordex Recruitment
            </div>
            <h1 className="text-xl md:text-2xl font-bold text-brand-blue tracking-tight leading-tight">
              Assessment Portal
            </h1>
          </div>
          <div className="text-left sm:text-right">
            <span className="text-sm font-bold text-brand-blue block">NORDEX</span>
            <span className="text-[10px] text-brand-muted block mt-0.5 font-mono tabular-numbers">
              Recruitment · Assessment
            </span>
          </div>
        </div>
      </header>

      {/* ── Role-aware sub-nav ── */}
      {navKind === "candidate" && <CandidateNav />}
      {navKind === "admin" && <AdminNav />}

      {/* ── Page content ── */}
      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-6">
          <Outlet />
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="bg-white border-t border-brand-hair py-8 mt-12">
        <div className="max-w-7xl mx-auto px-4 md:px-8 space-y-3 text-center text-xs text-brand-muted">
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 font-semibold">
            <Link to="/privacy" className="hover:text-brand-blue transition-colors">
              Privacy
            </Link>
            <span className="text-brand-hair" aria-hidden="true">|</span>
            <span className="text-brand-ink">Nordex Recruitment</span>
          </div>
          <p className="text-[11px] leading-relaxed max-w-2xl mx-auto">
            We practise data minimisation — only your first name and a system ID are stored. No tracking, no marketing tags.
          </p>
        </div>
      </footer>
    </div>
  );
}
