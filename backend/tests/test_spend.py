"""Tests for per-candidate USD spend (workspace mapping + Anthropic Cost API).

The Cost API itself is never hit over the network: the router-level tests
monkeypatch the fetch function, and the parser test uses an httpx MockTransport.
"""

import httpx
from sqlalchemy import select

from app import cost_api
from app.config import get_settings
from app.models import Candidate
from app.seed import seed_admin_and_config


def login_admin(client):
    client.post("/api/auth/admin/login", json={"username": "admin", "password": "changeme"})


def _make_candidate(client, db_session, first_name="Spender"):
    seed_admin_and_config(db_session)
    login_admin(client)
    r = client.post("/api/admin/candidates", json={"first_name": first_name})
    assert r.status_code == 201
    return r.json()["candidate_id"]


# ---------------------------------------------------------------------------
# Workspace assignment
# ---------------------------------------------------------------------------


class TestSetWorkspace:
    def test_set_and_clear_workspace(self, client, db_session):
        candidate_id = _make_candidate(client, db_session)

        r = client.put(
            f"/api/admin/candidates/{candidate_id}/workspace",
            json={"workspace_id": "wrkspc_01ABC"},
        )
        assert r.status_code == 200
        assert r.json()["workspace_id"] == "wrkspc_01ABC"

        # Appears in the candidate list
        rows = client.get("/api/admin/candidates").json()
        row = next(c for c in rows if c["candidate_id"] == candidate_id)
        assert row["workspace_id"] == "wrkspc_01ABC"

        # Clearing (empty string → None)
        r = client.put(
            f"/api/admin/candidates/{candidate_id}/workspace",
            json={"workspace_id": ""},
        )
        assert r.status_code == 200
        assert r.json()["workspace_id"] is None

    def test_set_workspace_requires_admin(self, client, db_session):
        seed_admin_and_config(db_session)
        r = client.put("/api/admin/candidates/cand-01/workspace", json={"workspace_id": "x"})
        assert r.status_code == 401

    def test_set_workspace_unknown_candidate_404(self, client, db_session):
        seed_admin_and_config(db_session)
        login_admin(client)
        r = client.put("/api/admin/candidates/NOPE/workspace", json={"workspace_id": "x"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Spend refresh
# ---------------------------------------------------------------------------


class TestSpendRefresh:
    def test_refresh_503_when_admin_key_missing(self, client, db_session, monkeypatch):
        seed_admin_and_config(db_session)
        login_admin(client)
        monkeypatch.setattr(get_settings(), "anthropic_admin_api_key", "")

        r = client.post("/api/admin/spend/refresh")
        assert r.status_code == 503
        assert "ANTHROPIC_ADMIN_API_KEY" in r.json()["detail"]

    def test_refresh_updates_candidate_spend(self, client, db_session, monkeypatch):
        candidate_id = _make_candidate(client, db_session)
        # Map the candidate to a workspace
        client.put(
            f"/api/admin/candidates/{candidate_id}/workspace",
            json={"workspace_id": "wrkspc_X"},
        )

        # Stub the Cost API: workspace X has 4200 cents.
        monkeypatch.setattr(
            "app.routers.admin.fetch_workspace_spend_cents",
            lambda: {"wrkspc_X": 4200, None: 100},
        )

        r = client.post("/api/admin/spend/refresh")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["updated"] == 1

        db_session.expire_all()
        cand = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == candidate_id)
        ).scalar_one()
        assert cand.usd_spend_cents == 4200
        assert cand.spend_updated_at is not None

        # Surfaced in the candidate list
        rows = client.get("/api/admin/candidates").json()
        row = next(c for c in rows if c["candidate_id"] == candidate_id)
        assert row["usd_spend_cents"] == 4200

    def test_refresh_zeroes_workspace_with_no_cost(self, client, db_session, monkeypatch):
        candidate_id = _make_candidate(client, db_session)
        client.put(
            f"/api/admin/candidates/{candidate_id}/workspace",
            json={"workspace_id": "wrkspc_Y"},
        )
        # Cost API returns nothing for this workspace → spend should be 0, not left null.
        monkeypatch.setattr(
            "app.routers.admin.fetch_workspace_spend_cents",
            lambda: {"wrkspc_other": 999},
        )
        r = client.post("/api/admin/spend/refresh")
        assert r.status_code == 200

        db_session.expire_all()
        cand = db_session.execute(
            select(Candidate).where(Candidate.candidate_id == candidate_id)
        ).scalar_one()
        assert cand.usd_spend_cents == 0


# ---------------------------------------------------------------------------
# Cost API parser (mocked transport — no network)
# ---------------------------------------------------------------------------


class TestCostApiParser:
    def test_parses_and_sums_across_pages_and_workspaces(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "anthropic_admin_api_key", "sk-ant-admin01-test")

        def handler(request: httpx.Request) -> httpx.Response:
            if b"page=" not in request.url.query:
                # First page
                return httpx.Response(
                    200,
                    json={
                        "data": [
                            {
                                "starting_at": "2025-08-01T00:00:00Z",
                                "ending_at": "2025-08-02T00:00:00Z",
                                "results": [
                                    {"amount": "100", "currency": "USD", "workspace_id": "ws_A"},
                                    {"amount": "25", "currency": "USD", "workspace_id": None},
                                ],
                            }
                        ],
                        "has_more": True,
                        "next_page": "PAGE2",
                    },
                )
            # Second page
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "starting_at": "2025-08-02T00:00:00Z",
                            "ending_at": "2025-08-03T00:00:00Z",
                            "results": [
                                {"amount": "50", "currency": "USD", "workspace_id": "ws_A"},
                            ],
                        }
                    ],
                    "has_more": False,
                    "next_page": None,
                },
            )

        transport = httpx.MockTransport(handler)
        real_client = httpx.Client
        monkeypatch.setattr(
            cost_api.httpx, "Client", lambda *a, **k: real_client(transport=transport)
        )

        totals = cost_api.fetch_workspace_spend_cents()
        assert totals == {"ws_A": 150, None: 25}

    def test_raises_not_configured_without_key(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "anthropic_admin_api_key", "")
        import pytest

        with pytest.raises(cost_api.CostAPINotConfigured):
            cost_api.fetch_workspace_spend_cents()
