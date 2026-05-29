"""
PerkGuard Dashboard (V1 — Fully Working)

Main view showing all perks grouped by card, live availability status,
expiring-soon alerts, and a real "Mark as Used + Log Value" flow that writes
directly to the ValueLogs sheet.
"""

import uuid
from datetime import date, datetime

import streamlit as st

from app.utils.sheets_client import (
    get_perks,
    get_value_logs,
    get_settings,
    get_connection_status,
    append_value_log,
    get_trips,
)
from app.utils.date_utils import (
    is_perk_available_in_current_period,
    get_days_until_reset,
    get_expiring_soon_perks,
    format_period_label,
    get_current_period_key,
)
from app.utils.suggestions import get_trip_suggestions

st.title("🛡️ PerkGuard")
st.caption("Never miss a credit card benefit • " + date.today().strftime("%B %d, %Y"))

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _clear_caches() -> None:
    """Bust Streamlit caches after we write new data."""
    get_perks.clear()
    get_value_logs.clear()
    get_settings.clear()


# --------------------------------------------------------------------------- #
# Connection Check
# --------------------------------------------------------------------------- #
status = get_connection_status()
if not status.get("ok"):
    st.error("Cannot connect to Google Sheets. Check your setup.")
    st.code(status.get("error", "Unknown error"))
    st.info(
        "Run the seeder first:\n\n"
        '    python scripts/seed_sheets.py --sheet-url "https://docs.google.com/spreadsheets/d/YOUR_ID/edit"'
    )
    st.stop()

# --------------------------------------------------------------------------- #
# Load Data (fresh on every rerun after writes)
# --------------------------------------------------------------------------- #
perks = get_perks()
value_logs = get_value_logs()
settings = get_settings()
trips = get_trips()

if not perks:
    st.warning("No perks found. Run the seed script to populate sample data.")
    st.stop()

# --------------------------------------------------------------------------- #
# Summary KPIs
# --------------------------------------------------------------------------- #
today = date.today()

available_count = sum(
    1 for p in perks if is_perk_available_in_current_period(p, value_logs, today, settings)
)
expiring = get_expiring_soon_perks(perks, value_logs, days_threshold=14, today=today, settings=settings)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Available Now", available_count)
col2.metric("Expiring ≤14d", len(expiring))
col3.metric("Total Perks Tracked", len(perks))
col4.metric("Logs Recorded", len(value_logs))

if expiring:
    st.warning(f"⚠️ {len(expiring)} perks expiring soon — review the lists below.")

# --------------------------------------------------------------------------- #
# V1.5: Trip-Aware Suggestions (prominent at top)
# --------------------------------------------------------------------------- #
available_perks = [p for p in perks if is_perk_available_in_current_period(p, value_logs, today, settings)]
suggestions = get_trip_suggestions(available_perks, trips, value_logs, today, settings)

if suggestions:
    with st.container(border=True):
        st.markdown("### 💡 Smart Suggestions for Your Upcoming Trips")
        for s in suggestions[:3]:
            trip_name = next((t.get("name") for t in trips if t.get("trip_id") == s.get("trip_id")), "")
            extra = f" → {trip_name}" if trip_name else ""
            st.markdown(f"- **{s['title']}**{extra}<br><span style='color:#666; font-size:0.9em'>{s['detail']}</span>", unsafe_allow_html=True)

st.divider()

# --------------------------------------------------------------------------- #
# Mark-as-Used Dialog (real write to ValueLogs)
# --------------------------------------------------------------------------- #
@st.dialog("Log Value Captured")
def log_usage_dialog(perk: dict) -> None:
    """Modal form for capturing value when a perk is used (V1.5: supports trip linking)."""
    st.write(f"**{perk.get('name')}**")
    st.caption(f"{perk.get('card')} • {perk.get('category')}")

    period_key = get_current_period_key(perk, today, settings)

    # Build trip options for linking (V1.5 feature)
    trip_options = ["(no trip)"] + [f"{t.get('name', 'Unnamed')} ({t.get('trip_id')})" for t in trips]
    trip_id_map = {f"{t.get('name', 'Unnamed')} ({t.get('trip_id')})": t.get("trip_id") for t in trips}

    with st.form("log_usage_form", clear_on_submit=True):
        used_date = st.date_input("Date used", value=today, max_value=today)
        value = st.number_input(
            "Value captured (USD or count)",
            min_value=0.0,
            value=float(perk.get("max_value", 0) or 0),
            step=1.0,
        )
        selected_trip = st.selectbox("Link to trip (optional)", options=trip_options, index=0)
        notes = st.text_area("Notes (optional)", placeholder="e.g. Used on flight to LAX, partial credit of $87")
        submitted = st.form_submit_button("Save & Mark as Used", type="primary")

        if submitted:
            chosen_trip_id = trip_id_map.get(selected_trip, "") if selected_trip != "(no trip)" else ""
            log_row = {
                "log_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "perk_id": perk.get("perk_id"),
                "period_key": period_key,
                "used_date": used_date.isoformat(),
                "value_captured": value,
                "trip_id": chosen_trip_id,
                "notes": notes,
                "source": "dashboard",
            }
            try:
                append_value_log(log_row)
                _clear_caches()
                st.success("✅ Value logged with trip link! Dashboard will refresh.")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to write to Google Sheets: {exc}")

# --------------------------------------------------------------------------- #
# Grouped Perk Display (by card)
# --------------------------------------------------------------------------- #
cards = sorted({p["card"] for p in perks if p.get("card")})

for card in cards:
    st.subheader(card)

    card_perks = [p for p in perks if p.get("card") == card]

    for perk in card_perks:
        available = is_perk_available_in_current_period(perk, value_logs, today, settings)
        days_left = get_days_until_reset(perk, today, settings)
        period_key = get_current_period_key(perk, today, settings)
        period_label = format_period_label(period_key)

        # Status pill
        if not perk.get("is_active", True):
            status_text = "🚫 Inactive"
            status_color = "#888"
        elif not available:
            status_text = "✅ Used this period"
            status_color = "#22c55e"
        elif days_left <= 14:
            status_text = f"⏰ Expiring in {days_left} days"
            status_color = "#f59e0b"
        else:
            status_text = "🟢 Available"
            status_color = "#22c55e"

        with st.container(border=True):
            c1, c2 = st.columns([3.5, 1.2])
            with c1:
                st.markdown(f"**{perk.get('name', 'Unnamed perk')}**")
                st.caption(f"{perk.get('category', '')} • Resets: {period_label}")
                if perk.get("notes"):
                    st.caption(f"📝 {perk['notes']}")
                if perk.get("enrollment_required"):
                    st.caption("📋 Enrollment required (check your Amex app)")

            with c2:
                st.markdown(
                    f"<div style='text-align:right; color:{status_color}; font-weight:600'>{status_text}</div>",
                    unsafe_allow_html=True,
                )
                if available and perk.get("is_active", True):
                    if st.button("Mark as Used", key=f"mark_{perk['perk_id']}", type="primary", use_container_width=True):
                        log_usage_dialog(perk)

    st.divider()

# --------------------------------------------------------------------------- #
# Expiring Soon Compact List
# --------------------------------------------------------------------------- #
if expiring:
    st.subheader("⏰ Expiring Soon (≤14 days)")
    for p in sorted(expiring, key=lambda x: x.get("days_left", 999)):
        st.write(f"- **{p['name']}** ({p['card']}) — **{p.get('days_left')} days** left • {format_period_label(get_current_period_key(p, today, settings))}")

st.caption(
    "Data cached ~60s. Use the refresh button in the top-right or rerun the page to pull the latest from Sheets. "
    "All status is computed live from ValueLogs — safe to edit notes directly in the sheet."
)

# Quick refresh affordance
if st.button("🔄 Refresh data from Sheets", type="secondary"):
    _clear_caches()
    st.rerun()
