"""
Settings & Connection Page

View/edit key configuration, test the Google Sheets connection,
and (in the future) trigger re-seeding or other maintenance actions.
"""

import streamlit as st

from app.utils.sheets_client import get_connection_status, get_settings

st.title("⚙️ Settings & Connection")

st.subheader("Google Sheets Connection")

status = get_connection_status()
if status.get("ok"):
    st.success("✅ Connected successfully")
    st.write(f"**Spreadsheet:** {status.get('title')}")
    st.write(f"**Worksheets:** {', '.join(status.get('worksheets', []))}")
    st.markdown(f"[Open in Google Sheets]({status.get('url')})")
else:
    st.error("❌ Connection failed")
    st.code(status.get("error", "Unknown error"))

st.divider()

st.subheader("Current Settings (from Google Sheet)")
settings = get_settings()
if settings:
    st.json(settings)
else:
    st.warning("No settings row found. Re-run the seed script.")

st.divider()

st.subheader("Next Steps (V1)")
st.markdown("""
1. Update your real email and anniversary months in the **Settings** worksheet.
2. Re-run the seeder if you want fresh sample data:  
   `python scripts/seed_sheets.py --sheet-url "..." --reset`
3. Configure the sheet ID in `.streamlit/secrets.toml` for the dashboard:
   ```toml
   [perkguard]
   sheet_id = "YOUR_SHEET_ID_HERE"
   ```
""")

st.caption("More settings (alert thresholds, digest preferences, etc.) will be editable directly from this page in later versions.")
