import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

interface ConfigMap {
  prep_window_days: string;
  retention_date: string | null;
  qa_sla_text: string;
  display_timezone: string;
  [key: string]: string | null | undefined;
}

interface FieldState {
  value: string;
  saving: boolean;
  message: string;
  isError: boolean;
}

function useFieldState(initial: string): [FieldState, (patch: Partial<FieldState>) => void] {
  const [state, setState] = useState<FieldState>({
    value: initial,
    saving: false,
    message: "",
    isError: false,
  });
  function patch(p: Partial<FieldState>) {
    setState((s) => ({ ...s, ...p }));
  }
  return [state, patch];
}

const PURGE_PHRASE = "PURGE ALL CANDIDATE DATA";

export default function AdminConfig() {
  const [config, setConfig] = useState<ConfigMap | null>(null);
  const [loadError, setLoadError] = useState("");

  // Per-field states
  const [prepDays, patchPrepDays] = useFieldState("");
  const [retDate, patchRetDate] = useFieldState("");
  const [slaText, patchSlaText] = useFieldState("");
  const [tz, patchTz] = useFieldState("");

  // Purge section
  const [purgeInput, setPurgeInput] = useState("");
  const [purging, setPurging] = useState(false);
  const [purgeResult, setPurgeResult] = useState<{
    deleted: Record<string, number>;
  } | null>(null);
  const [purgeError, setPurgeError] = useState("");

  useEffect(() => {
    api
      .get("/api/admin/config")
      .then((data: unknown) => {
        const cfg = data as ConfigMap;
        setConfig(cfg);
        patchPrepDays({ value: cfg.prep_window_days ?? "" });
        patchRetDate({ value: cfg.retention_date ?? "" });
        patchSlaText({ value: cfg.qa_sla_text ?? "" });
        patchTz({ value: cfg.display_timezone ?? "" });
      })
      .catch((err: Error) => {
        setLoadError(err.message || "Failed to load config.");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saveField(
    key: string,
    value: string,
    patch: (p: Partial<FieldState>) => void
  ) {
    patch({ saving: true, message: "", isError: false });
    try {
      await api.put(`/api/admin/config/${key}`, { value });
      patch({ saving: false, message: "Saved.", isError: false });
      setConfig((c) => (c ? { ...c, [key]: value } : c));
    } catch (err) {
      patch({
        saving: false,
        message: (err as Error).message || "Save failed.",
        isError: true,
      });
    }
  }

  async function clearRetentionDate() {
    patchRetDate({ saving: true, message: "", isError: false });
    try {
      await api.put("/api/admin/config/retention_date", { value: "" });
      patchRetDate({ value: "", saving: false, message: "Cleared.", isError: false });
      setConfig((c) => (c ? { ...c, retention_date: null } : c));
    } catch (err) {
      patchRetDate({
        saving: false,
        message: (err as Error).message || "Clear failed.",
        isError: true,
      });
    }
  }

  async function handlePurge() {
    if (purgeInput !== PURGE_PHRASE) return;
    if (
      !window.confirm(
        "This will permanently delete all candidate data. This cannot be undone. Proceed?"
      )
    )
      return;
    setPurging(true);
    setPurgeError("");
    setPurgeResult(null);
    try {
      const res = (await api.post("/api/admin/purge", { confirm: purgeInput })) as {
        deleted: Record<string, number>;
      };
      setPurgeResult(res);
      setPurgeInput("");
    } catch (err) {
      setPurgeError((err as Error).message || "Purge failed.");
    } finally {
      setPurging(false);
    }
  }

  if (loadError) {
    return (
      <div>
        <h1>Settings &amp; data</h1>
        <p style={{ color: "red" }}>{loadError}</p>
        <p>
          <Link to="/admin">← Back to candidates</Link>
        </p>
      </div>
    );
  }

  if (!config) {
    return (
      <div>
        <h1>Settings &amp; data</h1>
        <p>Loading…</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, padding: "0 16px" }}>
      <h1>Settings &amp; data</h1>
      <p>
        <Link to="/admin">← Back to candidates</Link>
      </p>

      {/* Config section */}
      <section style={{ marginBottom: 32 }}>
        <h2>Configuration</h2>

        {/* prep_window_days */}
        <div style={{ marginBottom: 20 }}>
          <label htmlFor="prep_window_days" style={{ display: "block", fontWeight: "bold" }}>
            Prep window (days)
          </label>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <input
              id="prep_window_days"
              type="number"
              min={1}
              value={prepDays.value}
              onChange={(e) => patchPrepDays({ value: e.target.value, message: "", isError: false })}
              style={{ width: 100 }}
            />
            <button
              onClick={() => saveField("prep_window_days", prepDays.value, patchPrepDays)}
              disabled={prepDays.saving}
            >
              {prepDays.saving ? "Saving…" : "Save"}
            </button>
            {prepDays.message && (
              <span style={{ color: prepDays.isError ? "red" : "green", fontSize: 13 }}>
                {prepDays.message}
              </span>
            )}
          </div>
        </div>

        {/* retention_date */}
        <div style={{ marginBottom: 20 }}>
          <label htmlFor="retention_date" style={{ display: "block", fontWeight: "bold" }}>
            Retention reminder date
          </label>
          <p style={{ fontSize: 13, color: "#555", margin: "2px 0 6px" }}>
            Retention reminder — NOT enforced; the system never auto-deletes. Leave blank to keep
            unset.
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              id="retention_date"
              type="date"
              value={retDate.value}
              onChange={(e) => patchRetDate({ value: e.target.value, message: "", isError: false })}
            />
            <button
              onClick={() => saveField("retention_date", retDate.value, patchRetDate)}
              disabled={retDate.saving}
            >
              {retDate.saving ? "Saving…" : "Save"}
            </button>
            <button
              onClick={clearRetentionDate}
              disabled={retDate.saving}
              style={{ background: "#eee" }}
            >
              Clear
            </button>
            {retDate.message && (
              <span style={{ color: retDate.isError ? "red" : "green", fontSize: 13 }}>
                {retDate.message}
              </span>
            )}
          </div>
        </div>

        {/* qa_sla_text */}
        <div style={{ marginBottom: 20 }}>
          <label htmlFor="qa_sla_text" style={{ display: "block", fontWeight: "bold" }}>
            Q&amp;A SLA text
          </label>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginTop: 4 }}>
            <textarea
              id="qa_sla_text"
              rows={3}
              value={slaText.value}
              onChange={(e) => patchSlaText({ value: e.target.value, message: "", isError: false })}
              style={{ width: 360, resize: "vertical" }}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <button
                onClick={() => saveField("qa_sla_text", slaText.value, patchSlaText)}
                disabled={slaText.saving}
              >
                {slaText.saving ? "Saving…" : "Save"}
              </button>
              {slaText.message && (
                <span style={{ color: slaText.isError ? "red" : "green", fontSize: 13 }}>
                  {slaText.message}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* display_timezone */}
        <div style={{ marginBottom: 20 }}>
          <label htmlFor="display_timezone" style={{ display: "block", fontWeight: "bold" }}>
            Display timezone
          </label>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <input
              id="display_timezone"
              type="text"
              value={tz.value}
              onChange={(e) => patchTz({ value: e.target.value, message: "", isError: false })}
              placeholder="e.g. Europe/London"
              style={{ width: 220 }}
            />
            <button
              onClick={() => saveField("display_timezone", tz.value, patchTz)}
              disabled={tz.saving}
            >
              {tz.saving ? "Saving…" : "Save"}
            </button>
            {tz.message && (
              <span style={{ color: tz.isError ? "red" : "green", fontSize: 13 }}>
                {tz.message}
              </span>
            )}
          </div>
        </div>
      </section>

      {/* Danger zone */}
      <section
        style={{
          border: "2px solid #c0392b",
          borderRadius: 6,
          padding: "16px 20px",
          marginBottom: 32,
        }}
      >
        <h2 style={{ color: "#c0392b", marginTop: 0 }}>
          Danger zone — Purge all candidate data
        </h2>

        <p>
          <strong>This action permanently deletes:</strong>
        </p>
        <ul>
          <li>All candidates</li>
          <li>All bookings</li>
          <li>All candidate questions</li>
          <li>All download events</li>
          <li>All candidate audit rows</li>
        </ul>
        <p>
          <strong>This action keeps:</strong> admin account, config, slots, admin audit log.
        </p>

        {config.retention_date && (
          <p style={{ background: "#fff3cd", padding: "6px 10px", borderRadius: 4, fontSize: 13 }}>
            Retention reminder date: <strong>{config.retention_date}</strong>
          </p>
        )}
        {!config.retention_date && (
          <p style={{ fontSize: 13, color: "#888" }}>
            No retention reminder date is set. Configure one above if needed.
          </p>
        )}

        {purgeResult ? (
          <div
            style={{
              background: "#d4edda",
              border: "1px solid #28a745",
              borderRadius: 4,
              padding: "10px 14px",
              marginBottom: 12,
            }}
          >
            <strong>Purge complete.</strong> Records deleted:
            <ul style={{ margin: "6px 0 0" }}>
              {Object.entries(purgeResult.deleted).map(([k, v]) => (
                <li key={k}>
                  {k}: <strong>{v}</strong>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {purgeError && (
          <p style={{ color: "#c0392b", fontWeight: "bold" }}>{purgeError}</p>
        )}

        <div style={{ marginTop: 12 }}>
          <label htmlFor="purge_confirm" style={{ display: "block", marginBottom: 4 }}>
            To confirm, type exactly:{" "}
            <code style={{ background: "#f8d7da", padding: "1px 4px" }}>{PURGE_PHRASE}</code>
          </label>
          <input
            id="purge_confirm"
            type="text"
            value={purgeInput}
            onChange={(e) => {
              setPurgeInput(e.target.value);
              setPurgeError("");
              setPurgeResult(null);
            }}
            placeholder={PURGE_PHRASE}
            style={{ width: 320, fontFamily: "monospace" }}
            autoComplete="off"
          />
        </div>

        <button
          onClick={handlePurge}
          disabled={purgeInput !== PURGE_PHRASE || purging}
          style={{
            marginTop: 12,
            background: purgeInput === PURGE_PHRASE ? "#c0392b" : "#ccc",
            color: purgeInput === PURGE_PHRASE ? "#fff" : "#666",
            border: "none",
            padding: "8px 18px",
            borderRadius: 4,
            cursor: purgeInput === PURGE_PHRASE ? "pointer" : "not-allowed",
            fontWeight: "bold",
          }}
        >
          {purging ? "Purging…" : "Purge all candidate data"}
        </button>
      </section>
    </div>
  );
}
