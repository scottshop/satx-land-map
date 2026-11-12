/**
 * San Antonio Land Map -> Google Land Deal Tracker bridge.
 * Deploy as a Google Apps Script Web App: execute as owner, access anyone.
 * Column positions are resolved by header names so tracker layout changes
 * do not corrupt new saves or the live map feed.
 */
const TRACKER_SPREADSHEET_ID = '1BUdhXHCmsmaTCWZI5mYTmlabQ7rePN7acsLsbLLZJzI';
const TRACKER_SHEET_NAME = 'Deals';
const HEADER_ROW = 1;
const FIRST_DATA_ROW = HEADER_ROW + 1;
const ALLOWED_COUNTIES = ['Bexar','Comal','Guadalupe','Kendall','Medina','Blanco','Kerr','Webb'];

function setupTrackerKey() {
  const key = Utilities.getUuid().replace(/-/g,'') + Utilities.getUuid().replace(/-/g,'');
  PropertiesService.getScriptProperties().setProperty('TRACKER_KEY',key);
  return key;
}

function clean_(value) {
  return String(value == null ? '' : value).trim().slice(0,2000);
}
function headerKey_(value) {
  return clean_(value).toLowerCase().replace(/[^a-z0-9]/g,'');
}
function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
function output_(callback,obj) {
  const cb=clean_(callback);
  if(cb && /^[A-Za-z_$][0-9A-Za-z_$]*$/.test(cb)) {
    return ContentService.createTextOutput(cb+'('+JSON.stringify(obj)+');')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return json_(obj);
}
function trackerSheet_() {
  const sheet=SpreadsheetApp.openById(TRACKER_SPREADSHEET_ID).getSheetByName(TRACKER_SHEET_NAME);
  if(!sheet) throw new Error('Deals sheet not found');
  return sheet;
}
function trackerColumns_(sheet) {
  const labels=sheet.getRange(HEADER_ROW,1,1,sheet.getLastColumn()).getDisplayValues()[0];
  const lookup={};
  labels.forEach(function(label,i){if(label && !lookup[headerKey_(label)])lookup[headerKey_(label)]=i+1;});
  function column(aliases,required) {
    for(let i=0;i<aliases.length;i++)if(lookup[headerKey_(aliases[i])])return lookup[headerKey_(aliases[i])];
    if(required)throw new Error('Tracker column missing: '+aliases[0]);
    return 0;
  }
  return {
    site:column(['Location / Intersection','Deal / Site'],true),
    priority:column(['Priority'],false),
    acres:column(['Size (AC)','Acres'],true),
    attachment:column(['Attachments'],false),
    stage:column(['Stage'],true),
    owner:column(['Owner Contact','Owner / Contact'],false),
    notes:column(['Notes'],false),
    mapLink:column(['Map Link'],true)
  };
}
function parseMapParcel_(link) {
  const raw=clean_(link);
  if(!/^https:\/\/(scottshop\.github\.io\/satx-land-map|satx-land-map\.netlify\.app)\/?(?:\?|$)/i.test(raw))return null;
  const query=raw.split('?')[1];
  if(!query)return null;
  const p={};
  query.split('#')[0].split('&').forEach(function(part) {
    const pair=part.split('=');
    try {
      const k=decodeURIComponent(pair[0]||'').toLowerCase();
      p[k]=decodeURIComponent((pair.slice(1).join('=')||'').replace(/\+/g,' '));
    } catch(e) {}
  });
  const county=clean_(p.county||p.importcounty);
  const parcelId=clean_(p.parcel||p.importparcel);
  const canonicalCounty=ALLOWED_COUNTIES.find(function(x){return x.toLowerCase()===county.toLowerCase();});
  if(!canonicalCounty||!/^[0-9A-Za-z-]{1,80}$/.test(parcelId))return null;
  return {county:canonicalCounty,parcelId:parcelId};
}
function trackerKey_(county,parcelId) {
  return clean_(county).toLowerCase()+'|'+clean_(parcelId);
}
function readTracker_(sheet,col) {
  const last=Math.max(sheet.getLastRow(),FIRST_DATA_ROW-1);
  if(last<FIRST_DATA_ROW)return [];
  const count=last-FIRST_DATA_ROW+1;
  const data=sheet.getRange(FIRST_DATA_ROW,1,count,sheet.getLastColumn()).getDisplayValues();
  return data.map(function(r,i){return {row:FIRST_DATA_ROW+i,values:r,ref:parseMapParcel_(r[col.mapLink-1])};});
}
function doGet(e) {
  const p=(e&&e.parameter)||{};
  try {
    if(clean_(p.action)!=='trackerSites')return json_({ok:true,service:'land-deal-tracker-bridge',version:'header-mapped-2026-11-12'});
    const sheet=trackerSheet_(),col=trackerColumns_(sheet);
    const sites=readTracker_(sheet,col).map(function(item) {
      const r=item.values,ref=item.ref;
      if(!ref||!clean_(r[col.site-1]))return null;
      const stage=clean_(r[col.stage-1])||'Pursuing';
      if(/^(closed|dead)$/i.test(stage))return null;
      return {
        row:item.row,dealSite:clean_(r[col.site-1]),
        acres:clean_(r[col.acres-1]),stage:stage,
        nextAction:'',nextActionDate:'',
        owner:col.owner?clean_(r[col.owner-1]):'',
        county:ref.county,parcelId:ref.parcelId,
        mapLink:clean_(r[col.mapLink-1])
      };
    }).filter(Boolean);
    return output_(p.callback,{ok:true,schemaVersion:'header-mapped-2026-11-12',sites:sites,generatedAt:new Date().toISOString()});
  } catch(err) {
    return output_(p.callback,{ok:false,error:String(err&&err.message||err)});
  }
}
function doPost(e) {
  const p=(e&&e.parameter)||{};
  const parcelId=clean_(p.parcelId);
  const county=clean_(p.county);
  const mapLink=clean_(p.mapLink);
  if(!parcelId||!county)return json_({ok:false,error:'missing parcelId/county'});
  if(ALLOWED_COUNTIES.indexOf(county)<0)return json_({ok:false,error:'unsupported county'});
  if(!/^[0-9A-Za-z-]{1,80}$/.test(parcelId))return json_({ok:false,error:'invalid parcelId'});
  const mapRef=parseMapParcel_(mapLink);
  if(!mapRef||mapRef.county!==county||mapRef.parcelId!==parcelId)
    return json_({ok:false,error:'invalid or mismatched map link'});
  const lock=LockService.getScriptLock();
  if(!lock.tryLock(10000))return json_({ok:false,error:'tracker busy; retry'});
  try {
    const sheet=trackerSheet_(),col=trackerColumns_(sheet);
    const entries=readTracker_(sheet,col);
    for(let i=0;i<entries.length;i++) {
      const ref=entries[i].ref;
      if(ref&&trackerKey_(ref.county,ref.parcelId)===trackerKey_(county,parcelId))
        return json_({ok:true,duplicate:true,row:entries[i].row});
    }
    // Priority and Contact Made? are checkbox-backed template cells, often FALSE
    // hundreds of rows past the last actual deal. Never use getLastRow()+1 here.
    let row=0;
    for(let i=0;i<entries.length;i++) {
      const item=entries[i],v=item.values;
      const businessCols=[col.site,col.acres,col.attachment,col.stage,col.owner,col.notes,col.mapLink].filter(Boolean);
      if(businessCols.every(function(c){return !clean_(v[c-1]);})) {row=item.row;break;}
    }
    if(!row) {
      row=Math.max(sheet.getLastRow()+1,FIRST_DATA_ROW);
      if(row>sheet.getMaxRows())sheet.insertRowsAfter(sheet.getMaxRows(),row-sheet.getMaxRows());
    }
    const width=sheet.getLastColumn();
    const cell=sheet.getRange(row,1,1,width);
    const existing=cell.getValues()[0];
    const values=existing.slice();
    const acres=Number(p.acres);
    // New clients send a HYPERLINK-formula fallback for older deployments.
    // Prefer the plain display text on upgraded deployments, so the native
    // rich-text Location hyperlink can be renamed directly in the Sheet.
    values[col.site-1]=clean_(p.locationText)||clean_(p.dealSite)||county+' parcel '+parcelId;
    values[col.acres-1]=clean_(p.acres)!==''&&isFinite(acres)&&acres>=0?acres.toFixed(2)+' AC':'';
    values[col.stage-1]='Pursuing';
    if(col.owner)values[col.owner-1]=clean_(p.owner);
    if(col.notes)values[col.notes-1]=clean_(p.notes)||'Saved from San Antonio Land Acquisition Map';
    values[col.mapLink-1]=mapLink;
    // Do not change existing priority/contact-made checkbox defaults, other columns,
    // or any pre-existing attachment link.
    cell.setValues([values]);
    // Google Maps links are attached to the visible Location text as native
    // rich-text links, not HYPERLINK formulas. The user can rename the site
    // directly in the Sheet without losing the coordinate destination.
    const latitude=Number(p.latitude),longitude=Number(p.longitude);
    if(clean_(p.latitude)!=='' && clean_(p.longitude)!=='' &&
       isFinite(latitude) && isFinite(longitude) &&
       latitude>=25 && latitude<=37 && longitude>=-107 && longitude<=-93) {
      const coord=latitude.toFixed(8)+','+longitude.toFixed(8);
      const mapsUrl='https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(coord);
      const rich=SpreadsheetApp.newRichTextValue()
        .setText(values[col.site-1])
        .setLinkUrl(mapsUrl)
        .build();
      sheet.getRange(row,col.site).setRichTextValue(rich);
    }
    SpreadsheetApp.flush();
    return json_({ok:true,duplicate:false,row:row});
  } catch(err) {
    return json_({ok:false,error:String(err&&err.message||err)});
  } finally {
    lock.releaseLock();
  }
}
