/* ================= boot ================= */
window.__cr={wake:Wake,bin:{BIN,open:openBin,close:closeBin,to:binTo,dig:binDig},night:{NIGHT,set:setNight,on:nightOn,start:startAuto},rain:Rain,srcRes:pageSourceRes,black:{scan:scanBlack,stats:pageBlackStats,blackStats,async statsOfUrl(u){ const b=await (await fetch(u)).blob(); const doc=await openPdf(new FileSource(b)); const out=[]; try{ for(let i=0;i<doc.numPages;i++){ const pg=await doc.getPage(i+1); out.push(await pageBlackStats(pg)); pg.cleanup(); } } finally{ await doc.destroy(); } return out; }},drive:Drive,issueNo,isRangeName,rack:{RK,open:openRack,close:closeRack,items:rackItems,center:rackCenter},online:{onlineDate,volHints,lookupAll,eligible:lkEligible,lookupDate},vols:{lift:liftAccent,bodyOf,titleInk,sample:spineSample,ink:spineInk,inks:spineInks,style:spineStyle,name:spineName,FONTS:SPINE_FONTS,contrast,hexRGB,width:spineW,info:volInfo,dominant:dominantColor},qs:{create:newQueue,seeAll},sale:{of:onSale,key:saleKey,open:openSale},credits:{sheet:actionSheet,hero:heroList,heroStart,of:creditsOf,issues:creatorIssues,open:openCreator,close:closeCreator,norm:crNorm,CRP,data:CREDITS,all:allCreators,openList:openCreators,closeList:closeCreators,meta:pdfCredits,about:{open:openAbout,close:closeAbout,of:notesOf,lookup:lookupNotes,AB,data:()=>NOTES}},dates:{of:dateOf,embed:EMBED_DATES,emb:embDate,weekDate,render:()=>renderShelf(),fromName:dateFromName,lookup:lookupDate,pdfDate,comicInfo:comicInfoDate,TL,open:openTimeline,close:closeTimeline,set:setDate,ov:()=>dateOv,backfill:backfillDates},series:{move:applySeries,rename:renameSeries,merge:mergeSeries,counts:seriesCounts,override:withSeriesOverride,ov:seriesOv,SEL},rows:{keys:rowKeys,prefs:rowPrefs,arrange:arrangeRows},cov:{makeCover,openPdf,IDBSource},R,Z,get flip(){return flip},get animating(){return animating},cache:()=>({n:cache.size,px:cachePx,budget:CACHE_BUDGET}),panels:{P,detect:detectPanels,thirds:panelThirds,enter:enterPanels,exit:exitPanels,step:stepPanel,units:unitsOfView,list:panelList,async detectUrl(u,rtl=false){ const b=await (await fetch(u)).blob(); const doc=await openPdf(new FileSource(b)); const out=[]; try{ for(let i=0;i<doc.numPages;i++){ const pg=await doc.getPage(i+1), vp=pg.getViewport({scale:1}), wide=vp.width>vp.height*1.15; const cv=await renderToCanvas(pg,wide?760:380,560,1,wide?420000:220000); pg.cleanup(); out.push(wide?{L:panelsOfCanvas(cv,'L',rtl),R:panelsOfCanvas(cv,'R',rtl)}:panelsOfCanvas(cv,'',rtl)); freeCanvas(cv); } } finally{ await doc.destroy(); } return out; }},CF,SCF,go,jumpTo,toggleUI,scheduleHi,get comics(){return comics},get queues(){return queues},kickBlack};
// v57 (thumbs stored as ArrayBuffers, not Blobs: Blobs in IndexedDB are unreliable in WebKit)
// v57: snapshot ~30 small random cover thumbnails (JPEG Blobs in IndexedDB 'cr-splash') for the next launch's panorama.
// Saved ~1 s after Home is up, and again when the app is hidden/closed (iOS often suspends a Home Screen app well before 5 s).
let splashBusy=false, splashSaved=0;
function splashDB(){ return new Promise((res,rej)=>{ const r=indexedDB.open('cr-splash',1); r.onupgradeneeded=()=>{ r.result.createObjectStore('k'); }; r.onsuccess=()=>res(r.result); r.onerror=()=>rej(r.error); }); }
const toJpeg=cv=>new Promise(r=>{ try{ cv.toBlob(b=>r(b),'image/jpeg',.6); }catch(e){ r(null); } });
function decode(blob){ if(window.createImageBitmap) return createImageBitmap(blob).catch(()=>imgOf(blob)); return imgOf(blob); }
function imgOf(blob){ return new Promise((res,rej)=>{ const u=URL.createObjectURL(blob), im=new Image(); im.onload=()=>{ res(im); setTimeout(()=>URL.revokeObjectURL(u),0); }; im.onerror=()=>{ URL.revokeObjectURL(u); rej(new Error('img')); }; im.src=u; }); }
async function saveSplash(){ if(splashBusy||Date.now()-splashSaved<60000) return; splashBusy=true;
  try{ const pool=comics.filter(c=>c.cover); if(!pool.length) return;
  for(let i=pool.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [pool[i],pool[j]]=[pool[j],pool[i]]; }
  const out=[], cv=document.createElement('canvas'); cv.width=120; cv.height=182; const g=cv.getContext('2d');
  for(const c of pool.slice(0,30)){ try{ const bm=await decode(c.cover instanceof Blob?c.cover:new Blob([c.cover],{type:'image/jpeg'})); const w=bm.width, h=bm.height;
      const s=Math.max(120/w,182/h); g.fillStyle='#000'; g.fillRect(0,0,120,182); g.drawImage(bm,(120-w*s)/2,(182-h*s)/2,w*s,h*s); bm.close&&bm.close();
      const jb=await toJpeg(cv); if(jb) out.push(await jb.arrayBuffer()); }catch(e){ console.warn('splash thumb',e); } }
  if(!out.length) return;
  const d=await splashDB(); await new Promise((res,rej)=>{ const t=d.transaction('k','readwrite'); t.objectStore('k').put(out,'thumbs'); t.oncomplete=res; t.onerror=t.onabort=()=>rej(t.error); }); d.close();
  splashSaved=Date.now(); try{ localStorage.removeItem('cr-splash-v1'); }catch(e){} }
  catch(e){ console.warn('splash save',e); } finally{ splashBusy=false; } }
addEventListener('visibilitychange',()=>{ if(document.visibilityState==='hidden'&&!splashSaved) saveSplash(); });
addEventListener('pagehide',()=>{ if(!splashSaved) saveSplash(); });
window.__crSaveSplash=saveSplash;
(async()=>{ try{ await loadLibrary(); }catch(e){ window.__crSplashHide&&window.__crSplashHide(true); console.warn(e); $('#homeScroll').innerHTML='<div class="empty"><h2>Storage unavailable</h2><p>On-device storage is unavailable in this browser mode (e.g. Private Browsing).</p></div>'; return; }
  try{ if(comics.length&&navigator.storage&&navigator.storage.persisted&&!(await navigator.storage.persisted())) navigator.storage.persist().catch(()=>{}); }catch(e){}
  try{
  const m=location.hash.match(/^#\/read\/(.+)$/);
  if(m&&comics.find(c=>c.id===m[1])){ try{ history.replaceState(null,'',location.pathname+location.search); history.pushState({r:m[1]},'','#/read/'+m[1]); }catch(e){} openReader(m[1],{push:false}); }
  else if(location.hash){ try{ history.replaceState(null,'',location.pathname+location.search); }catch(e){} }   // stale / unknown hash: plain Home
  launchHome();
  }catch(e){ console.error(e); try{ launchHome(); }catch(e2){ (window.__crFail||console.error)(e2); return; } }
  document.documentElement.dataset.ready='1';
  if(window.__crSplashHide) requestAnimationFrame(()=>window.__crSplashHide());
  setTimeout(saveSplash,1000);
})().catch(e=>(window.__crFail||console.error)(e));
