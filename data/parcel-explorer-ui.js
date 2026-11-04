/* SATX Parcel Explorer: map-first property details and search UI.
   Uses existing CAD/Tracker bindings; no new data sources or credentials. */
(function(){
  "use strict";
  function boot(){
    if(window.__satxParcelExplorerReady)return;
    var map=window.map_33cc2c2ac68d72d2971fbb7de3650b24;
    if(!map || !document.getElementById("v9ParcelSearch")){
      setTimeout(boot,80); return;
    }
    window.__satxParcelExplorerReady=true;
    var icon={
      menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
      search:'<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
      layers:'<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/>',
      reset:'<circle cx="12" cy="12" r="7"/><path d="M12 2v5m0 10v5M2 12h5m10 0h5"/>'
    };
    function svg(path){return '<svg class="lgIcon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'+path+'</svg>';}
    var search=document.createElement("div");
    search.id="lgSearchBar";
    search.setAttribute("role","search");
    search.innerHTML=
      '<button type="button" id="lgMenuBtn" aria-label="Open Land Finder">'+svg(icon.menu)+'</button>'+
      '<span class="lgSearchIcon">'+svg(icon.search)+'</span>'+
      '<input id="lgQuickSearch" type="search" autocomplete="off" aria-label="Search owner, address or parcel ID" placeholder="Owner, address, or parcel ID"/>'+
      '<button type="button" id="lgSearchSubmit" aria-label="Search parcels">'+svg(icon.search)+'</button>';
    document.body.appendChild(search);
    var drawer=document.createElement("aside");
    drawer.id="lgDrawer";
    drawer.setAttribute("aria-label","Selected parcel details");
    drawer.setAttribute("aria-hidden","true");
    drawer.innerHTML=
      '<div class="lgDrawerHandle" aria-hidden="true"></div>'+
      '<div class="lgDrawerTop"><span class="lgEyebrow">Property information</span>'+
      '<button type="button" id="lgCloseDetails" aria-label="Close property details" title="Close">×</button></div>'+
      '<div id="lgDetails"></div>';
    document.body.appendChild(drawer);
    var details=drawer.querySelector("#lgDetails");
    var rail=document.createElement("div");
    rail.id="lgRail";
    rail.setAttribute("aria-label","Map navigation");
    rail.innerHTML=
      '<button type="button" id="lgZoomIn" aria-label="Zoom in" title="Zoom in">+</button>'+
      '<button type="button" id="lgZoomOut" aria-label="Zoom out" title="Zoom out">−</button>'+
      '<button type="button" id="lgReset" aria-label="Reset San Antonio map view" title="Reset map view">'+svg(icon.reset)+'</button>'+
      '<button type="button" id="lgMapLayers" aria-label="Map layers" title="Map layers">'+svg(icon.layers)+'</button>';
    document.body.appendChild(rail);
    // Keep controls isolated so clicking them never identifies a map parcel.
    if(window.L && L.DomEvent){
      [search,drawer,rail].forEach(function(el){
        L.DomEvent.disableClickPropagation(el);
        L.DomEvent.disableScrollPropagation(el);
      });
    }
    function showFinder(){
      var panel=document.getElementById("v6TopPanel");
      var toggle=document.getElementById("v6TopToggle");
      if(!panel||!toggle)return;
      if(getComputedStyle(panel).display==="none")toggle.click();
    }
    function doSearch(){
      var v=search.querySelector("#lgQuickSearch").value.trim();
      var input=document.getElementById("v9ParcelSearch");
      if(!input)return;
      input.value=v;
      showFinder();
      // The underlying Land Finder already handles all eight counties.
      var btn=document.getElementById("v9SearchBtn");
      if(btn)btn.click();
    }
    search.querySelector("#lgMenuBtn").addEventListener("click",showFinder);
    search.querySelector("#lgSearchSubmit").addEventListener("click",doSearch);
    search.querySelector("#lgQuickSearch").addEventListener("keydown",function(e){
      if(e.key==="Enter"){e.preventDefault();doSearch();}
    });
    rail.querySelector("#lgZoomIn").onclick=function(){map.zoomIn();};
    rail.querySelector("#lgZoomOut").onclick=function(){map.zoomOut();};
    rail.querySelector("#lgReset").onclick=function(){map.setView([29.505,-98.55],10);};
    rail.querySelector("#lgMapLayers").onclick=function(){
      var btn=document.getElementById("v17LayersToggle");if(btn)btn.click();
    };
    function closeDrawer(){
      drawer.classList.remove("lgOpen");
      drawer.setAttribute("aria-hidden","true");
      document.body.classList.remove("lgDrawerVisible");
      details.innerHTML="";
    }
    drawer.querySelector("#lgCloseDetails").onclick=closeDrawer;
    document.addEventListener("keydown",function(e){if(e.key==="Escape"&&drawer.classList.contains("lgOpen"))closeDrawer();});
    function bindCopyButtons(){
      Array.prototype.forEach.call(details.querySelectorAll(".copy-property-id"),function(button){
        button.onclick=async function(){
          try{
            await navigator.clipboard.writeText(button.dataset.propertyId||"");
            button.textContent="Copied";
          }catch(err){button.textContent="Copy unavailable";}
        };
      });
    }
    function addShareAction(){
      var save=details.querySelector(".save-to-tracker"), actions=
        details.querySelector(".bcad-actions")||details.querySelector(".v7PopupActions");
      if(!save||!actions)return;
      var data;
      try{data=JSON.parse(decodeURIComponent(save.getAttribute("data-tracker-payload")||""));}catch(e){return;}
      if(!data.county||!data.parcelId)return;
      var copy=document.createElement("button");
      copy.type="button";
      copy.textContent="Copy map link";
      copy.title="Copy a link to this parcel";
      copy.onclick=async function(){
        var url="https://scottshop.github.io/satx-land-map/?county="+
          encodeURIComponent(data.county)+"&parcel="+encodeURIComponent(data.parcelId);
        try{await navigator.clipboard.writeText(url);copy.textContent="Link copied";}
        catch(e){copy.textContent="Copy unavailable";}
      };
      actions.appendChild(copy);
    }
    function displayPopupInDrawer(evt){
      if(!evt||!evt.popup)return;
      var popup=evt.popup,el=popup.getElement&&popup.getElement();
      if(!el)return;
      var old=el.querySelector(".leaflet-popup-content");
      if(!old)return;
      // Only intercept parcel and tracker details: non-parcel map alerts
      // retain native Leaflet popups.
      var isParcel=!!(old.querySelector(".bcad-card")||
        old.querySelector(".popup-facts")||
        old.querySelector(".v7Popup")&&old.textContent.indexOf("PARCEL")>=0);
      if(!isParcel)return;
      var clone=old.cloneNode(true);
      details.innerHTML="";
      while(clone.firstChild)details.appendChild(clone.firstChild);
      drawer.classList.add("lgOpen");
      drawer.setAttribute("aria-hidden","false");
      document.body.classList.add("lgDrawerVisible");
      details.scrollTop=0;
      bindCopyButtons();
      if(typeof window.v12BindTrackerButtons==="function")window.v12BindTrackerButtons(details);
      if(typeof window.v31HydrateBexarOwner==="function")window.v31HydrateBexarOwner(details);
      addShareAction();
      // The dock replaces the small balloon so the property boundary remains
      // visible, while retaining parcel selection/highlighting on the map.
      setTimeout(function(){if(map._popup===popup)map.closePopup(popup);},20);
    }
    map.on("popupopen",function(e){setTimeout(function(){displayPopupInDrawer(e);},0);});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
  else boot();
})();
