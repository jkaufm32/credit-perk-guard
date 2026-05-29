"""
PerkGuard Trip-Aware Suggestion Engine (V1.5)

Lightweight, rule-based suggestions that surface high-value ways to use
available perks for upcoming trips.

Designed to be called from both the Streamlit dashboard and the digest generators.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.utils.date_utils import is_perk_available_in_current_period


def get_trip_suggestions(
    available_perks: list[dict[str, Any]],
    trips: list[dict[str, Any]],
    value_logs: list[dict[str, Any]],
    today: date | None = None,
    settings: dict[str, Any] | None = None,
    lookahead_days: int = 90,
) -> list[dict[str, Any]]:
    """Return a list of actionable suggestions for the next `lookahead_days`.

    Each suggestion is a small dict with:
        - title: short headline
        - detail: 1-2 sentence explanation
        - perk_id (optional): the specific perk this applies to
        - trip_id (optional)
        - priority: "high" | "medium" | "low"
    """
    if today is None:
        today = date.today()

    upcoming_trips = [
        t for t in trips
        if t.get("start_date") and _parse_date(t["start_date"]) >= today
        and _parse_date(t["start_date"]) <= today + timedelta(days=lookahead_days)
    ]

    suggestions: list[dict[str, Any]] = []

    # 1. Delta Companion Certificate for upcoming domestic / short-haul trips
    companion = next((p for p in available_perks if "companion" in (p.get("perk_id") or "")), None)
    if companion and upcoming_trips:
        domestic_trips = [t for t in upcoming_trips if "domestic" in (t.get("destination_type") or "").lower()]
        if domestic_trips:
            t = domestic_trips[0]
            suggestions.append({
                "title": "Use your Delta Companion Certificate",
                "detail": f"You have an upcoming domestic trip ({t.get('name')}). The Companion Certificate is available and perfect for this.",
                "perk_id": companion.get("perk_id"),
                "trip_id": t.get("trip_id"),
                "priority": "high",
            })

    # 2. Amex Hotel credits for international or premium stays
    hotel_credits = [p for p in available_perks if "hotel" in (p.get("name") or "").lower()]
    intl_trips = [t for t in upcoming_trips if "international" in (t.get("destination_type") or "").lower()]
    if hotel_credits and intl_trips:
        suggestions.append({
            "title": "Book with Fine Hotels + Resorts or The Hotel Collection",
            "detail": "You have hotel credits available and an international trip coming up. Consider using the $300 semi-annual credit.",
            "perk_id": hotel_credits[0].get("perk_id") if hotel_credits else None,
            "trip_id": intl_trips[0].get("trip_id"),
            "priority": "high",
        })

    # 3. Airline incidental credit before a trip (bags, seat selection, etc.)
    airline = next((p for p in available_perks if "airline" in (p.get("name") or "").lower()), None)
    if airline and upcoming_trips:
        suggestions.append({
            "title": "Apply airline incidental credit before your trip",
            "detail": "Use the $200 credit for checked bags, in-flight purchases, or seat selection on your upcoming flights.",
            "perk_id": airline.get("perk_id"),
            "trip_id": upcoming_trips[0].get("trip_id"),
            "priority": "medium",
        })

    # 4. Chase 5% activation reminder (always useful when active)
    chase_5x = next((p for p in available_perks if "5%" in (p.get("name") or "") and "Activate" in (p.get("name") or "")), None)
    if chase_5x:
        suggestions.append({
            "title": "Activate Chase Freedom Flex 5% categories",
            "detail": "Quarterly 5% bonus categories are still available to activate. Do this before the deadline for your upcoming spending.",
            "perk_id": chase_5x.get("perk_id"),
            "priority": "medium",
        })

    # 5. Rideshare / Resy credits for any trip with dining or ground transport
    rideshare = next((p for p in available_perks if "rideshare" in (p.get("name") or "").lower()), None)
    if rideshare and upcoming_trips:
        suggestions.append({
            "title": "Use your monthly rideshare credit around travel days",
            "detail": "Airport transfers, local rides, etc. — your $10–$15 monthly rideshare credit resets soon and pairs well with trips.",
            "perk_id": rideshare.get("perk_id"),
            "priority": "low",
        })

    return suggestions[:6]  # Keep it focused


def _parse_date(d: str) -> date:
    try:
        return date.fromisoformat(d)
    except Exception:
        return date(2099, 1, 1)
