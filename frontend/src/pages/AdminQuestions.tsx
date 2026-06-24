import { useEffect, useState } from "react";
import { api } from "../api/client";

type Question = {
  id: number;
  candidate_id: string;
  first_name: string;
  body: string;
  asked_at: string;
  answer: string | null;
  answered_at: string | null;
  answered: boolean;
};

function fmt(ts: string | null) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString();
}

function AnswerForm({ q, onSaved }: { q: Question; onSaved: () => void }) {
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSaving(true);
    setError("");
    try {
      await api.post(`/api/admin/questions/${q.id}/answer`, { answer: text });
      setText("");
      onSaved();
    } catch (err) {
      setError((err as Error).message || "Failed to save answer.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} style={{ marginTop: 6 }}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        style={{ width: "100%", boxSizing: "border-box" }}
        placeholder="Type your answer…"
      />
      <button type="submit" disabled={saving || !text.trim()} style={{ marginTop: 4 }}>
        {saving ? "Saving…" : "Save"}
      </button>
      {error && <span style={{ color: "red", marginLeft: 8, fontSize: 13 }}>{error}</span>}
    </form>
  );
}

export default function AdminQuestions() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await api.get("/api/admin/questions");
      setQuestions(data as Question[]);
    } catch (err) {
      setError((err as Error).message || "Failed to load questions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const unanswered = questions.filter((q) => !q.answered);
  const answered = questions.filter((q) => q.answered);

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 16 }}>
      <h1>Questions Queue</h1>
      {loading && <p>Loading…</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loading && !error && (
        <>
          <h2>
            Unanswered{" "}
            {unanswered.length > 0 && (
              <span
                style={{
                  background: "#e53e3e",
                  color: "#fff",
                  borderRadius: 12,
                  padding: "2px 9px",
                  fontSize: 14,
                  fontWeight: 700,
                  verticalAlign: "middle",
                }}
              >
                {unanswered.length}
              </span>
            )}
          </h2>
          {unanswered.length === 0 && <p style={{ color: "#555" }}>No unanswered questions.</p>}
          {unanswered.map((q) => (
            <div
              key={q.id}
              style={{
                border: "2px solid #e53e3e",
                borderRadius: 6,
                padding: 12,
                marginBottom: 12,
                background: "#fff5f5",
              }}
            >
              <div style={{ marginBottom: 4 }}>
                <strong>{q.first_name}</strong>{" "}
                <span style={{ color: "#555", fontSize: 13 }}>({q.candidate_id})</span>{" "}
                <span style={{ fontSize: 12, color: "#888" }}>asked {fmt(q.asked_at)}</span>
              </div>
              <p style={{ margin: "4px 0 8px" }}>{q.body}</p>
              <AnswerForm q={q} onSaved={load} />
            </div>
          ))}

          <h2>Answered</h2>
          {answered.length === 0 && <p style={{ color: "#555" }}>No answered questions yet.</p>}
          {answered.map((q) => (
            <div
              key={q.id}
              style={{
                border: "1px solid #ccc",
                borderRadius: 6,
                padding: 12,
                marginBottom: 12,
                background: "#f9f9f9",
              }}
            >
              <div style={{ marginBottom: 4 }}>
                <strong>{q.first_name}</strong>{" "}
                <span style={{ color: "#555", fontSize: 13 }}>({q.candidate_id})</span>{" "}
                <span style={{ fontSize: 12, color: "#888" }}>asked {fmt(q.asked_at)}</span>
              </div>
              <p style={{ margin: "4px 0 8px" }}>{q.body}</p>
              <div
                style={{
                  background: "#e8f5e9",
                  border: "1px solid #a5d6a7",
                  borderRadius: 4,
                  padding: "8px 10px",
                  fontSize: 14,
                }}
              >
                <strong>Answer</strong>{" "}
                <span style={{ fontSize: 12, color: "#555" }}>(answered {fmt(q.answered_at)})</span>
                <p style={{ margin: "4px 0 0" }}>{q.answer}</p>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
