/* ================= v42: creator credits — writer + artist on each issue, tappable; creator page ================= */
// name variants -> one creator (data is normalised at build time; this also covers names typed later / other spellings)
const CR_ALIAS={'james lee':'Jim Lee','erik j. larsen':'Erik Larsen','eliot r. brown':'Eliot Brown','john romita jr':'John Romita Jr.','john romita, jr.':'John Romita Jr.','allen milgrom':'Al Milgrom','james shooter':'Jim Shooter',"dennis o'neil":"Denny O'Neil",'louise jones':'Louise Simonson','todd smith':'Tod Smith'};
const crNorm=n=>{ const s=String(n||'').replace(/[[\]]/g,'').replace(/\s+/g,' ').trim(); return CR_ALIAS[s.toLowerCase()]||s; };
const crKey=n=>crNorm(n).toLowerCase();
// v54: built-in list first; the file's own metadata fills only roles the built-in list has no names for (never replaces them)
function creditsOf(c){ const r=(c.driveId&&CREDITS.d[c.driveId])||(c.fileName&&CREDITS.f[c.fileName]);
  let [w,p]=r?r.split('|').map(s=>s?s.split(',').map(i=>crNorm(CREDITS.n[+i])):[]):[[],[]]; let v=[]; const m=c.metaCredits;
  if(m){ if(!w.length&&m.writer) w=m.writer.map(crNorm); if(!p.length&&m.artist) p=m.artist.map(crNorm); if(m.cover) v=m.cover.map(crNorm); }
  return (w.length||p.length||v.length)?{writer:[...new Set(w)],artist:[...new Set(p)],cover:[...new Set(v)]}:null; }
const CR_ROLES=[['writer','Writer'],['artist','Artist'],['cover','Cover']];
const crBtn=n=>`<button type="button" class="crn" data-creator="${esc(n)}">${esc(n)}</button>`;
function creditsHTML(c){ const k=creditsOf(c); if(!k) return '';
  const row=(lab,L)=>L.length?`<div class="crrow"><span class="crl">${lab}</span><span class="crv">${L.map(crBtn).join('')}</span></div>`:'';
  return `<div class="credits">${row('Writer',k.writer)}${row('Artist',k.artist)}${row('Cover',k.cover)}</div>`; }
// every issue in the library by a creator: [{series,items:[{c,d,roles}]}], groups and issues oldest first
function creatorIssues(name){ const key=crKey(name), by=new Map();
  for(const c of comics){ const k=creditsOf(c); if(!k) continue; const roles=CR_ROLES.filter(([f])=>k[f].some(n=>crKey(n)===key)).map(r=>r[1]); if(!roles.length) continue;
    const s=c.series||'Other'; if(!by.has(s)) by.set(s,[]); by.get(s).push({c,d:dateOf(c),roles}); }
  const t=x=>x.d?ymOf(x.d):1e9;
  const groups=[...by.entries()].map(([series,items])=>({series,items:items.sort((a,b)=>t(a)-t(b)||byIssue(a.c,b.c))}));
  return groups.sort((a,b)=>t(a.items[0])-t(b.items[0])||a.series.localeCompare(b.series)); }
const CRP={on:false,name:''};
function openCreator(name){ name=crNorm(name); const mw=document.querySelector('.mwrap'); if(mw){ const x=mw.querySelector('[data-r=cancel],[data-r=done]'); if(x) x.click(); else mw.remove(); } const G=creatorIssues(name), n=G.reduce((s,g)=>s+g.items.length,0);
  const roles=[...new Set(G.flatMap(g=>g.items.flatMap(x=>x.roles)))].join(' · ');
  const yrs=G.flatMap(g=>g.items.filter(x=>x.d).map(x=>x.d.y)), span=yrs.length?(Math.min(...yrs)===Math.max(...yrs)?String(yrs[0]):`${Math.min(...yrs)}–${Math.max(...yrs)}`):'';
  const el=$('#creator'); el.setAttribute('aria-label','Creator'); CRP.sale=null; $('#crName').textContent=name; $('#crSub').textContent=[roles,`${n} issue${n===1?'':'s'}`,span].filter(Boolean).join(' · ');
  $('#crBody').innerHTML=G.map(g=>`<section class="crg"><h3>${esc(g.series)}<small>${g.items.length}</small></h3><div class="crgrid">${g.items.map(x=>`<button class="crc" data-id="${x.c.id}" aria-label="${esc(x.c.title)}${x.d?', '+esc(fmtDate(x.d)):''}">${coverBox(x.c)}<span class="tt">${esc(x.c.title)}</span><span class="td">${x.d?esc(fmtDate(x.d)):'Unknown date'}</span><span class="tr">${x.roles.join(' · ')}</span></button>`).join('')}</div></section>`).join('')||'<p class="qempty">No issues by this creator in your library.</p>';
  $('#crBody').scrollTop=0; el.classList.remove('hidden'); CRP.on=true; CRP.name=name; }
function closeCreator(){ $('#creator').classList.add('hidden'); CRP.on=false; CRP.sale=null; }
$('#crClose').addEventListener('click',()=>{ if(performance.now()-(CRP.t0||0)>=450) closeCreator(); });
$('#crBody').addEventListener('click',e=>{ const b=e.target.closest('.crc'); if(!b) return; if(performance.now()-(CRP.t0||0)<450) return; /* the tap that opened the page (from the reader canvas) must not land on a cover */ const sale=CRP.sale, name=CRP.name; closeCreator(); if(typeof AB!=='undefined'&&AB.on) closeAbout(); PAGE_RET=sale?()=>openSale(sale):name?()=>openCreator(name):null; openReader(b.dataset.id); });
document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&CRP.on&&!document.querySelector('.mwrap')) closeCreator(); });
// any tappable name anywhere (info sheet, reader info) opens the creator page
document.addEventListener('click',e=>{ const b=e.target.closest('.crn[data-creator]'); if(!b) return; e.preventDefault(); e.stopPropagation(); openCreator(b.dataset.creator); },true);
// reader: Issue Info (More menu)
function readerInfo(){ const c=R.comic; if(!c) return; const d=dateOf(c);
  modal(`<div class="mh"><h3>Issue Info</h3></div><div class="mb"><div class="rinfo"><img src="${cover(c)}" alt=""><div><b>${esc(c.title)}</b><span>${c.series?esc(c.series)+' · ':''}${d?esc(fmtDate(d)):'Unknown date'}</span></div></div>${creditsHTML(c)||'<p class="fhint">No creator credits for this issue.</p>'}</div><div class="mf"><button class="btn" data-r="about" id="riAbout">About this issue</button><button class="btn" data-r="done" id="riDone">Done</button></div>`,null,'rinfom').then(o=>{ if(o&&o.r==='about') openAbout(c.id); }); }

/* ================= v54: Creators list (Library › Creators button) + series creators + edge-swipe back ================= */
function allCreators(){ const by=new Map();
  for(const c of comics){ const k=creditsOf(c); if(!k) continue; const seen=new Set();
    for(const [f,lab] of CR_ROLES) for(const n of k[f]){ const key=crKey(n); let e=by.get(key); if(!e) by.set(key,e={name:n,ids:new Set(),roles:new Set()}); e.ids.add(c.id); e.roles.add(lab); } }
  return [...by.values()].map(e=>({name:e.name,n:e.ids.size,roles:CR_ROLES.map(r=>r[1]).filter(r=>e.roles.has(r))})); }
const CRL={on:false,sort:'name',q:''};
const lastKey=n=>{ const p=n.replace(/\b(Jr\.?|Sr\.?|III|II)$/,'').trim().split(' '); return (p[p.length-1]+' '+n).toLowerCase(); };
function renderCreators(){ let L=allCreators(); const q=CRL.q.trim().toLowerCase(); if(q) L=L.filter(e=>e.name.toLowerCase().includes(q));
  L.sort(CRL.sort==='count'?(a,b)=>b.n-a.n||a.name.localeCompare(b.name):(a,b)=>lastKey(a.name).localeCompare(lastKey(b.name)));
  const withC=comics.filter(c=>creditsOf(c)).length;
  $('#crlSub').textContent=`${allCreators().length} creators · ${withC} of ${comics.length} issues credited`;
  $('#crlSort').querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.s===CRL.sort));
  $('#crlList').innerHTML=L.map(e=>`<button class="crlr" data-creator-row="${esc(e.name)}"><span class="crln">${esc(e.name)}<small>${e.roles.join(' · ')}</small></span><span class="crlc">${e.n}</span><svg class="i" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg></button>`).join('')||`<p class="qempty">${comics.length?'No creators match.':'No comics yet.'}</p>`; }
function openCreators(){ CRL.q=''; $('#crlQ').value=''; renderCreators(); $('#crlList').scrollTop=0; $('#creators').classList.remove('hidden'); CRL.on=true; }
function closeCreators(){ $('#creators').classList.add('hidden'); CRL.on=false; }
$('#crlBtn').addEventListener('click',openCreators);
$('#crlClose').addEventListener('click',closeCreators);
$('#crlQ').addEventListener('input',e=>{ CRL.q=e.target.value; renderCreators(); });
$('#crlSort').addEventListener('click',e=>{ const b=e.target.closest('button[data-s]'); if(!b) return; CRL.sort=b.dataset.s; renderCreators(); });
$('#crlList').addEventListener('click',e=>{ const b=e.target.closest('[data-creator-row]'); if(!b) return; openCreator(b.dataset.creatorRow); });
document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&CRL.on&&!CRP.on&&!document.querySelector('.mwrap')) closeCreators(); });
// series page: the series' writers and artists, tappable, under the carousel
function seriesCreatorsHTML(L){ const tally=f=>{ const m=new Map(); for(const c of L){ const k=creditsOf(c); if(k) for(const n of k[f]) m.set(n,(m.get(n)||0)+1); } return [...m.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,8).map(x=>x[0]); };
  const row=(lab,N)=>N.length?`<div class="crrow"><span class="crl">${lab}</span><span class="crv">${N.map(crBtn).join('')}</span></div>`:'';
  const h=row('Writers',tally('writer'))+row('Artists',tally('artist'))+row('Covers',tally('cover')); return h?`<div class="credits scred">${h}</div>`:''; }
// left-edge swipe back on the creator page and the Creators list
function edgeBack(el,back){ let d=null;
  el.addEventListener('touchstart',e=>{ const t=e.touches[0]; d=(e.touches.length===1&&t.clientX<=24)?{x:t.clientX,y:t.clientY,ok:false}:null; },{passive:true});
  el.addEventListener('touchmove',e=>{ if(!d) return; const t=e.touches[0], dx=t.clientX-d.x, dy=Math.abs(t.clientY-d.y); if(dy>60&&dy>dx) { d=null; el.style.transform=''; return; } if(dx>0){ el.style.transform=`translateX(${dx}px)`; d.dx=dx; } },{passive:true});
  el.addEventListener('touchend',()=>{ if(!d) return; const go=(d.dx||0)>80; d=null; if(go){ el.style.transition='transform .18s ease-out'; el.style.transform='translateX(100%)'; setTimeout(()=>{ el.style.transition=''; el.style.transform=''; back(); },180); } else { el.style.transition='transform .15s'; el.style.transform=''; setTimeout(()=>el.style.transition='',160); } });
  el.addEventListener('touchcancel',()=>{ d=null; el.style.transform=''; }); }
edgeBack($('#creator'),closeCreator); edgeBack($('#creators'),closeCreators);
