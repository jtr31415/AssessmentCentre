import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { api } from "../api/client";

export default function AdminLogin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await api.post("/api/auth/admin/login", { username, password });
      nav("/admin");
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
          <h2 className="text-2xl font-bold text-brand-blue">Assessor Login</h2>
          <p className="text-xs text-brand-muted mt-2">
            Sign in with your administrator credentials.
          </p>
        </div>

        <form onSubmit={submit} className="space-y-5">
          <div>
            <label
              htmlFor="username"
              className="block text-xs font-semibold text-brand-ink mb-1.5 uppercase tracking-wider"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              placeholder="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={busy}
              className="w-full text-sm border border-brand-hair rounded px-3 py-2.5 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
            />
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
            {busy ? "Verifying…" : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
