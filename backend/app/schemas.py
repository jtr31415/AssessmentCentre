from datetime import datetime

from pydantic import BaseModel


class AdminLogin(BaseModel):
    username: str
    password: str


class CandidateLogin(BaseModel):
    candidate_id: str
    password: str


class SetPassword(BaseModel):
    token: str
    password: str


class CreateCandidate(BaseModel):
    first_name: str


class SlotCreate(BaseModel):
    starts_at: datetime
    capacity: int = 1


class SlotUpdate(BaseModel):
    starts_at: datetime | None = None
    capacity: int | None = None


class ReassignRequest(BaseModel):
    candidate_id: str
    new_slot_id: int


class ReleaseRequest(BaseModel):
    candidate_id: str
