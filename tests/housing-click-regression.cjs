/* Regression: housing development popups must have priority over CAD parcel identify.
   Run: node tests/housing-click-regression.cjs */
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const html=fs.readFileSync(path.resolve(__dirname,"..","index.html"),"utf8");
const pane=html.match(/\[\['cad',(\d+)\],\['cadSelected',(\d+)\],\['ownership',(\d+)\],\['infrastructure',(\d+)\],\['housing',(\d+)\],\['diligence',(\d+)\]\]/);
assert(pane,"The map must declare a dedicated housing pane");
const [cad,selected,ownership,infrastructure,housing,diligence]=pane.slice(1).map(Number);
assert(housing>cad,"Housing outlines must appear above CAD parcels");
assert(housing>selected,"Housing popups must remain clickable above selection highlights");
assert(housing>infrastructure,"Housing click areas must not be hidden behind other context layers");
assert(diligence<cad,"Original due-diligence layer stacking must remain unchanged");
assert(html.includes('if(v30LastPopupOpen>=clickedAt||v30LastHousingClick>=clickedAt)return;'),
  "Click fallback must respect existing popup and housing click event");
assert(html.includes('function v30MarkHousingClick()'),"Map must record housing clicks");
assert(html.includes("v30IdentifySerial++"),"Housing clicks should cancel pending CAD identifies");
const checks=[
  ['Bexar housing plats','function v10HousingPlatLayer(', 'layer.on("click",v30MarkHousingClick);'],
  ['Schertz housing plats','var v10SchertzHousingPlats=', 'v10SchertzHousingPlats.on("click",v30MarkHousingClick);'],
  ['Comal active plats','var v11ComalHousingPlats=', 'v11ComalHousingPlats.on("click",v30MarkHousingClick);']
];
for(const [label,start,click]of checks){
  const at=html.indexOf(start);
  assert(at>=0,label+" source is missing");
  assert(html.slice(at,at+400).includes('pane:"housing"'),label+" pane must be above CAD");
  assert(html.includes(click),label+" click handler must suppress CAD fallback");
}
assert(html.includes('return L.marker(latlng,{\n              pane:"housing",'),
  "Comal plat markers need the same housing pane");
assert(html.includes('var v10NewHousingPlats=L.layerGroup(['),
  "Housing layers must stay grouped under the same existing toggle");
for(const popup of [
 'v10HousingPlatPopup(l,status)',
 'v10SchertzHousingPlats.bindPopup(',
 'v11ComalHousingPlats.bindPopup('
])assert(html.includes(popup),"Development detail popup was removed: "+popup);
assert(html.includes('window.v10NewHousingPlats=v10NewHousingPlats'),
  "The existing new housing toggle must stay connected");
assert(html.includes('function v30IdentifyAnyParcel('),"Parcel identify must still work outside housing");
console.log("PASS future housing Bexar/Schertz/Comal click priority and existing parcel fallback");
