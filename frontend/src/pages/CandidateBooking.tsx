import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
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
  assessment_at_iso: string;
  unlock_at_iso: string;
}

export default function CandidateBooking() {
  const nav = useNavigate();
  const [alreadyBooked, setAlreadyBooked] = useState<boolean | null>(null);
  const [slots, setSlots] = useState<OpenSlot[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loadError, setLoadError] = useState("");
  const [bookError, setBookError] = useState("");
  const [booking, setBooking] = useState(false);

  // On mount: check whether the candidate already has a booking
  useEffect(() => {
    async function checkExisting() {
      try {
        const data = await api.get("/api/me/booking");
        const booking = data as { has_booking: boolean };
        if (booking.has_booking) {
          setAlreadyBooked(true);
        } else {
          setAlreadyBooked(false);
          loadSlots();
        }
      } catch {
        // If the check fails just fall through to show the slot picker
        setAlreadyBooked(false);
        loadSlots();
      }
    }
    checkExisting();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadSlots() {
    setLoadError("");
    try {
      const data = await api.get("/api/slots/open");
      setSlots(data as OpenSlot[]);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }

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

  // Still determining booking status
  if (alreadyBooked === null) {
    return (
      <div className="p-8">
        <p className="text-brand-muted text-sm">Loading…</p>
      </div>
    );
  }

  // Already booked — show friendly message instead of slot picker
  if (alreadyBooked) {
    return (
      <div className="max-w-md mx-auto mt-12 border border-brand-hair rounded-lg p-8 bg-white space-y-4">
        <h1 className="panel-title text-xl font-bold text-brand-blue">
          Already Booked
        </h1>
        <p className="text-sm text-brand-muted">
          You already have an assessment booking.
        </p>
        <Link
          to="/dashboard"
          className="inline-block mt-2 text-sm font-semibold text-brand-blue underline hover:text-brand-red"
        >
          Go to your dashboard
        </Link>
      </div>
    );
  }

  const todayLabel = new Date().toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  return (
    <div className="space-y-6 animate-[fade-in_0.3s_ease-out]">
      {/* Page heading */}
      <h3 className="text-xl font-bold text-brand-blue">
        Book your assessment slot
      </h3>

      {/* Two-column layout: main content + sidebar */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Left column */}
        <div className="md:col-span-8 space-y-6">
          {/* Slots selection panel */}
          <div className="border border-brand-hair rounded-lg p-6 bg-white space-y-4">
            <div className="panel-title">
              <h4 className="font-bold text-brand-blue text-sm">
                Available Assessment Slots
              </h4>
            </div>

            {loadError && (
              <p className="text-sm text-brand-red ml-4">{loadError}</p>
            )}

            {slots.length === 0 && !loadError && (
              <p className="text-sm text-brand-muted ml-4">
                No slots currently available.
              </p>
            )}

            {slots.length > 0 && (
              <div className="grid grid-cols-1 gap-3 ml-4">
                {slots.map((slot) => {
                  const isSelected = selectedId === slot.id;
                  return (
                    <div
                      key={slot.id}
                      onClick={() => handleSelect(slot.id)}
                      role="button"
                      tabIndex={0}
                      aria-pressed={isSelected}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          handleSelect(slot.id);
                        }
                      }}
                      className={`border rounded-lg p-4 flex items-center justify-between cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-brand-redbg border-brand-red"
                          : "bg-white border-brand-hair hover:border-brand-muted"
                      }`}
                    >
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-brand-ink tabular-numbers">
                          {new Date(slot.starts_at).toLocaleString("en-GB", {
                            weekday: "short",
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>

                      <div>
                        {isSelected ? (
                          <span className="text-[10px] uppercase font-bold text-white bg-brand-red px-2 py-1 rounded">
                            Selected
                          </span>
                        ) : (
                          <span className="text-[10px] uppercase font-bold text-brand-muted bg-neutral-100 px-2 py-1 rounded">
                            Available
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Prep-window Preview (shown once a slot is selected and preview loaded) */}
          {selectedId !== null && preview && (
            <div
              className={`border rounded-lg p-5 space-y-4 ${
                preview.unlocks_immediately
                  ? "border-brand-red bg-brand-redbg"
                  : "border-brand-red bg-brand-redbg"
              }`}
              id="prep-preview-box"
            >
              <div className="panel-title">
                <h4 className="font-bold text-brand-red text-sm">
                  Booking Timeline &amp; Prep Window
                </h4>
              </div>

              <div className="ml-4 space-y-4">
                {/* Prep sentence */}
                <div className="text-xs text-brand-ink leading-relaxed">
                  {preview.unlocks_immediately ? (
                    <p className="text-brand-red">
                      <AlertTriangle
                        className="w-4 h-4 inline mr-1 -mt-0.5 text-brand-red"
                        aria-hidden="true"
                      />
                      <b>Immediate Unlock Warning:</b> If you choose this slot,
                      your exercise data unlocks{" "}
                      <b className="uppercase animate-pulse">immediately</b>,
                      giving you{" "}
                      <b className="tabular-numbers">{preview.prep_days} days</b>{" "}
                      to work on it before your assessment on{" "}
                      <b>{preview.assessment_display}</b>.
                    </p>
                  ) : (
                    <p>
                      If you choose this slot, your exercise data unlocks on{" "}
                      <b className="font-semibold">{preview.unlock_display}</b>,
                      giving you{" "}
                      <b className="font-bold tabular-numbers">
                        {preview.prep_days} days
                      </b>{" "}
                      to work on it before your assessment on{" "}
                      <b className="font-semibold">{preview.assessment_display}</b>
                      .
                    </p>
                  )}
                </div>

                {/* Interactive Timeline Visual */}
                <div className="bg-white border border-brand-hair p-4 rounded-lg space-y-3">
                  <div className="relative flex items-center justify-between">
                    {/* Track background */}
                    <div className="absolute left-0 right-0 h-1 bg-brand-hair top-1/2 -translate-y-1/2" />
                    {/* Filled prep bar */}
                    <div
                      className="absolute left-0 h-1 bg-brand-red top-1/2 -translate-y-1/2 transition-all duration-300"
                      style={{
                        width: preview.unlocks_immediately ? "100%" : "50%",
                      }}
                    />

                    {/* Node 1: Today */}
                    <div className="relative z-10 flex flex-col items-center">
                      <div
                        className="w-6 h-6 rounded-full bg-brand-blue text-white flex items-center justify-center text-[10px] font-bold"
                        aria-label="Step 1: Today"
                      >
                        1
                      </div>
                      <span className="text-[10px] font-bold text-brand-blue mt-1 bg-white px-1">
                        Today
                      </span>
                    </div>

                    {/* Node 2: Unlock */}
                    <div className="relative z-10 flex flex-col items-center">
                      <div
                        className="w-6 h-6 rounded-full bg-brand-red text-white flex items-center justify-center text-[10px] font-bold"
                        aria-label="Step 2: Unlock"
                      >
                        2
                      </div>
                      <span className="text-[10px] font-bold text-brand-red mt-1 bg-white px-1">
                        Unlock
                      </span>
                    </div>

                    {/* Node 3: Session */}
                    <div className="relative z-10 flex flex-col items-center">
                      <div
                        className="w-6 h-6 rounded-full bg-brand-blue text-white flex items-center justify-center text-[10px] font-bold"
                        aria-label="Step 3: Session"
                      >
                        3
                      </div>
                      <span className="text-[10px] font-bold text-brand-blue mt-1 bg-white px-1">
                        Session
                      </span>
                    </div>
                  </div>

                  {/* Timeline footer labels */}
                  <div className="flex justify-between text-[10px] text-brand-muted pt-2 border-t border-neutral-100">
                    <div>
                      <span>Today: </span>
                      <span className="font-mono text-brand-ink tabular-numbers">
                        {todayLabel}
                      </span>
                    </div>
                    <div className="text-center">
                      <span className="font-bold text-brand-red tabular-numbers">
                        {preview.prep_days} Days
                      </span>{" "}
                      prep window
                    </div>
                    <div className="text-right">
                      <span>Session: </span>
                      <span className="font-mono text-brand-ink">
                        {preview.assessment_display}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Spinner / loading state while fetching preview */}
          {selectedId !== null && !preview && !bookError && (
            <p className="text-sm text-brand-muted ml-1">
              Loading preview…
            </p>
          )}
        </div>

        {/* Right sidebar: Confirm Selection */}
        <div className="md:col-span-4">
          <div className="border border-brand-hair rounded-lg p-5 bg-white space-y-4">
            <h4 className="font-bold text-sm text-brand-blue">
              Confirm Selection
            </h4>
            <p className="text-xs text-brand-muted">
              You can only book one assessment slot. Once confirmed, you must
              ask the assessor to release or reschedule your slot.
            </p>

            {bookError && (
              <p
                className="text-xs text-brand-red bg-brand-redbg border border-brand-red rounded p-2"
                role="alert"
              >
                {bookError}
              </p>
            )}

            <button
              onClick={handleConfirm}
              disabled={selectedId === null || booking}
              aria-busy={booking}
              className="w-full text-center py-2.5 bg-brand-red text-white text-sm font-semibold rounded hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {booking ? "Booking…" : "Confirm Assessment Booking"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
