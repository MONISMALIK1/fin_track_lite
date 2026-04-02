# schemas.py — Pydantic models for input validation and response shaping

from pydantic import BaseModel, field_validator
from datetime import date, datetime
from typing import Optional, List

from models import Role, EntryType


# ── Auth ───────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Users ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    role: Role = Role.viewer

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

class UserOut(BaseModel):
    id: int
    username: str
    role: Role
    is_active: bool

    model_config = {"from_attributes": True}


# ── Entries ────────────────────────────────────────────────────────────────────

class EntryCreate(BaseModel):
    amount:   float
    type:     EntryType
    category: str
    date:     date
    notes:    Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2)

    @field_validator("category")
    @classmethod
    def category_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Category cannot be blank")
        return v.strip()

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date cannot be in the future")
        return v

class EntryUpdate(BaseModel):
    amount:   Optional[float]     = None
    type:     Optional[EntryType] = None
    category: Optional[str]       = None
    date:     Optional[date]       = None
    notes:    Optional[str]        = None

class EntryOut(BaseModel):
    id:         int
    amount:     float
    type:       EntryType
    category:   str
    date:       date
    notes:      Optional[str]
    user_id:    int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Summary ────────────────────────────────────────────────────────────────────

class CategoryBreakdown(BaseModel):
    category: str
    total:    float
    count:    int

class MonthlyTotal(BaseModel):
    year:     int
    month:    int
    income:   float
    expenses: float
    net:      float

class Summary(BaseModel):
    total_income:       float
    total_expenses:     float
    balance:            float
    category_breakdown: List[CategoryBreakdown]
    monthly_totals:     List[MonthlyTotal]
    recent_entries:     List[EntryOut]


# ── AI ─────────────────────────────────────────────────────────────────────────

class AIQuestion(BaseModel):
    question: str = "Give me a brief summary of my finances and one actionable tip."

class AIResponse(BaseModel):
    answer: str
    model:  str
