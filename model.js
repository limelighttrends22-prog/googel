export const CATEGORIES = ['Skincare','Sunscreen','Face serum','Face wash','Haircare','Cosmetics','Oral care','Toothpaste','Herbal personal care','Body care','Sheet masks','Other'];
export const PLATFORMS = ['Meta','Google Search','Google Shopping','Google Display','Google Performance Max','Other'];
export const FORMATS = ['Image','Video','Carousel','Text','Shopping','Collection','Other'];
export const STORES = ['competitors','ads','pages','reports','imports','hypotheses','performance'];
export const DB_VERSION = 1;
export const stamp = () => new Date().toISOString();
export const uid = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
export const tidy = (x, max=1500) => String(x??'').trim().slice(0,max);
export function validUrl(value, {allowBlank=false}={}) {
  if (!value) return allowBlank;
  try { const u = new URL(value); return ['http:','https:'].includes(u.protocol) && Boolean(u.hostname) && !u.username && !u.password; } catch { return false; }
}
export function urlOrEmpty(v) { const value=tidy(v,2048); if (value && !validUrl(value)) throw Error('Only valid http:// or https:// URLs are supported.'); return value; }
export const commaTags = v => [...new Set(String(v||'').split(',').map(x=>tidy(x,50)).filter(Boolean))].slice(0,20);
export function competitorFrom(v, old={}) {
  const name=tidy(v.name,120); if (!name) throw Error('Competitor name is required.');
  return { id:old.id||uid(), name, website:urlOrEmpty(v.website), category:CATEGORIES.includes(v.category)?v.category:'Other', tags:commaTags(v.tags), watch:Boolean(v.watch), notes:tidy(v.notes,4000), createdAt:old.createdAt||stamp(), updatedAt:stamp() };
}
export function adFrom(v, old={}) {
  const advertiser=tidy(v.advertiser,120), text=tidy(v.text,9000);
  if (!advertiser) throw Error('Advertiser name is required.');
  if (!text && !v.sourceUrl && !v.landingUrl) throw Error('Add ad text or a source/landing-page URL.');
  const sourceUrl=urlOrEmpty(v.sourceUrl), landingUrl=urlOrEmpty(v.landingUrl);
  return { id:old.id||uid(), competitorId:tidy(v.competitorId,100), advertiser, platform:PLATFORMS.includes(v.platform)?v.platform:'Other', sourceUrl, landingUrl, text, format:FORMATS.includes(v.format)?v.format:'Other', category:CATEGORIES.includes(v.category)?v.category:'Other', hook:tidy(v.hook,250), problem:tidy(v.problem,500), benefit:tidy(v.benefit,500), offer:tidy(v.offer,250), cta:tidy(v.cta,120), audience:tidy(v.audience,500), trust:tidy(v.trust,500), notes:tidy(v.notes,4000), tags:commaTags(v.tags), observations:Array.isArray(old.observations)?old.observations:[], createdAt:old.createdAt||stamp(), updatedAt:stamp() };
}
export function observe(ad, {status='unknown',note=''}={}) {
  if (!['active','inactive','unknown'].includes(status)) throw Error('Invalid observation status.');
  return {...ad, updatedAt:stamp(), observations:[...(ad.observations||[]),{id:uid(),at:stamp(),status,note:tidy(note,1500),verification:'User-entered observation'}]};
}
export function pageFrom(v,old={}) {
  const url=urlOrEmpty(v.url); if (!url) throw Error('Page URL is required.');
  return {id:old.id||uid(), url,title:tidy(v.title,250),headline:tidy(v.headline,300),description:tidy(v.description,1200),offer:tidy(v.offer,300),cta:tidy(v.cta,120),price:tidy(v.price,100),category:CATEGORIES.includes(v.category)?v.category:'Other',notes:tidy(v.notes,4000),createdAt:old.createdAt||stamp(),updatedAt:stamp(),provenance:'User-initiated page capture or manual entry'};
}
export function normalizeWebsite(str) {
  const s=tidy(str,2048); if (!s) return ''; return urlOrEmpty(/^https?:\/\//i.test(s)?s:`https://${s}`);
}
export function safeFilename(s) {return String(s).toLowerCase().replace(/[^a-z0-9-]+/g,'-').slice(0,75).replace(/-$/,'')||'export';}
export function duplicateOf(candidate,items,type) {
  if (type==='competitors') return items.find(x=>x.id!==candidate.id && x.name.toLowerCase()===candidate.name.toLowerCase()) || null;
  if(type==='pages') return items.find(x=>x.id!==candidate.id && x.url.replace(/\/$/,'')===candidate.url.replace(/\/$/,'')) || null;
  if(type==='ads') return items.find(x=>x.id!==candidate.id && x.sourceUrl && candidate.sourceUrl && x.sourceUrl===candidate.sourceUrl && x.advertiser.toLowerCase()===candidate.advertiser.toLowerCase()) || null;
  return null;
}
export function searchRecords(rows,q) {const s=tidy(q).toLowerCase(); if(!s)return rows; return rows.filter(x=>JSON.stringify(x).toLowerCase().includes(s));}
export const money = (n,currency='INR') => Number.isFinite(Number(n)) ? new Intl.NumberFormat('en-IN',{style:'currency',currency:currency||'INR',maximumFractionDigits:2}).format(Number(n)) : '—';
export const integer = n => Number.isFinite(Number(n)) ? new Intl.NumberFormat('en-IN',{maximumFractionDigits:0}).format(Number(n)) : '—';
export const pct = n => Number.isFinite(n) ? `${n.toFixed(2)}%` : '—';
