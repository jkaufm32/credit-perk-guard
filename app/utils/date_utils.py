"""
PerkGuard Date & Reset Utilities
Pure functions for calculating availability, period keys, and expiry
across all supported reset types.

Supported reset_type values:
    calendar_year, quarterly, monthly, card_anniversary, semi_annual, one_time, custom

Hard expiry support:
    For one_time or custom perks that have a fixed deadline (e.g. certain
    companion certificates), you can store an ISO date (YYYY-MM-DD) in
    reset_anchor. The utils will treat it as the effective end date for
    status and expiring calculations.

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
        card = perk.get("card", "")
        anniv_month = _get_anniversary_month(card, settings)
        if today.month < anniv_month:
            period_year = year - 1
        else:
            period_year = year
        return f"{period_year}-{anniv_month:02d}-anniv"
    if reset_type == "semi_annual":
        anchor = (perk.get("reset_anchor") or "H1").upper()
        if today.month <= 6:
            current_half = "H1"
            current_year = year
        else:
            current_half = "H2"
            current_year = year

        if anchor == current_half:
            return f"{current_year}-{anchor}"
        else:
            # Perk belongs to the opposite half → use the most recent occurrence of its half
            if current_half == "H1":
                # We're in H1, so H2 perk's current period is last year's H2
                return f"{year - 1}-H2"
            else:
                # We're in H2, so H1 perk's current period is this year's H1
                return f"{year}-H1"
    if reset_type == "one_time":
        return f"{year}-one_time"
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
        if end_month == 12:
            return date(year, 12, 31)
        return date(year, end_month, 1) + relativedelta(months=1) - relativedelta(days=1)
    if reset_type == "monthly":
        if today.month == 12:
            return date(year, 12, 31)
        return date(year, today.month + 1, 1) - relativedelta(days=1)
    if reset_type == "card_anniversary":
        anniv_month = _get_anniversary_month(perk.get("card", ""), settings)
        period_year = year if today.month >= anniv_month else year - 1
        if anniv_month == 12:
            return date(period_year, 12, 31)
        return date(period_year, anniv_month + 1, 1) - relativedelta(days=1)
    if reset_type == "semi_annual":
        anchor = (perk.get("reset_anchor") or "H1").upper()
        if today.month <= 6:
            current_half = "H1"
            current_year = year
        else:
            current_half = "H2"
            current_year = year

        if anchor == current_half:
            # This perk's half is the current one
            if anchor == "H1":
                return date(current_year, 6, 30)
            else:
                return date(current_year, 12, 31)
        else:
            # Perk belongs to the opposite half → end date of its most recent period
            if anchor == "H1":
                # We're in H2, H1 perk's most recent period ended June 30 this year
                return date(current_year, 6, 30)
            else:
                # We're in H1, H2 perk's most recent period ended Dec 31 last year
                return date(current_year - 1, 12, 31)
    if reset_type == "one_time":
        return date(2099, 12, 31)
    return date(year, 12, 31)


def is_perk_currently_relevant(
    perk: dict[str, Any],
    today: Optional[date] = None,
    settings: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Return whether a perk should be shown in the current dashboard / digest view.
    This version is defensive against bad/malformed rows in the sheet.
    """
    if today is None:
        today = date.today()

    # Skip completely empty or broken rows
    perk_id = perk.get("perk_id")
    if not perk_id or str(perk_id).strip() == "":
        return False

    reset_type = perk.get("reset_type")
    if not reset_type:
        return True  # default to showing if reset_type is missing/empty

    # Safely coerce reset_anchor to string (handles dates, numbers, None, etc.)
    raw_anchor = perk.get("reset_anchor")
    anchor = str(raw_anchor).upper().strip() if raw_anchor is not None else ""

    if reset_type == "semi_annual":
        current_half = "H1" if today.month <= 6 else "H2"
        return anchor == current_half

    if reset_type == "quarterly":
        current_q = f"Q{(today.month - 1) // 3 + 1}"
        return anchor == current_q

    if reset_type == "monthly":
        # Monthly benefits are relevant every month.
        # (If someone creates per-month rows in the future, this can be extended.)
        return True

    # calendar_year, one_time, custom, etc. → always show
    return True


def get_effective_end_date(
    perk: dict[str, Any],
    today: Optional[date] = None,
    settings: Optional[dict[str, Any]] = None,
) -> date:
    """
    Return the effective end date for a perk.

    This unifies two concepts:
    - Normal period-based resets (via reset_type + reset_anchor)
    - Hard expiry dates for one-off or limited-time perks.

    If `reset_anchor` is a valid YYYY-MM-DD string and represents a date
    in the future (or today), it is treated as a hard expiry date.
    This supports real-world cases like certain companion certificates
    or promotional benefits that have a fixed deadline unrelated to
    the normal reset cycle.

    Otherwise, falls back to the normal `get_period_end_date`.
    """
    if today is None:
        today = date.today()

    raw_anchor = perk.get("reset_anchor")
    if raw_anchor and isinstance(raw_anchor, str) and raw_anchor.count("-") == 2:
        try:
            hard_date = datetime.strptime(raw_anchor, "%Y-%m-%d").date()
            if hard_date >= today:
                return hard_date
        except ValueError:
            pass

    return get_period_end_date(perk, today, settings)


# --------------------------------------------------------------------------- #
# Availability Logic
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
    """
    Return the number of days remaining until the effective end date.

    Uses hard expiry date (if present in reset_anchor) when applicable,
    otherwise falls back to normal period end.
    """
    if today is None:
        today = date.today()
    end = get_effective_end_date(perk, today, settings)
    delta = (end - today).days
    return max(0, delta)


def get_perk_status(
    perk: dict[str, Any],
    value_logs: list[dict[str, Any]],
    today: Optional[date] = None,
    settings: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Single source of truth for a perk's current visual and logical status.

    This function replaces the previous duplicated ad-hoc logic that lived
    in the dashboard for handling both normal reset periods and hard expiry
    dates (YYYY-MM-DD stored in reset_anchor).

    Returns a rich dict that can drive:
    - Individual perk cards (status text + color)
    - KPI counts
    - Warning banners
    - Filtered "Expiring Soon" views
    - Future notifications and reports

    Fields:
        state: "available" | "used" | "expiring_soon" | "inactive"
        days_left: int (0 if already past)
        expiry_date: the effective date being used
        is_hard_expiry: True when a literal date in reset_anchor was used
        status_text: human-ready string (with emoji)
        status_color: hex color for UI
        priority: "high" | "medium" | "low" | "none"
        is_available: convenience bool
    """
    if today is None:
        today = date.today()

    is_active = perk.get("is_active", True)
    available = is_perk_available_in_current_period(perk, value_logs, today, settings)
    days_left = get_days_until_reset(perk, today, settings)
    effective_end = get_effective_end_date(perk, today, settings)

    # Detect hard expiry (date in reset_anchor that differs from normal period end)
    raw_anchor = perk.get("reset_anchor")
    normal_end = get_period_end_date(perk, today, settings)
    is_hard_expiry = bool(
        raw_anchor
        and isinstance(raw_anchor, str)
        and raw_anchor.count("-") == 2
        and effective_end != normal_end
    )

    if not is_active:
        state = "inactive"
        status_text = "🚫 Inactive"
        status_color = "#888888"
        priority = "none"
    elif not available:
        state = "used"
        status_text = "✅ Used this period"
        status_color = "#22c55e"
        priority = "none"
    elif 0 < days_left <= 14:
        state = "expiring_soon"
        if is_hard_expiry:
            status_text = f"⏰ Expires {effective_end.strftime('%b %d, %Y')} ({days_left}d)"
        else:
            status_text = f"⏰ Expiring in {days_left} days"
        status_color = "#f59e0b"
        priority = "high"
    else:
        state = "available"
        status_text = "🟢 Available"
        status_color = "#22c55e"
        priority = "low" if days_left < 30 else "none"

    return {
        "state": state,
        "days_left": days_left,
        "expiry_date": effective_end,
        "is_hard_expiry": is_hard_expiry,
        "status_text": status_text,
        "status_color": status_color,
        "priority": priority,
        "is_available": available,
    }


def get_expiring_soon_perks(
    perks: list[dict[str, Any]],
    value_logs: list[dict[str, Any]],
    days_threshold: int = 14,
    today: Optional[date] = None,
    settings: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Return perks that are still available and expiring within `days_threshold` days.

    Uses the unified status logic (including hard expiry dates from reset_anchor).
    Returns richer dictionaries containing the full output of get_perk_status().
    """
    if today is None:
        today = date.today()

    # === Exclude inactive perks from the expiring list ===
    perks = [p for p in perks if p.get("is_active", True)]

    result = []
    for perk in perks:
        if not perk.get("is_active", True):
            continue
        status = get_perk_status(perk, value_logs, today, settings)
        if status["state"] == "expiring_soon" and status["days_left"] <= days_threshold:
            result.append({**perk, **status})
    return result


# --------------------------------------------------------------------------- #
# Helper Functions
# --------------------------------------------------------------------------- #
def _get_anniversary_month(card: str, settings: Optional[dict[str, Any]]) -> int:
    """Return the anniversary month (1-12) for the given card from Settings."""
    if not settings:
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
# Small Demo / Self-Test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    from pprint import pprint

    today = date(2026, 5, 28)
    settings = {"amex_anniversary_month": 5, "delta_anniversary_month": 6}

    print("=== Normal reset-type behavior ===")
    quarterly = {
        "perk_id": "amex_plat_resy_2026_q2",
        "reset_type": "quarterly",
        "card": "Amex Platinum",
        "reset_anchor": "Q2",
    }
    print("Today:", today)
    print("Quarterly ends:", get_period_end_date(quarterly, today))
    print("Days left:", get_days_until_reset(quarterly, today))

    print("\n=== Hard expiry date support (the 2025 Companion pattern) ===")
    hard_expiry_cert = {
        "perk_id": "delta_companion_2025",
        "card": "Delta SkyMiles Platinum American Express",
        "name": "Delta Companion Certificate 2025",
        "reset_type": "one_time",
        "reset_anchor": "2026-06-05",   # Hard deadline, not a reset rule
    }
    print("Hard-expiry perk anchor:", hard_expiry_cert["reset_anchor"])
    print("Effective end date:", get_effective_end_date(hard_expiry_cert, today))
    print("Days left:", get_days_until_reset(hard_expiry_cert, today))

    status = get_perk_status(hard_expiry_cert, value_logs=[], today=today)
    print("get_perk_status output:")
    pprint(status)

    print("\n=== get_expiring_soon_perks with hard expiry ===")
    all_perks = [quarterly, hard_expiry_cert]
    expiring = get_expiring_soon_perks(all_perks, value_logs=[], days_threshold=14, today=today)
    print(f"Found {len(expiring)} expiring perks (should include the 2025 cert):")
    for p in expiring:
        print(f"  - {p['name']} | hard_expiry={p.get('is_hard_expiry')} | days={p.get('days_left')}")

    print("\n=== Semi-annual H1 vs H2 independent periods ===")
    h1_perk = {"perk_id": "amex_hotel_h1", "reset_type": "semi_annual", "reset_anchor": "H1", "card": "Amex Platinum"}
    h2_perk = {"perk_id": "amex_hotel_h2", "reset_type": "semi_annual", "reset_anchor": "H2", "card": "Amex Platinum"}

    print(f"Today is in {'H1' if today.month <= 6 else 'H2'} {today.year}")
    print(f"H1 perk current period key: {get_current_period_key(h1_perk, today)}")
    print(f"H1 perk ends: {get_period_end_date(h1_perk, today)}")
    print(f"H2 perk current period key: {get_current_period_key(h2_perk, today)}")
    print(f"H2 perk ends: {get_period_end_date(h2_perk, today)}")
