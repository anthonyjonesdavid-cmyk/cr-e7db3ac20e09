
/* ================= Shelf: Home (coverflow + rows) and Library (grid) ================= */
let comics=[]; const coverURL=new Map();
const ui={tab:store.get('tab','home'), sort:store.get('sort','recent'), filter:'all', series:null, q:''};
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
  grid:'<svg class="i" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 10h18M12 10v11"/></svg>',
};
function cover(c){ if(!c.cover) return ''; let u=coverURL.get(c.id); if(!u){ u=URL.createObjectURL(c.cover instanceof Blob?c.cover:new Blob([c.cover],{type:'image/jpeg'})); coverURL.set(c.id,u); } return u; }
const pctOf=c=>c.pages?Math.round(clamp(c.progress||0,0,1)*100):0;
const isDone=c=>(c.progress||0)>=1, isUnread=c=>!c.lastRead&&!((c.progress||0)>0), inProg=c=>!isDone(c)&&!isUnread(c);
const byTitle=(a,b)=>a.title.localeCompare(b.title,undefined,{numeric:true,sensitivity:'base'});
function seriesGuess(t){ const s=t.replace(/[([].*?[)\]]/g,' ').replace(/\s+/g,' ').trim();
  const m=s.match(/^(.*?)[\s,_-]*(?:#|no\.?\s*|issue\s*|vol(?:ume)?\.?\s*|v|ch(?:apter)?\.?\s*|book\s*)?(\d{1,4})(?:\s*of\s*\d+)?$/i);
  return m&&m[1].trim().length>=2&&/[a-z]/i.test(m[1])? m[1].replace(/[\s,_#-]+$/,'').trim() : ''; }
async function loadLibrary(){ comics=await dbAll(); renderShelf(); }
function renderShelf(){ renderHome(); renderLibrary(); renderPill(); setTab(ui.tab); }
function setTab(t){ ui.tab=t; store.set('tab',t); document.querySelectorAll('#tabs button').forEach(b=>{ b.classList.toggle('on',b.dataset.tab===t); b.setAttribute('aria-selected',b.dataset.tab===t); });
  $('#home').classList.toggle('hidden',t!=='home'); $('#library').classList.toggle('hidden',t!=='library'); if(t==='home') CF.size(); }
$('#tabs').addEventListener('click',e=>{ const b=e.target.closest('button'); if(b) setTab(b.dataset.tab); });

const coverBox=c=>`<div class="cvr"><img src="${cover(c)}" alt="" decoding="async" loading="lazy" draggable="false">${isDone(c)?`<span class="done" aria-label="Finished">${IC.check}</span>`:''}</div>${inProg(c)?`<div class="pl"><i style="width:${Math.max(2,pctOf(c))}%"></i></div>`:'<div class="pl none"></div>'}`;
const emptyHTML=()=>`<div class="empty">${IC.book}<h2>No comics yet</h2><p>Import PDF comics from Google Drive or the Files app. They're stored on this device only and never uploaded.</p><div class="ebtns"><button class="pillbtn" data-act="drive">From Google Drive</button><button class="pillbtn ghost" data-act="import">From Files</button></div></div>`;

/* ---------- Home ---------- */
function rowHTML(title,list,kind,series){ if(!list.length) return ''; const see=`data-act="see" data-kind="${kind}"${series!=null?` data-series="${esc(series)}"`:''}`;
  return `<section class="row"><button class="row-h" ${see}><h2>${esc(title)}</h2><span class="n">${list.length}</span>${IC.chev}</button>
  <div class="row-s">${list.slice(0,20).map(c=>`<button class="rc" data-act="open" data-id="${c.id}" aria-label="${esc(c.title)}">${coverBox(c)}<div class="t">${esc(c.title)}</div></button>`).join('')}<button class="seeall" ${see}>${IC.grid}See all</button></div></section>`; }
function renderHome(){
  const el=$('#homeScroll'); if(!comics.length){ el.innerHTML=emptyHTML(); Drive.preload(); CF.items=[]; CF.el=null; return; }
  let cf=comics.filter(c=>c.lastRead).sort((a,b)=>b.lastRead-a.lastRead).slice(0,12);
  if(cf.length<7) cf=cf.concat(comics.filter(c=>!c.lastRead).sort((a,b)=>b.added-a.added).slice(0,9-cf.length));
  const groups=new Map(); comics.forEach(c=>{ const s=(c.series||'').trim(); if(s){ if(!groups.has(s)) groups.set(s,[]); groups.get(s).push(c); } });
  let rows=rowHTML('Recently Added',comics.slice().sort((a,b)=>b.added-a.added),'added');
  [...groups.keys()].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true})).forEach(s=>{ rows+=rowHTML(s,groups.get(s).sort(byTitle),'series',s); });
  rows+=rowHTML('Unread',comics.filter(isUnread).sort(byTitle),'unread')+rowHTML('Finished',comics.filter(isDone).sort((a,b)=>b.lastRead-a.lastRead),'finished');
  el.innerHTML=`<div class="hero"><div class="cf" id="cf" aria-label="Recently read">${cf.map((c,i)=>`<div class="cf-item" data-i="${i}" data-id="${c.id}"><img src="${cover(c)}" alt="${esc(c.title)}" draggable="false"><div class="dim"></div></div>`).join('')}</div><div class="cf-info" id="cfInfo"></div></div><div class="rows">${rows}</div>`;
  CF.mount($('#cf'),cf);
}

/* ---------- 3D coverflow: touch-tracked, momentum, snaps to center ---------- */
const CF={items:[],pos:0,el:null,cw:240,sp:180,raf:0,shown:-1,
  mount(el,items){ this.el=el; this.items=items; this.pos=0; this.shown=-1; this.size(); this.bind(); },
  size(){ if(!this.el||!this.el.isConnected) return; const vw=innerWidth, vh=innerHeight;
    this.cw=Math.round(vw<600? Math.min(vw*.46,vh*.3) : Math.min(290,vw*.3,vh*.33)); this.sp=this.cw*.8; this.el.style.setProperty('--cw',this.cw+'px'); this.layout(); },
  layout(){ if(!this.el) return; const kids=this.el.children, cw=this.cw;
    for(let k=0;k<kids.length;k++){ const it=kids[k], o=k-this.pos, ao=Math.abs(o);
      if(ao>5){ it.style.visibility='hidden'; continue; } it.style.visibility='';
      const s=Math.sign(o), a=Math.min(ao,1), x=s*(a*cw*.8+Math.max(0,ao-1)*cw*.3);
      const z=-a*cw*.55-Math.max(0,ao-1)*cw*.2, rot=-clamp(o,-1,1)*52, sc=1-a*.1;
      it.style.transform=`translateX(${x.toFixed(1)}px) translateZ(${z.toFixed(1)}px) rotateY(${rot.toFixed(2)}deg) scale(${sc.toFixed(3)})`;
      it.style.zIndex=1000-Math.round(ao*100); it.lastChild.style.opacity=Math.min(.82,a*.42+Math.max(0,ao-1)*.16).toFixed(3);
      it.classList.toggle('far',ao>.55); }
    this.info(); },
  info(){ const i=clamp(Math.round(this.pos),0,this.items.length-1); if(i===this.shown) return; this.shown=i; const c=this.items[i], box=$('#cfInfo'); if(!c||!box) return;
    box.innerHTML=`<div class="cf-kick">${c.lastRead?'Continue Reading':'Recently Added'}</div><div class="cf-title">${esc(c.title)}</div><div class="cf-sub">${c.lastRead?`Page ${(c.page||0)+1} of ${c.pages}${isDone(c)?' · Finished':''}`:`${c.pages} pages`}</div><div class="cf-prog"><i style="width:${pctOf(c)}%"></i></div><button class="pillbtn" data-act="open" data-id="${c.id}">${c.lastRead&&!isDone(c)?'Continue':'Read'}</button>`; },
  stop(){ cancelAnimationFrame(this.raf); this.raf=0; },
  to(target,dur){ this.stop(); const from=this.pos, t0=performance.now(); target=clamp(target,0,this.items.length-1);
    const step=now=>{ const k=Math.min(1,(now-t0)/dur), e=1-Math.pow(1-k,3); this.pos=from+(target-from)*e; this.layout(); if(k<1) this.raf=requestAnimationFrame(step); else { this.raf=0; this.pos=target; this.layout(); } };
    this.raf=requestAnimationFrame(step); },
  bind(){ const el=this.el; let d=null;
    el.addEventListener('pointerdown',e=>{ if(e.button>0) return; this.stop(); d={id:e.pointerId,x0:e.clientX,y0:e.clientY,p0:this.pos,drag:false,s:[[e.timeStamp,e.clientX]],t0:e.timeStamp}; });
    el.addEventListener('pointermove',e=>{ if(!d||e.pointerId!==d.id) return; const dx=e.clientX-d.x0, dy=e.clientY-d.y0;
      if(!d.drag){ if(Math.abs(dx)>7&&Math.abs(dx)>Math.abs(dy)){ d.drag=true; cancelLP(); try{el.setPointerCapture(e.pointerId)}catch(_){} } else if(Math.abs(dy)>10){ d=null; return; } else return; }
      d.s.push([e.timeStamp,e.clientX]); if(d.s.length>6) d.s.shift();
      let p=d.p0-dx/this.sp; const n=this.items.length-1; if(p<0) p*=.35; else if(p>n) p=n+(p-n)*.35; this.pos=p; this.layout(); });
    const end=(e,cancel)=>{ if(!d||e.pointerId!==d.id) return; const g=d; d=null;
      if(g.drag){ const s=g.s, a=s[0], b=s[s.length-1]; const v=(b[0]-a[0])>0&&(e.timeStamp-b[0])<90? (b[1]-a[1])/(b[0]-a[0]) : 0;   // px/ms
        const target=Math.round(this.pos-(v*260)/this.sp); const dist=Math.abs(target-this.pos); this.to(target,clamp(280+dist*110,300,900)); return; }
      if(cancel||lpFired) return; if(e.timeStamp-g.t0>600) return;
      const it=e.target.closest('.cf-item'); if(!it) return; const i=+it.dataset.i;
      if(i===Math.round(this.pos)) openReader(it.dataset.id); else this.to(i,420); };
    el.addEventListener('pointerup',e=>end(e,false)); el.addEventListener('pointercancel',e=>end(e,true));
    let wt=0; el.addEventListener('wheel',e=>{ if(Math.abs(e.deltaX)<=Math.abs(e.deltaY)) return; e.preventDefault(); this.stop(); const n=this.items.length-1;
      this.pos=clamp(this.pos+e.deltaX/this.sp,-.3,n+.3); this.layout(); clearTimeout(wt); wt=setTimeout(()=>this.to(Math.round(this.pos),300),120); },{passive:false}); }
};
addEventListener('resize',()=>{ clearTimeout(CF.rt); CF.rt=setTimeout(()=>CF.size(),80); });

/* ---------- Library ---------- */
const FILTERS=[['all','All'],['unread','Unread'],['progress','In Progress'],['finished','Finished']];
const SORTS={recent:'Recent',title:'Title',added:'Date Added',series:'Series'};
function libList(){ const q=ui.q.trim().toLowerCase(); let L=comics.filter(c=>(ui.series==null||(c.series||'')===ui.series)&&(!q||c.title.toLowerCase().includes(q)||(c.series||'').toLowerCase().includes(q)));
  if(ui.filter==='unread') L=L.filter(isUnread); else if(ui.filter==='progress') L=L.filter(inProg); else if(ui.filter==='finished') L=L.filter(isDone);
  if(ui.sort==='title') L.sort(byTitle); else if(ui.sort==='added') L.sort((a,b)=>b.added-a.added);
  else if(ui.sort==='series') L.sort((a,b)=>(!a.series)-(!b.series)||(a.series||'').localeCompare(b.series||'',undefined,{numeric:true})||byTitle(a,b));
  else L.sort((a,b)=>(b.lastRead||0)-(a.lastRead||0)||b.added-a.added);
  return L; }
const letterOf=t=>{ const ch=(t||'').trim().charAt(0).toUpperCase(); return /[A-Z]/.test(ch)?ch:'#'; };
function renderLibrary(){
  $('#sortLbl').textContent=SORTS[ui.sort];
  $('#chips').innerHTML=(ui.series!=null?`<button class="chip scope" data-act="unscope" aria-label="Clear series">${IC.x}${esc(ui.series||'No series')}</button>`:'')+FILTERS.map(([k,l])=>`<button class="chip${ui.filter===k?' on':''}" data-act="filter" data-f="${k}">${l}</button>`).join('');
  const grid=$('#libGrid'), az=$('#azIndex');
  if(!comics.length){ grid.innerHTML=''; $('#libScroll').firstElementChild.style.display='none'; if(!$('#libScroll .empty')) $('#libScroll').insertAdjacentHTML('beforeend',emptyHTML()); az.classList.add('hidden'); $('#library .libbar').classList.add('hidden'); return; }
  $('#library .libbar').classList.remove('hidden'); $('#libScroll .empty')?.remove(); grid.style.display='';
  const L=libList(); const seen=new Set();
  grid.innerHTML=L.length? L.map(c=>{ const l=letterOf(c.title); const first=ui.sort==='title'&&!seen.has(l)&&(seen.add(l),true);
    return `<button class="lc" data-act="open" data-id="${c.id}" data-title="${esc(c.title)}" aria-label="${esc(c.title)}"${first?` data-letter="${l}"`:''}>${coverBox(c)}</button>`; }).join('')
    : `<div class="lempty" style="grid-column:1/-1">No comics here${ui.q?` matching “${esc(ui.q)}”`:''}.</div>`;
  const showAZ=ui.sort==='title'&&L.length>0; az.classList.toggle('hidden',!showAZ); grid.style.setProperty('--azw',showAZ?'14px':'0px');
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

/* ---------- now-reading pill ---------- */
function renderPill(){ const p=$('#nowPill'); const c=comics.filter(x=>x.lastRead&&!isDone(x)).sort((a,b)=>b.lastRead-a.lastRead)[0];
  if(!c){ p.classList.add('hidden'); return; } p.classList.remove('hidden'); p.dataset.id=c.id; const pc=pctOf(c);
  p.innerHTML=`<img src="${cover(c)}" alt=""><div class="np"><b>${esc(c.title)}</b><span>Page ${(c.page||0)+1} of ${c.pages}</span></div><span class="pct">${pc}%</span>${IC.play}<i class="npl" style="width:${pc}%"></i>`; }
$('#nowPill').addEventListener('click',()=>{ const id=$('#nowPill').dataset.id; if(id) openReader(id); });

/* ---------- clicks, long-press & context menu ---------- */
let lp=null, lpFired=false;
function cancelLP(){ if(lp){ clearTimeout(lp.t); lp=null; } }
const shelfEl=$('#shelf');
shelfEl.addEventListener('pointerdown',e=>{ lpFired=false; const t=e.target.closest('[data-id]:not(#nowPill)'); if(!t||e.button>0) return; cancelLP();
  lp={x:e.clientX,y:e.clientY,t:setTimeout(()=>{ lp=null; lpFired=true; try{navigator.vibrate&&navigator.vibrate(8)}catch(_){} actionSheet(t.dataset.id); },520)}; });
shelfEl.addEventListener('pointermove',e=>{ if(lp&&Math.hypot(e.clientX-lp.x,e.clientY-lp.y)>9) cancelLP(); });
shelfEl.addEventListener('pointerup',cancelLP); shelfEl.addEventListener('pointercancel',cancelLP);
shelfEl.addEventListener('scroll',cancelLP,true);
shelfEl.addEventListener('contextmenu',e=>{ const t=e.target.closest('[data-id]:not(#nowPill)'); e.preventDefault(); if(t&&!lpFired){ cancelLP(); lpFired=true; actionSheet(t.dataset.id); } });
shelfEl.addEventListener('click',e=>{ if(lpFired){ lpFired=false; e.preventDefault(); e.stopPropagation(); return; }
  const a=e.target.closest('[data-act]'); if(!a) return; const k=a.dataset.act;
  if(k==='open') openReader(a.dataset.id); else if(k==='see') seeAll(a.dataset.kind,a.dataset.series);
  else if(k==='filter'){ ui.filter=a.dataset.f; renderLibrary(); $('#libScroll').scrollTop=0; } else if(k==='unscope'){ ui.series=null; renderLibrary(); }
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
    <button class="act" data-r="edit" id="aEdit">${IC.edit}Edit Title &amp; Series</button>
    <button class="act" data-r="toggle" id="aToggle">${isDone(c)?IC.undo+'Mark as Unread':IC.done+'Mark as Finished'}</button>
    <button class="act red" data-r="delete" id="aDelete">${IC.trash}Delete from Device</button></div>
    <button class="cancel" data-r="cancel">Cancel</button>`,null,'sheet');
  if(r==='read') openReader(id); else if(r==='edit') editComic(id); else if(r==='delete') deleteComic(id);
  else if(r==='toggle'){ if(isDone(c)){ c.progress=0; c.page=0; c.lastRead=0; } else { c.progress=1; } await dbPut(c); renderShelf(); } }
async function editComic(id){ const c=comics.find(x=>x.id===id); if(!c) return;
  const series=[...new Set(comics.map(x=>x.series).filter(Boolean))].sort();
  const {r,vals}=await modal(`<div class="mh"><h3>Edit Comic</h3></div><div class="mb">
    <label class="fld"><span>Title</span><input type="text" id="eTitle" value="${esc(c.title)}" maxlength="140"></label>
    <label class="fld"><span>Series</span><input type="text" id="eSeries" value="${esc(c.series||'')}" list="seriesList" placeholder="None" maxlength="80"><datalist id="seriesList">${series.map(s=>`<option value="${esc(s)}">`).join('')}</datalist></label>
    <label class="tgl"><input type="checkbox" id="eRtl" ${c.rtl?'checked':''}><span>Right-to-left (manga)<small>Reverses page order and swipe direction</small></span></label>
    <div class="mstat">${esc(c.fileName)} · ${fmtBytes(c.size)} · ${c.pages} pages</div>
  </div><div class="mf"><button class="btn ghost" data-r="delete" id="eDelete" style="color:#ff453a">Delete</button><span class="sp"></span><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="save" id="eSave">Save</button></div>`,
  w=>{ w._vals=()=>({t:w.querySelector('#eTitle').value,s:w.querySelector('#eSeries').value,r:w.querySelector('#eRtl').checked});
       w.querySelectorAll('input[type=text]').forEach(i=>i.addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); w.querySelector('#eSave').click(); } })); });
  if(r==='save'){ c.title=vals.t.trim()||c.title; c.series=vals.s.trim(); c.rtl=vals.r; await dbPut(c); renderShelf(); }
  else if(r==='delete') deleteComic(id); }
async function deleteComic(id){ const c=comics.find(x=>x.id===id); if(!c) return;
  if(!await confirmBox('Delete Comic?',`“${c.title}” and its stored PDF (${fmtBytes(c.size)}) will be removed from this device. Your original file in Google Drive is not affected.`)) return;
  await dbDelete(id); comics=comics.filter(x=>x.id!==id); const u=coverURL.get(id); if(u){ URL.revokeObjectURL(u); coverURL.delete(id); } renderShelf(); toast('Deleted'); }
async function openSettings(){
  let est={usage:0,quota:0}, persisted=false;
  try{ if(navigator.storage&&navigator.storage.estimate) est=await navigator.storage.estimate(); if(navigator.storage&&navigator.storage.persisted) persisted=await navigator.storage.persisted(); }catch(e){}
  const mine=comics.reduce((a,c)=>a+(c.size||0),0); const standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone;
  const {r}=await modal(`<div class="mh"><h3>Settings</h3></div><div class="mb">
    <div class="stor"><b>${fmtBytes(est.usage||mine)}</b><span>used${est.quota?` of ~${fmtBytes(est.quota)} available`:''}</span></div>
    <div class="mstat">${comics.length} comic${comics.length===1?'':'s'} · ${fmtBytes(mine)} of PDFs · storage ${persisted?'persistent ✓':'not yet marked persistent'}</div>
    <label class="tgl" style="margin-top:8px"><input type="checkbox" id="sSingle" ${store.get('singleLandscape',false)?'checked':''}><span>Single page in landscape<small>Off shows two-page spreads when the iPad is sideways</small></span></label>
    <div class="sgrp"><b>Google Drive folder</b><span id="sFolderCur">${esc(Drive.folder().name||'Folder')} · <code>${esc(Drive.folder().id)}</code>${store.get('driveFolder',null)?'':' (default)'}</span>
      <div class="frow"><input id="sFolder" type="url" placeholder="Paste a Drive folder link" autocomplete="off" autocapitalize="off" spellcheck="false"><button class="btn ghost" id="sFolderSave">Save</button></div>
      <small>Google Drive opens in this folder, and Import Entire Drive Folder lists it.${store.get('driveFolder',null)?' <button class="lnk" id="sFolderReset">Reset to default</button>':''}</small></div>
    <div class="note"><b>Private and offline.</b> Comics are copied into this app's on-device storage (IndexedDB). Nothing is uploaded.</div>
    <div class="note"><b>Home Screen app:</b> on iPad, the Home Screen app has its own storage, separate from Safari's. Add this page to your Home Screen (Share → Add to Home Screen), open it from there, and import your comics inside the Home Screen app.${standalone?'<br><b>✓ You are in the Home Screen app.</b>':'<br>You are currently in the browser.'}</div>
    ${persisted?'':'<button class="btn ghost" id="sPersist" data-r="persist">Request Persistent Storage</button>'}
  </div><div class="mf"><button class="btn" data-r="done">Done</button></div>`,w=>{ w.querySelector('#sSingle').addEventListener('change',e=>store.set('singleLandscape',e.target.checked));
    const cur=()=>{ const f=Drive.folder(); w.querySelector('#sFolderCur').innerHTML=`${esc(f.name||'Folder')} · <code>${esc(f.id)}</code>${store.get('driveFolder',null)?'':' (default)'}`; };
    w.querySelector('#sFolderSave').onclick=()=>{ const f=Drive.parseFolderLink(w.querySelector('#sFolder').value); if(!f){ toast("That doesn't look like a Google Drive folder link"); return; }
      Drive.setFolder({...f,name:'Custom folder'}); w.querySelector('#sFolder').value=''; cur(); toast('Drive folder saved'); };
    const rs=w.querySelector('#sFolderReset'); if(rs) rs.onclick=()=>{ Drive.setFolder(null); rs.remove(); cur(); toast('Using the default Drive folder'); }; });
  if(r==='persist'){ try{ const ok=await navigator.storage.persist(); toast(ok?'Storage marked persistent':'The browser declined for now. It often allows it in the Home Screen app.'); }catch(e){ toast('Not supported here'); } } }

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
      const page=await doc.getPage(1); const vp=page.getViewport({scale:1});
      const cc=await renderToCanvas(page,360,540,1,400000); const coverBlob=await (await toBlob(cc,.82)).arrayBuffer();   // stored as bytes (Blobs in IDB fail in some WebKit modes) freeCanvas(cc); page.cleanup();
      const pages=doc.numPages; await doc.destroy(); doc=null;
      const n=Math.ceil(f.size/CHUNK);
      for(let i=0;i<n;i++){ const ab=await f.slice(i*CHUNK,Math.min(f.size,(i+1)*CHUNK)).arrayBuffer(); await dbPutChunk(id,i,ab);
        toast(`Saving ${f.name}${tag}…`,{progress:(i+1)/n,sticky:true}); }
      const t0=titleFromName(f.name); const rec={id,title:t0,series:seriesGuess(t0),fileName:f.name,size:f.size,pages,aspect:vp.width/vp.height,cover:coverBlob,added:Date.now()+k,lastRead:0,page:0,progress:0,rtl:false};
      await dbPut(rec); comics.push(rec); ok++; renderShelf();
    }catch(err){ console.warn('import failed',err); try{ if(doc) await doc.destroy(); }catch(e){} try{ await dbDelete(id); }catch(e){}
      const quota=err&&(err.name==='QuotaExceededError'||/quota/i.test(err.message||''));
      toast(quota?`Out of storage space importing “${f.name}”.`:`Couldn't import “${f.name}”: ${err&&err.message||'not a valid PDF'}`); await new Promise(r=>setTimeout(r,1800)); }
  }
  importing=false; if(ok) toast(`Imported ${ok} comic${ok>1?'s':''} ✓`); renderShelf();
}

