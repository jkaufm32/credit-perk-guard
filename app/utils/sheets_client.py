"""
PerkGuard Sheets Client

Central, reusable wrapper around gspread for the Streamlit dashboard and
Python automation scripts.

Authentication priority:
1. Streamlit secrets (st.secrets["gcp_service_account"]) — works locally and on Streamlit Cloud
2. Local service-account-key.json in repo root (gitignored)

All functions use type hints and are documented per AGENTS.md guidelines.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #

def get_credentials() -> Credentials:
    """Return Google service account credentials.

    Raises:
        RuntimeError: If no valid credentials can be found.
    """
    # Preferred path: Streamlit secrets (works in app + when script run via streamlit)
    try:
        if "gcp_service_account" in st.secrets:
            return Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=SCOPES
            )
    except Exception:
        pass

    # Fallback for local development / seed script
    key_path = Path("service-account-key.json")
    if key_path.exists():
        return Credentials.from_service_account_file(str(key_path), scopes=SCOPES)

    raise RuntimeError(
        "Google credentials not found. "
        "Add [gcp_service_account] to .streamlit/secrets.toml "
        "or place service-account-key.json in the project root."
    )


@st.cache_resource(show_spinner="Connecting to Google Sheets...")
def get_client() -> gspread.Client:
    """Return a cached authorized gspread client (resource-cached for Streamlit)."""
    creds = get_credentials()
    return gspread.authorize(creds)


# --------------------------------------------------------------------------- #
# Spreadsheet / Worksheet Access
# --------------------------------------------------------------------------- #

def get_spreadsheet(sheet_id: Optional[str] = None) -> gspread.Spreadsheet:
    """Open the PerkGuard spreadsheet.

    Args:
        sheet_id: Optional explicit ID. If not provided, reads from
                  st.secrets["perkguard"]["sheet_id"] or PERKGUARD_SHEET_ID env var.
    """
    if sheet_id is None:
        try:
            sheet_id = st.secrets["perkguard"]["sheet_id"]
        except Exception:
            sheet_id = os.getenv("PERKGUARD_SHEET_ID")

    if not sheet_id:
        raise RuntimeError(
            "No spreadsheet ID configured. "
            "Set st.secrets['perkguard']['sheet_id'] or PERKGUARD_SHEET_ID."
        )

    client = get_client()
    return client.open_by_key(sheet_id)


def get_worksheet(name: str, sheet_id: Optional[str] = None) -> gspread.Worksheet:
    """Return a worksheet by name, creating it if it does not exist (with generous defaults)."""
    spreadsheet = get_spreadsheet(sheet_id)
    try:
        return spreadsheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        # Create with reasonable dimensions for our use case
        return spreadsheet.add_worksheet(title=name, rows=500, cols=20)


# --------------------------------------------------------------------------- #
# Read Helpers (cached where safe)
# --------------------------------------------------------------------------- #

@st.cache_data(ttl=60, show_spinner=False)
def get_all_records(worksheet_name: str, sheet_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Return all rows from a worksheet as a list of dictionaries.

    Results are cached for 60 seconds in the Streamlit session.
    """
    ws = get_worksheet(worksheet_name, sheet_id)
    records = ws.get_all_records()
    return records


def get_perks(sheet_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Convenience wrapper for the Perks sheet."""
    return get_all_records("Perks", sheet_id)


def get_trips(sheet_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Convenience wrapper for the Trips sheet."""
    return get_all_records("Trips", sheet_id)


def get_value_logs(sheet_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Convenience wrapper for the ValueLogs sheet (history)."""
    return get_all_records("ValueLogs", sheet_id)


def get_settings(sheet_id: Optional[str] = None) -> dict[str, Any]:
    """Return the Settings row as a single dictionary (first row after header)."""
    records = get_all_records("Settings", sheet_id)
    if not records:
        return {}
    return records[0]


# --------------------------------------------------------------------------- #
# Write Helpers
# --------------------------------------------------------------------------- #

def append_value_log(
    log_row: dict[str, Any],
    sheet_id: Optional[str] = None,
) -> None:
    """Append a single usage/value log row to the ValueLogs sheet.

    The caller is responsible for providing a complete row including
    log_id, timestamp, period_key, etc.
    """
    ws = get_worksheet("ValueLogs", sheet_id)
    headers = ws.row_values(1)
    row_values = [log_row.get(h, "") for h in headers]
    ws.append_row(row_values, value_input_option="USER_ENTERED")

    # Invalidate any cached reads of ValueLogs
    get_all_records.clear()


def update_perk_notes(
    perk_id: str,
    new_notes: str,
    sheet_id: Optional[str] = None,
) -> bool:
    """Update the notes field for a specific perk (simple cell update by perk_id)."""
    ws = get_worksheet("Perks", sheet_id)
    records = ws.get_all_records()

    for idx, record in enumerate(records, start=2):  # +2 because header row + 1-indexed
        if record.get("perk_id") == perk_id:
            # Find the notes column index (1-indexed for gspread)
            headers = ws.row_values(1)
            notes_col = headers.index("notes") + 1
            ws.update_cell(idx, notes_col, new_notes)

            # Also bump updated_at
            updated_col = headers.index("updated_at") + 1
            ws.update_cell(idx, updated_col, datetime.utcnow().isoformat(timespec="seconds") + "Z")

            # Bust cache
            get_all_records.clear()
            return True

    return False


# --------------------------------------------------------------------------- #
# Convenience / Diagnostics
# --------------------------------------------------------------------------- #

def get_connection_status(sheet_id: Optional[str] = None) -> dict[str, Any]:
    """Lightweight health check used by the Settings page."""
    try:
        ss = get_spreadsheet(sheet_id)
        ws_names = [ws.title for ws in ss.worksheets()]
        return {
            "ok": True,
            "title": ss.title,
            "worksheets": ws_names,
            "url": ss.url,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
