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
    var full=firstAddress(p), street=full, city=pick(p,["SITUS_CITY","situs_city","City"]), state=pick(p,["SITUS_STAT","situs_stat"]), zip=pick(p,["Situs_Zip","SITUS_ZIP","situs_zip"]);
    // Hosted BCAD situs can be "STREET, CITY, TX 78253". SARA situs is often street only.
    var comma=full.split(",").map(function(v){return v.trim();});
    if(comma.length>=3){
      street=comma[0];
      if(!city)city=comma[1];
      var match=comma.slice(2).join(" ").match(/\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\b/);
      if(match){if(!state)state=match[1];if(!zip)zip=match[2];}
    }else if(comma.length===2 && !city && !/\d{5}/.test(comma[1])){street=comma[0];city=comma[1];}
    if(!state && county && ["Bexar","Comal","Guadalupe","Kendall","Kerr","Medina","Blanco","Webb"].indexOf(county)>=0)state="TX";
    return {street:street,city:city,state:state,zip:zip,county:county?county+" County":""};
  }
  function mailingParts(p,county){
    var street;
    if(county==="Bexar")street=pick(p,["Addr_line1","Addr_line2","Addr_line3"]);
    else if(county==="Comal")street=pick(p,["PY_ADDR_LI","PY_ADDR__1","PY_ADDR__2","PY_ADDR__3"]);
    else street=pick(p,["MAIL_ADDR","MAIL_LINE1","mail_line1","addr_line1","mail_line2","addr_line2"]);
    if(!street)street=pick(p,["MAIL_LINE2","mail_line3","addr_line3"]);
    var city=pick(p,["Addr_city","PY_ADDR_CI","MAIL_CITY","mail_city","addr_city"]);
    var state=pick(p,["Addr_state","PY_ADDR_ST","MAIL_STAT","mail_state","addr_state"]);
    var zip=pick(p,["Zip","PY_ADDR_ZI","MAIL_ZIP","mail_zip","addr_zip"]);
    // Do not infer mailing address from the situs address; the owner may live elsewhere.
    return {street:street,city:city,state:state,zip:zip};
  }
  function propertyFields(p,county){
    var bexar=county==="Bexar";
    var owner=pick(p,["Owner_name","Owner_Name","OWNER_NAME","PY_OWNER_N","owner_name","file_as_na"]);
    var propId=pick(p,["Prop_id","PropID","PROP_ID","Prop_ID","prop_id","propidtxt","account_id","geo_id","GEO_ID"]);
    var location=addressParts(p,county),mail=mailingParts(p,county);
    var area=pick(p,["Land_acres","legal_acre","LEGAL_ACRE","legal_acres","LEGAL_AREA"]);
    var landRows=[
      ["Legal Acres",fixed(area)],
      ["Calculated Acres",fixed(p.LandSqft?Number(p.LandSqft)/43560:(p.Shape_STAr?Number(p.Shape_STAr)/43560:""))],
      ["Zoning",pick(p,["ZONING","Zoning","zoning"])],
      ["Zoning Description",pick(p,["ZONING_DESC","ZoneDesc","zone_desc"])],
      ["Land Use Code",pick(p,["State_cd","STAT_LAND_USE","STAT_LAND_","LOC_LAND_USE","LOC_LAND_U","Property_use_cd"])],
      ["Legal Description",pick(p,["Legal_desc","legal_desc","LEGAL_DESC"])]
    ];
    var market=pick(p,["Market_val","MKT_VALUE","APPRAISED","market","market_val"]);
    var taxyear=pick(p,["Prop_yr","TAX_YEAR","PROP_VAL_Y","owner_tax_","prop_val_yr"]);
    var values=[
      ["Market Total Value",money(market)],
      ["Reported Land Value",bexar?sumIfKnown(p,["Land_hstd_val","Land_non_hstd_val"]):money(pick(p,["LAND_VALUE","land_val","land_hstd_val"]))],
      ["Reported Improvement Value",bexar?sumIfKnown(p,["Imprv_hstd_val","Imprv_non_hstd_val"]):money(pick(p,["IMP_VALUE"]))],
      ["Agricultural Market Value",money(pick(p,["AG_Market","ag_market_val"]))],
      ["Agricultural Use Value",money(pick(p,["AG_Use_val"]))],
      ["Prior Market Value",money(pick(p,["Prior_Mkt_val"]))],
      ["Assessment / Data Year",taxyear]
    ];
    return {
      owner:owner,parcelId:propId,location:location,mail:mail,county:county,
      sections:[
        {name:"Location",rows:[
          ["Street Address",location.street],["City",location.city],["State",location.state],
          ["Zip",location.zip],["Municipality",pick(p,["municipality","Municipality"])],
          ["County",location.county],["School District",pick(p,["School","school_district","SCHOOL_DISTRICT"])]
        ]},
        {name:"Mailing Address",rows:[
          ["Street Address",mail.street],["City",mail.city],["State",mail.state],["Zip",mail.zip]
        ]},
        {name:"Sales History",rows:[
          ["Current Owner",owner],["Last Recorded Deed",pick(p,["Last_Deed_Date"])],
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
    data.rows.forEach(function(pair){body.appendChild(row(pair[0],pair[1]));});
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
  }
  function render(target,attrs,county){
    if(!target||!target.isConnected)return;
    var data=propertyFields(attrs,county);
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
      if(data.owner){
        var ownerEl=bcad.querySelector(".bcad-owner");
        if(ownerEl)ownerEl.textContent=data.owner;
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
  window.v32RenderParcelAccordion=function(root){
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
    if(county==="Bexar")supplementBexar(root,attrs,id);
  };
})();