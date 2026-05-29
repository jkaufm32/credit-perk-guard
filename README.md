# PerkGuard — Credit Card Perk Tracker

**Never miss a valuable statement credit, companion certificate, quarterly activation, or monthly benefit again.**

PerkGuard is a personal, reliable system for tracking perks across three specific cards:

- American Express Platinum
- Delta SkyMiles Platinum American Express
- Chase Freedom Flex

It uses **Google Sheets as the single source of truth** (easy to edit on your phone) + a local Streamlit dashboard + cloud notifications that keep working even when your computer is off.

---

## Features (V1 + V1.5 Delivered)

**Core (V1)**
- Live perk status computed from usage history (no fragile "used" flags)
- Support for all major reset types: calendar year, quarterly, monthly, card anniversary, semi-annual
- Fast "Mark as Used + Log Value" flow that writes directly to Google Sheets
- Clean, dark-mode friendly dashboard with status pills and expiring-soon alerts

**V1.5**
- Trip management + trip-aware suggestions in the dashboard
- Link trips when logging value (see exactly which perks paid for which trips)
- Smart suggestions engine (Companion Certificate before domestic Delta trips, hotel credits before international travel, Chase activation reminders, etc.)

**Notifications (Cloud-First)**
- **Google Apps Script** monthly digest on the 1st (recommended — zero hosting cost, extremely reliable)
- Python alternative for PythonAnywhere / cron
- Both use the same core logic as the dashboard

---

## Tech Stack

- **Dashboard**: Streamlit (local, beautiful, mobile-usable)
- **Data**: Google Sheets + gspread (single source of truth)
- **Notifications**: Google Apps Script (primary) or Python script
- **Language**: Python 3.11+ with full type hints

---

## Quick Start (15–30 minutes to a working system)

### 1. Clone & Install

```bash
git clone https://github.com/yourname/credit-perk-guard.git
cd credit-perk-guard
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Create Your Google Sheet

1. Create a brand new Google Spreadsheet.
2. Name the tabs exactly (or let the seeder create them):
   - `Perks`
   - `Trips`
   - `ValueLogs`
   - `Enrollments`
   - `Settings`

### 3. Create a Google Service Account (one-time)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project → Enable **Google Sheets API** (and Drive API if you want).
3. Create a **Service Account** → Create a JSON key → Download it.
4. **Rename** the file `service-account-key.json` and place it in the repo root (it is already gitignored).

5. Share your Google Sheet with the service account's `client_email` (edit access).

### 4. Seed Realistic Sample Data

```bash
# Using the sheet URL
python scripts/seed_sheets.py --sheet-url "https://docs.google.com/spreadsheets/d/YOUR_ID_HERE/edit"

# Or set the env var once
export PERKGUARD_SHEET_ID="YOUR_ID_HERE"
python scripts/seed_sheets.py
```

This creates ~25 realistic 2026 perks with correct reset behavior for all three cards.

### 5. Configure the Dashboard

Create `.streamlit/secrets.toml`:

```toml
[perkguard]
sheet_id = "YOUR_SHEET_ID_HERE"

[gcp_service_account]
# Paste the entire contents of your service-account-key.json here
# (or keep using the local JSON file — the client supports both)
```

### 6. Run the Dashboard

```bash
streamlit run app/main.py
```

You now have a fully working local dashboard that can mark perks used and log value.

### 7. Set Up Cloud Notifications (the part that works when your laptop is off)

**Recommended path (Google Apps Script — 5 minutes):**

See the complete guide: [automation/apps_script/README.md](automation/apps_script/README.md)

In short:
- Open your Sheet → Extensions → Apps Script
- Paste `automation/apps_script/Code.gs`
- Run `sendDigestNow` once (authorize)
- Create a monthly time-driven trigger for the 1st

You will receive a beautiful digest email on the 1st of every month forever.

---

## Project Structure

```
app/
├── main.py                 # Streamlit entry + navigation
├── pages/
│   ├── 01_Dashboard.py     # Main working V1 + V1.5 UI
│   ├── 02_Trips.py
│   ├── 03_History.py
│   └── 04_Settings.py
└── utils/
    ├── sheets_client.py    # gspread + auth + helpers (cached)
    ├── date_utils.py       # All reset logic (pure, testable)
    └── suggestions.py      # V1.5 trip-aware suggestions

automation/
├── monthly_digest.py       # Python alternative (dry-run ready)
└── apps_script/
    ├── Code.gs             # Production cloud digest
    └── README.md           # Exact setup instructions

scripts/
└── seed_sheets.py          # The hero onboarding tool

data/
└── seed_perks.py           # Realistic 2026 sample data for 3 cards

docs/
├── sheets-schema.md        # The canonical data model reference
└── architecture.md
```

---

## Development Notes

See [AGENTS.md](AGENTS.md) for the full set of guidelines (plan mode for new features, type hints, separation of concerns, etc.).

Key principles followed:
- Google Sheets is the source of truth
- All status is computed live from append-only logs
- Cloud notifications are independent and reliable
- Low friction for daily mobile use

---

## Status (as of late May 2026)

**V1 + V1.5 complete and usable today**:
- Working dashboard with real writes
- Full reset-type support + correct 2026 sample data
- Working cloud monthly digest via Google Apps Script
- Trip linking + suggestion engine live in the UI

V2 scaffolding (enrollments UI + richer reports) is the logical next increment.

---

Built with care using Grok Build following the project's own AGENTS.md.
