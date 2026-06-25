import { useEffect, useState } from "react";
import { AlertTriangle, ShieldAlert } from "lucide-react";
import { api } from "../api/client";

interface ConfigMap {
  prep_window_days: string;
  retention_date: string | null;
  qa_sla_text: string;
  display_timezone: string;
  assessment_format: string;
  assessment_duration: string;
  assessment_location: string;
  api_docs_url: string;
  api_tier: string;
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
  const [fmt, patchFmt] = useFieldState("");
  const [dur, patchDur] = useFieldState("");
  const [loc, patchLoc] = useFieldState("");
  const [docsUrl, patchDocsUrl] = useFieldState("");
  const [apiTier, patchApiTier] = useFieldState("");

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
        patchFmt({ value: cfg.assessment_format ?? "" });
        patchDur({ value: cfg.assessment_duration ?? "" });
        patchLoc({ value: cfg.assessment_location ?? "" });
        patchDocsUrl({ value: cfg.api_docs_url ?? "" });
        patchApiTier({ value: cfg.api_tier ?? "" });
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
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-brand-blue">Settings &amp; data</h1>
        <div className="p-4 bg-brand-redbg border border-brand-red text-brand-red text-sm rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{loadError}</span>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-brand-blue">Settings &amp; data</h1>
        <p className="text-sm text-brand-muted">Loading…</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Configuration Settings */}
      <div className="border border-brand-hair rounded-lg p-5 bg-white space-y-6 shadow-xs">
        <div className="panel-title">
          <h2 className="font-bold text-brand-blue text-sm">Configuration Settings</h2>
        </div>

        <div className="ml-4 space-y-6">
          {/* prep_window_days */}
          <div>
            <label
              htmlFor="prep_window_days"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Prep Window Duration (Days)
            </label>
            <div className="flex items-center gap-3">
              <input
                id="prep_window_days"
                type="number"
                min={1}
                value={prepDays.value}
                onChange={(e) =>
                  patchPrepDays({ value: e.target.value, message: "", isError: false })
                }
                className="w-28 text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue tabular-numbers"
              />
              <button
                onClick={() => saveField("prep_window_days", prepDays.value, patchPrepDays)}
                disabled={prepDays.saving}
                className="px-4 py-2 bg-brand-blue text-white hover:bg-opacity-90 text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                {prepDays.saving ? "Saving…" : "Save"}
              </button>
              {prepDays.message && (
                <span
                  className={`text-xs font-medium ${
                    prepDays.isError ? "text-brand-red" : "text-emerald-700"
                  }`}
                >
                  {prepDays.message}
                </span>
              )}
            </div>
            <p className="text-[10px] text-brand-muted mt-1">
              Number of days candidates have to preview materials before their slot.
            </p>
          </div>

          {/* retention_date */}
          <div>
            <label
              htmlFor="retention_date"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Retention Reminder Date
            </label>
            <div className="flex items-center gap-3 flex-wrap">
              <input
                id="retention_date"
                type="date"
                value={retDate.value}
                onChange={(e) =>
                  patchRetDate({ value: e.target.value, message: "", isError: false })
                }
                className="text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue tabular-numbers"
              />
              <button
                onClick={() => saveField("retention_date", retDate.value, patchRetDate)}
                disabled={retDate.saving}
                className="px-4 py-2 bg-brand-blue text-white hover:bg-opacity-90 text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                {retDate.saving ? "Saving…" : "Save"}
              </button>
              <button
                onClick={clearRetentionDate}
                disabled={retDate.saving}
                className="px-4 py-2 bg-white text-brand-muted hover:text-brand-ink border border-brand-hair text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                Clear
              </button>
              {retDate.message && (
                <span
                  className={`text-xs font-medium ${
                    retDate.isError ? "text-brand-red" : "text-emerald-700"
                  }`}
                >
                  {retDate.message}
                </span>
              )}
            </div>
            <p className="text-[10px] text-brand-muted mt-1">
              Retention reminder — NOT enforced; the system never auto-deletes. Leave blank to keep
              unset.
            </p>
          </div>

          {/* qa_sla_text */}
          <div>
            <label
              htmlFor="qa_sla_text"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Q&amp;A Service-Level Agreement (SLA) Text
            </label>
            <textarea
              id="qa_sla_text"
              rows={3}
              value={slaText.value}
              onChange={(e) =>
                patchSlaText({ value: e.target.value, message: "", isError: false })
              }
              className="w-full text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue resize-y"
            />
            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={() => saveField("qa_sla_text", slaText.value, patchSlaText)}
                disabled={slaText.saving}
                className="px-4 py-2 bg-brand-blue text-white hover:bg-opacity-90 text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                {slaText.saving ? "Saving…" : "Save"}
              </button>
              {slaText.message && (
                <span
                  className={`text-xs font-medium ${
                    slaText.isError ? "text-brand-red" : "text-emerald-700"
                  }`}
                >
                  {slaText.message}
                </span>
              )}
            </div>
            <p className="text-[10px] text-brand-muted mt-1">
              Shown inside the candidate's Q&amp;A dashboard portal. Sets human expectations.
            </p>
          </div>

          {/* display_timezone */}
          <div>
            <label
              htmlFor="display_timezone"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Display Timezone Descriptor
            </label>
            <div className="flex items-center gap-3 flex-wrap">
              <input
                id="display_timezone"
                type="text"
                value={tz.value}
                onChange={(e) => patchTz({ value: e.target.value, message: "", isError: false })}
                placeholder="e.g. Europe/London"
                className="w-56 text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              />
              <button
                onClick={() => saveField("display_timezone", tz.value, patchTz)}
                disabled={tz.saving}
                className="px-4 py-2 bg-brand-blue text-white hover:bg-opacity-90 text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                {tz.saving ? "Saving…" : "Save"}
              </button>
              {tz.message && (
                <span
                  className={`text-xs font-medium ${
                    tz.isError ? "text-brand-red" : "text-emerald-700"
                  }`}
                >
                  {tz.message}
                </span>
              )}
            </div>
          </div>

          {/* assessment_format */}
          <div>
            <label
              htmlFor="assessment_format"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Assessment Format
            </label>
            <div className="flex items-center gap-3 flex-wrap">
              <input
                id="assessment_format"
                type="text"
                value={fmt.value}
                onChange={(e) => patchFmt({ value: e.target.value, message: "", isError: false })}
                placeholder="e.g. In person"
                className="w-72 text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              />
              <button
                onClick={() => saveField("assessment_format", fmt.value, patchFmt)}
                disabled={fmt.saving}
                className="px-4 py-2 bg-brand-blue text-white hover:bg-opacity-90 text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                {fmt.saving ? "Saving…" : "Save"}
              </button>
              {fmt.message && (
                <span
                  className={`text-xs font-medium ${
                    fmt.isError ? "text-brand-red" : "text-emerald-700"
                  }`}
                >
                  {fmt.message}
                </span>
              )}
            </div>
            <p className="text-[10px] text-brand-muted mt-1">
              Shown to candidates on the booking page and dashboard.
            </p>
          </div>

          {/* assessment_duration */}
          <div>
            <label
              htmlFor="assessment_duration"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Assessment Duration
            </label>
            <div className="flex items-center gap-3 flex-wrap">
              <input
                id="assessment_duration"
                type="text"
                value={dur.value}
                onChange={(e) => patchDur({ value: e.target.value, message: "", isError: false })}
                placeholder="e.g. 2 hours"
                className="w-72 text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              />
              <button
                onClick={() => saveField("assessment_duration", dur.value, patchDur)}
                disabled={dur.saving}
                className="px-4 py-2 bg-brand-blue text-white hover:bg-opacity-90 text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                {dur.saving ? "Saving…" : "Save"}
              </button>
              {dur.message && (
                <span
                  className={`text-xs font-medium ${
                    dur.isError ? "text-brand-red" : "text-emerald-700"
                  }`}
                >
                  {dur.message}
                </span>
              )}
            </div>
          </div>

          {/* assessment_location */}
          <div>
            <label
              htmlFor="assessment_location"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Assessment Location
            </label>
            <div className="flex items-center gap-3 flex-wrap">
              <input
                id="assessment_location"
                type="text"
                value={loc.value}
                onChange={(e) => patchLoc({ value: e.target.value, message: "", isError: false })}
                placeholder="e.g. Nordex HQ, Hamburg"
                className="w-full sm:w-96 text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              />
              <button
                onClick={() => saveField("assessment_location", loc.value, patchLoc)}
                disabled={loc.saving}
                className="px-4 py-2 bg-brand-blue text-white hover:bg-opacity-90 text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                {loc.saving ? "Saving…" : "Save"}
              </button>
              {loc.message && (
                <span
                  className={`text-xs font-medium ${
                    loc.isError ? "text-brand-red" : "text-emerald-700"
                  }`}
                >
                  {loc.message}
                </span>
              )}
            </div>
          </div>

          {/* api_docs_url */}
          <div>
            <label
              htmlFor="api_docs_url"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              API Documentation Link
            </label>
            <div className="flex items-center gap-3 flex-wrap">
              <input
                id="api_docs_url"
                type="url"
                value={docsUrl.value}
                onChange={(e) =>
                  patchDocsUrl({ value: e.target.value, message: "", isError: false })
                }
                placeholder="https://docs.claude.com"
                className="w-full sm:w-96 text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              />
              <button
                onClick={() => saveField("api_docs_url", docsUrl.value, patchDocsUrl)}
                disabled={docsUrl.saving}
                className="px-4 py-2 bg-brand-blue text-white hover:bg-opacity-90 text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                {docsUrl.saving ? "Saving…" : "Save"}
              </button>
              {docsUrl.message && (
                <span
                  className={`text-xs font-medium ${
                    docsUrl.isError ? "text-brand-red" : "text-emerald-700"
                  }`}
                >
                  {docsUrl.message}
                </span>
              )}
            </div>
            <p className="text-[10px] text-brand-muted mt-1">
              Shown to candidates next to their API key.
            </p>
          </div>

          {/* api_tier */}
          <div>
            <label
              htmlFor="api_tier"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              API Tier (rate-limit guidance)
            </label>
            <div className="flex items-center gap-3 flex-wrap">
              <input
                id="api_tier"
                type="text"
                value={apiTier.value}
                onChange={(e) =>
                  patchApiTier({ value: e.target.value, message: "", isError: false })
                }
                placeholder="e.g. Tier 1"
                className="w-72 text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              />
              <button
                onClick={() => saveField("api_tier", apiTier.value, patchApiTier)}
                disabled={apiTier.saving}
                className="px-4 py-2 bg-brand-blue text-white hover:bg-opacity-90 text-xs font-semibold rounded cursor-pointer disabled:opacity-50"
              >
                {apiTier.saving ? "Saving…" : "Save"}
              </button>
              {apiTier.message && (
                <span
                  className={`text-xs font-medium ${
                    apiTier.isError ? "text-brand-red" : "text-emerald-700"
                  }`}
                >
                  {apiTier.message}
                </span>
              )}
            </div>
            <p className="text-[10px] text-brand-muted mt-1">
              Tells candidates which rate-limit tier their key is on.
            </p>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div
        className="border border-brand-red rounded-lg p-5 bg-brand-redbg space-y-4"
        id="danger-zone"
      >
        <div className="flex items-center gap-2 text-brand-red">
          <ShieldAlert className="w-5 h-5 flex-shrink-0" />
          <h2 className="font-bold text-sm uppercase tracking-wider">
            Danger Zone — Purge all candidate data
          </h2>
        </div>

        <div className="ml-4 space-y-4 text-xs text-brand-ink leading-relaxed">
          <p>
            This action is destructive and{" "}
            <strong className="text-brand-red">permanent</strong>. It deletes all candidate
            audit histories, questions, bookings, and logins, resetting the assessment pipeline.
          </p>

          {/* What's deleted / kept */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-white border border-brand-hair p-4 rounded-lg">
            <div>
              <p className="font-bold text-brand-red mb-1">This action permanently deletes:</p>
              <ul className="list-disc pl-4 space-y-0.5 text-brand-ink font-semibold">
                <li>All candidates</li>
                <li>All bookings</li>
                <li>All candidate questions</li>
                <li>All download events</li>
                <li>All candidate audit rows</li>
              </ul>
            </div>
            <div>
              <p className="font-bold text-brand-blue mb-1">This action preserves:</p>
              <ul className="list-disc pl-4 space-y-0.5 text-brand-muted">
                <li>Admin account</li>
                <li>Config</li>
                <li>Slots</li>
                <li>Admin audit log</li>
              </ul>
            </div>
          </div>

          {/* Retention reminder */}
          {config.retention_date ? (
            <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-300 text-amber-900 text-xs rounded">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-600" />
              <span>
                Retention reminder date:{" "}
                <strong className="font-mono tabular-numbers">{config.retention_date}</strong>
              </span>
            </div>
          ) : (
            <p className="text-[11px] text-brand-muted italic">
              No retention reminder date is set. Configure one above if needed.
            </p>
          )}

          {/* Purge success result */}
          {purgeResult && (
            <div className="p-4 bg-amber-50 border border-amber-400 text-amber-900 rounded space-y-2">
              <p className="font-bold text-xs uppercase tracking-wider">
                Purge complete. Records deleted:
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(purgeResult.deleted).map(([k, v]) => (
                  <div
                    key={k}
                    className="bg-white p-2 rounded border border-amber-200 min-w-[80px] text-center"
                  >
                    <p className="text-[10px] text-brand-muted font-sans font-semibold uppercase">
                      {k}
                    </p>
                    <p className="text-brand-red font-mono font-bold tabular-numbers">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Purge error */}
          {purgeError && (
            <div className="p-3 bg-brand-redbg border border-brand-red text-brand-red text-xs rounded flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{purgeError}</span>
            </div>
          )}

          {/* Confirmation input + button */}
          <div className="space-y-3">
            <label
              htmlFor="purge_confirm"
              className="block text-[11px] font-semibold text-brand-ink uppercase tracking-wider"
            >
              To confirm, type exactly:{" "}
              <code className="font-mono bg-white border border-brand-hair px-1.5 py-0.5 text-brand-red rounded font-bold normal-case tracking-normal">
                {PURGE_PHRASE}
              </code>
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
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
                autoComplete="off"
                className="flex-1 text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-red font-mono"
              />
              <button
                onClick={handlePurge}
                disabled={purgeInput !== PURGE_PHRASE || purging}
                className="px-5 py-2 bg-brand-red text-white text-xs font-bold rounded hover:bg-opacity-90 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center gap-1 whitespace-nowrap"
              >
                <ShieldAlert className="w-4 h-4" />
                {purging ? "Purging…" : "Purge all candidate data"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
