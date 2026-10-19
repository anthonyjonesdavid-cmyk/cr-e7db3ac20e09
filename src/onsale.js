/* ================= v45: "Also on sale this month" — bottom of the end-of-issue / up-next page: other comics in your library with the same cover month (Timeline dates) =================
   Exact month: dates set by you, looked up, built-in list, metadata or file name. An ≈ estimate is labelled "around <Mon Year>";
   a year-only date matches the whole year ("around 1987"). No usable date or no other issue: no section. "+N more" opens the full grid page (#creator). */
function saleKey(c){ const d=dateOf(c); if(!d||!d.y) return null; const est=d.src==='lookup';
  if(!d.m) return {mode:'year',y:d.y,label:`around ${d.y}`,est:true};
  return {mode:'month',y:d.y,m:d.m,ym:ymOf(d),label:`${est?'around ':''}${MONTHS[d.m-1].slice(0,3)} ${d.y}`,est}; }
function onSale(c){ const k=saleKey(c); if(!k) return null; const others=comics.filter(x=>x.id!==c.id).map(x=>({c:x,d:dateOf(x)})).filter(x=>x.d&&x.d.y);
  const hit=k.mode==='year'? x=>x.d.y===k.y : x=>x.d.y===k.y&&x.d.m===k.m;
  let L=others.filter(hit), near=null;
  if(!L.length&&others.length){
    if(k.mode==='year'){ const ys=[...new Set(others.map(x=>x.d.y))].sort((a,b)=>Math.abs(a-k.y)-Math.abs(b-k.y)||a-b); near={y:ys[0],label:String(ys[0])}; L=others.filter(x=>x.d.y===near.y); }
    else { const md=others.filter(x=>x.d.m); if(md.length){ const ym=md.map(x=>ymOf(x.d)).sort((a,b)=>Math.abs(a-k.ym)-Math.abs(b-k.ym)||a-b)[0]; near={ym,label:ymLabel(ym)}; L=md.filter(x=>ymOf(x.d)===ym); } } }
  L.sort((a,b)=>(a.c.series||'').localeCompare(b.c.series||'')||byIssue(a.c,b.c)); return {k,L,near,exact:near?0:L.length}; }
var PAGE_RET=null;   // reopen this page when you come back from an issue opened on it
function openSale(id){ const c=comics.find(x=>x.id===id); if(!c) return; const s=onSale(c); if(!s) return;
  const mw=document.querySelector('.mwrap'); if(mw){ const x=mw.querySelector('[data-r=cancel],[data-r=done]'); if(x) x.click(); else mw.remove(); }
  $('#creator').setAttribute('aria-label','Also on sale'); $('#crName').textContent=`Also on sale · ${s.k.label}`;
  $('#crSub').textContent=`${s.exact} other issue${s.exact===1?'':'s'} in your library${s.k.est?' · dates are approximate':''}`;
  const note=s.near?`<p class="salenote" id="saleNote">Nothing else in your library from ${esc(s.k.label.replace(/^around /,''))}. Showing ${esc(s.near.label)}, the nearest ${s.k.mode==='year'?'year':'month'} with comics.</p>`:'';
  $('#crBody').innerHTML=note+(s.L.length?`<div class="crgrid salegrid">${s.L.map(x=>`<button class="crc" data-id="${x.c.id}" data-ret="sale:${c.id}" aria-label="${esc(x.c.title)}, ${esc(fmtDate(x.d))}">${coverBox(x.c)}<span class="tt">${esc(x.c.title)}</span><span class="td">${esc(fmtDate(x.d))}</span></button>`).join('')}</div>`:'<p class="qempty">No other dated comics in your library yet.</p>');
  $('#crBody').scrollTop=0; $('#creator').classList.remove('hidden'); CRP.on=true; CRP.name=''; CRP.sale=id; CRP.t0=performance.now(); }
