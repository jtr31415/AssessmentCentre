import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertCircle, Check, Copy } from "lucide-react";
import { api } from "../api/client";

export default function SetPassword() {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);
  const [candidateId, setCandidateId] = useState("");
  const [copied, setCopied] = useState(false);
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (newPassword.length < 8) {
      setErr("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setErr("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const res = (await api.post("/api/auth/candidate/set-password", {
        token,
        password: newPassword,
      })) as { candidate_id?: string };
      setCandidateId(res.candidate_id ?? "");
      setSuccess(true);
    } catch (x) {
      setErr(x instanceof Error ? x.message : String(x));
    } finally {
      setBusy(false);
    }
  }

  function copyId() {
    navigator.clipboard.writeText(candidateId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-md mx-auto my-12 animate-fade-in">
      <div className="border border-brand-hair rounded-lg p-8 bg-white shadow-xs">
        <div className="mb-6 text-center">
          <span className="text-[10px] uppercase tracking-widest text-brand-muted font-semibold block mb-1">
            One-Time Access Token Verified
          </span>
          <h2 className="text-2xl font-bold text-brand-blue">Create Your Password</h2>
          <p className="text-xs text-brand-muted mt-2">
            For security, set a secure password to activate your candidate profile.
          </p>
        </div>

        {success ? (
          <div className="space-y-4">
            <div className="p-4 bg-emerald-50 border border-emerald-500 text-emerald-800 text-sm rounded flex items-start gap-2">
              <Check className="w-5 h-5 flex-shrink-0 text-emerald-600 mt-0.5" />
              <div>
                <p className="font-semibold">Password set successfully!</p>
                <p className="text-xs text-emerald-700 mt-1">
                  Your candidate account is now active.
                </p>
              </div>
            </div>

            {candidateId && (
              <div className="p-5 bg-brand-redbg border-2 border-brand-red rounded-lg shadow-sm">
                <p className="text-xs uppercase tracking-widest text-brand-red font-extrabold mb-2 flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4" />
                  Your Candidate ID — save this now
                </p>
                <div className="flex items-center gap-2 bg-white border border-brand-red rounded px-3 py-2">
                  <code className="flex-1 font-mono font-extrabold text-2xl text-brand-red tabular-numbers tracking-wide select-all">
                    {candidateId}
                  </code>
                  <button
                    onClick={copyId}
                    title="Copy"
                    className="p-2 rounded text-brand-red hover:bg-brand-redbg cursor-pointer flex-shrink-0"
                  >
                    {copied ? (
                      <Check className="w-5 h-5 text-emerald-600" />
                    ) : (
                      <Copy className="w-5 h-5" />
                    )}
                  </button>
                </div>
                <p className="text-xs text-brand-ink font-semibold mt-2.5">
                  You'll need this ID together with your password every time you log in.
                  Write it down somewhere safe before continuing.
                </p>
              </div>
            )}

            <Link
              to={candidateId ? `/login?id=${encodeURIComponent(candidateId)}` : "/login"}
              className="block w-full text-center py-2.5 bg-brand-blue hover:bg-opacity-90 text-white font-medium text-sm rounded transition"
            >
              Proceed to Login
            </Link>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-5">
            <div>
              <label
                htmlFor="newPassword"
                className="block text-xs font-semibold text-brand-ink mb-1.5 uppercase tracking-wider"
              >
                New Password
              </label>
              <input
                id="newPassword"
                type="password"
                placeholder="At least 8 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={busy}
                className="w-full text-sm border border-brand-hair rounded px-3 py-2.5 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              />
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-xs font-semibold text-brand-ink mb-1.5 uppercase tracking-wider"
              >
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                placeholder="Re-enter password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={busy}
                className="w-full text-sm border border-brand-hair rounded px-3 py-2.5 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              />
            </div>

            {err && (
              <div
                className="p-3 bg-brand-redbg border border-brand-red text-brand-red text-xs rounded flex items-center gap-2"
                role="alert"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{err}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={busy}
              className="w-full text-center py-2.5 bg-brand-blue hover:bg-opacity-90 text-white font-medium text-sm rounded transition cursor-pointer disabled:opacity-50"
            >
              {busy ? "Activating…" : "Activate Account"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
