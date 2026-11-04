/* Regression checks for the selected-parcel accordion renderer.
   Run: node tests/parcel-accordion.cjs */
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"..");
const index=fs.readFileSync(path.join(root,"index.html"),"utf8");
const source=fs.readFileSync(path.join(root,"data/parcel-accordion.js"),"utf8");
const css=fs.readFileSync(path.join(root,"data/parcel-accordion.css"),"utf8");
const wired=fs.readFileSync(path.join(root,"data/parcel-explorer-ui.js"),"utf8");
assert(index.includes('src="data/parcel-accordion.js"'));
assert(index.includes('href="data/parcel-accordion.css"'));
assert(index.includes("function v32ParcelDetailData(p,county)"));
assert(wired.includes("window.v32RenderParcelAccordion(details, popup.getLatLng"));
assert(css.includes("lgAccordionHeader")&&css.includes("lgDetailRow"));
assert(css.includes(".lgAccordionSection:not(.open) .lgAccordionBody"));
assert(source.includes(".returnGeometry(false)"),"Detail lookup must avoid transferring whole parcel geometry");
// Expose one pure helper in a temporary VM; production source is unchanged.
const injection=source.replace(
  "  window.v32RenderParcelAccordion=function(root,selectedPoint){",
  "  window.__testPropertyFields=propertyFields;\n  window.v32RenderParcelAccordion=function(root,selectedPoint){"
);
assert.notEqual(injection,source);
const context={window:{}};vm.runInNewContext(injection,context,{filename:"parcel-accordion.js"});
const build=context.window.__testPropertyFields;
assert.equal(typeof build,"function");
const bexar={
 Prop_id:1041308,Geo_id:"04401-000-0143",Owner_name:"BOEHME ISABELL ETAL",
 Situs:"TALLY RD, SAN ANTONIO, TX 78253",Situs_Zip:"78253",
 Addr_line2:"4461 TALLEY RD",Addr_city:"SAN ANTONIO",Addr_state:"TX",Zip:"78253",
 Land_acres:596.882,LandSqft:26068655.65,School:"NORTHSIDE ISD",Prop_yr:2025,
 Market_val:25412480,Land_hstd_val:42500,Imprv_hstd_val:45000,State_cd:"E1"
};
const result=build(bexar,"Bexar");
assert.equal(result.owner,"BOEHME ISABELL ETAL");
assert.equal(result.parcelId,"1041308");
assert.deepEqual(Array.from(result.sections.map(s=>s.name)),["Location","Mailing Address","Sales History","Value","Land"]);
const entries=Object.fromEntries(result.sections.map(s=>[s.name,Object.fromEntries(s.rows)]));
assert.equal(entries.Location["Street Address"],"TALLY RD");
assert.equal(entries.Location.City,"SAN ANTONIO");
assert.equal(entries.Location["School District"],"NORTHSIDE ISD");
assert.equal(entries["Mailing Address"]["Street Address"],"4461 TALLEY RD");
assert.equal(entries.Value["Market Total Value"],"$25,412,480");
assert.equal(entries.Land["Legal Acres"],"596.882");
assert.notEqual(entries.Land["Calculated GIS Acres"],"");
assert.equal(entries.Land["Zoning at Selected Point"],"","Unavailable zoning must not be fabricated");
assert.equal(result.acres,"596.882");
assert.equal(entries.Value["Market Land Value (calculated)"],"$25,367,480");
assert.equal(entries.Value["Reported Improvement Value"],"$45,000");
assert(source.includes("supplementSanAntonioZoning"),"Optional COSA point zoning lookup must exist");
assert(css.includes("lgHeaderAcres"),"Prominent header acreage style must exist");
const others=[
 ["Comal",{PROP_ID:60165,PY_OWNER_N:"COMAL OWNER",SITUS_ADDR:"100 MAIN ST",LEGAL_ACRE:2.2}],
 ["Guadalupe",{PROP_ID:57261,OWNER_NAME:"GUAD OWNER",SITUS_ADDR:"100 GUAD ST",LEGAL_AREA:3.2}],
 ["Kendall",{geo_id:"1-0002-0171-0020",file_as_na:"KENDALL OWNER",situs_full:"107 SCHEELE RD",legal_acre:4.63}],
 ["Kerr",{prop_id:"20885",owner_name:"KERR OWNER",kcad_address:"100 KERR RD",legal_acres:6.5}],
 ["Medina",{PROP_ID:"1002",OWNER_NAME:"MEDINA OWNER",SITUS_ADDR:"100 MEDINA RD",LEGAL_AREA:7.5}],
 ["Blanco",{Prop_ID:"1006",OWNER_NAME:"BLANCO OWNER",SITUS_ADDR:"100 BLANCO RD",LEGAL_AREA:8.5}],
 ["Webb",{Prop_ID:"528431",OWNER_NAME:"WEBB OWNER",SITUS_ADDR:"100 WEBB RD",LEGAL_AREA:9.5}]
];
for(const [county,p]of others){
 const data=build(p,county);
 assert.equal(data.county,county);
 assert(data.owner.endsWith("OWNER"));
 assert.equal(data.sections.length,5);
 assert(data.sections[0].rows.some(([key,val])=>key==="County"&&val===county+" County"));
 assert.equal(data.sections[1].rows[0][1],"","Missing mailing addresses must not be invented");
}
console.log("PASS accordion sections and county data for all eight counties");
