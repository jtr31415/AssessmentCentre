"""Prep-window unlock computation and booking preview.

Pure module — no database access. All datetimes must be tz-aware UTC.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def compute_unlock_at(
    slot_starts_at: datetime,
    booked_at: datetime,
    prep_window_days: int,
) -> datetime:
    """Return the datetime at which content unlocks for a booking.

    unlock_at = max(booked_at, slot_starts_at - timedelta(days=prep_window_days))

    If the nominal unlock (slot - N days) is already in the past at the time of
    booking, content unlocks immediately (i.e. unlock_at == booked_at).
    """
    nominal_unlock = slot_starts_at - timedelta(days=prep_window_days)
    return max(booked_at, nominal_unlock)


def build_preview(
    slot_starts_at: datetime,
    now: datetime,
    prep_window_days: int,
    tz_name: str,
) -> dict:
    """Build the booking-preview dict shown to a candidate before they confirm.

    Returns:
        assessment_at_iso: ISO-8601 string of slot_starts_at (UTC)
        unlock_at_iso:     ISO-8601 string of unlock_at (UTC)
        prep_days:         float rounded to 1 dp — days between unlock_at and slot
        assessment_display: slot_starts_at formatted in tz_name
        unlock_display:     unlock_at formatted in tz_name
        unlocks_immediately: True if unlock_at == now (content available straight away)
    """
    unlock_at = compute_unlock_at(slot_starts_at, now, prep_window_days)
    prep_days = round((slot_starts_at - unlock_at).total_seconds() / 86400, 1)
    unlocks_immediately = unlock_at == now

    tz = ZoneInfo(tz_name)

    def _display(dt: datetime) -> str:
        local = dt.astimezone(tz)
        # Portable cross-platform day formatting (no %-d on Windows)
        return f"{local:%a} {local.day} {local:%b %Y, %H:%M}"

    return {
        "assessment_at_iso": slot_starts_at.isoformat(),
        "unlock_at_iso": unlock_at.isoformat(),
        "prep_days": prep_days,
        "assessment_display": _display(slot_starts_at),
        "unlock_display": _display(unlock_at),
        "unlocks_immediately": unlocks_immediately,
    }
