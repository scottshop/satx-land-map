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


## Active Deals map layer

The map can also read the active tracker rows through the same private tracker key.

The read endpoint returns only the fields needed for the map:
- deal/site
- stage
- next action and date
- owner
- county
- parcel ID
- map link

It does **not** return offer/price, deadlines, closing date, deal folder, or notes.

Map colors:
- **Yellow** — Pursuing / Watch List
- **Blue** — LOI
- **Green** — Under Contract
- Closed / Dead — not shown

After updating `Code.gs`, create a **new Web App deployment version** (or edit the existing deployment to a new version) so the public `/exec` URL serves the updated `doGet(e)` logic. Keep the same `/exec` URL in `data/tracker-config.js`.
