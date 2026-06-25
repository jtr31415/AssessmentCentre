import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Copy,
  Database,
  Download,
  Eye,
  EyeOff,
  FileText,
  HelpCircle,
  Key,
  Lock,
  ShieldCheck,
} from "lucide-react";
import { api } from "../api/client";
import Countdown from "../components/Countdown";

interface NoBooking {
  has_booking: false;
}

interface HasBooking {
  has_booking: true;
  slot_starts_at: string;
  unlock_at: string;
  unlocked: boolean;
}

type BookingState = NoBooking | HasBooking;

interface ContentItem {
  file_key: string;
  label: string;
  description: string | null;
  category: string;
}

interface ApiKeyInfo {
  api_key: string;
  note: string;
}

const CATEGORY_ORDER: string[] = ["brief", "data", "reference"];
const CATEGORY_LABELS: Record<string, string> = {
  brief: "Exercise Brief",
  data: "Data Files",
  reference: "Reference Material",
};
const CATEGORY_ICONS: Record<
  string,
  React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>
> = {
  brief: BookOpen,
  data: Database,
  reference: FileText,
};

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// Content panel — category tabs, each file shows its description + download.
// (No in-browser preview: download is the single, reliable action.)
// ---------------------------------------------------------------------------

function ContentTabs({ items }: { items: ContentItem[] }) {
  const grouped: Record<string, ContentItem[]> = {};
  for (const item of items) {
    if (!grouped[item.category]) grouped[item.category] = [];
    grouped[item.category].push(item);
  }
  const categories = [
    ...CATEGORY_ORDER.filter((c) => grouped[c]?.length),
    ...Object.keys(grouped).filter(
      (c) => !CATEGORY_ORDER.includes(c) && grouped[c]?.length
    ),
  ];

  const [activeTab, setActiveTab] = useState<string>(categories[0] ?? "");
  const activeFiles = grouped[activeTab] ?? [];

  return (
    <div className="border border-brand-hair rounded-lg bg-white overflow-hidden">
      {/* Tab bar */}
      <div
        className="flex border-b border-brand-hair px-2"
        role="tablist"
        aria-label="Assessment materials"
      >
        {categories.map((cat) => {
          const Icon = CATEGORY_ICONS[cat] ?? FileText;
          const isActive = cat === activeTab;
          return (
            <button
              key={cat}
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(cat)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 -mb-px transition-colors cursor-pointer ${
                isActive
                  ? "text-brand-blue border-brand-blue"
                  : "text-brand-muted border-transparent hover:text-brand-ink"
              }`}
            >
              <Icon className="w-4 h-4" aria-hidden={true} />
              {CATEGORY_LABELS[cat] ?? cat}
            </button>
          );
        })}
      </div>

      {/* File list for the active tab */}
      <div className="p-5 space-y-3">
        {activeFiles.map((file) => (
          <div
            key={file.file_key}
            className="flex items-start justify-between gap-4 border border-brand-hair rounded-lg p-4 bg-white"
          >
            <div className="flex items-start gap-3 min-w-0">
              <FileText
                className="w-4 h-4 text-brand-muted flex-shrink-0 mt-0.5"
                aria-hidden={true}
              />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-brand-ink">{file.label}</p>
                {file.description && (
                  <p className="text-xs text-brand-muted mt-1 leading-relaxed whitespace-pre-wrap">
                    {file.description}
                  </p>
                )}
              </div>
            </div>
            <a
              href={"/api/content/" + file.file_key}
              download
              className="flex items-center gap-1.5 text-xs font-semibold text-white bg-brand-blue rounded px-3 py-2 hover:opacity-90 transition-opacity flex-shrink-0"
            >
              <Download className="w-3.5 h-3.5" aria-hidden={true} />
              Download
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

function UnlockedContent() {
  const [items, setItems] = useState<ContentItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/content")
      .then((d) => setItems(d as ContentItem[]))
      .catch((e) => setError((e as Error).message));
  }, []);

  if (error) {
    return (
      <div className="border border-brand-hair rounded-lg bg-white p-6">
        <p
          className="text-sm text-brand-red bg-brand-redbg border border-brand-red rounded p-3"
          role="alert"
        >
          Could not load files: {error}
        </p>
      </div>
    );
  }

  if (items === null) {
    return (
      <div className="border border-brand-hair rounded-lg bg-white p-6">
        <p className="text-sm text-brand-muted">Loading files…</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="border border-brand-hair rounded-lg bg-white p-6">
        <p className="text-sm text-brand-muted">No files available yet.</p>
      </div>
    );
  }

  return <ContentTabs items={items} />;
}

// ---------------------------------------------------------------------------
// API-key card
// ---------------------------------------------------------------------------

function ApiKeyCard() {
  const [keyInfo, setKeyInfo] = useState<ApiKeyInfo | null>(null);
  const [noKey, setNoKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const copyTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (copyTimeout.current) clearTimeout(copyTimeout.current);
    },
    []
  );

  async function revealKey() {
    setLoading(true);
    setError("");
    setNoKey(false);
    try {
      const data = await api.get("/api/me/api-key");
      setKeyInfo(data as ApiKeyInfo);
    } catch (e) {
      const status = (e as { status?: number }).status;
      if (status === 404) {
        setNoKey(true);
      } else {
        setError((e as Error).message);
      }
    } finally {
      setLoading(false);
    }
  }

  function copyKey() {
    if (!keyInfo) return;
    navigator.clipboard.writeText(keyInfo.api_key).then(() => {
      setCopied(true);
      if (copyTimeout.current) clearTimeout(copyTimeout.current);
      copyTimeout.current = setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="border border-brand-hair rounded-lg bg-white p-6 space-y-4">
      <div className="panel-title">
        <h4 className="font-bold text-brand-blue text-sm flex items-center gap-2">
          <Key className="w-4 h-4" aria-hidden={true} />
          Your API Key
        </h4>
      </div>

      <div className="ml-4 space-y-3">
        {!keyInfo && !noKey && !error && (
          <button
            onClick={revealKey}
            disabled={loading}
            aria-busy={loading}
            className="inline-flex items-center gap-2 text-sm font-semibold text-white bg-brand-blue rounded px-4 py-2 hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Eye className="w-4 h-4" aria-hidden={true} />
            {loading ? "Loading…" : "Reveal API key"}
          </button>
        )}

        {error && (
          <div className="space-y-2">
            <p
              className="text-sm text-brand-red bg-brand-redbg border border-brand-red rounded p-3"
              role="alert"
            >
              {error}
            </p>
            <button
              onClick={revealKey}
              disabled={loading}
              className="text-sm font-semibold text-brand-blue underline hover:text-brand-red cursor-pointer"
            >
              Try again
            </button>
          </div>
        )}

        {noKey && (
          <div className="space-y-2">
            <p className="text-sm text-brand-muted">
              Your assessor hasn't added your API key yet.
            </p>
            <button
              onClick={revealKey}
              disabled={loading}
              className="text-sm font-semibold text-brand-blue underline hover:text-brand-red cursor-pointer"
            >
              Try again
            </button>
          </div>
        )}

        {keyInfo && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input
                readOnly
                aria-label="API key"
                type={visible ? "text" : "password"}
                value={keyInfo.api_key}
                className="flex-1 font-mono text-sm bg-brand-codebg border border-brand-hair rounded px-3 py-2 text-brand-ink min-w-0"
              />
              <button
                onClick={() => setVisible((v) => !v)}
                aria-label={visible ? "Hide API key" : "Show API key"}
                className="flex items-center gap-1.5 text-xs font-semibold text-brand-blue border border-brand-hair rounded px-3 py-2 hover:bg-brand-b5 transition-colors cursor-pointer"
              >
                {visible ? (
                  <EyeOff className="w-3.5 h-3.5" aria-hidden={true} />
                ) : (
                  <Eye className="w-3.5 h-3.5" aria-hidden={true} />
                )}
                {visible ? "Hide" : "Show"}
              </button>
              <button
                onClick={copyKey}
                className="flex items-center gap-1.5 text-xs font-semibold text-brand-blue border border-brand-hair rounded px-3 py-2 hover:bg-brand-b5 transition-colors cursor-pointer"
              >
                <Copy className="w-3.5 h-3.5" aria-hidden={true} />
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            {keyInfo.note && (
              <p className="text-xs text-brand-muted whitespace-pre-wrap leading-relaxed">
                {keyInfo.note}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Right sidebar
// ---------------------------------------------------------------------------

function Sidebar() {
  return (
    <div className="space-y-6">
      <div className="border border-brand-hair rounded-lg bg-white p-5 space-y-3">
        <div className="panel-title">
          <h4 className="font-bold text-brand-blue text-sm flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" aria-hidden={true} />
            Data Minimisation
          </h4>
        </div>
        <p className="text-xs text-brand-muted leading-relaxed ml-4">
          We only collect what we need to run your assessment, and your exercise
          materials are released to you alone. Read how we handle your data.
        </p>
        <a
          href="/privacy"
          className="ml-4 inline-block text-xs font-semibold text-brand-blue underline hover:text-brand-red"
        >
          Privacy &amp; data handling
        </a>
      </div>

      <div className="border border-brand-hair rounded-lg bg-brand-redbg p-5 space-y-3">
        <div className="panel-title">
          <h4 className="font-bold text-brand-red text-sm flex items-center gap-2">
            <HelpCircle className="w-4 h-4" aria-hidden={true} />
            Need Clarification?
          </h4>
        </div>
        <p className="text-xs text-brand-ink leading-relaxed ml-4">
          If anything in the brief or data is unclear, send a question to your
          assessor before your session.
        </p>
        <a
          href="/questions"
          className="ml-4 inline-block text-xs font-semibold text-white bg-brand-red rounded px-3 py-2 hover:opacity-90 transition-opacity"
        >
          Ask a question
        </a>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// State cards
// ---------------------------------------------------------------------------

function NoBookingCard({ onBook }: { onBook: () => void }) {
  return (
    <div className="border border-brand-red rounded-lg bg-brand-redbg p-6 space-y-4 max-w-2xl">
      <div className="panel-title">
        <h3 className="font-bold text-brand-red text-base flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" aria-hidden={true} />
          You haven't booked your assessment yet
        </h3>
      </div>
      <p className="text-sm text-brand-ink leading-relaxed ml-4">
        To receive your exercise materials and API key, you first need to choose
        an assessment slot. Your exercise data unlocks ahead of your session so
        you have time to prepare.
      </p>
      <div className="ml-4">
        <button
          onClick={onBook}
          className="inline-flex items-center gap-2 text-sm font-semibold text-white bg-brand-red rounded px-5 py-2.5 hover:opacity-90 transition-opacity cursor-pointer"
        >
          Book your assessment
        </button>
      </div>
    </div>
  );
}

function LockedCard({
  booking,
  onUnlock,
}: {
  booking: HasBooking;
  onUnlock: () => void;
}) {
  const unlockLabel = formatDateTime(booking.unlock_at);
  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
      <div className="md:col-span-8 space-y-6">
        <div className="border border-brand-hair rounded-lg bg-white p-6 space-y-3">
          <div className="panel-title">
            <h3 className="font-bold text-brand-blue text-sm">
              Your Scheduled Assessment
            </h3>
          </div>
          <p className="text-sm text-brand-ink ml-4">
            Your assessment is scheduled for{" "}
            <strong className="font-semibold tabular-numbers">
              {formatDateTime(booking.slot_starts_at)}
            </strong>
            .
          </p>
        </div>

        <div className="border border-brand-hair rounded-lg bg-white p-6 space-y-4">
          <div className="panel-title">
            <h3 className="font-bold text-brand-blue text-sm flex items-center gap-2">
              <Lock className="w-4 h-4" aria-hidden={true} />
              Exercise Materials Locked
            </h3>
          </div>
          <p className="text-sm text-brand-muted ml-4">
            Your exercise data and API key unlock on{" "}
            <strong className="text-brand-ink font-semibold tabular-numbers">
              {unlockLabel}
            </strong>
            . The page will refresh automatically when the timer reaches zero.
          </p>
          <div className="ml-4">
            <Countdown unlockAt={booking.unlock_at} onUnlock={onUnlock} />
          </div>
        </div>
      </div>

      <div className="md:col-span-4">
        <Sidebar />
      </div>
    </div>
  );
}

function UnlockedState() {
  return (
    <div className="space-y-6">
      {/* Celebratory banner */}
      <div className="border border-emerald-300 bg-emerald-50 rounded-lg p-5 flex items-start gap-3">
        <CheckCircle2
          className="w-6 h-6 text-emerald-600 flex-shrink-0 mt-0.5"
          aria-hidden={true}
        />
        <div>
          <p className="font-bold text-emerald-800 text-sm">
            Your exercise data is now unlocked. Good luck!
          </p>
          <p className="text-xs text-emerald-700 mt-1">
            Download your materials below, and reveal your API key when you're
            ready to start.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        <div className="md:col-span-8 space-y-6">
          <UnlockedContent />
          <ApiKeyCard />
        </div>
        <div className="md:col-span-4">
          <Sidebar />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CandidateDashboard() {
  const nav = useNavigate();
  const [bookingState, setBookingState] = useState<BookingState | null>(null);
  const [error, setError] = useState("");

  const fetchBooking = useCallback(async () => {
    setError("");
    try {
      const data = await api.get("/api/me/booking");
      setBookingState(data as BookingState);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    fetchBooking();
  }, [fetchBooking]);

  return (
    <div className="space-y-6 animate-fade-in">
      {error && (
        <p
          className="text-sm text-brand-red bg-brand-redbg border border-brand-red rounded p-3"
          role="alert"
        >
          {error}
        </p>
      )}

      {bookingState === null && !error && (
        <p className="text-sm text-brand-muted">Loading…</p>
      )}

      {bookingState !== null && !bookingState.has_booking && (
        <NoBookingCard onBook={() => nav("/book")} />
      )}

      {bookingState !== null &&
        bookingState.has_booking &&
        !bookingState.unlocked && (
          <LockedCard booking={bookingState} onUnlock={fetchBooking} />
        )}

      {bookingState !== null &&
        bookingState.has_booking &&
        bookingState.unlocked && <UnlockedState />}
    </div>
  );
}
