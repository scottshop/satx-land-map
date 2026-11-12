// Regression test for Google Apps Script bridge after Deals column moves.
// Run: node tests/tracker-bridge.cjs
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const file=require('node:path').join(__dirname,'../tracker-bridge/Code.gs');
const code=fs.readFileSync(file,'utf8');
const headers=['Location / Intersection','Priority','Size (AC)','Attachments','Stage','Purchase Price','Price (PSF)','Point Person','Contact Made?','Last Contact','Owner Contact','Notes','Map Link',''];
const cells=[headers];
for(let row=2;row<=234;row++){
  const a=Array(14).fill('');
  a[1]=false;a[8]=false;
  if(row<=76){
    a[0]='Tracked location '+row;
    a[2]='5.00 AC';
    a[3]='📎 Files';
    a[4]=row===4?'LOI':'Pursuing';
    a[10]=row===4?'Real owner contact':'';
    a[12]=row===4
      ?'https://scottshop.github.io/satx-land-map/?importCounty=Bexar&importParcel=619202'
      :'https://scottshop.github.io/satx-land-map/?county=Comal&parcel='+row;
  }
  cells.push(a);
}
let writes=0;
const richLinks={};
const sheet={
 getLastColumn:()=>14,
 getLastRow:()=>234,
 getMaxRows:()=>234,
 getRange:(row,col,n=1,w=1)=>({
   getDisplayValues:()=>Array.from({length:n},(_,i)=>cells[row+i-1].slice(col-1,col+w-1).map(v=>v===false?'FALSE':String(v??''))),
   getValues:()=>Array.from({length:n},(_,i)=>cells[row+i-1].slice(col-1,col+w-1)),
   setValues:(v)=>{v.forEach((x,i)=>x.forEach((item,j)=>cells[row+i-1][col+j-1]=item));writes++;return this;},
   setRichTextValue:(v)=>{cells[row-1][col-1]=v.text;richLinks[row]=v.uri;return this;}
 })
};
const ContentService={
 MimeType:{JSON:'json',JAVASCRIPT:'js'},
 createTextOutput:(text)=>({text,setMimeType:function(){return this;}})
};
const context={SpreadsheetApp:{openById:()=>({getSheetByName:()=>sheet}),flush:()=>{},
 newRichTextValue:()=>({text:'',uri:'',setText:function(v){this.text=v;return this;},setLinkUrl:function(v){this.uri=v;return this;},build:function(){return this;}})},
 LockService:{getScriptLock:()=>({tryLock:()=>true,releaseLock:()=>{}})},
 ContentService,console,Date,
 Utilities:{getUuid:()=> '12345678-aaaa-bbbb-cccc-12345678bbbb'},
 PropertiesService:{getScriptProperties:()=>({setProperty:()=>{}})}
};
vm.createContext(context);
vm.runInContext(code,context,{filename:file});
const get=()=>JSON.parse(context.doGet({parameter:{action:'trackerSites'}}).text);
const post=p=>JSON.parse(context.doPost({parameter:p}).text);
let live=get();
assert.equal(live.ok,true);
assert.equal(live.sites.length,75);
const ex=live.sites.find(x=>x.row===4);
assert.equal(ex.county,'Bexar');
assert.equal(ex.parcelId,'619202');
assert.equal(ex.stage,'LOI');
assert.equal(ex.owner,'Real owner contact');
const duplicate=post({county:'Bexar',parcelId:'619202',mapLink:cells[3][12]});
assert.equal(duplicate.duplicate,true);
assert.equal(writes,0);
const mapLink='https://scottshop.github.io/satx-land-map/?county=Guadalupe&parcel=001245';
const added=post({county:'Guadalupe',parcelId:'001245',mapLink,locationText:'NWC Test & IH-10',dealSite:'=HYPERLINK("https://www.google.com/maps/search/?api=1&query=29.47390609%2C-98.29319984","NWC Test & IH-10")',acres:'12.34',owner:'Known landowner',notes:'Test save',latitude:'29.47390609',longitude:'-98.29319984'});
assert.equal(added.ok,true);
assert.equal(added.row,77);
assert.equal(cells[76][0],'NWC Test & IH-10');
assert.equal(richLinks[77],'https://www.google.com/maps/search/?api=1&query=29.47390609%2C-98.29319984');
assert.equal(cells[76][2],'12.34 AC');
assert.equal(cells[76][4],'Pursuing');
assert.equal(cells[76][10],'Known landowner');
assert.equal(cells[76][11],'Test save');
assert.equal(cells[76][12],mapLink);
assert.equal(cells[76][1],false);
assert.equal(cells[76][8],false);
assert.equal(cells[76][3],'');
live=get();
assert.equal(live.sites.length,76);
assert.equal(live.sites.find(x=>x.parcelId==='001245').county,'Guadalupe');
assert.equal(post({county:'Guadalupe',parcelId:'001245',mapLink}).duplicate,true);
assert.equal(writes,1);
assert.equal(post({county:'Comal',parcelId:'001245',mapLink}).ok,false);
assert.equal(writes,1);
console.log('PASS tracker bridge read, coordinate Location hyperlink, append, preserve checkboxes, and duplicate detection');
