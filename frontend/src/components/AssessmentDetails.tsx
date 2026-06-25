import { useEffect, useState } from "react";
import { MapPin, Clock, Users, CalendarClock } from "lucide-react";
import { api } from "../api/client";

interface Info {
  format: string;
  duration: string;
  location: string;
  prep_window_days: number;
}

/**
 * Admin-configurable assessment details (format / duration / location) plus the
 * prep-window explanation. Shown on the booking page and the candidate dashboard.
 * Renders nothing until loaded; omits any blank field.
 */
export default function AssessmentDetails() {
  const [info, setInfo] = useState<Info | null>(null);

  useEffect(() => {
    api
      .get("/api/me/assessment-info")
      .then((d) => setInfo(d as Info))
      .catch(() => {});
  }, []);

  if (!info) return null;

  const rows: { Icon: typeof Users; label: string; value: string }[] = [];
  if (info.format) rows.push({ Icon: Users, label: "Format", value: info.format });
  if (info.duration) rows.push({ Icon: Clock, label: "Duration", value: info.duration });
  if (info.location) rows.push({ Icon: MapPin, label: "Location", value: info.location });

  return (
    <div className="border border-brand-hair rounded-lg bg-white p-5 space-y-3">
      <div className="panel-title">
        <h3 className="font-bold text-brand-blue text-sm">Assessment Details</h3>
      </div>

      {rows.length > 0 && (
        <ul className="ml-4 space-y-2">
          {rows.map(({ Icon, label, value }) => (
            <li key={label} className="flex items-start gap-2.5 text-sm">
              <Icon className="w-4 h-4 text-brand-muted flex-shrink-0 mt-0.5" aria-hidden={true} />
              <span className="text-brand-muted w-20 flex-shrink-0">{label}</span>
              <span className="font-semibold text-brand-ink">{value}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="ml-4 flex items-start gap-2.5 text-xs text-brand-ink bg-brand-b5 border border-brand-b4 rounded p-3">
        <CalendarClock
          className="w-4 h-4 text-brand-blue flex-shrink-0 mt-0.5"
          aria-hidden={true}
        />
        <span className="leading-relaxed">
          Your exercise materials are released{" "}
          <strong className="tabular-numbers">{info.prep_window_days} days</strong> before your
          assessment, giving you that time to prepare. They are not available any earlier.
        </span>
      </div>
    </div>
  );
}
