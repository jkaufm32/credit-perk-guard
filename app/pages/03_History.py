"""
History & Value Page (V1.5 / V2)

Shows past value captured, YTD totals, and basic reporting.

Full implementation (with charts and trip-linked history) lands in V1.5 + V2.
"""

import streamlit as st

st.title("📈 History & Value")
st.caption("See what you've captured and where your biggest wins came from")

st.info(
    "This page is scaffolded in V1 and will be completed during the V1.5 / V2 phases.\n\n"
    "Planned features:\n"
    "• Full table of all ValueLogs\n"
    "• YTD total value captured (by card and overall)\n"
    "• Simple bar/pie charts (via plotly)\n"
    "• Filter by trip, card, or date range"
)

st.markdown("**Demo YTD value (placeholder):** $1,247 captured across 11 perks")
