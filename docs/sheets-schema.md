# PerkGuard Google Sheets Schema

This document is the **single source of truth** for the Google Sheets data model used by PerkGuard.

All worksheets live in **one Google Spreadsheet**. The Streamlit dashboard and the notification scripts (Apps Script + Python) read and write against this structure.

---

## 1. `Perks` (Core Benefit Definitions)

This sheet defines every perk you want to track. Most fields are static; a few (notes, is_active) are user-editable on mobile.

| Column                | Type     | Required | Description / Example |
|-----------------------|----------|----------|-----------------------|
| `perk_id`             | string   | Yes      | Stable unique slug, e.g. `amex_plat_airline_2026`, `delta_companion_2026`. Never change after creation. |
| `card`                | string   | Yes      | One of: `Amex Platinum`, `Delta SkyMiles Platinum American Express`, `Chase Freedom Flex` |
| `name`                | string   | Yes      | User-facing name shown in dashboard & emails, e.g. "$200 Airline Incidental Credit" |
| `category`            | string   | Yes      | Airline, Hotel, Dining, Entertainment, Travel, Rideshare, Shopping, Other |
| `reset_type`          | string   | Yes      | `calendar_year`, `quarterly`, `monthly`, `card_anniversary`, `semi_annual`, `one_time`, `custom` |
| `reset_anchor`        | string   | Yes      | Controls when the period resets. See "Reset Anchor Rules" below. |
| `max_value`           | number   | Yes      | Dollar amount, certificate count, or activation cap (e.g. 200, 100, 1, 1500) |
| `value_unit`          | string   | Yes      | `USD`, `certificate`, `activation` |
| `enrollment_required` | boolean  | Yes      | `TRUE` or `FALSE` |
| `notes`               | string   | No       | Free text. Good place for "Selected AA for 2026", airline choice, enrollment status notes, etc. Editable on mobile. |
| `is_active`           | boolean  | Yes      | `TRUE` to show in dashboard and digests. Set `FALSE` to hide retired benefits without deleting history. |
| `created_at`          | datetime | Yes      | ISO timestamp when row was first seeded |
| `updated_at`          | datetime | Yes      | Last time any field (especially notes) was changed |

### Reset Anchor Rules (critical for date_utils)

- `calendar_year` → `01-01` (or any date in Jan). Resets every January 1.
- `quarterly` → `Q1`, `Q2`, `Q3`, `Q4`. Quarters are calendar (Jan-Mar, Apr-Jun, etc.).
- `monthly` → `01` (or day of month). Resets on that day each month.
- `card_anniversary` → `anniv`. Uses the corresponding `_anniversary_month` from the **Settings** sheet.
- `semi_annual` → `H1` (Jan 1 – Jun 30) or `H2` (Jul 1 – Dec 31).
- `one_time` → Any value. Never automatically resets (Global Entry, lifetime credits, etc.).
  **Special case supported**: You may store a hard expiry date as `YYYY-MM-DD` here for limited-time benefits (e.g. a 2025 Companion Certificate that expires on a specific date). `date_utils` will treat it as the effective deadline for status and expiring calculations.
- `custom` → Free-form string (advanced; implement specific logic in date_utils when needed).
  Same hard-expiry date convention as `one_time` is supported.

**Computed (never stored in this sheet)**:
- Current period key (e.g. `2026-Q2`, `2026-05`, `2026-05-anniv`)
- Whether the perk is still available in the current period (derived from `ValueLogs`)
- Days until end of current period

---

## 2. `Trips`

Used for V1.5 trip-aware suggestions and value attribution.

| Column            | Type     | Required | Notes |
|-------------------|----------|----------|-------|
| `trip_id`         | string   | Yes      | Stable slug, e.g. `trip_2026_june_lax` |
| `name`            | string   | Yes      | "NYC → LAX June 2026" |
| `start_date`      | date     | Yes      | ISO `YYYY-MM-DD` |
| `end_date`        | date     | Yes      | ISO `YYYY-MM-DD` |
| `destination_type`| string   | No       | Domestic, International, Hawaii, etc. (drives suggestion rules) |
| `notes`           | string   | No       | "Good Companion Certificate candidate" |
| `created_at`      | datetime | Yes      | |

---

## 3. `ValueLogs` (Append-Only History — Source of Truth)

**Never edit or delete rows** after they are written (except for obvious typos in notes). This is the audit log that powers "available" status, YTD value captured, and reporting.

| Column           | Type     | Required | Description |
|------------------|----------|----------|-------------|
| `log_id`         | string   | Yes      | Unique (UUID or timestamp-based) |
| `timestamp`      | datetime | Yes      | When the log entry was created |
| `perk_id`        | string   | Yes      | FK to Perks.perk_id |
| `period_key`     | string   | Yes      | e.g. `2026-Q2`, `2026-05-anniv`. Computed at write time by the dashboard. |
| `used_date`      | date     | Yes      | Date the benefit was actually used (user input) |
| `value_captured` | number   | Yes      | Actual dollar amount or 1 for certificate/activation |
| `trip_id`        | string   | No       | Optional link to Trips.trip_id |
| `notes`          | string   | No       | "Used for flight to LAX", "Partial $87 of $200" |
| `source`         | string   | Yes      | `dashboard` or `manual` |

**Key rule**: A perk is considered "used this period" if there is **at least one** row in ValueLogs matching `perk_id` + current `period_key`.

---

## 4. `Enrollments` (V2 — Scaffold in V1)

Tracks enrollment status for benefits that require annual or one-time enrollment (Resy, lululemon, airline selection, etc.).

| Column         | Type     | Required |
|----------------|----------|----------|
| `perk_id`      | string   | Yes      |
| `status`       | string   | Yes      | `enrolled`, `not_enrolled`, `pending` |
| `enrolled_date`| date     | No       |
| `details`      | string   | No       | "Airline: American", "Selected for 2026" |
| `notes`        | string   | No       |

The V1 dashboard can show a simple "Enrollment" badge; full management UI comes in V2.

---

## 5. `Settings` (Single-Row or Key/Value)

Simple configuration that both the dashboard and notification scripts need.

Recommended layout (one row, many columns):

| Column                        | Example Value          | Purpose |
|-------------------------------|------------------------|-------|
| `user_email`                  | you@gmail.com          | Recipient for monthly digest & alerts |
| `digest_day`                  | 1                      | Day of month to send monthly digest |
| `urgent_alert_days`           | 14,30                  | Comma-separated list of days-before-expiry for urgent emails |
| `amex_anniversary_month`      | 5                      | 1-12. Used for any `card_anniversary` perks on Amex Platinum |
| `delta_anniversary_month`     | 6                      | Used for Delta Companion Certificate |
| `chase_anniversary_month`     | (optional)             | Rarely needed |
| `default_currency`            | USD                    | Future-proofing |
| `suggestion_lookahead_days`   | 90                     | How far ahead the dashboard & digest look for trips when generating suggestions |

Apps Script can read these values easily via `SpreadsheetApp`.

---

## How "Available" Status Is Computed (Important)

The `Perks` sheet does **not** contain a `status` or `used` column that the UI trusts.

Instead, at runtime:

1. Determine today's date.
2. For each perk, calculate its `current_period_key` using `reset_type` + `reset_anchor` + the relevant anniversary month from Settings.
3. Query `ValueLogs` for any rows with matching `perk_id` + `current_period_key`.
4. If ≥1 row exists → the perk is **used this period**.
5. If 0 rows → the perk is **available**.
6. Also compute `days_until_period_end` to decide "expiring soon".

This design is resilient to manual edits on mobile and gives full historical auditability.

---

## Adding a New Custom Perk (Mobile-Friendly)

1. Add a new row at the bottom of the `Perks` sheet.
2. Fill all required columns (copy an existing similar row as template).
3. Set `is_active = TRUE`.
4. The dashboard will pick it up on next load (or after cache clear).

You can also add rows via the Streamlit UI in later versions.

---

## Backup & Safety

- Google Sheets revision history is your friend.
- Do not delete rows from `ValueLogs`.
- Keep a "PerkGuard Archive" copy of the entire spreadsheet monthly if you are risk-averse.

---

## Version History of This Schema

- 2026-05-28: Initial version created during V1 foundation work.

When you make breaking changes, append a new dated section here and consider adding a `schema_version` cell in the Settings sheet.

---

**Next steps after reading this doc**:
- Run `python scripts/seed_sheets.py` against a fresh spreadsheet (see setup instructions in the main README).
- Then open the Streamlit dashboard.
