#!/usr/bin/env python3
"""
PerkGuard Sheet Seeder

One-time (or occasional) script that:
1. Connects to your Google Sheet using a service account.
2. Creates the exact 5 worksheets PerkGuard expects (if missing).
3. Wipes and re-populates the Perks, Settings, and Trips tabs with realistic 2026 sample data.
4. Leaves ValueLogs and Enrollments empty (or with a couple of demo rows).

Usage (after you have created a blank Google Sheet and shared it with your service account email):

    python scripts/seed_sheets.py --sheet-url "https://docs.google.com/spreadsheets/d/1abc123/edit"

Or set the environment variable:
    export PERKGUARD_SHEET_ID="1abc123..."
    python scripts/seed_sheets.py

The script is idempotent in structure (it won't duplicate worksheets) but will
replace data in Perks / Settings / Trips when run with --reset (default).

Prerequisites:
- pip install -r requirements.txt
- Valid service account credentials (see README for setup)
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

# Make it possible to run this script directly from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.seed_perks import SEED_PERKS, SEED_SETTINGS, SEED_TRIPS  # type: ignore

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

WORKSHEETS = ["Perks", "Trips", "ValueLogs", "Enrollments", "Settings"]

HEADERS = {
    "Perks": [
        "perk_id", "card", "name", "category", "reset_type", "reset_anchor",
        "max_value", "value_unit", "enrollment_required", "notes",
        "is_active", "created_at", "updated_at",
    ],
    "Trips": [
        "trip_id", "name", "start_date", "end_date", "destination_type",
        "notes", "created_at",
    ],
    "ValueLogs": [
        "log_id", "timestamp", "perk_id", "period_key", "used_date",
        "value_captured", "trip_id", "notes", "source",
    ],
    "Enrollments": [
        "perk_id", "status", "enrolled_date", "details", "notes",
    ],
    "Settings": [
        "user_email", "digest_day", "urgent_alert_days",
        "amex_anniversary_month", "delta_anniversary_month",
        "chase_anniversary_month", "default_currency",
        "suggestion_lookahead_days",
    ],
}

# --------------------------------------------------------------------------- #
# Auth & Client
# --------------------------------------------------------------------------- #

def get_credentials() -> Credentials:
    """Load service account credentials from Streamlit secrets or local file."""
    # 1. Try Streamlit secrets (works when running inside the app too)
    try:
        import streamlit as st  # type: ignore
        if "gcp_service_account" in st.secrets:
            return Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=SCOPES
            )
    except Exception:
        pass

    # 2. Fallback to local file (common during initial setup)
    key_path = Path("service-account-key.json")
    if key_path.exists():
        return Credentials.from_service_account_file(str(key_path), scopes=SCOPES)

    raise RuntimeError(
        "No Google service account credentials found.\n"
        "Either place service-account-key.json in the repo root\n"
        "or configure [gcp_service_account] in .streamlit/secrets.toml"
    )


def get_sheet_client(spreadsheet_id: str) -> gspread.Spreadsheet:
    """Return an authorized gspread Spreadsheet object."""
    creds = get_credentials()
    gc = gspread.authorize(creds)
    return gc.open_by_key(spreadsheet_id)


# --------------------------------------------------------------------------- #
# Worksheet Helpers
# --------------------------------------------------------------------------- #

def ensure_worksheet(spreadsheet: gspread.Spreadsheet, title: str, rows: int = 100, cols: int = 15) -> gspread.Worksheet:
    """Create the worksheet if it does not exist; otherwise return existing."""
    try:
        ws = spreadsheet.worksheet(title)
        return ws
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
        return ws


def clear_and_write_headers(ws: gspread.Worksheet, headers: list[str]) -> None:
    """Clear the sheet and write the canonical header row."""
    ws.clear()
    ws.append_row(headers)
    # Freeze the header row
    ws.freeze(rows=1)


def batch_append(ws: gspread.Worksheet, rows: list[dict[str, Any]], headers: list[str]) -> None:
    """Append many rows efficiently."""
    values = []
    for row in rows:
        values.append([row.get(h, "") for h in headers])
    if values:
        ws.append_rows(values, value_input_option="USER_ENTERED")


# --------------------------------------------------------------------------- #
# Seeding Logic
# --------------------------------------------------------------------------- #

def seed_perks(ws: gspread.Worksheet) -> int:
    """Seed the Perks worksheet from data/seed_perks.py."""
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    rows = []
    for p in SEED_PERKS:
        row = p.copy()
        row["created_at"] = now
        row["updated_at"] = now
        # Convert booleans to strings that Sheets will interpret nicely
        row["enrollment_required"] = "TRUE" if row.get("enrollment_required") else "FALSE"
        row["is_active"] = "TRUE" if row.get("is_active") else "FALSE"
        rows.append(row)
    batch_append(ws, rows, HEADERS["Perks"])
    return len(rows)


def seed_settings(ws: gspread.Worksheet) -> None:
    """Write the Settings row (single row of config)."""
    ws.append_row([SEED_SETTINGS.get(h, "") for h in HEADERS["Settings"]])


def seed_trips(ws: gspread.Worksheet) -> int:
    """Seed a couple of example upcoming trips."""
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    rows = []
    for t in SEED_TRIPS:
        row = t.copy()
        row["created_at"] = now
        rows.append(row)
    batch_append(ws, rows, HEADERS["Trips"])
    return len(rows)


def seed_value_logs_placeholder(ws: gspread.Worksheet) -> None:
    """Leave mostly empty; optionally add 1-2 demo rows in the future."""
    # Intentionally left minimal for a clean starting state
    pass


def seed_enrollments_placeholder(ws: gspread.Worksheet) -> None:
    """Scaffold only — real data added later via UI or manually."""
    # Add a couple of example enrollment rows so the sheet is not completely empty
    example = [
        ["amex_plat_airline_2026", "enrolled", "2026-01-15", "Selected airline: American", ""],
        ["amex_plat_resy_2026_q2", "enrolled", "2026-04-01", "", ""],
    ]
    ws.append_rows(example)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed PerkGuard Google Sheet with realistic sample data.")
    parser.add_argument("--sheet-url", help="Full Google Sheets URL (or just the ID)")
    parser.add_argument("--sheet-id", help="Spreadsheet ID only")
    parser.add_argument("--reset", action="store_true", default=True,
                        help="Replace data in Perks/Settings/Trips (default: True)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without writing")
    args = parser.parse_args()

    # Resolve spreadsheet ID
    sheet_id = args.sheet_id
    if args.sheet_url:
        # Extract ID from URL if present
        if "/d/" in args.sheet_url:
            sheet_id = args.sheet_url.split("/d/")[1].split("/")[0]
        else:
            sheet_id = args.sheet_url

    if not sheet_id:
        sheet_id = os.getenv("PERKGUARD_SHEET_ID")

    if not sheet_id:
        print("ERROR: Provide --sheet-url, --sheet-id, or set PERKGUARD_SHEET_ID env var.")
        sys.exit(1)

    print(f"Connecting to spreadsheet: {sheet_id}")

    if args.dry_run:
        print("DRY RUN — no changes will be made.")
        print(f"Would seed {len(SEED_PERKS)} perks, {len(SEED_TRIPS)} trips, and Settings.")
        return

    spreadsheet = get_sheet_client(sheet_id)

    # Ensure all required worksheets exist
    for title in WORKSHEETS:
        ws = ensure_worksheet(spreadsheet, title)
        print(f"✓ Ensured worksheet exists: {title}")

    # Seed Perks
    perks_ws = spreadsheet.worksheet("Perks")
    clear_and_write_headers(perks_ws, HEADERS["Perks"])
    count = seed_perks(perks_ws)
    print(f"✓ Seeded {count} perks into Perks sheet")

    # Seed Settings (single row)
    settings_ws = spreadsheet.worksheet("Settings")
    clear_and_write_headers(settings_ws, HEADERS["Settings"])
    seed_settings(settings_ws)
    print("✓ Seeded Settings (update anniversary months and email!)")

    # Seed Trips
    trips_ws = spreadsheet.worksheet("Trips")
    clear_and_write_headers(trips_ws, HEADERS["Trips"])
    tcount = seed_trips(trips_ws)
    print(f"✓ Seeded {tcount} example trips")

    # ValueLogs and Enrollments get headers + light scaffolding
    value_ws = spreadsheet.worksheet("ValueLogs")
    clear_and_write_headers(value_ws, HEADERS["ValueLogs"])
    seed_value_logs_placeholder(value_ws)
    print("✓ ValueLogs sheet ready (empty — logs will be appended by the app)")

    enroll_ws = spreadsheet.worksheet("Enrollments")
    clear_and_write_headers(enroll_ws, HEADERS["Enrollments"])
    seed_enrollments_placeholder(enroll_ws)
    print("✓ Enrollments sheet ready with a couple of example rows")

    print("\n✅ Seeding complete!")
    print("Next steps:")
    print("  1. Open the spreadsheet and update the Settings row (your real email + anniversary months).")
    print("  2. Share the sheet with the service account email if you haven't already.")
    print("  3. Run: streamlit run app/main.py")
    print("  4. Follow the Apps Script setup instructions in automation/apps_script/README.md")


if __name__ == "__main__":
    main()
