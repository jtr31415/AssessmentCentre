import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

type Cand = { candidate_id: string; first_name: string; status: string; set_password_path: string | null };

interface KeyRowState {
  value: string;
  saving: boolean;
  message: string;
  isError: boolean;
}

function SetApiKeyControl({ candidateId }: { candidateId: string }) {
  const [state, setState] = useState<KeyRowState>({
    value: "",
    saving: false,
    message: "",
    isError: false,
  });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!state.value.trim()) return;
    setState((s) => ({ ...s, saving: true, message: "", isError: false }));
    try {
      await api.put(`/api/admin/candidates/${candidateId}/api-key`, { api_key: state.value });
      setState({ value: "", saving: false, message: "Key saved.", isError: false });
    } catch (err) {
      setState((s) => ({
        ...s,
        saving: false,
        message: (err as Error).message || "Failed to save key.",
        isError: true,
      }));
    }
  }

  return (
    <form onSubmit={save} style={{ display: "inline-flex", alignItems: "center", gap: 4, marginLeft: 8 }}>
      <input
        type="password"
        placeholder="API key"
        value={state.value}
        onChange={(e) => setState((s) => ({ ...s, value: e.target.value }))}
        style={{ width: 180 }}
        autoComplete="new-password"
      />
      <button type="submit" disabled={state.saving || !state.value.trim()}>
        {state.saving ? "Saving…" : "Save"}
      </button>
      {state.message && (
        <span style={{ color: state.isError ? "red" : "green", fontSize: 13 }}>{state.message}</span>
      )}
    </form>
  );
}

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
      <p><Link to="/admin/slots">Manage slots</Link></p>
      <form onSubmit={create}>
        <input placeholder="first name" value={name} onChange={(e) => setName(e.target.value)} />
        <button>Create</button>
      </form>
      <ul>
        {cands.map((c) => (
          <li key={c.candidate_id}>
            {c.candidate_id} — {c.first_name} — {c.status}
            {c.set_password_path && <code> {location.origin}{c.set_password_path}</code>}
            <SetApiKeyControl candidateId={c.candidate_id} />
          </li>
        ))}
      </ul>
    </div>
  );
}
