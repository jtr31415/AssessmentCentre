import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

interface OpenSlot {
  id: number;
  starts_at: string;
}

interface Preview {
  unlock_display: string;
  prep_days: number;
  assessment_display: string;
  unlocks_immediately: boolean;
}

export default function CandidateBooking() {
  const nav = useNavigate();
  const [slots, setSlots] = useState<OpenSlot[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loadError, setLoadError] = useState("");
  const [bookError, setBookError] = useState("");
  const [booking, setBooking] = useState(false);

  async function loadSlots() {
    setLoadError("");
    try {
      const data = await api.get("/api/slots/open");
      setSlots(data as OpenSlot[]);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }

  useEffect(() => {
    loadSlots();
  }, []);

  async function handleSelect(id: number) {
    setSelectedId(id);
    setPreview(null);
    setBookError("");
    try {
      const data = await api.get(`/api/slots/${id}/preview`);
      setPreview(data as Preview);
    } catch (e) {
      setBookError((e as Error).message);
    }
  }

  async function handleConfirm() {
    if (selectedId === null) return;
    setBooking(true);
    setBookError("");
    try {
      await api.post(`/api/slots/${selectedId}/book`);
      nav("/dashboard");
    } catch (e) {
      setBookError((e as Error).message);
      setSelectedId(null);
      setPreview(null);
      await loadSlots();
    } finally {
      setBooking(false);
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h1>Book your assessment slot</h1>

      {loadError && <p style={{ color: "red" }}>{loadError}</p>}

      {slots.length === 0 && !loadError && <p>No slots currently available.</p>}

      {slots.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {slots.map((slot) => (
            <li key={slot.id} style={{ marginBottom: 8 }}>
              <button
                onClick={() => handleSelect(slot.id)}
                style={{
                  fontWeight: selectedId === slot.id ? "bold" : "normal",
                  cursor: "pointer",
                }}
              >
                {new Date(slot.starts_at).toLocaleString()}
              </button>
            </li>
          ))}
        </ul>
      )}

      {preview && selectedId !== null && (
        <div style={{ marginTop: 16, padding: 12, border: "1px solid #ccc", borderRadius: 4 }}>
          <p>
            {preview.unlocks_immediately ? (
              <>
                If you choose this slot, your exercise data unlocks{" "}
                <strong>immediately</strong>, giving you{" "}
                <strong>{preview.prep_days}</strong> days to work on it before
                your assessment on{" "}
                <strong>{preview.assessment_display}</strong>.
              </>
            ) : (
              <>
                If you choose this slot, your exercise data unlocks on{" "}
                <strong>{preview.unlock_display}</strong>, giving you{" "}
                <strong>{preview.prep_days}</strong> days to work on it before
                your assessment on{" "}
                <strong>{preview.assessment_display}</strong>.
              </>
            )}
          </p>
          <button onClick={handleConfirm} disabled={booking}>
            {booking ? "Booking..." : "Confirm"}
          </button>
        </div>
      )}

      {bookError && <p style={{ color: "red", marginTop: 8 }}>{bookError}</p>}
    </div>
  );
}
