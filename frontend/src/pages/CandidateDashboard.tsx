import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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
  category: string;
}

interface ApiKeyInfo {
  api_key: string;
  note: string;
}

const CATEGORY_ORDER: string[] = ["brief", "data", "reference"];
const CATEGORY_LABELS: Record<string, string> = {
  brief: "Brief",
  data: "Data Files",
  reference: "Reference Material",
};

function DownloadArea() {
  const [items, setItems] = useState<ContentItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/content")
      .then((d) => setItems(d as ContentItem[]))
      .catch((e) => setError((e as Error).message));
  }, []);

  if (error) return <p style={{ color: "red" }}>Could not load files: {error}</p>;
  if (items === null) return <p>Loading files…</p>;
  if (items.length === 0) return <p>No files available yet.</p>;

  const grouped: Record<string, ContentItem[]> = {};
  for (const item of items) {
    if (!grouped[item.category]) grouped[item.category] = [];
    grouped[item.category].push(item);
  }

  const categories = [
    ...CATEGORY_ORDER.filter((c) => grouped[c]),
    ...Object.keys(grouped).filter((c) => !CATEGORY_ORDER.includes(c)),
  ];

  return (
    <div>
      <h2>Assessment Files</h2>
      {categories.map((cat) => (
        <div key={cat} style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 8 }}>{CATEGORY_LABELS[cat] ?? cat}</h3>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {grouped[cat].map((item) => (
              <li key={item.file_key} style={{ marginBottom: 6 }}>
                <a
                  href={"/api/content/" + item.file_key}
                  download
                  style={{ textDecoration: "underline", cursor: "pointer" }}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function ApiKeySection() {
  const [keyInfo, setKeyInfo] = useState<ApiKeyInfo | null>(null);
  const [noKey, setNoKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const copyTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (copyTimeout.current) clearTimeout(copyTimeout.current);
  }, []);

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
    <div style={{ marginTop: 24 }}>
      <h2>Your API Key</h2>
      {!keyInfo && !noKey && (
        <button onClick={revealKey} disabled={loading}>
          {loading ? "Loading…" : "Reveal API key"}
        </button>
      )}
      {error && <p style={{ color: "red" }}>{error}</p>}
      {noKey && (
        <div>
          <p style={{ color: "#888" }}>Your assessor hasn't added your API key yet.</p>
          <button onClick={revealKey} disabled={loading} style={{ marginTop: 4 }}>
            Try again
          </button>
        </div>
      )}
      {keyInfo && (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <input
              readOnly
              type={visible ? "text" : "password"}
              value={keyInfo.api_key}
              style={{ fontFamily: "monospace", minWidth: 280 }}
            />
            <button onClick={() => setVisible((v) => !v)}>{visible ? "Hide" : "Show"}</button>
            <button onClick={copyKey}>{copied ? "Copied!" : "Copy"}</button>
          </div>
          {keyInfo.note && (
            <p style={{ color: "#444", fontSize: 14, whiteSpace: "pre-wrap" }}>{keyInfo.note}</p>
          )}
        </div>
      )}
    </div>
  );
}

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

  async function logout() {
    try {
      await api.post("/api/auth/logout");
    } finally {
      nav("/login");
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h1>Welcome</h1>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {bookingState === null && !error && <p>Loading...</p>}

      {bookingState !== null && !bookingState.has_booking && (
        <p>
          <Link to="/book">Book your assessment</Link>
        </p>
      )}

      {bookingState !== null && bookingState.has_booking && !bookingState.unlocked && (
        <div>
          <p>
            Your assessment is scheduled for{" "}
            <strong>{new Date(bookingState.slot_starts_at).toLocaleString()}</strong>.
          </p>
          <p>
            Your exercise data unlocks in:{" "}
            <Countdown unlockAt={bookingState.unlock_at} onUnlock={fetchBooking} />
          </p>
        </div>
      )}

      {bookingState !== null && bookingState.has_booking && bookingState.unlocked && (
        <div>
          <p>Your exercise data is now unlocked. Good luck!</p>
          <DownloadArea />
          <ApiKeySection />
        </div>
      )}

      <button onClick={logout} style={{ marginTop: 16 }}>
        Log out
      </button>
    </div>
  );
}
