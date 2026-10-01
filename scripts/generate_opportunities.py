#!/usr/bin/env python3
import csv, json, math, os, re, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
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
COMAL_PARCEL_URL = "https://services7.arcgis.com/Q6vsXnxTnYcWB7qg/arcgis/rest/services/COMAL_PARCELS/FeatureServer/0/query"
GUADALUPE_PARCEL_URL = "https://maps.pape-dawson.com/server1/rest/services/LandDevelopment/LANDDEVELOPMENT__Lennar_SiteSelection/MapServer/83/query"
TXDOT_ROADS_URL = "https://services.arcgis.com/KTcxiTD9dsQw4r7Z/ArcGIS/rest/services/TxDOT_Roadways/FeatureServer/0/query"
SAWS_SEWER_URL = "https://maps.pape-dawson.com/server1/rest/services/LandDevelopment/LANDDEVELOPMENT__GreaterSATX/MapServer/28/query"
NBU_SEWER_URL = "https://maps.pape-dawson.com/server1/rest/services/LandDevelopment/LANDDEVELOPMENT__Hines_SiteSelection/MapServer/512/query"
GBRA_GRAVITY_URL = "https://maps.pape-dawson.com/server2/rest/services/PD_GIS_Webmap/PD_GIS_WebMap__SanAntonio_External/MapServer/170/query"
GBRA_FORCE_URL = "https://maps.pape-dawson.com/server2/rest/services/PD_GIS_Webmap/PD_GIS_WebMap__SanAntonio_External/MapServer/172/query"
NBU_LIVE_PARCELS_URL = "https://services6.arcgis.com/OCHBpyHMBFOeBqny/ArcGIS/rest/services/NBU_Parcels_live/FeatureServer/0/query"
GBRA_LIVE_PARCELS_URL = "https://services6.arcgis.com/OCHBpyHMBFOeBqny/ArcGIS/rest/services/GBRA_Parcels_live/FeatureServer/0/query"

NODE_COUNTIES = {
  "INT-002":"Comal",
  "INT-007":"Comal",
  "INT-022":"Comal",
  "INT-015":"Guadalupe",
  "INT-025":"Guadalupe",
  "INT-019":"Medina",
  "INT-023":"Kendall",
}

PARCEL_SOURCE_INFO = {
  "Bexar":{"label":"SARA / Bexar CAD","snapshot":"2025-12","freshness":"RECENT"},
  "Comal":{"label":"Comal CAD public ArcGIS parcel layer","snapshot":"2024-11-22","freshness":"AGING"},
  "Guadalupe":{"label":"Guadalupe CAD via TxGIO public extract","snapshot":"2022-02","freshness":"STALE"},
}

NODES = [
 {"id":"INT-002","name":"I-35 / Kohlenberg Rd (Mayfair)","lat":29.748,"lng":-98.079,"base":90},
 {"id":"INT-001","name":"Culebra Rd / SH 211","lat":29.522725,"lng":-98.805837,"base":89},
 {"id":"INT-003","name":"I-10 / Loop 1604 East","lat":29.514,"lng":-98.312,"base":88},
 {"id":"INT-004","name":"US 90 / SH 211","lat":29.3748152,"lng":-98.7651618,"base":86},
 {"id":"INT-005","name":"Potranco Rd / SH 211","lat":29.4212674,"lng":-98.7826287,"base":84},
 {"id":"INT-009","name":"Schuwirth Rd / Loop 1604 East","lat":29.456,"lng":-98.2879,"base":82},
 {"id":"INT-006","name":"FM 1518 / I-10","lat":29.4879614,"lng":-98.2236575,"base":81},
 {"id":"INT-007","name":"Loop 337 / Word Pkwy (Veramendi)","lat":29.736,"lng":-98.179,"base":81},
 {"id":"INT-010","name":"FM 1516 / I-10 East","lat":29.4587922,"lng":-98.3171707,"base":81},
 {"id":"INT-011","name":"US 90 / Loop 1604 West","lat":29.394,"lng":-98.682,"base":81},
 {"id":"INT-012","name":"SH 211 / Briggs Ranch Rd","lat":29.410,"lng":-98.813,"base":79},
 {"id":"INT-013","name":"S Zarzamora / Mitra Way (VIDA)","lat":29.318,"lng":-98.530,"base":79},
 {"id":"INT-014","name":"FM 1518 / Lower Seguin Rd","lat":29.5237,"lng":-98.2462,"base":78},
 {"id":"INT-015","name":"FM 1103 / Orth Rd","lat":29.597,"lng":-98.228,"base":77},
 {"id":"INT-016","name":"Loop 1604 / Green Rd","lat":29.496,"lng":-98.293,"base":74},
 {"id":"INT-017","name":"Texas Research Pkwy / SH 211","lat":29.435,"lng":-98.797,"base":73},
 {"id":"INT-019","name":"US 90 / FM 471 (Castroville)","lat":29.3557074,"lng":-98.8714514,"base":72},
 {"id":"INT-018","name":"Louis Bauer Dr / Laser Dr (Brooks)","lat":29.346,"lng":-98.443,"base":72},
 {"id":"INT-022","name":"SH 46 / FM 1863","lat":29.7213978,"lng":-98.1781374,"base":71},
 {"id":"INT-023","name":"Old San Antonio Rd / Cascade Caverns Rd","lat":29.744,"lng":-98.686,"base":65},
 {"id":"INT-020","name":"Applewhite Rd / Lone Star Pass","lat":29.297,"lng":-98.552,"base":64},
 {"id":"INT-021","name":"Chavaneaux Rd / S Zarzamora","lat":29.284,"lng":-98.529,"base":61},
 {"id":"INT-025","name":"I-10 / SH 46 (Seguin Exchange)","lat":29.5843613,"lng":-97.9932498,"base":80},
 {"id":"INT-024","name":"Talley Rd / Potranco Rd","lat":29.414,"lng":-98.744,"base":78},
]

CATALYSTS = [
 {"name":"Culebra / SH 211 H-E-B","lat":29.524162,"lng":-98.802373},
 {"name":"I-10 / Loop 1604 East H-E-B","lat":29.514,"lng":-98.312},
 {"name":"Mayfair Costco","lat":29.747031,"lng":-98.056017},
 {"name":"Veramendi mixed-use / future Market Center","lat":29.736,"lng":-98.179},
 {"name":"Seguin Exchange / planned Target","lat":29.5843613,"lng":-97.9932498},
 {"name":"H-E-B Foster campus","lat":29.41984,"lng":-98.36083},
]

PUBLIC_OWNER = re.compile(r"(CITY OF|COUNTY OF|(BEXAR|COMAL|GUADALUPE|MEDINA|KENDALL|WILSON|ATASCOSA) COUNTY|STATE OF TEXAS|UNITED STATES|US GOVERNMENT|U S GOVERNMENT|SCHOOL DISTRICT|ISD|I S D|SCHOOL|MONTESSORI|ACADEMY|SAWS|CPS ENERGY|RIVER AUTHORITY|TXDOT|TEXAS DEPARTMENT|HOUSING AUTHORITY|HOUSING TRUST|PUBLIC FACILITY CORPORATION|PUBLIC FACILITY CORP|DEVELOPMENT AUTHORITY|FIRE AND RESCUE|EMERGENCY SERVICES DISTRICT|ESD|UNIVERSITY SYSTEM|UNIVERSITY OF|TEXAS A.*M|HOMEOWNERS|HOME OWNER|PROPERTY OWNERS|OWNERS ASSN|OWNERS ASSOCIATION|PLACE ASSOCIATION|MASTER COMMUNITY|LAND TRUST|HOSPITAL|HEALTHCARE SYSTEM|MEDICAL CENTER| HOA| POA)", re.I)
ANCHOR_OWNER = re.compile(r"(HEB GROCERY|H E B GROCERY|WAL.?MART|WALMART|COSTCO|TARGET CORPORATION|LOWE.?S|HOME DEPOT)", re.I)
INSTITUTIONAL_OWNER = re.compile(r"(CHURCH|MINISTR|TEMPLE|DIOCESE|PARISH|SYNAGOGUE|MOSQUE|FOUNDATION|BOYSVILLE|YMCA|Y W C A|SALVATION ARMY|BAPTIST|METHODIST|CATHOLIC|LUTHERAN|PRESBYTERIAN|EPISCOPAL|PREGNANCY CARE|CHARITY)", re.I)
RESIDENTIAL_BUILDER_OWNER = re.compile(r"(KB HOME|KB HOMES|CONTINENTAL HOMES|D\s*R\s*HORTON|DR HORTON|LENNAR|PULTE|CENTEX|MERITAGE|PERRY HOMES|CASTLEROCK|CHESMAR|DAVID WEEKLEY|TOLL BROTHERS|M/I HOMES|MI HOMES)", re.I)
OPERATING_USER_OWNER = re.compile(r"(LOVE.?S TRAVEL|QUIKTRIP|QT SOUTH|BUC.?EE|PILOT|FLYING J|DOGGETT|FREIGHTLINER|COUNTERTOPS|MURPHY USA|7.?ELEVEN|CIRCLE K|STRIPES|LOCK AWAY|SELF STORAGE|STORAGE LLC|STORAGE INC)", re.I)

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

def envelope_geom(node, miles):
    dy=miles/69.0
    dx=miles/(69.0*max(0.25,math.cos(math.radians(node["lat"]))))
    return {"xmin":node["lng"]-dx,"ymin":node["lat"]-dy,
            "xmax":node["lng"]+dx,"ymax":node["lat"]+dy,
            "spatialReference":{"wkid":4326}}

def arc_query(url, *, where="1=1", geom=None, geom_type="esriGeometryPoint",
              distance=None, units="esriSRUnit_Meter", out_fields="*",
              return_geometry=True, page_size=2000, timeout=18):
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
        data=None; last_error=None
        for attempt in range(3):
            try:
                r=session.get(url,params=params,timeout=timeout)
                r.raise_for_status()
                data=r.json()
                break
            except Exception as e:
                last_error=e
                if attempt<2: time.sleep(.7*(attempt+1))
        if data is None:
            raise RuntimeError(f"{url}: {last_error}")
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

def clean_road_label(v):
    s=str(v or "").strip().upper()
    if not s: return ""
    # TxDOT route codes often include roadway-direction suffixes, e.g. FM1102-KG or IH0035-RP.
    m=re.match(r"^(IH|US|SH|FM|SL|LP)0*(\d+)(?:-[A-Z0-9]+)?$",s.replace(" ",""))
    if m:
        prefix={"IH":"IH","US":"US","SH":"SH","FM":"FM","SL":"SL","LP":"LOOP"}.get(m.group(1),m.group(1))
        return f"{prefix} {int(m.group(2))}"
    return str(v or "").strip()

def road_name(p):
    candidates=["RTE_NM","MAP_LBL","FULLNAME","FullName","StreetName","STREETNAME","STREET_NAME","ROAD_NAME","RoadName","NAME","Name","RD_NAME","ST_NAME"]
    for k in candidates:
        if p.get(k): return clean_road_label(p[k])
    for k,v in p.items():
        if isinstance(v,str) and v.strip() and re.search(r"(name|street|road)",k,re.I):
            return clean_road_label(v)
    return ""

def road_class(p):
    vals=[]
    for k,v in p.items():
        if isinstance(v,str) and re.search(r"(function|class|type|route|system|rte_prfx|rdbd)",k,re.I):
            vals.append(v)
    return " | ".join(vals)

def road_importance(name,cls):
    n=(name or "").upper().strip(); t=(cls or "").upper()
    # Numbered routes and true highway designations. Do not treat every street ending in "Loop" as a highway.
    if re.search(r"\b(IH|I-|INTERSTATE)\s*[- ]?\d+\b|\bUS\s*(HWY|HIGHWAY)?\s*\d+\b|\bSH\s*\d+\b|\bSTATE\s+(HWY|HIGHWAY)\s*\d+\b|\bFM\s*\d+\b|\bLOOP\s*\d+\b",n):
        return 3
    if re.search(r"PRINCIPAL|ARTERIAL|EXPRESS|INTERSTATE|FREEWAY|HIGHWAY",t):
        return 3
    if re.search(r"COLLECTOR",t) or re.search(r"\b(PKWY|PARKWAY|EXPY|EXPRESSWAY)\b",n):
        return 2
    if name and name!="Unnamed road":
        return 1
    return 0

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

def node_county(node):
    return NODE_COUNTIES.get(node.get("id"),"Bexar")

def raw_land_score_values(total,impr,a,gba=0,houses=0):
    tot=max(1,float(total or 0))
    impr=float(impr or 0)
    ratio=impr/tot
    s=100-min(65,ratio*120)
    if a>0 and gba:
        s-=min(35,(gba/a)/600)
    if houses>1:
        s-=min(35,(houses-1)*8)
    return clamp(s),ratio,float(gba or 0)

def normalized_parcel(feature,county):
    p=props(feature)
    if county=="Bexar":
        pid=str(int(nval(p,"PropID"))) if nval(p,"PropID") else str(p.get("OBJECTID",""))
        return {
          "prop_id":pid,"owner":sval(p,"Owner"),"situs":sval(p,"Situs"),
          "acres":nval(p,"Acres","LglAcres"),"land_value":nval(p,"LandVal"),
          "improvement_value":nval(p,"ImprVal"),"market_value":nval(p,"TotVal"),
          "gba":nval(p,"TOT_GBA","GBA"),"houses":nval(p,"Houses"),
          "prop_use":sval(p,"PropUse"),"legal":sval(p,"LglDesc"),"cad_record_url":""
        }
    if county=="Comal":
        return {
          "prop_id":sval(p,"PROP_ID","PARCELKEY","OBJECTID"),"owner":sval(p,"PY_OWNER_N"),
          "situs":sval(p,"SITUS_ADDR"),"acres":nval(p,"LEGAL_ACRE"),
          "land_value":nval(p,"LAND_HMSTD")+nval(p,"LAND_NON_H"),
          "improvement_value":nval(p,"IMPRV_VAL")+nval(p,"IMPROV_NON"),
          "market_value":nval(p,"APPRAISED","ASSESSED"),"gba":0,"houses":0,
          "prop_use":sval(p,"PROP_TYPE_"),"legal":sval(p,"LEGAL_DESC","LEGAL_DE_1"),
          "cad_record_url":sval(p,"CADLINK")
        }
    if county=="Guadalupe":
        unit=sval(p,"LGL_AREA_UNIT").upper()
        gis_unit=sval(p,"GIS_AREA_UNIT").upper()
        acres=nval(p,"LEGAL_AREA") if unit=="ACRES" else nval(p,"GIS_AREA") if gis_unit=="ACRES" else 0
        return {
          "prop_id":sval(p,"PROP_ID","OBJECTID"),"owner":sval(p,"OWNER_NAME"),
          "situs":sval(p,"SITUS_ADDR"),"acres":acres,
          "land_value":nval(p,"LAND_VALUE"),"improvement_value":nval(p,"IMP_VALUE"),
          "market_value":nval(p,"MKT_VALUE"),"gba":0,"houses":0,
          "prop_use":sval(p,"LOC_LAND_USE","STAT_LAND_USE"),"legal":sval(p,"LEGAL_DESC"),
          "cad_record_url":""
        }
    return {}

def nearest_catalyst(lat,lng):
    best=None
    for c in CATALYSTS:
        d=haversine(lat,lng,c["lat"],c["lng"])
        if best is None or d<best[0]: best=(d,c["name"])
    return best or (99,"")

def node_support(node):
    county=node_county(node)
    support={"county":county,"plats":[],"permits":[],"traffic":[],"roads":[],"mtp":[],"fema":[],"flu":[],
             "utility":[],"utility_provider":"","utility_snapshot":""}

    # Detailed plat/permit/FLU signals are currently strongest in Bexar.
    if county=="Bexar":
        for layer,stage_w in PLAT_LAYERS.items():
            feats=safe_query(f"plats-{layer}",f"{BEXAR}/{layer}/query",geom=point_geom(node),distance=8046.72,
                             out_fields="*",return_geometry=True)
            for f in feats: f["_stage_weight"]=stage_w
            support["plats"].extend(feats)
        support["roads"]+=safe_query("cosa-streets",STREETS_URL,geom=point_geom(node),distance=3218.688,
                                     out_fields="*",return_geometry=True)
        support["roads"]+=safe_query("county-roads",COUNTY_ROADS_URL,geom=point_geom(node),distance=3218.688,
                                     out_fields="*",return_geometry=True)
        support["mtp"]=safe_query("mtp",COSA_MTP_URL,geom=point_geom(node),distance=3218.688,
                                  out_fields="*",return_geometry=True)
        support["flu"]=safe_query("flu",FLU_URL,geom=point_geom(node),distance=2414.016,
                                  out_fields="*",return_geometry=True)
        support["utility"]=safe_query("saws-sewer",SAWS_SEWER_URL,geom=point_geom(node),distance=3218.688,
                                      out_fields="*",return_geometry=True,page_size=2000,timeout=25)
        support["utility_provider"]="SAWS"
        support["utility_snapshot"]="2021-07-21"
    elif county=="Comal":
        support["utility"]=safe_query("nbu-sewer",NBU_SEWER_URL,geom=point_geom(node),distance=3218.688,
                                      out_fields="*",return_geometry=True,page_size=2000,timeout=25)
        support["utility_provider"]="NBU"
        support["utility_snapshot"]="2024-01-17"
    elif county=="Guadalupe":
        support["utility"]=safe_query("gbra-sewer-gravity",GBRA_GRAVITY_URL,geom=point_geom(node),distance=3218.688,
                                      out_fields="*",return_geometry=True,page_size=2000,timeout=25)
        support["utility"]+=safe_query("gbra-sewer-force",GBRA_FORCE_URL,geom=point_geom(node),distance=3218.688,
                                       out_fields="*",return_geometry=True,page_size=2000,timeout=25)
        support["utility_provider"]="GBRA"
        support["utility_snapshot"]="Not published"

    # Statewide road and traffic coverage is used for every county.
    support["roads"]+=safe_query("txdot-roadways",TXDOT_ROADS_URL,geom=point_geom(node),distance=3218.688,
                                 out_fields="RTE_NM,RTE_PRFX,RTE_NBR,RDBD_TYPE,COUNTY,MAP_LBL,SYSTEM,EXT_DATE",
                                 return_geometry=True,page_size=2000,timeout=25)
    support["traffic"]=safe_query("aadt",AADT_URL,geom=point_geom(node),distance=3218.688,
                                  out_fields="*",return_geometry=True)
    return support

def fetch_recent_permits():
    fields="housingunitstotal,housingunitsexist,permittypemapped,permitclassmapped,workclass,proposeduse,landusedescription,latitude_perm,longitude_perm"
    return safe_query("permits-citywide",PERMITS_URL,where="1=1",out_fields=fields,
                      return_geometry=True,page_size=2000,timeout=25)

def assign_permits_to_nodes(permits,supports):
    for feat in permits:
        p=props(feat)
        lat=nval(p,"latitude_perm"); lng=nval(p,"longitude_perm")
        g=feature_shape(feat)
        if g and not g.is_empty:
            cc=g.centroid
            lat=cc.y; lng=cc.x
        if not lat or not lng: continue
        for node in NODES:
            if haversine(node["lat"],node["lng"],lat,lng)<=3.0:
                supports[node["id"]]["permits"].append(feat)

def node_network_quality(node,support):
    nodep=proj(Point(node["lng"],node["lat"]))
    if not nodep: return 45,[],False
    all_names=set(); major_names=set(); mtp_near=False
    for f in support["roads"]:
        g=feature_shape(f); gp=proj(g) if g else None
        if not gp or gp.distance(nodep)>2640: continue
        p=props(f); name=road_name(p) or "Unnamed road"; cls=road_class(p)
        all_names.add(name)
        if road_importance(name,cls)>=3:
            major_names.add(name)
    for f in support["mtp"]:
        g=feature_shape(f); gp=proj(g) if g else None
        if gp and gp.distance(nodep)<=1320:
            mtp_near=True; break
    if len(major_names)>=2: score=100
    elif len(major_names)==1 and len(all_names)>=2: score=88
    elif len(major_names)==1: score=78
    elif len(all_names)>=2: score=68
    elif all_names: score=55
    else: score=35
    if mtp_near: score=min(100,score+6)
    return round(score,1),sorted(major_names)[:4],mtp_near

def score_node(node,support):
    county=support.get("county") or node_county(node)
    now=datetime.now(timezone.utc)
    res=comm=recent=0.0
    active_plats=0
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
        if r or cm: active_plats+=1
        res+=r*sw*dw; comm+=cm*sw*dw
        ed=date_from_any(p.get("last_edited_date")) or date_from_any(p.get("INIT_SUBMIT_DT"))
        if ed and (now-ed).days<=180: recent+=r*sw*dw
    net_units=res_permits=0
    for f in support["permits"]:
        p=props(f)
        total=nval(p,"housingunitstotal"); exist=nval(p,"housingunitsexist")
        net=max(0,total-exist)
        net_units+=net
        txt=" ".join([sval(p,"permittypemapped"),sval(p,"permitclassmapped"),sval(p,"workclass"),
                      sval(p,"proposeduse"),sval(p,"landusedescription")]).lower()
        if "residen" in txt or "single family" in txt or net>0: res_permits+=1
    best_aadt=best_growth=0
    for f in support["traffic"]:
        p=props(f)
        cur=nval(p,"AADT_RPT_QTY","AADT_RPT_CURR_QTY","AADT_2025","AADT")
        old=nval(p,"AADT_RPT_HIST_05_QTY","AADT_2020")
        if cur>best_aadt:
            best_aadt=cur
            best_growth=((cur-old)/old*100) if old else 0
    catalyst_d,catalyst_name=nearest_catalyst(node["lat"],node["lng"])
    network,major_roads,mtp_near=node_network_quality(node,support)

    housing=.72*sat(res,3500)+.18*sat(recent,1200)+.10*sat(net_units+res_permits,180)
    volume=sat(best_aadt,38000)
    growth_score=clamp((max(-20,min(100,best_growth))+5)*2.15)
    traffic=.65*volume+.35*growth_score
    catalyst=100 if catalyst_d<=1 else 90 if catalyst_d<=2 else 72 if catalyst_d<=4 else 50 if catalyst_d<=6 else 28
    demand_gap=clamp(48 + sat(res,3500)*.58 - sat(comm,80)*.42)
    momentum=.72*sat(recent,1200)+.28*sat(net_units+res_permits,180)
    timing=.58*demand_gap+.42*momentum

    evidence_score=(20*housing+15*network+10*catalyst+10*traffic+5*timing)/60
    confidence=0
    confidence+=30 if active_plats else 8
    confidence+=25 if support["traffic"] else 0
    confidence+=25 if support["roads"] else 0
    confidence+=10 if support["flu"] else 0
    confidence+=10 if support["utility"] else 4
    confidence=clamp(confidence)

    evidence_model="Bexar detailed growth + statewide road/traffic evidence"
    node_score=evidence_score
    if county!="Bexar":
        # Comparable plat/permit feeds are not yet loaded countywide outside Bexar.
        # Use the curated corridor prior conservatively, and cap confidence.
        node_score=.55*evidence_score+.45*float(node.get("base",50))
        confidence=min(confidence,68)
        evidence_model="Regional corridor prior + statewide road/traffic; county housing feed incomplete"

    search_supported=county in {"Bexar","Comal","Guadalupe"}
    if county=="Bexar" and node_score>=76 and confidence>=70: node_class="PRIORITY NODE"
    elif node_score>=66 and confidence>=55: node_class="EMERGING NODE"
    elif node_score>=52: node_class="WATCH NODE"
    else: node_class="LOWER CONFIDENCE"

    return {
        **node,"county":county,"search_supported":search_supported,
        "score":round(clamp(node_score),1),"evidence_score":round(clamp(evidence_score),1),
        "confidence_score":round(confidence,1),"node_class":node_class,"evidence_model":evidence_model,
        "weighted_future_res_lots":round(res,1),"weighted_future_commercial_lots":round(comm,1),
        "recent_progress_res_lots":round(recent,1),"active_plat_signals":active_plats,
        "net_new_housing_units_180d":round(net_units,1),"residential_permits_180d":int(res_permits),
        "aadt":int(best_aadt),"aadt_5yr_growth_pct":round(best_growth,1),
        "nearest_catalyst":catalyst_name,"catalyst_miles":round(catalyst_d,2),
        "major_node_roads":major_roads,"mtp_near_node":mtp_near,
        "utility_provider":support.get("utility_provider",""),"mapped_utility_features":len(support.get("utility",[])),
        "component_scores":{
            "residential_growth":round(housing,1),"intersection_network":round(network,1),
            "retail_catalyst":round(catalyst,1),"traffic":round(traffic,1),"timing":round(timing,1)
        }
    }

def query_parcels(node):
    county=node.get("county") or node_county(node)
    if county=="Bexar":
        return safe_query("bexar-parcels",PARCEL_URL,where="Acres >= 3",geom=point_geom(node),distance=2414.016,
                          out_fields="OBJECTID,PropID,Situs,Owner,DBA,LglDesc,LandVal,ImprVal,TotVal,GBA,TOT_GBA,YrBlt,Houses,LglAcres,Acres,PropUse",
                          return_geometry=True)
    if county=="Comal":
        return safe_query("comal-parcels",COMAL_PARCEL_URL,where="LEGAL_ACRE >= 3",geom=point_geom(node),distance=2414.016,
                          out_fields="OBJECTID,PROP_ID,PARCELKEY,PROP_TYPE_,PY_OWNER_N,SITUS_ADDR,LEGAL_DESC,LEGAL_DE_1,LEGAL_ACRE,LAND_HMSTD,LAND_NON_H,IMPRV_VAL,IMPROV_NON,APPRAISED,ASSESSED,CADLINK",
                          return_geometry=True,page_size=2000,timeout=25)
    if county=="Guadalupe":
        where="(LGL_AREA_UNIT='ACRES' AND LEGAL_AREA >= 3) OR (GIS_AREA_UNIT='ACRES' AND GIS_AREA >= 3)"
        return safe_query("guadalupe-parcels",GUADALUPE_PARCEL_URL,where=where,geom=point_geom(node),distance=2414.016,
                          out_fields="OBJECTID,PROP_ID,GEO_ID,OWNER_NAME,LEGAL_AREA,LGL_AREA_UNIT,GIS_AREA,GIS_AREA_UNIT,LEGAL_DESC,STAT_LAND_USE,LOC_LAND_USE,LAND_VALUE,IMP_VALUE,MKT_VALUE,SITUS_ADDR,TAX_YEAR,YEAR_BUILT",
                          return_geometry=True,page_size=2000,timeout=25)
    return []

def make_candidate(feature,node_result):
    county=node_result.get("county") or node_county(node_result)
    rec=normalized_parcel(feature,county)
    owner=rec.get("owner","").strip()
    if not rec or not owner: return None
    if (PUBLIC_OWNER.search(owner) or ANCHOR_OWNER.search(owner)
            or INSTITUTIONAL_OWNER.search(owner) or RESIDENTIAL_BUILDER_OWNER.search(owner)
            or OPERATING_USER_OWNER.search(owner)): return None
    reported_acres=float(rec.get("acres") or 0)
    g=feature_shape(feature)
    if not g or g.is_empty: return None
    gp=proj(g)
    if not gp or gp.is_empty: return None
    geometry_acres=max(0,gp.area/43560.0)
    # County feeds are inconsistent about area units. Trust the legal/reported acres only
    # when it is reasonably consistent with the polygon; otherwise use GIS geometry acres.
    if reported_acres>0 and geometry_acres>0 and .60 <= reported_acres/geometry_acres <= 1.67:
        a=reported_acres; acres_source="REPORTED"
    else:
        a=geometry_acres; acres_source="GEOMETRY"
    if a<3: return None
    nodep=proj(Point(node_result["lng"],node_result["lat"]))
    edge_mi=gp.distance(nodep)/5280
    if edge_mi>1.5: return None

    raw,impr_ratio,gba=raw_land_score_values(rec.get("market_value"),rec.get("improvement_value"),a,
                                             rec.get("gba",0),rec.get("houses",0))
    if a<12 and impr_ratio>.55: return None
    if a<8 and gba and gba/a>12000: return None
    houses=float(rec.get("houses") or 0)
    if a<12 and houses>=5: return None

    sh,compact,aspect=geometry_shape_metrics(gp)
    dist=parcel_distance_score(edge_mi); acre=acreage_score(a)
    pre=.60*node_result["score"]+.15*dist+.10*acre+.10*raw+.05*sh
    ctr=g.centroid
    source=PARCEL_SOURCE_INFO.get(county,{})
    pid=str(rec.get("prop_id") or "").strip()
    if not pid: return None
    return {
        "feature":feature,"candidate_id":county+":"+pid,"county":county,"prop_id":pid,
        "owner":owner,"owner_key":normalize_owner(owner),"situs":rec.get("situs",""),
        "acres":round(a,2),"reported_acres":round(reported_acres,2) if reported_acres else None,
        "geometry_acres":round(geometry_acres,2),"acres_source":acres_source,
        "land_value":round(float(rec.get("land_value") or 0),0),
        "assessed_value":round(float(rec.get("market_value") or 0),0),
        "improvement_value":round(float(rec.get("improvement_value") or 0),0),
        "improvement_ratio":round(impr_ratio,3),"gba":round(gba,0),
        "prop_use":rec.get("prop_use",""),"legal":rec.get("legal",""),
        "cad_record_url":rec.get("cad_record_url",""),
        "parcel_source":source.get("label",""),"parcel_snapshot":source.get("snapshot",""),
        "parcel_freshness":source.get("freshness","UNKNOWN"),
        "node_id":node_result["id"],"node_name":node_result["name"],"node_score":node_result["score"],
        "node_edge_miles":round(edge_mi,3),"centroid_lat":ctr.y,"centroid_lng":ctr.x,
        "dist_score":dist,"acre_score":acre,"raw_score":round(raw,1),"shape_score":round(sh,1),
        "compactness":round(compact,3),"aspect_ratio":round(aspect,2),"preliminary_score":round(pre,1),
        "_geom2278":gp
    }

def road_quality(c,support):
    poly=c["_geom2278"]; boundary=poly.boundary
    roads=[]; frontage=0
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
            roads.append((name,cls,d,near_len,road_importance(name,cls)))
            frontage+=near_len
    unique=[]; seen=set()
    for name,cls,d,l,importance in sorted(roads,key=lambda x:x[2]):
        k=name.upper()
        if k not in seen:
            unique.append((name,cls,d,l,importance)); seen.add(k)
    primary=[x for x in unique if x[4]>=3]
    collectors=[x for x in unique if x[4]>=2]
    meaningful=[x for x in unique if x[4]>=1 and x[3]>=40]
    major=bool(primary)
    strong_corner=bool(primary and len(meaningful)>=2)
    secondary_corner=bool(collectors and len(meaningful)>=2)
    mtp_cross=False
    for f in support["mtp"]:
        g=feature_shape(f); gp=proj(g) if g else None
        if gp and gp.distance(poly)<=60:
            mtp_cross=True; break
    if len(collectors)>=2 and strong_corner: score=100
    elif strong_corner: score=94
    elif major and frontage>=200: score=90
    elif major: score=84
    elif secondary_corner: score=80
    elif collectors and frontage>=200: score=75
    elif collectors: score=70
    elif meaningful: score=60
    else: score=20
    display=[]
    for item in primary+collectors+meaningful+unique:
        if item[0] not in display: display.append(item[0])
    return round(score,1),display[:4],round(frontage,0),strong_corner,major,mtp_cross
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

def screen_fema_candidate(c):
    g=feature_shape(c["feature"])
    if not g or g.is_empty:
        c["flood_confidence"]="UNKNOWN"; c["eligible"]=False
        return classify_candidate(c)
    minx,miny,maxx,maxy=g.bounds
    env={"xmin":minx,"ymin":miny,"xmax":maxx,"ymax":maxy,"spatialReference":{"wkid":4326}}
    try:
        feats=arc_query(FEMA_URL,geom=env,geom_type="esriGeometryEnvelope",
                        out_fields="FLD_ZONE,ZONE_SUBTY,SFHA_TF",return_geometry=True,
                        page_size=300,timeout=25)
        flood_score,flood_pct,fw_pct,zones=flood_quality(c,{"fema":feats})
        c["flood_score"]=flood_score
        c["flood_pct"]=flood_pct
        c["floodway_pct"]=fw_pct
        c["flood_zones"]=zones
        c["flood_confidence"]="SCREENED"
        usable_acres=c["acres"]*(1-min(100,flood_pct)/100)
        c["usable_acres_proxy"]=round(max(0,usable_acres),2)
        # Flood was provisionally neutral (55) in parcel execution; replace it with the screened value.
        c["parcel_execution_score"]=round(clamp(c["parcel_execution_score"] + (5/40)*(flood_score-55)),1)
        c["parcel_component_scores"]["flood"]=round(flood_score,1)
        c["parcel_opportunity_score"]=round(clamp(.60*c["node_score"]+.40*c["parcel_execution_score"]),1)
        c["eligible"]=bool(c.get("eligible_pre_flood") and fw_pct<10 and flood_pct<50 and usable_acres>=3)
        why=[x for x in str(c.get("why_this_tract","")).split(" · ") if x and "FEMA" not in x]
        if flood_pct==0: why.append("no mapped FEMA SFHA overlap returned")
        elif flood_pct<25: why.append(f"{flood_pct:.1f}% mapped FEMA SFHA overlap")
        c["why_this_tract"]=" · ".join(why[:4])
    except Exception as e:
        errors.append(f"fema-parcel {c.get('prop_id')}: {e}")
        c["flood_confidence"]="UNKNOWN"; c["eligible"]=False
    c["confidence_score"]=candidate_confidence(c)
    return classify_candidate(c)

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

def route_key(name):
    s=str(name or "").upper()
    m=re.search(r"\b(IH|I|US|SH|FM|LOOP)\s*[- ]?0*(\d+)\b",s)
    if not m: return ""
    p="IH" if m.group(1)=="I" else m.group(1)
    return f"{p}:{int(m.group(2))}"

def traffic_for_parcel(c,support,frontage_roads=None):
    matched=[]; fallback=[]
    parcel=c["_geom2278"]
    frontage_keys={route_key(x) for x in (frontage_roads or []) if route_key(x)}
    for f in support["traffic"]:
        g=feature_shape(f)
        if not g: continue
        gp=proj(g)
        if not gp: continue
        d=parcel.distance(gp)/5280
        p=props(f)
        cur=nval(p,"AADT_RPT_QTY","AADT_RPT_CURR_QTY","AADT_2025","AADT")
        old=nval(p,"AADT_RPT_HIST_05_QTY","AADT_2020")
        if cur<=0: continue
        growth=((cur-old)/old*100) if old else 0
        rkey=route_key(road_name(p))
        rec=(d,cur,growth,rkey)
        fallback.append(rec)
        if rkey and rkey in frontage_keys and d<=1.25:
            matched.append(rec)
    pool=matched if matched else fallback
    if not pool: return 0,0,99
    # Same-route station wins; among those use the closest count station to the parcel.
    best=min(pool,key=lambda x:x[0])
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

def utility_for_parcel(c,support):
    poly=c["_geom2278"]
    best_ft=None
    for f in support.get("utility",[]):
        g=feature_shape(f); gp=proj(g) if g else None
        if not gp: continue
        try: d=poly.distance(gp)
        except: continue
        if best_ft is None or d<best_ft: best_ft=d
    provider=support.get("utility_provider","")
    snapshot=support.get("utility_snapshot","")
    if best_ft is None:
        return 20,"UNKNOWN",None,provider,snapshot
    if best_ft<=200: score=100
    elif best_ft<=500: score=92
    elif best_ft<=1000: score=82
    elif best_ft<=2640: score=65
    else: score=35
    confidence="PROXY" if best_ft<=1000 else "NEARBY" if best_ft<=2640 else "UNKNOWN"
    return round(score,1),confidence,round(best_ft,0),provider,snapshot

def candidate_confidence(c):
    score=.25*float(c.get("node_confidence_score") or 0)
    score+=20 if c.get("cad_geometry_verified") else 5
    score+=15 if c.get("frontage_roads") else 3
    score+=15 if c.get("flood_confidence")=="SCREENED" else 0
    score+=10 if c.get("aadt") and float(c.get("aadt_station_miles") or 99)<=2 else 4 if c.get("aadt") else 0
    score+=10 if c.get("utility_confidence")=="PROXY" else 6 if c.get("utility_confidence")=="NEARBY" else 2
    score+=5 if c.get("owner") else 0
    score=clamp(score)
    if c.get("utility_confidence")!="PROXY":
        score=min(score,84)
    county=c.get("county")
    if county=="Comal":
        score=min(score,78 if c.get("live_secondary_verified") else 72)
    elif county=="Guadalupe":
        score=min(score,68 if c.get("live_secondary_verified") else 48)
    if not c.get("cad_geometry_verified"):
        score=min(score,45)
    return round(score,1)

def classify_candidate(c):
    risks=[]
    county=c.get("county","Bexar")
    if c.get("node_edge_miles",99)>.5: risks.append("not on the immediate intersection")
    if not c.get("major_road_signal"): risks.append("major-road exposure needs confirmation")
    if c.get("frontage_ft_proxy",0)<200: risks.append("limited frontage proxy")
    if c.get("utility_confidence")=="UNKNOWN": risks.append("mapped sewer path is unverified")
    elif c.get("utility_confidence")=="NEARBY": risks.append("mapped sewer is nearby but not close to parcel")
    else: risks.append("utility capacity is unverified")
    if c.get("flood_pct") is None: risks.append("flood screen unavailable")
    elif c.get("flood_pct",0)>0: risks.append(f"{c['flood_pct']:.1f}% mapped SFHA overlap")
    if c.get("shape_score",100)<55: risks.append("parcel geometry is less efficient")
    if c.get("parcel_freshness")=="AGING": risks.append("county parcel snapshot is aging")
    if c.get("parcel_freshness")=="STALE": risks.append("county parcel snapshot is stale")
    if c.get("confidence_score",100)<65: risks.append("important diligence data is incomplete")

    score=float(c.get("parcel_opportunity_score") or 0)
    conf=float(c.get("confidence_score") or 0)
    access_ready=(c.get("major_road_signal") and c.get("road_score",0)>=84
                  and (c.get("frontage_ft_proxy",0)>=150 or c.get("corner_signal")=="STRONG"))
    priority=(county=="Bexar" and c.get("parcel_freshness")=="RECENT" and c.get("eligible")
              and score>=78 and conf>=68 and c.get("node_edge_miles",99)<=.60
              and access_ready and c.get("flood_score",0)>=75 and c.get("parcel_execution_score",0)>=68
              and c.get("utility_confidence")=="PROXY")
    watch=(c.get("eligible") and score>=68 and conf>=52 and c.get("road_score",0)>=66
           and not (county=="Guadalupe" and not c.get("live_secondary_verified")))
    early=(c.get("eligible") and c.get("node_score",0)>=58 and score>=58 and conf>=42)
    if priority: category="PRIORITY"
    elif watch: category="WATCH"
    elif early: category="EARLY SPECULATION"
    else: category="REVIEW"

    c["acquisition_category"]=category
    c["main_risks"]=risks[:5]
    if category=="PRIORITY":
        c["decision_summary"]="Investigate ownership, access, utilities and pricing now."
    elif category=="WATCH":
        c["decision_summary"]="Strong enough to track closely; verify title, access and utility feasibility before elevating."
    elif category=="EARLY SPECULATION":
        c["decision_summary"]="Interesting node/parcel thesis, but data freshness or execution certainty is not strong enough for active pursuit."
    else:
        c["decision_summary"]="Does not currently clear the acquisition-mode highlight standard."
    return c

def enrich_candidate(c,support,node_result):
    road_score,roads,frontage,corner,major,mtp=road_quality(c,support)
    flood_score,flood_pct,fw_pct,zones=55,None,None,[]
    flood_confidence="PENDING"
    flu,flu_names=land_use_quality(c,support)
    aadt,growth,aadt_dist=traffic_for_parcel(c,support,roads)
    val=value_score(c)
    catalyst_d,catalyst_name=nearest_catalyst(c["centroid_lat"],c["centroid_lng"])
    utility_score,utility_conf,utility_ft,utility_provider,utility_snapshot=utility_for_parcel(c,support)
    parcel_fit=.62*c["acre_score"]+.38*c["shape_score"]
    acquisition=.72*c["raw_score"]+.28*val
    parcel_execution=(12*road_score+10*parcel_fit+8*utility_score+5*flood_score+5*acquisition)/40
    score=.60*c["node_score"]+.40*parcel_execution

    eligible_pre_flood=(c["acres"]>=3 and c["node_edge_miles"]<=1.0 and road_score>=66 and c["raw_score"]>=60
                        and flu>=35 and c["shape_score"]>=30 and c["node_score"]>=52
                        and node_result.get("confidence_score",0)>=45 and bool(roads))
    reasons=[]
    if corner and major: reasons.append("corner exposure on a major road")
    elif major: reasons.append("major-road frontage")
    elif roads: reasons.append("road frontage")
    if c["node_edge_miles"]<=.25: reasons.append("within ¼ mile of the node")
    elif c["node_edge_miles"]<=.5: reasons.append("within ½ mile of the node")
    else: reasons.append("within 1 mile of the node")
    if node_result["weighted_future_res_lots"]>=1200:
        reasons.append(f"{int(node_result['weighted_future_res_lots'])} weighted future residential lots")
    elif c.get("county")!="Bexar":
        reasons.append("regional growth node; county housing feed incomplete")
    if catalyst_d<=2.5: reasons.append(f"{catalyst_d:.1f} mi from {catalyst_name}")
    if utility_ft is not None and utility_ft<=1000:
        reasons.append(f"mapped {utility_provider or 'sewer'} feature ~{int(utility_ft)} ft from parcel")
    if c["raw_score"]>=80: reasons.append("mostly raw / low-improvement land")

    c.update({
        "road_score":road_score,"frontage_roads":roads,"frontage_ft_proxy":frontage,
        "corner_signal":"STRONG" if corner and major else "YES" if corner else "NO",
        "major_road_signal":major,"mtp_row_flag":mtp,
        "flood_score":flood_score,"flood_pct":flood_pct,"floodway_pct":fw_pct,"flood_zones":zones,"flood_confidence":flood_confidence,
        "future_land_use_score":flu,"future_land_use":flu_names,
        "aadt":aadt,"aadt_5yr_growth_pct":growth,"aadt_station_miles":aadt_dist,
        "nearest_retail_catalyst":catalyst_name,"retail_catalyst_miles":round(catalyst_d,2),
        "future_residential_lots_nearby":node_result["weighted_future_res_lots"],
        "recent_housing_units_180d":node_result["net_new_housing_units_180d"],
        "node_confidence_score":node_result.get("confidence_score",0),
        "node_class":node_result.get("node_class",""),
        "node_evidence_model":node_result.get("evidence_model",""),
        "node_component_scores":node_result.get("component_scores",{}),
        "utility_score":round(utility_score,1),"utility_confidence":utility_conf,
        "utility_provider":utility_provider,"utility_distance_ft":utility_ft,"utility_snapshot":utility_snapshot,
        "utility_context":("No mapped sewer feature returned near parcel" if utility_ft is None else
                           f"{utility_provider or 'Mapped sewer'} feature approximately {int(utility_ft)} ft from parcel; capacity NOT verified"),
        "parcel_fit_score":round(parcel_fit,1),"acquisition_complexity_score":round(acquisition,1),
        "parcel_execution_score":round(parcel_execution,1),
        "parcel_component_scores":{
            "frontage_access":round(road_score,1),"size_shape":round(parcel_fit,1),
            "utilities":round(utility_score,1),"flood":round(flood_score,1),"acquisition":round(acquisition,1)
        },
        "parcel_opportunity_score":round(clamp(score),1),"eligible_pre_flood":eligible_pre_flood,"eligible":False,
        "why_this_tract":" · ".join(reasons[:5]),
        "verification_notes":"Frontage is a GIS proximity proxy, not legal access. Sewer distance is a mapped-line proxy, not a capacity commitment. Confirm current title/CAD, survey, curb access, median/turn movements, ROW, flood and provider capacity."
    })
    c["confidence_score"]=candidate_confidence(c)
    return c

def owners_compatible(a,b):
    aa=normalize_owner(a); bb=normalize_owner(b)
    if not aa or not bb: return False
    return aa==bb or (len(aa)>=8 and aa in bb) or (len(bb)>=8 and bb in aa)

def verify_candidate(c):
    county=c.get("county","Bexar")
    pid=str(c.get("prop_id") or "").strip()
    if not pid: return c
    qpid=pid.replace("'","''")
    feats=[]
    if county=="Bexar":
        if not pid.isdigit(): return c
        feats=safe_query("sara-bcad-enrich",SARA_BCAD_URL,where=f"Prop_id={int(pid)}",out_fields="*",
                         return_geometry=True,page_size=10,timeout=30)
        if feats:
            f=feats[0]; p=props(f)
            c["cad_geometry_verified"]=True
            c["bcad_geometry_verified"]=True
            c["geometry_source"]="SARA / BCAD parcel service"
            c["cad_verification_source"]="SARA / BCAD live service"
            c["bcad_geo_id"]=sval(p,"Geo_id")
            c["ownership_type"]=sval(p,"Ownership_Type")
            current_owner=sval(p,"Owner_name")
            if current_owner:
                c["owner_verification_match"]=owners_compatible(c.get("owner"),current_owner)
                c["verified_owner"]=current_owner
            dd=p.get("Last_Deed_Date")
            dt=date_from_any(dd)
            if dt:
                c["last_deed_date"]=dt.date().isoformat()
                c["hold_years"]=round((datetime.now(timezone.utc)-dt).days/365.25,1)
            g=feature_shape(f)
            if g and not g.is_empty: c["feature"]["geometry"]=mapping(g)

    elif county=="Comal":
        where=f"PROP_ID={int(pid)}" if pid.isdigit() else f"PARCELKEY='{qpid}'"
        feats=safe_query("comal-cad-enrich",COMAL_PARCEL_URL,where=where,out_fields="*",
                         return_geometry=True,page_size=10,timeout=30)
        if feats:
            f=feats[0]; p=props(f)
            c["cad_geometry_verified"]=True
            c["geometry_source"]="Comal CAD public ArcGIS parcel layer"
            c["cad_verification_source"]="Comal CAD public ArcGIS service"
            current_owner=sval(p,"PY_OWNER_N")
            if current_owner:
                c["owner_verification_match"]=owners_compatible(c.get("owner"),current_owner)
                c["verified_owner"]=current_owner
            c["cad_record_url"]=sval(p,"CADLINK") or c.get("cad_record_url","")
            g=feature_shape(f)
            if g and not g.is_empty: c["feature"]["geometry"]=mapping(g)
        live=safe_query("nbu-live-parcel-check",NBU_LIVE_PARCELS_URL,
                        where=f"Property_ID='{qpid}' OR Parcel_No_='{qpid}'",
                        out_fields="Property_ID,Parcel_No_,Land_Owner_Name,County_Name",return_geometry=False,page_size=10,timeout=20)
        if live:
            lp=props(live[0]); live_owner=sval(lp,"Land_Owner_Name")
            if live_owner and owners_compatible(c.get("owner"),live_owner):
                c["live_secondary_verified"]=True
                c["secondary_verification_source"]="NBU live project parcel feed"
                c["verified_owner"]=live_owner

    elif county=="Guadalupe":
        feats=safe_query("guadalupe-cad-enrich",GUADALUPE_PARCEL_URL,where=f"PROP_ID='{qpid}'",out_fields="*",
                         return_geometry=True,page_size=10,timeout=30)
        if feats:
            f=feats[0]; p=props(f)
            c["cad_geometry_verified"]=True
            c["geometry_source"]="Guadalupe CAD / TxGIO public parcel extract"
            c["cad_verification_source"]="Guadalupe public parcel extract (2022 vintage)"
            current_owner=sval(p,"OWNER_NAME")
            if current_owner:
                c["owner_verification_match"]=owners_compatible(c.get("owner"),current_owner)
                c["verified_owner"]=current_owner
            g=feature_shape(f)
            if g and not g.is_empty: c["feature"]["geometry"]=mapping(g)

        live_where=(f"Property_ID='{qpid}' OR Parcel_No_='{qpid}' OR PropID_Text='{qpid}'"
                    + (f" OR PROP_ID={int(pid)}" if pid.isdigit() else ""))
        live=safe_query("gbra-live-parcel-check",GBRA_LIVE_PARCELS_URL,where=live_where,
                        out_fields="PROP_ID,PropID_Text,Property_ID,Parcel_No_,Land_Owner_Name,County,County_Name",
                        return_geometry=False,page_size=10,timeout=20)
        if live:
            lp=props(live[0]); live_owner=sval(lp,"Land_Owner_Name")
            if live_owner and owners_compatible(c.get("owner"),live_owner):
                c["live_secondary_verified"]=True
                c["secondary_verification_source"]="GBRA live project parcel feed"
                c["verified_owner"]=live_owner

    verified=c.get("verified_owner")
    if verified:
        c["owner"]=verified
        c["owner_key"]=normalize_owner(verified)
        if (PUBLIC_OWNER.search(verified) or ANCHOR_OWNER.search(verified)
                or INSTITUTIONAL_OWNER.search(verified) or RESIDENTIAL_BUILDER_OWNER.search(verified)
                or OPERATING_USER_OWNER.search(verified)):
            c["eligible"]=False
            c["verification_exclusion"]="verified owner falls in an excluded ownership class"
    c["confidence_score"]=candidate_confidence(c)
    classify_candidate(c)
    return c
else_dummy = None

def select_top(candidates,limit=36,node_cap=3):
    order={"PRIORITY":0,"WATCH":1,"EARLY SPECULATION":2,"REVIEW":3}
    pool=[x for x in candidates if x.get("eligible") and x.get("cad_geometry_verified") is True
          and x.get("acquisition_category") in {"PRIORITY","WATCH","EARLY SPECULATION"}]
    candidates=sorted(pool,key=lambda x:(order.get(x.get("acquisition_category"),9),
                                          -x["parcel_opportunity_score"],-x.get("confidence_score",0)))
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
      "candidate_id","county","prop_id","owner","verified_owner","owner_verification_match","situs","acres",
      "reported_acres","geometry_acres","acres_source","land_value","assessed_value","improvement_value","improvement_ratio","gba","prop_use","legal","cad_record_url",
      "parcel_source","parcel_snapshot","parcel_freshness","cad_geometry_verified","cad_verification_source",
      "live_secondary_verified","secondary_verification_source",
      "node_id","node_name","node_score","node_edge_miles","dist_score","acre_score","raw_score",
      "shape_score","compactness","aspect_ratio","road_score","frontage_roads","frontage_ft_proxy","corner_signal",
      "major_road_signal","mtp_row_flag","flood_score","flood_pct","floodway_pct","flood_zones","flood_confidence",
      "future_land_use_score","future_land_use","aadt","aadt_5yr_growth_pct","aadt_station_miles",
      "nearest_retail_catalyst","retail_catalyst_miles","future_residential_lots_nearby","recent_housing_units_180d",
      "utility_confidence","utility_provider","utility_distance_ft","utility_snapshot","utility_context",
      "assessed_value_per_acre","land_value_per_acre","parcel_opportunity_score","parcel_execution_score",
      "parcel_fit_score","acquisition_complexity_score","utility_score","confidence_score","node_confidence_score",
      "node_class","node_evidence_model","node_component_scores","parcel_component_scores","acquisition_category",
      "decision_summary","main_risks","usable_acres_proxy","eligible","why_this_tract","verification_notes",
      "bcad_geometry_verified","geometry_source","bcad_geo_id","ownership_type","last_deed_date","hold_years"
    ]
    p={k:c.get(k) for k in keys if k in c}
    if rank is not None: p["rank"]=rank
    return p
def main():
    print("Analyzing nodes in parallel...")
    supports={}; node_results=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs={ex.submit(node_support,node):node for node in NODES}
        for idx,fut in enumerate(as_completed(futs),1):
            node=futs[fut]
            try:
                sup=fut.result()
            except Exception as e:
                errors.append(f"node-support {node['name']}: {e}")
                county=node_county(node)
                sup={"county":county,"plats":[],"permits":[],"traffic":[],"roads":[],"mtp":[],"fema":[],"flu":[],
                     "utility":[],"utility_provider":"","utility_snapshot":""}
            supports[node["id"]]=sup
            node_results.append(score_node(node,sup))
            print(f"[{idx}/{len(NODES)}] {node['name']}")

    print("Fetching recent CoSA permits once and assigning where geographically relevant...")
    recent_permits=fetch_recent_permits()
    assign_permits_to_nodes(recent_permits,supports)
    node_results=[score_node(node,supports[node["id"]]) for node in NODES]
    node_results.sort(key=lambda x:x["score"],reverse=True)
    node_by={x["id"]:x for x in node_results}

    # Preserve quality while preventing Bexar from crowding out the regional counties.
    active_nodes=[]
    county_rules={
      "Bexar":{"min_score":55,"min_conf":55,"cap":10},
      "Comal":{"min_score":45,"min_conf":45,"cap":3},
      "Guadalupe":{"min_score":45,"min_conf":45,"cap":3},
    }
    for county,rule in county_rules.items():
        pool=[x for x in node_results if x.get("county")==county and x.get("search_supported")
              and x["score"]>=rule["min_score"] and x.get("confidence_score",0)>=rule["min_conf"]]
        active_nodes.extend(pool[:rule["cap"]])
    active_ids={x["id"] for x in active_nodes}
    for n in node_results:
        n["selected_for_parcel_search"]=n["id"] in active_ids
    active_nodes.sort(key=lambda x:x["score"],reverse=True)
    print("Active parcel-search nodes:",", ".join(f"{x['county']}:{x['name']}" for x in active_nodes))

    print("Querying parcel universes around selected nodes in parallel...")
    by_pid={}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs={ex.submit(query_parcels,node):node for node in active_nodes}
        for fut in as_completed(futs):
            node=futs[fut]
            try: feats=fut.result()
            except Exception as e:
                errors.append(f"parcel-query {node['name']}: {e}"); feats=[]
            for feat in feats:
                cand=make_candidate(feat,node)
                if not cand: continue
                key=cand["candidate_id"]
                old=by_pid.get(key)
                if old is None or cand["preliminary_score"]>old["preliminary_score"]:
                    by_pid[key]=cand

    all_candidates=list(by_pid.values())
    candidates=[]
    county_candidate_caps={"Bexar":180,"Comal":100,"Guadalupe":100}
    for county,cap in county_candidate_caps.items():
        county_pool=sorted([x for x in all_candidates if x.get("county")==county],
                           key=lambda x:x["preliminary_score"],reverse=True)[:cap]
        candidates.extend(county_pool)
        print(f"Base candidates {county}: {len(county_pool)}")
    candidates.sort(key=lambda x:x["preliminary_score"],reverse=True)
    print(f"Base candidates total: {len(candidates)}")

    print("Enriching parcel execution quality...")
    enriched=[]
    for i,cand in enumerate(candidates,1):
        if i%25==0: print(f"  {i}/{len(candidates)}")
        enriched.append(enrich_candidate(cand,supports[cand["node_id"]],node_by[cand["node_id"]]))

    provisional=[]
    fema_caps={"Bexar":90,"Comal":45,"Guadalupe":45}
    for county,cap in fema_caps.items():
        pool=sorted([x for x in enriched if x.get("county")==county and x.get("eligible_pre_flood")],
                    key=lambda x:x["parcel_opportunity_score"],reverse=True)[:cap]
        provisional.extend(pool)
    print(f"Parcel-level FEMA screening on {len(provisional)} provisional candidates...")
    with ThreadPoolExecutor(max_workers=2) as ex:
        screened=list(ex.map(screen_fema_candidate,provisional))

    verify_pool=[x for x in screened if x.get("eligible")]
    print(f"County parcel verification on all {len(verify_pool)} eligible finalists...")
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(verify_candidate,verify_pool))
    for cand in screened:
        cand["confidence_score"]=candidate_confidence(cand)
        classify_candidate(cand)

    top=select_top(screened,36,3)
    print(f"Acquisition Mode V3 highlighted parcels: {len(top)}")
    category_order={"PRIORITY":0,"WATCH":1,"EARLY SPECULATION":2}
    top.sort(key=lambda x:(category_order.get(x.get("acquisition_category"),9),
                           -x["parcel_opportunity_score"],-x.get("confidence_score",0)))
    for i,cand in enumerate(top,1): cand["rank"]=i

    fc={"type":"FeatureCollection","features":[
        {"type":"Feature","geometry":cand["feature"]["geometry"],"properties":public_props(cand,i)}
        for i,cand in enumerate(top,1)
    ]}
    (DATA/"opportunity_parcels.geojson").write_text(json.dumps(fc,indent=2))

    all_fc={"type":"FeatureCollection","features":[
        {"type":"Feature","geometry":cand["feature"]["geometry"],"properties":public_props(cand)}
        for cand in sorted(screened,key=lambda x:x["parcel_opportunity_score"],reverse=True)[:180]
    ]}
    (DATA/"opportunity_parcels_all.geojson").write_text(json.dumps(all_fc,indent=2))
    (DATA/"opportunity_nodes.json").write_text(json.dumps(node_results,indent=2))
    ass=assemblages(screened)
    (DATA/"assemblages.geojson").write_text(json.dumps({"type":"FeatureCollection","features":ass},indent=2))

    cols=["rank","acquisition_category","county","candidate_id","parcel_opportunity_score","confidence_score",
          "parcel_execution_score","node_score","node_class","owner","prop_id","situs","acres","usable_acres_proxy",
          "node_name","node_edge_miles","frontage_roads","frontage_ft_proxy","corner_signal","raw_score","shape_score",
          "future_residential_lots_nearby","aadt","aadt_5yr_growth_pct","nearest_retail_catalyst","retail_catalyst_miles",
          "flood_pct","floodway_pct","parcel_source","parcel_snapshot","parcel_freshness","cad_geometry_verified",
          "live_secondary_verified","assessed_value","assessed_value_per_acre","land_value_per_acre","last_deed_date",
          "hold_years","utility_provider","utility_distance_ft","utility_confidence","decision_summary","why_this_tract",
          "main_risks","verification_notes"]
    with (DATA/"tracts_to_review.csv").open("w",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=cols); w.writeheader()
        for cand in top:
            row={k:cand.get(k,"") for k in cols}
            for k in ("frontage_roads","main_risks"):
                if isinstance(row.get(k),list): row[k]=" | ".join(map(str,row[k]))
            w.writerow(row)

    by_county={county:sum(1 for x in top if x.get("county")==county) for county in ("Bexar","Comal","Guadalupe")}
    active_by_county={county:sum(1 for x in active_nodes if x.get("county")==county) for county in ("Bexar","Comal","Guadalupe")}
    meta={
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "generator":"scripts/generate_opportunities.py",
      "version":"Acquisition Mode V3 Multi-County",
      "node_count":len(node_results),"active_node_count":len(active_nodes),"active_nodes_by_county":active_by_county,
      "candidate_count":len(enriched),"fema_screened_count":len(screened),"highlighted_count":len(top),
      "highlighted_by_county":by_county,
      "priority_count":sum(1 for x in top if x.get("acquisition_category")=="PRIORITY"),
      "watch_count":sum(1 for x in top if x.get("acquisition_category")=="WATCH"),
      "early_speculation_count":sum(1 for x in top if x.get("acquisition_category")=="EARLY SPECULATION"),
      "assemblage_count":len(ass),
      "sources":{
        "parcels_bexar":"Bexar Public Works candidate universe; finalists re-verified through SARA/BCAD",
        "parcels_comal":"Comal CAD public ArcGIS parcel layer; data edit date November 22, 2024",
        "parcels_guadalupe":"Guadalupe CAD / TxGIO public parcel extract; February 2022 vintage; secondary GBRA project-feed corroboration attempted",
        "plats":"Bexar Public Works plat stages; comparable countywide plat feed not yet loaded for Comal/Guadalupe",
        "permits":"City of San Antonio building permits past 180 days; regional counties have lower permit-data confidence",
        "traffic":"TxDOT AADT Annuals Public View",
        "roads":"TxDOT statewide roadways plus CoSA/Bexar local road sources where available",
        "flood":"FEMA NFHL flood hazard polygons",
        "land_use":"City of San Antonio Future Land Use where available",
        "utilities":"Mapped existing sewer proximity: SAWS (Bexar), NBU (Comal/New Braunfels), GBRA (Guadalupe); capacity unverified"
      },
      "errors":errors[:120],"source_feature_counts":dict(source_stats),
      "methodology":{
        "architecture":"Node first -> county parcel universe -> hard filters -> 60% location / 40% parcel execution -> confidence -> category",
        "node_weights":{"residential_growth":20,"intersection_network":15,"retail_catalyst":10,"traffic":10,"timing":5},
        "parcel_weights":{"frontage_access":12,"size_shape":10,"utilities":8,"flood":5,"acquisition_complexity":5},
        "parcel_query_radius_miles":1.5,"hard_highlight_distance_miles":1.0,"min_acres":3,
        "active_node_caps":{"Bexar":10,"Comal":3,"Guadalupe":3},"top_limit":36,"per_node_cap":3,
        "freshness_policy":"Only recent Bexar parcel data can earn PRIORITY. Aging Comal data is capped at WATCH. Guadalupe 2022 data is capped at EARLY unless corroborated by a newer GBRA project parcel feed, then WATCH is possible.",
        "hard_gate":"3+ ac; <=1 mi parcel-edge distance; road signal >=66; raw-land >=60; shape >=30; node >=52/confidence >=45; FEMA <10% floodway/<50% SFHA and >=3 usable-acre proxy; excluded public/institutional/major-anchor/homebuilder ownership.",
        "priority_rule":"Bexar only; recent parcel source; score >=78; confidence >=68; <=0.60 mi to node; major-road access proxy; flood >=75; parcel execution >=68; mapped sewer within 1,000 ft proxy."
      }
    }
    (DATA/"opportunity_metadata.json").write_text(json.dumps(meta,indent=2))
    print(json.dumps({"highlighted":len(top),"by_county":by_county,"assemblages":len(ass),"errors":len(errors)},indent=2))

if __name__=="__main__":
    main()
