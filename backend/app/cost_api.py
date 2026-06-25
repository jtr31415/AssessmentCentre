"""Anthropic organisation Cost API client.

Pulls real USD spend per workspace from the org-level Cost API so each
candidate's spend (their workspace) can be shown to the admin.

Auth: an org **Admin** API key (``sk-ant-admin01-…``, distinct from a normal
key), sent as ``x-api-key``.  Configure via ``ANTHROPIC_ADMIN_API_KEY``.

Cost amounts come back as USD **cents, as decimal strings** (e.g. ``"123.45"``
== $1.23).  The default workspace is reported with ``workspace_id == null``.
"""

from datetime import UTC, datetime, timedelta

import httpx

from app.config import get_settings

COST_API_URL = "https://api.anthropic.com/v1/organizations/cost_report"
ANTHROPIC_VERSION = "2023-06-01"

# How far back to total spend. Daily buckets, max 31 per page → we paginate.
SPEND_LOOKBACK_DAYS = 90
# Safety bound on pagination loops (90 days / 31 per page is ~3 pages; allow slack).
_MAX_PAGES = 64


class CostAPIError(RuntimeError):
    """Cost API was unreachable or returned an error."""


class CostAPINotConfigured(CostAPIError):
    """No Admin API key configured — spend tracking is inert."""


def fetch_workspace_spend_cents(now: datetime | None = None) -> dict[str | None, int]:
    """Return ``{workspace_id -> total USD cents}`` over the lookback window.

    ``workspace_id`` is ``None`` for the default workspace.  Raises
    ``CostAPINotConfigured`` if no Admin key is set, ``CostAPIError`` on any
    upstream failure.
    """
    settings = get_settings()
    key = settings.anthropic_admin_api_key
    if not key:
        raise CostAPINotConfigured("ANTHROPIC_ADMIN_API_KEY is not configured")

    now = now or datetime.now(UTC)
    starting_at = (now - timedelta(days=SPEND_LOOKBACK_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    ending_at = now.strftime("%Y-%m-%dT00:00:00Z")

    base_params: list[tuple[str, str]] = [
        ("starting_at", starting_at),
        ("ending_at", ending_at),
        ("group_by[]", "workspace_id"),
        ("limit", "31"),
    ]
    headers = {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION}

    totals: dict[str | None, float] = {}
    try:
        with httpx.Client(timeout=30.0) as client:
            page: str | None = None
            for _ in range(_MAX_PAGES):
                params = list(base_params)
                if page:
                    params.append(("page", page))
                resp = client.get(COST_API_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    raise CostAPIError(
                        f"cost API returned HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                body = resp.json()
                for bucket in body.get("data", []):
                    for item in bucket.get("results", []):
                        amount = item.get("amount")
                        if amount is None:
                            continue
                        ws = item.get("workspace_id")
                        try:
                            totals[ws] = totals.get(ws, 0.0) + float(amount)
                        except (TypeError, ValueError):
                            continue
                if body.get("has_more") and body.get("next_page"):
                    page = body["next_page"]
                else:
                    break
    except httpx.HTTPError as e:
        raise CostAPIError(f"cost API request failed: {e}") from e

    # amount is in cents already; round each workspace total to the nearest cent.
    return {ws: round(v) for ws, v in totals.items()}
