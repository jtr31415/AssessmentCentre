import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export default function CandidateLogin() {
  const [candidateId, setCandidateId] = useState("");
  const [password, setP] = useState("");
  const [err, setErr] = useState("");
  const nav = useNavigate();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/auth/candidate/login", { candidate_id: candidateId, password });
      nav("/dashboard");
    } catch (x) {
      setErr(String(x));
    }
  }
  return (
    <form onSubmit={submit}>
      <h1>Candidate login</h1>
      <input placeholder="candidate ID" value={candidateId} onChange={(e) => setCandidateId(e.target.value)} />
      <input type="password" placeholder="password" value={password} onChange={(e) => setP(e.target.value)} />
      <button>Log in</button>
      {err && <p role="alert">{err}</p>}
    </form>
  );
}
