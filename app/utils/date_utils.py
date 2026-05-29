"""
PerkGuard Date & Reset Utilities

Pure functions for calculating availability, period keys, and expiry
across all supported reset types.

Supported reset_type values:
    calendar_year, quarterly, monthly, card_anniversary, semi_annual, one_time, custom

All functions are side-effect free and accept explicit `today` for easy testing.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from dateutil.relativedelta import relativedelta

# --------------------------------------------------------------------------- #
# Core Period Calculation
# --------------------------------------------------------------------------- #

def get_current_period_key(
    perk: dict[str, Any],
    today: Optional[date] = None,
    settings: Optional[dict[str, Any]] = None,
) -> str:
    """Return a stable string key representing the current benefit period for this perk.

    Examples:
        - "2026-Q2"
        - "2026-05"
        - "2026-05-anniv"
        - "2026-H1"
        - "2026-one_time"
    """
    if today is None:
        today = date.today()

    reset_type = perk.get("reset_type", "calendar_year")
    year = today.year

    if reset_type == "calendar_year":
        return f"{year}-calendar"

    if reset_type == "quarterly":
        q = (today.month - 1) // 3 + 1
        return f"{year}-Q{q}"

    if reset_type == "monthly":
        return f"{year}-{today.month:02d}"

    if reset_type == "card_anniversary":
        # Use the correct card's anniversary month from Settings
        card = perk.get("card", "")
        anniv_month = _get_anniversary_month(card, settings)
        # The "year" for anniversary periods is the year of the most recent anniversary
        if today.month < anniv_month:
            period_year = year - 1
        else:
            period_year = year
        return f"{period_year}-{anniv_month:02d}-anniv"

    if reset_type == "semi_annual":
        half = "H1" if today.month <= 6 else "H2"
        return f"{year}-{half}"

    if reset_type == "one_time":
        return f"{year}-one_time"  # or a fixed key; we mostly care about existence of any log

    # custom or unknown — fall back to year-month for safety
    return f"{year}-{today.month:02d}-custom"


def get_period_end_date(
    perk: dict[str, Any],
    today: Optional[date] = None,
    settings: Optional[dict[str, Any]] = None,
) -> date:
    """Return the last day the current period is active (inclusive)."""
    if today is None:
        today = date.today()

    reset_type = perk.get("reset_type", "calendar_year")
    year = today.year

    if reset_type == "calendar_year":
        return date(year, 12, 31)

    if reset_type == "quarterly":
        q = (today.month - 1) // 3 + 1
        end_month = q * 3
        # Last day of the quarter month
        if end_month == 12:
            return date(year, 12, 31)
        return date(year, end_month, 1) + relativedelta(months=1) - relativedelta(days=1)

    if reset_type == "monthly":
        # Last day of the current month
        if today.month == 12:
            return date(year, 12, 31)
        return date(year, today.month + 1, 1) - relativedelta(days=1)

    if reset_type == "card_anniversary":
        anniv_month = _get_anniversary_month(perk.get("card", ""), settings)
        # End of the anniversary month in the current period year
        period_year = year if today.month >= anniv_month else year - 1
        if anniv_month == 12:
            return date(period_year, 12, 31)
        return date(period_year, anniv_month + 1, 1) - relativedelta(days=1)

    if reset_type == "semi_annual":
        if today.month <= 6:
            return date(year, 6, 30)
        return date(year, 12, 31)

    if reset_type == "one_time":
        # Far future — effectively never expires for UI purposes
        return date(2099, 12, 31)

    # custom fallback
    return date(year, 12, 31)


# --------------------------------------------------------------------------- #
# Availability Logic (the heart of the dashboard)
# --------------------------------------------------------------------------- #

def is_perk_available_in_current_period(
    perk: dict[str, Any],
    value_logs: list[dict[str, Any]],
    today: Optional[date] = None,
    settings: Optional[dict[str, Any]] = None,
) -> bool:
    """True if no usage has been logged for this perk in the current period."""
    if today is None:
        today = date.today()

    if not perk.get("is_active", True):
        return False

    period_key = get_current_period_key(perk, today, settings)
    perk_id = perk.get("perk_id")

    for log in value_logs:
        if log.get("perk_id") == perk_id and log.get("period_key") == period_key:
            return False
    return True


def get_days_until_reset(
    perk: dict[str, Any],
    today: Optional[date] = None,
    settings: Optional[dict[str, Any]] = None,
) -> int:
    """Return the number of days remaining until the end of the current period."""
    if today is None:
        today = date.today()

    end = get_period_end_date(perk, today, settings)
    delta = (end - today).days
    return max(0, delta)


def get_expiring_soon_perks(
    perks: list[dict[str, Any]],
    value_logs: list[dict[str, Any]],
    days_threshold: int = 14,
    today: Optional[date] = None,
    settings: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Return perks that are still available but expire within `days_threshold` days."""
    if today is None:
        today = date.today()

    result = []
    for perk in perks:
        if not is_perk_available_in_current_period(perk, value_logs, today, settings):
            continue
        days_left = get_days_until_reset(perk, today, settings)
        if 0 < days_left <= days_threshold:
            result.append({**perk, "days_left": days_left})
    return result


# --------------------------------------------------------------------------- #
# Helper Functions
# --------------------------------------------------------------------------- #

def _get_anniversary_month(card: str, settings: Optional[dict[str, Any]]) -> int:
    """Return the anniversary month (1-12) for the given card from Settings."""
    if not settings:
        # Sensible defaults for demo data (see data/seed_perks.py)
        if "Delta" in card:
            return 6
        if "Amex" in card:
            return 5
        return 1

    if "Delta" in card:
        return int(settings.get("delta_anniversary_month") or 6)
    if "Amex" in card:
        return int(settings.get("amex_anniversary_month") or 5)
    return int(settings.get("chase_anniversary_month") or 1)


def format_period_label(period_key: str) -> str:
    """Human-friendly label for display in the UI."""
    if "-Q" in period_key:
        year, q = period_key.split("-Q")
        return f"Q{q} {year}"
    if "-anniv" in period_key:
        return period_key.replace("-anniv", " (anniversary year)")
    if period_key.endswith("-calendar"):
        year = period_key.split("-")[0]
        return f"Calendar Year {year}"
    if "-H" in period_key:
        year, half = period_key.split("-")
        return f"{half} {year}"
    return period_key


# --------------------------------------------------------------------------- #
# Small Demo / Self-Test (run with `python -m app.utils.date_utils`)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    from pprint import pprint

    today = date(2026, 5, 28)  # Mid Q2 2026

    sample_perk = {
        "perk_id": "amex_plat_resy_2026_q2",
        "reset_type": "quarterly",
        "card": "Amex Platinum",
    }
    settings = {"amex_anniversary_month": 5, "delta_anniversary_month": 6}

    print("Today:", today)
    print("Quarterly period key:", get_current_period_key(sample_perk, today))
    print("Period ends:", get_period_end_date(sample_perk, today))
    print("Days left:", get_days_until_reset(sample_perk, today))

    companion = {"perk_id": "delta_companion_2026", "reset_type": "card_anniversary", "card": "Delta SkyMiles Platinum American Express"}
    print("\nDelta Companion (anniv June):")
    print("  Period key:", get_current_period_key(companion, today, settings))
    print("  Ends:", get_period_end_date(companion, today, settings))

    pprint({"expiring_soon_example": "See get_expiring_soon_perks()"})
