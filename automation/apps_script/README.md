# PerkGuard — Google Apps Script Monthly Digest Setup

This is the **recommended production path** for reliable notifications that run even when your computer is completely off.

The script sends a clean monthly digest email on the 1st of every month (and supports manual testing).

---

## 5-Minute Setup (One Time)

1. **Open your PerkGuard Google Sheet**

2. **Go to Extensions → Apps Script**

3. **Delete all default code** in the editor.

4. **Paste the entire contents** of `Code.gs` (the file next to this README).

5. **Save the project** (give it a nice name like "PerkGuard Digest").

6. **Run a test immediately**:
   - In the function dropdown at the top, select `sendDigestNow`
   - Click the ▶️ Run button
   - First time only: authorize the script (it only needs access to the Sheet you opened it from + Gmail to send email)
   - Check your inbox — you should receive a digest within a minute

7. **Create the monthly trigger**:
   - Click the **clock icon** (Triggers) in the left sidebar
   - Click **+ Add Trigger** (bottom right)
   - Choose function: `sendMonthlyDigest`
   - Choose deployment: `Head` (default)
   - Event source: **Time-driven**
   - Time-based trigger type: **Month timer**
   - Day of month: **1**
   - Time of day: pick a convenient window (e.g. 8am–9am)
   - Failure notification: your email (default is fine)
   - Click **Save**

That's it. The digest will now arrive automatically on the 1st of every month.

---

## Recommended Script Properties (Strongly Suggested)

Instead of hard-coding values, store them in the script:

1. In Apps Script, click the **gear icon** (Project Settings) on the left.
2. Scroll to **Script Properties**.
3. Add these two properties:

| Property Name       | Example Value                              | Purpose |
|---------------------|--------------------------------------------|---------|
| `SHEET_ID`          | `1AbCdEfG...` (the long ID from your sheet URL) | Tells the script exactly which spreadsheet to read |
| `RECIPIENT_EMAIL`   | `you@gmail.com`                            | Who receives the digest (defaults to script owner if omitted) |

These are much safer and easier to change than editing the code later.

---

## What the Email Contains (V1)

- Available perks this period (with rough value caps)
- Perks expiring within 30 days
- Recently used perks (this period)
- Simple trip-aware suggestions (when you have trips in the Trips sheet)
- Direct link back to your Google Sheet

The logic is intentionally kept simple and self-contained so the Apps Script never depends on any external Python code or hosting.

---

## Updating the Script Later

1. Make your changes in `Code.gs`
2. Paste the new version into the Apps Script editor
3. Save
4. Run `sendDigestNow` again to test
5. The existing time-driven trigger will automatically use the new code

---

## Troubleshooting

| Problem                        | Fix |
|--------------------------------|-----|
| "You do not have permission"   | Re-run the script manually once and re-authorize |
| Email never arrives            | Check spam, or run `sendDigestNow` and look at the Execution Log (bug icon) |
| Wrong / missing data           | Verify the exact worksheet names match (`Perks`, `ValueLogs`, `Settings`, etc.) |
| Trigger not firing             | Check Triggers list — make sure it's still enabled and points to `sendMonthlyDigest` |
| "SHEET_ID not found"           | Add the `SHEET_ID` Script Property as described above |

---

## Alternative: PythonAnywhere / Local Python

If you ever prefer (or need) a Python-based scheduler instead of Apps Script, see the sibling file:

`automation/monthly_digest.py`

It can produce an identical (or richer) digest using the same Python logic as the Streamlit app.

Most users should start with the Apps Script path — it is the lowest-friction, most reliable option for this use case.

---

## Security Note

The script only ever reads your PerkGuard sheet and sends email via your own Gmail account using `MailApp`. It never phones home or stores any data outside your Google account.

---

**You now have a working, cloud-hosted monthly reminder system.**  
Combine this with the local Streamlit dashboard and you have the complete V1 PerkGuard experience.
