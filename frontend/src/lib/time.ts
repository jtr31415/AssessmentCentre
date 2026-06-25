/**
 * Format an ISO timestamp in Central European time with an explicit CEST label.
 * Assessment slots are always run on-site (CEST), so candidate-facing times are
 * pinned to Europe/Berlin regardless of the viewer's browser timezone.
 */
export function formatCEST(iso: string): string {
  const t = new Date(iso).toLocaleString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Berlin",
  });
  return `${t} CEST`;
}

/** Offset (minutes) of Europe/Berlin at the given UTC instant — +120 in summer (CEST). */
function berlinOffsetMinutes(utcMillis: number): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Berlin",
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(new Date(utcMillis));
  const m: Record<string, number> = {};
  for (const p of parts) if (p.type !== "literal") m[p.type] = Number(p.value);
  const asUTC = Date.UTC(
    m.year,
    m.month - 1,
    m.day,
    m.hour === 24 ? 0 : m.hour,
    m.minute,
    m.second
  );
  return Math.round((asUTC - utcMillis) / 60000);
}

/**
 * Interpret a `datetime-local` value ("YYYY-MM-DDTHH:mm") as a Europe/Berlin
 * wall-clock time and return the absolute instant as an ISO-UTC string. This
 * makes slot entry independent of the admin's own computer timezone — what they
 * type is always read as CEST.
 */
export function berlinLocalToISO(naive: string): string {
  const [datePart, timePart] = naive.split("T");
  const [y, mo, d] = datePart.split("-").map(Number);
  const [h, mi] = (timePart || "00:00").split(":").map(Number);
  const guess = Date.UTC(y, mo - 1, d, h, mi);
  // One refinement pass handles DST edges.
  const corrected = guess - berlinOffsetMinutes(guess) * 60000;
  return new Date(guess - berlinOffsetMinutes(corrected) * 60000).toISOString();
}

/** Render an absolute instant as a Berlin wall-clock `datetime-local` value. */
export function isoToBerlinLocal(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Berlin",
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).formatToParts(new Date(iso));
  const m: Record<string, string> = {};
  for (const p of parts) if (p.type !== "literal") m[p.type] = p.value;
  const hour = m.hour === "24" ? "00" : m.hour;
  return `${m.year}-${m.month}-${m.day}T${hour}:${m.minute}`;
}
