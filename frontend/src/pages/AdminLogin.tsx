import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export default function AdminLogin() {
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [err, setErr] = useState("");
  const nav = useNavigate();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/auth/admin/login", { username, password });
      nav("/admin");
    } catch (x) {
      setErr(String(x));
    }
  }
  return (
    <form onSubmit={submit}>
      <h1>Admin login</h1>
      <input placeholder="username" value={username} onChange={(e) => setU(e.target.value)} />
      <input type="password" placeholder="password" value={password} onChange={(e) => setP(e.target.value)} />
      <button>Log in</button>
      {err && <p role="alert">{err}</p>}
    </form>
  );
}
