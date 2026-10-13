
/* ================= Shelf: Home (coverflow + rows) and Library (grid) ================= */
let comics=[]; const coverURL=new Map();
// every launch starts on Home: the last tab is NOT restored (it used to be saved in localStorage 'cr.tab', which made reopening the app land on Library)
try{ localStorage.removeItem('cr.tab'); }catch(e){}
const ui={tab:'home', sort:store.get('sort','recent'), filter:'all', series:null, q:''};
const IC={
  chev:'<svg class="i" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>',
  check:'<svg class="i" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  play:'<svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z"/></svg>',
  x:'<svg class="i" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>',
  book:'<svg class="i" viewBox="0 0 24 24"><path d="M2 5.5C4.5 4 8 4 12 6c4-2 7.5-2 10-.5V19c-2.5-1.5-6-1.5-10 .5-4-2-7.5-2-10-.5z"/><path d="M12 6v13.5"/></svg>',
  edit:'<svg class="i" viewBox="0 0 24 24"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  done:'<svg class="i" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m8 12.5 3 3 5-6"/></svg>',
  undo:'<svg class="i" viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg>',
  trash:'<svg class="i" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg>',
  more:'<svg class="i" viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.6" fill="currentColor"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/><circle cx="19" cy="12" r="1.6" fill="currentColor"/></svg>',
  grip:'<svg class="i" viewBox="0 0 24 24"><path d="M4 8h16M4 12h16M4 16h16"/></svg>',
  up:'<svg class="i" viewBox="0 0 24 24"><path d="m6 15 6-6 6 6"/></svg>',
  down:'<svg class="i" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>',
  arrange:'<svg class="i" viewBox="0 0 24 24"><path d="M4 6h11M4 12h11M4 18h11M19 4v16M16.5 6.5 19 4l2.5 2.5M16.5 17.5 19 20l2.5-2.5"/></svg>',
  merge:'<svg class="i" viewBox="0 0 24 24"><path d="M6 3v6a6 6 0 0 0 6 6h0a6 6 0 0 1 6 6M18 3v6a6 6 0 0 1-6 6"/></svg>',
  list:'<svg class="i" viewBox="0 0 24 24"><path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6h.01M4 12h.01M4 18h.01" stroke-width="3"/></svg>',
  clock:'<svg class="i" viewBox="0 0 24 24"><path d="M4 12h16"/><path d="M7 9v6M12 7v10M17 9v6"/></svg>',
  cal:'<svg class="i" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
  rack:'<svg class="i" viewBox="0 0 24 24"><path d="M12 2v20M7 22h10"/><rect x="5" y="4" width="14" height="5" rx="1"/><rect x="5" y="11" width="14" height="5" rx="1"/></svg>',
  grid:'<svg class="i" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 10h18M12 10v11"/></svg>',
};
function cover(c){ if(!c.cover) return ''; let u=coverURL.get(c.id); if(!u){ u=URL.createObjectURL(c.cover instanceof Blob?c.cover:new Blob([c.cover],{type:'image/jpeg'})); coverURL.set(c.id,u); } return u; }
const pctOf=c=>c.pages?Math.round(clamp(c.progress||0,0,1)*100):0;
const isDone=c=>(c.progress||0)>=1, isUnread=c=>!c.lastRead&&!((c.progress||0)>0), inProg=c=>!isDone(c)&&!isUnread(c);
const byTitle=(a,b)=>a.title.localeCompare(b.title,undefined,{numeric:true,sensitivity:'base'});
// issue number from a title: '#12' wins; else the last number once (…)/[…] tags (years, scanner names) are dropped. X-MEN177 -> 177
function issueNo(t){ const s=String(t||''); let m=s.match(/#\s*(\d+(?:\.\d+)?)/); if(m) return parseFloat(m[1]);
  m=s.replace(/[([].*?[)\]]/g,' ').match(/(\d+(?:\.\d+)?)(?!.*\d)/); return m?parseFloat(m[1]):Infinity; }
const byIssue=(a,b)=>{ const x=issueNo(a.title), y=issueNo(b.title); return x!==y? (x===Infinity?1:y===Infinity?-1:x-y) : byTitle(a,b); };
function seriesGuess(t){ const s=t.replace(/[([].*?[)\]]/g,' ').replace(/\s+/g,' ').trim();
  const m=s.match(/^(.*?)[\s,_-]*(?:#|no\.?\s*|issue\s*|vol(?:ume)?\.?\s*|v|ch(?:apter)?\.?\s*|book\s*)?(\d{1,4})(?:\s*of\s*\d+)?$/i);
  return m&&m[1].trim().length>=2&&/[a-z]/i.test(m[1])? m[1].replace(/[\s,_#-]+$/,'').trim() : ''; }
/* ---- manual series: a series set by hand (Move to Series, Rename/Merge, Edit) is remembered per file (Drive id, or file name + size),
   so deleting and re-importing / re-syncing from Drive keeps it instead of re-grouping by folder or file name.
   c.autoSeries = what automatic grouping gave at import; Remove from Series goes back to it. ---- */
const fileKeys=c=>[c.driveId?'d:'+c.driveId:null,c.fileName?'f:'+c.fileName+'|'+(c.size||0):null].filter(Boolean);
const seriesOv=()=>store.get('seriesOv',{})||{};
const autoSeriesOf=c=>c.autoSeries!=null?c.autoSeries:seriesGuess(titleFromName(c.fileName||c.title));
function setSeriesManual(c,to){ c.series=to; c.seriesManual=true; const ov=seriesOv(); fileKeys(c).forEach(k=>ov[k]=to); store.set('seriesOv',ov); }
function clearSeriesManual(c){ c.series=autoSeriesOf(c); delete c.seriesManual; const ov=seriesOv(); fileKeys(c).forEach(k=>delete ov[k]); store.set('seriesOv',ov); }
// new record (Files or Drive import): remember the automatic series, then apply a saved manual series for this file
function withSeriesOverride(rec){ applyDateOv(rec); rec.autoSeries=rec.series||''; const ov=seriesOv(), k=fileKeys(rec).find(k=>k in ov); if(k!=null){ rec.series=ov[k]; rec.seriesManual=true; } return rec; }
async function loadLibrary(){ comics=await dbAll(); try{ dateOv=new Map((await ovAll()).filter(o=>o.date).map(o=>[o.k,o.date])); }catch(e){ dateOv=new Map(); } comics.forEach(applyDateOv); try{ queues=await qAll(); }catch(e){ console.warn('reading lists unavailable',e); queues=[]; } renderShelf(); setTimeout(migrateCovers,400); kickBlack(5000); setTimeout(backfillDates,2500); }
/* ---- background blank-black page detection, cached per comic (c.blackPages, c.blackV) ----
   newest-read first, one comic at a time, idle-paced; while a comic is open only that comic is scanned */
const needsBlack=c=>c.blackV!==BLACK_V;
const skipVal=c=>(c.skipBlack??store.get('skipBlack',true))?'on':'off';
const blankList=c=>[...(c.blackPages||[]),...(c.whitePages||[])].filter(p=>p>0&&p<c.pages).sort((a,b)=>a-b);
const skipList=c=>skipVal(c)==='on'?blankList(c):[];
let blackBusy=false, blackT=0;
let lastInput=0; ['pointerdown','pointermove','keydown','wheel'].forEach(t=>addEventListener(t,()=>{ lastInput=performance.now(); },{capture:true,passive:true}));
const readerBusy=()=>!!R.comic&&(flip||animating||landing||running>0||jobs.size>0||performance.now()-lastInput<1500);
function kickBlack(delay=1500){ clearTimeout(blackT); blackT=setTimeout(blackLoop,delay); }
async function blackLoop(){ if(blackBusy||window.__crNoScan) return; blackBusy=true;
  try{ for(;;){ if(importing) { kickBlack(3000); break; }
      const open=R.comic, c=open?(needsBlack(open)?open:null):comics.filter(needsBlack).sort((a,b)=>(b.lastRead||0)-(a.lastRead||0)||(b.added||0)-(a.added||0))[0];
      if(!c) break; if(!await scanOne(c)) break; } }
  finally{ blackBusy=false; } }
async function scanOne(c){ let doc=null; const id=c.id;
  const alive=()=>!window.__crNoScan&&comics.some(x=>x.id===id)&&(!R.comic||R.comic.id===id);
  const pause=async()=>{ for(let k=0;k<600&&readerBusy();k++) await new Promise(r=>setTimeout(r,100));   /* never compete with a page turn or page render */
    await new Promise(r=>{ const go=()=>setTimeout(r,R.comic?40:6); if(window.requestIdleCallback) requestIdleCallback(go,{timeout:300}); else go(); }); };
  try{ doc=await openPdf(new IDBSource(c.id,c.size)); const r=await scanBlack(doc,{alive,pause,from:R.comic&&R.comic.id===id?(c.page||0):1}); if(r==null) return false;
    c.blackPages=r.black; c.whitePages=r.white; c.blackV=BLACK_V; delete c.blankPages; delete c.blankPagesV2; delete c.blankTail; await dbPut(c); dispatchEvent(new CustomEvent('cr-black',{detail:id})); return true; }
  catch(e){ console.warn('black-page scan failed',e); c.blackPages=[]; c.whitePages=[]; c.blackV=BLACK_V; return true; }
  finally{ if(doc) doc.destroy().catch(()=>{}); } }
/* regenerate a comic's cover thumbnail from its stored PDF (cover mode change, or migration) */
let coverJob=Promise.resolve();
function recover(c,mode){ return coverJob=coverJob.then(async()=>{ const doc=await openPdf(new IDBSource(c.id,c.size));
  try{ const m=await coverMeta(doc,mode||c.coverMode||'auto'); Object.assign(c,m); if(!c.coverMode||mode) c.coverMode=m.coverMode; } finally{ await doc.destroy(); }
  await dbPut(c); const u=coverURL.get(c.id); if(u){ URL.revokeObjectURL(u); coverURL.delete(c.id); } renderShelf(); }).catch(e=>{ throw e; }); }
// one-time (per COVER_V) background migration: older imports get cropped covers + crop info
async function migrateCovers(){ const todo=comics.filter(c=>(c.coverV||0)<COVER_V); if(!todo.length){ store.set('coverMig',COVER_V); return; }
  for(const c of todo){ if(!comics.includes(c)) continue; while(R&&R.comic) await new Promise(r=>setTimeout(r,1500));   // don't compete with the reader
    try{ await recover(c,c.coverMode||'auto'); }catch(e){ console.warn('cover migration failed for',c.title,e); c.coverV=COVER_V; try{ await dbPut(c); }catch(_){} } }
  store.set('coverMig',COVER_V); }
// app launch / restore from the back-forward cache: back to Home (no series page, no search), at the top
function launchHome(){ closeRack(); closeTimeline(); ui.series=null; ui.q=''; ui.filter='all'; const q=$('#q'); if(q) q.value=''; renderLibrary(); setTab('home'); const h=$('#homeScroll'); if(h) h.scrollTop=0; }
addEventListener('pageshow',e=>{ if(e.persisted&&!(R&&R.comic)) launchHome(); });
function renderShelf(){ renderHome(); renderLibrary(); setTab(ui.tab); if(TL.on) renderTimeline(); }
function setTab(t){ if(t!==ui.tab&&SEL.on) exitSel(); ui.tab=t; $('#shelf').classList.toggle('libtab',t==='library'); document.querySelectorAll('#tabs button').forEach(b=>{ b.classList.toggle('on',b.dataset.tab===t); b.setAttribute('aria-selected',b.dataset.tab===t); });
  $('#home').classList.toggle('hidden',t!=='home'); $('#library').classList.toggle('hidden',t!=='library'); const wasTL=TL.on; TL.on=t==='timeline'; $('#timeline').classList.toggle('hidden',!TL.on); if(TL.on&&!wasTL) renderTimeline(); scopeUI(); if(t==='home') CF.size(); else if(t==='library') SCF.size(); }
// series page = Library scoped to one series: just carousel + grid, a back chevron replaces the gear
function scopeUI(){ $('#shelf').classList.toggle('scoped',ui.tab==='library'&&ui.series!=null); }
function unscope(){ ui.series=null; renderLibrary(); $('#libScroll').scrollTop=0; }
$('#libBack').addEventListener('click',unscope);
$('#tabs').addEventListener('click',e=>{ const b=e.target.closest('button'); if(!b) return; if(b.dataset.tab==='library'&&ui.series!=null){ ui.series=null; renderLibrary(); } setTab(b.dataset.tab); });

const coverBox=c=>`<div class="cvr"><img src="${cover(c)}" alt="" decoding="async" loading="lazy" draggable="false">${isDone(c)?`<span class="done" aria-label="Finished">${IC.check}</span>`:''}</div>${inProg(c)?`<div class="pl"><i style="width:${Math.max(2,pctOf(c))}%"></i></div>`:'<div class="pl none"></div>'}`;
const emptyHTML=()=>`<div class="empty">${IC.book}<h2>No comics yet</h2><p>Import PDF comics from Google Drive or the Files app. They're stored on this device only and never uploaded.</p><div class="ebtns"><button class="pillbtn" data-act="drive">From Google Drive</button><button class="pillbtn ghost" data-act="import">From Files</button></div></div>`;

/* ---------- Home ---------- */
function rowHTML(title,list,kind,series){ if(!list.length) return ''; const see=`data-act="see" data-kind="${kind}"${series!=null?` data-series="${esc(series)}"`:''}`;
  const more=`<button class="row-more" data-act="smenu" data-kind="${kind}"${series!=null?` data-series="${esc(series)}"`:''} aria-label="Options for ${esc(title)}">${IC.more}</button>`;
  return `<section class="row"><div class="row-top"><button class="row-h" ${see}><h2>${esc(title)}</h2><span class="n">${list.length}</span>${IC.chev}</button>${more}</div>
  <div class="row-s">${list.slice(0,20).map(c=>`<button class="rc" data-act="open" data-id="${c.id}" aria-label="${esc(c.title)}">${coverBox(c)}<div class="t">${esc(c.title)}</div></button>`).join('')}<button class="seeall" ${see}>${IC.grid}See all</button></div></section>`; }
/* ---------- reading lists (queues): named reading orders mixing any series; a comic opened from one continues in its order ---------- */
let queues=[];
const queueComics=q=>q?q.items.map(id=>comics.find(c=>c.id===id)).filter(Boolean):[];
const queueStat=q=>{ const L=queueComics(q); return {x:L.filter(isDone).length,y:L.length}; };
function queueRowHTML(q){ const L=queueComics(q), st=queueStat(q);
  const more=`<button class="row-more" data-act="qmenu" data-q="${q.id}" aria-label="Options for ${esc(q.name)}">${IC.more}</button>`;
  return `<section class="row qrow" data-q="${q.id}"><div class="row-top"><button class="row-h" data-act="qedit" data-kind="queue" data-q="${q.id}"><span class="qtag" aria-hidden="true">${IC.list}</span><h2>${esc(q.name)}</h2><span class="n qprog">${st.x} of ${st.y}</span>${IC.chev}</button>${more}</div>
  <div class="row-s">${L.length?L.map((c,i)=>`<button class="rc" data-act="open" data-id="${c.id}" data-q="${q.id}" aria-label="${i+1}. ${esc(c.title)}">${coverBox(c)}<div class="t"><span class="qn">${i+1}</span>${esc(c.title)}</div></button>`).join('')
    :`<div class="qempty">Empty. Long-press a comic and choose <b>Add to Reading List</b>.</div>`}</div></section>`; }
async function saveQueue(q){ q.updated=Date.now(); if(!queues.includes(q)) queues.push(q); await qPut(q); }
async function newQueue(name,items=[]){ const q={id:uid(),name:name.trim().slice(0,80)||'Reading List',items:[...items],created:Date.now(),updated:Date.now()}; await saveQueue(q); return q; }
async function deleteQueue(q){ if(!await confirmBox('Delete Reading List?',`“${q.name}” will be removed. The comics in it stay in your library.`)) return false;
  await qDel(q.id); queues=queues.filter(x=>x!==q); if(R&&R.queue===q.id) R.queue=null; renderShelf(); toast('Reading list deleted'); return true; }
function queueMenu(anchor,qid){ const q=queues.find(x=>x.id===qid); if(!q) return;
  openMenu(anchor,[{label:'Edit Reading List…',icon:IC.edit,id:'qmEdit',run:()=>editQueue(qid)},{label:'Arrange Categories…',icon:IC.arrange,run:()=>arrangeRows()},{label:'Delete Reading List',icon:IC.trash,id:'qmDelete',run:()=>deleteQueue(q)}]); }
// add one comic to reading lists: tick lists, or name a new one
async function addToQueue(id){ const c=comics.find(x=>x.id===id); if(!c) return; document.querySelector('.mwrap')?.remove();
  const Q=queues.slice().sort((a,b)=>b.updated-a.updated);
  const {r,vals}=await modal(`<div class="mh"><h3>Add to Reading List</h3><p class="dlsub">${esc(c.title)}</p></div>
    <div class="dllist ck" id="qaList">${Q.map(q=>`<label class="ckr"><input type="checkbox" data-q="${q.id}" ${q.items.includes(id)?'checked':''}><span class="ckt"><b>${esc(q.name)}</b><small>${queueStat(q).y} comic${queueStat(q).y===1?'':'s'}</small></span></label>`).join('')||'<p class="qnone">No reading lists yet. Name one below, e.g. “Inferno”.</p>'}</div>
    <div class="mb qnew"><label class="fld"><span>New reading list</span><input type="text" id="qaName" maxlength="80" placeholder="e.g. Inferno" autocomplete="off" autocapitalize="words"></label></div>
    <div class="mf"><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="save" id="qaDone">Done</button></div>`,
  w=>{ const i=w.querySelector('#qaName'); i.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); w.querySelector('#qaDone').click(); } });
    w._vals=()=>({name:i.value,on:[...w.querySelectorAll('#qaList input[data-q]')].map(x=>[x.dataset.q,x.checked])}); },'drv ckm');
  if(r!=='save') return; const added=[];
  for(const [qid,on] of vals.on){ const q=queues.find(x=>x.id===qid); if(!q) continue; const has=q.items.includes(id);
    if(on&&!has){ q.items.push(id); await saveQueue(q); added.push(q.name); } else if(!on&&has){ q.items=q.items.filter(x=>x!==id); await saveQueue(q); } }
  if(vals.name.trim()){ const q=await newQueue(vals.name,[id]); added.push(q.name); }
  renderShelf(); if(added.length) toast(`Added to ${added.map(n=>'“'+n+'”').join(', ')}`); }
// edit a list: rename, drag ≡ to reorder, remove comics, delete the list
async function editQueue(qid){ const q=queues.find(x=>x.id===qid); if(!q) return; document.querySelector('.mwrap')?.remove();
  const li=c=>`<li class="arr qi" data-id="${c.id}"><span class="ah" aria-hidden="true">${IC.grip}</span><img src="${cover(c)}" alt=""><span class="at"><b>${esc(c.title)}</b><small>${c.series?esc(c.series)+' · ':''}${isDone(c)?'Finished':inProg(c)?pctOf(c)+'%':'Unread'}</small></span>
    <button class="qx" aria-label="Remove ${esc(c.title)}">${IC.x}</button></li>`;
  const {r,vals}=await modal(`<div class="mh"><h3>Reading List</h3><label class="fld" style="margin-top:8px"><input type="text" id="qeName" value="${esc(q.name)}" maxlength="80" autocomplete="off" aria-label="Name"></label>
    <p class="dlsub" id="qeSub"></p></div>
    <ul class="dllist arrl" id="qeList">${queueComics(q).map(li).join('')}</ul>
    <div class="mf"><button class="btn ghost" data-r="delete" id="qeDelete" style="color:#ff453a">Delete</button><span class="sp"></span><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="save" id="qeDone">Done</button></div>`,
  w=>{ const L=w.querySelector('#qeList'); const sync=()=>{ const n=L.children.length; w.querySelector('#qeSub').textContent=n?`${n} comic${n===1?'':'s'} · drag ≡ to change the reading order`:'Empty. Long-press a comic and choose Add to Reading List.'; };
    L.addEventListener('click',e=>{ const b=e.target.closest('.qx'); if(b){ b.closest('li').remove(); sync(); } }); dragSort(L,sync); sync();
    w._vals=()=>({name:w.querySelector('#qeName').value,items:[...L.children].map(x=>x.dataset.id)}); },'drv ckm arrm qem');
  if(r==='delete'){ deleteQueue(q); return; } if(r!=='save') return;
  const missing=q.items.filter(id=>!comics.some(c=>c.id===id));   // keep ids of comics not on this device (none normally)
  q.name=vals.name.trim()||q.name; q.items=vals.items.concat(missing); await saveQueue(q); renderShelf(); }
/* ---------- Home row arrangement: saved order + hidden set (settings store); keys 'added' | 's:<series>' ---------- */
const alpha=(a,b)=>a.localeCompare(b,undefined,{numeric:true});
const rowPrefs=()=>{ const p=store.get('rowOrder',null)||{}; return {order:Array.isArray(p.order)?p.order:[],hidden:Array.isArray(p.hidden)?p.hidden:[],saved:!!p.order}; };
const setRowPrefs=(order,hidden)=>store.set('rowOrder',{order,hidden});
const defaultKeys=()=>['added',...queues.slice().sort((a,b)=>a.created-b.created).map(q=>'q:'+q.id),...seriesCounts().map(([s])=>'s:'+s).sort((a,b)=>alpha(a,b))];
// saved order (only rows that still exist), then any rows not in it: new series appended alphabetically
function rowKeys(){ const cur=defaultKeys(), have=new Set(cur), p=rowPrefs(); if(!p.saved) return cur;
  const out=p.order.filter(k=>have.has(k)), inn=new Set(out), nq=cur.filter(k=>!inn.has(k)&&k.startsWith('q:')), rest=cur.filter(k=>!inn.has(k)&&!k.startsWith('q:'));
  const at=out.indexOf('added')+1; out.splice(at,0,...nq); return out.concat(rest); }   // new reading lists go right under Recently Added
// rename/merge: the result takes the topmost position of the rows involved; hidden only if all of them were hidden
function carryRow(from,to){ const p=rowPrefs(); if(!p.saved&&!p.hidden.length) return; const order=rowKeys(), tk='s:'+to, keys=new Set(from.map(f=>'s:'+f).concat(tk));
  const idx=order.findIndex(k=>keys.has(k)); const allHidden=[...keys].filter(k=>order.includes(k)).every(k=>p.hidden.includes(k));
  const no=order.filter(k=>!keys.has(k)); if(idx>=0) no.splice(Math.min(idx,no.length),0,tk); else no.push(tk);
  const nh=p.hidden.filter(k=>!keys.has(k)); if(allHidden) nh.push(tk); setRowPrefs(no,nh); }
// carousel: in-progress (most recently read first), then other read comics, then newest unread; de-duplicated, max CF_MAX
const CF_MAX=50, CF_WIN=10;
function heroList(){ const seen=new Set(), out=[], push=L=>{ for(const c of L){ if(out.length>=CF_MAX) return; if(!seen.has(c.id)){ seen.add(c.id); out.push(c); } } };
  const read=comics.filter(c=>c.lastRead).sort((a,b)=>b.lastRead-a.lastRead);
  push(read.filter(inProg)); push(read); push(comics.filter(c=>!c.lastRead).sort((a,b)=>b.added-a.added)); push(comics.slice().sort((a,b)=>b.added-a.added));
  return out; }
const cfItemsHTML=L=>L.map((c,i)=>`<div class="cf-item" data-i="${i}" data-id="${c.id}" style="display:none"><img alt="${esc(c.title)}" decoding="async" draggable="false"><div class="dim"></div></div>`).join('');
// series page carousel: strictly by issue number (ascending), then title
const seriesHeroList=s=>comics.filter(c=>(c.series||'')===s).sort(byIssue);
function renderSeriesHero(){ const sh=$('#seriesHero'); if(!sh) return;
  if(!ui.series||!comics.length){ if(sh.dataset.sig){ sh.dataset.sig=''; sh.innerHTML=''; SCF.stop(); SCF.el=null; SCF.items=[]; } return; }
  const L=seriesHeroList(ui.series), sig=ui.series+'|'+L.map(c=>c.id+'.'+(c.coverV||'')).join(',');
  if(sh.dataset.sig===sig) return; sh.dataset.sig=sig; SCF.stop();
  if(!L.length){ sh.innerHTML=''; SCF.el=null; SCF.items=[]; return; }
  sh.innerHTML=`<div class="hero shero"><div class="cf" id="scf" aria-label="${esc(ui.series)}">${cfItemsHTML(L)}</div></div>`; SCF.mount($('#scf'),L); }
function renderHome(){
  const el=$('#homeScroll'); if(!comics.length){ el.innerHTML=emptyHTML(); Drive.preload(); CF.items=[]; CF.el=null; return; }
  const cf=heroList();
  const groups=new Map(); comics.forEach(c=>{ const s=(c.series||'').trim(); if(s){ if(!groups.has(s)) groups.set(s,[]); groups.get(s).push(c); } });
  let rows=''; const hid=new Set(rowPrefs().hidden);
  rowKeys().filter(k=>!hid.has(k)).forEach(k=>{ if(k==='added') rows+=rowHTML('Recently Added',comics.slice().sort((a,b)=>b.added-a.added),'added');
    else if(k.startsWith('q:')){ const q=queues.find(x=>'q:'+x.id===k); if(q) rows+=queueRowHTML(q); }
    else { const s=k.slice(2); if(groups.has(s)) rows+=rowHTML(s,groups.get(s).sort(byIssue),'series',s); } });
  // Home rows: Recently Added + one per series only (Unread/Finished live as Library filter chips)
  el.innerHTML=`<div class="hero"><div class="cf" id="cf" aria-label="Recently read">${cfItemsHTML(cf)}</div></div><div class="rows">${rows}</div>`;
  CF.mount($('#cf'),cf);
}

/* ---------- 3D coverflow: touch-tracked, momentum, snaps to center ---------- */
// one factory, two carousels: Home (CF) and the series page (SCF)
const makeCF=()=>({items:[],pos:0,el:null,cw:240,sp:180,raf:0,shown:-1,
  mount(el,items){ this.el=el; this.items=items; this.pos=0; this.shown=-1; this.vis=new Set(); this.size(); this.bind(); },
  size(){ if(!this.el||!this.el.isConnected) return; const vw=innerWidth, vh=innerHeight;
    this.cw=Math.round(vw<600? Math.min(vw*.46,vh*.3) : Math.min(290,vw*.3,vh*.33)); this.sp=this.cw*.8;
    // side-stack spacing: solve so the 7th neighbour's centre lands on the screen edge (after perspective shrink), so stacks run off both edges
    { const cw=this.cw, T=7, P=1100, z=cw*.55+(T-1)*cw*.2, need=(vw/2)*(P+z)/P; this.gap=clamp((need-cw*.8)/(T-1),cw*.12,cw*.5);
      // window = neighbours up to the first one that sits fully past the screen edge (capped at CF_WIN): stacks always bleed off, no wasted layers
      this.win=CF_WIN; for(let k=2;k<=CF_WIN;k++){ const f=P/(P+cw*.55+(k-1)*cw*.2); if((cw*.8+(k-1)*this.gap-cw*.32)*f>vw/2){ this.win=k; break; } } }
    this.el.style.setProperty('--cw',this.cw+'px'); this.layout(); },
  // virtualized: only covers within ±CF_WIN of centre are displayed/transformed (enough to bleed past both edges); covers load lazily (±CF_WIN+2 prefetch)
  layout(){ if(!this.el) return; const kids=this.el.children, cw=this.cw, gap=this.gap||cw*.3, n=kids.length, W=this.win||CF_WIN;
    const lo=Math.max(0,Math.floor(this.pos)-W), hi=Math.min(n-1,Math.ceil(this.pos)+W), vis=this.vis||(this.vis=new Set());
    for(const k of [...vis]) if(k<lo||k>hi){ kids[k].style.display='none'; vis.delete(k); }
    for(let k=Math.max(0,lo-2);k<=Math.min(n-1,hi+2);k++){ const im=kids[k].firstChild; if(!im.src){ const u=cover(this.items[k]); if(u) im.src=u; } }
    for(let k=lo;k<=hi;k++){ const it=kids[k], o=k-this.pos, ao=Math.abs(o);
      if(!vis.has(k)){ it.style.display=''; vis.add(k); }
      const s=Math.sign(o), a=Math.min(ao,1), x=s*(a*cw*.8+Math.max(0,ao-1)*gap);
      const z=-a*cw*.55-Math.max(0,ao-1)*cw*.2, rot=-clamp(o,-1,1)*52, sc=1-a*.1;
      it.style.transform=`translateX(${x.toFixed(1)}px) translateZ(${z.toFixed(1)}px) rotateY(${rot.toFixed(2)}deg) scale(${sc.toFixed(3)})`;
      it.style.zIndex=1000-Math.round(ao*100); it.lastChild.style.opacity=Math.min(.55,a*.3+Math.max(0,ao-1)*.04).toFixed(3);   // light dimming so the centre stands out; far covers fade only slightly
      it.classList.toggle('lite',ao>2.5); }   // covers stay sharp (no blur); far stacks drop reflection/shadow (keeps compositing cheap)
    this.info(); },
  info(){ const i=clamp(Math.round(this.pos),0,this.items.length-1); if(i===this.shown) return; this.shown=i; const c=this.items[i]; if(!c||!this.el) return;
    // no caption under the carousel: the centre cover itself is the control (tap opens); keep it labelled for VoiceOver
    [...this.el.children].forEach((it,k)=>{ it.setAttribute('role','button'); it.setAttribute('aria-label',k===i?`${c.lastRead&&!isDone(c)?'Continue reading':'Open'} ${c.title}${c.lastRead?`, page ${(c.page||0)+1-skipList(c).filter(p=>p<(c.page||0)).length} of ${c.pages-skipList(c).length}`:''}`:this.items[k].title); }); },
  stop(){ cancelAnimationFrame(this.raf); this.raf=0; },
  moving(v){ if(this.el) this.el.classList.toggle('moving',v); },   // shadows are dropped while moving (cheaper compositing)
  to(target,dur){ this.stop(); this.moving(true); const from=this.pos, t0=performance.now(); target=clamp(target,0,this.items.length-1);
    const step=now=>{ const k=Math.min(1,(now-t0)/dur), e=1-Math.pow(1-k,3); this.pos=from+(target-from)*e; this.layout(); if(k<1) this.raf=requestAnimationFrame(step); else { this.raf=0; this.pos=target; this.layout(); this.moving(false); } };
    this.raf=requestAnimationFrame(step); },
  bind(){ const el=this.el; let d=null;
    el.addEventListener('pointerdown',e=>{ if(e.button>0) return; this.stop(); d={id:e.pointerId,x0:e.clientX,y0:e.clientY,p0:this.pos,drag:false,s:[[e.timeStamp,e.clientX]],t0:e.timeStamp}; });
    el.addEventListener('pointermove',e=>{ if(!d||e.pointerId!==d.id) return; const dx=e.clientX-d.x0, dy=e.clientY-d.y0;
      if(!d.drag){ if(Math.abs(dx)>7&&Math.abs(dx)>Math.abs(dy)){ d.drag=true; this.moving(true); cancelLP(); try{el.setPointerCapture(e.pointerId)}catch(_){} } else if(Math.abs(dy)>10){ d=null; return; } else return; }
      d.s.push([e.timeStamp,e.clientX]); if(d.s.length>8) d.s.shift();
      let p=d.p0-dx/this.sp; const n=this.items.length-1; if(p<0) p*=.35; else if(p>n) p=n+(p-n)*.35; this.pos=p; this.layout(); });
    const end=(e,cancel)=>{ if(!d||e.pointerId!==d.id) return; const g=d; d=null;
      if(g.drag){ const s=g.s.filter(q=>g.s[g.s.length-1][0]-q[0]<=100), a=s[0], b=s[s.length-1]; /* velocity over the last ~100ms of the gesture */ const v=(b[0]-a[0])>0&&(e.timeStamp-b[0])<90? (b[1]-a[1])/(b[0]-a[0]) : 0;   // px/ms
        const proj=v*300*(1+Math.min(2.5,Math.abs(v))*.45); const target=Math.round(this.pos-proj/this.sp); const dist=Math.abs(clamp(target,0,this.items.length-1)-this.pos); this.to(target,clamp(300+dist*75,300,1400)); return; }
      if(cancel||lpFired) return; if(e.timeStamp-g.t0>600) return;
      const it=e.target.closest('.cf-item'); if(!it) return; const i=+it.dataset.i;
      if(SEL.on) return; if(i===Math.round(this.pos)) openReader(it.dataset.id); else this.to(i,420); };
    el.addEventListener('pointerup',e=>end(e,false)); el.addEventListener('pointercancel',e=>end(e,true));
    let wt=0; el.addEventListener('wheel',e=>{ if(Math.abs(e.deltaX)<=Math.abs(e.deltaY)) return; e.preventDefault(); this.stop(); this.moving(true); const n=this.items.length-1;
      this.pos=clamp(this.pos+e.deltaX/this.sp,-.3,n+.3); this.layout(); clearTimeout(wt); wt=setTimeout(()=>this.to(Math.round(this.pos),300),120); },{passive:false}); }
});
const CF=makeCF(), SCF=makeCF();
addEventListener('resize',()=>{ clearTimeout(CF.rt); CF.rt=setTimeout(()=>{ CF.size(); SCF.size(); },80); });

/* ---------- Library ---------- */
const FILTERS=[['all','All'],['unread','Unread'],['progress','In Progress'],['finished','Finished']];
const SORTS={recent:'Recent',title:'Title',added:'Date Added',series:'Series'};
function libList(){ const q=ui.q.trim().toLowerCase(); let L=comics.filter(c=>(ui.series==null||(c.series||'')===ui.series)&&(!q||c.title.toLowerCase().includes(q)||(c.series||'').toLowerCase().includes(q)));
  if(ui.filter==='unread') L=L.filter(isUnread); else if(ui.filter==='progress') L=L.filter(inProg); else if(ui.filter==='finished') L=L.filter(isDone);
  if(ui.sort==='title') L.sort(ui.series!=null?byIssue:byTitle); else if(ui.sort==='added') L.sort((a,b)=>b.added-a.added);
  else if(ui.sort==='series') L.sort((a,b)=>(!a.series)-(!b.series)||(a.series||'').localeCompare(b.series||'',undefined,{numeric:true})||byIssue(a,b));
  else L.sort((a,b)=>(b.lastRead||0)-(a.lastRead||0)||b.added-a.added);
  return L; }
const letterOf=t=>{ const ch=(t||'').trim().charAt(0).toUpperCase(); return /[A-Z]/.test(ch)?ch:'#'; };
function renderLibrary(){ scopeUI();
  $('#sortLbl').textContent=SORTS[ui.sort];
  $('#chips').innerHTML=''+FILTERS.map(([k,l])=>`<button class="chip${ui.filter===k?' on':''}" data-act="filter" data-f="${k}">${l}</button>`).join('');
  const grid=$('#libGrid'), az=$('#azIndex');
  if(!comics.length){ grid.innerHTML=''; grid.style.display='none'; renderSeriesHero(); if(!$('#libScroll .empty')) $('#libScroll').insertAdjacentHTML('beforeend',emptyHTML()); az.classList.add('hidden'); $('#library .libbar').classList.add('hidden'); return; }
  $('#library .libbar').classList.remove('hidden'); $('#libScroll .empty')?.remove(); grid.style.display='';
  renderSeriesHero(); const L=libList(); const seen=new Set();
  grid.innerHTML=L.length? L.map(c=>{ const l=letterOf(c.title); const first=ui.sort==='title'&&!seen.has(l)&&(seen.add(l),true);
    return `<button class="lc${SEL.ids.has(c.id)?' on':''}" data-act="open" data-id="${c.id}" data-title="${esc(c.title)}" aria-label="${esc(c.title)}"${first?` data-letter="${l}"`:''}>${coverBox(c)}<span class="ck" aria-hidden="true">${IC.check}</span></button>`; }).join('')
    : `<div class="lempty" style="grid-column:1/-1">No comics here${ui.q?` matching “${esc(ui.q)}”`:''}.</div>`;
  const showAZ=ui.sort==='title'&&ui.series==null&&L.length>0; az.classList.toggle('hidden',!showAZ); grid.style.setProperty('--azw',showAZ?'14px':'0px');
  if(SEL.on) syncSel();
  if(showAZ) az.innerHTML=[...'ABCDEFGHIJKLMNOPQRSTUVWXYZ#'].map(l=>`<span data-l="${l}" class="${seen.has(l)?'':'off'}">${l}</span>`).join('');
}
$('#q').addEventListener('input',e=>{ ui.q=e.target.value; renderLibrary(); });
$('#sortBtn').addEventListener('click',e=>{ e.stopPropagation(); openMenu($('#sortBtn'),Object.entries(SORTS).map(([k,l])=>({label:l,on:ui.sort===k,run:()=>{ ui.sort=k; store.set('sort',k); renderLibrary(); $('#libScroll').scrollTop=0; }}))); });
function seeAll(kind,series){ ui.series=null; ui.filter='all'; ui.q=''; $('#q').value='';
  if(kind==='series'){ ui.series=series; ui.sort='title'; } else if(kind==='added') ui.sort='added'; else if(kind==='unread'){ ui.filter='unread'; ui.sort='title'; } else if(kind==='finished') ui.filter='finished';
  store.set('sort',ui.sort); renderLibrary(); setTab('library'); $('#libScroll').scrollTop=0; }
// A–Z jump index (drag along it like iOS)
(()=>{ const az=$('#azIndex'); let pop=null, on=false;
  const pick=y=>{ const els=[...az.children]; if(!els.length) return; let best=els[0]; for(const s of els){ const r=s.getBoundingClientRect(); if(y>=r.top) best=s; }
    const order=els.map(s=>s.dataset.l), i0=order.indexOf(best.dataset.l); let tgt=null;
    for(let i=i0;i<order.length&&!tgt;i++) tgt=$(`#libGrid [data-letter="${order[i]}"]`);
    for(let i=i0;i>=0&&!tgt;i--) tgt=$(`#libGrid [data-letter="${order[i]}"]`);
    els.forEach(s=>s.classList.toggle('hit',s===best));
    if(!pop){ pop=document.createElement('div'); pop.className='azpop'; $('#library').appendChild(pop); }
    pop.textContent=best.dataset.l; const lr=$('#library').getBoundingClientRect(); pop.style.top=(clamp(y-lr.top-28,60,lr.height-80))+'px';
    if(tgt){ const sc=$('#libScroll'); sc.scrollTop=tgt.offsetTop-8; } };
  const done=()=>{ on=false; setTimeout(()=>{ pop?.remove(); pop=null; az.querySelectorAll('.hit').forEach(s=>s.classList.remove('hit')); },350); };
  az.addEventListener('pointerdown',e=>{ on=true; try{az.setPointerCapture(e.pointerId)}catch(_){} pick(e.clientY); e.preventDefault(); });
  az.addEventListener('pointermove',e=>{ if(on) pick(e.clientY); }); az.addEventListener('pointerup',done); az.addEventListener('pointercancel',done); })();

/* ---------- clicks, long-press & context menu ---------- */
let lp=null, lpFired=false;
function cancelLP(){ if(lp){ clearTimeout(lp.t); lp=null; } }
const shelfEl=$('#shelf');
const lpTarget=e=>e.target.closest('[data-id]')||e.target.closest('#homeScroll .row-h');
const lpRun=t=>t.dataset.id? actionSheet(t.dataset.id) : t.dataset.kind==='queue'? queueMenu(t,t.dataset.q) : seriesMenu(t,t.dataset.kind==='series'?t.dataset.series:'');
shelfEl.addEventListener('pointerdown',e=>{ lpFired=false; if(SEL.on) return; const t=lpTarget(e); if(!t||e.button>0) return; cancelLP();
  lp={x:e.clientX,y:e.clientY,t:setTimeout(()=>{ lp=null; lpFired=true; try{navigator.vibrate&&navigator.vibrate(8)}catch(_){} lpRun(t); },520)}; });
shelfEl.addEventListener('pointermove',e=>{ if(lp&&Math.hypot(e.clientX-lp.x,e.clientY-lp.y)>9) cancelLP(); });
shelfEl.addEventListener('pointerup',cancelLP); shelfEl.addEventListener('pointercancel',cancelLP);
shelfEl.addEventListener('scroll',cancelLP,true);
shelfEl.addEventListener('contextmenu',e=>{ e.preventDefault(); if(SEL.on) return; const t=lpTarget(e); if(t&&!lpFired){ cancelLP(); lpFired=true; lpRun(t); } });
shelfEl.addEventListener('click',e=>{ if(lpFired){ lpFired=false; e.preventDefault(); e.stopPropagation(); return; }
  const a=e.target.closest('[data-act]'); if(!a) return; const k=a.dataset.act;
  if(SEL.on&&a.classList.contains('lc')){ e.preventDefault(); e.stopPropagation(); toggleSel(a.dataset.id); return; }
  if(k==='timeline'){ openTimeline(); return; }
  if(k==='rack'){ openRack(+a.dataset.ym); return; }
  if(k==='open') openReader(a.dataset.id,a.dataset.q?{queue:a.dataset.q}:{queue:null}); else if(k==='qedit') editQueue(a.dataset.q); else if(k==='qmenu') queueMenu(a,a.dataset.q); else if(k==='see') seeAll(a.dataset.kind,a.dataset.series);
  else if(k==='filter'){ ui.filter=a.dataset.f; renderLibrary(); $('#libScroll').scrollTop=0; } else if(k==='unscope') unscope();
  else if(k==='smenu') seriesMenu(a,a.dataset.kind==='series'?a.dataset.series:''); else if(k==='srename') renameSeries(a.dataset.series); else if(k==='smerge') mergeSeries([a.dataset.series]);
  else if(k==='import') $('#fileIn').click(); else if(k==='drive') Drive.start(); },true);
$('#fileIn').addEventListener('change',e=>{ const fs=[...e.target.files]; e.target.value=''; if(fs.length) importFiles(fs); });
$('#settingsBtn').onclick=()=>openSettings();
document.addEventListener('keydown',e=>{ if(R&&R.comic||document.querySelector('.mwrap')||ui.tab!=='home'||!CF.el||e.target.matches('input')) return;
  if(e.key==='ArrowLeft') CF.to(Math.round(CF.pos)-1,320); else if(e.key==='ArrowRight') CF.to(Math.round(CF.pos)+1,320); else if(e.key==='Enter'){ const c=CF.items[Math.round(CF.pos)]; if(c) openReader(c.id); } });

/* ---------- menus, sheets, modals ---------- */
function openMenu(anchor,items,cls){ document.querySelector('.menu')?.remove(); const m=document.createElement('div'); m.className='menu'+(cls?' '+cls:''); m.setAttribute('role','menu');
  m.innerHTML=items.map((it,i)=>it.icon?`<button role="menuitem" data-i="${i}"${it.id?` id="${it.id}"`:''}><span>${esc(it.label)}</span>${it.icon}</button>`:`<button role="menuitemradio" aria-checked="${!!it.on}" data-i="${i}">${esc(it.label)}${it.on?IC.check:''}</button>`).join(''); document.body.appendChild(m);
  const r=anchor.getBoundingClientRect(); m.style.top=(r.bottom+6)+'px'; m.style.left=Math.max(8,Math.min(innerWidth-m.offsetWidth-8,r.right-m.offsetWidth))+'px';
  const close=()=>{ m.remove(); document.removeEventListener('pointerdown',out,true); }; const out=e=>{ if(!m.contains(e.target)) close(); };
  setTimeout(()=>document.addEventListener('pointerdown',out,true),0); m.addEventListener('click',e=>{ const b=e.target.closest('button'); if(b){ close(); items[+b.dataset.i].run(); } }); }
function modal(html,onOpen,cls){ return new Promise(res=>{ const w=document.createElement('div'); w.className='mwrap'; w.innerHTML=`<div class="modal${cls?' '+cls:''}" role="dialog" aria-modal="true">${html}</div>`; document.body.appendChild(w);
  let vals=null; const close=v=>{ if(w._vals) vals=w._vals(); w.remove(); document.removeEventListener('keydown',kd); res({r:v,vals}); };
  const kd=e=>{ if(e.key==='Escape') close(null); }; document.addEventListener('keydown',kd);
  w.addEventListener('click',e=>{ if(e.target===w) close(null); const b=e.target.closest('[data-r]'); if(b) close(b.dataset.r); });
  onOpen&&onOpen(w,close); }); }
async function confirmBox(title,msg,ok='Delete'){ return (await modal(`<div class="mh"><h3>${esc(title)}</h3></div><div class="mb"><p class="confirm-msg">${esc(msg)}</p></div><div class="mf"><button class="btn ghost" data-r="no">Cancel</button><button class="btn red" data-r="yes" id="confirmOk">${esc(ok)}</button></div>`)).r==='yes'; }
async function actionSheet(id){ const c=comics.find(x=>x.id===id); if(!c) return; document.querySelector('.mwrap')?.remove();
  const {r}=await modal(`<div class="grp"><div class="hd"><img src="${cover(c)}" alt=""><div><b>${esc(c.title)}</b><span>${c.series?esc(c.series)+' · ':''}${c.pages} pages${c.lastRead?' · '+pctOf(c)+'%':''}</span></div></div>
    <button class="act" data-r="read" id="aRead">${IC.book}${c.lastRead&&!isDone(c)?'Continue Reading':'Read'}</button>
    <button class="act" data-r="queue" id="aQueue">${IC.list}Add to Reading List…</button>
    <button class="act" data-r="edit" id="aEdit">${IC.edit}Edit Title &amp; Series</button>
    <button class="act" data-r="date" id="aDate">${IC.cal}Release Date<small class="actv">${esc(fmtDate(dateOf(c)))}</small></button>
    <button class="act" data-r="toggle" id="aToggle">${isDone(c)?IC.undo+'Mark as Unread':IC.done+'Mark as Finished'}</button>
    <button class="act red" data-r="delete" id="aDelete">${IC.trash}Delete from Device</button></div>
    <button class="cancel" data-r="cancel">Cancel</button>`,null,'sheet');
  if(r==='read') openReader(id); else if(r==='queue') addToQueue(id); else if(r==='edit') editComic(id); else if(r==='date') dateSheet(id); else if(r==='delete') deleteComic(id);
  else if(r==='toggle'){ if(isDone(c)){ c.progress=0; c.page=0; c.lastRead=0; } else { c.progress=1; } await dbPut(c); renderShelf(); } }
async function editComic(id){ const c=comics.find(x=>x.id===id); if(!c) return;
  const series=[...new Set(comics.map(x=>x.series).filter(Boolean))].sort();
  const {r,vals}=await modal(`<div class="mh"><h3>Edit Comic</h3></div><div class="mb">
    <label class="fld"><span>Title</span><input type="text" id="eTitle" value="${esc(c.title)}" maxlength="140"></label>
    <label class="fld"><span>Series</span><input type="text" id="eSeries" value="${esc(c.series||'')}" list="seriesList" placeholder="None" maxlength="80"><datalist id="seriesList">${series.map(s=>`<option value="${esc(s)}">`).join('')}</datalist></label>
    <div class="fld"><span>Cover</span><div class="seg4" id="eCover" role="radiogroup">${[['auto','Auto'],['right','Right half'],['left','Left half'],['full','Full page']].map(([v,l])=>`<button type="button" role="radio" data-v="${v}" aria-checked="${(c.coverMode||'auto')===v}" class="${(c.coverMode||'auto')===v?'on':''}">${l}</button>`).join('')}</div></div>
    <div class="fld"><span>Page turn</span><div class="seg4 seg3" id="eTurn" role="radiogroup">${[['auto','Auto'],['standard','Standard'],['fold','Fold in middle']].map(([v,l])=>`<button type="button" role="radio" data-v="${v}" aria-checked="${(c.turnMode||'auto')===v}" class="${(c.turnMode||'auto')===v?'on':''}">${l}</button>`).join('')}</div>
      <small class="fhint">Fold in middle: for PDFs with two comic pages side by side on each page. Auto detects them${typeof c.foldAuto==='boolean'?` (detected: ${c.foldAuto?'fold in middle':'standard'})`:''}.</small></div>
    <div class="fld" id="eFoldPW"${(c.turnMode==='fold'||(c.turnMode!=='standard'&&c.foldAuto))?'':' style="display:none"'}><span>Portrait</span><div class="seg4 seg2" id="eFoldP" role="radiogroup">${[['half','Half pages'],['full','Full sheet']].map(([v,l])=>`<button type="button" role="radio" data-v="${v}" aria-checked="${(c.foldPortrait||'half')===v}" class="${(c.foldPortrait||'half')===v?'on':''}">${l}</button>`).join('')}</div>
      <small class="fhint">For fold-in-middle comics held upright: Half pages shows one comic page at a time, fitted to the screen. Landscape always shows the full sheet.</small></div>
    <div class="fld"><span>Skip blank pages</span><div class="seg4 seg2" id="eSkip" role="radiogroup">${[['on','On'],['off','Off']].map(([v,l])=>`<button type="button" role="radio" data-v="${v}" aria-checked="${skipVal(c)===v}" class="${skipVal(c)===v?'on':''}">${l}</button>`).join('')}</div>
      <small class="fhint" id="eSkipHint">Leaves out blank pages: black ones (like a black “TM &amp; ©” page between ads) and nearly white ones. ${needsBlack(c)?'Not checked yet.':blankList(c).length?`Found: page${blankList(c).length>1?'s':''} ${blankList(c).map(p=>p+1).join(', ')}.`:'None found in this comic.'}</small></div>
    <label class="tgl"><input type="checkbox" id="eRtl" ${c.rtl?'checked':''}><span>Right-to-left (manga)<small>Reverses page order and swipe direction</small></span></label>
    <div class="mstat">${esc(c.fileName)} · ${fmtBytes(c.size)} · ${c.pages} pages</div>
  </div><div class="mf"><button class="btn ghost" data-r="delete" id="eDelete" style="color:#ff453a">Delete</button><span class="sp"></span><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="save" id="eSave">Save</button></div>`,
  w=>{ w._vals=()=>({t:w.querySelector('#eTitle').value,s:w.querySelector('#eSeries').value,r:w.querySelector('#eRtl').checked,cv:w.querySelector('#eCover .on').dataset.v,tm:w.querySelector('#eTurn .on').dataset.v,fp:w.querySelector('#eFoldP .on').dataset.v,sk:w.querySelector('#eSkip .on').dataset.v});
       ['#eCover','#eTurn','#eFoldP','#eSkip'].forEach(sel=>w.querySelector(sel).addEventListener('click',e=>{ const b=e.target.closest('button'); if(!b) return; w.querySelectorAll(sel+' button').forEach(x=>{ x.classList.toggle('on',x===b); x.setAttribute('aria-checked',x===b); });
         if(sel==='#eTurn') w.querySelector('#eFoldPW').style.display=(b.dataset.v==='fold'||(b.dataset.v==='auto'&&c.foldAuto))?'':'none'; }));
       w.querySelectorAll('input[type=text]').forEach(i=>i.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); w.querySelector('#eSave').click(); } })); });
  if(r==='save'){ c.title=vals.t.trim()||c.title; if(vals.s.trim()!==(c.series||'')) setSeriesManual(c,vals.s.trim()); c.rtl=vals.r; c.turnMode=vals.tm; c.foldPortrait=vals.fp; if(vals.sk!==skipVal(c)) c.skipBlack=vals.sk==='on'; await dbPut(c); renderShelf(); dispatchEvent(new CustomEvent('cr-black',{detail:c.id}));
    if(vals.cv!==(c.coverMode||'auto')){ try{ await recover(c,vals.cv); toast('Cover updated'); }catch(e){ console.warn(e); toast("Couldn't update the cover"); } } }
  else if(r==='delete') deleteComic(id); }
/* ---------- series: rename (renaming onto an existing name merges) and multi-merge ---------- */
const seriesCounts=()=>{ const m=new Map(); comics.forEach(c=>{ const s=(c.series||'').trim(); if(s) m.set(s,(m.get(s)||0)+1); }); return [...m].sort((a,b)=>a[0].localeCompare(b[0],undefined,{numeric:true})); };
const canonSeries=n=>{ n=n.trim().replace(/\s+/g,' '); const hit=seriesCounts().find(([s])=>s.toLowerCase()===n.toLowerCase()); return hit?hit[0]:n; };
async function applySeries(from,to){ const F=new Set(from); let n=0; carryRow(from.filter(f=>f!==to),to);
  for(const c of comics){ const s=(c.series||'').trim(); if(F.has(s)&&s!==to){ setSeriesManual(c,to); await dbPut(c); n++; } }
  if(ui.series!=null&&F.has(ui.series)) ui.series=to; renderShelf(); return n; }
function seriesMenu(anchor,s){ const arr={label:'Arrange Categories…',icon:IC.arrange,id:'smArrange',run:()=>arrangeRows()};
  openMenu(anchor,s?[{label:'Rename Series…',icon:IC.edit,id:'smRename',run:()=>renameSeries(s)},{label:'Merge Series…',icon:IC.merge,id:'smMerge',run:()=>mergeSeries([s])},arr]:[arr]); }
// drag to reorder a list: pointer capture on the .ah handle; the row follows the finger and swaps with neighbours past their midpoint
function dragSort(L,done){ let d=null;
  L.addEventListener('pointerdown',e=>{ const h=e.target.closest('.ah'); if(!h||e.button>0) return; e.preventDefault(); const x=h.closest('li');
    d={x,id:e.pointerId,y0:e.clientY,raf:0,lastY:e.clientY}; x.classList.add('drag'); try{h.setPointerCapture(e.pointerId)}catch(_){} });
  const move=y=>{ if(!d) return; d.lastY=y; const x=d.x; let dy=y-d.y0; let p=x.previousElementSibling, n=x.nextElementSibling;
    while(p&&dy<-p.offsetHeight/2){ L.insertBefore(x,p); d.y0-=p.offsetHeight; dy=y-d.y0; p=x.previousElementSibling; }
    while(n&&dy>n.offsetHeight/2){ L.insertBefore(n,x); d.y0+=n.offsetHeight; dy=y-d.y0; n=x.nextElementSibling; }
    x.style.transform=`translateY(${dy}px)`;
    const lr=L.getBoundingClientRect(); const edge=y<lr.top+36?-1:y>lr.bottom-36?1:0;   // auto-scroll near the list edges
    if(edge&&!d.raf){ const tick=()=>{ if(!d){return;} const before=L.scrollTop; L.scrollTop+=edge*8; d.y0-=L.scrollTop-before; move(d.lastY); d.raf=(L.scrollTop!==before&&(d.lastY<L.getBoundingClientRect().top+36||d.lastY>L.getBoundingClientRect().bottom-36))?requestAnimationFrame(tick):0; }; d.raf=requestAnimationFrame(tick); } };
  L.addEventListener('pointermove',e=>{ if(d&&e.pointerId===d.id){ e.preventDefault(); move(e.clientY); } });
  const end=e=>{ if(!d||e.pointerId!==d.id) return; cancelAnimationFrame(d.raf); d.x.classList.remove('drag'); d.x.style.transform=''; d=null; done&&done(); };
  L.addEventListener('pointerup',end); L.addEventListener('pointercancel',end); }
/* Arrange Categories sheet: drag handle (touch/pen/mouse via pointer events), ↑/↓ buttons, show/hide toggle, reset */
async function arrangeRows(){ document.querySelector('.mwrap')?.remove(); const cnt=new Map(seriesCounts());
  const p=rowPrefs(); let keys=rowKeys(); const hidden=new Set(p.hidden);
  const qOf=k=>queues.find(q=>'q:'+q.id===k);
  const label=k=>k==='added'?'Recently Added':k.startsWith('q:')?(qOf(k)||{}).name||'Reading List':k.slice(2), sub=k=>k==='added'?`${comics.length} comic${comics.length===1?'':'s'}`:k.startsWith('q:')?`Reading list · ${queueStat(qOf(k)).y} comics`:`${cnt.get(k.slice(2))||0} comic${cnt.get(k.slice(2))===1?'':'s'}`;
  const li=k=>`<li class="arr${hidden.has(k)?' off':''}" data-k="${esc(k)}"><span class="ah" aria-hidden="true">${IC.grip}</span><span class="at"><b>${esc(label(k))}</b><small>${sub(k)}</small></span>
    <button class="ab" data-mv="-1" aria-label="Move ${esc(label(k))} up">${IC.up}</button><button class="ab" data-mv="1" aria-label="Move ${esc(label(k))} down">${IC.down}</button>
    <label class="tgl sm" aria-label="Show ${esc(label(k))} on Home"><input type="checkbox" class="avis" ${hidden.has(k)?'':'checked'}></label></li>`;
  const {r,vals}=await modal(`<div class="mh"><h3>Arrange Categories</h3><p class="dlsub">Drag ≡ to reorder Home rows, or use the arrows. Switch off to hide a row.</p></div>
    <ul class="dllist arrl" id="arrList">${keys.map(li).join('')}</ul>
    <div class="mf"><button class="btn ghost" id="arrReset">Reset to alphabetical</button><span class="sp"></span><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="save" id="arrDone">Done</button></div>`,
  w=>{ const L=w.querySelector('#arrList');
    const sync=()=>{ const it=[...L.children]; it.forEach((x,i)=>{ x.querySelector('[data-mv="-1"]').disabled=i===0; x.querySelector('[data-mv="1"]').disabled=i===it.length-1; }); };
    L.addEventListener('click',e=>{ const b=e.target.closest('[data-mv]'); if(!b) return; const x=b.closest('li'), d=+b.dataset.mv;
      if(d<0&&x.previousElementSibling) L.insertBefore(x,x.previousElementSibling); else if(d>0&&x.nextElementSibling) L.insertBefore(x.nextElementSibling,x); sync(); b.focus(); });
    L.addEventListener('change',e=>{ const c=e.target.closest('.avis'); if(c) c.closest('li').classList.toggle('off',!c.checked); });
    w.querySelector('#arrReset').onclick=()=>{ const by=new Map([...L.children].map(x=>[x.dataset.k,x])); defaultKeys().forEach(k=>{ const x=by.get(k); if(x) L.appendChild(x); }); sync(); toast('Sorted alphabetically'); };
    dragSort(L,sync);
    w._vals=()=>({order:[...L.children].map(x=>x.dataset.k),hidden:[...L.children].filter(x=>!x.querySelector('.avis').checked).map(x=>x.dataset.k)}); sync(); },'drv ckm arrm');
  if(r!=='save') return; setRowPrefs(vals.order,vals.hidden); renderHome(); toast(vals.hidden.length?`Home rows arranged · ${vals.hidden.length} hidden`:'Home rows arranged'); }
const nameField=(id,val,ph)=>`<input type="text" id="${id}" value="${esc(val)}" list="${id}L" placeholder="${esc(ph)}" maxlength="80" autocomplete="off" autocapitalize="words"><datalist id="${id}L">${seriesCounts().map(([s])=>`<option value="${esc(s)}">`).join('')}</datalist>`;
async function renameSeries(old){ if(!old) return; document.querySelector('.mwrap')?.remove(); const n=comics.filter(c=>(c.series||'').trim()===old).length;
  const {r,vals}=await modal(`<div class="mh"><h3>Rename Series</h3></div><div class="mb">
    <label class="fld"><span>Series name</span>${nameField('srName',old,'Series name')}</label>
    <small class="fhint">“${esc(old)}” · ${n} comic${n===1?'':'s'}. Renaming to the name of another series merges them into one.</small>
  </div><div class="mf"><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="save" id="srSave">Rename</button></div>`,
  w=>{ const i=w.querySelector('#srName'); w._vals=()=>({n:i.value}); setTimeout(()=>{ try{ i.focus(); i.select(); }catch(_){} },60);
       i.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); w.querySelector('#srSave').click(); } }); });
  if(r!=='save') return; const to=canonSeries(vals.n||''); if(!to||to===old) return;
  const merge=seriesCounts().some(([s])=>s===to); const k=await applySeries([old],to);
  toast(merge?`Merged ${k} comic${k===1?'':'s'} into “${to}”`:`Renamed to “${to}”`); }
async function mergeSeries(pre=[]){ document.querySelector('.mwrap')?.remove(); const S=seriesCounts();
  if(S.length<2){ toast('You need at least two series to merge'); return; }
  const sel=new Set(pre.filter(p=>S.some(([s])=>s===p)));
  const guessFor=()=>{ const t=new Map(); comics.filter(c=>sel.has((c.series||'').trim())).forEach(c=>{ const g=seriesGuess(c.title); if(g) t.set(g,(t.get(g)||0)+1); });
    const best=[...t].sort((a,b)=>b[1]-a[1])[0]; if(best) return best[0]; const big=S.filter(([s])=>sel.has(s)).sort((a,b)=>b[1]-a[1])[0]; return big?big[0]:''; };
  const {r,vals}=await modal(`<div class="mh"><h3>Merge Series</h3><p class="dlsub" id="mgSub">Select the series to combine, then name the result.</p></div>
    <div class="dllist ck" id="mgList">${S.map(([s,n],i)=>`<label class="ckr"><input type="checkbox" data-s="${i}" ${sel.has(s)?'checked':''}><span class="ckt"><b>${esc(s)}</b><small>${n} comic${n===1?'':'s'}</small></span></label>`).join('')}</div>
    <div class="mb mgname"><label class="fld"><span>Merged series name</span>${nameField('mgName','','e.g. Uncanny X-Men')}</label></div>
    <div class="mf"><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="go" id="mgGo">Merge</button></div>`,
  w=>{ const inp=w.querySelector('#mgName'), go=w.querySelector('#mgGo'); let typed=false;
    const sync=()=>{ const k=sel.size, cnt=S.filter(([s])=>sel.has(s)).reduce((a,x)=>a+x[1],0); if(!typed) inp.value=k?guessFor():'';
      const nm=canonSeries(inp.value||''); const ok=!!nm&&(k>=2||(k===1&&!sel.has(nm)));
      go.disabled=!ok; go.textContent=k?`Merge ${k} series (${cnt})`:'Merge'; w.querySelector('#mgSub').textContent=k?`${k} selected · ${cnt} comics`:'Select the series to combine, then name the result.'; };
    w.addEventListener('change',e=>{ const c=e.target.closest('input[data-s]'); if(!c) return; const s=S[+c.dataset.s][0]; c.checked?sel.add(s):sel.delete(s); sync(); });
    inp.addEventListener('input',()=>{ typed=!!inp.value; sync(); }); inp.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); if(!go.disabled) go.click(); } });
    w._vals=()=>({n:inp.value,sel:[...sel]}); sync(); },'drv ckm');
  if(r!=='go') return; const to=canonSeries(vals.n||''); if(!to||!vals.sel.length) return;
  const k=await applySeries(vals.sel,to); toast(`Merged ${vals.sel.length} series into “${to}” (${k} comic${k===1?'':'s'} updated)`); }
async function deleteComic(id){ const c=comics.find(x=>x.id===id); if(!c) return;
  if(!await confirmBox('Delete Comic?',`“${c.title}” and its stored PDF (${fmtBytes(c.size)}) will be removed from this device. Your original file in Google Drive is not affected.`)) return;
  await dbDelete(id); comics=comics.filter(x=>x.id!==id); for(const q of queues) if(q.items.includes(id)){ q.items=q.items.filter(x=>x!==id); await saveQueue(q); } const u=coverURL.get(id); if(u){ URL.revokeObjectURL(u); coverURL.delete(id); } renderShelf(); toast('Deleted'); }
async function openSettings(){
  let est={usage:0,quota:0}, persisted=false;
  try{ if(navigator.storage&&navigator.storage.estimate) est=await navigator.storage.estimate(); if(navigator.storage&&navigator.storage.persisted) persisted=await navigator.storage.persisted(); }catch(e){}
  const mine=comics.reduce((a,c)=>a+(c.size||0),0); const standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone;
  const {r}=await modal(`<div class="mh"><h3>Settings</h3></div><div class="mb">
    <div class="stor"><b>${fmtBytes(est.usage||mine)}</b><span>used${est.quota?` of ~${fmtBytes(est.quota)} available`:''}</span></div>
    <div class="mstat">${comics.length} comic${comics.length===1?'':'s'} · ${fmtBytes(mine)} of PDFs · storage ${persisted?'persistent ✓':'not yet marked persistent'}</div>
    <label class="tgl" style="margin-top:8px"><input type="checkbox" id="sSkipBlack" ${store.get('skipBlack',true)?'checked':''}><span>Skip blank pages<small>Leaves out blank pages: black ones (like a black “TM &amp; ©” page between ads) and nearly white ones. Each comic can override this in Edit.</small></span></label>
    <label class="tgl" style="margin-top:8px"><input type="checkbox" id="sPanels" ${store.get('panelView',true)?'checked':''}><span>Guided panel view<small>Double-tap a panel to zoom to it, then swipe panel by panel. Double-tap again for the full page.</small></span></label>
    <label class="tgl" style="margin-top:8px"><input type="checkbox" id="sSingle" ${store.get('singleLandscape',false)?'checked':''}><span>Single page in landscape<small>Off shows two-page spreads when the iPad is sideways</small></span></label>
    <div class="sgrp"><b>Google Drive folder</b><span id="sFolderCur">${esc(Drive.folder().name||'Folder')} · <code>${esc(Drive.folder().id)}</code>${store.get('driveFolder',null)?'':' (default)'}</span>
      <div class="frow"><input id="sFolder" type="url" placeholder="Paste a Drive folder link" autocomplete="off" autocapitalize="off" spellcheck="false"><button class="btn ghost" id="sFolderSave">Save</button></div>
      <small>Google Drive opens in this folder, and Import Entire Drive Folder lists it.${store.get('driveFolder',null)?' <button class="lnk" id="sFolderReset">Reset to default</button>':''}</small></div>
    <div class="sgrp"><b>Release dates</b><span>${comics.filter(lkEligible).length} issue${comics.filter(lkEligible).length===1?'':'s'} with an unknown or estimated (≈) date. Looks up cover dates on the Fandom comics wikis; dates you set are kept.</span>
      <div class="frow"><button class="btn ghost" data-r="lookup" id="sLookup">Look Up Release Dates…</button></div></div>
    <div class="sgrp"><b>Series</b><span>${seriesCounts().length} series. Combine series that came from separate folders (e.g. issue ranges) into one.</span>
      <div class="frow"><button class="btn ghost" data-r="merge" id="sMerge">Merge Series…</button><button class="btn ghost" data-r="arrange" id="sArrange">Arrange Categories…</button></div></div>
    <div class="note"><b>Private and offline.</b> Comics are copied into this app's on-device storage (IndexedDB). Nothing is uploaded.</div>
    <div class="note"><b>Home Screen app:</b> on iPad, the Home Screen app has its own storage, separate from Safari's. Add this page to your Home Screen (Share → Add to Home Screen), open it from there, and import your comics inside the Home Screen app.${standalone?'<br><b>✓ You are in the Home Screen app.</b>':'<br>You are currently in the browser.'}</div>
    ${persisted?'':'<button class="btn ghost" id="sPersist" data-r="persist">Request Persistent Storage</button>'}
  </div><div class="mf"><button class="btn" data-r="done">Done</button></div>`,w=>{ w.querySelector('#sSingle').addEventListener('change',e=>store.set('singleLandscape',e.target.checked)); w.querySelector('#sPanels').addEventListener('change',e=>store.set('panelView',e.target.checked)); w.querySelector('#sSkipBlack').addEventListener('change',e=>{ store.set('skipBlack',e.target.checked); if(R.comic) dispatchEvent(new CustomEvent('cr-black',{detail:R.comic.id})); });
    const cur=()=>{ const f=Drive.folder(); w.querySelector('#sFolderCur').innerHTML=`${esc(f.name||'Folder')} · <code>${esc(f.id)}</code>${store.get('driveFolder',null)?'':' (default)'}`; };
    w.querySelector('#sFolderSave').onclick=()=>{ const f=Drive.parseFolderLink(w.querySelector('#sFolder').value); if(!f){ toast("That doesn't look like a Google Drive folder link"); return; }
      Drive.setFolder({...f,name:'Custom folder'}); w.querySelector('#sFolder').value=''; cur(); toast('Drive folder saved'); };
    const rs=w.querySelector('#sFolderReset'); if(rs) rs.onclick=()=>{ Drive.setFolder(null); rs.remove(); cur(); toast('Using the default Drive folder'); }; });
  if(r==='lookup'){ lookupAll(); return; }
  if(r==='merge'){ mergeSeries(); return; } if(r==='arrange'){ arrangeRows(); return; }
  if(r==='persist'){ try{ const ok=await navigator.storage.persist(); toast(ok?'Storage marked persistent':'The browser declined for now. It often allows it in the Home Screen app.'); }catch(e){ toast('Not supported here'); } } }

/* ---------- release dates + Timeline ---------- */
let dateOv=new Map();   // file key -> {y,m}: manual dates (IndexedDB 'overrides'), re-applied when the same file is imported again
function applyDateOv(c){ const k=fileKeys(c).find(k=>dateOv.has(k)); if(k) c.dateManual=dateOv.get(k); return c; }
function dateOf(c){ if(c.dateManual&&c.dateManual.y) return {...c.dateManual,src:'manual'}; if(c.metaDate&&c.metaDate.y) return c.metaDate;
  return dateFromName(c.fileName)||dateFromName(c.title)||(c.onlineDate&&c.onlineDate.y?c.onlineDate:null)||lookupDate(c.series,issueNo(c.title),c.title,c.fileName,c.autoSeries)||null; }
async function setDate(c,d){ if(d) c.dateManual={y:d.y,m:d.m||0}; else delete c.dateManual;
  for(const k of fileKeys(c)){ if(d){ dateOv.set(k,c.dateManual); await ovPut({k,date:c.dateManual}); } else { dateOv.delete(k); await ovDel(k); } }
  await dbPut(c); renderShelf(); }
const MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
const fmtDate=d=>d?`${d.src==='lookup'?'≈ ':''}${d.m?MONTHS[d.m-1].slice(0,3)+' ':''}${d.y}`:'Unknown';
const SRC_TXT={online:'Looked up online',manual:'Set by you',meta:'From the file’s metadata',name:'From the file name',lookup:'Estimated from series history'};
// comics imported before v24: read embedded dates once, idle-paced
async function backfillDates(){ for(const c of comics){ if(c.dateV===DATE_V||R&&R.comic) continue; let doc; try{ doc=await openPdf(new IDBSource(c.id,c.size)); c.metaDate=await pdfDate(doc); }catch(e){} finally{ try{ doc&&await doc.destroy(); }catch(e){} }
  c.dateV=DATE_V; await dbPut(c); if(c.metaDate&&TL.on) renderTimeline(); await new Promise(r=>setTimeout(r,120)); } }
function dateSheet(id){ const c=comics.find(x=>x.id===id); if(!c) return; const d=dateOf(c); document.querySelector('.mwrap')?.remove();
  return modal(`<div class="mh"><h3>Release Date</h3><p class="dlsub">${esc(c.title)} · ${d?esc(fmtDate(d))+' — '+SRC_TXT[d.src]:'Unknown'}</p></div><div class="mb">
    <div class="dtrow"><label class="fld"><span>Month</span><select id="dMonth"><option value="0">—</option>${MONTHS.map((m,i)=>`<option value="${i+1}"${d&&d.m===i+1?' selected':''}>${m}</option>`).join('')}</select></label>
    <label class="fld"><span>Year</span><input type="text" id="dYear" inputmode="numeric" maxlength="4" placeholder="1983" value="${d?d.y:''}" autocomplete="off"></label></div>
    <div class="frow" style="margin-top:10px"><button class="btn ghost" id="dLook" type="button">Look Up Online</button><small class="fhint" id="dLookTxt" style="flex:1">${esc(lkSeries(c))}${issueNo(c.title)!=null?' #'+issueNo(c.title):''}</small></div><div id="dLookRes" class="lkres" style="border:0"></div></div>
    <div class="mf">${c.dateManual?'<button class="btn ghost" data-r="clear" id="dClear">Automatic</button>':''}<button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="save" id="dSave">Save</button></div>`,
  w=>{ const y=w.querySelector('#dYear'), b=w.querySelector('#dSave'); const sync=()=>{ const v=+y.value; const ok=/^\d{4}$/.test(y.value)&&v>=1900&&v<=2100; if(b.disabled!==!ok) b.disabled=!ok; };
    y.addEventListener('input',sync); y.addEventListener('keydown',e=>{ if(e.key==='Enter'&&!b.disabled){ e.preventDefault(); b.click(); } }); sync();
    const lb=w.querySelector('#dLook'), res=w.querySelector('#dLookRes');
    const use=async f=>{ if(c.dateManual){ res.innerHTML=`<div class="lkr"><b>${lkTxt(f)}</b><span>Your date is kept</span></div>`; return; } await lkSave(c,f); renderShelf(); res.innerHTML=`<div class="lkr ok"><b>${lkTxt(f)}</b><span>Saved</span></div>`; w.querySelector('.dlsub').textContent=`${c.title} · ${fmtDate(dateOf(c))} — ${SRC_TXT.online}`; };
    lb.addEventListener('click',async()=>{ if(issueNo(c.title)==null){ res.innerHTML='<div class="lkr"><b>No issue number in the title</b></div>'; return; } lb.disabled=true; lb.textContent='Looking up…';
      let r; try{ r=await lkRun(c); }catch(e){ r={error:1}; } lb.disabled=false; lb.textContent='Look Up Online';
      if(r.found) use(r.found);
      else if(r.candidates){ res.innerHTML=`<div class="lkr"><b>Several volumes match — which one?</b></div>`+r.candidates.map((f,i)=>`<div class="lkr"><b>${lkTxt(f)}</b><button class="btn ghost" type="button" data-i="${i}">Use</button></div>`).join('');
        res.querySelectorAll('button[data-i]').forEach(x=>x.addEventListener('click',()=>use(r.candidates[+x.dataset.i]))); }
      else res.innerHTML=`<div class="lkr"><b>${r.error?'Network error — are you online?':'Not found on the comics wikis'}</b></div>`; });
    w._vals=()=>({y:+y.value,m:+w.querySelector('#dMonth').value}); }).then(async({r,vals})=>{ if(r==='save') await setDate(c,vals); else if(r==='clear') await setDate(c,null); }); }
/* ---- online lookup (manual only: Settings button, or Look Up Online in the Release Date sheet) ---- */
const lkSeries=c=>c.series||seriesGuess(c.title)||'';
const lkEligible=c=>{ if(c.dateManual) return false; const d=dateOf(c); return (!d||d.src==='lookup')&&lkSeries(c)&&issueNo(c.title)!=null&&isFinite(issueNo(c.title)); };
async function lkRun(c,signal){ return onlineDate(lkSeries(c),issueNo(c.title),[c.title,c.fileName,c.autoSeries],signal); }
async function lkSave(c,f){ if(c.dateManual) return false; c.onlineDate={y:f.y,m:f.m||0,src:'online',wiki:f.wiki,title:f.title,url:f.url,at:Date.now()}; await dbPut(c); return true; }
const lkTxt=f=>`${f.m?MONTHS[f.m-1].slice(0,3)+' ':''}${f.y} · ${esc(f.wiki)} (${esc(f.title)})`;
async function lookupAll(){ const L=comics.filter(lkEligible); document.querySelector('.mwrap')?.remove(); const ctl=new AbortController(); let done=false;
  const p=modal(`<div class="mh"><h3>Look Up Release Dates</h3><p class="dlsub" id="lkSum">${L.length?`Checking ${L.length} issue${L.length===1?'':'s'} with unknown or estimated dates…`:'Every issue already has a date from its file or from you.'}</p></div>
    <div class="mb"><div class="lkres" id="lkRes"></div><small class="fhint">Source: Fandom comics wikis (Marvel, DC, Image, Dark Horse Databases). Dates you set by hand are never changed.</small></div>
    <div class="mf"><button class="btn" data-r="done" id="lkDone">${L.length?'Stop':'Done'}</button></div>`,null);
  const box=()=>document.querySelector('#lkRes'); let n=0,f=0,amb=0;
  (async()=>{ for(const c of L){ if(ctl.signal.aborted) break; const row=document.createElement('div'); row.className='lkr'; row.innerHTML=`<b>${esc(c.title)}</b><span>Looking up…</span>`; box()&&box().prepend(row);
      let r; try{ r=await lkRun(c,ctl.signal); }catch(e){ r={error:e.message||String(e)}; } if(ctl.signal.aborted) break; n++;
      if(r.found){ await lkSave(c,r.found); f++; row.classList.add('ok'); row.querySelector('span').innerHTML=lkTxt(r.found); }
      else if(r.candidates){ amb++; row.querySelector('span').textContent=`${r.candidates.length} volumes match — pick in Release Date`; }
      else row.querySelector('span').textContent=r.error?'Network error':'Not found';
      const sm=document.querySelector('#lkSum'); if(sm) sm.textContent=`${n} of ${L.length} checked · ${f} found${amb?` · ${amb} need a volume`:''}`; await new Promise(r=>setTimeout(r,250)); }
    done=true; const b=document.querySelector('#lkDone'); if(b) b.textContent='Done'; if(f) renderShelf(); })();
  await p; ctl.abort(); if(f) renderShelf(); }
const TL={on:false};
function tlGroups(){ const by=new Map(), unk=[]; comics.forEach(c=>{ const d=dateOf(c); if(d){ if(!by.has(d.y)) by.set(d.y,[]); by.get(d.y).push({c,d}); } else unk.push(c); });
  const years=[...by.keys()].sort((a,b)=>a-b); years.forEach(y=>by.get(y).sort((a,b)=>(a.d.m||13)-(b.d.m||13)||(a.c.series||'').localeCompare(b.c.series||'')||byIssue(a.c,b.c)));
  return {by,years,unk:unk.sort((a,b)=>(a.series||a.title).localeCompare(b.series||b.title)||byIssue(a,b))}; }
function tlRange(){ const {years}=tlGroups(); return years.length?(years[0]===years.at(-1)?String(years[0]):`${years[0]} – ${years.at(-1)}`):''; }
function renderTimeline(){ const el=$('#tlScroll'); if(!el) return; const {by,years,unk}=tlGroups(), st=el.scrollTop; let h='', ly=null;
  const card=(c,d,lab)=>{ const ym=d?ymOf(d):0, dec=d?Math.floor(d.y/10)*10:'unk';
    return `<div class="tc" data-dec="${dec}" data-ym="${ym}">${lab?`<button class="tyr" data-act="${d?'rack':'noop'}" data-ym="${ym}" aria-label="${d?`Spinner rack, ${lab}`:lab}">${lab}${d?IC.rack:''}</button>`:''}<button class="tcb" data-act="open" data-id="${c.id}" aria-label="${esc(c.title)}${d?', '+esc(fmtDate(d)):''}">${coverBox(c)}<span class="tt">${esc(c.title)}</span><span class="td${d&&d.src==='lookup'?' est':''}">${d?esc(fmtDate(d)):'Unknown date'}</span></button></div>`; };
  for(const y of years) by.get(y).forEach((x,k)=>{ h+=card(x.c,x.d,k===0?String(y):''); });
  unk.forEach((c,k)=>{ h+=card(c,null,k===0?'Unknown':''); });
  const decades=[...new Set(years.map(y=>Math.floor(y/10)*10))];
  $('#tlDec').innerHTML=decades.map(d=>`<button class="chip" data-dec="${d}">${d}s</button>`).join('')+(unk.length?'<button class="chip" data-dec="unk">Unknown</button>':'');
  el.innerHTML=comics.length?`<div class="tlg" id="tlGrid">${h}</div>${unk.length?'<p class="tlhint">Unknown dates: long-press an issue to set one, or use Look Up Release Dates in Settings.</p>':''}`:'<p class="qempty">No comics yet.</p>';
  $('#tlCount').textContent=`${comics.length} issue${comics.length===1?'':'s'}`; el.scrollTop=st; tlSpy(); }
function tlFirstVisible(){ const el=$('#tlScroll'), top=el.getBoundingClientRect().top; for(const c of el.querySelectorAll('.tc')){ const r=c.getBoundingClientRect(); if(r.bottom>top+8) return c; } return null; }
function tlSpy(){ const c=tlFirstVisible(), cur=c&&c.dataset.dec; $('#tlDec').querySelectorAll('.chip').forEach(b=>{ const on=b.dataset.dec===cur; if(b.classList.contains('on')!==on){ b.classList.toggle('on',on); if(on) b.scrollIntoView({inline:'nearest',block:'nearest'}); } }); }
function openTimeline(){ setTab('timeline'); }
function closeTimeline(){ if(TL.on) setTab('home'); }
$('#tlScroll').addEventListener('scroll',()=>requestAnimationFrame(tlSpy),{passive:true});
$('#tlDec').addEventListener('click',e=>{ const b=e.target.closest('[data-dec]'); if(!b) return; const el=$('#tlScroll'), s=el.querySelector(`.tc[data-dec="${b.dataset.dec}"]`); if(s) el.scrollTo({top:Math.max(0,s.offsetTop-8),behavior:reduced()?'auto':'smooth'}); });
$('#tlRack').addEventListener('click',()=>{ const c=tlFirstVisible(); let ym=c&&+c.dataset.ym; if(!ym){ const d=comics.map(dateOf).filter(Boolean).map(ymOf).sort((a,b)=>a-b); ym=d[Math.floor((d.length-1)/2)]; } if(ym) openRack(ym); else toast('Set a release date on some issues first'); });

/* ---------- spinner rack (v25): the issues that were "on the racks" around a month ---------- */
const ymOf=d=>d.y*12+((d.m||6)-1);            // year-only dates count as June
const ymLabel=i=>`${MONTHS[i%12].slice(0,3)} ${Math.floor(i/12)}`;
function rackCenter(list){ const v=list.map(x=>ymOf(x.d)).sort((a,b)=>a-b); return v[Math.floor((v.length-1)/2)]; }
const RK={on:false,ym:0,win:0,items:[],N:6,T:8,a:0,v:0,raf:0,drag:null,step:60,front:0};
const rmq=matchMedia('(prefers-reduced-motion: reduce)'); const reduced=()=>rmq.matches;
const TILT=16;   // covers lean back in their wire pockets
// every pocket filled: nearest dates first (outward from the month), then undated issues; repeats only if the library is smaller than the rack
function rackItems(ym,cap){ const all=comics.map(c=>({c,d:dateOf(c)})); const dated=all.filter(x=>x.d).map(x=>({...x,i:ymOf(x.d)})), und=all.filter(x=>!x.d);
  dated.sort((a,b)=>Math.abs(a.i-ym)-Math.abs(b.i-ym)||a.i-b.i||(a.c.series||'').localeCompare(b.c.series||'')||byIssue(a.c,b.c));
  let L=dated.concat(und.sort((a,b)=>(a.c.series||a.c.title).localeCompare(b.c.series||b.c.title)||byIssue(a.c,b.c)));
  const uniq=L.length; if(!uniq) return {L:[],uniq:0,lo:0,hi:0,repeats:false}; const out=[]; for(let k=0;k<cap;k++) out.push(L[k%uniq]);
  const used=out.slice(0,Math.min(cap,uniq)).filter(x=>x.d).map(x=>x.i); return {L:out,uniq:Math.min(cap,uniq),lo:Math.min(...used,ym),hi:Math.max(...used,ym),repeats:uniq<cap}; }
// wing order: front first, then alternating right/left so the nearest dates sit in front
const wingOrder=N=>{ const o=[0]; for(let k=1;o.length<N;k++){ o.push(k); if(o.length<N) o.push(N-k); } return o; };
function rackLayout(){ const st=$('#rkStage'), W=st.clientWidth, H=st.clientHeight, T=RK.T;
  let ph=(H*.9)/((T-1)*.55+1+.62+.3), pw=ph/1.54; if(pw*3.3>W*.96){ pw=W*.96/3.3; ph=pw*1.54; }
  const pitch=ph*.55, sign=ph*.62, base=ph*.3, R=pw*.95+8, rackH=(T-1)*pitch+ph;
  Object.assign(RK,{pw,ph,pitch,R,sign});
  const sc=$('#rkScene'); Object.entries({'--pw':pw+'px','--ph':ph+'px','--pitch':pitch+'px','--R':R+'px','--sign':sign+'px','--base':base+'px','--rh':rackH+'px'}).forEach(([k,v])=>sc.style.setProperty(k,v));
  sc.style.height=(sign+rackH+base)+'px'; st.style.perspective=Math.max(900,ph*7)+'px';
  for(const e of RK.els||[]) e._tf=null; rackApply(); }
function renderRack(){ const cap=RK.N*RK.T, {L,uniq,lo,hi,repeats}=rackItems(RK.ym,cap); RK.items=L.map(x=>x.c); RK.win=Math.max(RK.ym-lo,hi-RK.ym); RK.step=360/RK.N; RK.a=0; RK.v=0; RK.repeats=repeats;
  $('#rkTitle').textContent=`On the racks · ${ymLabel(RK.ym)}`;
  const sh=i=>innerWidth<560?`${MONTHS[i%12].slice(0,3)} ’${String(Math.floor(i/12)).slice(2)}`:ymLabel(i);
  $('#rkSub').textContent=uniq?`${uniq} issue${uniq===1?'':'s'} · ${lo===hi?sh(lo):`${sh(lo)} – ${sh(hi)}`}${repeats?(innerWidth<560?' · repeats':' · repeats to fill'):''}`:'No comics yet';
  const ord=wingOrder(RK.N); let h=''; for(let w=0;w<RK.N;w++) h+=`<div class="wing" data-w="${w}"></div>`;
  L.forEach((x,k)=>{ const w=ord[Math.floor(k/RK.T)], t=k%RK.T; h+=`<div class="pk" data-w="${w}" data-t="${t}"><button class="pkc" data-rk="${x.c.id}" aria-label="${esc(x.c.title)}${x.d?', '+esc(fmtDate(x.d)):''}"><img src="${cover(x.c)}" alt="" draggable="false"></button></div>`; });
  $('#rkRotor').innerHTML=h+'<div class="rkpole"></div><div class="rksign"><span>COMICS</span></div>'; $('#rkEmpty').classList.toggle('hidden',uniq>0);
  RK.els=[...$('#rkRotor').querySelectorAll('.pk,.wing')]; rackLayout(); rackApply(); }
function rackApply(){ const a=RK.a;
  // every pocket gets its full transform (wing angle + spin) so the rack is right even where nested preserve-3d gets flattened
  RK.front=((Math.round(-a/RK.step)%RK.N)+RK.N)%RK.N;
  // depth order + hide the far side in JS as well (works even where 3D depth sorting / backface culling is flaky)
  for(const e of RK.els||[]){ const c=Math.cos((+e.dataset.w*RK.step+a)*Math.PI/180), vis=c>-0.55, isW=e.classList.contains('wing');
    if(e._v!==vis){ e._v=vis; e.style.visibility=vis?'':'hidden'; }
    if(vis){ const ang=+e.dataset.w*RK.step+a; e.style.transform=isW?`rotateY(${ang}deg) translateZ(${RK.R-3}px)`:`rotateY(${ang}deg) translateZ(${RK.R}px) translateY(${+e.dataset.t*RK.pitch}px) rotateX(${TILT}deg)`; } const z=1000+Math.round(c*400)+(isW?-50:+e.dataset.t); if(e._z!==z){ e._z=z; e.style.zIndex=z; }
    if(!isW){ const dim=c<.75; if(e._d!==dim){ e._d=dim; e.classList.toggle('dim',dim); } const f=c>.97; if(e._f!==f){ e._f=f; e.classList.toggle('front',f); } } } }
function rackSnap(){ cancelAnimationFrame(RK.raf); const tgt=Math.round(RK.a/RK.step)*RK.step;
  if(reduced()){ RK.a=tgt; RK.v=0; rackApply(); return; } const a0=RK.a, t0=performance.now(), D=320;
  const f=t=>{ const k=Math.min(1,(t-t0)/D), e=1-Math.pow(1-k,3); RK.a=a0+(tgt-a0)*e; rackApply(); if(k<1) RK.raf=requestAnimationFrame(f); else RK.raf=0; }; RK.raf=requestAnimationFrame(f); }
function rackCoast(){ cancelAnimationFrame(RK.raf); let last=performance.now();
  const f=t=>{ const dt=Math.min(40,t-last); last=t; RK.a+=RK.v*dt; RK.v*=Math.pow(.925,dt/16); rackApply(); if(Math.abs(RK.v)>.02) RK.raf=requestAnimationFrame(f); else { RK.raf=0; rackSnap(); } };
  RK.raf=requestAnimationFrame(f); }
function rackSpin(dir){ cancelAnimationFrame(RK.raf); RK.raf=0; const t=Math.round(RK.a/RK.step)*RK.step+dir*RK.step; if(reduced()){ RK.a=t; rackApply(); } else rackSnapTo(t); }
function rackSnapTo(t){ cancelAnimationFrame(RK.raf); const a0=RK.a,t0=performance.now(),D=420; const f=x=>{ const k=Math.min(1,(x-t0)/D), e=1-Math.pow(1-k,3); RK.a=a0+(t-a0)*e; rackApply(); if(k<1) RK.raf=requestAnimationFrame(f); else RK.raf=0; }; RK.raf=requestAnimationFrame(f); }
function openRack(ym){ if(!(ym>0)) return; RK.on=true; RK.ym=ym; $('#rack').classList.remove('hidden'); renderRack(); }
function closeRack(){ RK.on=false; cancelAnimationFrame(RK.raf); RK.raf=0; const r=$('#rack'); if(r){ r.classList.add('hidden'); $('#rkRotor').innerHTML=''; } document.querySelectorAll('.rkpull').forEach(e=>e.remove()); }
function rackPull(btn){ if(RK.pulling||(R&&R.comic)) return; const id=btn.dataset.rk, img=btn.querySelector('img'), r=img.getBoundingClientRect();
  if(reduced()||!r.width){ RK.pulling=id; openReader(id); setTimeout(()=>RK.pulling=null,400); return; }
  const cl=document.createElement('img'); cl.className='rkpull'; cl.src=img.src; Object.assign(cl.style,{left:r.left+'px',top:r.top+'px',width:r.width+'px',height:r.height+'px'}); document.body.appendChild(cl);
  btn.classList.add('pulled'); const W=innerWidth,H=innerHeight, s=Math.min(W*.7/r.width,H*.7/r.height), dx=W/2-(r.left+r.width/2), dy=H/2-(r.top+r.height/2);
  cl.getBoundingClientRect(); cl.style.transform=`translate(${dx}px,${dy-r.height*.15}px) translateZ(0) scale(${s})`; RK.pulling=id;
  setTimeout(()=>{ openReader(id); setTimeout(()=>{ cl.remove(); btn.classList.remove('pulled'); RK.pulling=null; },400); },380); }
{ const st=$('#rkStage');
  st.addEventListener('pointerdown',e=>{ if(e.button>0||e.target.closest('.rkspin')) return; cancelAnimationFrame(RK.raf); RK.raf=0; RK.v=0; RK.drag={x:e.clientX,y:e.clientY,a:RK.a,t:performance.now(),lx:e.clientX,moved:false,id:e.pointerId,tgt:e.target.closest('.pkc')}; try{ st.setPointerCapture(e.pointerId); }catch(_){} });
  st.addEventListener('pointermove',e=>{ const d=RK.drag; if(!d||e.pointerId!==d.id) return; const dx=e.clientX-d.x; if(Math.abs(dx)>8||Math.abs(e.clientY-d.y)>8) d.moved=true; if(!d.moved) return;
    const now=performance.now(), deg=(st.clientWidth>0?180/Math.max(320,st.clientWidth*.9):.3); RK.a=d.a+dx*deg; const dt=Math.max(1,now-d.t); RK.v=Math.max(-1.1,Math.min(1.1,.7*RK.v+.3*((e.clientX-d.lx)*deg/dt))); d.t=now; d.lx=e.clientX; rackApply(); });
  const up=e=>{ const d=RK.drag; if(!d||e.pointerId!==d.id) return; RK.drag=null;
    if(!d.moved){ const pk=d.tgt&&d.tgt.closest('.pk'); if(pk&&pk.classList.contains('front')) rackPull(d.tgt); else if(pk){ const f=+pk.dataset.w, t=-f*RK.step, k=Math.round((RK.a-t)/360); if(reduced()){ RK.a=t+k*360; rackApply(); } else rackSnapTo(t+k*360); } return; }
    if(performance.now()-d.t>90) RK.v=0; if(reduced()||Math.abs(RK.v)<.05) rackSnap(); else rackCoast(); };
  st.addEventListener('pointerup',up); st.addEventListener('pointercancel',up);
  $('#rkBack').addEventListener('click',closeRack);
  $('#rkPrev').addEventListener('click',()=>{ RK.ym--; renderRack(); }); $('#rkNext').addEventListener('click',()=>{ RK.ym++; renderRack(); });
  $('#rkLeft').addEventListener('click',()=>rackSpin(1)); $('#rkRight').addEventListener('click',()=>rackSpin(-1));
  addEventListener('resize',()=>{ if(RK.on) rackLayout(); });
  addEventListener('keydown',e=>{ if(!RK.on||(R&&R.comic)) return; if(e.key==='ArrowLeft') rackSpin(1); else if(e.key==='ArrowRight') rackSpin(-1); else if(e.key==='Escape') closeRack(); }); }

/* ---------- multi-select (Library and series pages): Select -> tap covers -> Move to Series… / Remove from Series ---------- */
const SEL={on:false,ids:new Set()};
const visIds=()=>libList().map(c=>c.id);
function enterSel(){ if(ui.tab!=='library'||!comics.length) return; SEL.on=true; SEL.ids.clear(); $('#shelf').classList.add('selecting'); $('#selBar').classList.remove('hidden');
  const b=$('#selBtn'); b.querySelector('.lbl').textContent='Done'; b.setAttribute('aria-pressed','true'); cancelLP(); syncSel(); }
function exitSel(){ SEL.on=false; SEL.ids.clear(); $('#shelf').classList.remove('selecting'); $('#selBar').classList.add('hidden'); const b=$('#selBtn'); b.querySelector('.lbl').textContent='Select'; b.setAttribute('aria-pressed','false');
  document.querySelectorAll('#libGrid .lc.on').forEach(x=>x.classList.remove('on')); }
function toggleSel(id){ if(SEL.ids.has(id)) SEL.ids.delete(id); else SEL.ids.add(id); syncSel(); }
function syncSel(){ const vis=visIds(); for(const id of [...SEL.ids]) if(!comics.some(c=>c.id===id)) SEL.ids.delete(id);
  document.querySelectorAll('#libGrid .lc').forEach(x=>{ const on=SEL.ids.has(x.dataset.id); x.classList.toggle('on',on); x.setAttribute('aria-pressed',on); });
  const n=SEL.ids.size, all=vis.length>0&&vis.every(id=>SEL.ids.has(id));
  $('#selCount').textContent=`${n} selected`; $('#selAll').textContent=all?'Select None':'Select All';
  $('#selMove').disabled=!n; $('#selRemove').disabled=!comics.some(c=>SEL.ids.has(c.id)&&(c.seriesManual||c.series)); }
$('#selBtn').addEventListener('click',()=>SEL.on?exitSel():enterSel());
$('#selAll').addEventListener('click',()=>{ const vis=visIds(); if(vis.length&&vis.every(id=>SEL.ids.has(id))) vis.forEach(id=>SEL.ids.delete(id)); else vis.forEach(id=>SEL.ids.add(id)); syncSel(); });
$('#selMove').addEventListener('click',()=>moveToSeries([...SEL.ids]));
$('#selRemove').addEventListener('click',()=>removeFromSeries([...SEL.ids]));
const volName=(n,v)=>{ n=n.trim().replace(/\s+/g,' '); v=String(v||'').trim().replace(/^vol(?:ume)?\.?\s*/i,''); return v?`${n} Vol. ${v}`:n; };
// after a move: a series page whose series emptied follows its comics to the destination
function afterSeriesChange(to){ if(ui.series!=null&&!comics.some(c=>(c.series||'')===ui.series)) ui.series=to||null; exitSel(); renderShelf(); }
async function moveToSeries(ids){ const L=comics.filter(c=>ids.includes(c.id)); if(!L.length) return; document.querySelector('.mwrap')?.remove();
  const S=seriesCounts(), from=new Set(L.map(c=>c.series||''));
  const {r,vals}=await modal(`<div class="mh"><h3>Move to Series</h3><p class="dlsub">${L.length} comic${L.length===1?'':'s'} selected</p></div>
    <div class="dllist" id="mvList">${S.map(([s,n],i)=>`<label class="mvr"><input type="radio" name="mvs" value="${i}"><span class="ckt"><b>${esc(s)}</b><small>${n} comic${n===1?'':'s'}${from.has(s)?' · current':''}</small></span></label>`).join('')}
      <label class="mvr"><input type="radio" name="mvs" value="new" id="mvNewR" ${S.length?'':'checked'}><span class="ckt"><b>New Series…</b><small>Name and optional volume</small></span></label>
      <div class="mvnew" id="mvNew"><input type="text" id="mvName" placeholder="Series name, e.g. Uncanny X-Men" maxlength="80" autocomplete="off" autocapitalize="words" aria-label="New series name"><input type="text" id="mvVol" placeholder="Vol." maxlength="8" inputmode="numeric" autocomplete="off" aria-label="Volume (optional)"></div>
      <div class="mvprev" id="mvPrev"></div></div>
    <div class="mf"><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="go" id="mvGo" disabled>Move</button></div>`,
  w=>{ const go=w.querySelector('#mvGo'), nm=w.querySelector('#mvName'), vo=w.querySelector('#mvVol'), pv=w.querySelector('#mvPrev');
    const target=()=>{ const r=w.querySelector('input[name=mvs]:checked'); if(!r) return ''; if(r.value==='new') return nm.value.trim()?canonSeries(volName(nm.value,vo.value)):''; return S[+r.value][0]; };
    const sync=()=>{ const t=target(), same=t&&L.every(c=>(c.series||'')===t); go.disabled=!t||same; const gt=t&&!same?`Move ${L.length}`:'Move', pt=t?(same?'Already in this series.':`→ “${t}”${seriesCounts().some(([s])=>s===t)?' (existing series)':' (new series)'}`):'';
      if(go.textContent!==gt) go.textContent=gt; if(pv.textContent!==pt) pv.textContent=pt; };   // don't touch the button's text node when nothing changed: a tap that blurs the field would lose its click (WebKit)
    [nm,vo].forEach(i=>{ i.addEventListener('focus',()=>{ w.querySelector('#mvNewR').checked=true; sync(); }); i.addEventListener('input',sync); i.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); if(!go.disabled) go.click(); } }); });
    w.addEventListener('change',sync); w._vals=()=>({to:target()}); sync(); },'drv ckm mvm');
  if(r!=='go'||!vals.to) return; const to=vals.to; let n=0;
  for(const c of L){ if((c.series||'')===to) continue; setSeriesManual(c,to); await dbPut(c); n++; }
  afterSeriesChange(to); toast(`Moved ${n} comic${n===1?'':'s'} to “${to}”`); }
async function removeFromSeries(ids){ const L=comics.filter(c=>ids.includes(c.id)); let n=0;
  for(const c of L){ clearSeriesManual(c); await dbPut(c); n++; }
  afterSeriesChange(null); toast(`${n} comic${n===1?'':'s'} back to automatic series`); }

/* ---------- toast ---------- */
let toastEl=null,toastT=0;
function toast(msg,{progress=null,sticky=false}={}){ if(!toastEl){ toastEl=document.createElement('div'); toastEl.className='toast'; toastEl.setAttribute('role','status'); document.body.appendChild(toastEl); }
  toastEl.innerHTML=esc(msg)+(progress!=null?`<div class="tb"><i style="width:${Math.round(progress*100)}%"></i></div>`:'');
  clearTimeout(toastT); if(!sticky) toastT=setTimeout(hideToast,2600); }
function hideToast(){ if(toastEl){ toastEl.remove(); toastEl=null; } }

/* ---------- import (validate + cover from the picked File, then copy into IndexedDB in chunks) ---------- */
let importing=false;
async function importFiles(files){
  if(importing){ toast('Already importing…'); return; } importing=true;
  try{ if(navigator.storage&&navigator.storage.persist) navigator.storage.persist().catch(()=>{}); }catch(e){}
  let ok=0;
  for(let k=0;k<files.length;k++){ const f=files[k]; const tag=files.length>1?` (${k+1}/${files.length})`:'';
    if(!(f.type==='application/pdf'||/\.pdf$/i.test(f.name))){ toast(`Skipped “${f.name}” — not a PDF`); continue; }
    const id=uid(); let doc=null;
    try{
      toast(`Reading ${f.name}${tag}…`,{progress:0,sticky:true});
      doc=await openPdf(new FileSource(f));
      await doc.getPage(1); await doc.destroy(); doc=null;          // validate before copying
      const n=Math.ceil(f.size/CHUNK);
      for(let i=0;i<n;i++){ const ab=await f.slice(i*CHUNK,Math.min(f.size,(i+1)*CHUNK)).arrayBuffer(); await dbPutChunk(id,i,ab);
        toast(`Saving ${f.name}${tag}…`,{progress:(i+1)/n,sticky:true}); }
      doc=await openPdf(new IDBSource(id,f.size));                    // cover from the stored copy (same path as Drive import/migration)
      const meta=await coverMeta(doc); const pages=doc.numPages; await doc.destroy(); doc=null;
      const t0=titleFromName(f.name); const rec=withSeriesOverride({id,title:t0,series:seriesGuess(t0),fileName:f.name,size:f.size,pages,...meta,added:Date.now()+k,lastRead:0,page:0,progress:0,rtl:false});
      await dbPut(rec); comics.push(rec); ok++; renderShelf();
    }catch(err){ console.warn('import failed',err); try{ if(doc) await doc.destroy(); }catch(e){} try{ await dbDelete(id); }catch(e){}
      const quota=err&&(err.name==='QuotaExceededError'||/quota/i.test(err.message||''));
      toast(quota?`Out of storage space importing “${f.name}”.`:`Couldn't import “${f.name}”: ${err&&err.message||'not a valid PDF'}`); await new Promise(r=>setTimeout(r,1800)); }
  }
  importing=false; if(ok) toast(`Imported ${ok} comic${ok>1?'s':''} ✓`); renderShelf(); if(ok) kickBlack();
}

