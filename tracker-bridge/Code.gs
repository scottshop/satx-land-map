/**
 * San Antonio Land Map -> Land Deal Tracker bridge.
 *
 * Deploy as a Web App:
 * - Execute as: Me
 * - Who has access: Anyone
 *
 * The private TRACKER_KEY stays in Apps Script Script Properties and in the
 * user's browser localStorage. It is never committed to GitHub.
 */

const TRACKER_SPREADSHEET_ID = '1BUdhXHCmsmaTCWZI5mYTmlabQ7rePN7acsLsbLLZJzI';
const TRACKER_SHEET_NAME = 'Deals';
const FIRST_DATA_ROW = 4;
const LAST_TEMPLATE_ROW = 203;

function setupTrackerKey() {
  const key = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
  PropertiesService.getScriptProperties().setProperty('TRACKER_KEY', key);
  console.log('TRACKER_KEY=' + key);
  return key;
}

function doGet(e) {
  try {
    const p = (e && e.parameter) || {};
    if (clean_(p.action) !== 'trackerSites') {
      return json_({ ok: true, service: 'land-deal-tracker-bridge' });
    }

    const expected = PropertiesService.getScriptProperties().getProperty('TRACKER_KEY');
    if (!expected || !p.key || p.key !== expected) {
      return output_(p.callback, { ok: false, error: 'unauthorized' });
    }

    const ss = SpreadsheetApp.openById(TRACKER_SPREADSHEET_ID);
    const sheet = ss.getSheetByName(TRACKER_SHEET_NAME);
    if (!sheet) return output_(p.callback, { ok: false, error: 'Deals sheet not found' });

    const lastRow = Math.max(sheet.getLastRow(), FIRST_DATA_ROW - 1);
    if (lastRow < FIRST_DATA_ROW) {
      return output_(p.callback, {
        ok: true,
        sites: [],
        generatedAt: new Date().toISOString()
      });
    }

    const rows = sheet
      .getRange(FIRST_DATA_ROW, 1, lastRow - FIRST_DATA_ROW + 1, 14)
      .getDisplayValues();

    const sites = rows
      .map(function(r, i) {
        const stage = clean_(r[2]);
        const county = clean_(r[9]);
        const parcelId = clean_(r[10]);
        if (!county || !parcelId) return null;

        const stageLower = stage.toLowerCase();
        if (stageLower === 'closed' || stageLower === 'dead') return null;

        return {
          row: FIRST_DATA_ROW + i,
          dealSite: clean_(r[0]),
          acres: clean_(r[1]),
          stage: stage || 'Pursuing',
          nextAction: clean_(r[4]),
          nextActionDate: clean_(r[5]),
          owner: clean_(r[8]),
          county: county,
          parcelId: parcelId,
          mapLink: clean_(r[11])
        };
      })
      .filter(Boolean);

    return output_(p.callback, {
      ok: true,
      sites: sites,
      generatedAt: new Date().toISOString()
    });
  } catch (err) {
    const p = (e && e.parameter) || {};
    return output_(p.callback, {
      ok: false,
      error: String(err && err.message || err)
    });
  }
}

function doPost(e) {
  try {
    const p = (e && e.parameter) || {};
    const expected = PropertiesService.getScriptProperties().getProperty('TRACKER_KEY');
    if (!expected || !p.key || p.key !== expected) {
      return json_({ ok: false, error: 'unauthorized' });
    }

    const parcelId = clean_(p.parcelId);
    const county = clean_(p.county);
    if (!parcelId || !county) {
      return json_({ ok: false, error: 'missing parcelId/county' });
    }

    const ss = SpreadsheetApp.openById(TRACKER_SPREADSHEET_ID);
    const sheet = ss.getSheetByName(TRACKER_SHEET_NAME);
    if (!sheet) return json_({ ok: false, error: 'Deals sheet not found' });

    const lastRow = Math.max(sheet.getLastRow(), FIRST_DATA_ROW - 1);
    if (lastRow >= FIRST_DATA_ROW) {
      const existing = sheet
        .getRange(FIRST_DATA_ROW, 10, lastRow - FIRST_DATA_ROW + 1, 2)
        .getDisplayValues();

      for (let i = 0; i < existing.length; i++) {
        if (
          clean_(existing[i][0]).toLowerCase() === county.toLowerCase() &&
          clean_(existing[i][1]) === parcelId
        ) {
          return json_({ ok: true, duplicate: true, row: FIRST_DATA_ROW + i });
        }
      }
    }

    let row = FIRST_DATA_ROW;
    while (row <= LAST_TEMPLATE_ROW && clean_(sheet.getRange(row, 1).getDisplayValue())) row++;
    if (row > LAST_TEMPLATE_ROW) {
      return json_({ ok: false, error: 'tracker row capacity reached' });
    }

    const acresNum = Number(p.acres);
    const values = [[
      clean_(p.dealSite) || (county + ' parcel ' + parcelId), // A Deal / Site
      isFinite(acresNum) ? acresNum : '',                    // B Acres
      'Pursuing',                                            // C Stage
      '',                                                    // D Offer / Price
      clean_(p.nextAction) || 'Contact owner',               // E Next Action
      '',                                                    // F Next Action Date
      '',                                                    // G Key Deadline
      '',                                                    // H Closing Date
      clean_(p.owner),                                       // I Owner / Contact
      county,                                                // J County
      parcelId,                                              // K Parcel ID
      clean_(p.mapLink),                                     // L Map Link
      '',                                                    // M Deal Folder
      clean_(p.notes)                                        // N Notes
    ]];

    sheet.getRange(row, 1, 1, 14).setValues(values);
    SpreadsheetApp.flush();
    return json_({ ok: true, duplicate: false, row: row });
  } catch (err) {
    return json_({ ok: false, error: String(err && err.message || err) });
  }
}

function output_(callback, obj) {
  const cb = clean_(callback);
  if (cb && /^[A-Za-z_$][0-9A-Za-z_$\.]*$/.test(cb)) {
    return ContentService
      .createTextOutput(cb + '(' + JSON.stringify(obj) + ');')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return json_(obj);
}

function clean_(value) {
  return String(value == null ? '' : value).trim().slice(0, 2000);
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
