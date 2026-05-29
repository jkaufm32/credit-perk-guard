"""
PerkGuard — Realistic 2026 seed data for three cards.

This module defines the initial Perks that will be loaded into Google Sheets
by scripts/seed_sheets.py.

Reset types supported (must match date_utils logic):
- calendar_year
- quarterly
- monthly
- card_anniversary
- semi_annual
- one_time
- custom

All values and rules are based on publicly documented benefits as of May 2026
(Amex 2025 refresh changes included). User should adjust anniversary months
in the Settings sheet after seeding.
"""

from typing import Any

# Default anniversary months used in sample data (user must update in Settings)
DEFAULT_AMEX_ANNIVERSARY_MONTH = 5   # Example: May renewal
DEFAULT_DELTA_ANNIVERSARY_MONTH = 6  # Example: June renewal

# Full list of perks to seed
SEED_PERKS: list[dict[str, Any]] = [
    # ===================== AMEX PLATINUM =====================
    {
        "perk_id": "amex_plat_airline_2026",
        "card": "Amex Platinum",
        "name": "$200 Airline Incidental Credit",
        "category": "Airline",
        "reset_type": "calendar_year",
        "reset_anchor": "01-01",
        "max_value": 200,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "Select airline in Amex app (change once per year). Covers bags, in-flight food, etc.",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_hotel_2026_h1",
        "card": "Amex Platinum",
        "name": "$300 Hotel Credit (Jan–Jun)",
        "category": "Hotel",
        "reset_type": "semi_annual",
        "reset_anchor": "H1",
        "max_value": 300,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "Fine Hotels + Resorts or The Hotel Collection (2-night min for THC). Book by June 30.",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_hotel_2026_h2",
        "card": "Amex Platinum",
        "name": "$300 Hotel Credit (Jul–Dec)",
        "category": "Hotel",
        "reset_type": "semi_annual",
        "reset_anchor": "H2",
        "max_value": 300,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "Fine Hotels + Resorts or The Hotel Collection. Book by Dec 31.",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_resy_2026_q2",
        "card": "Amex Platinum",
        "name": "$100 Resy Credit (Q2)",
        "category": "Dining",
        "reset_type": "quarterly",
        "reset_anchor": "Q2",
        "max_value": 100,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "Eligible Resy restaurants (U.S.). $400 total annual cap across quarters.",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_resy_2026_q3",
        "card": "Amex Platinum",
        "name": "$100 Resy Credit (Q3)",
        "category": "Dining",
        "reset_type": "quarterly",
        "reset_anchor": "Q3",
        "max_value": 100,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_resy_2026_q4",
        "card": "Amex Platinum",
        "name": "$100 Resy Credit (Q4)",
        "category": "Dining",
        "reset_type": "quarterly",
        "reset_anchor": "Q4",
        "max_value": 100,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_lululemon_2026_q2",
        "card": "Amex Platinum",
        "name": "$75 lululemon Credit (Q2)",
        "category": "Shopping",
        "reset_type": "quarterly",
        "reset_anchor": "Q2",
        "max_value": 75,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "U.S. stores + lululemon.com (no outlets). $300 annual total.",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_digital_entertainment_2026",
        "card": "Amex Platinum",
        "name": "$25/mo Digital Entertainment Credit",
        "category": "Entertainment",
        "reset_type": "monthly",
        "reset_anchor": "01",
        "max_value": 25,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "Disney+, Hulu, ESPN+, NYT, WSJ, YouTube Premium, etc. $300 annual cap.",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_uber_cash_2026",
        "card": "Amex Platinum",
        "name": "$200 Uber Cash (monthly + bonus)",
        "category": "Rideshare",
        "reset_type": "monthly",
        "reset_anchor": "01",
        "max_value": 15,  # simplified; actual is $15/mo + $20 Dec bonus
        "value_unit": "USD",
        "enrollment_required": False,
        "notes": "Link Amex in Uber app. $200 total per calendar year.",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_clear_2026",
        "card": "Amex Platinum",
        "name": "$209 CLEAR+ Credit",
        "category": "Travel",
        "reset_type": "calendar_year",
        "reset_anchor": "01-01",
        "max_value": 209,
        "value_unit": "USD",
        "enrollment_required": False,
        "notes": "Auto-renewing CLEAR+ membership.",
        "is_active": True,
    },
    {
        "perk_id": "amex_plat_saks_2026_h1",
        "card": "Amex Platinum",
        "name": "$50 Saks Credit (Jan–Jun only)",
        "category": "Shopping",
        "reset_type": "semi_annual",
        "reset_anchor": "H1",
        "max_value": 50,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "Benefit ends July 1 2026. Use in first half of year.",
        "is_active": True,
    },

    # ===================== DELTA SKYMILES PLATINUM AMEX =====================
    {
        "perk_id": "delta_companion_2026",
        "card": "Delta SkyMiles Platinum American Express",
        "name": "Delta Companion Certificate",
        "category": "Travel",
        "reset_type": "card_anniversary",
        "reset_anchor": "anniv",
        "max_value": 1,
        "value_unit": "certificate",
        "enrollment_required": False,
        "notes": "Issued in your card renewal month (see Settings). Valid ~1 year. Main Cabin companion (taxes/fees only).",
        "is_active": True,
    },
    {
        "perk_id": "delta_resy_2026",
        "card": "Delta SkyMiles Platinum American Express",
        "name": "$10/mo Resy Credit",
        "category": "Dining",
        "reset_type": "monthly",
        "reset_anchor": "01",
        "max_value": 10,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "$120 annual cap. U.S. Resy restaurants.",
        "is_active": True,
    },
    {
        "perk_id": "delta_rideshare_2026",
        "card": "Delta SkyMiles Platinum American Express",
        "name": "$10/mo Rideshare Credit",
        "category": "Rideshare",
        "reset_type": "monthly",
        "reset_anchor": "01",
        "max_value": 10,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "$120 annual cap. Uber/Lyft rides (not delivery).",
        "is_active": True,
    },
    {
        "perk_id": "delta_stays_2026",
        "card": "Delta SkyMiles Platinum American Express",
        "name": "$150 Delta Stays Credit",
        "category": "Hotel",
        "reset_type": "calendar_year",
        "reset_anchor": "01-01",
        "max_value": 150,
        "value_unit": "USD",
        "enrollment_required": True,
        "notes": "Prepaid hotels/vacation rentals via Delta Stays. Book early for posting in same year.",
        "is_active": True,
    },
    {
        "perk_id": "delta_inflight_2026",
        "card": "Delta SkyMiles Platinum American Express",
        "name": "20% Back on Delta In-Flight Purchases",
        "category": "Travel",
        "reset_type": "calendar_year",
        "reset_anchor": "01-01",
        "max_value": 999,  # effectively uncapped for practical purposes
        "value_unit": "USD",
        "enrollment_required": False,
        "notes": "20% statement credit on food, beverage, and other onboard purchases (Delta operated).",
        "is_active": True,
    },

    # ===================== CHASE FREEDOM FLEX =====================
    {
        "perk_id": "chase_q2_2026_5x_activation",
        "card": "Chase Freedom Flex",
        "name": "Q2 2026 5% Categories (Activate by Jun 14)",
        "category": "Other",
        "reset_type": "quarterly",
        "reset_anchor": "Q2",
        "max_value": 1500,  # spend cap for 5%
        "value_unit": "activation",
        "enrollment_required": True,
        "notes": "Amazon, Chase Travel, Feeding America / Whole Foods. Activate at chasebonus.com or app by deadline.",
        "is_active": True,
    },
    {
        "perk_id": "chase_q3_2026_5x_activation",
        "card": "Chase Freedom Flex",
        "name": "Q3 2026 5% Categories (Activate by Sep 14)",
        "category": "Other",
        "reset_type": "quarterly",
        "reset_anchor": "Q3",
        "max_value": 1500,
        "value_unit": "activation",
        "enrollment_required": True,
        "notes": "Categories announced ~June 2026. Activation required every quarter.",
        "is_active": True,
    },
    {
        "perk_id": "chase_q4_2026_5x_activation",
        "card": "Chase Freedom Flex",
        "name": "Q4 2026 5% Categories (Activate by Dec 14)",
        "category": "Other",
        "reset_type": "quarterly",
        "reset_anchor": "Q4",
        "max_value": 1500,
        "value_unit": "activation",
        "enrollment_required": True,
        "notes": "",
        "is_active": True,
    },
]

# Settings defaults (written to Settings sheet)
SEED_SETTINGS: dict[str, Any] = {
    "user_email": "your-email@example.com",
    "digest_day": 1,
    "urgent_alert_days": "14,30",
    "amex_anniversary_month": DEFAULT_AMEX_ANNIVERSARY_MONTH,
    "delta_anniversary_month": DEFAULT_DELTA_ANNIVERSARY_MONTH,
    "chase_anniversary_month": None,
    "default_currency": "USD",
    "suggestion_lookahead_days": 90,
}

# Minimal starter trips (optional, for V1.5 demo)
SEED_TRIPS: list[dict[str, Any]] = [
    {
        "trip_id": "trip_2026_june_lax",
        "name": "NYC → LAX (June 2026)",
        "start_date": "2026-06-12",
        "end_date": "2026-06-18",
        "destination_type": "Domestic",
        "notes": "Delta flight — good candidate for Companion Certificate if available.",
    },
    {
        "trip_id": "trip_2026_aug_europe",
        "name": "NYC → Europe (August 2026)",
        "start_date": "2026-08-05",
        "end_date": "2026-08-20",
        "destination_type": "International",
        "notes": "Consider FHR or Hotel Collection for Amex $300 credit.",
    },
]
