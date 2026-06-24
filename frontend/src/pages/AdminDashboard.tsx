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

interface AccountControlsState {
  busy: boolean;
  link: string;
  status: string;
  error: string;
}

function AccountControls({
  cand,
  onStatusChange,
}: {
  cand: Cand;
  onStatusChange: (candidateId: string, newStatus: string) => void;
}) {
  const [state, setState] = useState<AccountControlsState>({
    busy: false,
    link: "",
    status: "",
    error: "",
  });

  async function resetPassword() {
    setState((s) => ({ ...s, busy: true, link: "", status: "", error: "" }));
    try {
      const res = await api.post(`/api/admin/candidates/${cand.candidate_id}/reset-password`);
      const path = (res as { set_password_path: string }).set_password_path;
      setState((s) => ({ ...s, busy: false, link: `${location.origin}${path}` }));
    } catch (err) {
      setState((s) => ({ ...s, busy: false, error: (err as Error).message || "Failed." }));
    }
  }

  async function reissueInvite() {
    setState((s) => ({ ...s, busy: true, link: "", status: "", error: "" }));
    try {
      const res = await api.post(`/api/admin/candidates/${cand.candidate_id}/reissue-invite`);
      const path = (res as { set_password_path: string }).set_password_path;
      setState((s) => ({ ...s, busy: false, link: `${location.origin}${path}` }));
    } catch (err) {
      setState((s) => ({ ...s, busy: false, error: (err as Error).message || "Failed." }));
    }
  }

  async function toggleDisable() {
    const endpoint = cand.status === "disabled" ? "enable" : "disable";
    setState((s) => ({ ...s, busy: true, link: "", status: "", error: "" }));
    try {
      const res = await api.post(`/api/admin/candidates/${cand.candidate_id}/${endpoint}`);
      const newStatus = (res as { status: string }).status;
      setState((s) => ({ ...s, busy: false, status: `Status: ${newStatus}` }));
      onStatusChange(cand.candidate_id, newStatus);
    } catch (err) {
      setState((s) => ({ ...s, busy: false, error: (err as Error).message || "Failed." }));
    }
  }

  const isInvited = cand.status === "invited";
  const isDisabled = cand.status === "disabled";

  return (
    <span style={{ marginLeft: 12, fontSize: 13 }}>
      <button onClick={resetPassword} disabled={state.busy} style={{ marginRight: 4 }}>
        Reset password
      </button>
      {isInvited && (
        <button onClick={reissueInvite} disabled={state.busy} style={{ marginRight: 4 }}>
          Re-issue invite
        </button>
      )}
      <button onClick={toggleDisable} disabled={state.busy} style={{ marginRight: 4 }}>
        {isDisabled ? "Enable" : "Disable"}
      </button>
      {state.link && (
        <span style={{ marginLeft: 4 }}>
          Link:{" "}
          <code
            style={{ background: "#f0f0f0", padding: "1px 4px", cursor: "pointer", fontSize: 12 }}
            onClick={() => navigator.clipboard.writeText(state.link)}
            title="Click to copy"
          >
            {state.link}
          </code>
        </span>
      )}
      {state.status && <span style={{ color: "green", marginLeft: 4 }}>{state.status}</span>}
      {state.error && <span style={{ color: "red", marginLeft: 4 }}>{state.error}</span>}
    </span>
  );
}

export default function AdminDashboard() {
  const [cands, setCands] = useState<Cand[]>([]);
  const [name, setName] = useState("");

  async function load() {
    setCands(await api.get("/api/admin/candidates"));
  }

  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/api/admin/candidates", { first_name: name });
    setName("");
    load();
  }

  function handleStatusChange(candidateId: string, newStatus: string) {
    setCands((prev) =>
      prev.map((c) => (c.candidate_id === candidateId ? { ...c, status: newStatus } : c))
    );
  }

  return (
    <div>
      <h1>Candidates</h1>
      <p>
        <Link to="/admin/slots">Manage slots</Link>
        {" · "}
        <Link to="/admin/questions">Questions queue</Link>
        {" · "}
        <Link to="/admin/activity">Activity overview</Link>
      </p>
      <form onSubmit={create}>
        <input placeholder="first name" value={name} onChange={(e) => setName(e.target.value)} />
        <button>Create</button>
      </form>
      <ul>
        {cands.map((c) => (
          <li key={c.candidate_id} style={{ marginBottom: 8 }}>
            {c.candidate_id} — {c.first_name} — {c.status}
            {c.set_password_path && <code> {location.origin}{c.set_password_path}</code>}
            <SetApiKeyControl candidateId={c.candidate_id} />
            <AccountControls cand={c} onStatusChange={handleStatusChange} />
          </li>
        ))}
      </ul>
    </div>
  );
}
