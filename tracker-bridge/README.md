# Map → Land Deal Tracker bridge

This folder contains the private-side Google Apps Script code for the **Save to Tracker** button.

The public GitHub map never stores Google credentials or the private tracker key.

## One-time setup

1. Open the **Land Deal Tracker** Google Sheet.
2. Go to **Extensions → Apps Script**.
3. Replace the default code with `Code.gs` from this folder.
4. In the script, replace `PASTE_SPREADSHEET_ID` with the spreadsheet ID from the Sheet URL.
5. Run `setupTrackerKey()` once and copy the generated key from the execution log.
6. Choose **Deploy → New deployment → Web app**.
   - Execute as: **Me**
   - Who has access: **Anyone**
7. Copy the deployed `/exec` URL into `data/tracker-config.js`.
8. The first time you press **Save to Tracker** on the map, paste the generated tracker key. The browser stores it locally so you do not enter it again.

The Apps Script checks **County + Parcel ID** before writing, so repeated clicks do not create duplicate deal rows.


## Live Tracker Sites sync

The map now supports a secure read endpoint:

- `GET /exec?action=trackerSites&key=<TRACKER_KEY>`
- Optional JSONP callback: `&callback=__landTrackerSitesCallback`

The endpoint returns only the fields needed to draw and label active tracker sites:
- deal/site
- acreage
- stage
- next action + date
- owner
- county
- parcel ID
- map link

It excludes offer/price, key deadlines, closing dates, deal-folder links, and notes.

While the **Tracker Sites** layer is on, the map refreshes the Sheet every 30 seconds. Existing parcel geometry is recolored in place:
- Pursuing / Tracking / Watch List → yellow
- LOI / Under Contract / Contract → green
- Closed / Dead → removed from Tracker Sites on the next sync

After changing `Code.gs`, publish a new Apps Script Web App version while keeping the same public `/exec` URL in `data/tracker-config.js`.
