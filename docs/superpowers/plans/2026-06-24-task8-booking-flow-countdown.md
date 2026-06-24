# Task 8: Candidate Booking Flow + Unlock Countdown + Dashboard Booked-State

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GET /api/me/booking backend endpoint and implement the full candidate booking UI (slot picker with preview, countdown, booked-state dashboard).

**Architecture:** Small backend endpoint reads the candidate's Booking row; frontend has three new components (CandidateBooking page, Countdown component, extended CandidateDashboard) wired together with a new /book route.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React 19 + TypeScript + Vite + oxlint (frontend).

## Global Constraints

- No new dependencies (backend or frontend).
- Lint: `ruff check .` clean (backend); `npm run lint` zero errors (frontend uses oxlint).
- Build: `npm run build` clean (frontend).
- Branch: `phase2-slots-booking`.
- Backend test runner: `TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5433/app_test ../.venv/Scripts/python.exe -m pytest tests/test_booking.py -v`
- All datetimes UTC-aware; use `datetime.now(UTC)` not `datetime.utcnow()`.

---

### Task 1: Backend GET /api/me/booking

**Files:**
- Modify: `backend/app/routers/booking.py` — add new endpoint
- Modify: `backend/tests/test_booking.py` — add TestMyBooking class

**Interfaces:**
- Consumes: `current_candidate` dep from `app.deps`, `Booking` model, `Slot` model, `get_db`
- Produces: `GET /api/me/booking` → `{"has_booking": false}` or `{"has_booking": true, "slot_starts_at": <iso>, "unlock_at": <iso>, "unlocked": <bool>}`

The router prefix is `/api/slots`; this new endpoint must use a DIFFERENT router prefix `/api/me`. Add a new `me_router = APIRouter(prefix="/api/me", tags=["me"])` in `booking.py` and register it in `main.py`.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_booking.py`

Append this class at the end of the file:

```python
# ---------------------------------------------------------------------------
# GET /api/me/booking
# ---------------------------------------------------------------------------

class TestMyBooking:
    def test_no_booking_returns_has_booking_false(self, client, db_session):
        """Candidate with no booking → {has_booking: false}."""
        seed_admin_and_config(db_session)
        create_and_login_candidate(client)

        r = client.get("/api/me/booking")
        assert r.status_code == 200, r.text
        assert r.json() == {"has_booking": False}

    def test_after_booking_returns_has_booking_true_with_correct_fields(self, client, db_session):
        """After booking, response has has_booking=true, slot_starts_at, unlock_at."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        # Create slot + book it
        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future, capacity=1)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        r = client.post(f"/api/slots/{slot_id}/book")
        assert r.status_code == 201, r.text

        r = client.get("/api/me/booking")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["has_booking"] is True
        assert "slot_starts_at" in data
        assert "unlock_at" in data
        assert "unlocked" in data

    def test_unlocked_false_when_unlock_at_is_future(self, client, db_session):
        """With unlock_at 20 days in the future, unlocked should be False."""
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        client.post("/api/auth/logout")
        login_admin(client)
        future = datetime.now(UTC) + timedelta(days=20)
        slot_id = admin_create_slot(client, future, capacity=1)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        client.post(f"/api/slots/{slot_id}/book")

        r = client.get("/api/me/booking")
        assert r.status_code == 200, r.text
        assert r.json()["unlocked"] is False

    def test_unlocked_true_when_unlock_at_is_past(self, client, db_session):
        """Booking with past unlock_at → unlocked=True."""
        from sqlalchemy import select as sa_select
        seed_admin_and_config(db_session)
        candidate_id = create_and_login_candidate(client)

        client.post("/api/auth/logout")
        login_admin(client)
        # Slot 2 days away → unlock_at == now (unlocks immediately)
        future = datetime.now(UTC) + timedelta(days=2)
        slot_id = admin_create_slot(client, future, capacity=1)

        client.post("/api/auth/logout")
        client.post(
            "/api/auth/candidate/login",
            json={"candidate_id": candidate_id, "password": "pw-123456"},
        )
        client.post(f"/api/slots/{slot_id}/book")

        # Force unlock_at to a past time in DB
        from app.models import Candidate as CandModel, Booking as BookModel
        cand_row = db_session.execute(
            sa_select(CandModel).where(CandModel.candidate_id == candidate_id)
        ).scalar_one()
        booking = db_session.execute(
            sa_select(BookModel).where(BookModel.candidate_id == cand_row.id)
        ).scalar_one()
        booking.unlock_at = datetime.now(UTC) - timedelta(hours=1)
        db_session.commit()

        r = client.get("/api/me/booking")
        assert r.status_code == 200, r.text
        assert r.json()["unlocked"] is True

    def test_requires_candidate_auth(self, client, db_session):
        """GET /api/me/booking returns 401 when not authenticated."""
        seed_admin_and_config(db_session)
        r = client.get("/api/me/booking")
        assert r.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd C:/Users/joetr/Documents/Assessment/backend
TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5433/app_test ../.venv/Scripts/python.exe -m pytest tests/test_booking.py::TestMyBooking -v
```

Expected: ImportError or 404/AttributeError failures (endpoint doesn't exist yet).

- [ ] **Step 3: Add the me_router and endpoint in booking.py**

Add after line 29 (after `admin_router = ...`):

```python
me_router = APIRouter(prefix="/api/me", tags=["me"])
```

Add at the end of the file (after the `release_booking` function):

```python
# ---------------------------------------------------------------------------
# Candidate: read own booking
# ---------------------------------------------------------------------------

@me_router.get("/booking")
def my_booking(
    db: Session = Depends(get_db),  # noqa: B008
    cand: Candidate = Depends(current_candidate),  # noqa: B008
):
    """Return the authenticated candidate's booking, or has_booking=false."""
    booking = (
        db.execute(select(Booking).where(Booking.candidate_id == cand.id))
        .scalar_one_or_none()
    )
    if booking is None:
        return {"has_booking": False}

    slot = db.get(Slot, booking.slot_id)
    now = datetime.now(UTC)
    return {
        "has_booking": True,
        "slot_starts_at": slot.starts_at.isoformat(),
        "unlock_at": booking.unlock_at.isoformat(),
        "unlocked": now >= booking.unlock_at,
    }
```

- [ ] **Step 4: Register me_router in main.py**

Read `backend/app/main.py` first, then add `app.include_router(me_router)` alongside the other router registrations. Import `me_router` from `app.routers.booking`.

- [ ] **Step 5: Run tests to verify they pass**

```
cd C:/Users/joetr/Documents/Assessment/backend
TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5433/app_test ../.venv/Scripts/python.exe -m pytest tests/test_booking.py::TestMyBooking -v
```

Expected: 5 PASSED.

- [ ] **Step 6: Run ruff**

```
cd C:/Users/joetr/Documents/Assessment/backend
../.venv/Scripts/python.exe -m ruff check .
```

Expected: no output (clean).

- [ ] **Step 7: Run full backend suite**

```
cd C:/Users/joetr/Documents/Assessment/backend
TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5433/app_test ../.venv/Scripts/python.exe -m pytest -v
```

Expected: all green.

---

### Task 2: Frontend — Countdown component

**Files:**
- Create: `frontend/src/components/Countdown.tsx`

**Interfaces:**
- Props: `{ unlockAt: string; onUnlock: () => void }`
- Renders: `"D days H hours M min S sec"` live countdown; calls `onUnlock()` once at <= 0.

- [ ] **Step 1: Create Countdown.tsx**

```tsx
import { useEffect, useState } from "react";

interface Props {
  unlockAt: string;
  onUnlock: () => void;
}

function getRemaining(unlockAt: string): number {
  return Math.max(0, new Date(unlockAt).getTime() - Date.now());
}

export default function Countdown({ unlockAt, onUnlock }: Props) {
  const [msLeft, setMsLeft] = useState(() => getRemaining(unlockAt));
  const [fired, setFired] = useState(false);

  useEffect(() => {
    if (msLeft <= 0 && !fired) {
      setFired(true);
      onUnlock();
      return;
    }
    const id = setInterval(() => {
      const rem = getRemaining(unlockAt);
      setMsLeft(rem);
      if (rem <= 0) {
        clearInterval(id);
        if (!fired) {
          setFired(true);
          onUnlock();
        }
      }
    }, 1000);
    return () => clearInterval(id);
  }, [unlockAt, onUnlock, fired, msLeft]);

  const totalSec = Math.floor(msLeft / 1000);
  const days = Math.floor(totalSec / 86400);
  const hours = Math.floor((totalSec % 86400) / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const seconds = totalSec % 60;

  if (msLeft <= 0) return <span>Unlocking...</span>;

  return (
    <span>
      {days}d {hours}h {minutes}m {seconds}s
    </span>
  );
}
```

- [ ] **Step 2: Verify lint passes**

```
cd C:/Users/joetr/Documents/Assessment/frontend
npm run lint
```

Expected: zero errors.

---

### Task 3: Frontend — CandidateBooking page

**Files:**
- Create: `frontend/src/pages/CandidateBooking.tsx`

**Interfaces:**
- Fetches: `GET /api/slots/open` → `Array<{ id: number; starts_at: string }>`
- Fetches: `GET /api/slots/{id}/preview` → `{ unlock_display: string; prep_days: number; assessment_display: string; unlocks_immediately: boolean }`
- Posts: `POST /api/slots/{id}/book` → 201 on success, 409 with `detail` on conflict

- [ ] **Step 1: Create CandidateBooking.tsx**

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
}

export default function CandidateBooking() {
  const nav = useNavigate();
  const [slots, setSlots] = useState<OpenSlot[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loadError, setLoadError] = useState("");
  const [bookError, setBookError] = useState("");
  const [booking, setBooking] = useState(false);

  async function loadSlots() {
    setLoadError("");
    try {
      const data = await api.get("/api/slots/open");
      setSlots(data as OpenSlot[]);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }

  useEffect(() => { loadSlots(); }, []);

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

  return (
    <div style={{ padding: 16 }}>
      <h1>Book your assessment slot</h1>

      {loadError && <p style={{ color: "red" }}>{loadError}</p>}

      {slots.length === 0 && !loadError && <p>No slots currently available.</p>}

      {slots.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {slots.map((slot) => (
            <li key={slot.id} style={{ marginBottom: 8 }}>
              <button
                onClick={() => handleSelect(slot.id)}
                style={{
                  fontWeight: selectedId === slot.id ? "bold" : "normal",
                  cursor: "pointer",
                }}
              >
                {new Date(slot.starts_at).toLocaleString()}
              </button>
            </li>
          ))}
        </ul>
      )}

      {preview && selectedId !== null && (
        <div style={{ marginTop: 16, padding: 12, border: "1px solid #ccc", borderRadius: 4 }}>
          <p>
            {preview.unlocks_immediately
              ? <>If you choose this slot, your exercise data unlocks <strong>immediately</strong>, giving you <strong>{preview.prep_days}</strong> days to work on it before your assessment on <strong>{preview.assessment_display}</strong>.</>
              : <>If you choose this slot, your exercise data unlocks on <strong>{preview.unlock_display}</strong>, giving you <strong>{preview.prep_days}</strong> days to work on it before your assessment on <strong>{preview.assessment_display}</strong>.</>
            }
          </p>
          <button onClick={handleConfirm} disabled={booking}>
            {booking ? "Booking..." : "Confirm"}
          </button>
        </div>
      )}

      {bookError && <p style={{ color: "red", marginTop: 8 }}>{bookError}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Verify lint passes**

```
cd C:/Users/joetr/Documents/Assessment/frontend
npm run lint
```

Expected: zero errors.

---

### Task 4: Frontend — CandidateDashboard booked-state + Route

**Files:**
- Modify: `frontend/src/pages/CandidateDashboard.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Fetches: `GET /api/me/booking` → `{ has_booking: false }` or `{ has_booking: true, slot_starts_at: string, unlock_at: string, unlocked: boolean }`
- Uses: `<Countdown unlockAt={...} onUnlock={refetch} />`
- Route: `/book` → `<CandidateBooking />`

- [ ] **Step 1: Replace CandidateDashboard.tsx**

```tsx
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import Countdown from "../components/Countdown";

interface NoBooking {
  has_booking: false;
}

interface HasBooking {
  has_booking: true;
  slot_starts_at: string;
  unlock_at: string;
  unlocked: boolean;
}

type BookingState = NoBooking | HasBooking;

export default function CandidateDashboard() {
  const nav = useNavigate();
  const [bookingState, setBookingState] = useState<BookingState | null>(null);
  const [error, setError] = useState("");

  const fetchBooking = useCallback(async () => {
    setError("");
    try {
      const data = await api.get("/api/me/booking");
      setBookingState(data as BookingState);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => { fetchBooking(); }, [fetchBooking]);

  async function logout() {
    try {
      await api.post("/api/auth/logout");
    } finally {
      nav("/login");
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h1>Welcome</h1>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {bookingState === null && !error && <p>Loading...</p>}

      {bookingState !== null && !bookingState.has_booking && (
        <p>
          <Link to="/book">Book your assessment</Link>
        </p>
      )}

      {bookingState !== null && bookingState.has_booking && !bookingState.unlocked && (
        <div>
          <p>
            Your assessment is scheduled for{" "}
            <strong>{new Date(bookingState.slot_starts_at).toLocaleString()}</strong>.
          </p>
          <p>
            Your exercise data unlocks in:{" "}
            <Countdown unlockAt={bookingState.unlock_at} onUnlock={fetchBooking} />
          </p>
        </div>
      )}

      {bookingState !== null && bookingState.has_booking && bookingState.unlocked && (
        <div>
          <p>Your exercise data is unlocked.</p>
          <p style={{ color: "#666", fontSize: 14 }}>
            Download links will be available in the next phase.
          </p>
        </div>
      )}

      <button onClick={logout} style={{ marginTop: 16 }}>Log out</button>
    </div>
  );
}
```

- [ ] **Step 2: Add /book route in App.tsx**

Add import: `import CandidateBooking from "./pages/CandidateBooking";`

Add route inside `<Routes>`: `<Route path="/book" element={<CandidateBooking />} />`

- [ ] **Step 3: Run lint**

```
cd C:/Users/joetr/Documents/Assessment/frontend
npm run lint
```

Expected: zero errors.

- [ ] **Step 4: Run build**

```
cd C:/Users/joetr/Documents/Assessment/frontend
npm run build
```

Expected: clean build, no TS errors.

---

### Task 5: Commit + Write Report

- [ ] **Step 1: Final backend check**

```
cd C:/Users/joetr/Documents/Assessment/backend
TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5433/app_test ../.venv/Scripts/python.exe -m pytest -v
../.venv/Scripts/python.exe -m ruff check .
```

Both must be clean.

- [ ] **Step 2: Final frontend check**

```
cd C:/Users/joetr/Documents/Assessment/frontend
npm run build && npm run lint
```

Both must be clean.

- [ ] **Step 3: Commit**

```
git add backend/app/routers/booking.py backend/app/main.py backend/tests/test_booking.py \
    frontend/src/components/Countdown.tsx frontend/src/pages/CandidateBooking.tsx \
    frontend/src/pages/CandidateDashboard.tsx frontend/src/App.tsx
git commit -m "feat: candidate booking, prep-window preview, and unlock countdown"
```

- [ ] **Step 4: Write report to .superpowers/sdd/task-8-report.md**

Include: commit SHA, backend test summary tail, frontend build/lint confirmation, any concerns.
