# credit-perk-guard

Personal credit card perk tracker and reminder system built with Grok Build.

Tracks benefits across Amex Platinum, Delta SkyMiles Platinum American Express, and Chase Freedom Flex.

Features:
- Flexible perk tracking with multiple reset types (calendar, quarterly, monthly, card anniversary)
- Monthly digest emails + urgent alerts
- Trip-aware suggestions (V1.5)
- Value logging and basic ROI reporting (V1.5)
- Google Sheets as the data backend
- Local Streamlit dashboard

## Tech Stack
- Python + Streamlit (dashboard)
- Google Sheets + gspread (data layer)
- Google Apps Script or PythonAnywhere (scheduled notifications)

## Getting Started

See AGENTS.md for development guidelines when using Grok Build.

## Setup

1. Clone the repo
2. Create a virtual environment and install requirements
3. Set up your Google Sheets and connect via gspread
4. Configure the scheduler (Apps Script or PythonAnywhere)

## Status

In active development with Grok Build.