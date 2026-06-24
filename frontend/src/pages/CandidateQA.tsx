import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

interface Question {
  id: number;
  body: string;
  asked_at: string;
  answer: string | null;
  answered_at: string | null;
}

interface QAResponse {
  questions: Question[];
  sla_text: string;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function CandidateQA() {
  const [slaText, setSlaText] = useState<string>("");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loadError, setLoadError] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function fetchQuestions() {
    setLoadError("");
    try {
      const data = (await api.get("/api/me/questions")) as QAResponse;
      setSlaText(data.sla_text);
      setQuestions(data.questions);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }

  useEffect(() => {
    fetchQuestions();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      await api.post("/api/me/questions", { body: body.trim() });
      setBody("");
      textareaRef.current?.focus();
      await fetchQuestions();
    } catch (e) {
      setSubmitError((e as Error).message || "Failed to send question.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ padding: 16, maxWidth: 720 }}>
      <p style={{ marginBottom: 8 }}>
        <Link to="/dashboard">&larr; Back to dashboard</Link>
      </p>

      <h1>Ask the Assessor</h1>

      {/* SLA / expectation banner */}
      {slaText && (
        <div
          style={{
            background: "#e8f4fd",
            border: "1px solid #b3d8f5",
            borderRadius: 6,
            padding: "12px 16px",
            marginBottom: 24,
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
          }}
        >
          <span style={{ fontSize: 18, lineHeight: 1.4 }}>&#8505;</span>
          <p style={{ margin: 0, fontSize: 14, color: "#1a4a6e" }}>
            <strong>Human-answered:</strong> {slaText}
          </p>
        </div>
      )}

      {/* Submit form */}
      <form onSubmit={handleSubmit} style={{ marginBottom: 32 }}>
        <label
          htmlFor="qa-body"
          style={{ display: "block", fontWeight: 600, marginBottom: 6 }}
        >
          Your question
        </label>
        <textarea
          id="qa-body"
          ref={textareaRef}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
          style={{
            width: "100%",
            boxSizing: "border-box",
            padding: 8,
            fontSize: 14,
            resize: "vertical",
          }}
          placeholder="Type your question here…"
        />
        {submitError && (
          <p style={{ color: "red", margin: "6px 0 0" }}>{submitError}</p>
        )}
        <button
          type="submit"
          disabled={submitting || !body.trim()}
          style={{ marginTop: 10 }}
        >
          {submitting ? "Sending…" : "Send question"}
        </button>
      </form>

      {/* Question thread */}
      <h2 style={{ marginBottom: 12 }}>Your questions</h2>

      {loadError && (
        <p style={{ color: "red" }}>Could not load questions: {loadError}</p>
      )}

      {!loadError && questions.length === 0 && (
        <p style={{ color: "#666" }}>No questions yet. Ask one above.</p>
      )}

      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {questions.map((q) => (
          <li
            key={q.id}
            style={{
              border: "1px solid #ddd",
              borderRadius: 6,
              padding: 14,
              marginBottom: 14,
              background: "#fafafa",
            }}
          >
            {/* Question */}
            <p style={{ margin: "0 0 4px", fontWeight: 600 }}>{q.body}</p>
            <p style={{ margin: "0 0 10px", fontSize: 12, color: "#888" }}>
              Asked {formatDate(q.asked_at)}
            </p>

            {/* Answer or badge */}
            {q.answer !== null ? (
              <div
                style={{
                  borderLeft: "3px solid #4caf50",
                  paddingLeft: 10,
                  marginTop: 6,
                }}
              >
                <p style={{ margin: "0 0 4px", whiteSpace: "pre-wrap" }}>
                  {q.answer}
                </p>
                {q.answered_at && (
                  <p style={{ margin: 0, fontSize: 12, color: "#888" }}>
                    Answered {formatDate(q.answered_at)}
                  </p>
                )}
              </div>
            ) : (
              <span
                style={{
                  display: "inline-block",
                  background: "#fff3cd",
                  border: "1px solid #ffc107",
                  borderRadius: 4,
                  padding: "2px 8px",
                  fontSize: 12,
                  color: "#856404",
                  marginTop: 4,
                }}
              >
                Awaiting answer
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
