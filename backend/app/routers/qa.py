"""Q&A endpoints.

Candidate:
  POST /api/me/questions         — submit a question (201)
  GET  /api/me/questions         — list own questions, newest first, with sla_text

Admin:
  GET  /api/admin/questions      — all questions with asker info; unanswered first
  POST /api/admin/questions/{id}/answer — set answer + answered_at (200); 404 if missing
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.audit import record
from app.config_helpers import get_config_str
from app.db import get_db
from app.deps import current_admin, current_candidate, require_nda
from app.models import Candidate, Question
from app.schemas import AnswerCreate, QuestionCreate

_DEFAULT_SLA = "Questions are answered by a person, usually within 1 working day."

me_router = APIRouter(prefix="/api/me", tags=["me-qa"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin-qa"])


def _question_dict(q: Question) -> dict:
    return {
        "id": q.id,
        "body": q.body,
        "asked_at": q.asked_at,
        "answer": q.answer,
        "answered_at": q.answered_at,
    }


# ---------------------------------------------------------------------------
# Candidate endpoints
# ---------------------------------------------------------------------------


@me_router.post("/questions", status_code=status.HTTP_201_CREATED)
def submit_question(
    body: QuestionCreate,
    db: Session = Depends(get_db),  # noqa: B008
    cand: Candidate = Depends(require_nda),  # noqa: B008
):
    """Candidate submits a question. Rejects empty / whitespace-only body."""
    stripped = body.body.strip()
    if not stripped:
        # Use the integer literal: the Starlette HTTP_422_* constant name is
        # deprecated in the installed version and accessing it warns.
        raise HTTPException(
            status_code=422,
            detail="body must not be empty",
        )

    q = Question(candidate_id=cand.id, body=stripped)
    db.add(q)
    db.commit()
    db.refresh(q)

    # Audit: detail = question id ONLY (never the body text)
    record(db, actor=cand.candidate_id, action="question_submit", detail=str(q.id))

    return _question_dict(q)


@me_router.get("/questions")
def list_my_questions(
    db: Session = Depends(get_db),  # noqa: B008
    cand: Candidate = Depends(current_candidate),  # noqa: B008
):
    """Return the session candidate's questions (newest first) plus sla_text.

    Viewing the thread marks any newly-answered questions as seen, clearing the
    candidate's unread-answer notification.
    """
    questions = (
        db.query(Question)
        .filter_by(candidate_id=cand.id)
        .order_by(desc(Question.asked_at))
        .all()
    )

    # Mark answered-but-unseen questions as seen now that the candidate is viewing.
    now = datetime.now(UTC)
    changed = False
    for q in questions:
        if q.answer is not None and q.answer_seen_at is None:
            q.answer_seen_at = now
            changed = True
    if changed:
        db.commit()

    sla_text = get_config_str(db, "qa_sla_text", _DEFAULT_SLA)
    return {
        "questions": [_question_dict(q) for q in questions],
        "sla_text": sla_text,
    }


@me_router.get("/notifications")
def my_notifications(
    db: Session = Depends(get_db),  # noqa: B008
    cand: Candidate = Depends(current_candidate),  # noqa: B008
):
    """Lightweight badge poll: how many of my questions were answered but not yet seen."""
    n = db.execute(
        select(func.count(Question.id)).where(
            Question.candidate_id == cand.id,
            Question.answer.isnot(None),
            Question.answer_seen_at.is_(None),
        )
    ).scalar()
    return {"answered_unseen": n or 0}


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@admin_router.get("/questions")
def admin_list_questions(
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    """Return ALL questions joined to asker; unanswered first, newest within group."""
    rows = (
        db.query(Question, Candidate)
        .join(Candidate, Question.candidate_id == Candidate.id)
        .order_by(
            # unanswered (answer IS NULL) first
            case((Question.answer.is_(None), 0), else_=1),
            desc(Question.asked_at),
        )
        .all()
    )
    return [
        {
            "id": q.id,
            "candidate_id": c.candidate_id,
            "first_name": c.first_name,
            "body": q.body,
            "asked_at": q.asked_at,
            "answer": q.answer,
            "answered_at": q.answered_at,
            "answered": q.answer is not None,
        }
        for q, c in rows
    ]


@admin_router.post("/questions/{question_id}/answer")
def admin_answer_question(
    question_id: int,
    body: AnswerCreate,
    db: Session = Depends(get_db),  # noqa: B008
    _: object = Depends(current_admin),  # noqa: B008
):
    """Set answer + answered_at on a question. 404 if not found."""
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="question not found")

    stripped_answer = body.answer.strip()
    if not stripped_answer:
        raise HTTPException(status_code=422, detail="answer must not be empty")

    q.answer = stripped_answer
    q.answered_at = datetime.now(UTC)
    db.commit()
    db.refresh(q)

    # Audit: detail = question id ONLY (never the answer text)
    record(db, actor="admin", action="question_answer", detail=str(q.id))

    return _question_dict(q)
