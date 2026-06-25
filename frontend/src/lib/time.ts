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
