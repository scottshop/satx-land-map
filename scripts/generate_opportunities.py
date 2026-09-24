#!/usr/bin/env python3
import csv, json, math, os, re, sys, time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from shapely.geometry import shape, mapping, Point
from shapely.ops import transform, unary_union
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

BEXAR = "https://maps.bexar.org/arcgis/rest/services/PW/PlatsMDPs/MapServer"
PARCEL_URL = f"{BEXAR}/2/query"
PLAT_LAYERS = {4:0.35, 5:0.55, 6:0.75, 7:0.90, 8:1.00}
PERMITS_URL = "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/Building_Permits_Issued_Past_180_Days/FeatureServer/0/query"
AADT_URL = "https://services.arcgis.com/KTcxiTD9dsQw4r7Z/ArcGIS/rest/services/TxDOT_AADT_Annuals_(Public_View)/FeatureServer/0/query"
STREETS_URL = "https://services.arcgis.com/g1fRTDLeMgspWrYp/ArcGIS/rest/services/Streets/FeatureServer/0/query"
COUNTY_ROADS_URL = "https://maps.bexar.org/arcgis/rest/services/PW/CountyRoads/MapServer/0/query"
COSA_MTP_URL = "https://services.arcgis.com/g1fRTDLeMgspWrYp/ArcGIS/rest/services/Major_Thoroughfare_Plan__MTP/FeatureServer/0/query"
FEMA_URL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
FLU_URL = "https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/Future_Land_Use/FeatureServer/4/query"
SAWS_CIP_POINT = "https://services.arcgis.com/g7IVOf0Gf9OkqkzV/ArcGIS/rest/services/SSORP_1_25_svc/FeatureServer/0/query"
SAWS_CIP_POLY = "https://services.arcgis.com/g7IVOf0Gf9OkqkzV/ArcGIS/rest/services/SSORP_1_25_svc/FeatureServer/1/query"
SARA_BCAD_URL = "https://gis.sara-tx.org/ags1/rest/services/FW_Bexar/BCAD_Parcels_PROD/MapServer/0/query"

NODES = [
 {"id":"INT-002","name":"I-35 / Kohlenberg Rd (Mayfair)","lat":29.748,"lng":-98.079,"base":90},
 {"id":"INT-001","name":"Culebra Rd / SH 211","lat":29.524162,"lng":-98.802373,"base":89},
 {"id":"INT-003","name":"I-10 / Loop 1604 East","lat":29.514,"lng":-98.312,"base":88},
 {"id":"INT-004","name":"US 90 / SH 211","lat":29.380,"lng":-98.800,"base":86},
 {"id":"INT-005","name":"Potranco Rd / SH 211","lat":29.4214,"lng":-98.7826,"base":84},
 {"id":"INT-009","name":"Schuwirth Rd / Loop 1604 East","lat":29.456,"lng":-98.2879,"base":82},
 {"id":"INT-006","name":"FM 1518 / I-10","lat":29.489044,"lng":-98.223251,"base":81},
 {"id":"INT-007","name":"Loop 337 / Word Pkwy (Veramendi)","lat":29.736,"lng":-98.179,"base":81},
 {"id":"INT-010","name":"FM 1516 / I-10 East","lat":29.514,"lng":-98.252,"base":81},
 {"id":"INT-011","name":"US 90 / Loop 1604 West","lat":29.394,"lng":-98.682,"base":81},
 {"id":"INT-012","name":"SH 211 / Briggs Ranch Rd","lat":29.410,"lng":-98.813,"base":79},
 {"id":"INT-013","name":"S Zarzamora / Mitra Way (VIDA)","lat":29.318,"lng":-98.530,"base":79},
 {"id":"INT-014","name":"FM 1518 / Lower Seguin Rd","lat":29.5237,"lng":-98.2462,"base":78},
 {"id":"INT-015","name":"FM 1103 / Orth Rd","lat":29.597,"lng":-98.228,"base":77},
 {"id":"INT-016","name":"Loop 1604 / Green Rd","lat":29.496,"lng":-98.293,"base":74},
 {"id":"INT-017","name":"Texas Research Pkwy / SH 211","lat":29.435,"lng":-98.797,"base":73},
 {"id":"INT-019","name":"US 90 / FM 471 (Castroville)","lat":29.356,"lng":-98.879,"base":72},
 {"id":"INT-018","name":"Louis Bauer Dr / Laser Dr (Brooks)","lat":29.346,"lng":-98.443,"base":72},
 {"id":"INT-022","name":"SH 46 / FM 1863","lat":29.750,"lng":-98.270,"base":71},
 {"id":"INT-023","name":"Old San Antonio Rd / Cascade Caverns Rd","lat":29.744,"lng":-98.686,"base":65},
 {"id":"INT-020","name":"Applewhite Rd / Lone Star Pass","lat":29.297,"lng":-98.552,"base":64},
 {"id":"INT-021","name":"Chavaneaux Rd / S Zarzamora","lat":29.284,"lng":-98.529,"base":61},
 {"id":"INT-025","name":"I-10 / SH 46 (Seguin Exchange)","lat":29.579,"lng":-97.949,"base":80},
 {"id":"INT-024","name":"Talley Rd / Potranco Rd","lat":29.414,"lng":-98.744,"base":78},
]

CATALYSTS = [
 {"name":"Culebra / SH 211 H-E-B","lat":29.524162,"lng":-98.802373},
 {"name":"I-10 / Loop 1604 East H-E-B","lat":29.514,"lng":-98.312},
 {"name":"Mayfair Costco","lat":29.747031,"lng":-98.056017},
 {"name":"H-E-B Foster campus","lat":29.41984,"lng":-98.36083},
]

PUBLIC_OWNER = re.compile(r"(CITY OF|COUNTY OF|STATE OF TEXAS|UNITED STATES|SCHOOL DISTRICT|\bISD\b|SAWS|CPS ENERGY|RIVER AUTHORITY|TXDOT|TEXAS DEPARTMENT|HOUSING AUTHORITY|HOMEOWNERS|HOME OWNER|PROPERTY OWNERS| HOA\b| POA\b)", re.I)

T4326_2278 = Transformer.from_crs("EPSG:4326","EPSG:2278",always_xy=True).transform

session = requests.Session()
session.headers.update({"User-Agent":"satx-land-map/parcel-discovery"})

errors = []
source_stats = defaultdict(int)

def clamp(x,a=0,b=100): return max(a,min(b,x))
def sat(x,k): return 100*(1-math.exp(-max(0,x)/k)) if k else 0

def haversine(lat1,lon1,lat2,lon2):
    r=3958.7613
    p1,p2=math.radians(lat1),math.radians(lat2)
    dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))

def point_geom(node):
    return {"x":node["lng"],"y":node["lat"],"spatialReference":{"wkid":4326}}

def arc_query(url, *, where="1=1", geom=None, geom_type="esriGeometryPoint",
              distance=None, units="esriSRUnit_Meter", out_fields="*",
              return_geometry=True, page_size=2000, timeout=50):
    params={
        "f":"geojson","where":where,"outFields":out_fields,
        "returnGeometry":"true" if return_geometry else "false",
        "outSR":"4326","resultRecordCount":str(page_size)
    }
    if geom is not None:
        params.update({
            "geometry":json.dumps(geom,separators=(",",":")) if isinstance(geom,dict) else geom,
            "geometryType":geom_type,"inSR":"4326",
            "spatialRel":"esriSpatialRelIntersects"
        })
        if distance is not None:
            params["distance"]=str(distance)
            params["units"]=units
    features=[]; offset=0
    for _ in range(8):
        params["resultOffset"]=str(offset)
        try:
            r=session.get(url,params=params,timeout=timeout)
            r.raise_for_status()
            data=r.json()
        except Exception as e:
            raise RuntimeError(f"{url}: {e}")
        if "error" in data:
            raise RuntimeError(f"{url}: {data['error']}")
        batch=data.get("features",[])
        features.extend(batch)
        exceeded=bool(data.get("exceededTransferLimit"))
        if len(batch)<page_size and not exceeded: break
        if not batch: break
        offset+=len(batch)
    source_stats[url]+=len(features)
    return features

def safe_query(label,url,**kwargs):
    try:
        return arc_query(url,**kwargs)
    except Exception as e:
        errors.append(f"{label}: {e}")
        return []

def props(f): return f.get("properties") or {}
def nval(p,*keys):
    for k in keys:
        v=p.get(k)
        if v not in (None,""):
            try: return float(str(v).replace(",",""))
            except: pass
    return 0.0

def sval(p,*keys):
    for k in keys:
        v=p.get(k)
        if v not in (None,""): return str(v).strip()
    return ""

def date_from_any(v):
    if v in (None,""): return None
    if isinstance(v,(int,float)):
        try: return datetime.fromtimestamp(v/1000,tz=timezone.utc)
        except: return None
    s=str(v).strip()
    for fmt in ("%Y-%m-%d","%m/%d/%Y","%Y/%m/%d","%m-%d-%Y"):
        try: return datetime.strptime(s[:10],fmt).replace(tzinfo=timezone.utc)
        except: pass
    return None

def feature_shape(f):
    try:
        g=f.get("geometry")
        return shape(g) if g else None
    except: return None

def proj(g):
    try: return transform(T4326_2278,g)
    except: return None

def road_name(p):
    candidates=["FULLNAME","FullName","StreetName","STREETNAME","STREET_NAME","ROAD_NAME","RoadName","NAME","Name","RD_NAME","ST_NAME"]
    for k in candidates:
        if p.get(k): return str(p[k]).strip()
    for k,v in p.items():
        if isinstance(v,str) and v.strip() and re.search(r"(name|street|road)",k,re.I):
            return v.strip()
    return ""

def road_class(p):
    vals=[]
    for k,v in p.items():
        if isinstance(v,str) and re.search(r"(function|class|type|route|system)",k,re.I):
            vals.append(v)
    return " | ".join(vals)

def flu_score(name):
    s=(name or "").lower()
    if re.search(r"regional.*(commercial|center)|commercial|mixed use|urban mixed",s): return 100
    if re.search(r"business park|industrial|specialized center",s): return 84
    if re.search(r"neighborhood.*(commercial|mixed)|community.*(commercial|mixed)",s): return 88
    if "residential" in s: return 45
    if re.search(r"open space|park|agric|rural|natural",s): return 25
    return 55

def normalize_owner(s):
    s=re.sub(r"[^A-Z0-9 ]"," ",(s or "").upper())
    s=re.sub(r"\b(LLC|L L C|INC|CORP|CORPORATION|LTD|LP|L P|TRUST|TR|ET AL|ETAL|PARTNERSHIP|HOLDINGS|PROPERTIES|PROPERTY)\b"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def geometry_shape_metrics(poly2278):
    if not poly2278 or poly2278.is_empty: return (40,0,0)
    area=poly2278.area; per=poly2278.length
    comp=4*math.pi*area/(per*per) if per else 0
    try:
        rect=poly2278.minimum_rotated_rectangle
        coords=list(rect.exterior.coords)
        lens=[Point(coords[i]).distance(Point(coords[i+1])) for i in range(4)]
        long=max(lens); short=max(1,min(lens)); aspect=long/short
    except:
        aspect=10
    score=clamp(comp*160,20,100)
    if aspect>5: score-=min(40,(aspect-5)*7)
    return (clamp(score),comp,aspect)

def parcel_distance_score(mi):
    if mi<=0.10: return 100
    if mi<=0.25: return 97
    if mi<=0.50: return 90
    if mi<=0.75: return 78
    if mi<=1.00: return 66
    if mi<=1.50: return 38
    return 10

def acreage_score(a):
    if 5<=a<=50: return 100
    if 3<=a<5: return 86
    if 50<a<=100: return 92
    if 100<a<=200: return 80
    return 66

def raw_land_score(p,a):
    tot=max(1,nval(p,"TotVal","Market_val"))
    impr=nval(p,"ImprVal","Imprv_hstd_val")+nval(p,"Imprv_non_hstd_val")
    ratio=impr/tot
    gba=nval(p,"TOT_GBA","GBA","Sq_ft")
    houses=nval(p,"Houses","Num_Units")
    s=100-min(65,ratio*120)
    if a>0: s-=min(35,(gba/a)/600)
    if houses>1: s-=min(35,(houses-1)*8)
    return clamp(s),ratio,gba

def nearest_catalyst(lat,lng):
    best=None
    for c in CATALYSTS:
        d=haversine(lat,lng,c["lat"],c["lng"])
        if best is None or d<best[0]: best=(d,c["name"])
    return best or (99,"")

def node_support(node):
    support={"plats":[],"permits":[],"traffic":[],"roads":[],"mtp":[],"fema":[],"flu":[],"cip":[]}
    # Plat stages within 5 mi.
    for layer,stage_w in PLAT_LAYERS.items():
        feats=safe_query(f"plats-{layer}",f"{BEXAR}/{layer}/query",geom=point_geom(node),distance=8046.72,
                         out_fields="*",return_geometry=True)
        for f in feats: f["_stage_weight"]=stage_w
        support["plats"].extend(feats)
    support["permits"]=safe_query("permits",PERMITS_URL,geom=point_geom(node),distance=4828.032,
                                  out_fields="*",return_geometry=True)
    support["traffic"]=safe_query("aadt",AADT_URL,geom=point_geom(node),distance=3218.688,
                                  out_fields="*",return_geometry=True)
    support["roads"]=safe_query("cosa-streets",STREETS_URL,geom=point_geom(node),distance=3218.688,
                                out_fields="*",return_geometry=True)
    support["roads"]+=safe_query("county-roads",COUNTY_ROADS_URL,geom=point_geom(node),distance=3218.688,
                                 out_fields="*",return_geometry=True)
    support["mtp"]=safe_query("mtp",COSA_MTP_URL,geom=point_geom(node),distance=3218.688,
                              out_fields="*",return_geometry=True)
    support["fema"]=safe_query("fema",FEMA_URL,geom=point_geom(node),distance=3218.688,
                               out_fields="*",return_geometry=True)
    support["flu"]=safe_query("flu",FLU_URL,geom=point_geom(node),distance=2414.016,
                              out_fields="*",return_geometry=True)
    support["cip"]=safe_query("saws-cip-points",SAWS_CIP_POINT,geom=point_geom(node),distance=1609.344,
                              out_fields="*",return_geometry=True)
    support["cip"]+=safe_query("saws-cip-polys",SAWS_CIP_POLY,geom=point_geom(node),distance=1609.344,
                               out_fields="*",return_geometry=True)
    return support

def score_node(node,support):
    now=datetime.now(timezone.utc)
    res=comm=recent=0.0
    for f in support["plats"]:
        p=props(f)
        if p.get("RETIRED_DT"): continue
        g=feature_shape(f)
        if not g or g.is_empty: continue
        c=g.centroid
        d=haversine(node["lat"],node["lng"],c.y,c.x)
        dw=1 if d<=1 else .75 if d<=3 else .45 if d<=5 else 0
        sw=f.get("_stage_weight",.5)
        if sw>=1:
            rd=date_from_any(p.get("PLAT_RCRD_DT"))
            if rd and (now-rd).days>365*5: continue
        r=nval(p,"NBR_NEW_SINGLE_LOTS")
        cm=nval(p,"NBR_NEW_COMMERCIAL_LOTS")
        res+=r*sw*dw; comm+=cm*sw*dw
        ed=date_from_any(p.get("last_edited_date")) or date_from_any(p.get("INIT_SUBMIT_DT"))
        if ed and (now-ed).days<=180: recent+=r*sw*dw
    net_units=res_permits=0
    for f in support["permits"]:
        p=props(f)
        total=nval(p,"housingunitstotal"); exist=nval(p,"housingunitsexist")
        net=max(0,total-exist)
        net_units+=net
        txt=" ".join([sval(p,"permittypemapped"),sval(p,"permitclassmapped"),sval(p,"workclass"),sval(p,"proposeduse"),sval(p,"landusedescription")]).lower()
        if "residen" in txt or "single family" in txt or net>0: res_permits+=1
    best_aadt=best_growth=0
    for f in support["traffic"]:
        p=props(f)
        cur=nval(p,"AADT_RPT_CURR_QTY","AADT_2025","AADT")
        old=nval(p,"AADT_RPT_HIST_05_QTY","AADT_2020")
        if cur>best_aadt:
            best_aadt=cur
            best_growth=((cur-old)/old*100) if old else 0
    catalyst_d,catalyst_name=nearest_catalyst(node["lat"],node["lng"])
    housing=sat(res,2200)
    permit=sat(net_units+res_permits*.5,250)
    volume=clamp(best_aadt/500)
    growth=clamp((best_growth+5)*4)
    traffic=.7*volume+.3*growth
    gap=clamp(45 + sat(res,1800)*.55 - sat(comm,30)*.45)
    momentum=.65*sat(recent,700)+.35*permit
    catalyst=100 if catalyst_d<=1 else 85 if catalyst_d<=2 else 65 if catalyst_d<=4 else 35
    score=.15*node["base"]+.27*housing+.14*permit+.15*traffic+.12*gap+.11*momentum+.06*catalyst
    return {
        **node,"score":round(clamp(score),1),
        "weighted_future_res_lots":round(res,1),"weighted_future_commercial_lots":round(comm,1),
        "recent_progress_res_lots":round(recent,1),"net_new_housing_units_180d":round(net_units,1),
        "residential_permits_180d":int(res_permits),"aadt":int(best_aadt),"aadt_5yr_growth_pct":round(best_growth,1),
        "nearest_catalyst":catalyst_name,"catalyst_miles":round(catalyst_d,2)
    }

def query_parcels(node):
    return safe_query("bexar-parcels",PARCEL_URL,where="Acres >= 3",geom=point_geom(node),distance=2414.016,
                      out_fields="OBJECTID,PropID,Situs,Owner,DBA,LglDesc,LandVal,ImprVal,TotVal,GBA,TOT_GBA,YrBlt,Houses,LglAcres,Acres,PropUse",
                      return_geometry=True)

def make_candidate(feature,node_result):
    p=props(feature)
    owner=sval(p,"Owner")
    if PUBLIC_OWNER.search(owner): return None
    a=nval(p,"Acres","LglAcres")
    if a<3: return None
    g=feature_shape(feature)
    if not g or g.is_empty: return None
    gp=proj(g)
    if not gp or gp.is_empty: return None
    nodep=proj(Point(node_result["lng"],node_result["lat"]))
    edge_mi=gp.distance(nodep)/5280
    if edge_mi>1.5: return None
    raw,impr_ratio,gba=raw_land_score(p,a)
    # Hard pre-screen obvious improved residential/multifamily.
    if a<12 and impr_ratio>.55: return None
    if a<8 and gba/a>12000: return None
    houses=nval(p,"Houses")
    if a<12 and houses>=5: return None
    sh,compact,aspect=geometry_shape_metrics(gp)
    dist=parcel_distance_score(edge_mi); acre=acreage_score(a)
    pre=.38*node_result["score"]+.24*dist+.14*acre+.14*raw+.10*sh
    c=g.centroid
    return {
        "feature":feature,"prop_id":str(int(nval(p,"PropID"))) if nval(p,"PropID") else str(p.get("OBJECTID","")),
        "owner":owner,"owner_key":normalize_owner(owner),"situs":sval(p,"Situs"),
        "acres":round(a,2),"land_value":round(nval(p,"LandVal"),0),"assessed_value":round(nval(p,"TotVal"),0),
        "improvement_value":round(nval(p,"ImprVal"),0),"improvement_ratio":round(impr_ratio,3),
        "gba":round(gba,0),"prop_use":sval(p,"PropUse"),"legal":sval(p,"LglDesc"),
        "node_id":node_result["id"],"node_name":node_result["name"],"node_score":node_result["score"],
        "node_edge_miles":round(edge_mi,3),"centroid_lat":c.y,"centroid_lng":c.x,
        "dist_score":dist,"acre_score":acre,"raw_score":round(raw,1),"shape_score":round(sh,1),
        "compactness":round(compact,3),"aspect_ratio":round(aspect,2),"preliminary_score":round(pre,1),
        "_geom2278":gp
    }

def road_quality(c,support):
    poly=c["_geom2278"]; boundary=poly.boundary
    roads=[]; frontage=0; major=False
    for f in support["roads"]:
        g=feature_shape(f)
        if not g: continue
        gp=proj(g)
        if not gp: continue
        d=boundary.distance(gp)
        if d<=90:
            p=props(f); name=road_name(p) or "Unnamed road"; cls=road_class(p)
            try: near_len=boundary.intersection(gp.buffer(55)).length
            except: near_len=0
            roads.append((name,cls,d,near_len))
            frontage+=near_len
            if re.search(r"arterial|collector|express|principal|major|interstate|highway|state|us |fm |loop",name+" "+cls,re.I):
                major=True
    unique=[]
    seen=set()
    for name,cls,d,l in sorted(roads,key=lambda x:x[2]):
        k=name.upper()
        if k not in seen:
            unique.append((name,cls,d,l)); seen.add(k)
    corner=len(unique)>=2
    mtp_cross=False
    for f in support["mtp"]:
        g=feature_shape(f); gp=proj(g) if g else None
        if gp and gp.distance(poly)<=60:
            mtp_cross=True; break
    if corner and major: score=100
    elif major and frontage>=200: score=92
    elif major: score=84
    elif corner: score=84
    elif frontage>=200: score=78
    elif unique: score=66
    else: score=20
    return round(score,1),[x[0] for x in unique[:4]],round(frontage,0),corner,major,mtp_cross

def flood_quality(c,support):
    poly=c["_geom2278"]; area=max(1,poly.area)
    sfha_area=fw_area=0
    zones=set()
    for f in support["fema"]:
        g=feature_shape(f); gp=proj(g) if g else None
        if not gp or not gp.intersects(poly): continue
        p=props(f); z=sval(p,"FLD_ZONE"); sub=sval(p,"ZONE_SUBTY").lower()
        is_fw="floodway" in sub
        is_sfha=sval(p,"SFHA_TF").upper()=="T" or z in {"A","AE","AH","AO","A99","V","VE"}
        try: ia=gp.intersection(poly).area
        except: ia=0
        if z: zones.add(z)
        if is_sfha: sfha_area+=ia
        if is_fw: fw_area+=ia
    sfha=min(100,sfha_area/area*100); fw=min(100,fw_area/area*100)
    score=100
    if fw>=10: score=10
    elif fw>0: score=45
    elif sfha>=50: score=30
    elif sfha>=25: score=55
    elif sfha>0: score=75
    return round(score,1),round(sfha,1),round(fw,1),sorted(zones)

def land_use_quality(c,support):
    poly=c["_geom2278"]; best=55; names=[]
    for f in support["flu"]:
        g=feature_shape(f); gp=proj(g) if g else None
        if not gp or not gp.intersects(poly): continue
        p=props(f)
        name=" / ".join(x for x in [sval(p,"LandUse"),sval(p,"CenterTiers"),sval(p,"PlanName")] if x)
        if name:
            names.append(name); best=max(best,flu_score(name))
    return round(best,1),names[:3]

def traffic_for_parcel(c,support):
    best=None
    for f in support["traffic"]:
        g=feature_shape(f)
        if not g: continue
        ctr=g.centroid
        d=haversine(c["centroid_lat"],c["centroid_lng"],ctr.y,ctr.x)
        p=props(f); cur=nval(p,"AADT_RPT_CURR_QTY","AADT_2025","AADT"); old=nval(p,"AADT_RPT_HIST_05_QTY","AADT_2020")
        if best is None or d<best[0]:
            growth=((cur-old)/old*100) if old else 0
            best=(d,cur,growth)
    if not best: return 0,0,99
    return int(best[1]),round(best[2],1),round(best[0],2)

def value_score(c):
    v=c["assessed_value"]/c["acres"] if c["acres"] else 0
    c["assessed_value_per_acre"]=round(v,0)
    lv=c["land_value"]/c["acres"] if c["acres"] else 0
    c["land_value_per_acre"]=round(lv,0)
    if not v: return 50
    if v<=50000: return 90
    if v<=100000: return 80
    if v<=200000: return 65
    if v<=350000: return 50
    return 35

def enrich_candidate(c,support,node_result):
    road_score,roads,frontage,corner,major,mtp=road_quality(c,support)
    flood_score,flood_pct,fw_pct,zones=flood_quality(c,support)
    flu,flu_names=land_use_quality(c,support)
    aadt,growth,aadt_dist=traffic_for_parcel(c,support)
    val=value_score(c)
    catalyst_d,catalyst_name=nearest_catalyst(c["centroid_lat"],c["centroid_lng"])
    traffic_score=clamp(aadt/500*.7 + clamp((growth+5)*4)*.3)
    score=(.22*c["node_score"]+.18*c["dist_score"]+.18*road_score+.10*c["acre_score"]+
           .10*c["raw_score"]+.08*flood_score+.05*c["shape_score"]+.04*flu+.03*traffic_score+.02*val)
    eligible=(c["acres"]>=3 and c["node_edge_miles"]<=1.0 and road_score>=65 and c["raw_score"]>=55
              and fw_pct<10 and flood_pct<50 and flu>=35 and c["shape_score"]>=25)
    reasons=[]
    if corner and major: reasons.append("corner exposure on a major road")
    elif major: reasons.append("major-road frontage")
    elif roads: reasons.append("road frontage")
    if c["node_edge_miles"]<=.25: reasons.append("within ¼ mile of priority intersection")
    elif c["node_edge_miles"]<=.5: reasons.append("within ½ mile of priority intersection")
    else: reasons.append("within 1 mile of priority intersection")
    if node_result["weighted_future_res_lots"]>=800: reasons.append(f"{int(node_result['weighted_future_res_lots'])} weighted future residential lots nearby")
    if catalyst_d<=2.5: reasons.append(f"{catalyst_d:.1f} mi from {catalyst_name}")
    if c["raw_score"]>=80: reasons.append("mostly raw / low-improvement land")
    if flood_pct==0: reasons.append("no mapped FEMA SFHA overlap returned")
    c.update({
        "road_score":road_score,"frontage_roads":roads,"frontage_ft_proxy":frontage,
        "corner_signal":"STRONG" if corner and major else "YES" if corner else "NO",
        "major_road_signal":major,"mtp_row_flag":mtp,
        "flood_score":flood_score,"flood_pct":flood_pct,"floodway_pct":fw_pct,"flood_zones":zones,
        "future_land_use_score":flu,"future_land_use":flu_names,
        "aadt":aadt,"aadt_5yr_growth_pct":growth,"aadt_station_miles":aadt_dist,
        "nearest_retail_catalyst":catalyst_name,"retail_catalyst_miles":round(catalyst_d,2),
        "future_residential_lots_nearby":node_result["weighted_future_res_lots"],
        "recent_housing_units_180d":node_result["net_new_housing_units_180d"],
        "utility_confidence":"PROXY" if support["cip"] else "UNKNOWN",
        "utility_context":f"{len(support['cip'])} mapped SAWS CIP feature(s) within 1 mi of node; capacity NOT verified" if support["cip"] else "No parcel-level capacity verification; request SAWS as-builts and written capacity",
        "parcel_opportunity_score":round(clamp(score),1),"eligible":eligible,
        "why_this_tract":" · ".join(reasons[:4]),
        "verification_notes":"Road frontage is a GIS proximity/overlap proxy, not legal access. Flood is FEMA screening. Utilities are not verified. Confirm survey, title, access, ROW and capacity."
    })
    return c

def sara_enrich(c):
    pid=c["prop_id"]
    if not pid or not pid.isdigit(): return
    feats=safe_query("sara-bcad-enrich",SARA_BCAD_URL,where=f"Prop_id={pid}",out_fields="*",return_geometry=True,page_size=10,timeout=30)
    if not feats: return
    f=feats[0]; p=props(f)
    c["bcad_geometry_verified"]=True
    c["geometry_source"]="SARA / BCAD parcel service"
    c["bcad_geo_id"]=sval(p,"Geo_id")
    c["ownership_type"]=sval(p,"Ownership_Type")
    dd=p.get("Last_Deed_Date")
    dt=date_from_any(dd)
    if dt:
        c["last_deed_date"]=dt.date().isoformat()
        c["hold_years"]=round((datetime.now(timezone.utc)-dt).days/365.25,1)
    g=feature_shape(f)
    if g and not g.is_empty:
        c["feature"]["geometry"]=mapping(g)
else_dummy = None

def select_top(candidates,limit=30,node_cap=4):
    candidates=sorted([x for x in candidates if x["eligible"]],key=lambda x:x["parcel_opportunity_score"],reverse=True)
    out=[]; counts=defaultdict(int)
    for c in candidates:
        if counts[c["node_id"]]>=node_cap: continue
        out.append(c); counts[c["node_id"]]+=1
        if len(out)>=limit: break
    return out

def assemblages(candidates):
    pool=[c for c in candidates if c["eligible"] and c["owner_key"]]
    groups=defaultdict(list)
    for c in pool: groups[c["owner_key"]].append(c)
    feats=[]
    for owner,arr in groups.items():
        if len(arr)<2: continue
        used=set()
        for i,c in enumerate(arr):
            if i in used: continue
            comp=[i]; used.add(i); changed=True
            while changed:
                changed=False
                for j,d in enumerate(arr):
                    if j in used: continue
                    if any(arr[k]["_geom2278"].distance(d["_geom2278"])<=30 for k in comp):
                        comp.append(j); used.add(j); changed=True
            if len(comp)<2: continue
            members=[arr[k] for k in comp]
            total=sum(x["acres"] for x in members)
            if total<3: continue
            geom=unary_union([feature_shape(x["feature"]) for x in members])
            score=sum(x["parcel_opportunity_score"] for x in members)/len(members)+min(8,math.log2(len(members)+1)*2)
            feats.append({"type":"Feature","geometry":mapping(geom),"properties":{
                "owner":members[0]["owner"],"owner_key":owner,"parcel_ids":[x["prop_id"] for x in members],
                "parcel_count":len(members),"combined_acres":round(total,2),
                "nearest_intersection":max(members,key=lambda x:x["node_score"])["node_name"],
                "assemblage_score":round(clamp(score),1),
                "underlying_parcels_remain_identifiable":True
            }})
    return sorted(feats,key=lambda f:f["properties"]["assemblage_score"],reverse=True)

def public_props(c,rank=None):
    keys=[
      "prop_id","owner","situs","acres","land_value","assessed_value","improvement_value","improvement_ratio","gba",
      "prop_use","legal","node_id","node_name","node_score","node_edge_miles","dist_score","acre_score","raw_score",
      "shape_score","compactness","aspect_ratio","road_score","frontage_roads","frontage_ft_proxy","corner_signal",
      "major_road_signal","mtp_row_flag","flood_score","flood_pct","floodway_pct","flood_zones","future_land_use_score",
      "future_land_use","aadt","aadt_5yr_growth_pct","aadt_station_miles","nearest_retail_catalyst","retail_catalyst_miles",
      "future_residential_lots_nearby","recent_housing_units_180d","utility_confidence","utility_context",
      "assessed_value_per_acre","land_value_per_acre","parcel_opportunity_score","eligible","why_this_tract",
      "verification_notes","bcad_geometry_verified","geometry_source","bcad_geo_id","ownership_type","last_deed_date","hold_years"
    ]
    p={k:c.get(k) for k in keys if k in c}
    if rank is not None: p["rank"]=rank
    return p

def main():
    print("Analyzing nodes...")
    supports={}; node_results=[]
    for idx,node in enumerate(NODES,1):
        print(f"[{idx}/{len(NODES)}] {node['name']}")
        sup=node_support(node); supports[node["id"]]=sup
        node_results.append(score_node(node,sup))
    node_results.sort(key=lambda x:x["score"],reverse=True)
    node_by={x["id"]:x for x in node_results}

    print("Querying parcel universe...")
    by_pid={}
    for node in node_results:
        feats=query_parcels(node)
        for f in feats:
            c=make_candidate(f,node)
            if not c: continue
            old=by_pid.get(c["prop_id"])
            if old is None or c["preliminary_score"]>old["preliminary_score"]:
                by_pid[c["prop_id"]]=c
    candidates=sorted(by_pid.values(),key=lambda x:x["preliminary_score"],reverse=True)[:180]
    print(f"Base candidates: {len(candidates)}")

    print("Enriching parcel quality...")
    enriched=[]
    for i,c in enumerate(candidates,1):
        if i%20==0: print(f"  {i}/{len(candidates)}")
        enriched.append(enrich_candidate(c,supports[c["node_id"]],node_by[c["node_id"]]))

    top=select_top(enriched,30,4)
    print(f"Eligible highlighted parcels: {len(top)}")
    for c in top:
        sara_enrich(c)

    # Stable rank after SARA enrichment.
    top.sort(key=lambda x:x["parcel_opportunity_score"],reverse=True)
    for i,c in enumerate(top,1): c["rank"]=i

    fc={"type":"FeatureCollection","features":[
        {"type":"Feature","geometry":c["feature"]["geometry"],"properties":public_props(c,i)}
        for i,c in enumerate(top,1)
    ]}
    (DATA/"opportunity_parcels.geojson").write_text(json.dumps(fc,indent=2))
    all_fc={"type":"FeatureCollection","features":[
        {"type":"Feature","geometry":c["feature"]["geometry"],"properties":public_props(c)}
        for c in sorted(enriched,key=lambda x:x["parcel_opportunity_score"],reverse=True)[:120]
    ]}
    (DATA/"opportunity_parcels_all.geojson").write_text(json.dumps(all_fc,indent=2))
    (DATA/"opportunity_nodes.json").write_text(json.dumps(node_results,indent=2))
    ass=assemblages(enriched)
    (DATA/"assemblages.geojson").write_text(json.dumps({"type":"FeatureCollection","features":ass},indent=2))

    cols=["rank","parcel_opportunity_score","owner","prop_id","situs","acres","node_name","node_edge_miles",
          "frontage_roads","corner_signal","raw_score","future_residential_lots_nearby","aadt","aadt_5yr_growth_pct",
          "nearest_retail_catalyst","flood_pct","floodway_pct","future_land_use","assessed_value","assessed_value_per_acre",
          "land_value_per_acre","last_deed_date","hold_years","utility_confidence","why_this_tract","verification_notes"]
    with (DATA/"tracts_to_review.csv").open("w",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=cols); w.writeheader()
        for c in top:
            row={k:c.get(k,"") for k in cols}
            for k in ("frontage_roads","future_land_use"):
                if isinstance(row[k],list): row[k]=" | ".join(map(str,row[k]))
            w.writerow(row)

    meta={
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "generator":"scripts/generate_opportunities.py",
      "node_count":len(node_results),"candidate_count":len(enriched),"highlighted_count":len(top),
      "assemblage_count":len(ass),
      "sources":{
        "parcels":"Bexar County Public Works PlatsMDPs parcel layer; top parcels optionally re-verified against SARA/BCAD",
        "plats":"Bexar County Public Works Plat Applications / Working / Staff Accepted / CC Approved / Recorded",
        "permits":"City of San Antonio Building Permits Issued Past 180 Days",
        "traffic":"TxDOT AADT Annuals Public View",
        "roads":"CoSA Streets + Bexar County Roads + CoSA Major Thoroughfare Plan",
        "flood":"FEMA NFHL flood hazard polygons",
        "land_use":"City of San Antonio Future Land Use",
        "utilities":"SAWS CIP proximity proxy only; capacity unverified"
      },
      "errors":errors[:100],"source_feature_counts":dict(source_stats),
      "methodology":{
        "parcel_query_radius_miles":1.5,"hard_highlight_distance_miles":1.0,"min_acres":3,
        "top_limit":30,"per_node_cap":4,
        "yellow_gate":"3+ ac; <=1 mi by parcel-edge distance; road signal >=65; raw-land >=55; <10% floodway; <50% SFHA; FLU >=35; shape >=25"
      }
    }
    (DATA/"opportunity_metadata.json").write_text(json.dumps(meta,indent=2))
    print(json.dumps({"highlighted":len(top),"assemblages":len(ass),"errors":len(errors)},indent=2))

if __name__=="__main__":
    main()
