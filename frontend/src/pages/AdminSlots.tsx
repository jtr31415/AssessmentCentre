import { useEffect, useState } from "react";
import { AlertTriangle, Calendar, Edit2, Plus, Trash2, X, Check } from "lucide-react";
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
  const [loadError, setLoadError] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [capacity, setCapacity] = useState(1);
  const [createError, setCreateError] = useState("");

  // Per-slot inline error messages keyed by slot id
  const [slotErrors, setSlotErrors] = useState<Record<number, string>>({});

  // Edit state: slot id -> { starts_at: string, capacity: number }
  const [editState, setEditState] = useState<
    Record<number, { starts_at: string; capacity: number }>
  >({});

  // Reassign state: keyed by `${slot.id}-${candidate_id}` -> new_slot_id string
  const [reassignSlotId, setReassignSlotId] = useState<Record<string, string>>({});

  async function load() {
    setLoadError("");
    try {
      const data = await api.get("/api/admin/slots");
      setSlots(data as Slot[]);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }

  useEffect(() => {
    load();
  }, []);

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
    setEditState((prev) => ({
      ...prev,
      [slot.id]: { starts_at: localStr, capacity: slot.capacity },
    }));
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
    <div className="space-y-6">
      {/* Page title */}
      <div className="flex items-center gap-2 pb-2 border-b border-brand-hair">
        <Calendar className="w-5 h-5 text-brand-blue flex-shrink-0" />
        <h1 className="text-xl font-bold text-brand-blue">Manage Assessment Slots</h1>
      </div>

      {/* Create Slot panel */}
      <div className="border border-brand-hair rounded-lg p-5 bg-white space-y-4">
        <div className="panel-title">
          <h2 className="font-bold text-brand-blue text-sm">Create New Assessment Slot</h2>
        </div>

        <form
          onSubmit={handleCreate}
          className="ml-4 grid grid-cols-1 sm:grid-cols-3 gap-4 items-end"
        >
          <div>
            <label
              htmlFor="slot-starts-at"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Date / Time of Slot
            </label>
            <input
              id="slot-starts-at"
              type="datetime-local"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
              required
              className="w-full text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
            />
          </div>

          <div>
            <label
              htmlFor="slot-capacity"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              Capacity (Max candidates)
            </label>
            <input
              id="slot-capacity"
              type="number"
              value={capacity}
              min={1}
              onChange={(e) => setCapacity(Number(e.target.value) || 1)}
              required
              className="w-full text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
            />
          </div>

          <button
            type="submit"
            className="bg-brand-blue hover:bg-opacity-90 text-white font-semibold text-xs px-4 py-2.5 rounded h-10 flex items-center justify-center gap-1 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Create Slot</span>
          </button>
        </form>

        {createError && (
          <div className="p-3 bg-brand-redbg border border-brand-red text-brand-red text-xs rounded ml-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{createError}</span>
          </div>
        )}
      </div>

      {/* Slots Table panel */}
      <div className="border border-brand-hair rounded-lg p-6 bg-white space-y-4">
        <div className="panel-title">
          <h2 className="font-bold text-brand-blue text-sm">Managed Assessment Slots</h2>
        </div>

        {loadError && (
          <div className="p-3 bg-brand-redbg border border-brand-red text-brand-red text-xs rounded flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{loadError}</span>
          </div>
        )}

        {!loadError && slots.length === 0 && (
          <div className="p-8 text-center text-brand-muted border border-dashed border-brand-hair rounded bg-neutral-50">
            <Calendar className="w-8 h-8 text-brand-b3 mx-auto mb-2" />
            <p className="text-xs">No slots yet.</p>
          </div>
        )}

        {slots.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-brand-b5 border-b border-brand-hair text-brand-blue font-bold">
                  <th className="p-3">Slot ID</th>
                  <th className="p-3">Starts At</th>
                  <th className="p-3">Capacity</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-hair">
                {slots.map((slot) => {
                  const isBooked = slot.bookings.length > 0;
                  const es = editState[slot.id];
                  const err = slotErrors[slot.id];

                  return (
                    <tr key={slot.id} className="hover:bg-neutral-50">
                      {/* ID */}
                      <td className="p-3 font-mono font-bold text-brand-ink tabular-numbers">
                        {slot.id}
                      </td>

                      {/* Starts At — editable */}
                      <td className="p-3 tabular-numbers text-brand-ink">
                        {es ? (
                          <input
                            type="datetime-local"
                            aria-label="Edit slot date and time"
                            value={es.starts_at}
                            onChange={(e) =>
                              setEditState((prev) => ({
                                ...prev,
                                [slot.id]: { ...prev[slot.id], starts_at: e.target.value },
                              }))
                            }
                            className="text-sm border border-brand-hair rounded px-2 py-1 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
                          />
                        ) : (
                          <span className="font-semibold">{formatDate(slot.starts_at)}</span>
                        )}
                      </td>

                      {/* Capacity — editable */}
                      <td className="p-3 font-mono tabular-numbers text-brand-ink">
                        {es ? (
                          <input
                            type="number"
                            aria-label="Edit slot capacity"
                            value={es.capacity}
                            min={1}
                            onChange={(e) =>
                              setEditState((prev) => ({
                                ...prev,
                                [slot.id]: {
                                  ...prev[slot.id],
                                  capacity: Number(e.target.value) || 1,
                                },
                              }))
                            }
                            className="w-20 text-sm border border-brand-hair rounded px-2 py-1 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
                          />
                        ) : (
                          slot.capacity
                        )}
                      </td>

                      {/* Status */}
                      <td className="p-3">
                        {slot.is_open ? (
                          <span className="text-brand-ink tabular-numbers">
                            Open (
                            <span className="font-mono">{slot.booked_count}/{slot.capacity}</span>
                            )
                          </span>
                        ) : (
                          <div className="space-y-1">
                            {slot.bookings.map((booking) => (
                              <div key={booking.candidate_id} className="flex items-center gap-1.5">
                                <span className="font-semibold text-brand-ink">
                                  {booking.candidate_id}
                                </span>
                                <code className="text-[10px] text-brand-muted bg-neutral-100 px-1 py-0.5 rounded font-mono">
                                  ({booking.first_name})
                                </code>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="p-3">
                        {err && (
                          <div className="mb-2 p-2 bg-brand-redbg border border-brand-red text-brand-red text-[10px] rounded flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                            <span>{err}</span>
                          </div>
                        )}

                        {/* Unbooked — view mode */}
                        {!isBooked && !es && (
                          <div className="flex gap-2">
                            <button
                              onClick={() => startEdit(slot)}
                              className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold rounded border border-brand-b4 text-brand-blue hover:bg-brand-b5 cursor-pointer"
                              title="Edit slot"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                              <span>Edit</span>
                            </button>
                            <button
                              onClick={() => handleDelete(slot)}
                              className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold rounded border border-brand-red text-brand-red hover:bg-brand-redbg cursor-pointer"
                              title="Delete slot"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              <span>Delete</span>
                            </button>
                          </div>
                        )}

                        {/* Unbooked — edit mode */}
                        {!isBooked && es && (
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleEdit(slot)}
                              className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold rounded bg-brand-blue text-white hover:bg-opacity-90 cursor-pointer"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Save</span>
                            </button>
                            <button
                              onClick={() => cancelEdit(slot.id)}
                              className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold rounded border border-brand-hair text-brand-muted hover:bg-neutral-100 cursor-pointer"
                            >
                              <X className="w-3.5 h-3.5" />
                              <span>Cancel</span>
                            </button>
                          </div>
                        )}

                        {/* Booked — per-booking reassign/release */}
                        {isBooked && (
                          <div className="space-y-2">
                            {slot.bookings.map((booking) => {
                              const key = `${slot.id}-${booking.candidate_id}`;
                              return (
                                <div key={booking.candidate_id} className="flex flex-wrap gap-2 items-center">
                                  <input
                                    type="number"
                                    aria-label={`New slot ID for ${booking.candidate_id}`}
                                    placeholder="New slot ID"
                                    value={reassignSlotId[key] ?? ""}
                                    min={1}
                                    onChange={(e) =>
                                      setReassignSlotId((prev) => ({
                                        ...prev,
                                        [key]: e.target.value,
                                      }))
                                    }
                                    className="w-24 text-sm border border-brand-hair rounded px-2 py-1 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue tabular-numbers"
                                  />
                                  <button
                                    onClick={() => handleReassign(slot, booking.candidate_id)}
                                    className="px-2.5 py-1 bg-brand-blue text-white text-[10px] font-bold rounded hover:bg-opacity-90 cursor-pointer"
                                  >
                                    Reassign
                                  </button>
                                  <button
                                    onClick={() => handleRelease(slot, booking.candidate_id)}
                                    className="px-2.5 py-1 text-[10px] font-bold rounded border border-brand-red text-brand-red hover:bg-brand-redbg cursor-pointer"
                                  >
                                    Release
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
