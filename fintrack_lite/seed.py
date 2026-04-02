# seed.py — run once to create users and sample data
# Usage: python seed.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
import random

from database import Session, create_tables
from models import User, Entry, Role, EntryType
from auth import hash_password

create_tables()
db = Session()

# ── Users ──────────────────────────────────────────────────────────────────────
users_data = [
    {"username": "admin",   "password": "admin123",   "role": Role.admin},
    {"username": "analyst", "password": "analyst123", "role": Role.analyst},
    {"username": "viewer",  "password": "viewer123",  "role": Role.viewer},
]

created = {}
for u in users_data:
    existing = db.query(User).filter(User.username == u["username"]).first()
    if not existing:
        user = User(username=u["username"], hashed_password=hash_password(u["password"]), role=u["role"])
        db.add(user)
        db.commit()
        db.refresh(user)
        created[u["username"]] = user
        print(f"  Created {u['role'].value}: {u['username']}")
    else:
        created[u["username"]] = existing
        print(f"  Already exists: {u['username']}")

# ── Sample entries for admin ───────────────────────────────────────────────────
admin = created["admin"]
if db.query(Entry).filter(Entry.user_id == admin.id).count() == 0:
    samples = [
        (3000, EntryType.income,  "Salary",        0),
        (500,  EntryType.income,  "Freelance",     5),
        (800,  EntryType.expense, "Rent",          2),
        (150,  EntryType.expense, "Groceries",     1),
        (80,   EntryType.expense, "Utilities",     3),
        (200,  EntryType.income,  "Freelance",    35),
        (60,   EntryType.expense, "Transport",     4),
        (120,  EntryType.expense, "Entertainment", 6),
        (3000, EntryType.income,  "Salary",       30),
        (900,  EntryType.expense, "Rent",         32),
    ]
    for amount, etype, category, days_ago in samples:
        db.add(Entry(
            user_id=admin.id,
            amount=amount,
            type=etype,
            category=category,
            date=date.today() - timedelta(days=days_ago),
            notes=f"Sample {category.lower()} entry",
        ))
    db.commit()
    print(f"  Added {len(samples)} sample entries for admin")

db.close()
print("\nDone! Credentials:")
print("  admin   / admin123   (full access)")
print("  analyst / analyst123 (view + AI insights)")
print("  viewer  / viewer123  (read only)")
