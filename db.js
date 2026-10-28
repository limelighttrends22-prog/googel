import {STORES,DB_VERSION,validUrl} from './model.js';
const NAME='limelight_ad_intelligence_v1';
let connection;
export function openDB(){
 if(connection) return connection;
 connection=new Promise((resolve,reject)=>{
   const req=indexedDB.open(NAME,DB_VERSION);
   req.onupgradeneeded=()=>{const db=req.result;for(const s of STORES) if(!db.objectStoreNames.contains(s)) db.createObjectStore(s,{keyPath:'id'});};
   req.onsuccess=()=>{const db=req.result;db.onversionchange=()=>{db.close();connection=null;};resolve(db);};
   req.onerror=()=>{connection=null;reject(req.error||new Error('Unable to open local database.'));};
   req.onblocked=()=>reject(new Error('Close other Limelight tabs before upgrading the database.'));
 });
 return connection;
}
export async function all(store){
 if(!STORES.includes(store))throw Error('Unknown record type.'); const db=await openDB();
 return new Promise((resolve,reject)=>{const tx=db.transaction(store,'readonly');const req=tx.objectStore(store).getAll();req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
}
export async function get(store,id){const db=await openDB();return new Promise((resolve,reject)=>{const r=db.transaction(store,'readonly').objectStore(store).get(id);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
export async function put(store,record){return transact(store,s=>s.put(record));}
export async function remove(store,id){return transact(store,s=>s.delete(id));}
function transact(store,op){
 if(!STORES.includes(store))throw Error('Unknown record type.');
 return openDB().then(db=>new Promise((resolve,reject)=>{let tx=db.transaction(store,'readwrite');try{op(tx.objectStore(store));}catch(e){tx.abort();reject(e);return;}tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error||new Error('Storage write failed.'));tx.onabort=()=>reject(tx.error||new Error('Storage write aborted.'));}));
}
export async function bulkAdd(store,records){
 if(!STORES.includes(store))throw Error('Unknown record type.'); const db=await openDB();
 return new Promise((resolve,reject)=>{const tx=db.transaction(store,'readwrite');for(const record of records)tx.objectStore(store).put(record);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});
}
export async function clearAll(){const db=await openDB();return new Promise((resolve,reject)=>{const tx=db.transaction(STORES,'readwrite');for(const s of STORES)tx.objectStore(s).clear();tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}
export async function snapshot(){const data={};for(const s of STORES)data[s]=await all(s);return {app:'Limelight Ad Intelligence',schemaVersion:DB_VERSION,exportedAt:new Date().toISOString(),data};}
export function validateBackup(obj){
 if(!obj||obj.app!=='Limelight Ad Intelligence'||obj.schemaVersion!==DB_VERSION||!obj.data||typeof obj.data!=='object') throw Error('Unsupported backup format/version.');
 const str=(v,max=10000)=>v===undefined||v===null||(typeof v==='string'&&v.length<=max);
 const num=(v)=>v===null||(typeof v==='number'&&Number.isFinite(v)&&v>=0);
 for(const store of STORES){
  const rows=obj.data[store];if(!Array.isArray(rows)||rows.length>50000)throw Error(`Invalid or oversized ${store} data.`);
  const ids=new Set();
  for(const r of rows){
   if(!r||typeof r!=='object'||Array.isArray(r)||typeof r.id!=='string'||!r.id||r.id.length>120||ids.has(r.id))throw Error(`Duplicate/invalid record in ${store}.`);
   ids.add(r.id);
   if(JSON.stringify(r).length>50000)throw Error(`Oversized record in ${store}.`);
   for(const [k,v] of Object.entries(r))if(typeof v==='string'&&v.length>12000)throw Error(`Oversized ${k} field in ${store}.`);
   if(store==='competitors'&&(!str(r.name,120)||!r.name||r.website&&!validUrl(r.website)))throw Error('Invalid competitor name or URL.');
   if(store==='ads'){
    if(!str(r.advertiser,120)||!r.advertiser||r.sourceUrl&&!validUrl(r.sourceUrl)||r.landingUrl&&!validUrl(r.landingUrl))throw Error('Invalid advertisement data.');
    if(!Array.isArray(r.observations)||r.observations.length>2000||r.observations.some(o=>!o||!['unknown','active','inactive'].includes(o.status)||!str(o.note,1500)||!str(o.at,50)))throw Error('Invalid observation history.');
   }
   if(store==='pages'&&(!r.url||!validUrl(r.url)))throw Error('Invalid landing page URL.');
   if(store==='performance'&&(!['Meta','Google'].includes(r.platform)||!/^[A-Z]{3}$/.test(r.currency||'')||!num(r.spend)||!num(r.impressions)||!num(r.clicks)||!num(r.conversions)||!num(r.conversionValue)))throw Error('Invalid imported metrics.');
   if((store==='reports'||store==='hypotheses')&&(!str(r.title,250)||!r.title))throw Error(`Invalid ${store} title.`);
  }
 }
 return true;
}
export async function restore(obj,{replace=false}={}){
 validateBackup(obj);const db=await openDB();
 return new Promise((resolve,reject)=>{const tx=db.transaction(STORES,'readwrite');if(replace)for(const s of STORES)tx.objectStore(s).clear();for(const s of STORES)for(const r of obj.data[s]){const normalized=JSON.parse(JSON.stringify(r));tx.objectStore(s).put(normalized);}tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error||new Error('Restore failed.'));tx.onabort=()=>reject(tx.error||new Error('Restore cancelled.'));});
}
export const preferences=async()=>({theme:'dark',currency:'INR',...(await chrome.storage.local.get(['theme','currency']))});
export const savePreferences=values=>chrome.storage.local.set(values);
