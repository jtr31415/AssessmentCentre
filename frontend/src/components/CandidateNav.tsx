import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { MessageSquare, LayoutDashboard, LogOut } from "lucide-react";
import { api } from "../api/client";

interface Profile {
  candidate_id: string;
  first_name: string;
  status: string;
  nda_accepted: boolean;
}

export default function CandidateNav() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [unseenAnswers, setUnseenAnswers] = useState(0);
  const prevUnseen = useRef<number | null>(null);

  // Ask once for browser-notification permission (falls back to the badge).
  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }
  }, []);

  useEffect(() => {
    api.get("/api/me/profile")
      .then((data: Profile) => {
        // Gate: candidates who haven't accepted the NDA can't reach the
        // dashboard/booking/questions pages — send them to the NDA page.
        if (!data.nda_accepted) {
          navigate("/nda", { replace: true });
          return;
        }
        setProfile(data);
      })
      .catch(() => {
        // 401 or network error — stay null, no crash
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Poll for answered-but-unseen questions (in-app notification badge).
  useEffect(() => {
    let active = true;
    const poll = () =>
      api
        .get("/api/me/notifications")
        .then((d: { answered_unseen: number }) => {
          if (!active) return;
          const n = d.answered_unseen;
          if (
            prevUnseen.current !== null &&
            n > prevUnseen.current &&
            typeof Notification !== "undefined" &&
            Notification.permission === "granted"
          ) {
            new Notification("Question answered", {
              body: "Your assessor has replied — open your Questions thread.",
            });
          }
          prevUnseen.current = n;
          setUnseenAnswers(n);
        })
        .catch(() => {});
    poll();
    const id = setInterval(poll, 20000);
    return () => {
      active = false;
      clearInterval(id);
    };
    // Re-poll when navigating (e.g. visiting Questions marks answers seen).
  }, [pathname]);

  async function handleLogout() {
    try {
      await api.post("/api/auth/logout");
    } catch {
      // ignore logout errors
    }
    navigate("/login");
  }

  const navLink = (
    to: string,
    label: string,
    icon: React.ReactNode,
    badge = 0
  ) => {
    const active = pathname === to;
    return (
      <Link
        to={to}
        className={`relative px-3 py-1.5 rounded text-xs font-semibold border flex items-center gap-1.5 transition-colors ${
          active
            ? "bg-brand-blue text-white border-brand-blue"
            : "bg-white text-brand-muted border-brand-hair hover:text-brand-ink"
        }`}
      >
        {icon}
        {label}
        {badge > 0 && (
          <span
            className="ml-1 min-w-[18px] h-[18px] px-1 inline-flex items-center justify-center rounded-full bg-brand-red text-white text-[10px] font-bold tabular-numbers"
            aria-label={`${badge} new`}
          >
            {badge}
          </span>
        )}
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
            <MessageSquare className="w-3.5 h-3.5" />,
            unseenAnswers
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
