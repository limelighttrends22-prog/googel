import {CATEGORIES,pageFrom,adFrom,duplicateOf,uid} from './src/model.js';
import {all,put} from './src/db.js';
const $=id=>document.getElementById(id);let current=null;
function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);}
function openDashboard(view='overview'){chrome.tabs.create({url:chrome.runtime.getURL('dashboard.html#'+view)});}
async function capture(){
 const [tab]=await chrome.tabs.query({active:true,currentWindow:true});if(!tab?.url||!/^https?:\/\//.test(tab.url))throw Error('Open a public http(s) page to capture it.');
 const data={url:tab.url,title:tab.title||'',headline:'',description:'',offer:'',cta:'',price:''};
 try{
  const res=await chrome.scripting.executeScript({target:{tabId:tab.id},func:()=>{
   const meta=document.querySelector('meta[name="description"]');const h=document.querySelector('h1');
   return {title:document.title||'',headline:h?.innerText?.trim().slice(0,300)||'',description:meta?.content?.trim().slice(0,1200)||''};
  }});
  Object.assign(data,res?.[0]?.result||{});
 }catch { /* Browser-restricted pages and injection failures fall back to tab title + URL. */ }
 return data;
}
async function refresh(){try{current=await capture();$('pageTitle').textContent=current.title||'(No page title)';$('pageUrl').textContent=current.url;}catch(e){current=null;$('pageTitle').textContent='Page capture unavailable';$('pageUrl').textContent=e.message;$('savePage').disabled=true;$('saveAd').disabled=true;}const ads=await all('ads');$('count').textContent=`${ads.length} saved ad${ads.length===1?'':'s'}`;}
async function save(mode){if(!current)return;const btn=$(mode==='ad'?'saveAd':'savePage');btn.disabled=true;try{
 const notes=$('notes').value,category=$('category').value;
 if(mode==='page'){
  const item=pageFrom({...current,category,notes});const others=await all('pages');if(duplicateOf(item,others,'pages'))throw Error('This URL is already saved. Edit it in Data Center.');await put('pages',item);notice('Page saved locally. Open the dashboard to review it.');
 }else{
  const advertiser=new URL(current.url).hostname.replace(/^www\./,'');const item=adFrom({advertiser,category,sourceUrl:current.url,landingUrl:current.url,text:current.headline||current.title,notes,platform:'Other',format:'Other'});
  const others=await all('ads');if(duplicateOf(item,others,'ads'))throw Error('This advertiser/source combination is already saved.');await put('ads',item);notice('Ad reference saved locally; ad activity is not verified.');
 }await refresh();
 }catch(e){notice(e.message,true);}finally{btn.disabled=false;}}
for(const cat of CATEGORIES){const o=document.createElement('option');o.value=cat;o.textContent=cat;$('category').append(o);}$('category').value='Skincare';
$('openDashboard').addEventListener('click',()=>openDashboard());$('openLibrary').addEventListener('click',e=>{e.preventDefault();openDashboard('ads');});$('savePage').addEventListener('click',()=>save('page'));$('saveAd').addEventListener('click',()=>save('ad'));refresh().catch(e=>notice(e.message,true));
