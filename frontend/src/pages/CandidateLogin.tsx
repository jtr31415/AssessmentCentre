import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { api } from "../api/client";

export default function CandidateLogin() {
  const [searchParams] = useSearchParams();
  const [candidateId, setCandidateId] = useState(searchParams.get("id") ?? "");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await api.post("/api/auth/candidate/login", { candidate_id: candidateId, password });
      nav("/dashboard");
    } catch (x) {
      setErr(x instanceof Error ? x.message : String(x));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-md mx-auto my-12 animate-fade-in">
      <div className="border border-brand-hair rounded-lg p-8 bg-white shadow-xs">
        <div className="mb-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-brand-muted font-semibold block mb-1">
            Nordex Recruitment
          </span>
          <h2 className="text-2xl font-bold text-brand-blue">Candidate Login</h2>
          <p className="text-xs text-brand-muted mt-2">
            Please access the assessment portal using your credentials.
          </p>
        </div>

        <form onSubmit={submit} className="space-y-5">
          <div>
            <label
              htmlFor="candidateId"
              className="block text-xs font-semibold text-brand-ink mb-1.5 uppercase tracking-wider"
            >
              Candidate ID
            </label>
            <input
              id="candidateId"
              type="text"
              placeholder="e.g. cand-07"
              value={candidateId}
              onChange={(e) => setCandidateId(e.target.value)}
              disabled={busy}
              className="w-full text-sm border border-brand-hair rounded px-3 py-2.5 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
            />
            <p className="text-[11px] text-brand-muted mt-1">
              The ID sent in your invitation, e.g.{" "}
              <code className="font-mono bg-brand-codebg px-1">cand-07</code>
            </p>
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-xs font-semibold text-brand-ink mb-1.5 uppercase tracking-wider"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={busy}
              className="w-full text-sm border border-brand-hair rounded px-3 py-2.5 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
            />
          </div>

          {err && (
            <div
              className="p-3 bg-brand-redbg border border-brand-red text-brand-red text-xs rounded flex items-start gap-2"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{err}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full text-center py-2.5 bg-brand-blue hover:bg-opacity-90 text-white font-medium text-sm rounded transition cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {busy ? "Verifying…" : "Access Portal"}
          </button>
        </form>
      </div>
    </div>
  );
}
