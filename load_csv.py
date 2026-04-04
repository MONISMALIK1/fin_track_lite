# load_csv.py — Import sample_data.csv into the database
# Each row is linked to the user specified in the 'username' column.
# Run:  python load_csv.py

import csv
from datetime import datetime

from database import create_tables, Session
from models import User, Entry, EntryType

CSV_FILE = "sample_data.csv"


def main():
    create_tables()
    db = Session()

    # Build a lookup of username → user_id
    users = {u.username: u.id for u in db.query(User).all()}
    if not users:
        print("No users found. Run  python seed.py  first.")
        return

    # Remove old entries so we can re-run cleanly
    deleted = db.query(Entry).delete()
    db.commit()
    if deleted:
        print(f"  Cleared {deleted} existing entries.")

    count = 0
    with open(CSV_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = row["username"].strip()
            if username not in users:
                print(f"  ⚠ Skipping row — unknown user '{username}'")
                continue

            entry = Entry(
                user_id=users[username],
                amount=round(float(row["amount"]), 2),
                type=EntryType(row["type"].strip()),
                category=row["category"].strip(),
                date=datetime.strptime(row["date"].strip(), "%Y-%m-%d").date(),
                notes=row["notes"].strip() if row.get("notes") else None,
            )
            db.add(entry)
            count += 1

    db.commit()
    db.close()
    print(f"\n✅ Loaded {count} entries from {CSV_FILE}")

    # Show per-user summary
    db = Session()
    for username, uid in sorted(users.items()):
        n = db.query(Entry).filter(Entry.user_id == uid).count()
        print(f"   {username:10s} → {n} entries")
    db.close()


if __name__ == "__main__":
    main()
