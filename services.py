# services.py — business logic kept separate from routes

from datetime import date
from typing import Optional, List

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

import config
from models import Entry, EntryType, User
from schemas import (
    EntryCreate, EntryUpdate,
    Summary, CategoryBreakdown, MonthlyTotal,
)


# ── Entry service ──────────────────────────────────────────────────────────────

class EntryService:

    def __init__(self, db: Session, user_id: int):
        self.db      = db
        self.user_id = user_id

    def _q(self):
        """Base query scoped to the current user."""
        return self.db.query(Entry).filter(Entry.user_id == self.user_id)

    # CRUD ────────────────────────────────────────────────────────────────────

    def create(self, data: EntryCreate) -> Entry:
        entry = Entry(user_id=self.user_id, **data.model_dump())
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_all(
        self,
        type: Optional[EntryType] = None,
        category: Optional[str]   = None,
        date_from: Optional[date] = None,
        date_to:   Optional[date] = None,
    ) -> List[Entry]:
        q = self._q()
        if type:
            q = q.filter(Entry.type == type)
        if category:
            q = q.filter(Entry.category.ilike(f"%{category}%"))
        if date_from:
            q = q.filter(Entry.date >= date_from)
        if date_to:
            q = q.filter(Entry.date <= date_to)
        return q.order_by(Entry.date.desc()).all()

    def get_one(self, entry_id: int) -> Optional[Entry]:
        return self._q().filter(Entry.id == entry_id).first()

    def update(self, entry: Entry, data: EntryUpdate) -> Entry:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entry, field, value)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete(self, entry: Entry) -> None:
        self.db.delete(entry)
        self.db.commit()

    # Analytics ───────────────────────────────────────────────────────────────

    def summary(self) -> Summary:
        total_income   = self._sum_by_type(EntryType.income)
        total_expenses = self._sum_by_type(EntryType.expense)

        return Summary(
            total_income       = total_income,
            total_expenses     = total_expenses,
            balance            = round(total_income - total_expenses, 2),
            category_breakdown = self._category_breakdown(),
            monthly_totals     = self._monthly_totals(),
            recent_entries     = self._q().order_by(Entry.date.desc()).limit(5).all(),
        )

    def _sum_by_type(self, entry_type: EntryType) -> float:
        result = (
            self.db.query(func.sum(Entry.amount))
            .filter(Entry.user_id == self.user_id, Entry.type == entry_type)
            .scalar()
        )
        return round(result or 0.0, 2)

    def _category_breakdown(self) -> List[CategoryBreakdown]:
        rows = (
            self.db.query(Entry.category, func.sum(Entry.amount), func.count(Entry.id))
            .filter(Entry.user_id == self.user_id)
            .group_by(Entry.category)
            .order_by(func.sum(Entry.amount).desc())
            .all()
        )
        return [CategoryBreakdown(category=r[0], total=round(r[1], 2), count=r[2]) for r in rows]

    def _monthly_totals(self) -> List[MonthlyTotal]:
        rows = (
            self.db.query(
                extract("year",  Entry.date).label("year"),
                extract("month", Entry.date).label("month"),
                Entry.type,
                func.sum(Entry.amount).label("total"),
            )
            .filter(Entry.user_id == self.user_id)
            .group_by("year", "month", Entry.type)
            .order_by("year", "month")
            .all()
        )
        # Pivot into {(year, month): {income, expenses}}
        pivot: dict = {}
        for r in rows:
            key = (int(r.year), int(r.month))
            pivot.setdefault(key, {"income": 0.0, "expenses": 0.0})
            if r.type == EntryType.income:
                pivot[key]["income"] = round(r.total, 2)
            else:
                pivot[key]["expenses"] = round(r.total, 2)

        return [
            MonthlyTotal(
                year=y, month=m,
                income=v["income"],
                expenses=v["expenses"],
                net=round(v["income"] - v["expenses"], 2),
            )
            for (y, m), v in sorted(pivot.items())
        ]

    def ai_context(self) -> str:
        """Plain-text financial snapshot to feed into Ollama."""
        s = self.summary()
        lines = [
            f"Total income:   {s.total_income}",
            f"Total expenses: {s.total_expenses}",
            f"Balance:        {s.balance}",
            "",
            "Spending by category:",
        ]
        for c in s.category_breakdown:
            lines.append(f"  {c.category}: {c.total} ({c.count} entries)")
        lines.append("\nLast 5 entries:")
        for e in s.recent_entries:
            lines.append(f"  [{e.date}] {e.type.value} | {e.category} | {e.amount}")
        return "\n".join(lines)


# ── Ollama service ─────────────────────────────────────────────────────────────

async def ask_ollama(context: str, question: str) -> str:
    """
    Send financial context + user question to a local Ollama model.
    Returns a mock response when Ollama is disabled via OLLAMA_ENABLED=false.
    Raises RuntimeError when Ollama is unreachable.
    """
    if not config.settings.OLLAMA_ENABLED:
        return f"[MOCK RESPONSE] Based on your financial data: {question[:50]}... (Ollama disabled in production)"

    system = (
        "You are a helpful personal finance assistant. "
        "Answer concisely based only on the data provided."
    )
    prompt = f"Financial data:\n{context}\n\nQuestion: {question}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{config.settings.OLLAMA_URL}/api/generate",
                json={"model": config.settings.OLLAMA_MODEL, "prompt": prompt, "system": system, "stream": False},
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()

    except httpx.ConnectError:
        raise RuntimeError(
            f"Ollama is not running at {config.settings.OLLAMA_URL}. "
            f"Start it with: ollama serve && ollama pull {config.settings.OLLAMA_MODEL}"
        )
