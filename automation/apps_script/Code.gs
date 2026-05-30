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

    // Apply the same relevance filter as the dashboard:
    // Hide H2 during H1 (and vice versa), hide non-current quarterly perks, etc.
    if (!isPerkCurrentlyRelevant(perk, today)) return;

    const periodKey = computePeriodKey(perk, today, settings);
    const hasUsage = valueLogs.some(log =>
      log.perk_id === perk.perk_id && log.period_key === periodKey
    );

    const daysLeft = computeDaysUntilReset(perk, today, settings);

    const enriched = { ...perk, period_key: periodKey, days_left: daysLeft };

    // Determine expiring threshold
    // Monthly perks only appear in "Expiring Soon" in the last 10 days of the month
    // (to avoid them dominating the list for most of the month)
    let expiringThreshold = 30;
    if (perk.reset_type === 'monthly') {
      expiringThreshold = 10;
    }

    if (hasUsage) {
      usedThisPeriod.push(enriched);
    } else {
      available.push(enriched);
      if (daysLeft > 0 && daysLeft <= expiringThreshold) {
        expiring.push(enriched);
      }
    }
  });

  // Simple trip-aware suggestions (V1 version — rule based)
  const suggestions = generateSimpleSuggestions(available, trips, today);

  // Compute quick stats for the email header
  const totalRelevant = available.length + usedThisPeriod.length;
  const usedCount = usedThisPeriod.length;
  const availableCount = available.length;
  const expiringCount = expiring.length;
  const usedPercent = totalRelevant > 0 ? Math.round((usedCount / totalRelevant) * 100) : 0;

  const html = buildHtmlEmail({
    today,
    available,
    expiring,
    usedThisPeriod,
    suggestions,
    settings,
    stats: {
      total: totalRelevant,
      used: usedCount,
      available: availableCount,
      expiring: expiringCount,
      usedPercent,
    },
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

function isPerkCurrentlyRelevant(perk, today) {
  // Mirrors the Python is_perk_currently_relevant logic for dashboard + digest
  const resetType = perk.reset_type;
  const anchor = (perk.reset_anchor || '').toUpperCase().trim();

  if (resetType === 'semi_annual') {
    const currentHalf = (today.getMonth() + 1) <= 6 ? 'H1' : 'H2';
    return anchor === currentHalf;
  }

  if (resetType === 'quarterly') {
    const currentQ = 'Q' + Math.floor(today.getMonth() / 3 + 1);
    return anchor === currentQ;
  }

  if (resetType === 'monthly') {
    return true; // Monthly benefits are always relevant
  }

  return true;
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
  const { today, available, expiring, usedThisPeriod, suggestions, settings, stats } = data;

  const fmt = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  // Stats header
  let statsHtml = '';
  if (stats) {
    statsHtml = `
      <table width="100%" style="background:#f8fafc; border-radius:10px; margin:16px 0; border:1px solid #e2e8f0;" cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding:12px 16px; text-align:center; border-right:1px solid #e2e8f0;">
            <div style="font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">Tracked</div>
            <div style="font-size:22px; font-weight:700; color:#0f172a; line-height:1.1;">${stats.total}</div>
          </td>
          <td style="padding:12px 16px; text-align:center; border-right:1px solid #e2e8f0;">
            <div style="font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">Used</div>
            <div style="font-size:22px; font-weight:700; color:#166534; line-height:1.1;">${stats.used} <span style="font-size:12px; color:#64748b;">(${stats.usedPercent}%)</span></div>
          </td>
          <td style="padding:12px 16px; text-align:center; border-right:1px solid #e2e8f0;">
            <div style="font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">Available</div>
            <div style="font-size:22px; font-weight:700; color:#1e40af; line-height:1.1;">${stats.available}</div>
          </td>
          <td style="padding:12px 16px; text-align:center;">
            <div style="font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;">Expiring Soon</div>
            <div style="font-size:22px; font-weight:700; color:#b45309; line-height:1.1;">${stats.expiring}</div>
          </td>
        </tr>
      </table>
    `;
  }

  let html = `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 620px; margin: 0 auto; color: #1f2937; padding: 0 12px; background:#ffffff;">
      <div style="padding-top: 8px;">
        <h1 style="color: #0f172a; margin:0 0 4px 0; font-size:24px; font-weight:700;">🛡️ PerkGuard</h1>
        <p style="color:#475569; margin:0; font-size:14px;">Monthly Digest — ${fmt(today)}</p>
      </div>

      ${statsHtml}
  `;

  if (available.length === 0) {
    html += `<p style="color:#666;">All tracked perks have been used this period. Great job!</p>`;
  } else {
    available.slice(0, 12).forEach(p => {
      const val = p.max_value ? ` (up to $${p.max_value})` : '';
      html += `
        <div style="margin:6px 0; padding:12px 14px; background:#f8fafc; border-radius:8px; border:1px solid #e2e8f0;">
          <div style="font-weight:600; color:#0f172a; font-size:14px;">${p.name}</div>
          <div style="font-size:12px; color:#475569; margin-top:3px;">${p.card}${val}</div>
          <div style="font-size:11px; color:#64748b; margin-top:2px;">Resets: ${p.period_key || '—'}</div>
        </div>`;
    });
    if (available.length > 12) html += `<p style="font-size:12px; color:#888; margin-top:4px;">+ ${available.length - 12} more available…</p>`;
  }

  if (expiring.length > 0) {
    html += `<h2 style="color:#b45309; margin-top:28px; margin-bottom:8px;">⏰ Expiring Soon (≤30 days)</h2>`;
    expiring.forEach(p => {
      html += `
        <div style="margin:4px 0; padding:8px 12px; background:#fefce8; border-left:4px solid #f59e0b; border-radius:6px; color:#92400e;">
          <strong>${p.name}</strong> — ${p.days_left} days left
        </div>`;
    });
  }

  if (usedThisPeriod.length > 0) {
    html += `<h2 style="color:#166534; margin-top:28px; margin-bottom:8px;">✅ Used This Period</h2>`;
    usedThisPeriod.slice(0, 8).forEach(p => {
      html += `<div style="margin:3px 0; color:#166534;">• ${p.name}</div>`;
    });
  }

  if (suggestions && suggestions.length) {
    html += `<h2 style="margin-top:28px; margin-bottom:8px;">💡 Smart Suggestions</h2>`;
    suggestions.forEach(s => {
      html += `<div style="margin:6px 0; padding:10px 14px; background:#fefce8; border-left:4px solid #ca8a04; border-radius:6px; color:#713f12;">${s}</div>`;
    });
  }

  html += `
      <hr style="margin:40px 0 16px; border:none; border-top:1px solid #e2e8f0;">
      <p style="font-size:11px; color:#64748b; line-height:1.5;">
        Generated by PerkGuard • 
        <a href="https://docs.google.com/spreadsheets/d/${getSpreadsheetIdForLink()}" style="color:#64748b;">Open your sheet</a><br>
        View full dashboard: <code>streamlit run app/main.py</code>
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
