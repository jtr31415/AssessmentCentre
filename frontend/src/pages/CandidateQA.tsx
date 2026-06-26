import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Check, Clock, MessageSquare, ShieldCheck } from "lucide-react";
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
  const [submitSuccess, setSubmitSuccess] = useState(false);
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
    setSubmitSuccess(false);
    try {
      await api.post("/api/me/questions", { body: body.trim() });
      setBody("");
      setSubmitSuccess(true);
      textareaRef.current?.focus();
      await fetchQuestions();
    } catch (e) {
      setSubmitError((e as Error).message || "Failed to send question.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back link + heading */}
      <div className="flex items-center gap-2">
        <Link
          to="/dashboard"
          className="p-1 rounded hover:bg-brand-b5 text-brand-muted hover:text-brand-ink transition-colors"
          aria-label="Back to dashboard"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-bold text-brand-blue">Ask the Assessor</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Main column */}
        <div className="md:col-span-8 space-y-6">
          {/* Privacy banner */}
          <div className="bg-emerald-50 border border-emerald-300 p-4 rounded-lg flex items-start gap-3 text-emerald-900">
            <ShieldCheck className="w-5 h-5 mt-0.5 flex-shrink-0 text-emerald-600" />
            <p className="text-xs leading-relaxed">
              <strong>This thread is private.</strong> Both your questions and your
              assessor's answers are confidential — visible only to you and your assessor.
              No other candidate can see them.
            </p>
          </div>

          {/* SLA banner */}
          {slaText && (
            <div className="bg-brand-b5 border border-brand-b4 p-4 rounded-lg flex items-start gap-3 text-brand-blue">
              <MessageSquare className="w-5 h-5 mt-0.5 flex-shrink-0 text-brand-blue" />
              <div>
                <h2 className="font-semibold text-xs uppercase tracking-wider">
                  Human-Answered Assistant
                </h2>
                <p className="text-xs text-brand-ink mt-0.5">{slaText}</p>
              </div>
            </div>
          )}

          {/* New Question card */}
          <div className="border border-brand-hair rounded-lg p-5 bg-white space-y-4">
            <div className="panel-title">
              <h3 className="font-bold text-brand-blue text-sm">New Question</h3>
            </div>

            <form onSubmit={handleSubmit} className="ml-4 space-y-4">
              <div>
                <label
                  htmlFor="qa-body"
                  className="block text-xs font-semibold text-brand-ink mb-1.5 uppercase tracking-wider"
                >
                  Your question
                </label>
                <textarea
                  id="qa-body"
                  ref={textareaRef}
                  value={body}
                  onChange={(e) => {
                    setBody(e.target.value);
                    if (submitSuccess) setSubmitSuccess(false);
                  }}
                  rows={4}
                  placeholder="Type your question here…"
                  disabled={submitting}
                  className="w-full text-sm border border-brand-hair rounded p-3 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue resize-y"
                />
                <p className="text-[10px] text-brand-muted mt-1">
                  Keep your questions concise. Your assessor will answer inline below.
                  Only you and your assessor can see your questions and their answers.
                </p>
              </div>

              {submitSuccess && (
                <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs rounded flex items-center gap-1.5 animate-fade-in">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Question sent. Your assessor has been notified.</span>
                </div>
              )}

              {submitError && (
                <p className="text-xs text-brand-red mt-1">{submitError}</p>
              )}

              <button
                type="submit"
                disabled={submitting || !body.trim()}
                className="px-4 py-2 bg-brand-blue hover:opacity-90 text-white font-semibold text-xs rounded cursor-pointer disabled:opacity-50 transition-opacity"
              >
                {submitting ? "Sending…" : "Send Question"}
              </button>
            </form>
          </div>

          {/* Private thread */}
          <div className="space-y-4">
            <h3 className="font-bold text-brand-blue text-sm uppercase tracking-wider border-b border-brand-hair pb-1.5">
              Your Questions (Strictly Private)
            </h3>

            {loadError && (
              <p className="text-xs text-brand-red">
                Could not load questions: {loadError}
              </p>
            )}

            {!loadError && questions.length === 0 ? (
              <div className="p-8 text-center text-brand-muted border border-dashed border-brand-hair rounded bg-brand-codebg">
                <MessageSquare className="w-8 h-8 text-brand-idle mx-auto mb-2" />
                <p className="text-xs">
                  No questions asked yet. Use the form above to query your assessor.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {questions.map((q) => (
                  <div
                    key={q.id}
                    className="border border-brand-hair rounded-lg p-4 bg-white space-y-3"
                  >
                    {/* Meta row */}
                    <div className="flex justify-between items-start gap-4">
                      <span className="text-[10px] bg-brand-codebg border border-brand-hair text-brand-muted font-mono px-1.5 py-0.5 rounded">
                        ID: {q.id}
                      </span>
                      <span className="text-[10px] text-brand-muted tabular-numbers">
                        Asked: {formatDate(q.asked_at)}
                      </span>
                    </div>

                    {/* Question body */}
                    <div className="text-xs font-medium text-brand-ink pl-2 border-l-2 border-brand-blue">
                      {q.body}
                    </div>

                    {/* Answer or awaiting */}
                    {q.answer !== null ? (
                      <div className="mt-2 bg-brand-b5 border border-brand-b4 p-3 rounded text-xs text-brand-blue space-y-1">
                        <p className="font-bold">Assessor Answer:</p>
                        <p className="text-brand-ink leading-relaxed whitespace-pre-wrap">
                          {q.answer}
                        </p>
                        {q.answered_at && (
                          <p className="text-[10px] text-brand-muted text-right pt-1 border-t border-brand-b4 tabular-numbers">
                            Answered: {formatDate(q.answered_at)}
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="mt-2 inline-flex items-center gap-1 text-[10px] bg-brand-redbg border border-brand-red text-brand-red px-2 py-1 rounded font-semibold uppercase animate-pulse">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Awaiting answer</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Support sidebar */}
        <div className="md:col-span-4">
          <div className="border border-brand-hair rounded-lg p-5 bg-brand-codebg space-y-3 text-xs text-brand-muted">
            <h3 className="font-bold text-brand-blue">Assessment Support</h3>
            <p className="leading-relaxed">
              Your assessor answers questions personally during European business hours.
              Both your questions and their answers stay strictly private — visible only
              to you and your assessor, never to other candidates.
            </p>
            <p className="leading-relaxed">
              Please keep your questions concise and specific to the assessment
              materials to receive the most accurate response.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
