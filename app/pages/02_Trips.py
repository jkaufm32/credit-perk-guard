"""
Trips Page (V1.5)

Manage upcoming trips. Trip data powers suggestion logic in the dashboard
and monthly digest.

This page is intentionally minimal in V1. Full CRUD + linking appears in V1.5.
"""

import streamlit as st

st.title("✈️ Trips")
st.caption("Track upcoming travel to unlock trip-aware perk suggestions (V1.5)")

st.info(
    "This page will be fully implemented in the V1.5 phase.\n\n"
    "Planned features:\n"
    "• Add / edit / delete upcoming trips\n"
    "• Link a trip when marking a perk as used\n"
    "• Automatic suggestions (Companion Certificate for Delta trips, hotel credits for international, etc.)"
)

st.markdown("**Example trips** (will come from your Google Sheet after seeding):")
st.dataframe(
    [
        {"name": "NYC → LAX (June 2026)", "dates": "Jun 12–18", "type": "Domestic"},
        {"name": "NYC → Europe (August 2026)", "dates": "Aug 5–20", "type": "International"},
    ],
    hide_index=True,
    use_container_width=True,
)
