/* ================= boot ================= */
window.__cr={black:{scan:scanBlack,stats:pageBlackStats,blackStats,async statsOfUrl(u){ const b=await (await fetch(u)).blob(); const doc=await openPdf(new FileSource(b)); const out=[]; try{ for(let i=0;i<doc.numPages;i++){ const pg=await doc.getPage(i+1); out.push(await pageBlackStats(pg)); pg.cleanup(); } } finally{ await doc.destroy(); } return out; }},drive:Drive,issueNo,isRangeName,series:{rename:renameSeries,merge:mergeSeries,counts:seriesCounts},rows:{keys:rowKeys,prefs:rowPrefs,arrange:arrangeRows},cov:{makeCover,openPdf,IDBSource},R,Z,get flip(){return flip},get animating(){return animating},cache:()=>({n:cache.size,px:cachePx,budget:CACHE_BUDGET}),CF,SCF,go,jumpTo,toggleUI,get comics(){return comics},kickBlack};
(async()=>{ try{ await loadLibrary(); }catch(e){ console.warn(e); $('#homeScroll').innerHTML='<div class="empty"><h2>Storage unavailable</h2><p>On-device storage is unavailable in this browser mode (e.g. Private Browsing).</p></div>'; return; }
  try{ if(comics.length&&navigator.storage&&navigator.storage.persisted&&!(await navigator.storage.persisted())) navigator.storage.persist().catch(()=>{}); }catch(e){}
  const m=location.hash.match(/^#\/read\/(.+)$/);
  if(m&&comics.find(c=>c.id===m[1])){ try{ history.replaceState(null,'',location.pathname+location.search); history.pushState({r:m[1]},'','#/read/'+m[1]); }catch(e){} openReader(m[1],{push:false}); }
  else if(m){ try{ history.replaceState(null,'',location.pathname+location.search); }catch(e){} }
  document.documentElement.dataset.ready='1';
})();
