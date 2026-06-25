import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, AlertTriangle, Loader2, Check, X } from "lucide-react";
import { api } from "../api/client";

type View = "loading" | "undecided" | "declined";

const TERMS: string[] = [
  "You may use the assessment data we provide solely to complete this assessment exercise.",
  "You may process that data through AI / large language models (LLMs) as part of your work on the exercise.",
  "You must NOT share the data with any other third party.",
  "You must delete the data if you are not selected for the role.",
  "Any code you produce during the exercise is yours to keep and use however you wish — provided it does not contain or embed any of the data we provided.",
];

export default function Nda() {
  const nav = useNavigate();
  const [view, setView] = useState<View>("loading");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .get("/api/me/profile")
      .then((p: { nda_accepted: boolean; nda_declined: boolean }) => {
        if (p.nda_accepted) {
          nav("/dashboard", { replace: true });
        } else {
          setView(p.nda_declined ? "declined" : "undecided");
        }
      })
      .catch(() => nav("/login", { replace: true }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function accept() {
    setBusy(true);
    setErr("");
    try {
      await api.post("/api/me/nda/accept");
      nav("/dashboard", { replace: true });
    } catch (x) {
      setErr(x instanceof Error ? x.message : String(x));
      setBusy(false);
    }
  }

  async function decline() {
    setBusy(true);
    setErr("");
    try {
      await api.post("/api/me/nda/decline");
      setView("declined");
    } catch (x) {
      setErr(x instanceof Error ? x.message : String(x));
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    try {
      await api.post("/api/auth/logout");
    } catch {
      // ignore
    }
    nav("/login", { replace: true });
  }

  if (view === "loading") {
    return (
      <div className="flex items-center justify-center py-20 text-brand-muted gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-brand-blue" />
        <span className="text-sm">Loading…</span>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto my-10 animate-fade-in">
      <div className="border border-brand-hair rounded-lg bg-white shadow-xs overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-brand-hair">
          <div className="flex items-center gap-2 text-brand-blue mb-1">
            <ShieldCheck className="w-5 h-5" />
            <h1 className="text-xl font-bold">Assessment Data Agreement</h1>
          </div>
          <p className="text-xs text-brand-muted">
            Before you take part, please read and accept the terms covering how you may use the
            data we provide. You must accept to continue.
          </p>
        </div>

        {/* Declined banner */}
        {view === "declined" && (
          <div className="m-6 mb-0 p-4 bg-brand-redbg border border-brand-red rounded text-brand-red text-sm flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">You have declined these terms.</p>
              <p className="text-xs mt-1">
                You cannot take part in the assessment while these terms are declined. If this was
                a mistake, you can accept below — otherwise you may log out.
              </p>
            </div>
          </div>
        )}

        {/* Terms */}
        <div className="p-6 space-y-3">
          <p className="text-[10px] uppercase tracking-widest text-brand-muted font-bold">
            By accepting, you agree that:
          </p>
          <ul className="space-y-2.5">
            {TERMS.map((t, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-brand-ink">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-b5 text-brand-blue text-[11px] font-bold flex items-center justify-center mt-0.5 tabular-numbers">
                  {i + 1}
                </span>
                <span className="leading-relaxed">{t}</span>
              </li>
            ))}
          </ul>
          <p className="text-[11px] text-brand-muted pt-2 border-t border-brand-hair">
            Declining means you cannot take part in the assessment exercise.
          </p>
        </div>

        {err && (
          <div className="mx-6 mb-2 p-3 bg-brand-redbg border border-brand-red text-brand-red text-xs rounded flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            {err}
          </div>
        )}

        {/* Actions */}
        <div className="p-6 pt-2 flex flex-col sm:flex-row gap-3">
          <button
            onClick={accept}
            disabled={busy}
            className="flex-1 py-2.5 bg-brand-blue hover:bg-opacity-90 text-white font-semibold text-sm rounded transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            I accept the terms
          </button>
          {view === "undecided" ? (
            <button
              onClick={decline}
              disabled={busy}
              className="flex-1 py-2.5 bg-white text-brand-red border border-brand-red hover:bg-brand-redbg font-semibold text-sm rounded transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <X className="w-4 h-4" />
              Decline
            </button>
          ) : (
            <button
              onClick={logout}
              disabled={busy}
              className="flex-1 py-2.5 bg-white text-brand-muted border border-brand-hair hover:text-brand-ink font-semibold text-sm rounded transition cursor-pointer disabled:opacity-50"
            >
              Log out
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
