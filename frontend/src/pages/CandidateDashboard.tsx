import { useCallback, useEffect, useState } from "react";
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
          <p>Your exercise data is unlocked.</p>
          <p style={{ color: "#666", fontSize: 14 }}>
            Download links will be available in the next phase.
          </p>
        </div>
      )}

      <button onClick={logout} style={{ marginTop: 16 }}>
        Log out
      </button>
    </div>
  );
}
