import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { MessageSquare, LayoutDashboard, LogOut } from "lucide-react";
import { api } from "../api/client";

interface Profile {
  candidate_id: string;
  first_name: string;
  status: string;
}

export default function CandidateNav() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    api.get("/api/me/profile")
      .then((data: Profile) => setProfile(data))
      .catch(() => {
        // 401 or network error — stay null, no crash
      });
  }, []);

  async function handleLogout() {
    try {
      await api.post("/api/auth/logout");
    } catch {
      // ignore logout errors
    }
    navigate("/login");
  }

  const navLink = (to: string, label: string, icon: React.ReactNode) => {
    const active = pathname === to;
    return (
      <Link
        to={to}
        className={`px-3 py-1.5 rounded text-xs font-semibold border flex items-center gap-1.5 transition-colors ${
          active
            ? "bg-brand-blue text-white border-brand-blue"
            : "bg-white text-brand-muted border-brand-hair hover:text-brand-ink"
        }`}
      >
        {icon}
        {label}
      </Link>
    );
  };

  return (
    <div className="bg-white border-b border-brand-hair">
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        {/* Identity */}
        <div>
          <span className="text-[10px] uppercase tracking-widest text-brand-muted font-semibold">
            Nordex Assessment Portal
          </span>
          {profile ? (
            <>
              <p className="text-lg font-bold text-brand-blue leading-tight">
                Welcome, {profile.first_name}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs font-mono text-brand-muted">ID: {profile.candidate_id}</span>
                <span className="text-[10px] bg-emerald-50 border border-emerald-300 text-emerald-800 uppercase px-1.5 py-0.5 rounded font-semibold tabular-numbers">
                  {profile.status}
                </span>
              </div>
            </>
          ) : (
            <p className="text-sm text-brand-muted">Loading…</p>
          )}
        </div>

        {/* Nav actions */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          {navLink(
            "/dashboard",
            "Dashboard",
            <LayoutDashboard className="w-3.5 h-3.5" />
          )}
          {navLink(
            "/questions",
            "Questions Thread",
            <MessageSquare className="w-3.5 h-3.5" />
          )}
          <button
            onClick={handleLogout}
            className="px-3 py-1.5 rounded text-xs font-semibold bg-white text-brand-red border border-brand-red hover:bg-brand-redbg transition-colors flex items-center gap-1.5 ml-auto sm:ml-0 cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            Log Out
          </button>
        </div>
      </div>
    </div>
  );
}
