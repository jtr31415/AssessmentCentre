import { useEffect, useState } from "react";
import { api } from "../api/client";

type Cand = { candidate_id: string; first_name: string; status: string; set_password_path: string | null };

export default function AdminDashboard() {
  const [cands, setCands] = useState<Cand[]>([]);
  const [name, setName] = useState("");
  async function load() { setCands(await api.get("/api/admin/candidates")); }
  useEffect(() => { load(); }, []);
  async function create(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/api/admin/candidates", { first_name: name });
    setName("");
    load();
  }
  return (
    <div>
      <h1>Candidates</h1>
      <form onSubmit={create}>
        <input placeholder="first name" value={name} onChange={(e) => setName(e.target.value)} />
        <button>Create</button>
      </form>
      <ul>
        {cands.map((c) => (
          <li key={c.candidate_id}>
            {c.candidate_id} — {c.first_name} — {c.status}
            {c.set_password_path && <code> {location.origin}{c.set_password_path}</code>}
          </li>
        ))}
      </ul>
    </div>
  );
}
