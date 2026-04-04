#!/usr/bin/env python3
"""
upload_api.py — Upload sample_data.csv to the FinTrack API.

This script:
  1. Logs in as admin
  2. Uploads sample_data.csv via the /upload-csv endpoint
  3. Prints live progress from the server

Run:  python upload_api.py
      python upload_api.py --file other_data.csv
"""

import argparse
import sys
import httpx
import os

API = "http://localhost:8000"
# Resolve sample_data.csv relative to this script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, "sample_data.csv")


def main():
    parser = argparse.ArgumentParser(description="Upload CSV data to FinTrack Lite")
    parser.add_argument("--file", default=CSV_FILE, help="Path to CSV file (default: sample_data.csv)")
    parser.add_argument("--user", default="admin", help="Username (default: admin)")
    parser.add_argument("--password", default="admin123", help="Password (default: admin123)")
    args = parser.parse_args()

    # ── Login ────────────────────────────────────────────────────────
    print(f"🔐  Logging in as '{args.user}'...")
    try:
        r = httpx.post(f"{API}/login", json={"username": args.user, "password": args.password})
        r.raise_for_status()
    except httpx.ConnectError:
        print("❌  Cannot connect to API. Is the server running?")
        print("    Start it with:  uvicorn main:app --reload")
        sys.exit(1)
    except httpx.HTTPStatusError:
        print(f"❌  Login failed: {r.json().get('detail', r.text)}")
        sys.exit(1)

    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅  Logged in successfully\n")

    # ── Upload CSV ───────────────────────────────────────────────────
    print(f"📤  Uploading '{args.file}' ...")
    try:
        with open(args.file, "rb") as f:
            r = httpx.post(
                f"{API}/upload-csv",
                files={"file": (args.file, f, "text/csv")},
                headers=headers,
                timeout=60.0
            )
    except FileNotFoundError:
        print(f"❌  File not found: {args.file}")
        sys.exit(1)

    if r.status_code != 200:
        print(f"❌  Upload failed ({r.status_code}): {r.json().get('detail', r.text)}")
        sys.exit(1)

    data = r.json()
    print()
    print("─" * 50)
    print(f"  ✅ Created:  {data['created']}")
    print(f"  ⏭  Skipped:  {data['skipped']}")
    print(f"  ❌ Errors:   {data['errors']}")
    print(f"  📄 File:     {data['filename']}")
    print("─" * 50)
    print("\n  Done! Check the dashboard for updated data.")
    print("  Analyst/Admin users can see live upload logs.")


if __name__ == "__main__":
    main()
