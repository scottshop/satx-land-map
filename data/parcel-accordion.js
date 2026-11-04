/* SATX Land Map: accordion parcel details. Only selected parcels are enriched.
   Public CAD fields vary by county; unavailable fields are never fabricated. */
(function(){
  "use strict";
  function pick(p, names){
    for(var i=0;i<names.length;i++){
      var v=p&&p[names[i]];
      if(v!==null&&v!==undefined&&String(v).trim()!==""&&String(v).trim()!=="null")return String(v).trim();
    }
    return "";
  }
  function money(raw){
    if(raw===""||raw===null||raw===undefined)return "";
    var n=Number(raw);return Number.isFinite(n)?"$"+n.toLocaleString("en-US",{minimumFractionDigits:0,maximumFractionDigits:0}):String(raw);
  }
  function asNumber(raw){
    if(raw===null||raw===undefined||String(raw).trim()==="")return null;
    var n=Number(raw);return Number.isFinite(n)?n:null;
  }
  function sumRawIfKnown(p,names){
    var vals=names.map(function(n){return asNumber(p&&p[n]);}).filter(function(v){return v!==null;});
    if(!vals.length)return null;
    return vals.reduce(function(a,v){return a+v;},0);
  }
  function fixed(raw){
    if(raw===""||raw===null||raw===undefined)return "";
    var n=Number(raw);return Number.isFinite(n)?n.toLocaleString("en-US",{maximumFractionDigits:3}):String(raw);
  }
  function sumIfKnown(p,names){
    var provided=names.map(function(n){return pick(p,[n]);}).filter(Boolean);
    if(!provided.length)return "";
    var total=provided.reduce(function(a,v){return a+Number(v);},0);
    return Number.isFinite(total)?money(total):"";
  }
  function firstAddress(p){
    var raw=pick(p,["Situs","SITUS_ADDR","situs_full","kcad_address","addr_street"]);
    if(!raw)raw=[pick(p,["addr_num","SITUS_NUM","situs_num"]),pick(p,["addr_street","SITUS_STRE","situs_stre"])].filter(Boolean).join(" ");
    return raw;
  }
  function addressParts(p,county){
    var full=firstAddress(p),street=full,
      city=pick(p,["SITUS_CITY","situs_city","situs_city_name"]),
      state=pick(p,["SITUS_STAT","situs_stat"]),
      zip=pick(p,["Situs_Zip","SITUS_ZIP","situs_zip"]);
    var comma=full.split(",").map(function(v){return v.trim();});
    if(comma.length>=3){
      street=comma[0];
      if(!city)city=comma[1];
      var match=comma.slice(2).join(" ").match(/\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\b/);
      if(match){if(!state)state=match[1];if(!zip)zip=match[2];}
    }else if(comma.length===2 && !city && !/\d{5}/.test(comma[1])){
      street=comma[0];city=comma[1];
    }
    // SARA's City field is a tax-jurisdiction label, not necessarily a situs city.
    // Use it for city only if it is present and no situs city is supplied.
    if(!city)city=pick(p,["City"]);
    if(!state && county)state="TX";
    return {street:street,city:city,state:state,zip:zip,county:county?county+" County":""};
  }
  function mailingParts(p,county){
    var lines;
    if(county==="Bexar")lines=["Addr_line1","Addr_line2","Addr_line3","addr_line1","addr_line2","addr_line3"];
    else if(county==="Comal")lines=["PY_ADDR_LI","PY_ADDR__1","PY_ADDR__2","PY_ADDR__3","PY_ADDR__4"];
    else lines=["MAIL_ADDR","MAIL_LINE1","MAIL_LINE2","mail_line1","mail_line2","mail_line3","addr_line1","addr_line2"];
    var chosen=[];
    lines.forEach(function(k){
      var x=pick(p,[k]);
      if(x && chosen.indexOf(x)<0 && !/^(C\/O|ATTN)\s*$/i.test(x))chosen.push(x);
    });
    // Some county services repeat a full mailing address in MAIL_ADDR and MAIL_LINE1.
    if(chosen.length>1 && county!=="Bexar" && county!=="Comal" && chosen[0].indexOf(chosen[1])!==-1)chosen=chosen.slice(0,1);
    var street=chosen.join(", ");
    var city=pick(p,["Addr_city","addr_city","PY_ADDR_CI","MAIL_CITY","mail_city"]);
    var state=pick(p,["Addr_state","addr_state","PY_ADDR_ST","MAIL_STAT","mail_state"]);
    var zip=pick(p,["Zip","zip","PY_ADDR_ZI","MAIL_ZIP","mail_zip"]);
    return {street:street,city:city,state:state,zip:zip};
  }
  function propertyFields(p,county){
    var bexar=county==="Bexar";
    var owner=pick(p,["Owner_name","Owner_Name","OWNER_NAME","PY_OWNER_N","owner_name","file_as_na"]);
    var propId=pick(p,["Prop_id","PropID","PROP_ID","Prop_ID","prop_id","propidtxt","account_id","geo_id","GEO_ID"]);
    var location=addressParts(p,county),mail=mailingParts(p,county);
    var legalAcres=pick(p,["Land_acres","legal_acre","LEGAL_ACRE","legal_acres","LEGAL_AREA"]);
    var gisArea=pick(p,["ParcelArea","Shape_STAr","Shape__Area","Shape.STArea()"]);
    var calculatedAcres=gisArea?fixed(Number(gisArea)/43560):
      (pick(p,["LandSqft"])?fixed(Number(p.LandSqft)/43560):"");
    var improvementFields=["Imprv_hstd_val","Imprv_non_hstd_val"];
    var improvements=bexar?sumRawIfKnown(p,improvementFields):asNumber(pick(p,["IMP_VALUE"]));
    var market=pick(p,["Market_val","MKT_VALUE","APPRAISED","market","market_val"]);
    var marketNumber=asNumber(market);
    var landMarket=marketNumber!==null && improvements!==null && marketNumber>=improvements?
      money(marketNumber-improvements):"";
    var taxyear=pick(p,["Prop_yr","TAX_YEAR","PROP_VAL_Y","owner_tax_","prop_val_yr"]);
    var stateCode=pick(p,["State_cd","state_cd","STAT_LAND_USE","STAT_LAND_"]);
    var cadUse=pick(p,["Property_use_cd","property_use_cd"]);
    var useDescriptions={"001":"Single Family","002":"Rural",
      "009":"Land (potential development land)","099":"Vacant Land",
      "0990":"Land-Only Account","0991":"Pad Site"};
    var zoning=pick(p,["ZONING","Zoning","zoning"]);
    var zoneDescription=pick(p,["ZONING_DESC","ZoneDesc","zone_desc"]);
    var values=[
      ["Market Total Value",money(market)],
      ["Market Land Value (calculated)",landMarket],
      ["Reported Improvement Value",improvements!==null?money(improvements):""],
      ["CAD Land Value",bexar?sumIfKnown(p,["Land_hstd_val","Land_non_hstd_val"]):
        money(pick(p,["LAND_VALUE","land_val","land_hstd_val"]))],
      ["Agricultural Market Value",money(pick(p,["AG_Market","ag_market_val"]))],
      ["Agricultural Use Value",money(pick(p,["AG_Use_val"]))],
      ["Prior Market Value",money(pick(p,["Prior_Mkt_val"]))],
      ["CAD Data Year",taxyear]
    ];
    var landRows=[
      ["Legal Acres",fixed(legalAcres)],["Calculated GIS Acres",calculatedAcres],
      ["Zoning at Selected Point",zoning],["Zoning Description",zoneDescription],
      ["State Classification",stateCode],["CAD Property Use Code",cadUse],
      ["CAD Property Use",bexar?useDescriptions[cadUse]||"":""],
      ["Legal Description",pick(p,["Legal_desc","legal_desc","LEGAL_DESC"])]
    ];
    return {
      owner:owner,parcelId:propId,acres:fixed(legalAcres)||calculatedAcres,
      county:county,location:location,mail:mail,
      sections:[
        {name:"Location",rows:[
          ["Street Address",location.street],["City",location.city],
          ["State",location.state],["Zip",location.zip],
          ["Municipality (CAD tax entity)",pick(p,["City"])],
          ["County",location.county],
          ["School District",pick(p,["School","school_district","SCHOOL_DISTRICT"])]
        ]},
        {name:"Mailing Address",rows:[
          ["Street Address",mail.street],["City",mail.city],
          ["State",mail.state],["Zip",mail.zip]
        ]},
        {name:"Sales History",rows:[
          ["Current Owner",owner],
          ["Last Recorded Deed",pick(p,["Last_Deed_Date"])],
          ["Previous Sale Date",pick(p,["Sale_Date","SALE_DATE","last_sale_date"])],
          ["Previous Sale Price",money(pick(p,["Sale_Price","SALE_PRICE","last_sale_price"]))]
        ]},
        {name:"Value",rows:values},
        {name:"Land",rows:landRows}
      ]
    };
  }
  function row(label,value){
    var el=document.createElement("div");el.className="lgDetailRow";
    var left=document.createElement("span");left.textContent=label;
    var right=document.createElement("strong");right.textContent=value||"Not reported";
    if(!value)right.classList.add("lgUnknown");
    el.appendChild(left);el.appendChild(right);return el;
  }
  function section(data,open){
    var el=document.createElement("section");
    el.className="lgAccordionSection"+(open?" open":"");
    el.dataset.section=data.name;
    var button=document.createElement("button");button.type="button";button.className="lgAccordionHeader";
    button.setAttribute("aria-expanded",open?"true":"false");
    var title=document.createElement("span");title.textContent=data.name;
    var chevron=document.createElement("span");chevron.className="lgChevron";chevron.setAttribute("aria-hidden","true");chevron.textContent="⌃";
    button.appendChild(title);button.appendChild(chevron);
    var body=document.createElement("div");body.className="lgAccordionBody";
    var available=data.rows.filter(function(pair){return pair[1]!==""&&pair[1]!==null&&pair[1]!==undefined;});
    if(!available.length){
      var missing=document.createElement("p");missing.className="lgSectionEmpty";
      missing.textContent=data.name==="Sales History"?
        "No transaction history is included in this county GIS record. Check recorded deeds with the county clerk.":
        data.name==="Mailing Address"?
        "No mailing address is provided in this county GIS record.":
        "No additional information provided by this CAD layer.";
      body.appendChild(missing);
    } else {
      available.forEach(function(pair){body.appendChild(row(pair[0],pair[1]));});
    }
    button.onclick=function(){
      var expanded=el.classList.toggle("open");
      button.setAttribute("aria-expanded",expanded?"true":"false");
    };
    el.appendChild(button);el.appendChild(body);return el;
  }
  function ensureSummary(wrapper,data){
    var bcad=wrapper.querySelector(".bcad-card");
    if(bcad)return; // Existing Bexar summary and Save to Tracker buttons are preserved.
    var popup=wrapper.querySelector(".v7Popup");
    if(!popup)return;
    var summary=popup.querySelector(".lgPropSummary");
    if(!summary){
      summary=document.createElement("div");summary.className="lgPropSummary";
      var facts=popup.querySelector(".popup-facts");
      if(facts)facts.replaceWith(summary);
      else popup.insertBefore(summary,popup.firstChild);
    }
    summary.innerHTML="";
    function item(value,label){
      var v=document.createElement("div");v.className="lgPropPrimary";v.textContent=value||"Not reported";
      var l=document.createElement("div");l.className="lgPropMetaLabel";l.textContent=label;
      summary.appendChild(v);summary.appendChild(l);
    }
    item(data.owner,"Owner");item(data.location.street,"Address");item(data.parcelId,"Parcel ID");
    if(data.acres){
      var acreBadge=document.createElement("div");acreBadge.className="lgHeaderAcres";
      var n=document.createElement("strong");n.textContent=data.acres;
      var label=document.createElement("span");label.textContent="ACRES";
      acreBadge.appendChild(n);acreBadge.appendChild(label);summary.appendChild(acreBadge);
    }
  }
  function render(target,attrs,county){
    if(!target||!target.isConnected)return;
    var full=Object.assign({},attrs,target.__lgZoningFields||{});
    target.__lgFullAttrs=full;
    var data=propertyFields(full,county);
    ensureSummary(target,data);
    var bcad=target.querySelector(".bcad-card"),popup=target.querySelector(".v7Popup");
    var host=bcad?bcad.querySelector(".bcad-card-body"):popup;
    if(!host)return;
    var prior=host.querySelector(".lgAccordionGroup");
    var states={};
    if(prior){
      Array.prototype.forEach.call(prior.querySelectorAll(".lgAccordionSection"),function(s){states[s.dataset.section]=s.classList.contains("open");});
      prior.remove();
    }
    if(bcad){
      Array.prototype.forEach.call(host.querySelectorAll(":scope > .bcad-row"),function(r){r.remove();});
    }
    var group=document.createElement("div");group.className="lgAccordionGroup";
    data.sections.forEach(function(s){group.appendChild(section(s,states[s.name]===undefined?true:states[s.name]));});
    var actions=host.querySelector(".bcad-actions")||host.querySelector(".v7PopupActions")||host.querySelector(".popup-source");
    if(actions)host.insertBefore(group,actions);
    else host.appendChild(group);
    if(bcad){
      var ownerEl=bcad.querySelector(".bcad-owner");
      if(ownerEl&&data.owner)ownerEl.textContent=data.owner;
      var badge=bcad.querySelector(".lgHeaderAcres");
      if(data.acres){
        if(!badge){
          badge=document.createElement("div");badge.className="lgHeaderAcres";
          if(ownerEl)ownerEl.insertAdjacentElement("afterend",badge);
          else bcad.querySelector(".bcad-card-head").appendChild(badge);
        }
        badge.innerHTML="";
        var n=document.createElement("strong");n.textContent=data.acres;
        var lbl=document.createElement("span");lbl.textContent="ACRES";
        badge.appendChild(n);badge.appendChild(lbl);
      }else if(badge)badge.remove();
    }
    if(county==="Bexar" && target.__lgZoningFields){
      var land=group.querySelector('[data-section="Land"] .lgAccordionBody');
      if(land){
        var note=document.createElement("p");note.className="lgSectionFootnote";
        note.textContent="Zoning data is for the selected point, not a parcel-wide determination. Source: COSA GIS zoning layer (2026 snapshot).";
        land.appendChild(note);
      }
    }
  }
  function supplementBexar(wrapper,initial,id){
    if(!window.L||!L.esri||!window.v3ParcelUrl)return;
    var prop=pick(initial,["Prop_id","PropID"]),geo=pick(initial,["Geo_id"]);
    if(!/^[1-9]\d*$/.test(prop)&&!/^[A-Za-z0-9-]+$/.test(geo))return;
    var where=/^[1-9]\d*$/.test(prop)?"Prop_id = "+Number(prop):"Geo_id = '"+geo.replace(/'/g,"''")+"'";
    L.esri.query({url:v3ParcelUrl+"/0"}).where(where)
      .fields(["Prop_id","Geo_id","Owner_name","Addr_line1","Addr_line2","Addr_line3",
        "Addr_city","Addr_state","Zip","Land_acres","Market_val","Land_hstd_val",
        "Land_non_hstd_val","Imprv_hstd_val","Imprv_non_hstd_val","AG_Market",
        "AG_Use_val","Prior_Mkt_val","Last_Deed_Date","School","City","Situs",
        "Situs_Zip","Ownership_Type","Prop_yr","State_cd","Property_use_cd","Legal_desc"])
      .returnGeometry(false).limit(1).run(function(err,fc){
      if(err||!fc||!fc.features||!fc.features.length||!wrapper.isConnected)return;
      if(wrapper.dataset.lgSelected!==id)return;
      var full=fc.features[0].properties||{};
      if(prop&&String(full.Prop_id)!==String(prop))return;
      if(!prop&&geo&&String(full.Geo_id||"").trim()!==geo)return;
      var combined=Object.assign({},initial,full);
      // Preserve the more detailed hosted situs (CITY, TX ZIP) when the
      // older SARA record only supplies a street name.
      if(String(initial.Situs||"").split(",").length>=3 &&
         String(full.Situs||"").split(",").length<3)combined.Situs=initial.Situs;
      wrapper.__lgFullAttrs=combined;
      render(wrapper,combined,"Bexar");
      var bcad=wrapper.querySelector(".bcad-card");
      var owner=pick(combined,["Owner_name","Owner_Name"]);
      if(bcad){
        var ownerNode=bcad.querySelector(".bcad-owner");
        if(ownerNode&&owner)ownerNode.textContent=owner;
        if(Number(full.Prop_id)>0){
          var chip=bcad.querySelector(".bcad-chip:last-child");
          if(chip)chip.textContent="ID "+full.Prop_id+(geo?" · GEO "+geo:"");
          bcad.setAttribute("data-bcad-prop-id",full.Prop_id);
          var copy=bcad.querySelector(".copy-property-id");
          if(copy)copy.dataset.propertyId=String(full.Prop_id);
        }
      }
      var save=wrapper.querySelector(".save-to-tracker");
      if(save){
        try{
          var payload=JSON.parse(decodeURIComponent(save.getAttribute("data-tracker-payload")||""));
          if(owner)payload.owner=owner;
          if(Number(full.Prop_id)>0){
            payload.parcelId=String(full.Prop_id);
            if(typeof window.v12TrackerMapLink==="function")payload.mapLink=window.v12TrackerMapLink("Bexar",full.Prop_id);
          }
          if(full.Land_acres!=null)payload.acres=full.Land_acres;
          save.setAttribute("data-tracker-payload",encodeURIComponent(JSON.stringify(payload)));
        }catch(e){}
      }
    });
  }
  function supplementSanAntonioZoning(wrapper,latlng,id){
    if(!latlng||typeof latlng.lat!=="number"||typeof latlng.lng!=="number")return;
    if(!window.L||!L.esri)return;
    // Query only once per selected parcel; no zoning layers are rendered to the map.
    var source="https://maps.pape-dawson.com/server2/rest/services/PD_GIS_Webmap/PD_GIS_WebMap__SanAntonio_External/MapServer/30";
    L.esri.query({url:source}).intersects(latlng)
      .fields(["Zoning","Base","BaseDescri","ZoningDeta","COSA_Zone"])
      .returnGeometry(false).limit(1).run(function(err,fc){
        if(err||!fc||!fc.features||!fc.features.length||!wrapper.isConnected)return;
        if(wrapper.dataset.lgSelected!==id)return;
        var p=fc.features[0].properties||{};
        var code=pick(p,["Zoning","Base"]),description=pick(p,["BaseDescri","ZoningDeta"]);
        if(!code&&!description)return;
        var cityStatus=code==="OCL"?"Outside San Antonio city limits (at clicked point)":code;
        wrapper.__lgZoningFields={ZONING:cityStatus,ZONING_DESC:description};
        render(wrapper,wrapper.__lgFullAttrs||{},"Bexar");
      });
  }
  window.v32RenderParcelAccordion=function(root,selectedPoint){
    if(!root)return;
    var anchor=root.querySelector(".lg-detail-data");
    if(!anchor)return;
    var county=anchor.getAttribute("data-lg-county")||"";
    var attrs;
    try{attrs=JSON.parse(decodeURIComponent(anchor.getAttribute("data-lg-attrs")||""));}catch(e){return;}
    if(!attrs||typeof attrs!=="object")return;
    var id=[county,pick(attrs,["Prop_id","PropID","PROP_ID","Prop_ID","prop_id","geo_id","GEO_ID"])].join(":");
    root.dataset.lgSelected=id;
    render(root,attrs,county);
    if(county==="Bexar"){
      supplementBexar(root,attrs,id);
      supplementSanAntonioZoning(root,selectedPoint,id);
    }
  };
})();