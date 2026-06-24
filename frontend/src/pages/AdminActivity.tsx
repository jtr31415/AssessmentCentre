import { useEffect, useState } from "react";
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
};

function fmt(ts: string | null) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString();
}

function Check({ yes }: { yes: boolean }) {
  return <span style={{ color: yes ? "green" : "#999" }}>{yes ? "✓" : "—"}</span>;
}

export default function AdminActivity() {
  const [rows, setRows] = useState<ActivityRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const data = await api.get("/api/admin/activity");
        setRows(data as ActivityRow[]);
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

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 16, overflowX: "auto" }}>
      <h1>Activity Overview</h1>
      {loading && <p>Loading…</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
      {!loading && !error && (
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 14 }}>
          <thead>
            <tr style={{ background: "#f0f0f0" }}>
              <th style={th}>Candidate</th>
              <th style={th}>Status</th>
              <th style={th}>Booked Slot</th>
              <th style={th}>Unlock At</th>
              <th style={th}>Logged In</th>
              {allFileKeys.map((k) => (
                <th key={k} style={th}>{k}</th>
              ))}
              <th style={th}>Key Revealed</th>
              <th style={th}>#Questions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.candidate_id} style={{ borderBottom: "1px solid #e0e0e0" }}>
                <td style={td}>
                  <strong>{r.first_name}</strong>
                  <br />
                  <span style={{ fontSize: 12, color: "#666" }}>{r.candidate_id}</span>
                </td>
                <td style={td}>{r.status}</td>
                <td style={td}>{fmt(r.slot_starts_at)}</td>
                <td style={td}>{fmt(r.unlock_at)}</td>
                <td style={{ ...td, textAlign: "center" }}>
                  <Check yes={r.has_logged_in} />
                </td>
                {allFileKeys.map((k) => (
                  <td key={k} style={{ ...td, textAlign: "center" }}>
                    <Check yes={r.downloads[k] != null} />
                  </td>
                ))}
                <td style={{ ...td, textAlign: "center" }}>
                  <Check yes={r.key_revealed} />
                </td>
                <td style={{ ...td, textAlign: "center" }}>{r.question_count}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5 + allFileKeys.length} style={{ ...td, color: "#888", textAlign: "center" }}>
                  No activity data.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

const th: React.CSSProperties = {
  padding: "8px 10px",
  textAlign: "left",
  fontWeight: 600,
  border: "1px solid #ddd",
  whiteSpace: "nowrap",
};

const td: React.CSSProperties = {
  padding: "6px 10px",
  border: "1px solid #ddd",
  verticalAlign: "top",
};
