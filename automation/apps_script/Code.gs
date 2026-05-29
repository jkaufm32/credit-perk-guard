/**
 * PerkGuard Monthly Digest — Google Apps Script
 *
 * This standalone script reads your PerkGuard Google Sheet and sends a
 * beautiful monthly digest email on the 1st of each month (or on demand).
 *
 * SETUP (5 minutes):
 *   1. In your Google Sheet, go to Extensions → Apps Script.
 *   2. Delete the default code and paste everything from this file.
 *   3. Save the project (give it a name like "PerkGuard Digest").
 *   4. Run "sendDigestNow" once manually (it will ask for authorization — grant it).
 *   5. Go to Triggers (clock icon) → Add Trigger:
 *        - Choose "sendMonthlyDigest"
 *        - Event source: Time-driven
 *        - Type: Month timer → Day of month: 1 → Time: 8am–9am (or whenever you like)
 *   6. (Optional but recommended) Set Script Properties:
 *        - Go to Project Settings (gear) → Script Properties
 *        - Add: SHEET_ID = your spreadsheet ID (the long string in the URL)
 *        - Add: RECIPIENT_EMAIL = your-email@gmail.com (falls back to session user)
 *
 * The script uses the same 5 worksheets as the Streamlit app.
 * It implements simplified but effective period/availability logic in JS.
 */

// ---------------------------------------------------------------------------
// Configuration (edit via Script Properties or hardcode for testing)
// ---------------------------------------------------------------------------
const SHEET_ID_PROP = 'SHEET_ID';
const RECIPIENT_PROP = 'RECIPIENT_EMAIL';

// ---------------------------------------------------------------------------
// Main Entry Points
// ---------------------------------------------------------------------------

/**
 * Time-driven trigger target. Runs automatically on the 1st.
 */
function sendMonthlyDigest() {
  const digest = buildDigest();
  sendEmail(digest);
  console.log('Monthly digest sent successfully.');
}

/**
 * Manual trigger — use this from the Apps Script editor to test instantly.
 * It will send the digest to the configured recipient (or you).
 */
function sendDigestNow() {
  const digest = buildDigest();
  sendEmail(digest, /* forceSend */ true);
  console.log('Test digest sent. Check your inbox.');
}

// ---------------------------------------------------------------------------
// Core Logic
// ---------------------------------------------------------------------------

function buildDigest() {
  const ss = getSpreadsheet();
  const perks = getPerks(ss);
  const valueLogs = getValueLogs(ss);
  const settings = getSettings(ss);
  const trips = getTrips(ss);

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1; // 1-12

  // Compute availability using the same mental model as the Python date_utils
  const available = [];
  const expiring = [];
  const usedThisPeriod = [];

  perks.forEach(perk => {
    if (!perk.is_active) return;

    const periodKey = computePeriodKey(perk, today, settings);
    const hasUsage = valueLogs.some(log =>
      log.perk_id === perk.perk_id && log.period_key === periodKey
    );

    const daysLeft = computeDaysUntilReset(perk, today, settings);

    const enriched = { ...perk, period_key: periodKey, days_left: daysLeft };

    if (hasUsage) {
      usedThisPeriod.push(enriched);
    } else {
      available.push(enriched);
      if (daysLeft > 0 && daysLeft <= 30) {
        expiring.push(enriched);
      }
    }
  });

  // Simple trip-aware suggestions (V1 version — rule based)
  const suggestions = generateSimpleSuggestions(available, trips, today);

  const html = buildHtmlEmail({
    today,
    available,
    expiring,
    usedThisPeriod,
    suggestions,
    settings,
  });

  const subject = `PerkGuard Digest — ${today.toLocaleString('default', { month: 'long' })} ${year}`;

  return { subject, html };
}

function sendEmail(digest, forceSend = false) {
  const recipient = getRecipient();
  if (!recipient && !forceSend) {
    console.log('No recipient configured and not forcing send. Aborting.');
    return;
  }

  const to = recipient || Session.getActiveUser().getEmail();

  MailApp.sendEmail({
    to: to,
    subject: digest.subject,
    htmlBody: digest.html,
  });
}

// ---------------------------------------------------------------------------
// Data Access
// ---------------------------------------------------------------------------

function getSpreadsheet() {
  const id = PropertiesService.getScriptProperties().getProperty(SHEET_ID_PROP);
  if (id) {
    return SpreadsheetApp.openById(id);
  }
  // Fallback: assume the script is bound to the sheet (rare for standalone)
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss) return ss;

  throw new Error('No SHEET_ID found in Script Properties and no active spreadsheet. Set SHEET_ID property.');
}

function getPerks(ss) {
  const sheet = ss.getSheetByName('Perks');
  if (!sheet) return [];
  const data = sheet.getDataRange().getValues();
  const headers = data.shift();
  return data.map(row => {
    const obj = {};
    headers.forEach((h, i) => obj[h] = row[i]);
    // Normalize booleans
    obj.is_active = String(obj.is_active).toUpperCase() === 'TRUE';
    obj.enrollment_required = String(obj.enrollment_required).toUpperCase() === 'TRUE';
    return obj;
  });
}

function getValueLogs(ss) {
  const sheet = ss.getSheetByName('ValueLogs');
  if (!sheet) return [];
  const data = sheet.getDataRange().getValues();
  const headers = data.shift();
  return data.map(row => {
    const obj = {};
    headers.forEach((h, i) => obj[h] = row[i]);
    return obj;
  });
}

function getSettings(ss) {
  const sheet = ss.getSheetByName('Settings');
  if (!sheet) return {};
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const values = data[1] || [];
  const obj = {};
  headers.forEach((h, i) => obj[h] = values[i]);
  return obj;
}

function getTrips(ss) {
  const sheet = ss.getSheetByName('Trips');
  if (!sheet) return [];
  const data = sheet.getDataRange().getValues();
  const headers = data.shift();
  return data.map(row => {
    const obj = {};
    headers.forEach((h, i) => obj[h] = row[i]);
    return obj;
  });
}

function getRecipient() {
  const prop = PropertiesService.getScriptProperties().getProperty(RECIPIENT_PROP);
  if (prop) return prop;
  // Last resort — the owner of the script
  return Session.getActiveUser().getEmail();
}

// ---------------------------------------------------------------------------
// Period Math (simplified JS version of Python date_utils)
// ---------------------------------------------------------------------------

function computePeriodKey(perk, today, settings) {
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const type = perk.reset_type || 'calendar_year';

  if (type === 'calendar_year') return `${year}-calendar`;
  if (type === 'quarterly') {
    const q = Math.floor((month - 1) / 3) + 1;
    return `${year}-Q${q}`;
  }
  if (type === 'monthly') return `${year}-${String(month).padStart(2, '0')}`;
  if (type === 'card_anniversary') {
    const anniv = getAnniversaryMonth(perk.card, settings);
    const periodYear = month >= anniv ? year : year - 1;
    return `${periodYear}-${String(anniv).padStart(2, '0')}-anniv`;
  }
  if (type === 'semi_annual') {
    const half = month <= 6 ? 'H1' : 'H2';
    return `${year}-${half}`;
  }
  return `${year}-custom`;
}

function computeDaysUntilReset(perk, today, settings) {
  const end = getPeriodEndDate(perk, today, settings);
  const diff = Math.ceil((end.getTime() - today.getTime()) / (1000 * 3600 * 24));
  return Math.max(0, diff);
}

function getPeriodEndDate(perk, today, settings) {
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const type = perk.reset_type || 'calendar_year';

  if (type === 'calendar_year') return new Date(year, 11, 31);
  if (type === 'quarterly') {
    const qEndMonth = Math.ceil(month / 3) * 3;
    return new Date(year, qEndMonth, 0); // last day of month
  }
  if (type === 'monthly') {
    return new Date(year, month, 0);
  }
  if (type === 'card_anniversary') {
    const anniv = getAnniversaryMonth(perk.card, settings);
    const periodYear = month >= anniv ? year : year - 1;
    return new Date(periodYear, anniv, 0);
  }
  if (type === 'semi_annual') {
    return month <= 6 ? new Date(year, 5, 30) : new Date(year, 11, 31);
  }
  return new Date(year, 11, 31);
}

function getAnniversaryMonth(card, settings) {
  if (!settings) return 5;
  if (String(card).includes('Delta')) return Number(settings.delta_anniversary_month) || 6;
  if (String(card).includes('Amex')) return Number(settings.amex_anniversary_month) || 5;
  return 1;
}

// ---------------------------------------------------------------------------
// Simple Suggestion Engine (V1)
// ---------------------------------------------------------------------------

function generateSimpleSuggestions(availablePerks, trips, today) {
  const suggestions = [];

  // Delta Companion for any upcoming domestic trip
  const companion = availablePerks.find(p => p.perk_id && p.perk_id.includes('companion'));
  if (companion && trips.length > 0) {
    const hasDomestic = trips.some(t => String(t.destination_type || '').toLowerCase().includes('domestic'));
    if (hasDomestic) {
      suggestions.push('Your Delta Companion Certificate is available and you have an upcoming domestic trip — consider using it!');
    }
  }

  // Hotel credit for international trips
  const hotel = availablePerks.find(p => p.name && p.name.toLowerCase().includes('hotel'));
  if (hotel && trips.length > 0) {
    const hasIntl = trips.some(t => String(t.destination_type || '').toLowerCase().includes('international'));
    if (hasIntl) {
      suggestions.push('You have an international trip coming up and hotel credits available — look at Fine Hotels + Resorts.');
    }
  }

  // Chase activation reminder (very common)
  const chaseActivation = availablePerks.find(p => p.name && p.name.includes('5%') && p.name.includes('Activate'));
  if (chaseActivation) {
    suggestions.push('Remember to activate your Chase Freedom Flex 5% categories before the quarterly deadline.');
  }

  return suggestions.length ? suggestions : ['No urgent trip-based suggestions this month.'];
}

// ---------------------------------------------------------------------------
// Email HTML Builder
// ---------------------------------------------------------------------------

function buildHtmlEmail(data) {
  const { today, available, expiring, usedThisPeriod, suggestions, settings } = data;

  const fmt = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  let html = `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 620px; margin: 0 auto; color: #222;">
      <h1 style="color: #0f1116;">🛡️ PerkGuard Monthly Digest</h1>
      <p style="color:#555;">${fmt(today)} • Your benefits at a glance</p>

      <h2 style="color:#0f1116; border-bottom:1px solid #eee; padding-bottom:6px;">Available Now (${available.length})</h2>
  `;

  if (available.length === 0) {
    html += `<p style="color:#666;">All tracked perks have been used this period. Great job!</p>`;
  } else {
    available.slice(0, 12).forEach(p => {
      const val = p.max_value ? ` (up to $${p.max_value})` : '';
      html += `<div style="margin:8px 0; padding:8px 12px; background:#f8f9fa; border-radius:6px;">
        <strong>${p.name}</strong>${val}<br>
        <span style="font-size:12px; color:#666;">${p.card} • ${p.period_key || ''}</span>
      </div>`;
    });
    if (available.length > 12) html += `<p style="font-size:12px; color:#888;">+ ${available.length - 12} more available…</p>`;
  }

  if (expiring.length > 0) {
    html += `<h2 style="color:#b45309; margin-top:24px;">⏰ Expiring Soon (≤30 days)</h2>`;
    expiring.forEach(p => {
      html += `<div style="margin:6px 0; color:#92400e;">• <strong>${p.name}</strong> — ${p.days_left} days left</div>`;
    });
  }

  if (usedThisPeriod.length > 0) {
    html += `<h2 style="color:#166534; margin-top:24px;">✅ Used This Period</h2>`;
    usedThisPeriod.slice(0, 6).forEach(p => {
      html += `<div style="margin:4px 0; color:#166534;">• ${p.name}</div>`;
    });
  }

  if (suggestions && suggestions.length) {
    html += `<h2 style="margin-top:28px;">💡 Smart Suggestions</h2>`;
    suggestions.forEach(s => {
      html += `<div style="margin:8px 0; padding:10px; background:#fefce8; border-left:4px solid #ca8a04; border-radius:4px;">${s}</div>`;
    });
  }

  html += `
      <hr style="margin:32px 0; border:none; border-top:1px solid #eee;">
      <p style="font-size:12px; color:#888;">
        Generated by PerkGuard • 
        <a href="https://docs.google.com/spreadsheets/d/${getSpreadsheetIdForLink()}" style="color:#888;">Open your sheet</a> • 
        Dashboard: run <code>streamlit run app/main.py</code>
      </p>
    </div>
  `;

  return html;
}

function getSpreadsheetIdForLink() {
  try {
    const id = PropertiesService.getScriptProperties().getProperty(SHEET_ID_PROP);
    return id || '';
  } catch (e) {
    return '';
  }
}
