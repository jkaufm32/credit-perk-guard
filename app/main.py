"""
PerkGuard — Main Streamlit Entry Point

Run with:
    streamlit run app/main.py

This file configures the app and defines the multipage navigation.
All heavy logic lives in app/pages/ and app/utils/.
"""

import streamlit as st

# Page config must be first Streamlit command
st.set_page_config(
    page_title="PerkGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Optional: load custom CSS (status colors, mobile tweaks)
try:
    with open(".streamlit/custom.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Define pages using the modern st.Page API (Streamlit >= 1.28)
pages = [
    st.Page("pages/01_Dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("pages/02_Trips.py", title="Trips", icon="✈️"),
    st.Page("pages/03_History.py", title="History & Value", icon="📈"),
    st.Page("pages/04_Settings.py", title="Settings & Connection", icon="⚙️"),
]

pg = st.navigation(pages)
pg.run()
