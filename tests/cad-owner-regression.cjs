// Deterministic regression checks for owner, property ID, and acreage mapping.
// Run: node tests/cad-owner-regression.cjs
// The fixtures reflect the live field schemas verified on 2026-11-04.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

function functionSource(name) {
  const start = html.indexOf('function ' + name + '(');
  assert(start >= 0, 'Missing map function: ' + name);
  const open = html.indexOf('{', start);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    if (html[i] === '}' && --depth === 0) return html.slice(start, i + 1);
  }
  throw new Error('Unbalanced function body: ' + name);
}

const names = [
  'v25BexarNormalize', 'v12ParcelTrackerData', 'v12TrackerMapLink',
  'v16First', 'v16TrackerParcelData', 'v9SearchConfig',
  'v9SearchValue', 'v9SearchPopupConfig'
];
const urls = [
  'v3ParcelUrl', 'v3ComalCadUrl', 'v3GuadalupeCadUrl',
  'v16KendallCadUrl', 'v16KerrCadUrl',
  'v16MedinaCadUrl', 'v16BlancoCadUrl', 'v16WebbCadUrl'
];
const sandbox = {window: {v31BexarOwnerCache: {}}};
const api = vm.runInNewContext(
  'var ' + urls.map(n => n + '="' + n + '"').join(',') + ';\n' +
  names.map(functionSource).join('\n') + '\n({' + names.join(',') + '})',
  sandbox
);

// The same property must resolve from BOTH Bexar sources; this was the
// Tally Road "owner not reported" regression in November 2026.
const tally = [
  {PropID: 1041308, Geo_id: '04401-000-0143',
   Owner_Name: 'BOEHME ISABELL ETAL', legal_acre: 596.882, Situs: 'TALLY RD'},
  {Prop_id: 1041308, Geo_id: '04401-000-0143',
   Owner_name: 'BOEHME ISABELL ETAL', Land_acres: 596.882, Situs: 'TALLY RD'}
];
for (const record of tally) {
  const normalized = api.v25BexarNormalize(record);
  assert.equal(normalized.Prop_id, 1041308);
  assert.equal(normalized.Geo_id, '04401-000-0143');
  assert.equal(normalized.Owner_name, 'BOEHME ISABELL ETAL');
  assert.equal(Number(normalized.Land_acres), 596.882);
  const deal = api.v12ParcelTrackerData(record, 'Bexar');
  assert.equal(String(deal.parcelId), '1041308');
  assert.equal(deal.owner, 'BOEHME ISABELL ETAL');
  assert.equal(Number(deal.acres), 596.882);
}

const schemas = [
  ['Bexar', 'Prop_id', 'Owner_name', 'Land_acres', 'Market_val'],
  ['Comal', 'PROP_ID', 'PY_OWNER_N', 'LEGAL_ACRE', 'APPRAISED'],
  ['Guadalupe', 'PROP_ID', 'OWNER_NAME', 'LEGAL_AREA', 'MKT_VALUE'],
  ['Kendall', 'geo_id', 'file_as_na', 'legal_acre', 'market'],
  ['Kerr', 'prop_id', 'owner_name', 'legal_acres', 'market_val'],
  ['Medina', 'PROP_ID', 'OWNER_NAME', 'LEGAL_AREA', 'MKT_VALUE'],
  ['Blanco', 'Prop_ID', 'OWNER_NAME', 'LEGAL_AREA', 'MKT_VALUE'],
  ['Webb', 'Prop_ID', 'OWNER_NAME', 'LEGAL_AREA', 'MKT_VALUE']
];
const configs = api.v9SearchConfig();
assert.equal(configs.length, 8, 'All eight CAD counties must stay searchable');
for (const [county, idField, ownerField, acresField, valueField] of schemas) {
  const cfg = configs.find(c => c.county === county);
  assert(cfg, 'No CAD configuration for ' + county);
  assert.equal(cfg.id, idField, county + ' property ID field');
  assert.equal(cfg.owner, ownerField, county + ' owner field');
  assert.equal(cfg.acres, acresField, county + ' acreage field');
  assert.equal(cfg.value, valueField, county + ' valuation field');

  const id = county === 'Kendall' ? '1-0002-0171-0020' : '123456';
  const attrs = {[idField]: id, [ownerField]: 'VERIFIED TEST OWNER',
                 [acresField]: 5.25, [valueField]: 250000};
  assert.equal(api.v9SearchValue(attrs, cfg, 'owner'), 'VERIFIED TEST OWNER');
  assert.equal(String(api.v9SearchValue(attrs, cfg, 'id')), id);
  let saved;
  if (['Bexar', 'Comal', 'Guadalupe'].includes(county)) {
    saved = api.v12ParcelTrackerData(attrs, county);
  } else {
    const popup = api.v9SearchPopupConfig(cfg);
    assert.equal(popup.ownerFields[0], ownerField);
    assert.equal(popup.valueFields[0], valueField);
    saved = api.v16TrackerParcelData(attrs, popup);
  }
  assert.equal(saved.owner, 'VERIFIED TEST OWNER', county + ' owner lost');
  assert.equal(String(saved.parcelId), id, county + ' parcel ID lost');
  assert.equal(Number(saved.acres), 5.25, county + ' acreage lost');

  // A source blank must remain unknown rather than be interpreted as an owner.
  attrs[ownerField] = ' ';
  assert.equal(api.v9SearchValue(attrs, cfg, 'owner'), '',
               county + ' blank owner must be detected');
  if (['Bexar', 'Comal', 'Guadalupe'].includes(county)) {
    assert.equal(api.v12ParcelTrackerData(attrs, county).owner, '',
                 county + ' blank owner must not be saved as whitespace');
  } else {
    assert.equal(api.v16TrackerParcelData(attrs, api.v9SearchPopupConfig(cfg)).owner,
                 '', county + ' blank owner must not be saved');
    attrs.Owner_Name = 'FALLBACK TEST OWNER';
    assert.equal(api.v16TrackerParcelData(attrs, api.v9SearchPopupConfig(cfg)).owner,
                 'FALLBACK TEST OWNER', county + ' owner alias fallback failed');
  }
}
assert(html.includes('where:"PropID > 0"'),
       'Hosted Bexar parcel layer must exclude negative-ID placeholders');
assert(html.includes('pointQuery.where("Prop_id > 0")'),
       'Bexar click identify must exclude negative-ID placeholders');
console.log('PASS CAD owner/parcel ID/acreage/valuation mappings for all eight counties');
