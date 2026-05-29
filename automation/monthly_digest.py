#!/usr/bin/env python3
"""
PerkGuard Monthly Digest — Python Version

Alternative to the Google Apps Script path. Useful for:
- PythonAnywhere scheduled tasks
- Local testing / cron
- When you want richer formatting or different email providers

This script reuses the same battle-tested utils as the Streamlit dashboard
(sheets_client + date_utils), so behavior stays consistent.

Usage:
    # Just see what the digest would say (recommended first)
    python automation/monthly_digest.py --dry-run

    # With a specific sheet
    python automation/monthly_digest.py --sheet-id YOUR_ID --dry-run

Future: add real email sending via smtplib (Gmail app password) or Resend/etc.
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Allow running directly from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.sheets_client import get_perks, get_value_logs, get_settings, get_trips
from app.utils.date_utils import (
    is_perk_available_in_current_period,
    get_days_until_reset,
    get_expiring_soon_perks,
    format_period_label,
    get_current_period_key,
)

# --------------------------------------------------------------------------- #
# Core Generation
# --------------------------------------------------------------------------- #

def build_digest(today: date | None = None) -> dict[str, Any]:
    """Return a structured digest dict (subject + sections)."""
    if today is None:
        today = date.today()

    perks = get_perks()
    value_logs = get_value_logs()
    settings = get_settings()
    trips = get_trips()

    available = []
    expiring = []
    used_this_period = []

    for perk in perks:
        if not perk.get("is_active", True):
            continue

        period_key = get_current_period_key(perk, today, settings)
        available_now = is_perk_available_in_current_period(perk, value_logs, today, settings)
        days_left = get_days_until_reset(perk, today, settings)

        enriched = {**perk, "period_key": period_key, "days_left": days_left}

        if not available_now:
            used_this_period.append(enriched)
        else:
            available.append(enriched)
            if 0 < days_left <= 30:
                expiring.append(enriched)

    # Very lightweight suggestions (same spirit as the Apps Script version)
    suggestions = generate_simple_suggestions(available, trips, today)

    subject = f"PerkGuard Digest — {today.strftime('%B %Y')}"

    return {
        "subject": subject,
        "today": today,
        "available": available,
        "expiring": sorted(expiring, key=lambda x: x["days_left"]),
        "used_this_period": used_this_period,
        "suggestions": suggestions,
        "settings": settings,
    }


def generate_simple_suggestions(available: list[dict], trips: list[dict], today: date) -> list[str]:
    suggestions: list[str] = []

    # Companion certificate + domestic trip
    has_companion = any("companion" in (p.get("perk_id") or "") for p in available)
    has_domestic_trip = any("domestic" in (t.get("destination_type") or "").lower() for t in trips)
    if has_companion and has_domestic_trip:
        suggestions.append("Your Delta Companion Certificate is available and you have an upcoming domestic trip — strong candidate for use.")

    # Hotel credit + international trip
    has_hotel = any("hotel" in (p.get("name") or "").lower() for p in available)
    has_intl = any("international" in (t.get("destination_type") or "").lower() for t in trips)
    if has_hotel and has_intl:
        suggestions.append("International trip on the horizon + hotel credits available — consider Fine Hotels + Resorts or The Hotel Collection.")

    # Chase activation (very common pain point)
    has_chase_activation = any("5%" in (p.get("name") or "") and "Activate" in (p.get("name") or "") for p in available)
    if has_chase_activation:
        suggestions.append("Don't forget to activate your Chase Freedom Flex 5% categories before the quarterly deadline.")

    return suggestions or ["No strong trip-based suggestions this month. Review the full available list above."]


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def render_text(digest: dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append(digest["subject"])
    lines.append(f"Generated: {digest['today'].isoformat()}")
    lines.append("=" * 60)
    lines.append("")

    lines.append(f"AVAILABLE NOW ({len(digest['available'])})")
    lines.append("-" * 40)
    for p in digest["available"][:15]:
        val = f" (up to ${p.get('max_value')})" if p.get("max_value") else ""
        lines.append(f"• {p.get('name')}{val} — {p['card']}")
    if len(digest["available"]) > 15:
        lines.append(f"  ... +{len(digest['available']) - 15} more")
    lines.append("")

    if digest["expiring"]:
        lines.append("EXPIRING SOON (≤30 days)")
        lines.append("-" * 40)
        for p in digest["expiring"]:
            lines.append(f"• {p.get('name')} — {p['days_left']} days left")
        lines.append("")

    if digest["used_this_period"]:
        lines.append("USED THIS PERIOD")
        lines.append("-" * 40)
        for p in digest["used_this_period"][:8]:
            lines.append(f"• {p.get('name')}")
        lines.append("")

    lines.append("SUGGESTIONS")
    lines.append("-" * 40)
    for s in digest["suggestions"]:
        lines.append(f"• {s}")
    lines.append("")

    lines.append("=" * 60)
    lines.append("Open your PerkGuard Sheet or run: streamlit run app/main.py")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_html(digest: dict[str, Any]) -> str:
    # For V1 we keep the HTML generation light — the Apps Script version has richer styling.
    # This is good enough for testing or forwarding.
    parts = [f"<h1>{digest['subject']}</h1>"]
    parts.append(f"<p>Generated: {digest['today'].isoformat()}</p>")

    parts.append(f"<h2>Available Now ({len(digest['available'])})</h2><ul>")
    for p in digest["available"][:12]:
        parts.append(f"<li>{p.get('name')} ({p['card']})</li>")
    parts.append("</ul>")

    if digest["expiring"]:
        parts.append("<h2>Expiring Soon</h2><ul>")
        for p in digest["expiring"]:
            parts.append(f"<li>{p.get('name')} — {p['days_left']} days</li>")
        parts.append("</ul>")

    if digest["suggestions"]:
        parts.append("<h2>Suggestions</h2><ul>")
        for s in digest["suggestions"]:
            parts.append(f"<li>{s}</li>")
        parts.append("</ul>")

    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Main / CLI
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PerkGuard monthly digest (Python path).")
    parser.add_argument("--sheet-id", help="Explicit Google Sheet ID (overrides secrets/env)")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Print the digest instead of sending email (default & recommended)")
    parser.add_argument("--format", choices=["text", "html"], default="text")
    args = parser.parse_args()

    if args.sheet_id:
        os.environ["PERKGUARD_SHEET_ID"] = args.sheet_id

    digest = build_digest()

    if args.format == "html":
        output = render_html(digest)
    else:
        output = render_text(digest)

    print(output)

    if not args.dry_run:
        print("\n[INFO] Real email sending is not yet implemented in this script.")
        print("       Use the Google Apps Script version for production cloud delivery,")
        print("       or extend this script with smtplib / your preferred provider.")


if __name__ == "__main__":
    main()
