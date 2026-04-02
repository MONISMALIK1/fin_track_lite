# test_app.py — tests for every major feature
# Run: pytest test_app.py -v

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Use an in-memory DB for tests — never touches fintrack.db
import config
config.DATABASE_URL = "sqlite:///:memory:"

from database import Base, get_db
from main import app
from models import User, Role
from auth import hash_password, create_token

engine     = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    from models import User, Entry  # ensure models registered
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    s = TestSession()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_user(db, username="alice", role=Role.admin):
    user = User(username=username, hashed_password=hash_password("pass123"), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def _auth(user):
    token = create_token(user.id, user.username, user.role.value)
    return {"Authorization": f"Bearer {token}"}

ENTRY = {"amount": 500, "type": "income", "category": "Salary", "date": str(date.today())}


# ── Auth tests ─────────────────────────────────────────────────────────────────

def test_login_success(client, db):
    _make_user(db, "bob", Role.admin)
    r = client.post("/login", json={"username": "bob", "password": "pass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()

def test_login_wrong_password(client, db):
    _make_user(db)
    r = client.post("/login", json={"username": "alice", "password": "wrong"})
    assert r.status_code == 401

def test_no_token_rejected(client):
    r = client.get("/entries")
    assert r.status_code == 401


# ── Role tests ─────────────────────────────────────────────────────────────────

def test_viewer_cannot_create_entry(client, db):
    viewer = _make_user(db, "v", Role.viewer)
    r = client.post("/entries", json=ENTRY, headers=_auth(viewer))
    assert r.status_code == 403

def test_analyst_cannot_create_entry(client, db):
    analyst = _make_user(db, "a", Role.analyst)
    r = client.post("/entries", json=ENTRY, headers=_auth(analyst))
    assert r.status_code == 403

def test_viewer_can_read_entries(client, db):
    viewer = _make_user(db, "v", Role.viewer)
    r = client.get("/entries", headers=_auth(viewer))
    assert r.status_code == 200

def test_viewer_cannot_access_ai(client, db):
    viewer = _make_user(db, "v", Role.viewer)
    r = client.post("/dashboard/ask", json={}, headers=_auth(viewer))
    assert r.status_code == 403


# ── Entry CRUD tests ───────────────────────────────────────────────────────────

def test_create_and_get_entry(client, db):
    admin = _make_user(db)
    r = client.post("/entries", json=ENTRY, headers=_auth(admin))
    assert r.status_code == 201
    entry_id = r.json()["id"]

    r2 = client.get(f"/entries/{entry_id}", headers=_auth(admin))
    assert r2.status_code == 200
    assert r2.json()["category"] == "Salary"

def test_update_entry(client, db):
    admin = _make_user(db)
    r = client.post("/entries", json=ENTRY, headers=_auth(admin))
    entry_id = r.json()["id"]

    r2 = client.patch(f"/entries/{entry_id}", json={"amount": 999}, headers=_auth(admin))
    assert r2.status_code == 200
    assert r2.json()["amount"] == 999.0

def test_delete_entry(client, db):
    admin = _make_user(db)
    r = client.post("/entries", json=ENTRY, headers=_auth(admin))
    entry_id = r.json()["id"]

    client.delete(f"/entries/{entry_id}", headers=_auth(admin))
    r2 = client.get(f"/entries/{entry_id}", headers=_auth(admin))
    assert r2.status_code == 404

def test_get_nonexistent_entry(client, db):
    admin = _make_user(db)
    r = client.get("/entries/9999", headers=_auth(admin))
    assert r.status_code == 404


# ── Validation tests ───────────────────────────────────────────────────────────

def test_negative_amount_rejected(client, db):
    admin = _make_user(db)
    r = client.post("/entries", json={**ENTRY, "amount": -100}, headers=_auth(admin))
    assert r.status_code == 422

def test_zero_amount_rejected(client, db):
    admin = _make_user(db)
    r = client.post("/entries", json={**ENTRY, "amount": 0}, headers=_auth(admin))
    assert r.status_code == 422

def test_future_date_rejected(client, db):
    admin = _make_user(db)
    r = client.post("/entries", json={**ENTRY, "date": "2099-01-01"}, headers=_auth(admin))
    assert r.status_code == 422

def test_blank_category_rejected(client, db):
    admin = _make_user(db)
    r = client.post("/entries", json={**ENTRY, "category": "  "}, headers=_auth(admin))
    assert r.status_code == 422

def test_invalid_entry_type_rejected(client, db):
    admin = _make_user(db)
    r = client.post("/entries", json={**ENTRY, "type": "savings"}, headers=_auth(admin))
    assert r.status_code == 422

def test_invalid_date_range(client, db):
    admin = _make_user(db)
    r = client.get("/entries?date_from=2024-06-01&date_to=2024-01-01", headers=_auth(admin))
    assert r.status_code == 422


# ── Filter tests ───────────────────────────────────────────────────────────────

def test_filter_by_type(client, db):
    admin = _make_user(db)
    h = _auth(admin)
    client.post("/entries", json=ENTRY, headers=h)
    client.post("/entries", json={**ENTRY, "type": "expense", "category": "Rent"}, headers=h)

    r = client.get("/entries?type=expense", headers=h)
    assert all(e["type"] == "expense" for e in r.json())

def test_filter_by_category(client, db):
    admin = _make_user(db)
    h = _auth(admin)
    client.post("/entries", json=ENTRY, headers=h)
    client.post("/entries", json={**ENTRY, "category": "Rent", "type": "expense"}, headers=h)

    r = client.get("/entries?category=salary", headers=h)
    assert all("salary" in e["category"].lower() for e in r.json())


# ── Dashboard / summary tests ──────────────────────────────────────────────────

def test_dashboard_summary_structure(client, db):
    admin = _make_user(db)
    h = _auth(admin)
    client.post("/entries", json=ENTRY, headers=h)
    client.post("/entries", json={**ENTRY, "type": "expense", "amount": 200, "category": "Rent"}, headers=h)

    r = client.get("/dashboard", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "total_income"       in data
    assert "total_expenses"     in data
    assert "balance"            in data
    assert "category_breakdown" in data
    assert "monthly_totals"     in data
    assert "recent_entries"     in data

def test_balance_is_correct(client, db):
    admin = _make_user(db)
    h = _auth(admin)
    client.post("/entries", json={**ENTRY, "amount": 1000}, headers=h)
    client.post("/entries", json={**ENTRY, "type": "expense", "amount": 300, "category": "Rent"}, headers=h)

    data = client.get("/dashboard", headers=h).json()
    assert data["balance"] == round(data["total_income"] - data["total_expenses"], 2)


# ── User management tests ──────────────────────────────────────────────────────

def test_admin_can_create_user(client, db):
    admin = _make_user(db)
    r = client.post("/users", json={"username": "newuser", "password": "pass123", "role": "viewer"}, headers=_auth(admin))
    assert r.status_code == 201

def test_duplicate_username_rejected(client, db):
    admin = _make_user(db)
    payload = {"username": "dup", "password": "pass123", "role": "viewer"}
    client.post("/users", json=payload, headers=_auth(admin))
    r = client.post("/users", json=payload, headers=_auth(admin))
    assert r.status_code == 409

def test_short_password_rejected(client, db):
    admin = _make_user(db)
    r = client.post("/users", json={"username": "x", "password": "ab", "role": "viewer"}, headers=_auth(admin))
    assert r.status_code == 422
