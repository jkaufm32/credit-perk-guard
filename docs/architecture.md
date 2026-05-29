# PerkGuard Architecture (V1 + V1.5)

## High-Level Principles
- **Google Sheets is the single source of truth**. Everything else is a view or a delivery mechanism.
- Notifications must work independently of any local machine.
- All "is available" state is computed on the fly from an append-only `ValueLogs` sheet (never trust mutable flags).
- Keep the system low-friction so it actually gets used on a phone at 11pm.

## Core Components

### 1. Data Layer (Google Sheets)
5 worksheets (see `docs/sheets-schema.md` for the complete column contract):
- `Perks` — definitions + user notes
- `Trips` — upcoming travel (drives suggestions)
- `ValueLogs` — append-only history (the source of all truth for usage)
- `Enrollments` — V2 focus (light scaffolding exists)
- `Settings` — anniversary months, email, thresholds, etc.

### 2. Dashboard (Streamlit)
- `app/main.py` + multipage navigation
- `app/utils/sheets_client.py` — auth (service account via `st.secrets` or local JSON) + cached reads + writes
- `app/utils/date_utils.py` — pure functions for `calendar_year`, `quarterly`, `monthly`, `card_anniversary`, `semi_annual`
- `app/utils/suggestions.py` — rule-based trip-aware suggestions (V1.5)
- Real-time "Mark as Used" modal that writes a full `ValueLog` row (with optional trip link)

### 3. Notifications (Cloud-First)
**Primary (recommended)**: Google Apps Script
- `automation/apps_script/Code.gs` — self-contained reader + JS period math + HTML email via `MailApp`
- Time-driven trigger on the 1st (plus manual `sendDigestNow` for testing)
- Zero external dependencies or hosting

**Alternative**: Python
- `automation/monthly_digest.py` — reuses the exact same `date_utils` + `sheets_client` as the dashboard
- `--dry-run` by default; easy to wire real email later (PythonAnywhere, cron, etc.)

### 4. Onboarding / Bootstrap
- `scripts/seed_sheets.py` — the hero tool. Creates worksheets + populates ~25 realistic 2026 perks across the three cards with correct reset anchors.
- `data/seed_perks.py` — the actual seed definitions (easy to extend with custom perks).

## Auth & Secrets Model
- Dashboard: Google Service Account (least-privilege, works great with Streamlit secrets)
- Apps Script: Runs as the sheet owner (uses `SpreadsheetApp` + `MailApp` — no extra keys needed)
- Never commit credentials (`.gitignore` already covers `service-account-key.json`, `.env`, and `.streamlit/secrets.toml`)

## Key Design Decisions That Matter
- Append-only logs instead of mutating "used" columns → full audit history + correct partial-value support
- Date logic lives in one pure module (Python) + a mirrored simplified version in Apps Script JS
- Suggestions are intentionally rule-based and transparent (easy for the user to understand and trust)
- Mobile editing of notes is safe because status is never stored in the Perks sheet

## Extension Points for V2+
- Enrollments sheet + UI (already has light scaffolding)
- Richer History/Reports page with charts (pandas + plotly ready)
- More sophisticated suggestion rules or user-configurable weights
- Optional second notification channel (urgent alerts on a daily/weekly Apps Script trigger)

## Trade-offs Accepted
- Streamlit is "good enough" on mobile (not native-app quality)
- Apps Script email HTML is simpler than the Python version (acceptable for V1)
- Some duplication between Python date logic and the Apps Script version (intentional — the cloud path must never depend on external Python)

This architecture has proven reliable and low-friction in practice.
