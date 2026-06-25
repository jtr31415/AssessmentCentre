import { useEffect, useState } from "react";
import { api } from "../api/client";
import {
  Plus,
  Key,
  Copy,
  Check,
  Lock,
  Unlock,
  RefreshCw,
  AlertTriangle,
  Loader2,
  Users,
  Trash2,
} from "lucide-react";

type Cand = {
  candidate_id: string;
  first_name: string;
  status: string;
  set_password_path: string | null;
  booked_slot_id: number | null;
  booked_slot_at: string | null;
  unlock_at: string | null;
};

function fmtSlot(ts: string | null) {
  if (!ts) return null;
  return new Date(ts).toLocaleString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* ─── Status badge ─────────────────────────────────────────────────────────── */
function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "active"
      ? "bg-emerald-50 text-emerald-800 border-emerald-300"
      : status === "invited"
      ? "bg-amber-50 text-amber-800 border-amber-300 animate-pulse"
      : "bg-brand-redbg text-brand-red border-brand-red";

  return (
    <span
      className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${cls}`}
    >
      {status}
    </span>
  );
}

/* ─── API key control ─────────────────────────────────────────────────────── */
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
      await api.put(`/api/admin/candidates/${candidateId}/api-key`, {
        api_key: state.value,
      });
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
    <form onSubmit={save} className="flex items-center gap-2">
      <label htmlFor={`api-key-${candidateId}`} className="sr-only">
        API key for candidate {candidateId}
      </label>
      <input
        id={`api-key-${candidateId}`}
        type="password"
        placeholder="Insert key token…"
        value={state.value}
        onChange={(e) => setState((s) => ({ ...s, value: e.target.value }))}
        autoComplete="new-password"
        className="border border-brand-hair rounded px-2 py-1 w-36 bg-white text-xs text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
      />
      <button
        type="submit"
        disabled={state.saving || !state.value.trim()}
        className="px-2.5 py-1 bg-brand-blue text-white text-[10px] font-semibold rounded hover:bg-opacity-90 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 cursor-pointer flex-shrink-0"
      >
        <Key className="w-3 h-3" />
        {state.saving ? "Saving…" : "Save"}
      </button>
      {state.message && (
        <span
          className={`text-[10px] font-semibold ${
            state.isError ? "text-brand-red" : "text-emerald-700"
          }`}
        >
          {state.message}
        </span>
      )}
    </form>
  );
}

/* ─── Per-candidate account controls ─────────────────────────────────────── */
interface AccountControlsState {
  busy: boolean;
  link: string;
  statusMsg: string;
  error: string;
  copied: boolean;
}

function AccountControls({
  cand,
  onStatusChange,
  onDeleted,
}: {
  cand: Cand;
  onStatusChange: (candidateId: string, newStatus: string) => void;
  onDeleted: (candidateId: string) => void;
}) {
  const [state, setState] = useState<AccountControlsState>({
    busy: false,
    link: "",
    statusMsg: "",
    error: "",
    copied: false,
  });

  // Delete-confirmation flow (must type the candidate ID)
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  async function confirmDelete() {
    if (confirmText !== cand.candidate_id) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await api.del(`/api/admin/candidates/${cand.candidate_id}`, {
        confirm: confirmText,
      });
      onDeleted(cand.candidate_id);
    } catch (err) {
      setDeleteError((err as Error).message || "Delete failed.");
      setDeleting(false);
    }
  }

  function reset() {
    setState((s) => ({ ...s, busy: true, link: "", statusMsg: "", error: "" }));
  }

  async function resetPassword() {
    reset();
    try {
      const res = await api.post(
        `/api/admin/candidates/${cand.candidate_id}/reset-password`
      );
      const path = (res as { set_password_path: string }).set_password_path;
      setState((s) => ({
        ...s,
        busy: false,
        link: `${window.location.origin}${path}`,
      }));
    } catch (err) {
      setState((s) => ({
        ...s,
        busy: false,
        error: (err as Error).message || "Failed.",
      }));
    }
  }

  async function reissueInvite() {
    reset();
    try {
      const res = await api.post(
        `/api/admin/candidates/${cand.candidate_id}/reissue-invite`
      );
      const path = (res as { set_password_path: string }).set_password_path;
      setState((s) => ({
        ...s,
        busy: false,
        link: `${window.location.origin}${path}`,
      }));
    } catch (err) {
      setState((s) => ({
        ...s,
        busy: false,
        error: (err as Error).message || "Failed.",
      }));
    }
  }

  async function toggleDisable() {
    const endpoint = cand.status === "disabled" ? "enable" : "disable";
    reset();
    try {
      const res = await api.post(
        `/api/admin/candidates/${cand.candidate_id}/${endpoint}`
      );
      const newStatus = (res as { status: string }).status;
      setState((s) => ({
        ...s,
        busy: false,
        statusMsg: `Status: ${newStatus}`,
      }));
      onStatusChange(cand.candidate_id, newStatus);
    } catch (err) {
      setState((s) => ({
        ...s,
        busy: false,
        error: (err as Error).message || "Failed.",
      }));
    }
  }

  function copyLink() {
    navigator.clipboard.writeText(state.link);
    setState((s) => ({ ...s, copied: true }));
    setTimeout(() => setState((s) => ({ ...s, copied: false })), 2000);
  }

  const isInvited = cand.status === "invited";
  const isDisabled = cand.status === "disabled";

  return (
    <div className="flex flex-col gap-2">
      {/* Action buttons */}
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          onClick={resetPassword}
          disabled={state.busy}
          className="px-2.5 py-1 text-[10px] font-semibold rounded border border-brand-b4 bg-brand-b5 text-brand-blue hover:bg-brand-b4 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 cursor-pointer"
        >
          <RefreshCw className="w-3 h-3" />
          Reset password
        </button>

        {isInvited && (
          <button
            onClick={reissueInvite}
            disabled={state.busy}
            className="px-2.5 py-1 text-[10px] font-semibold rounded border border-brand-b4 bg-brand-b5 text-brand-blue hover:bg-brand-b4 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 cursor-pointer"
          >
            <RefreshCw className="w-3 h-3" />
            Re-issue invite
          </button>
        )}

        <button
          onClick={toggleDisable}
          disabled={state.busy}
          className={`px-2.5 py-1 text-[10px] font-bold rounded border flex items-center gap-1 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
            isDisabled
              ? "bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100"
              : "bg-brand-redbg text-brand-red border-brand-red hover:bg-red-100"
          }`}
        >
          {isDisabled ? (
            <>
              <Unlock className="w-3 h-3" />
              Enable
            </>
          ) : (
            <>
              <Lock className="w-3 h-3" />
              Disable
            </>
          )}
        </button>

        <button
          onClick={() => {
            setDeleteOpen((o) => !o);
            setConfirmText("");
            setDeleteError("");
          }}
          disabled={state.busy || deleting}
          className="px-2.5 py-1 text-[10px] font-bold rounded border border-brand-red bg-brand-redbg text-brand-red hover:bg-red-100 flex items-center gap-1 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Trash2 className="w-3 h-3" />
          Delete
        </button>
      </div>

      {/* Delete confirmation */}
      {deleteOpen && (
        <div className="bg-brand-redbg border border-brand-red rounded p-2.5 space-y-2 max-w-sm">
          <p className="text-[10px] text-brand-ink">
            This permanently deletes <strong>{cand.candidate_id}</strong> and all their data
            (booking, questions, downloads). Type{" "}
            <code className="font-mono bg-white border border-brand-hair px-1 rounded text-brand-red">
              {cand.candidate_id}
            </code>{" "}
            to confirm.
          </p>
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={cand.candidate_id}
              autoComplete="off"
              className="flex-1 text-[11px] font-mono border border-brand-hair rounded px-2 py-1 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-red"
            />
            <button
              onClick={confirmDelete}
              disabled={confirmText !== cand.candidate_id || deleting}
              className="px-2.5 py-1 text-[10px] font-bold rounded bg-brand-red text-white hover:bg-opacity-90 flex items-center gap-1 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed flex-shrink-0"
            >
              {deleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
              Delete
            </button>
          </div>
          {deleteError && (
            <p className="text-[10px] text-brand-red font-semibold flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              {deleteError}
            </p>
          )}
        </div>
      )}

      {/* Feedback area */}
      {state.link && (
        <div className="flex items-center gap-1.5 max-w-xs">
          <code className="bg-brand-codebg border border-brand-hair px-1.5 py-0.5 rounded text-[10px] font-mono truncate select-all flex-1">
            {state.link}
          </code>
          <button
            onClick={copyLink}
            title="Click to copy"
            className="p-1 hover:bg-neutral-100 rounded text-brand-muted hover:text-brand-ink flex-shrink-0 cursor-pointer"
          >
            {state.copied ? (
              <Check className="w-3.5 h-3.5 text-emerald-600" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      )}
      {state.statusMsg && (
        <span className="text-[10px] text-emerald-700 font-semibold">
          {state.statusMsg}
        </span>
      )}
      {state.error && (
        <span className="text-[10px] text-brand-red font-semibold flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          {state.error}
        </span>
      )}
    </div>
  );
}

/* ─── Main page ───────────────────────────────────────────────────────────── */
export default function AdminDashboard() {
  const [cands, setCands] = useState<Cand[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createSuccess, setCreateSuccess] = useState("");

  async function load() {
    setLoading(true);
    setLoadError("");
    try {
      const data = await api.get("/api/admin/candidates");
      setCands(data as Cand[]);
    } catch (err) {
      setLoadError((err as Error).message || "Failed to load candidates.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setCreateError("");
    setCreateSuccess("");
    try {
      await api.post("/api/admin/candidates", { first_name: name.trim() });
      setCreateSuccess(
        `Candidate "${name.trim()}" created successfully as Invited!`
      );
      setName("");
      setTimeout(() => setCreateSuccess(""), 4000);
      await load();
    } catch (err) {
      setCreateError(
        (err as Error).message || "Failed to create candidate."
      );
    } finally {
      setCreating(false);
    }
  }

  function handleStatusChange(candidateId: string, newStatus: string) {
    setCands((prev) =>
      prev.map((c) =>
        c.candidate_id === candidateId ? { ...c, status: newStatus } : c
      )
    );
  }

  function handleDeleted(candidateId: string) {
    setCands((prev) => prev.filter((c) => c.candidate_id !== candidateId));
  }


  return (
    <div className="space-y-6">
      {/* ── Create candidate card ───────────────────────────────────────────── */}
      <div className="border border-brand-hair rounded-lg p-5 bg-white space-y-4">
        <div className="panel-title">
          <h3 className="font-bold text-brand-blue text-sm">
            Add New Candidate Account
          </h3>
        </div>

        <form
          onSubmit={create}
          className="ml-4 flex flex-col sm:flex-row gap-3 items-end"
        >
          <div className="flex-1 w-full">
            <label
              htmlFor="new-candidate-name"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Candidate First Name
            </label>
            <input
              id="new-candidate-name"
              type="text"
              placeholder="e.g. Sarah"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
            />
          </div>

          <button
            type="submit"
            disabled={creating || !name.trim()}
            className="bg-brand-blue hover:bg-opacity-90 text-white font-semibold text-xs px-4 py-2.5 rounded h-10 flex items-center gap-1 cursor-pointer w-full sm:w-auto justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {creating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            <span>Create Candidate</span>
          </button>
        </form>

        {createSuccess && (
          <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs rounded ml-4">
            {createSuccess}
          </div>
        )}
        {createError && (
          <div className="p-3 bg-brand-redbg border border-brand-red text-brand-red text-xs rounded ml-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            {createError}
          </div>
        )}
      </div>

      {/* ── Candidate list card ─────────────────────────────────────────────── */}
      <div className="border border-brand-hair rounded-lg p-6 bg-white space-y-4">
        <div className="panel-title">
          <h3 className="font-bold text-brand-blue text-sm">
            Managed Candidate Profiles
          </h3>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-12 text-brand-muted gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-brand-blue" />
            <span className="text-sm">Loading candidates…</span>
          </div>
        )}

        {/* Load error state */}
        {!loading && loadError && (
          <div className="p-4 bg-brand-redbg border border-brand-red rounded flex items-center gap-3 text-brand-red text-sm">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-semibold">Failed to load candidates</p>
              <p className="text-xs mt-0.5">{loadError}</p>
            </div>
            <button
              onClick={load}
              className="px-3 py-1.5 bg-brand-red text-white text-xs font-bold rounded hover:bg-opacity-90 cursor-pointer flex-shrink-0"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty state */}
        {!loading && !loadError && cands.length === 0 && (
          <div className="py-12 flex flex-col items-center text-brand-muted gap-3 border border-dashed border-brand-hair rounded-lg bg-brand-b5">
            <Users className="w-8 h-8 text-brand-b3" />
            <p className="text-sm">No candidates yet — create one above.</p>
          </div>
        )}

        {/* Table */}
        {!loading && !loadError && cands.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-brand-b5 border-b border-brand-hair text-brand-blue font-bold">
                  <th className="p-3">ID</th>
                  <th className="p-3">First Name</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Booked Slot</th>
                  <th className="p-3">API Key (Write-Only)</th>
                  <th className="p-3">Invite / Reset Link</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-hair">
                {cands.map((c) => (
                  <tr key={c.candidate_id} className="hover:bg-neutral-50 align-top">
                    <td className="p-3 font-mono font-bold text-brand-ink tabular-numbers whitespace-nowrap">
                      {c.candidate_id}
                    </td>
                    <td className="p-3 font-semibold text-brand-ink whitespace-nowrap">
                      {c.first_name}
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      {c.booked_slot_at ? (
                        <span className="text-brand-ink tabular-numbers font-medium">
                          {fmtSlot(c.booked_slot_at)}
                        </span>
                      ) : (
                        <span className="text-brand-muted italic text-[10px]">
                          Not booked
                        </span>
                      )}
                    </td>
                    <td className="p-3">
                      <SetApiKeyControl candidateId={c.candidate_id} />
                    </td>
                    <td className="p-3">
                      {c.set_password_path ? (
                        <code className="bg-brand-codebg border border-brand-hair px-1.5 py-0.5 rounded text-[10px] font-mono select-all break-all">
                          {window.location.origin}
                          {c.set_password_path}
                        </code>
                      ) : (
                        <span className="text-brand-muted italic text-[10px]">
                          —
                        </span>
                      )}
                    </td>
                    <td className="p-3">
                      <AccountControls
                        cand={c}
                        onStatusChange={handleStatusChange}
                        onDeleted={handleDeleted}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
