import {parseCSV} from './csv.js';
import {uid,stamp} from './model.js';
const norm=s=>String(s??'').toLowerCase().replace(/[^a-z0-9]/g,'');
function field(header, options){for(const o of options){const j=header.findIndex(h=>norm(h)===norm(o));if(j>=0)return j;}return -1;}
function value(row,idx){return idx<0?null:(row[idx]??'').trim();}
export function numberValue(s){
 if(s===null||s===undefined||String(s).trim()===''||['—','-','--','n/a','null'].includes(String(s).toLowerCase().trim()))return null;
 const cleaned=String(s).replace(/[,₹$€£%\s]/g,'');
 if(!/^-?\d+(\.\d+)?$/.test(cleaned))throw Error(`Invalid numeric metric: ${String(s).slice(0,35)}`);
 const n=Number(cleaned); if(!Number.isFinite(n)||n<0)throw Error('Metrics must be nonnegative finite numbers.');return n;
}
export function normalizeDate(s){if(!s)return '';const v=String(s).trim();if(/^\d{4}-\d{2}-\d{2}$/.test(v)){const d=new Date(`${v}T00:00:00Z`);return d.toISOString().slice(0,10)===v?v:'';}const m=v.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);if(m){const d=`${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}`;return normalizeDate(d);}return '';}
export function importPerformanceCSV(text,{platform,currency='INR',conversionDefinition='',fileName='report.csv',importId=uid()}={}) {
 if(!['Meta','Google'].includes(platform))throw Error('Choose Meta or Google as the platform.');
 if(!/^[A-Z]{3}$/.test(currency))throw Error('Enter a valid three-letter currency.');
 const rows=parseCSV(text);if(rows.length<2)throw Error('CSV needs a header and at least one data row.');
 const candidates=rows.slice(0,12);let headerIndex=candidates.findIndex(r=>field(r,platform==='Meta'?['Campaign name','Campaign']:['Campaign','Campaign name'])>=0 && field(r,platform==='Meta'?['Amount spent','Amount spent (INR)','Spend']:['Cost','Cost (INR)','Spend'])>=0);
 if(headerIndex<0)throw Error('Unable to find campaign and spend/cost columns. See the CSV format guide.');
 const headers=rows[headerIndex]; const ix={
 campaign:field(headers,['Campaign name','Campaign']),group:field(headers,['Ad set name','Ad group','Ad group name','Asset group']),
 spend:field(headers,platform==='Meta'?['Amount spent','Amount spent (INR)','Spend','Cost']:['Cost','Cost (INR)','Spend']),
 impressions:field(headers,['Impressions']),clicks:field(headers,['Clicks','Link clicks','Clicks (all)']),
 conversions:field(headers,['Conversions','Leads','Purchases','Website purchases']),value:field(headers,['Conv. value','Conversion value','Purchase conversion value','Purchases conversion value','Total conversion value']),
 start:field(headers,['Day','Date','Reporting starts','Start date']),end:field(headers,['Reporting ends','End date']),
 };
 if(ix.impressions<0||ix.clicks<0)throw Error('CSV must contain Impressions and Clicks columns.');
 let definition=conversionDefinition.trim();
 if(!definition&&ix.conversions>=0)definition=String(headers[ix.conversions]);
 const out=[]; const warnings=[];
 for(let i=headerIndex+1;i<rows.length;i++){
  const r=rows[i],campaign=value(r,ix.campaign);
  if(!campaign||/^total[: ]|^account total|^overall total/i.test(campaign))continue;
  if(r.length>headers.length+1){warnings.push(`Skipped row ${i+1}: unexpected extra columns.`);continue;}
  try{
   const startRaw=value(r,ix.start),endRaw=value(r,ix.end);const startDate=startRaw?normalizeDate(startRaw):'', endDate=endRaw?normalizeDate(endRaw):startDate;
   if((startRaw&&!startDate)||(endRaw&&!endDate))throw Error('Unsupported date; use YYYY-MM-DD or MM/DD/YYYY.');
   const spend=numberValue(value(r,ix.spend)),impressions=numberValue(value(r,ix.impressions)),clicks=numberValue(value(r,ix.clicks));
   if(spend===null||impressions===null||clicks===null)throw Error('Spend, impressions and clicks cannot be blank.');
   const conv=numberValue(value(r,ix.conversions)),convValue=numberValue(value(r,ix.value));
   out.push({id:`${importId}-${i}`,importId,platform,campaign:campaign.slice(0,250),adGroup:(value(r,ix.group)||'').slice(0,250),startDate,endDate,currency,spend,impressions,clicks,conversions:conv,conversionValue:convValue,conversionDefinition:definition||'Not supplied',attribution:'Platform-reported; attribution configuration not verified',importedAt:stamp(),provenance:'User-imported platform CSV'});
  }catch(e){warnings.push(`Skipped row ${i+1}: ${e.message}`);}
 }
 if(!out.length)throw Error(`No valid campaign rows found. ${warnings.slice(0,2).join(' ')}`);
 if(warnings.length>30)warnings.splice(30,Infinity,`Plus additional skipped rows.`);
 if(ix.conversions<0)warnings.unshift('Conversion column absent: conversion totals are unavailable, not zero.');
 if(ix.value<0)warnings.unshift('Conversion value absent: ROAS is unavailable.');
 return {rows:out, warnings,meta:{id:importId,fileName:fileName.slice(0,200),platform,currency,conversionDefinition:definition||'Not supplied',rowCount:out.length,skippedCount:warnings.filter(x=>x.startsWith('Skipped')).length,createdAt:stamp(),type:'performance-csv',source:'User-imported CSV'}};
}
export function aggregate(rows) {
 const curr=[...new Set(rows.map(x=>x.currency).filter(Boolean))];const definitions=[...new Set(rows.filter(x=>x.conversions!==null).map(x=>x.conversionDefinition).filter(Boolean))];
 const mixedCurrency=curr.length>1,mixedDefinitions=definitions.length>1;
 const sum=k=>rows.reduce((s,r)=>s+(Number.isFinite(r[k])?r[k]:0),0);
 const any=k=>rows.some(r=>Number.isFinite(r[k]));
 const conversions=(!mixedDefinitions&&rows.length>0&&rows.every(r=>Number.isFinite(r.conversions)))?sum('conversions'):null;
 const conversionValue=(!mixedCurrency&&!mixedDefinitions&&rows.length>0&&rows.every(r=>Number.isFinite(r.conversionValue)))?sum('conversionValue'):null;
 const spend=(!mixedCurrency&&any('spend'))?sum('spend'):null;
 const impressions=any('impressions')?sum('impressions'):null,clicks=any('clicks')?sum('clicks'):null;
 return {rowCount:rows.length,currency:curr.length===1?curr[0]:null,mixedCurrency,mixedDefinitions,definitions,spend,impressions,clicks,conversions,conversionValue,ctr:clicks!==null&&impressions>0?clicks/impressions*100:null,cpc:spend!==null&&clicks>0?spend/clicks:null,cpa:spend!==null&&conversions>0?spend/conversions:null,roas:spend>0&&conversionValue!==null?conversionValue/spend:null};
}
export function insights({ads=[],competitors=[],pages=[],performance=[]}) {
 const out=[];
 const add=(title,detail,kind='Observation')=>out.push({title,detail,kind});
 if(!ads.length)add('Start your creative library','Save a public ad or add one manually. Comparisons will use only your own observations.');
 else {
  const notLinked=ads.filter(x=>!x.competitorId).length;
  if(notLinked)add('Link ad records to competitors',`${notLinked} saved ads are not associated with a competitor. This makes watchlist analysis less complete.`);
  const unobserved=ads.filter(x=>!x.observations?.length).length;
  if(unobserved)add('Observation history is incomplete',`${unobserved} ads have no verification snapshots. Use “Observe” when you revisit their source.`);
  const categories=new Map();for(const ad of ads)categories.set(ad.category,(categories.get(ad.category)||0)+1);
  const lead=[...categories.entries()].sort((a,b)=>b[1]-a[1])[0];if(lead)add('Most researched category',`${lead[0]} accounts for ${lead[1]} of ${ads.length} manually saved ads. This describes your saved research, not market share.`,'Calculated fact');
 }
 if(!pages.length)add('Build a landing-page evidence bank','Save product or landing pages directly from the extension popup.');
 const byPlatform=['Meta','Google'].map(platform=>({platform,rows:performance.filter(r=>r.platform===platform)}));
 for(const {platform,rows} of byPlatform){if(!rows.length){add(`${platform} account data not imported`,'Upload an authorized platform CSV to unlock verified account-level calculations. No API connection has been made.');continue;}
 const a=aggregate(rows);if(a.conversions===null)add(`${platform}: conversion definition missing or incompatible`,'Cost per conversion and ROAS require compatible, platform-reported input fields.');
 if(a.clicks===0&&a.spend>0)add(`${platform}: spend with no recorded clicks`,'Check the selected reporting range and click metric in the source export.','Calculated fact');
 }
 if(!competitors.some(c=>c.watch))add('Watchlist is empty','Mark priority competitors as watched. Observation checks are manual, not scheduled.');
 return out;
}
