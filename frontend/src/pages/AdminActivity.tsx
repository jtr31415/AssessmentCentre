import { useEffect, useState } from "react";
import { CheckIcon } from "lucide-react";
import { api } from "../api/client";

type ActivityRow = {
  candidate_id: string;
  first_name: string;
  status: string;
  has_booking: boolean;
  slot_starts_at: string | null;
  unlock_at: string | null;
  has_logged_in: boolean;
  downloads: Record<string, string | null>;
  key_revealed: boolean;
  question_count: number;
  nda_accepted_at: string | null;
  nda_declined_at: string | null;
};

function NdaBadge({ row }: { row: ActivityRow }) {
  if (row.nda_accepted_at) {
    return (
      <span className="px-2 py-0.5 rounded text-[9px] uppercase font-bold border bg-emerald-50 text-emerald-800 border-emerald-200">
        Accepted
      </span>
    );
  }
  if (row.nda_declined_at) {
    return (
      <span className="px-2 py-0.5 rounded text-[9px] uppercase font-bold border bg-red-50 text-red-800 border-red-300">
        Declined
      </span>
    );
  }
  return <span className="text-brand-muted">—</span>;
}

function fmt(ts: string | null) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString();
}

function Tick({ yes }: { yes: boolean }) {
  if (yes) {
    return (
      <span className="inline-flex items-center justify-center text-emerald-600" aria-label="Yes">
        <CheckIcon className="w-3.5 h-3.5" aria-hidden="true" />
        <span className="sr-only">Yes</span>
      </span>
    );
  }
  return (
    <span className="text-brand-muted" aria-label="No">
      —
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const lower = status.toLowerCase();
  const cls =
    lower === "active"
      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
      : lower === "invited"
      ? "bg-amber-50 text-amber-800 border-amber-200"
      : "bg-red-50 text-red-800 border-red-300";
  return (
    <span
      className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold border ${cls}`}
    >
      {status}
    </span>
  );
}

type ContentMeta = { file_key: string; label: string };

export default function AdminActivity() {
  const [rows, setRows] = useState<ActivityRow[]>([]);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [activity, content] = await Promise.all([
          api.get("/api/admin/activity"),
          api.get("/api/admin/content").catch(() => [] as ContentMeta[]),
        ]);
        setRows(activity as ActivityRow[]);
        const map: Record<string, string> = {};
        for (const c of content as ContentMeta[]) map[c.file_key] = c.label;
        setLabels(map);
      } catch (err) {
        setError((err as Error).message || "Failed to load activity.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const allFileKeys = Array.from(
    new Set(rows.flatMap((r) => Object.keys(r.downloads)))
  ).sort();

  const totalCols = 6 + allFileKeys.length + 2; // 6 fixed + file keys + Key Revealed + #Questions

  return (
    <div className="space-y-4">
      <div className="border border-brand-hair rounded-lg p-5 bg-white space-y-4 shadow-xs">
        {/* Panel header */}
        <div className="panel-title">
          <h2 className="font-bold text-brand-blue text-sm">
            Candidate Status Matrix
          </h2>
        </div>
        <p className="text-xs text-brand-muted ml-4">
          A comprehensive at-a-glance monitoring audit for progression tracking
          (fairness &amp; completeness).
        </p>

        {/* Loading state */}
        {loading && (
          <p className="ml-4 text-xs text-brand-muted animate-pulse">
            Loading activity data…
          </p>
        )}

        {/* Error state */}
        {error && (
          <p
            className="ml-4 text-xs text-brand-red bg-brand-redbg border border-brand-red rounded px-3 py-2"
            role="alert"
          >
            {error}
          </p>
        )}

        {/* Table — only rendered when not loading and no error */}
        {!loading && !error && (
          <div className="overflow-x-auto border border-brand-hair rounded-lg ml-4">
            <table
              className="w-full text-left border-collapse text-xs"
              aria-label="Candidate activity matrix"
            >
              <thead>
                <tr className="bg-brand-b5 border-b border-brand-hair text-brand-blue font-bold whitespace-nowrap">
                  <th
                    scope="col"
                    className="p-3 sticky left-0 bg-brand-b5 shadow-sm z-10 border-r border-brand-hair"
                  >
                    Candidate
                  </th>
                  <th scope="col" className="p-3">
                    Status
                  </th>
                  <th scope="col" className="p-3">
                    Booked Slot
                  </th>
                  <th scope="col" className="p-3">
                    Unlock At
                  </th>
                  <th scope="col" className="p-3 text-center">
                    Logged In
                  </th>
                  <th scope="col" className="p-3 text-center">
                    NDA
                  </th>
                  {allFileKeys.map((k) => (
                    <th key={k} scope="col" className="p-3 text-center">
                      {labels[k] ?? k}
                    </th>
                  ))}
                  <th scope="col" className="p-3 text-center">
                    Key Revealed
                  </th>
                  <th scope="col" className="p-3 text-center">
                    #&nbsp;Qs
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-hair font-mono">
                {rows.map((r) => (
                  <tr
                    key={r.candidate_id}
                    className="hover:bg-neutral-50 whitespace-nowrap text-[11px] text-brand-ink"
                  >
                    {/* Sticky candidate column */}
                    <td className="p-3 sticky left-0 bg-white border-r border-brand-hair shadow-xs">
                      <div className="flex flex-col">
                        <span className="font-bold font-sans text-brand-ink">
                          {r.first_name}
                        </span>
                        <span className="text-[10px] text-brand-muted tabular-numbers">
                          {r.candidate_id}
                        </span>
                      </div>
                    </td>

                    <td className="p-3">
                      <StatusBadge status={r.status} />
                    </td>

                    <td className="p-3 font-sans tabular-numbers text-brand-ink">
                      {r.slot_starts_at ? (
                        fmt(r.slot_starts_at)
                      ) : (
                        <span className="text-brand-muted">—</span>
                      )}
                    </td>

                    <td className="p-3 tabular-numbers text-brand-ink">
                      {r.unlock_at ? (
                        fmt(r.unlock_at)
                      ) : (
                        <span className="text-brand-muted">—</span>
                      )}
                    </td>

                    <td className="p-3 text-center">
                      <Tick yes={r.has_logged_in} />
                    </td>

                    <td className="p-3 text-center">
                      <NdaBadge row={r} />
                    </td>

                    {allFileKeys.map((k) => (
                      <td key={k} className="p-3 text-center">
                        <Tick yes={r.downloads[k] != null} />
                      </td>
                    ))}

                    <td className="p-3 text-center">
                      <Tick yes={r.key_revealed} />
                    </td>

                    <td className="p-3 text-center font-bold tabular-numbers text-brand-ink">
                      {r.question_count}
                    </td>
                  </tr>
                ))}

                {rows.length === 0 && (
                  <tr>
                    <td
                      colSpan={totalCols}
                      className="p-6 text-center text-brand-muted text-xs"
                    >
                      No activity data.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
