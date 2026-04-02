# models.py — SQLAlchemy table definitions

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Date, Text, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship

from database import Base


class Role(str, enum.Enum):
    viewer  = "viewer"   # read-only
    analyst = "analyst"  # read + filters + AI insights
    admin   = "admin"    # full CRUD + user management


class EntryType(str, enum.Enum):
    income  = "income"
    expense = "expense"


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True)
    username        = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role            = Column(SAEnum(Role), default=Role.viewer, nullable=False)
    is_active       = Column(Boolean, default=True)

    entries = relationship("Entry", back_populates="owner", cascade="all, delete-orphan")


class Entry(Base):
    __tablename__ = "entries"

    id         = Column(Integer, primary_key=True)
    amount     = Column(Float,  nullable=False)
    type       = Column(SAEnum(EntryType), nullable=False)
    category   = Column(String, nullable=False)
    date       = Column(Date,   nullable=False)
    notes      = Column(Text,   nullable=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="entries")
