/* Browser-only regression checks. Requires Playwright outside the static site.
   CHROMIUM_PATH=/path/to/chromium node tests/map-smoke.cjs
   MAP_URL can select a deployed preview instead of the local static server. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const root = path.resolve(__dirname, '..');
const server = process.env.MAP_URL ? null : http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  const file = path.join(root, pathname === '/' ? 'index.html' : pathname);
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  try { res.end(fs.readFileSync(file)); } catch { res.writeHead(404).end(); }
}).listen(Number(process.env.TEST_PORT||8770), '127.0.0.1');
(async () => {
  const browser = await chromium.launch({
    headless: true, executablePath: process.env.CHROMIUM_PATH || undefined,
    args: ['--no-sandbox', '--disable-dev-shm-usage', ...(process.env.HTTPS_PROXY ? ['--disable-http2'] : [])],
    proxy: process.env.HTTPS_PROXY ? {server: process.env.HTTPS_PROXY, bypass: '127.0.0.1,localhost'} : undefined
  });
  try {
    const page = await browser.newPage({ignoreHTTPSErrors: true, viewport: {width: 1440, height: 1000}});
    const errors = []; page.on('pageerror', e => { errors.push(e.message); console.log('PAGE ERROR', e.message); });
    await page.goto(process.env.MAP_URL || 'http://127.0.0.1:'+(process.env.TEST_PORT||8770), {waitUntil: 'domcontentloaded', timeout: 90000});
    await page.waitForFunction(() => window.v6OppLoaded, null, {timeout: 60000});
    await page.evaluate(() => { window.testMap = map_33cc2c2ac68d72d2971fbb7de3650b24; });
    assert.equal(await page.evaluate(() => v6OpportunityData.length), 30);
    assert.equal(await page.evaluate(() => testMap.hasLayer(tile_layer_satellite_hybrid)), true);
    for (const name of ['v3Parcels','v3ComalParcels','v3GuadalupeParcels','v3SewerService','v3FemaHazard','v3AADT','v3FutureLandUse','v3Rings','v3VerifiedTargetGeometry']) {
      assert.equal(await page.evaluate(n => testMap.hasLayer(window[n]), name), false, name + ' must default OFF');
    }
    console.log('PASS page/GeoJSON/defaults');
    if(process.env.TEST_STAGE!=='gis') {
    try { await page.waitForFunction(() => Array.from(document.querySelectorAll('img.leaflet-tile-loaded')).some(i=>i.src.includes('World_Imagery')&&i.naturalWidth>0), null, {timeout:60000}); }
    catch(e) {console.log('TILE DEBUG',await page.evaluate(()=>({base:testMap.hasLayer(tile_layer_satellite_hybrid),satellite:testMap.hasLayer(tile_layer_satellite),zoom:testMap.getZoom(),images:Array.from(document.querySelectorAll('img.leaflet-tile')).slice(0,8).map(x=>({src:x.src,complete:x.complete,width:x.naturalWidth,class:x.className}))})));await page.screenshot({path:'/tmp/satx-tile-failure.png'});throw e;}
    console.log('PASS actual satellite imagery');
    await page.screenshot({path: process.env.SCREENSHOT_DIR ? path.join(process.env.SCREENSHOT_DIR,'desktop.png') : '/tmp/satx-desktop.png'});
    await page.setViewportSize({width:390,height:844}); await page.evaluate(()=>testMap.invalidateSize());
    await page.locator('.leaflet-control-layers').hover(); assert(await page.getByText('Exact Target Parcels',{exact:true}).isVisible());
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:process.env.SCREENSHOT_DIR ? path.join(process.env.SCREENSHOT_DIR,'mobile.png') : '/tmp/satx-mobile.png'});
    await page.mouse.click(60,700); await page.locator('#v6TopToggle').click(); assert(await page.locator('#v6TopPanel').isVisible());
    console.log('PASS mobile menu/panel/no overflow');await page.locator('#v6TopToggle').click();await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>testMap.invalidateSize());
    }
    await page.locator('.leaflet-control-layers').hover();
    for (const removed of ['Assemblage Opportunities','Preliminary Plats','Future Land Use','Parcel Search Results','Legacy Parcel References','Legacy References']) {
      assert.equal(await page.getByText(removed,{exact:true}).count(),0, removed+' should be removed from Layers');
    }
    for (const title of ['BASEMAPS','LAND','PARCEL DATA','GROWTH','INFRASTRUCTURE','DUE DILIGENCE','RESEARCH']) assert(await page.getByText(title, {exact: true}).isVisible());
    const targetLabel = page.locator('.leaflet-control-layers label').filter({hasText: 'Exact Target Parcels'});
    await targetLabel.locator('input').uncheck(); assert.equal(await page.evaluate(() => testMap.hasLayer(v6OpportunityLayer)), false);
    await targetLabel.locator('input').check(); assert.equal(await page.evaluate(() => testMap.hasLayer(v6OpportunityLayer)), true);
    await page.mouse.click(750,850); console.log('PASS layer menu headings/toggles');
    await page.evaluate(() => { window.testTarget = Object.values(v6OpportunityById)[0].layer; testMap.fitBounds(testTarget.getBounds(), {maxZoom: 17, animate: false}); });
    await page.waitForTimeout(300);
    async function clickFeature(name, expected) {
      const point = await page.evaluate(n => {
        const paths = []; function visit(l) { if (l._path && l._path.isConnected) paths.push(l._path); else if (l.eachFeature) l.eachFeature(visit); else if (l.eachLayer) l.eachLayer(visit); } visit(window[n]);
        function exposed(x,y,p) { return x>55 && y>105 && x<innerWidth-285 && y<innerHeight-55 && document.elementFromPoint(x,y)===p; }
        for (const p of paths) {
          const r=p.getBoundingClientRect();
          for(let i=1;i<12;i++) for(let j=1;j<12;j++){const x=r.x+r.width*i/12,y=r.y+r.height*j/12;if(exposed(x,y,p))return{x,y};}
          for(let f=.05;f<1;f+=.05){const t=p.getPointAtLength(p.getTotalLength()*f),q=new DOMPoint(t.x,t.y).matrixTransform(p.getScreenCTM());if(exposed(q.x,q.y,p))return{x:q.x,y:q.y};}
        } throw Error('No exposed path for '+n);
      }, name);
      await page.mouse.move(point.x, point.y);
      assert.equal(await page.evaluate(({x,y}) => getComputedStyle(document.elementFromPoint(x,y)).cursor, point), 'pointer');
      await page.mouse.click(point.x, point.y);
      await page.locator('.leaflet-popup-content').waitFor();
      assert((await page.locator('.leaflet-popup-content').innerText()).includes(expected));
      if(name==='v3Parcels'){
        assert(await page.locator('.bcad-card').isVisible(),'Bexar CAD should use the dedicated parcel card');
        assert.equal(await page.locator('.bcad-address').count(),1);
        assert.equal(await page.evaluate(()=>v3BexarSelectedParcel&&v3BexarSelectedParcel.options.color),'#ff645c','selected Bexar parcel should use the coral highlight');
      }
      await page.locator('.leaflet-popup-close-button').click(); await page.waitForFunction(()=>document.querySelectorAll('.leaflet-popup').length===0);
      console.log('PASS feature hover/click/popup/close',name);
    }
    if(process.env.TEST_STAGE==='gis') {
      const manifest=JSON.parse(fs.readFileSync('/tmp/satx-live-manifest.json'));
      for(const [name,title] of [
        ['v3Parcels','Bexar'],['v3ComalParcels','Comal'],['v3GuadalupeParcels','Guadalupe'],
        ['v3HEBOwnedParcels','H-E-B'],['v3HEBComalParcels','H-E-B'],['v3HEBGuadalupeParcels','H-E-B'],
        ['v3SewerSAWS','SAWS'],['v3SewerNBU','NBU'],['v3SewerGBRAGravity','GBRA'],['v3SewerGBRAForce','GBRA']
      ]) {
        const source=manifest.find(x=>x.name===name); assert(source.location, name+' live query failed');
        await page.evaluate(({name,location})=>{
          v7applyMode('acquisition'); testMap.removeLayer(v6OpportunityLayer); testMap.removeLayer(v6OpportunityMarkers);
          testMap.setView(location,17,{animate:false}); window[name].addTo(testMap);
        },{name,location:source.location});
        await page.waitForFunction(n=>{let found=false;window[n].eachFeature(l=>{if(l._path&&l._path.isConnected)found=true;});return found;},name,{timeout:45000});
        await clickFeature(name,title); await page.evaluate(n=>testMap.removeLayer(window[n]),name);
      }
      await page.evaluate(()=>{
        v7applyMode('acquisition');testMap.removeLayer(v6OpportunityLayer);testMap.removeLayer(v6OpportunityMarkers);
        testMap.setView([29.39,-98.72],14,{animate:false});feature_group_370786adb15c6d6d865f189609798696.addTo(testMap);
      });
      await page.waitForFunction(()=>feature_group_370786adb15c6d6d865f189609798696.getLayers().length>0,null,{timeout:45000});
      await page.evaluate(()=>testMap.fitBounds(feature_group_370786adb15c6d6d865f189609798696.getLayers()[0].getBounds().pad(.3),{maxZoom:16,animate:false}));
      await page.waitForTimeout(300);
      await clickFeature('feature_group_370786adb15c6d6d865f189609798696','TxDOT');
      assert.deepEqual(errors,[]);console.log('LIVE GIS CHECKS PASSED');return;
    }
    await clickFeature('testTarget', 'WHY THIS TRACT');
    await page.evaluate(() => { v3Parcels.addTo(testMap); });
    await clickFeature('testTarget', 'WHY THIS TRACT');
    await page.evaluate(() => { testMap.removeLayer(v3Parcels); testMap.removeLayer(v6OpportunityLayer); });
    await page.locator('#v6TopToggle').click(); await page.locator('.v6OppCard').first().click();
    assert(await page.evaluate(() => testMap.hasLayer(v6OpportunityLayer)));
    await page.locator('.leaflet-popup-close-button').click(); await page.waitForFunction(()=>document.querySelectorAll('.leaflet-popup').length===0); await page.locator('#v6TopToggle').click();
    console.log('PASS Top Land');
    const before = await page.evaluate(() => testMap.getCenter());
    await page.mouse.move(650,800); await page.mouse.down(); await page.mouse.move(830,850,{steps:10}); await page.mouse.up(); await page.waitForTimeout(400);
    assert.notDeepEqual(await page.evaluate(() => testMap.getCenter()),before);
    const zoom=await page.evaluate(() => testMap.getZoom()); await page.locator('.leaflet-control-zoom-in').click(); await page.waitForTimeout(400); assert.equal(await page.evaluate(() => testMap.getZoom()),zoom+1);
    console.log('PASS drag/zoom');
    await page.locator('#v7ModeToggle').click(); assert.equal(await page.locator('#v7ModeToggle').getAttribute('data-mode'),'research');
    await page.locator('#v7ModeToggle').click(); assert.equal(await page.locator('#v7ModeToggle').getAttribute('data-mode'),'acquisition'); console.log('PASS modes');
    const zoomState = await page.evaluate(() => ({
      maxZoom: map_33cc2c2ac68d72d2971fbb7de3650b24.getMaxZoom(),
      clusterDisableAt: marker_cluster_9871e831b359eb1ea9745338fc5ffd62.options.disableClusteringAtZoom,
      satelliteOn: map_33cc2c2ac68d72d2971fbb7de3650b24.hasLayer(tile_layer_satellite_hybrid)
    }));
    assert.equal(zoomState.maxZoom,20,'map should expose a finite max zoom for marker clustering');
    assert.equal(zoomState.clusterDisableAt,11,'development markers should uncluster at zoom 11');
    assert.equal(zoomState.satelliteOn,true,'satellite should activate after the initial parcel extent is chosen');
    console.log('PASS startup zoom/cluster/satellite');
    assert.deepEqual(errors,[]); console.log('CORE CHECKS PASSED');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode=1; }).finally(()=>server?.close());
