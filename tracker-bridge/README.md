# Land Deal Tracker web app bridge

This folder contains the Google Apps Script code behind **Save to Tracker**
and the live **Tracker Sites** map layer.

## Current tracker schema

The source of truth is the existing **Land Deal Tracker** Google Sheet,
**Deals** tab. Its header row includes:

- A: Location / Intersection
- B: Priority (checkbox)
- C: Size (AC)
- D: Attachments
- E: Stage
- I: Contact Made? (checkbox)
- K: Owner Contact
- L: Notes
- M: Map Link

The Apps Script resolves columns by **header text**, not fixed positions.
County and Parcel ID are extracted from the Map Link query parameters
(`county/parcel` or legacy `importCounty/importParcel`).

Do **not** revert the script to the original 14-column Deal / Site format,
which would misinterpret these columns and corrupt future saves.

## Deploy an update without changing the public URL

1. Open the **Land Deal Tracker** Sheet and select **Extensions → Apps Script**.
2. Update `Code.gs` with the reviewed file here.
3. Select **Deploy → Manage deployments** and edit the existing active Web App.
4. Choose **New version** and deploy, preserving **Execute as Me** and
   **Who has access: Anyone**.
5. **Keep the existing deployment URL** configured in `data/tracker-config.js`.
   Do not create a new deployment.
6. In the Apps Script editor, select the function `setupTrackerFolderAutomation`
   and click **Run** once as the tracker owner. Approve Google Drive/Sheets permissions.
   This installs the edit trigger and hourly reconciliation for manual/API additions.

The API supports:
- `GET /exec?action=trackerSites&callback=<safeCallbackName>` to read map-safe
  active records (no notes, prices, or attachment URLs).
- `POST /exec` with form fields `county`, `parcelId`, `mapLink`,
  `dealSite`, `acres`, `owner`, and `notes`.

The bridge checks County + Parcel ID before writing, then places new deals in
the next truly empty deal row, ignoring empty template rows containing FALSE
checkbox values. It preserves existing deals, attachment cells, checkbox
defaults, and Google Maps links on the Location cells.

## Test

```sh
node tests/tracker-bridge.cjs
```

Also confirm that the live endpoint returns the correct `county` and
`parcelId`, not dates or contact names. The map verifies saves with its
own live JSONP callback rather than depending on the Tracker Sites toggle.

## Automatic attachment folders

- Each newly saved site gets its own Drive folder under the existing **Land Deal Tracker Attachments** folder (`1pxwxPuEeklingY-NyOGq4CnAn0YwZ8di`). Its `Attachments` cell becomes a `📎 Files` hyperlink.
- New folders follow `Site Name — deal <row>` naming, matching the folders already created for deals 1–77.
- Duplicate Save-to-Tracker requests repair a missing attachment link rather than making duplicate folders. Existing attachment hyperlinks are never overwritten.
- Manual additions to the `Deals` tab are handled immediately by the installed edit trigger. An hourly reconciliation covers rows written by API/other automations, because edit triggers do not fire for API writes.
- **Source changes in GitHub do not automatically deploy to Apps Script**. To activate this for live saves, update the existing script deployment and run `setupTrackerFolderAutomation` once, as above. Never create a new Web App URL.

Run `node tests/tracker-bridge.cjs` to check the folder creation, duplicate behavior, and manual-entry repair logic.
