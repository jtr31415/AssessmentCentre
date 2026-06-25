import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Check, MessageSquare } from "lucide-react";

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

  const labelId = `answer-label-${q.id}`;

  return (
    <form onSubmit={save} className="space-y-2">
      <label
        id={labelId}
        className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted"
      >
        Answer Text
      </label>
      <textarea
        aria-labelledby={labelId}
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type response for the candidate…"
        className="w-full text-xs border border-brand-hair rounded p-2.5 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue resize-y"
      />
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={saving || !text.trim()}
          className="px-4 py-2 bg-brand-blue text-white text-xs font-semibold rounded hover:bg-opacity-90 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saving ? "Saving…" : "Submit Answer"}
        </button>
        {error && (
          <span className="text-xs text-brand-red">{error}</span>
        )}
      </div>
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

  useEffect(() => {
    load();
  }, []);

  const unanswered = questions.filter((q) => !q.answered);
  const answered = questions.filter((q) => q.answered);

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-8">
      {/* Page heading */}
      <div className="flex items-center gap-3 pb-4 border-b border-brand-hair">
        <MessageSquare className="w-5 h-5 text-brand-blue flex-shrink-0" />
        <h1 className="text-xl font-bold text-brand-blue">Questions Queue</h1>
      </div>

      {/* Loading */}
      {loading && (
        <p className="text-sm text-brand-muted">Loading…</p>
      )}

      {/* Error */}
      {!loading && error && (
        <p className="text-sm text-brand-red bg-brand-redbg border border-brand-red rounded px-3 py-2">
          {error}
        </p>
      )}

      {!loading && !error && (
        <>
          {/* ── Unanswered Queue ── */}
          <div className="space-y-4">
            <h2 className="font-bold text-brand-blue text-sm flex items-center gap-2 uppercase tracking-wider">
              <span>Unanswered Queue</span>
              {unanswered.length > 0 && (
                <span className="bg-brand-red text-white text-[10px] px-2 py-0.5 rounded-full font-bold tabular-numbers">
                  {unanswered.length}
                </span>
              )}
            </h2>

            {unanswered.length === 0 ? (
              <div className="p-8 text-center text-brand-muted border border-dashed border-brand-hair rounded bg-neutral-50">
                <Check className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                <p className="text-xs">All candidate questions answered. Excellent triage state.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {unanswered.map((q) => (
                  <div
                    key={q.id}
                    className="border border-brand-red rounded-lg p-5 bg-white space-y-4 shadow-xs"
                  >
                    {/* Card header */}
                    <div className="flex flex-wrap justify-between items-start gap-3 border-b border-brand-hair pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-brand-blue text-xs">
                          {q.first_name}
                        </span>
                        <code className="text-[10px] text-brand-muted font-mono bg-brand-b5 px-1.5 py-0.5 rounded">
                          {q.candidate_id}
                        </code>
                      </div>
                      <span className="text-[10px] text-brand-muted font-mono tabular-numbers">
                        Asked: {fmt(q.asked_at)}
                      </span>
                    </div>

                    {/* Question body */}
                    <p className="text-xs font-semibold text-brand-ink leading-relaxed pl-2 border-l-2 border-brand-red bg-neutral-50 py-2 rounded-r">
                      {q.body}
                    </p>

                    {/* Inline answer form */}
                    <AnswerForm q={q} onSaved={load} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Answered Archive ── */}
          <div className="space-y-4">
            <h2 className="font-bold text-brand-blue text-sm uppercase tracking-wider">
              Answered Archive
            </h2>

            {answered.length === 0 ? (
              <div className="p-8 text-center text-brand-muted border border-dashed border-brand-hair rounded">
                <p className="text-xs">No questions have been answered yet.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {answered.map((q) => (
                  <div
                    key={q.id}
                    className="border border-brand-hair rounded-lg p-4 bg-neutral-50 space-y-2"
                  >
                    {/* Card header */}
                    <div className="flex flex-wrap justify-between items-start gap-3">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-brand-ink text-xs">
                          {q.first_name}
                        </span>
                        <code className="text-[10px] text-brand-muted font-mono">
                          ({q.candidate_id})
                        </code>
                      </div>
                      <span className="text-[10px] text-brand-muted tabular-numbers">
                        Asked: {fmt(q.asked_at)}
                      </span>
                    </div>

                    {/* Question body (muted, italic) */}
                    <p className="text-xs text-brand-muted pl-2 border-l border-brand-muted italic">
                      "{q.body}"
                    </p>

                    {/* Answer block */}
                    <div className="bg-white border border-brand-hair p-3 rounded text-xs mt-2">
                      <p className="font-bold text-brand-blue mb-1">
                        Assessor Answer{" "}
                        <span className="font-normal text-brand-muted tabular-numbers">
                          (answered {fmt(q.answered_at)})
                        </span>
                      </p>
                      <p className="text-brand-ink leading-relaxed">{q.answer}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
