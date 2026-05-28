# AGENTS.md - credit-perk-guard

## Project Overview
Personal credit card perk tracking and reminder system for three cards:
- Amex Platinum
- Delta SkyMiles Platinum American Express
- Chase Freedom Flex

Goal: Never miss valuable statement credits, companion certificates, quarterly activations, or monthly benefits. Provide monthly digests and smart trip-aware suggestions.

## Tech Stack & Architecture
- **Dashboard**: Streamlit (local, beautiful UI)
- **Data Layer**: Google Sheets (single source of truth, easy mobile editing) + gspread
- **Scheduler / Notifications**: Google Apps Script (preferred) or Python script on PythonAnywhere for monthly digests + urgent alerts
- **Language**: Python 3.11+

## Key Principles
- Keep it simple and maintainable
- Prioritize reliability of notifications (they must work even if local machine is off)
- Make data easy to edit on mobile
- Use plan mode for larger changes or new features
- Separate concerns: app/ for dashboard, automation/ for scheduler scripts

## Coding Guidelines
- Use type hints
- Prefer clear function and variable names
- Keep Google Sheets integration clean and well-documented
- For the scheduler, make it easy to switch between Apps Script and PythonAnywhere
- Never store sensitive card numbers or credentials in code (use env vars / secrets)

## Development Workflow with Grok Build
1. Always start in plan mode for new features or refactors
2. Review diffs carefully before approving
3. After changes, test locally with `streamlit run app/app.py`
4. Update AGENTS.md and README.md when architecture changes
5. Use `github___create_or_update_file` style thinking when modifying remote files if needed

## Folder Structure
- `app/` → Streamlit dashboard code
- `automation/` → Scheduler / notification scripts
- `data/` → Sample data and templates
- `docs/` → Architecture and planning docs

## Current Focus (as of May 2026)
Building V1 + V1.5 features:
- Core perk tracking + monthly digest
- Trip suggestions
- Value logging and basic reporting

## Future / V2 Ideas
- Enrollment status tracking
- Historical value reports
- More polished emails

## Important Notes
- The monthly digest and alerts run independently in the cloud
- Google Sheets is the source of truth
- Keep the system low-friction so it actually gets used