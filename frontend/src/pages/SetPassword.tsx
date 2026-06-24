import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";

export default function SetPassword() {
  const [password, setP] = useState("");
  const [err, setErr] = useState("");
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/auth/candidate/set-password", { token, password });
      nav("/login");
    } catch (x) {
      setErr(String(x));
    }
  }
  return (
    <form onSubmit={submit}>
      <h1>Set password</h1>
      <input type="password" placeholder="new password" value={password} onChange={(e) => setP(e.target.value)} />
      <button>Set password</button>
      {err && <p role="alert">{err}</p>}
    </form>
  );
}
