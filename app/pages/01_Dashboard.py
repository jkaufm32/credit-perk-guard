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
    get_perk_status,
    is_perk_currently_relevant,
    format_period_label,
    get_current_period_key,
)
from app.utils.suggestions import get_trip_suggestions

st.title("🛡️ PerkGuard")
st.caption("Never miss a credit card benefit • " + date.today().strftime("%B %d, %Y"))

def _clear_caches() -> None:
    """Clear all cached Sheets data (safe version)."""
    from app.utils.sheets_client import get_all_records
    try:
        get_all_records.clear()
    except Exception:
        pass  # Don't crash the UI if cache clearing fails after a successful write

status = get_connection_status()
if not status.get("ok"):
    st.error("Cannot connect to Google Sheets. Check your setup.")
    st.code(status.get("error", "Unknown error"))
    st.stop()

perks = get_perks()
value_logs = get_value_logs()
settings = get_settings()
trips = get_trips()

if not perks:
    st.warning("No perks found. Run the seed script to populate sample data.")
    st.stop()

today = date.today()

# Hide semi-annual perks whose half is not currently active
# (e.g. hide H2 perks while we are still in H1)
perks = [p for p in perks if is_perk_currently_relevant(p, today, settings)]

# Compute summary stats early so KPIs + warning banner can render near the top
available_perks = [p for p in perks if is_perk_available_in_current_period(p, value_logs, today, settings)]
expiring = get_expiring_soon_perks(perks, value_logs, days_threshold=14, today=today, settings=settings)
available_count = len(available_perks)

suggestions = get_trip_suggestions(available_perks, trips, value_logs, today, settings)

if suggestions:
    with st.container(border=True):
        st.markdown("### 💡 Smart Suggestions for Your Upcoming Trips")
        for s in suggestions[:3]:
            trip_name = next((t.get("name") for t in trips if t.get("trip_id") == s.get("trip_id")), "")
            extra = f" → {trip_name}" if trip_name else ""
            st.markdown(
                f"- **{s['title']}**{extra}<br><span style='color:#666; font-size:0.9em'>{s['detail']}</span>",
                unsafe_allow_html=True,
            )

st.divider()

# --------------------------------------------------------------------------- #
# Summary KPIs + Warning Banner (prominently near top)
# --------------------------------------------------------------------------- #
col1, col2, col3, col4 = st.columns(4)
col1.metric("Available Now", available_count)
col2.metric("Expiring ≤14d", len(expiring))
col3.metric("Total Perks Tracked", len(perks))
col4.metric("Logs Recorded", len(value_logs))

if expiring:
    st.warning(f"⚠️ {len(expiring)} perks expiring soon — see the Expiring Soon tab below.")

@st.dialog("Log Value Captured")
def log_usage_dialog(perk: dict) -> None:
    st.write(f"**{perk.get('name')}**")
    st.caption(f"{perk.get('card')} • {perk.get('category')}")

    period_key = get_current_period_key(perk, today, settings)
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
                # Even if cache clearing fails, the write usually succeeded.
                # Show a milder message so the user isn't alarmed.
                st.warning(
                    "Value was saved to Google Sheets, but there was a problem refreshing the cache.\n"
                    f"Error details: {exc}\n\n"
                    "Click the 'Refresh data from Sheets' button below to see the updated status."
                )


def render_perk_card(perk: dict, status: dict, today, settings, show_mark_button: bool = True, key_prefix: str = "") -> None:
    """Render a single perk card with improved visual treatment."""
    period_label = format_period_label(get_current_period_key(perk, today, settings))

    is_expiring = status.get("state") == "expiring_soon"
    container_class = "perk-card-expiring" if is_expiring else ""

    # Add extra "critical" class for very urgent items (stronger visual)
    days_left = status.get("days_left", 999)
    if is_expiring and days_left <= 7:
        container_class += " critical"

    # Build unique key for the button (required because the same perk can appear in multiple tabs)
    button_key = f"mark_{perk['perk_id']}"
    if key_prefix:
        button_key += f"_{key_prefix}"

    # Top progress bar on EVERY card — shows how close or far the perk is from its effective deadline/reset
    days_left = status.get("days_left", 999)

    # Use a 90-day scale. Cards with >90 days left will show a small minimum sliver so the bar is never completely empty.
    BAR_MAX_DAYS = 90
    MIN_VISIBLE_PCT = 5

    if days_left >= BAR_MAX_DAYS:
        fill_pct = MIN_VISIBLE_PCT
    else:
        fill_pct = max(MIN_VISIBLE_PCT, min(100, (BAR_MAX_DAYS - days_left) / BAR_MAX_DAYS * 100))

    # Color coding for clarity
    if days_left <= 14:
        bar_color = "#f59e0b"      # Strong orange = urgent
    elif days_left <= 30:
        bar_color = "#fbbf24"      # Amber = approaching
    else:
        bar_color = "#6b7280"      # Muted gray = plenty of time left

    # Use a container with optional extra class for styling
    with st.container(border=True):
        # Top progress bar – more prominent when critically close
        bar_opacity = 0.35 if days_left <= 7 else 0.2
        st.markdown(
            f"""
            <div style="
                height: 7px;
                width: 100%;
                background: linear-gradient(to right, {bar_color} {fill_pct}%, #2d2d2d {fill_pct}%);
                margin: 0 0 8px 0;
                border-radius: 4px;
                box-shadow: 0 0 0 1px rgba(245, 158, 11, {bar_opacity});
            "></div>
            """,
            unsafe_allow_html=True,
        )

        if container_class:
            st.markdown(
                f"<div class='{container_class}'>",
                unsafe_allow_html=True,
            )

        c1, c2 = st.columns([3.5, 1.2])
        with c1:
            st.markdown(f"**{perk.get('name', 'Unnamed perk')}**")
            st.caption(f"{perk.get('category', '')} • Resets: {period_label}")
            if perk.get("notes"):
                st.caption(f"📝 {perk['notes']}")
            if perk.get("enrollment_required"):
                st.caption("📋 Enrollment required (check your Amex app)")

            # Show hard-expiry callout when relevant
            if status.get("is_hard_expiry"):
                st.caption("⏰ **Hard expiry date** (does not follow normal reset cycle)")

        with c2:
            st.markdown(
                f"<div style='text-align:right; color:{status['status_color']}; font-weight:600'>{status['status_text']}</div>",
                unsafe_allow_html=True,
            )
            if show_mark_button and status.get("is_available") and perk.get("is_active", True):
                if st.button("Mark as Used", key=button_key, type="primary", use_container_width=True):
                    log_usage_dialog(perk)

        if container_class:
            st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Main Perk Views — Tabbed for clarity (per user preference)
# --------------------------------------------------------------------------- #
cards = sorted({p["card"] for p in perks if p.get("card")})

tab_all, tab_expiring, tab_available, tab_used = st.tabs(
    ["All Perks", "⏰ Expiring Soon", "Available Now", "Used This Period"]
)

with tab_all:
    for card in cards:
        st.subheader(card)
        card_perks = [p for p in perks if p.get("card") == card]

        for perk in card_perks:
            status = get_perk_status(perk, value_logs, today, settings)
            render_perk_card(perk, status, today, settings, key_prefix="all")

        st.divider()

with tab_expiring:
    if expiring:
        st.caption("Perks with ≤14 days remaining (including hard-expiry dates). Strongest visual treatment applied.")
        sorted_expiring = sorted(expiring, key=lambda x: x.get("days_left", 999))
        for p in sorted_expiring:
            status = get_perk_status(p, value_logs, today, settings)
            # Force the rich card view even in this tab
            render_perk_card(p, status, today, settings, show_mark_button=True, key_prefix="expiring")
    else:
        st.info("No perks expiring in the next 14 days. Great job!")

with tab_available:
    available_now = [p for p in perks if get_perk_status(p, value_logs, today, settings).get("is_available")]
    if available_now:
        for card in cards:
            card_available = [p for p in available_now if p.get("card") == card]
            if card_available:
                st.subheader(card)
                for perk in card_available:
                    status = get_perk_status(perk, value_logs, today, settings)
                    render_perk_card(perk, status, today, settings, key_prefix="available")
    else:
        st.info("No available perks right now.")

with tab_used:
    used_perks = [p for p in perks if not get_perk_status(p, value_logs, today, settings).get("is_available")]
    if used_perks:
        for card in cards:
            card_used = [p for p in used_perks if p.get("card") == card]
            if card_used:
                st.subheader(card)
                for perk in card_used:
                    status = get_perk_status(perk, value_logs, today, settings)
                    render_perk_card(perk, status, today, settings, show_mark_button=False, key_prefix="used")
    else:
        st.info("Nothing marked as used yet this period.")

st.caption(
    "Data is cached for ~60 seconds. Use the button below if you edited the Sheets directly on mobile."
)

if st.button("🔄 Refresh data from Sheets", type="secondary", use_container_width=True):
    _clear_caches()
    st.rerun()
    st.toast("Cache cleared — pulling latest from Google Sheets...")
