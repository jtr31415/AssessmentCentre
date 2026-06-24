"""Tests for prep_window.py and config_helpers.py — written BEFORE implementation (TDD RED)."""

from datetime import datetime, timedelta, timezone

import pytest

UTC = timezone.utc


# ---------------------------------------------------------------------------
# compute_unlock_at
# ---------------------------------------------------------------------------

class TestComputeUnlockAt:
    """Tests for the core unlock-at computation: max(booked_at, slot - N days)."""

    def test_slot_far_out_unlock_is_nominal(self):
        """Slot 30 days out, N=8 → unlock == slot - 8d (not immediate)."""
        from app.prep_window import compute_unlock_at

        booked_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot_starts_at = booked_at + timedelta(days=30)  # 2026-10-31 12:00
        result = compute_unlock_at(slot_starts_at, booked_at, prep_window_days=8)
        assert result == slot_starts_at - timedelta(days=8)

    def test_slot_far_out_prep_days_is_full_window(self):
        """Slot 30 days out, N=8 → prep_days == 8.0."""
        from app.prep_window import compute_unlock_at

        booked_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot_starts_at = booked_at + timedelta(days=30)
        unlock = compute_unlock_at(slot_starts_at, booked_at, prep_window_days=8)
        prep_days = round((slot_starts_at - unlock).total_seconds() / 86400, 1)
        assert prep_days == 8.0

    def test_slot_far_out_not_immediate(self):
        """Slot 30 days out, N=8 → unlocks_immediately is False."""
        from app.prep_window import compute_unlock_at

        booked_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot_starts_at = booked_at + timedelta(days=30)
        unlock = compute_unlock_at(slot_starts_at, booked_at, prep_window_days=8)
        assert unlock != booked_at  # nominal unlock is in the future → not immediate

    def test_slot_exactly_n_days_out_unlock_is_now(self):
        """Slot exactly 8 days out, N=8 → unlock == booked_at (immediate, prep_days==8.0)."""
        from app.prep_window import compute_unlock_at

        booked_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot_starts_at = booked_at + timedelta(days=8)
        result = compute_unlock_at(slot_starts_at, booked_at, prep_window_days=8)
        # nominal = slot - 8d = booked_at → max(booked_at, booked_at) = booked_at
        assert result == booked_at
        prep_days = round((slot_starts_at - result).total_seconds() / 86400, 1)
        assert prep_days == 8.0

    def test_slot_exactly_n_days_out_is_immediate(self):
        """Slot exactly 8 days out, N=8 → unlocks_immediately True."""
        from app.prep_window import compute_unlock_at

        booked_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot_starts_at = booked_at + timedelta(days=8)
        unlock = compute_unlock_at(slot_starts_at, booked_at, prep_window_days=8)
        assert unlock == booked_at  # confirms immediate

    def test_slot_3_days_out_unlock_is_now(self):
        """Slot 3 days out, N=8 → unlock == booked_at (immediate), prep_days ≈ 3.0."""
        from app.prep_window import compute_unlock_at

        booked_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot_starts_at = booked_at + timedelta(days=3)
        result = compute_unlock_at(slot_starts_at, booked_at, prep_window_days=8)
        assert result == booked_at
        prep_days = round((slot_starts_at - result).total_seconds() / 86400, 1)
        assert prep_days == 3.0

    def test_slot_3_days_out_is_immediate(self):
        """Slot 3 days out, N=8 → unlocks_immediately True."""
        from app.prep_window import compute_unlock_at

        booked_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot_starts_at = booked_at + timedelta(days=3)
        unlock = compute_unlock_at(slot_starts_at, booked_at, prep_window_days=8)
        assert unlock == booked_at

    def test_slot_1_hour_out_prep_days_rounds_to_zero(self):
        """Slot 1 hour out, N=8 → unlock immediate, prep_days ≈ 0.0 (round(1/24,1)=0.0)."""
        from app.prep_window import compute_unlock_at

        booked_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot_starts_at = booked_at + timedelta(hours=1)
        result = compute_unlock_at(slot_starts_at, booked_at, prep_window_days=8)
        assert result == booked_at
        prep_days = round((slot_starts_at - result).total_seconds() / 86400, 1)
        assert prep_days == 0.0

    def test_explicit_n5_on_30_day_slot(self):
        """Explicit N=5 on 30-day-out slot → unlock == slot-5d, prep_days==5.0."""
        from app.prep_window import compute_unlock_at

        booked_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot_starts_at = booked_at + timedelta(days=30)
        result = compute_unlock_at(slot_starts_at, booked_at, prep_window_days=5)
        assert result == slot_starts_at - timedelta(days=5)
        prep_days = round((slot_starts_at - result).total_seconds() / 86400, 1)
        assert prep_days == 5.0


# ---------------------------------------------------------------------------
# build_preview
# ---------------------------------------------------------------------------

class TestBuildPreview:
    """Tests for build_preview — the dict returned to the frontend."""

    def _make_preview(self, days_out: int, n: int = 8):
        from app.prep_window import build_preview

        now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        slot = now + timedelta(days=days_out)
        return build_preview(slot_starts_at=slot, now=now, prep_window_days=n, tz_name="Europe/London")

    def test_build_preview_far_slot_keys_present(self):
        """build_preview returns all required keys."""
        preview = self._make_preview(days_out=30)
        assert set(preview.keys()) == {
            "assessment_at_iso", "unlock_at_iso", "prep_days",
            "assessment_display", "unlock_display", "unlocks_immediately",
        }

    def test_build_preview_far_slot_iso_fields_are_utc(self):
        """ISO fields in build_preview contain UTC offset +00:00."""
        preview = self._make_preview(days_out=30)
        assert "+00:00" in preview["assessment_at_iso"]
        assert "+00:00" in preview["unlock_at_iso"]

    def test_build_preview_far_slot_prep_days(self):
        """build_preview: 30-day slot, N=8 → prep_days==8.0, unlocks_immediately False."""
        preview = self._make_preview(days_out=30, n=8)
        assert preview["prep_days"] == 8.0
        assert preview["unlocks_immediately"] is False

    def test_build_preview_immediate_slot_unlocks_immediately(self):
        """build_preview: 3-day slot, N=8 → unlocks_immediately True."""
        preview = self._make_preview(days_out=3, n=8)
        assert preview["unlocks_immediately"] is True

    def test_build_preview_display_strings_contain_weekday_and_month(self):
        """build_preview display strings formatted in Europe/London contain weekday + month."""
        from app.prep_window import build_preview

        # 2026-11-03 14:00 UTC → in London (no BST in Nov) is same time
        slot = datetime(2026, 11, 3, 14, 0, tzinfo=UTC)
        now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        preview = build_preview(slot_starts_at=slot, now=now, prep_window_days=8, tz_name="Europe/London")

        assessment_display = preview["assessment_display"]
        # Should contain weekday abbreviation ("Tue"), day "3", month "Nov", year "2026", time "14:00"
        assert "Tue" in assessment_display
        assert "3" in assessment_display
        assert "Nov" in assessment_display
        assert "2026" in assessment_display
        assert "14:00" in assessment_display

    def test_build_preview_unlock_display_formatted_in_tz(self):
        """build_preview unlock_display is formatted in Europe/London, not raw UTC."""
        from app.prep_window import build_preview

        slot = datetime(2026, 11, 3, 14, 0, tzinfo=UTC)
        now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        preview = build_preview(slot_starts_at=slot, now=now, prep_window_days=8, tz_name="Europe/London")

        # unlock_at = slot - 8d = 2026-10-26 14:00 UTC (still BST? No, clocks go back 25 Oct 2026)
        # 25 Oct 2026 → clocks go back at 01:00 UTC. 26 Oct 14:00 UTC = 14:00 London (GMT).
        unlock_display = preview["unlock_display"]
        assert "Oct" in unlock_display
        assert "2026" in unlock_display

    def test_build_preview_unlocks_immediately_exact_n_days(self):
        """build_preview: slot exactly N days out → unlocks_immediately True, prep_days==8.0."""
        preview = self._make_preview(days_out=8, n=8)
        assert preview["unlocks_immediately"] is True
        assert preview["prep_days"] == 8.0
