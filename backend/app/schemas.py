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
