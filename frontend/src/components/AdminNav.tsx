import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Users,
  Calendar,
  MessageSquare,
  Activity,
  Settings,
  FolderUp,
  Lock,
  LogOut,
} from "lucide-react";
import { api } from "../api/client";

const TABS = [
  { to: "/admin",              label: "Candidates",     Icon: Users         },
  { to: "/admin/slots",        label: "Slots",          Icon: Calendar      },
  { to: "/admin/content",      label: "Content",        Icon: FolderUp      },
  { to: "/admin/questions",    label: "Questions",      Icon: MessageSquare },
  { to: "/admin/activity",     label: "Activity",       Icon: Activity      },
  { to: "/admin/config",       label: "Settings & Data",Icon: Settings      },
] as const;

export default function AdminNav() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [pendingQuestions, setPendingQuestions] = useState(0);
  const prevPending = useRef<number | null>(null);

  // Ask once for browser-notification permission (falls back to the badge).
  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }
  }, []);

  // Poll for unanswered candidate questions (in-app badge + browser notification).
  useEffect(() => {
    let active = true;
    const poll = () =>
      api
        .get("/api/admin/notifications")
        .then((d: { unanswered_questions: number }) => {
          if (!active) return;
          const n = d.unanswered_questions;
          if (
            prevPending.current !== null &&
            n > prevPending.current &&
            typeof Notification !== "undefined" &&
            Notification.permission === "granted"
          ) {
            new Notification("New candidate question", {
              body: "A candidate has submitted a question — open the Questions tab.",
            });
          }
          prevPending.current = n;
          setPendingQuestions(n);
        })
        .catch(() => {});
    poll();
    const id = setInterval(poll, 20000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [pathname]);

  async function handleLogout() {
    try {
      await api.post("/api/auth/logout");
    } catch {
      // ignore
    }
    navigate("/admin/login");
  }

  return (
    <div className="bg-white border-b border-brand-hair">
      <div className="max-w-7xl mx-auto px-4 md:px-8 pt-3">
        {/* Top row: role label + logout */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] uppercase tracking-widest text-brand-red font-extrabold flex items-center gap-1">
            <Lock className="w-3.5 h-3.5" />
            Nordex Assessor Environment
          </span>
          <button
            onClick={handleLogout}
            className="px-3 py-1.5 rounded text-xs font-bold bg-white text-brand-red border border-brand-red hover:bg-brand-redbg transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            Assessor Logout
          </button>
        </div>

        {/* Tab row */}
        <div className="flex items-center gap-1 overflow-x-auto pb-0">
          {TABS.map(({ to, label, Icon }) => {
            const active = pathname === to;
            const badge = to === "/admin/questions" ? pendingQuestions : 0;
            return (
              <Link
                key={to}
                to={to}
                className={`px-4 py-2 text-xs font-semibold rounded-t-lg border-t border-x -mb-px flex items-center gap-1.5 whitespace-nowrap transition-colors ${
                  active
                    ? "bg-white text-brand-blue border-brand-hair font-bold relative z-10"
                    : "bg-neutral-50 text-brand-muted border-transparent hover:text-brand-ink"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
                {badge > 0 && (
                  <span
                    className="min-w-[18px] h-[18px] px-1 inline-flex items-center justify-center rounded-full bg-brand-red text-white text-[10px] font-bold tabular-numbers"
                    aria-label={`${badge} unanswered`}
                  >
                    {badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
