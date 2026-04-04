# main.py — FastAPI app: all routes in one file, clearly grouped

import asyncio
import csv
import io
import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import config
from auth import create_token, hash_password, verify_password, get_current_user, require
from database import get_db, create_tables
from models import User, Entry, Role
from schemas import (
    LoginRequest, TokenResponse,
    UserCreate, UserOut,
    EntryCreate, EntryUpdate, EntryOut,
    AIQuestion, AIResponse,
    Summary,
    EntryType,
)
from services import EntryService, ask_ollama


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="FinTrack Lite", version="1.0", lifespan=lifespan)


    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/seed", tags=["Utility"])
def seed_db():
    """Seed users into the database if they don't exist."""
    from database import Session, create_tables
    from models import User, Role
    from auth import hash_password

    create_tables()
    db = Session()

    users_data = [
        {"username": "admin",   "password": "admin123",   "role": Role.admin},
        {"username": "analyst", "password": "analyst123", "role": Role.analyst},
        {"username": "viewer",  "password": "viewer123",  "role": Role.viewer},
    ]

    for u in users_data:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if not existing:
            user = User(
                username=u["username"],
                hashed_password=hash_password(u["password"]),
                role=u["role"]
            )
            db.add(user)

    db.commit()
    db.close()

    return {"message": "Users seeded successfully"}



# ── Auth ───────────────────────────────────────────────────────────────────────

@app.post("/login", response_model=TokenResponse, tags=["Auth"])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return TokenResponse(access_token=create_token(user.id, user.username, user.role.value))


# ── Users (admin only) ─────────────────────────────────────────────────────────

@app.post("/users", response_model=UserOut, status_code=201, tags=["Users"])
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require(Role.admin)),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    user = User(username=body.username, hashed_password=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users", response_model=List[UserOut], tags=["Users"])
def list_users(db: Session = Depends(get_db), _: User = Depends(require(Role.admin))):
    return db.query(User).all()


@app.delete("/users/{user_id}", status_code=204, tags=["Users"])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.admin)),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()


# ── Entries ────────────────────────────────────────────────────────────────────

@app.post("/entries", response_model=EntryOut, status_code=201, tags=["Entries"])
def create_entry(
    body: EntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.admin)),
):
    return EntryService(db, current_user.id).create(body)


@app.get("/entries", response_model=List[EntryOut], tags=["Entries"])
def list_entries(
    type:      Optional[EntryType] = Query(None),
    category:  Optional[str]       = Query(None),
    date_from: Optional[date]      = Query(None),
    date_to:   Optional[date]      = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.viewer)),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from cannot be after date_to")
    return EntryService(db, current_user.id).get_all(type, category, date_from, date_to)


@app.get("/export-csv", tags=["Entries"])
def export_entries_csv(
    type:      Optional[EntryType] = Query(None),
    category:  Optional[str]       = Query(None),
    date_from: Optional[date]      = Query(None),
    date_to:   Optional[date]      = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.analyst)),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from cannot be after date_to")
    
    entries = EntryService(db, current_user.id).get_all(type, category, date_from, date_to)
    
    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "User", "Date", "Type", "Category", "Amount", "Notes", "Created At"])
        yield output.getvalue()
        
        for entry in entries:
            output.seek(0)
            output.truncate(0)
            writer.writerow([
                entry.id,
                entry.user_id, # Can also be username if available, but entry output has user_id
                entry.date,
                entry.type.value,
                entry.category,
                entry.amount,
                entry.notes or "",
                entry.created_at
            ])
            yield output.getvalue()
            
    headers = {
        "Content-Disposition": "attachment; filename=export.csv"
    }
    return StreamingResponse(generate(), media_type="text/csv", headers=headers)


@app.get("/entries/{entry_id}", response_model=EntryOut, tags=["Entries"])
def get_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.viewer)),
):
    entry = EntryService(db, current_user.id).get_one(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@app.patch("/entries/{entry_id}", response_model=EntryOut, tags=["Entries"])
def update_entry(
    entry_id: int,
    body: EntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.admin)),
):
    svc   = EntryService(db, current_user.id)
    entry = svc.get_one(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return svc.update(entry, body)


@app.delete("/entries/{entry_id}", status_code=204, tags=["Entries"])
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.admin)),
):
    svc   = EntryService(db, current_user.id)
    entry = svc.get_one(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    svc.delete(entry)


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_model=Summary, tags=["Dashboard"])
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.viewer)),
):
    return EntryService(db, current_user.id).summary()


@app.post("/dashboard/ask", response_model=AIResponse, tags=["Dashboard"])
async def ask_ai(
    body: AIQuestion = AIQuestion(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.analyst)),
):
    svc     = EntryService(db, current_user.id)
    context = svc.ai_context()
    if not context.strip():
        raise HTTPException(status_code=400, detail="No financial data yet. Add some entries first.")
    try:
        answer = await ask_ollama(context, body.question)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return AIResponse(answer=answer, model=config.OLLAMA_MODEL)


# ── Live Log (SSE) ─────────────────────────────────────────────────────────────

# In-memory log broadcast: list of asyncio.Queue (one per connected client)
_log_clients: List[asyncio.Queue] = []
_log_history: List[dict] = []          # last 100 log messages
MAX_HISTORY = 100


def _broadcast_log(level: str, message: str, extra: dict = None):
    """Push a log entry to all connected SSE clients."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        **(extra or {}),
    }
    _log_history.append(entry)
    if len(_log_history) > MAX_HISTORY:
        _log_history.pop(0)
    for q in _log_clients:
        q.put_nowait(entry)


async def _event_generator(queue: asyncio.Queue):
    """Yield SSE events from client queue."""
    # Send history first
    for entry in _log_history[-20:]:
        yield f"data: {json.dumps(entry)}\n\n"
    # Then stream new events
    try:
        while True:
            entry = await asyncio.wait_for(queue.get(), timeout=30)
            yield f"data: {json.dumps(entry)}\n\n"
    except asyncio.TimeoutError:
        yield f"data: {json.dumps({'level': 'ping', 'message': 'keepalive'})}\n\n"
    except asyncio.CancelledError:
        pass


@app.get("/logs/stream", tags=["Logs"])
async def log_stream(token: str = Query(...), db: Session = Depends(get_db)):
    """SSE endpoint — analyst + admin can watch live upload logs. Pass token as query param."""
    from auth import decode_token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or user.role == Role.viewer:
        raise HTTPException(status_code=403, detail="Requires analyst or admin role")

    queue: asyncio.Queue = asyncio.Queue()
    _log_clients.append(queue)

    async def generate():
        try:
            async for chunk in _event_generator(queue):
                yield chunk
        finally:
            _log_clients.remove(queue)

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/logs/recent", tags=["Logs"])
def recent_logs(current_user: User = Depends(require(Role.analyst))):
    """Return the last 50 log entries (for initial load)."""
    return _log_history[-50:]


# ── CSV Upload ─────────────────────────────────────────────────────────────────

@app.post("/upload-csv", tags=["Upload"])
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require(Role.admin)),
):
    """
    Upload a CSV file to bulk-create entries.
    Broadcasts live progress logs to connected SSE clients.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    _broadcast_log("info", f"📄 Upload started: {file.filename}", {"filename": file.filename})

    # Build username→id lookup
    users = {u.username: u.id for u in db.query(User).all()}

    created = 0
    skipped = 0
    errors = 0
    total_rows = text.strip().count("\n")  # approximate

    for i, row in enumerate(reader, start=1):
        username = row.get("username", "").strip()
        user_id = users.get(username)
        if not user_id:
            _broadcast_log("warn", f"Row {i}: unknown user '{username}' — skipped")
            skipped += 1
            continue

        try:
            amount = round(float(row["amount"]), 2)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            entry_type = row["type"].strip()
            if entry_type not in ("income", "expense"):
                raise ValueError(f"Invalid type: {entry_type}")
            entry_date = datetime.strptime(row["date"].strip(), "%Y-%m-%d").date()
            category = row["category"].strip()
            if not category:
                raise ValueError("Empty category")

            entry = Entry(
                user_id=user_id,
                amount=amount,
                type=EntryType(entry_type),
                category=category,
                date=entry_date,
                notes=row.get("notes", "").strip() or None,
            )
            db.add(entry)
            db.commit()
            created += 1

            _broadcast_log("success", f"Row {i}: ✅ {entry_type} ${amount:.2f} → {category} ({username})", {
                "row": i, "username": username, "amount": amount,
                "type": entry_type, "category": category,
            })

        except Exception as e:
            errors += 1
            _broadcast_log("error", f"Row {i}: ❌ {str(e)}")
            continue

    summary_msg = f"📊 Upload complete — {created} created, {skipped} skipped, {errors} errors"
    _broadcast_log("info", summary_msg, {"created": created, "skipped": skipped, "errors": errors})

    return {"created": created, "skipped": skipped, "errors": errors, "filename": file.filename}
