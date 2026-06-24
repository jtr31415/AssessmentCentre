import { useEffect, useState } from "react";
import { api } from "../api/client";

type Booking = { candidate_id: string; first_name: string };

type Slot = {
  id: number;
  starts_at: string;
  capacity: number;
  booked_count: number;
  is_open: boolean;
  bookings: Booking[];
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function AdminSlots() {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [startsAt, setStartsAt] = useState("");
  const [capacity, setCapacity] = useState(1);
  const [createError, setCreateError] = useState("");

  // Per-slot inline error messages keyed by slot id
  const [slotErrors, setSlotErrors] = useState<Record<number, string>>({});

  // Edit state: slot id -> { starts_at: string, capacity: number }
  const [editState, setEditState] = useState<Record<number, { starts_at: string; capacity: number }>>({});

  // Reassign state: keyed by `${slot.id}-${candidate_id}` -> new_slot_id string
  const [reassignSlotId, setReassignSlotId] = useState<Record<string, string>>({});

  async function load() {
    try {
      const data = await api.get("/api/admin/slots");
      setSlots(data as Slot[]);
    } catch (e) {
      setCreateError((e as Error).message);
    }
  }

  useEffect(() => { load(); }, []);

  function setSlotError(id: number, msg: string) {
    setSlotErrors((prev) => ({ ...prev, [id]: msg }));
  }

  function clearSlotError(id: number) {
    setSlotErrors((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError("");
    try {
      await api.post("/api/admin/slots", {
        starts_at: new Date(startsAt).toISOString(),
        capacity: capacity || 1,
      });
      setStartsAt("");
      setCapacity(1);
      await load();
    } catch (e) {
      setCreateError((e as Error).message);
    }
  }

  async function handleDelete(slot: Slot) {
    clearSlotError(slot.id);
    try {
      await api.del(`/api/admin/slots/${slot.id}`);
      await load();
    } catch (e) {
      setSlotError(slot.id, (e as Error).message);
    }
  }

  function startEdit(slot: Slot) {
    // Convert ISO to datetime-local format (strip seconds/ms, keep local)
    const local = new Date(slot.starts_at);
    const pad = (n: number) => String(n).padStart(2, "0");
    const localStr = `${local.getFullYear()}-${pad(local.getMonth() + 1)}-${pad(local.getDate())}T${pad(local.getHours())}:${pad(local.getMinutes())}`;
    setEditState((prev) => ({ ...prev, [slot.id]: { starts_at: localStr, capacity: slot.capacity } }));
  }

  function cancelEdit(id: number) {
    setEditState((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  async function handleEdit(slot: Slot) {
    const es = editState[slot.id];
    if (!es) return;
    clearSlotError(slot.id);
    try {
      await api.patch(`/api/admin/slots/${slot.id}`, {
        starts_at: new Date(es.starts_at).toISOString(),
        capacity: Number(es.capacity) || 1,
      });
      cancelEdit(slot.id);
      await load();
    } catch (e) {
      setSlotError(slot.id, (e as Error).message);
    }
  }

  async function handleReassign(slot: Slot, candidateId: string) {
    const key = `${slot.id}-${candidateId}`;
    const newSlotId = reassignSlotId[key];
    if (!newSlotId) return;
    clearSlotError(slot.id);
    try {
      await api.post("/api/admin/bookings/reassign", {
        candidate_id: candidateId,
        new_slot_id: Number(newSlotId),
      });
      setReassignSlotId((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
      await load();
    } catch (e) {
      setSlotError(slot.id, (e as Error).message);
    }
  }

  async function handleRelease(slot: Slot, candidateId: string) {
    clearSlotError(slot.id);
    try {
      await api.post("/api/admin/bookings/release", { candidate_id: candidateId });
      await load();
    } catch (e) {
      setSlotError(slot.id, (e as Error).message);
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h1>Manage Slots</h1>

      <section>
        <h2>Create Slot</h2>
        <form onSubmit={handleCreate} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <label>
            Date/Time:{" "}
            <input
              type="datetime-local"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
              required
            />
          </label>
          <label>
            Capacity:{" "}
            <input
              type="number"
              value={capacity}
              min={1}
              onChange={(e) => setCapacity(Number(e.target.value) || 1)}
              required
              style={{ width: 60 }}
            />
          </label>
          <button type="submit">Create</button>
          {createError && <span style={{ color: "red" }}>{createError}</span>}
        </form>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Slots</h2>
        {slots.length === 0 && <p>No slots yet.</p>}
        {slots.length > 0 && (
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                {["ID", "Starts At", "Capacity", "Status", "Actions"].map((h) => (
                  <th key={h} style={{ textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #ccc" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {slots.map((slot) => {
                const isBooked = slot.bookings.length > 0;
                const es = editState[slot.id];
                const err = slotErrors[slot.id];

                return (
                  <tr key={slot.id} style={{ borderBottom: "1px solid #eee" }}>
                    <td style={{ padding: "4px 8px" }}>{slot.id}</td>

                    <td style={{ padding: "4px 8px" }}>
                      {es ? (
                        <input
                          type="datetime-local"
                          value={es.starts_at}
                          onChange={(e) =>
                            setEditState((prev) => ({ ...prev, [slot.id]: { ...prev[slot.id], starts_at: e.target.value } }))
                          }
                        />
                      ) : (
                        formatDate(slot.starts_at)
                      )}
                    </td>

                    <td style={{ padding: "4px 8px" }}>
                      {es ? (
                        <input
                          type="number"
                          value={es.capacity}
                          min={1}
                          style={{ width: 60 }}
                          onChange={(e) =>
                            setEditState((prev) => ({ ...prev, [slot.id]: { ...prev[slot.id], capacity: Number(e.target.value) || 1 } }))
                          }
                        />
                      ) : (
                        slot.capacity
                      )}
                    </td>

                    <td style={{ padding: "4px 8px" }}>
                      {slot.is_open
                        ? `Open (${slot.booked_count}/${slot.capacity})`
                        : `Booked by ${slot.bookings.map((b) => b.candidate_id).join(", ")}`}
                    </td>

                    <td style={{ padding: "4px 8px" }}>
                      {err && <span style={{ color: "red", display: "block", marginBottom: 4 }}>{err}</span>}

                      {!isBooked && !es && (
                        <>
                          <button onClick={() => startEdit(slot)} style={{ marginRight: 4 }}>Edit</button>
                          <button onClick={() => handleDelete(slot)}>Delete</button>
                        </>
                      )}

                      {!isBooked && es && (
                        <>
                          <button onClick={() => handleEdit(slot)} style={{ marginRight: 4 }}>Save</button>
                          <button onClick={() => cancelEdit(slot.id)}>Cancel</button>
                        </>
                      )}

                      {isBooked && slot.bookings.map((booking) => (
                        <div key={booking.candidate_id} style={{ marginBottom: 4 }}>
                          <span style={{ marginRight: 4 }}>
                            {booking.candidate_id} ({booking.first_name})
                          </span>
                          <input
                            type="number"
                            placeholder="New slot ID"
                            value={reassignSlotId[`${slot.id}-${booking.candidate_id}`] ?? ""}
                            min={1}
                            style={{ width: 90, marginRight: 4 }}
                            onChange={(e) =>
                              setReassignSlotId((prev) => ({ ...prev, [`${slot.id}-${booking.candidate_id}`]: e.target.value }))
                            }
                          />
                          <button
                            onClick={() => handleReassign(slot, booking.candidate_id)}
                            style={{ marginRight: 4 }}
                          >
                            Reassign
                          </button>
                          <button onClick={() => handleRelease(slot, booking.candidate_id)}>
                            Release
                          </button>
                        </div>
                      ))}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
