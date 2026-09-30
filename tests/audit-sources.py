"""Audit only the map's existing endpoints. Writes a small live test manifest to /tmp."""
import concurrent.futures, json, pathlib, re, urllib.parse, urllib.request
root=pathlib.Path(__file__).resolve().parents[1]
html=(root/'index.html').read_text()
urls=dict(re.findall(r'var (\w+Url) = "(https:[^"]+)"',html))
entries=[]
for name,body in re.findall(r'var (\w+) = L.esri.featureLayer\(\{(.*?)\n        \}\);',html,re.S):
    u=re.search(r'url:(\w+)(\+"/0")?',body)
    if not u or u[1] not in urls:continue
    where=re.search(r'where:"([^"]+)"',body)
    entries.append((name,urls[u[1]]+('/0' if u[2] else ''),where[1] if where else '1=1'))
def get(url,params):
    with urllib.request.urlopen(url+'?'+urllib.parse.urlencode(params),timeout=25) as r:return json.load(r)
def check(item):
    name,url,where=item;result={'name':name,'url':url,'where':where}
    try:
        meta=get(url,{'f':'json'});sample=get(url+'/query',{'f':'json','where':where,'outFields':'*','returnGeometry':'true','outSR':4326,'resultRecordCount':1})
        result.update(geometryType=meta.get('geometryType'),fields=[f['name'] for f in meta.get('fields',[])],editingInfo=meta.get('editingInfo'),error=meta.get('error') or sample.get('error'))
        if sample.get('features'):
            feature=sample['features'][0];geom=feature['geometry'];xy=(geom.get('rings') or geom.get('paths') or [[[geom.get('x'),geom.get('y')]]])[0][0]
            result['location']=[xy[1],xy[0]];result['attributes']=feature['attributes']
        if 'HEB' in name or 'NBU' in name:result['count']=get(url+'/query',{'f':'json','where':where,'returnCountOnly':'true'})
    except Exception as e:result['error']=str(e)
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(check,entries))
pathlib.Path('/tmp/satx-live-manifest.json').write_text(json.dumps(results,indent=2))
for r in results: print(r['name'],r.get('geometryType'),r.get('error'),r.get('count',{}),flush=True)
