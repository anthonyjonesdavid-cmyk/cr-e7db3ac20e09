/* ================= Reader ================= */
const readerEl=$('#reader'), stage=$('#stage'), zoomer=$('#zoomer');
const R={ comic:null, doc:null, n:0, views:[], vh:[], vi:0, spread:false, fold:false, half:false, lastHalf:null, rtl:false, aspects:[], viewEl:null, thumbs:new Map(), gen:0, uiT:0 };
const Z={s:1,tx:0,ty:0};
let flip=null, animating=false, anim=null, drag=null, pinch=null, scrubbing=false;

/* ---- bitmap LRU (pixel budget; evicted canvases are zeroed to release memory on iPad) ---- */
const cache=new Map(); let cachePx=0;
function cacheGet(k){ const e=cache.get(k); if(e){ cache.delete(k); cache.set(k,e); } return e; }
function cachePut(k,e){ if(cache.has(k)){ freeCanvas(e.canvas); return cache.get(k); } cache.set(k,e); cachePx+=e.px;
  while(cachePx>CACHE_BUDGET&&cache.size>1){ const [ok,oe]=cache.entries().next().value; if(ok===k) break; cache.delete(ok); cachePx-=oe.px; freeCanvas(oe.canvas); } return e; }
function cacheClear(){ cache.forEach(e=>freeCanvas(e.canvas)); cache.clear(); cachePx=0; }

/* ---- priority job queue: one pdf.js render at a time, nearest pages first ---- */
const jobs=new Map(); let running=0;
function enqueue(key,kind,page,prio,run){ let j=jobs.get(key); if(j){ if(prio<j.prio) j.prio=prio; return j.promise; }
  j={key,kind,page,prio,run,started:false}; j.promise=new Promise((res,rej)=>{j.resolve=res;j.reject=rej}); j.promise.catch(()=>{}); jobs.set(key,j); pump(); return j.promise; }
let pumpT=0;
function pump(){ if(running>=1) return; let best=null; for(const j of jobs.values()) if(!j.started&&(!best||j.prio<best.prio)) best=j; if(!best) return;
  // keep the fold animation smooth: background renders wait while a page is being turned (visible pages still render)
  if((flip||animating)&&best.prio>0){ clearTimeout(pumpT); pumpT=setTimeout(pump,90); return; }
  best.started=true; running++; const gen=R.gen;
  Promise.resolve().then(best.run).then(v=>{ if(gen!==R.gen){ if(v&&v.canvas) freeCanvas(v.canvas); throw {stale:true}; } best.resolve(v); },e=>best.reject(e))
    .catch(e=>best.reject(e)).finally(()=>{ jobs.delete(best.key); running--; pump(); }); }
function dropJobs(pred){ for(const [k,j] of jobs) if(!j.started&&pred(j)){ jobs.delete(k); j.reject({stale:true}); } }

const keyFor=(i,w,h)=>`${i}|${Math.round(w*DPR)}x${Math.round(h*DPR)}`;
let aspectT=0;
function noteAspect(i,a){ const old=R.aspects[i]; R.aspects[i]=a; if(R.half&&old&&(old>WIDE)!==(a>WIDE)&&i>0){ clearTimeout(aspectT); aspectT=setTimeout(()=>{ if(!flip&&!drag&&Z.s<=1.01) relayout(true); },30); return; } if(old&&Math.abs(old-a)/a>0.03&&R.viewEl&&pagesOf(R.views[R.vi]).includes(i)){ clearTimeout(aspectT); aspectT=setTimeout(()=>{ if(!flip&&!drag&&Z.s<=1.01) renderView(); },30); } }
function requestPage(i,w,h,prio){ const key=keyFor(i,w,h); const e=cacheGet(key); if(e) return Promise.resolve(e); const doc=R.doc;
  return enqueue(key,'page',i,prio,async()=>{ const page=await doc.getPage(i+1); const vp=page.getViewport({scale:1}); noteAspect(i,vp.width/vp.height);
    const c=await renderToCanvas(page,w,h,DPR,BASE_MAX_PX); page.cleanup(); return cachePut(key,{canvas:c,px:c.width*c.height}); }); }

/* ---- views: single pages, or spreads with the cover alone ---- */
// half mode (fold comics in portrait): each wide sheet becomes two views, its halves in reading order (RTL: right half first);
// the wide cover sheet shows only its cover half (from the cover-crop detection); narrow sheets stay whole. R.vh[k] = 'L' | 'R' | null
const WIDE=1.15;
function buildViews(){ const v=[], vh=[];
  if(R.spread){ v.push([null,0]); for(let i=1;i<R.n;i+=2) v.push([i,i+1<R.n?i+1:null]); }
  else if(R.half){ const ord=R.rtl?['R','L']:['L','R'], side=(R.comic.coverCrop&&R.comic.coverCrop.side)||'';
    for(let i=0;i<R.n;i++){ const wide=(R.aspects[i]||0)>WIDE;
      if(i===0&&wide&&(side==='right'||side==='left')){ v.push([0]); vh.push(side==='right'?'R':'L'); }
      else if(wide) ord.forEach(h=>{ v.push([i]); vh.push(h); });
      else { v.push([i]); vh.push(null); } } }
  else for(let i=0;i<R.n;i++) v.push([i]);
  R.views=v; R.vh=R.half?vh:[]; }
const halfOf=k=>R.half?(R.vh[k]||null):null;
const pagesOf=v=>v?v.filter(x=>x!=null):[];
function viewOfPage(p,h){ if(R.spread) return p<=0?0:Math.floor((p-1)/2)+1; if(!R.half) return p;
  let first=-1; for(let k=0;k<R.views.length;k++){ if(R.views[k][0]===p){ if(first<0) first=k; if(!h||R.vh[k]===h) return k; } else if(first>=0) break; }
  if(first>=0) return first; let k=0; while(k<R.views.length-1&&R.views[k+1][0]<=p) k++; return k; }
const visualPages=v=>v.length===1?v:(R.rtl?[v[1],v[0]]:[v[0],v[1]]);   // [left slot, right slot]
function aspectOf(v,h){ let a=0; pagesOf(v).forEach(p=>{ a=Math.max(a,R.aspects[p]||0); }); a=a||R.comic.aspect||0.66; return h?a/2:a; }
function geom(v,h){ const W=stage.clientWidth,H=stage.clientHeight, ar=aspectOf(v,h===undefined?halfOf(R.views.indexOf(v)):h);
  if(v.length===2){ const sw=Math.floor(Math.min(W/2,H*ar)), sh=Math.floor(sw/ar), x0=Math.round((W-2*sw)/2), y0=Math.round((H-sh)/2); return [{x:x0,y:y0,w:sw,h:sh},{x:x0+sw,y:y0,w:sw,h:sh}]; }
  const sw=Math.floor(Math.min(W,H*ar)), sh=Math.floor(sw/ar); return [{x:Math.round((W-sw)/2),y:Math.round((H-sh)/2),w:sw,h:sh}]; }
const isLandscape=()=>stage.clientWidth>stage.clientHeight*1.05;
const wantSpread=()=>isLandscape()&&stage.clientWidth>=560&&!store.get('singleLandscape',false)&&R.n>1&&!R.fold;
const wantHalf=()=>R.fold&&!isLandscape()&&(R.comic.foldPortrait||'half')==='half';   // fold comics in portrait: one half at a time   // fold-in-middle comics: one wide page at a time

/* ---- page elements ---- */
function placeCanvas(cv,w,h,align){ const ar=cv.width/cv.height; let cw=w,ch=w/ar; if(ch>h){ ch=h; cw=h*ar; }
  cv.style.width=cw+'px'; cv.style.height=ch+'px'; cv.style.top=((h-ch)/2)+'px'; cv.style.left=(align==='r'?w-cw:align==='l'?0:(w-cw)/2)+'px'; }
function halfCopy(ent,half){ const sw=ent.canvas.width, sh=ent.canvas.height, hw=Math.ceil(sw/2), c=document.createElement('canvas'); c.width=hw; c.height=sh;
  c.getContext('2d',{alpha:false}).drawImage(ent.canvas,half==='R'?sw-hw:0,0,hw,sh,0,0,hw,sh); return c; }
function copyOf(ent){ const c=document.createElement('canvas'); c.width=ent.canvas.width; c.height=ent.canvas.height; c.getContext('2d',{alpha:false}).drawImage(ent.canvas,0,0); return c; }
// half: show one half of sheet i; the whole sheet is rendered at twice the width (shared by both halves) and that half is copied
function fillPage(d,i,w,h,align,prio,half){ Object.assign(d.dataset,{p:i,w,h,a:align}); if(half) d.dataset.half=half; else delete d.dataset.half; const fw=half?w*2:w;
  const show=ent=>{ d.classList.remove('loading'); d.querySelectorAll('canvas,.phn').forEach(x=>x.remove()); const c=half?halfCopy(ent,half):copyOf(ent); placeCanvas(c,w,h,align); d.prepend(c); };
  const e=cacheGet(keyFor(i,fw,h)); if(e){ show(e); return; }
  d.classList.add('loading'); const ph=document.createElement('span'); ph.className='phn'; ph.textContent=i+1; d.prepend(ph);
  requestPage(i,fw,h,prio).then(ent=>{ if(d.isConnected&&d.dataset.p==String(i)&&!d.dataset.hi) show(ent); }).catch(()=>{}); }
function pageEl(i,r,align,cls,half){ const d=document.createElement('div'); d.className=cls||'pg'; d.style.width=r.w+'px'; d.style.height=r.h+'px';
  if(i==null) d.classList.add('blank'); else fillPage(d,i,r.w,r.h,align,0,half); return d; }

function renderView(){
  if(!R.comic||!R.views.length) return; freeHi();
  const v=R.views[R.vi], hv=halfOf(R.vi), g=geom(v,hv), vis=visualPages(v);
  const view=document.createElement('div'); view.className='view';
  vis.forEach((p,k)=>{ const r=g[k]; const d=pageEl(p,r,v.length===2?(k===0?'r':'l'):'c','pg',hv); d.style.left=r.x+'px'; d.style.top=r.y+'px'; view.appendChild(d); });
  zoomer.replaceChildren(view); R.viewEl=view; Z.s=1; Z.tx=0; Z.ty=0; applyZoom(false);
  updateChrome(); prefetch(); saveSoon();
}
function prefetch(){ const want=new Set(pagesOf(R.views[R.vi]));
  [1,-1,2,-2].forEach((d,k)=>{ const v=R.views[R.vi+d]; if(!v) return; const hv=halfOf(R.vi+d), g=geom(v,hv), vis=visualPages(v);
    vis.forEach((p,j)=>{ if(p==null) return; want.add(p); requestPage(p,hv?g[j].w*2:g[j].w,g[j].h,1+k).catch(()=>{}); }); });   // adjacent halves share their sheet's render
  dropJobs(j=>(j.kind==='page'&&!want.has(j.page))||j.kind==='hi'); }
function updateChrome(){ const ps=pagesOf(R.views[R.vi]); let a=ps[0]+1, b=ps[ps.length-1]+1, N=R.n;
  if(R.half){ a=b=R.vi+1; N=R.views.length; }   // portrait half pages: counter + scrubber count halves
  $('#pgText').textContent=(a===b?a:`${a}–${b}`)+' / '+N;
  const s=$('#scrub'); s.max=N; s.value=b; s.dir=R.rtl?'rtl':'ltr'; s.style.setProperty('--pct',(N>1?(b-1)/(N-1)*100:100)+'%');
  $('#rRtl').classList.toggle('on',R.rtl); $('#rRtl').setAttribute('aria-pressed',R.rtl);
  const sp=$('#rSpread'); sp.classList.toggle('hidden',!isLandscape()||R.n<2||R.fold); sp.classList.toggle('on',R.spread); $('#rSpreadTxt').textContent=R.spread?'2-up':'1-up'; }

/* ---- progress ---- */
let saveT=0;
function saveSoon(){ clearTimeout(saveT); saveT=setTimeout(saveNow,250); }
function saveNow(){ clearTimeout(saveT); const c=R.comic; if(!c||!R.views.length) return; const ps=pagesOf(R.views[R.vi]); c.page=ps[0]; c.half=halfOf(R.vi)||null; c.progress=R.half?(R.vi+1)/R.views.length:(ps[ps.length-1]+1)/R.n; c.lastRead=Date.now(); dbPut(c).catch(()=>{}); }
addEventListener('pagehide',saveNow); document.addEventListener('visibilitychange',()=>{ if(document.hidden) saveNow(); });

/* ---- open / close ---- */
async function openReader(id,{push=true}={}){
  const c=comics.find(x=>x.id===id); if(!c){ toast('Comic not found'); return; }
  if(push) try{ history.pushState({r:id},'','#/read/'+id); }catch(e){}
  R.gen++; R.comic=c; R.n=c.pages; R.rtl=!!c.rtl; R.aspects=new Array(c.pages).fill(c.aspect||0.66); R.vi=0; R.views=[];
  hideToast(); readerEl.classList.remove('hidden'); readerEl.classList.add('ui'); $('#shelf').classList.add('hidden'); $('#rTitle').textContent=c.title; zoomer.replaceChildren(); R.viewEl=null;
  let doc; try{ doc=await openPdf(new IDBSource(c.id,c.size)); }catch(err){ console.warn(err); toast('Could not open this comic: '+(err.message||err)); closeReader(); return; }
  if(R.comic!==c){ doc.destroy().catch(()=>{}); return; }
  R.doc=doc; if(doc.numPages!==R.n){ R.n=c.pages=doc.numPages; R.aspects=new Array(R.n).fill(c.aspect||0.66); }
  R.fold=false; try{ R.fold=await turnIsFold(doc,c); }catch(e){ console.warn('page-turn detection failed',e); } if(R.comic!==c) return;
  R.spread=wantSpread(); R.half=wantHalf(); R.lastHalf=c.half?{s:c.page||0,h:c.half}:null; buildViews(); R.vi=clamp(viewOfPage(c.page||0,c.half),0,R.views.length-1); renderView();
  clearTimeout(R.uiT); R.uiT=setTimeout(()=>{ if(R.comic===c&&!scrubbing) readerEl.classList.remove('ui'); },1800);   // chrome slides away so the art fills the screen
}
function closeReader(){ saveNow(); cancelFlipNow(); R.gen++; dropJobs(()=>true); const d=R.doc; R.doc=null; R.comic=null; R.views=[]; if(d) d.destroy().catch(()=>{});
  freeHi(); cacheClear(); R.thumbs.forEach(u=>URL.revokeObjectURL(u)); R.thumbs.clear(); zoomer.replaceChildren(); R.viewEl=null; $('#pages').classList.add('hidden');
  readerEl.classList.add('hidden'); $('#shelf').classList.remove('hidden'); renderShelf(); }
$('#rBack').onclick=()=>{ if(history.state&&history.state.r) history.back(); else { try{history.replaceState(null,'',location.pathname+location.search)}catch(e){} closeReader(); } };
addEventListener('popstate',()=>{ const m=location.hash.match(/^#\/read\/(.+)$/); if(m){ if(!R.comic||R.comic.id!==m[1]) openReader(m[1],{push:false}); } else if(R.comic) closeReader(); });
$('#rRtl').onclick=()=>{ R.rtl=!R.rtl; R.comic.rtl=R.rtl; dbPut(R.comic); cancelFlipNow(); if(R.half) relayout(true); else renderView(); toast(R.rtl?'Right-to-left (manga) on':'Left-to-right'); };
$('#rSpread').onclick=()=>{ store.set('singleLandscape',!store.get('singleLandscape',false)); relayout(true); };
// rotation keeps the place: half (sheet s, half h) <-> sheet s; coming back to portrait on the same sheet restores the same half
function relayout(force){ if(!R.comic||!R.doc) return; cancelFlipNow(); const ps=pagesOf(R.views[R.vi]); const keep=ps.length?ps[0]:(R.comic.page||0); const sp=wantSpread(), hf=wantHalf();
  if(R.half&&R.views.length&&halfOf(R.vi)) R.lastHalf={s:keep,h:halfOf(R.vi)};
  if(sp!==R.spread||hf!==R.half||force||!R.views.length){ R.spread=sp; R.half=hf; buildViews(); }
  R.vi=clamp(viewOfPage(keep,R.half&&R.lastHalf&&R.lastHalf.s===keep?R.lastHalf.h:null),0,R.views.length-1); renderView(); }
let rsT=0; new ResizeObserver(()=>{ clearTimeout(rsT); rsT=setTimeout(()=>relayout(),120); }).observe(stage);

/* ================= Flip engine: real 3D page turn, finger-tracked, with shading ================= */
function face(i,r,align,extra,half){ const d=pageEl(i,r,align,'face'+(extra?' '+extra:''),half); const s=document.createElement('div'); s.className='shade'; d.appendChild(s); d._s=s; return d; }
// fold-in-middle: one half of a wide page (the bitmap is the full page's cached render; only that half is copied)
function halfFace(i,full,half,extra){ const lw=Math.floor(full.w/2), r={x:half==='R'?full.x+lw:full.x,y:full.y,w:half==='R'?full.w-lw:lw,h:full.h};
  const d=document.createElement('div'); d.className='face half'+(extra?' '+extra:''); d.style.width=r.w+'px'; d.style.height=r.h+'px'; d._r=r; d.dataset.p=i; d.dataset.half=half;
  const show=ent=>{ d.classList.remove('loading'); d.querySelectorAll('canvas').forEach(x=>x.remove());
    const sw=ent.canvas.width, sh=ent.canvas.height, hw=Math.ceil(sw/2), c=document.createElement('canvas'); c.width=hw; c.height=sh;
    c.getContext('2d',{alpha:false}).drawImage(ent.canvas,half==='R'?sw-hw:0,0,hw,sh,0,0,hw,sh);
    const ar=sw/sh; let cw=full.w,ch=full.w/ar; if(ch>full.h){ ch=full.h; cw=full.h*ar; } const css=cw*hw/sw;
    c.style.width=css+'px'; c.style.height=ch+'px'; c.style.top=((full.h-ch)/2)+'px'; c.style.left=(half==='R'?(full.w/2-lw):(full.w/2-css))+'px'; d.prepend(c); };
  if(i==null) d.classList.add('blank');
  else { const e=cacheGet(keyFor(i,full.w,full.h)); if(e) show(e); else { d.classList.add('loading'); requestPage(i,full.w,full.h,0).then(ent=>{ if(d.isConnected) show(ent); }).catch(()=>{}); } }
  const s=document.createElement('div'); s.className='shade'; d.appendChild(s); d._s=s; return d; }
function place(d,r){ d.style.left=r.x+'px'; d.style.top=r.y+'px'; d.style.width=r.w+'px'; d.style.height=r.h+'px'; }
const grad=(deg,a,b)=>`linear-gradient(${deg}deg,rgba(0,0,0,${a}),rgba(0,0,0,${b}))`;
// vdir: -1 = the page sweeps leftwards (swipe left / tap right), +1 = sweeps rightwards
function startFlip(vdir){
  if(flip||animating||!R.viewEl||Z.s>1.01) return false;
  const fwd=R.rtl?vdir>0:vdir<0, t=R.vi+(fwd?1:-1); if(t<0||t>=R.views.length) return false;
  const cv=R.views[R.vi], tv=R.views[t], W=stage.clientWidth;
  const wrap=document.createElement('div'); wrap.className='flip';
  const flipper=document.createElement('div'); flipper.className='flipper';
  let front,back,under=[],covered=null,angle,frontR,spine;
  const fold=R.fold&&!R.half, single=cv.length===1&&!fold, ch=halfOf(R.vi), th=halfOf(t);   // half pages turn like ordinary single pages
  if(fold){
    // wide two-page scans fold at the centre of the sheet, like a book (mirrored automatically for RTL via vdir)
    const gc=geom(cv)[0], gt=geom(tv)[0], ci=cv[0], ti=tv[0];
    if(vdir<0){ // right half lifts and folds over onto the left half; next sheet's right half is revealed underneath
      const uL=halfFace(ci,gc,'L'), uR=halfFace(ti,gt,'R'); place(uL,uL._r); place(uR,uR._r); under=[uR]; covered=uL; wrap.append(uL,uR);
      front=halfFace(ci,gc,'R','front'); back=halfFace(ti,gt,'L','back'); frontR=front._r; flipper.style.transformOrigin='0 50%'; angle=p=>-180*p; spine=frontR.x;
      uR._s.style.background=grad(90,.6,.04); uL._s.style.background=grad(270,.5,.05); front._s.style.background=grad(90,.04,.45); back._s.style.background=grad(270,.04,.45);
    } else {    // left half lifts and folds over onto the right half
      const uL=halfFace(ti,gt,'L'), uR=halfFace(ci,gc,'R'); place(uL,uL._r); place(uR,uR._r); under=[uL]; covered=uR; wrap.append(uL,uR);
      front=halfFace(ci,gc,'L','front'); back=halfFace(ti,gt,'R','back'); frontR=front._r; flipper.style.transformOrigin='100% 50%'; angle=p=>180*p; spine=frontR.x+frontR.w;
      uL._s.style.background=grad(270,.6,.04); uR._s.style.background=grad(90,.5,.05); front._s.style.background=grad(270,.04,.45); back._s.style.background=grad(90,.04,.45);
    }
  } else if(!single){
    const g=geom(cv), [cL,cR]=visualPages(cv), [tL,tR]=visualPages(tv);
    if(vdir<0){ // right page turns over the spine to the left
      const uL=face(cL,g[0],'r'), uR=face(tR,g[1],'l'); place(uL,g[0]); place(uR,g[1]); under=[uR]; covered=uL; wrap.append(uL,uR);
      front=face(cR,g[1],'l','front'); back=face(tL,g[0],'r','back'); frontR=g[1]; flipper.style.transformOrigin='0 50%'; angle=p=>-180*p; spine=g[1].x;
      uR._s.style.background=grad(90,.6,.04); uL._s.style.background=grad(270,.5,.05); front._s.style.background=grad(90,.04,.45); back._s.style.background=grad(270,.04,.45);
    } else {    // left page turns over the spine to the right
      const uL=face(tL,g[0],'r'), uR=face(cR,g[1],'l'); place(uL,g[0]); place(uR,g[1]); under=[uL]; covered=uR; wrap.append(uL,uR);
      front=face(cL,g[0],'r','front'); back=face(tR,g[1],'l','back'); frontR=g[0]; flipper.style.transformOrigin='100% 50%'; angle=p=>180*p; spine=g[0].x+g[0].w;
      uL._s.style.background=grad(270,.6,.04); uR._s.style.background=grad(90,.5,.05); front._s.style.background=grad(270,.04,.45); back._s.style.background=grad(90,.04,.45);
    }
  } else {
    // single page: the sheet hinges on its spine edge (left for LTR, right for RTL) and lifts away / swings back in
    const gc=geom(cv,ch)[0], gt=geom(tv,th)[0], sgn=R.rtl?1:-1;
    const turning=fwd?cv[0]:tv[0], stay=fwd?tv[0]:cv[0], rT=fwd?gc:gt, rS=fwd?gt:gc, hT=fwd?ch:th, hS=fwd?th:ch;
    const u=face(stay,rS,'c','',hS); place(u,rS); under=[u]; wrap.append(u);
    front=face(turning,rT,'c','front',hT); back=face(turning,rT,'c','back paper',hT); frontR=rT;
    flipper.style.transformOrigin=R.rtl?'100% 50%':'0 50%'; spine=R.rtl?rT.x+rT.w:rT.x;
    angle=fwd?(p=>sgn*180*p):(p=>sgn*180*(1-p));
    u._s.style.background=grad(R.rtl?270:90,.7,.06); front._s.style.background=grad(R.rtl?270:90,.04,.5); back._s.style.background=grad(R.rtl?90:270,.04,.35);
  }
  place(flipper,frontR); flipper.append(front,back); wrap.append(flipper);
  wrap.style.perspective=Math.round(Math.max(1600,W*2.4))+'px'; wrap.style.perspectiveOrigin=`${spine}px 50%`;
  const gl=document.createElement('div'); gl.className='shade'; gl.style.background='linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,.28) 50%,rgba(255,255,255,0))'; front.appendChild(gl);
  front.style.boxShadow=back.style.boxShadow='0 0 26px rgba(0,0,0,.5)';
  stage.appendChild(wrap); R.viewEl.style.visibility='hidden';
  // finger tracking: keep the sheet's free edge under the finger (edge x = w*cos(angle))
  const fw=frontR.w, k=single?1.15:1;
  const track=travel=>{ const e=clamp(travel*k/fw,0,2); return (single&&!fwd)? 1-Math.acos(clamp(e,-1,1))/Math.PI : Math.acos(clamp(1-e,-1,1))/Math.PI; };
  flip={vdir,fwd,t,wrap,p:-1,track,mode:fold?'fold':single?(R.half?'half':'single'):'spread',setP(p){ p=clamp(p,0,1); this.p=p; const a=angle(p), aa=Math.abs(a);
    flipper.style.transform=`rotateY(${a.toFixed(2)}deg)`; const showFront=aa<90;
    front.style.visibility=showFront?'visible':'hidden'; back.style.visibility=showFront?'hidden':'visible';
    front._s.style.opacity=showFront?(aa/90)*.85:0; gl.style.opacity=showFront?Math.sin(aa/90*Math.PI)*.55:0;
    back._s.style.opacity=showFront?0:((180-aa)/90)*.8;
    under.forEach(u=>u._s.style.opacity=single?(1-aa/180)*.9:(1-p)*.9);
    if(covered) covered._s.style.opacity=p>.5?Math.sin((p-.5)*2*Math.PI)*.5:0; }};
  flip.setP(0); return true;
}
function finishFlip(complete){ if(!flip) return; const f=flip; flip=null;
  if(complete){ R.vi=f.t; renderView(); } else if(R.viewEl) R.viewEl.style.visibility='';
  f.wrap.remove(); }
const easeInOut=t=>t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2, easeOut=t=>1-Math.pow(1-t,3);
function animateP(from,to,dur,ease,done){ animating=true; const t0=performance.now(); let raf=0, over=false;
  const end=()=>{ if(over) return; over=true; cancelAnimationFrame(raf); anim=null; if(flip) flip.setP(to); animating=false; done&&done(); };
  const step=now=>{ if(over) return; if(!flip){ over=true; anim=null; animating=false; return; } const k=Math.min(1,Math.max(0,(now-t0)/dur)); flip.setP(from+(to-from)*ease(k)); if(k<1) raf=requestAnimationFrame(step); else end(); };
  anim={end}; raf=requestAnimationFrame(step); }
const fastForward=()=>{ if(anim) anim.end(); };
function cancelFlipNow(){ if(anim) anim.end(); if(flip) finishFlip(false); animating=false; drag=null; }
function go(vdir,dur=620){ if(!R.doc||Z.s>1.01) return; if(animating) fastForward(); if(flip) return;
  if(startFlip(vdir)) animateP(0,1,dur,easeInOut,()=>finishFlip(true)); else bounce(vdir); }
function bounce(vdir){ if(!R.viewEl||!R.viewEl.animate) return; R.viewEl.animate([{transform:'none'},{transform:`translateX(${vdir*14}px)`},{transform:'none'}],{duration:300,easing:'ease-out'}); }
function jumpTo(p){ cancelFlipNow(); R.vi=clamp(viewOfPage(p),0,R.views.length-1); renderView(); }
function jumpToView(k){ cancelFlipNow(); R.vi=clamp(k,0,R.views.length-1); renderView(); }

/* ================= Gestures ================= */
// A tiny quick flick (~20px) turns; slow drags commit past 13% of the page width; axis lock keeps vertical pans from turning.
const G={ SLOP:6, AXIS:1.2, VEL_WIN:100, FLICK_VEL:.2, FLICK_MIN:10, BACK_VEL:-.2, COMMIT:.13, QUICK_MS:220, QUICK_MIN:12, TAP_MS:350, TAP_SLOP:10, DTAP_MS:270 };
let suppressUntilAllUp=false; const ptrs=new Map();
const tstamp=e=>(e&&e.timeStamp)||performance.now();
function pushS(d,e){ const t=tstamp(e); d.s.push([t,e.clientX]); while(d.s.length>2&&t-d.s[0][0]>G.VEL_WIN*2) d.s.shift(); }
function vel(d,tEnd){ const s=d.s; if(s.length<2) return 0; const last=s[s.length-1], tr=Math.max(tEnd||last[0],last[0]); let first=s[s.length-2];
  for(let i=s.length-2;i>=0;i--){ if(tr-s[i][0]<=G.VEL_WIN) first=s[i]; else break; } if(tr-last[0]>G.VEL_WIN) return 0; return (last[1]-first[1])/Math.max(8,last[0]-first[0]); }
function pageSpan(){ const v=R.views[R.vi], g=geom(v,halfOf(R.vi)); return v.length===2?g[0].w*2:g[0].w; }
function stagePt(e){ const b=stage.getBoundingClientRect(); return {x:e.clientX-b.left,y:e.clientY-b.top}; }
stage.addEventListener('pointerdown',e=>{
  if(!R.doc||(e.pointerType==='mouse'&&e.button!==0)) return;
  ptrs.set(e.pointerId,stagePt(e)); try{ stage.setPointerCapture(e.pointerId); }catch(_){}
  if(ptrs.size===2){ if(drag&&drag.mode==='flip'&&flip&&!animating) animateP(flip.p,0,160,easeOut,()=>finishFlip(false)); drag=null; startPinch(); return; }
  if(ptrs.size>2||suppressUntilAllUp) return;
  if(animating) fastForward();
  drag={id:e.pointerId,x0:e.clientX,y0:e.clientY,t0:tstamp(e),mode:null,s:[[tstamp(e),e.clientX]],zoomed:Z.s>1.01,tx0:Z.tx,ty0:Z.ty};
});
stage.addEventListener('pointermove',e=>{
  if(!ptrs.has(e.pointerId)) return; ptrs.set(e.pointerId,stagePt(e));
  if(pinch){ movePinch(); return; }
  const d=drag; if(!d||e.pointerId!==d.id) return;
  const dx=e.clientX-d.x0, dy=e.clientY-d.y0; pushS(d,e);
  if(d.zoomed){ if(!d.mode&&Math.hypot(dx,dy)<G.SLOP) return; d.mode='pan'; Z.tx=d.tx0+dx; Z.ty=d.ty0+dy; clampZoom(); applyZoom(false); return; }
  if(!d.mode){ if(Math.abs(dx)<G.SLOP&&Math.abs(dy)<G.SLOP) return;
    if(Math.abs(dx)>Math.abs(dy)*G.AXIS){ d.dir=dx<0?-1:1; d.mode=startFlip(d.dir)?'flip':'rubber'; } else { d.mode='vert'; return; } }
  if(d.mode==='flip'&&flip) flip.setP(flip.track(d.dir<0?-dx:dx));
  else if(d.mode==='rubber'&&R.viewEl) R.viewEl.style.transform=`translateX(${dx*.12}px)`;
});
function pointerEnd(e,cancelled){
  if(!ptrs.has(e.pointerId)) return; ptrs.delete(e.pointerId);
  if(pinch){ if(ptrs.size<2){ endPinch(); suppressUntilAllUp=ptrs.size>0; } return; }
  if(ptrs.size===0) suppressUntilAllUp=false;
  const d=drag; if(!d||e.pointerId!==d.id) return; drag=null;
  if(!cancelled) pushS(d,e);
  const dx=e.clientX-d.x0, dy=e.clientY-d.y0, dt=tstamp(e)-d.t0;
  if(!d.mode&&!cancelled&&Math.hypot(dx,dy)<G.TAP_SLOP&&dt<G.TAP_MS){ onTap(stagePt(e)); return; }
  if(d.mode==='pan'){ scheduleHi(); return; }
  if(d.zoomed) return;
  if(!d.mode&&!cancelled&&Math.abs(dx)>=G.SLOP&&Math.abs(dx)>Math.abs(dy)*G.AXIS){   // whole flick landed between move events
    const v=Math.abs(vel(d,tstamp(e))), quick=dt<=G.QUICK_MS&&Math.abs(dx)>=G.QUICK_MIN;
    if(quick||v>=G.FLICK_VEL||Math.abs(dx)>=pageSpan()*G.COMMIT) go(dx<0?-1:1,440); return; }
  if(d.mode==='flip'&&flip){
    const travel=d.dir<0?-dx:dx, v=vel(d,tstamp(e))*(d.dir<0?-1:1);
    const quick=dt<=G.QUICK_MS&&travel>=G.QUICK_MIN&&v>G.BACK_VEL;
    const flick=(v>=G.FLICK_VEL&&travel>=G.FLICK_MIN)||quick;
    const far=travel>=pageSpan()*G.COMMIT&&v>G.BACK_VEL;
    const complete=cancelled?travel>=pageSpan()*G.COMMIT:(flick||far);
    const p=flip.p, to=complete?1:0;
    const dur=complete?clamp(Math.round((1-p)*(flick?440:540)),240,540):clamp(Math.round(p*480),140,360);
    animateP(p,to,dur,easeOut,()=>finishFlip(complete));
  } else if(d.mode==='rubber'&&R.viewEl){ const el=R.viewEl; el.style.transition='transform .3s cubic-bezier(.2,1.4,.4,1)'; el.style.transform=''; setTimeout(()=>{ el.style.transition=''; },320); }
}
stage.addEventListener('pointerup',e=>pointerEnd(e,false));
stage.addEventListener('pointercancel',e=>pointerEnd(e,true));
document.addEventListener('gesturestart',e=>e.preventDefault()); document.addEventListener('gesturechange',e=>e.preventDefault());
stage.addEventListener('contextmenu',e=>e.preventDefault());
stage.addEventListener('wheel',e=>{ if(!R.doc) return; e.preventDefault(); if(e.ctrlKey){ zoomAt(stagePt(e),Z.s*Math.exp(-e.deltaY*.01),false); if(Z.s<1.02) resetZoom(false); else scheduleHi(); } else if(Z.s>1.01){ Z.tx-=e.deltaX; Z.ty-=e.deltaY; clampZoom(); applyZoom(false); scheduleHi(); } },{passive:false});

let lastTap=null;
function onTap(pt){ const now=performance.now();
  if(lastTap&&now-lastTap.t<G.DTAP_MS+40&&Math.hypot(pt.x-lastTap.x,pt.y-lastTap.y)<40){ clearTimeout(lastTap.timer); lastTap=null; doubleTap(pt); return; }
  const tp={t:now,x:pt.x,y:pt.y}; tp.timer=setTimeout(()=>{ if(lastTap===tp) lastTap=null; singleTap(pt); },G.DTAP_MS); lastTap=tp; }
function singleTap(pt){ const W=stage.clientWidth, edge=Math.min(W*.28,240);
  if(Z.s<=1.01&&pt.x<edge) go(1); else if(Z.s<=1.01&&pt.x>W-edge) go(-1); else toggleUI(); }
function toggleUI(force){ const on=force??!readerEl.classList.contains('ui'); readerEl.classList.toggle('ui',on); clearTimeout(R.uiT); }
function doubleTap(pt){ if(flip) return; if(Z.s>1.01) resetZoom(true); else { zoomAt(pt,2.5,true); scheduleHi(); } }

/* ---- zoom & pan (no page turns while zoomed) ---- */
function contentBox(){ const g=geom(R.views[R.vi],halfOf(R.vi)); return {x0:g[0].x,y0:g[0].y,x1:g[g.length-1].x+g[g.length-1].w,y1:g[0].y+g[0].h}; }
function clampZoom(){ const W=stage.clientWidth,H=stage.clientHeight,b=contentBox(),s=Z.s;
  const ax=(lo,hi,size,t)=>{ const ext=(hi-lo)*s; if(ext<=size) return (size-ext)/2-lo*s; return clamp(t,size-hi*s,-lo*s); };
  Z.tx=ax(b.x0,b.x1,W,Z.tx); Z.ty=ax(b.y0,b.y1,H,Z.ty); }
function applyZoom(animate){ zoomer.classList.toggle('anim',!!animate); zoomer.style.transform=(Z.s===1&&Z.tx===0&&Z.ty===0)?'':`translate3d(${Z.tx}px,${Z.ty}px,0) scale(${Z.s})`;
  if(animate) setTimeout(()=>zoomer.classList.remove('anim'),280); }
function zoomAt(pt,s,animate){ const cx=(pt.x-Z.tx)/Z.s, cy=(pt.y-Z.ty)/Z.s; Z.s=clamp(s,1,6); Z.tx=pt.x-cx*Z.s; Z.ty=pt.y-cy*Z.s; clampZoom(); applyZoom(animate); }
function resetZoom(animate){ const was=Z.s>1.01; Z.s=1; Z.tx=0; Z.ty=0; applyZoom(animate&&was); restoreBase(); }
function startPinch(){ const [a,b]=[...ptrs.values()]; pinch={d0:Math.hypot(a.x-b.x,a.y-b.y)||1,s0:Z.s,cx:((a.x+b.x)/2-Z.tx)/Z.s,cy:((a.y+b.y)/2-Z.ty)/Z.s}; zoomer.classList.remove('anim'); }
function movePinch(){ const [a,b]=[...ptrs.values()]; if(!b) return; const d=Math.hypot(a.x-b.x,a.y-b.y), mx=(a.x+b.x)/2, my=(a.y+b.y)/2;
  Z.s=clamp(pinch.s0*d/pinch.d0,.85,6); Z.tx=mx-pinch.cx*Z.s; Z.ty=my-pinch.cy*Z.s; if(Z.s>=1) clampZoom(); applyZoom(false); }
function endPinch(){ pinch=null; if(Z.s<1.06) resetZoom(true); else { clampZoom(); applyZoom(true); scheduleHi(); } }
/* sharper re-render of the visible page(s) while zoomed; released on zoom-out or page change */
let hiT=0, hiCanvases=[];
function scheduleHi(){ clearTimeout(hiT); hiT=setTimeout(doHi,220); }
function doHi(){ if(!R.viewEl||Z.s<=1.01) return; const mul=Math.min(4,Math.ceil(Z.s*2)/2), doc=R.doc, viewEl=R.viewEl;
  viewEl.querySelectorAll('.pg[data-p]').forEach(d=>{ if(+(d.dataset.hi||0)>=mul) return; const i=+d.dataset.p, w=+d.dataset.w, h=+d.dataset.h, half=d.dataset.half||'', fw=half?w*2:w;
    enqueue(`hi|${i}|${fw}x${h}|${mul}|${half}`,'hi',i,-1,async()=>{ const page=await doc.getPage(i+1); let c=await renderToCanvas(page,fw,h,DPR*mul,HI_MAX_PX*(half?2:1)); page.cleanup();
      if(half){ const hc=halfCopy({canvas:c},half); freeCanvas(c); c=hc; } return {canvas:c,px:c.width*c.height}; })
    .then(ent=>{ if(R.viewEl!==viewEl||Z.s<=1.01||!d.isConnected){ freeCanvas(ent.canvas); return; }
      const old=d.querySelector('canvas'); placeCanvas(ent.canvas,w,h,d.dataset.a); d.classList.remove('loading'); d.querySelectorAll('.phn').forEach(x=>x.remove());
      if(old){ old.replaceWith(ent.canvas); if(hiCanvases.includes(old)) hiCanvases=hiCanvases.filter(x=>x!==old); freeCanvas(old); } else d.prepend(ent.canvas);
      hiCanvases.push(ent.canvas); d.dataset.hi=mul; }).catch(()=>{}); }); }
function freeHi(){ clearTimeout(hiT); hiCanvases.forEach(freeCanvas); hiCanvases=[]; dropJobs(j=>j.kind==='hi'); }
function restoreBase(){ if(!R.viewEl) return; const had=hiCanvases.length; freeHi(); if(!had) return;
  R.viewEl.querySelectorAll('.pg[data-p]').forEach(d=>{ delete d.dataset.hi; fillPage(d,+d.dataset.p,+d.dataset.w,+d.dataset.h,d.dataset.a,0,d.dataset.half||''); }); }

/* ---- keyboard (desktop / iPad keyboard) ---- */
document.addEventListener('keydown',e=>{ if(!R.comic||document.querySelector('.mwrap')||e.target.matches('input[type=text],input[type=search]')) return;
  if(e.key==='ArrowLeft'){ go(1); e.preventDefault(); } else if(e.key==='ArrowRight'||e.key===' '){ go(-1); e.preventDefault(); }
  else if(e.key==='Escape'){ if(!$('#pages').classList.contains('hidden')) $('#pages').classList.add('hidden'); else if(Z.s>1.01) resetZoom(true); else $('#rBack').click(); } });

/* ================= Thumbnails, scrubber, page grid ================= */
function thumb(i,prio){ const u=R.thumbs.get(i); if(u){ R.thumbs.delete(i); R.thumbs.set(i,u); return Promise.resolve(u); } const doc=R.doc;
  return enqueue('t|'+i,'thumb',i,prio,async()=>{ const page=await doc.getPage(i+1); const c=await renderToCanvas(page,110,165,2,80000); page.cleanup(); const b=await toBlob(c,.7); freeCanvas(c);
    const url=URL.createObjectURL(b); R.thumbs.set(i,url); while(R.thumbs.size>400){ const [k,v]=R.thumbs.entries().next().value; URL.revokeObjectURL(v); R.thumbs.delete(k); } return url; }); }
const scrub=$('#scrub'), bubble=$('#bubble');
function showBubble(){ const v=+scrub.value, n=R.half?R.views.length:R.n, frac=n>1?(v-1)/(n-1):0, w=scrub.clientWidth, x=(R.rtl?1-frac:frac)*(w-16)+8;
  bubble.classList.remove('hidden'); bubble.style.left=clamp(x,56,w-40)+'px'; bubble.querySelector('span').textContent=`Page ${v}`;
  const sh=R.half?((R.views[v-1]||[0])[0]):v-1;   // half pages: thumbnail of that half's sheet
  scrub.style.setProperty('--pct',frac*100+'%'); const img=bubble.querySelector('img'); img.dataset.p=sh; const u=R.thumbs.get(sh);
  if(u) img.src=u; else { img.removeAttribute('src'); thumb(sh,-2).then(url=>{ if(img.dataset.p==String(sh)) img.src=url; }).catch(()=>{}); } }
const hideBubble=ms=>setTimeout(()=>{ bubble.classList.add('hidden'); scrubbing=false; },ms);
scrub.addEventListener('input',()=>{ scrubbing=true; clearTimeout(R.uiT); showBubble(); });
scrub.addEventListener('change',()=>{ if(R.half) jumpToView(+scrub.value-1); else jumpTo(+scrub.value-1); hideBubble(600); });
$('#rGrid').onclick=openPages; $('#pagesClose').onclick=()=>$('#pages').classList.add('hidden');
let pagesIO=null;
function openPages(){ const grid=$('#pgrid'), cur=new Set(pagesOf(R.views[R.vi]));
  grid.innerHTML=Array.from({length:R.n},(_,i)=>`<button data-p="${i}" class="${cur.has(i)?'cur':''}"><div class="th"></div><span>${i+1}</span></button>`).join('');
  $('#pages').classList.remove('hidden'); if(pagesIO) pagesIO.disconnect();
  pagesIO=new IntersectionObserver(es=>es.forEach(en=>{ if(!en.isIntersecting) return; const b=en.target; pagesIO.unobserve(b); const i=+b.dataset.p;
    thumb(i,20+i*.001).then(u=>{ b.querySelector('.th').innerHTML=`<img src="${u}" alt="">`; }).catch(()=>{}); }),{root:grid,rootMargin:'300px'});
  grid.querySelectorAll('button').forEach(b=>pagesIO.observe(b));
  const c=grid.querySelector('.cur'); if(c) c.scrollIntoView({block:'center'}); }
$('#pgrid').addEventListener('click',e=>{ const b=e.target.closest('button[data-p]'); if(!b) return; $('#pages').classList.add('hidden'); jumpTo(+b.dataset.p); });

