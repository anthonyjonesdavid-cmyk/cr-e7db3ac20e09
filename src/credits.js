/* ================= v42: creator credits — writer + artist on each issue, tappable; creator page ================= */
// name variants -> one creator (data is normalised at build time; this also covers names typed later / other spellings)
const CR_ALIAS={'james lee':'Jim Lee','erik j. larsen':'Erik Larsen','eliot r. brown':'Eliot Brown','john romita jr':'John Romita Jr.','john romita, jr.':'John Romita Jr.','allen milgrom':'Al Milgrom','james shooter':'Jim Shooter',"dennis o'neil":"Denny O'Neil",'louise jones':'Louise Simonson','todd smith':'Tod Smith'};
const crNorm=n=>{ const s=String(n||'').replace(/[[\]]/g,'').replace(/\s+/g,' ').trim(); return CR_ALIAS[s.toLowerCase()]||s; };
const crKey=n=>crNorm(n).toLowerCase();
function creditsOf(c){ const r=(c.driveId&&CREDITS.d[c.driveId])||(c.fileName&&CREDITS.f[c.fileName]); if(!r) return null;
  const [w,p]=r.split('|').map(s=>s?s.split(',').map(i=>crNorm(CREDITS.n[+i])):[]); return (w.length||p.length)?{writer:[...new Set(w)],artist:[...new Set(p)]}:null; }
const crBtn=n=>`<button type="button" class="crn" data-creator="${esc(n)}">${esc(n)}</button>`;
function creditsHTML(c){ const k=creditsOf(c); if(!k) return '';
  const row=(lab,L)=>L.length?`<div class="crrow"><span class="crl">${lab}</span><span class="crv">${L.map(crBtn).join('')}</span></div>`:'';
  return `<div class="credits">${row('Writer',k.writer)}${row('Artist',k.artist)}</div>`; }
// every issue in the library by a creator: [{series,items:[{c,d,roles}]}], groups and issues oldest first
function creatorIssues(name){ const key=crKey(name), by=new Map();
  for(const c of comics){ const k=creditsOf(c); if(!k) continue; const roles=[]; if(k.writer.some(n=>crKey(n)===key)) roles.push('Writer'); if(k.artist.some(n=>crKey(n)===key)) roles.push('Artist'); if(!roles.length) continue;
    const s=c.series||'Other'; if(!by.has(s)) by.set(s,[]); by.get(s).push({c,d:dateOf(c),roles}); }
  const t=x=>x.d?ymOf(x.d):1e9;
  const groups=[...by.entries()].map(([series,items])=>({series,items:items.sort((a,b)=>t(a)-t(b)||byIssue(a.c,b.c))}));
  return groups.sort((a,b)=>t(a.items[0])-t(b.items[0])||a.series.localeCompare(b.series)); }
const CRP={on:false,name:''};
function openCreator(name){ name=crNorm(name); const mw=document.querySelector('.mwrap'); if(mw){ const x=mw.querySelector('[data-r=cancel],[data-r=done]'); if(x) x.click(); else mw.remove(); } const G=creatorIssues(name), n=G.reduce((s,g)=>s+g.items.length,0);
  const roles=[...new Set(G.flatMap(g=>g.items.flatMap(x=>x.roles)))].join(' · ');
  const yrs=G.flatMap(g=>g.items.filter(x=>x.d).map(x=>x.d.y)), span=yrs.length?(Math.min(...yrs)===Math.max(...yrs)?String(yrs[0]):`${Math.min(...yrs)}–${Math.max(...yrs)}`):'';
  const el=$('#creator'); el.setAttribute('aria-label','Creator'); CRP.sale=null; $('#crName').textContent=name; $('#crSub').textContent=[roles,`${n} issue${n===1?'':'s'}`,span].filter(Boolean).join(' · ');
  $('#crBody').innerHTML=G.map(g=>`<section class="crg"><h3>${esc(g.series)}<small>${g.items.length}</small></h3><div class="crgrid">${g.items.map(x=>`<button class="crc" data-id="${x.c.id}" aria-label="${esc(x.c.title)}${x.d?', '+esc(fmtDate(x.d)):''}">${coverBox(x.c)}<span class="tt">${esc(x.c.title)}</span><span class="td">${x.d?esc(fmtDate(x.d)):'Unknown date'}${x.roles.length===1&&roles.includes('·')?' · '+x.roles[0]:''}</span></button>`).join('')}</div></section>`).join('')||'<p class="qempty">No issues by this creator in your library.</p>';
  $('#crBody').scrollTop=0; el.classList.remove('hidden'); CRP.on=true; CRP.name=name; }
function closeCreator(){ $('#creator').classList.add('hidden'); CRP.on=false; CRP.sale=null; }
$('#crClose').addEventListener('click',()=>{ if(performance.now()-(CRP.t0||0)>=450) closeCreator(); });
$('#crBody').addEventListener('click',e=>{ const b=e.target.closest('.crc'); if(!b) return; if(performance.now()-(CRP.t0||0)<450) return; /* the tap that opened the page (from the reader canvas) must not land on a cover */ const sale=CRP.sale, name=CRP.name; closeCreator(); PAGE_RET=sale?()=>openSale(sale):name?()=>openCreator(name):null; openReader(b.dataset.id); });
document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&CRP.on&&!document.querySelector('.mwrap')) closeCreator(); });
// any tappable name anywhere (info sheet, reader info) opens the creator page
document.addEventListener('click',e=>{ const b=e.target.closest('.crn[data-creator]'); if(!b) return; e.preventDefault(); e.stopPropagation(); openCreator(b.dataset.creator); },true);
// reader: Issue Info (More menu)
function readerInfo(){ const c=R.comic; if(!c) return; const d=dateOf(c);
  modal(`<div class="mh"><h3>Issue Info</h3></div><div class="mb"><div class="rinfo"><img src="${cover(c)}" alt=""><div><b>${esc(c.title)}</b><span>${c.series?esc(c.series)+' · ':''}${d?esc(fmtDate(d)):'Unknown date'}</span></div></div>${creditsHTML(c)||'<p class="fhint">No creator credits for this issue.</p>'}</div><div class="mf"><button class="btn" data-r="done" id="riDone">Done</button></div>`,null,'rinfom'); }
