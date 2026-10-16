/* ---------- v40: back-issue bin (Timeline) ---------- */
// A longbox seen from slightly above: bagged comics stand in a row, tops showing. Swipe riffles them forward (~120ms a card, with momentum);
// the front comic lifts to show its cover; tap it to read. Virtualized: a fixed pool of BIN_SLOTS cards is re-bound as you flip.
const BIN_SLOTS=30, BIN_BEHIND=2, BIN_MS=120, BIN_DIG=8;
var BIN={on:false,ids:[],pos:0,raf:0,drag:null,els:[]};
const binShuffle=a=>{ for(let i=a.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [a[i],a[j]]=[a[j],a[i]]; } return a; };
function openBin(){ if(!comics.length){ toast('Import some comics to fill the bin'); return; }
  BIN.on=true; BIN.ids=binShuffle(comics.map(c=>c.id)); BIN.pos=0; $('#bin').classList.remove('hidden');
  const box=$('#binCards'); if(!BIN.els.length||!box.children.length){ box.innerHTML=Array.from({length:BIN_SLOTS},()=>`<button class="bn-c" tabindex="-1" style="display:none"><img alt="" decoding="async" draggable="false"><span class="bn-bag"></span><span class="bn-tab"></span></button>`).join(''); BIN.els=[...box.children]; }
  binLayout(); Rain.sync(); }
function closeBin(){ BIN.on=false; cancelAnimationFrame(BIN.raf); BIN.raf=0; $('#bin').classList.add('hidden'); Rain.sync(); }
function binLayout(){ if(!BIN.on) return; const n=BIN.ids.length, st=$('#binStage'), H=st.clientHeight||600, W=st.clientWidth||400;
  const cw=Math.min(W*.56,H*.30,300), ch=cw*1.5, step=ch*.045, base=Math.floor(BIN.pos), lift=ch*.36;
  st.style.setProperty('--bcw',cw+'px'); st.style.setProperty('--bch',ch+'px');
  $('#binSub').textContent=n?`${Math.min(n,Math.round(BIN.pos)+1)} of ${n} · from your whole collection`:'';
  BIN.els.forEach((el,s)=>{ const k=base-BIN_BEHIND+s; if(k<0||k>=n){ if(el.style.display!=='none') el.style.display='none'; el.dataset.k=''; el.classList.remove('lift','front-out'); return; }
    const c=comics.find(x=>x.id===BIN.ids[k]); if(!c){ el.style.display='none'; return; }
    const o=k-BIN.pos, im=el.firstChild; el.style.display=''; el.dataset.k=k; el.dataset.id=c.id; el.setAttribute('aria-label',c.title);
    if(im.dataset.cid!==c.id){ im.dataset.cid=c.id; const u=cover(c); if(u) im.src=u; else im.removeAttribute('src'); }
    let ty,rx,sc,op=1;
    if(o<=-1){ ty=ch*.55; rx=-80; sc=1.04; op=Math.max(0,1.6+o); }                 // flipped forward, falling toward you
    else if(o<0){ const t=-o; ty=-lift*(1-t)+ch*.55*t; rx=-80*t; sc=1+.04*t; }     // the front one tipping over
    else if(o<1){ const t=o; ty=-lift*(1-t)+(-step)*t; rx=6*t; sc=1-.006*t; }       // next one rising into the lifted spot
    else { ty=-o*step; rx=6; sc=Math.max(.75,1-.006*o); }                              // standing in the box, receding
    el.style.transform=`perspective(1100px) translate3d(-50%,${ty.toFixed(1)}px,${(-Math.max(0,o)*6).toFixed(1)}px) rotateX(${rx.toFixed(1)}deg) scale(${sc.toFixed(3)})`;
    el.style.opacity=op.toFixed(2); el.style.zIndex=String(500-Math.round(o*10)); el.classList.toggle('lift',Math.abs(o)<.5); el.classList.toggle('front-out',o<-.5); }); }
function binTo(t,dur){ cancelAnimationFrame(BIN.raf); const n=BIN.ids.length; t=clamp(Math.round(t),0,Math.max(0,n-1)); const from=BIN.pos;
  if(dur==null) dur=clamp(Math.abs(t-from)*BIN_MS,BIN_MS,1600); BIN.lastDur=dur; if(reduced()){ BIN.pos=t; binLayout(); return; }
  const t0=performance.now(), f=now=>{ const k=Math.min(1,(now-t0)/dur), e=1-Math.pow(1-k,2.2); BIN.pos=from+(t-from)*e; binLayout(); if(k<1) BIN.raf=requestAnimationFrame(f); else { BIN.raf=0; BIN.pos=t; binLayout(); } };
  BIN.raf=requestAnimationFrame(f); }
function binDig(){ const n=BIN.ids.length; if(n<2) return; const at=Math.round(BIN.pos)+1, keep=new Set(BIN.ids.slice(0,at));
  const pool=binShuffle(comics.map(c=>c.id).filter(id=>!keep.has(id))).slice(0,BIN_DIG), ps=new Set(pool);
  BIN.ids=BIN.ids.slice(0,at).concat(pool,BIN.ids.slice(at).filter(id=>!ps.has(id))); binLayout(); binTo(at,BIN_MS*1.5); toast(`Dug up ${pool.length} comic${pool.length===1?'':'s'}`); }
{ const st=$('#binStage'), PX=70;
  st.addEventListener('pointerdown',e=>{ if(e.button>0) return; cancelAnimationFrame(BIN.raf); BIN.raf=0; BIN.drag={id:e.pointerId,x:e.clientX,y:e.clientY,p0:BIN.pos,moved:false,s:[[e.timeStamp,0]],tgt:e.target.closest('.bn-c')}; try{ st.setPointerCapture(e.pointerId); }catch(_){} });
  st.addEventListener('pointermove',e=>{ const d=BIN.drag; if(!d||e.pointerId!==d.id) return; const dx=e.clientX-d.x, dy=e.clientY-d.y, m=dy-dx;   // pull down or swipe left = forward
    if(!d.moved&&Math.hypot(dx,dy)<8) return; d.moved=true; d.s.push([e.timeStamp,m]); if(d.s.length>8) d.s.shift();
    BIN.pos=clamp(d.p0+m/PX,-.3,BIN.ids.length-.7); binLayout(); });
  const up=e=>{ const d=BIN.drag; if(!d||e.pointerId!==d.id) return; BIN.drag=null;
    if(!d.moved){ const el=d.tgt; if(!el||el.style.display==='none') return; const k=+el.dataset.k; if(k===Math.round(BIN.pos)) openReader(el.dataset.id); else binTo(k); return; }
    const s=d.s.filter(q=>d.s[d.s.length-1][0]-q[0]<=100), a=s[0], b=s[s.length-1], v=(b[0]-a[0])>0&&(e.timeStamp-b[0])<90?(b[1]-a[1])/(b[0]-a[0]):0;   // px/ms
    binTo(BIN.pos+(Math.abs(v)<.5?0:clamp(v*120/PX,-12,12))); };   // momentum only for a real flick
  st.addEventListener('pointerup',up); st.addEventListener('pointercancel',up);
  st.addEventListener('wheel',e=>{ e.preventDefault(); const d=Math.abs(e.deltaY)>Math.abs(e.deltaX)?e.deltaY:e.deltaX; binTo(Math.round(BIN.pos)+(d>0?1:-1)); },{passive:false});
  $('#tlBin').addEventListener('click',openBin); $('#binClose').addEventListener('click',closeBin); $('#binDig').addEventListener('click',binDig);
  addEventListener('resize',()=>{ if(BIN.on) binLayout(); });
  addEventListener('keydown',e=>{ if(!BIN.on||(R&&R.comic)) return; if(e.key==='ArrowRight'||e.key==='ArrowDown') binTo(Math.round(BIN.pos)+1); else if(e.key==='ArrowLeft'||e.key==='ArrowUp') binTo(Math.round(BIN.pos)-1); else if(e.key==='Enter'){ const id=BIN.ids[Math.round(BIN.pos)]; if(id) openReader(id); } else if(e.key==='Escape') closeBin(); }); }

/* ---------- v40: night at the comic shop (rack screen) + rain sound ---------- */
// Night: dim shop + warm lamp glow (flat 2D layers on the stage, never inside the 3D rotor — v37 lesson) and slow idle auto-rotation.
var NIGHT={araf:0,last:0,t:0,idle:()=>window.__crIdle||5000,speed:5};   // deg/s
const nightOn=()=>!!store.get('nightShop',false);
function setNight(v){ store.set('nightShop',!!v); nightUI(); }
function nightUI(){ const on=nightOn(), r=$('#rack'); if(r) r.classList.toggle('night',on); const b=$('#rkNight'); if(b) b.setAttribute('aria-pressed',on); const s=$('#sNight'); if(s) s.checked=on;
  stopAuto(); if(on) armAuto(true); }
function stopAuto(){ cancelAnimationFrame(NIGHT.araf); NIGHT.araf=0; clearTimeout(NIGHT.t); RK.auto=false; }
function armAuto(soon){ clearTimeout(NIGHT.t); if(!RK.on||!nightOn()||reduced()) return; NIGHT.t=setTimeout(startAuto,soon?Math.min(900,NIGHT.idle()):NIGHT.idle()); }
function startAuto(){ if(!RK.on||!nightOn()||reduced()||RK.drag||RK.raf||RK.pulling){ armAuto(false); return; } RK.auto=true; let last=performance.now();
  const f=t=>{ if(!RK.auto) return; const dt=Math.min(50,t-last); last=t; RK.a-=NIGHT.speed*dt/1000; rackApply(); NIGHT.araf=requestAnimationFrame(f); }; NIGHT.araf=requestAnimationFrame(f); }
function rackTouched(){ stopAuto(); armAuto(false); }
// Rain: soft filtered noise from the Web Audio API. Starts only from a tap; plays while the Timeline tab (or its rack/bin) is on screen; stops when leaving or hidden.
var Rain={ctx:null,gain:null,playing:false,unlocked:false,
  wanted(){ return !!store.get('rainSound',false)&&(TL.on||RK.on||BIN.on)&&!(R&&R.comic)&&document.visibilityState==='visible'; },
  build(){ const AC=window.AudioContext||window.webkitAudioContext; if(!AC) return false; const ctx=this.ctx=new AC(), sr=ctx.sampleRate, len=sr*2, buf=ctx.createBuffer(2,len,sr);
    for(let ch=0;ch<2;ch++){ const d=buf.getChannelData(ch); let b=0; for(let i=0;i<len;i++){ const w=Math.random()*2-1; b=(b+.02*w)/1.02; d[i]=w*.35+b*3.2; } }   // white + brown noise: hiss + rumble
    const src=ctx.createBufferSource(); src.buffer=buf; src.loop=true;
    const hp=ctx.createBiquadFilter(); hp.type='highpass'; hp.frequency.value=320; const lp=ctx.createBiquadFilter(); lp.type='lowpass'; lp.frequency.value=2600; lp.Q.value=.4;
    this.gain=ctx.createGain(); this.gain.gain.value=0; src.connect(hp); hp.connect(lp); lp.connect(this.gain); this.gain.connect(ctx.destination); src.start(); return true; },
  sync(gesture){ if(gesture) this.unlocked=true; const want=this.wanted()&&this.unlocked;
    if(want&&!this.playing){ if(!this.ctx&&!this.build()) return; this.playing=true; try{ this.ctx.resume(); }catch(e){} const g=this.gain.gain, t=this.ctx.currentTime; g.cancelScheduledValues(t); g.setValueAtTime(g.value,t); g.linearRampToValueAtTime(.16,t+1.2); }
    else if(!want&&this.playing){ this.playing=false; const g=this.gain.gain, t=this.ctx.currentTime; g.cancelScheduledValues(t); g.setValueAtTime(g.value,t); g.linearRampToValueAtTime(0,t+.25); const c=this.ctx; setTimeout(()=>{ if(!this.playing) try{ c.suspend(); }catch(e){} },300); }
    const b=$('#rkRain'); if(b) b.setAttribute('aria-pressed',!!store.get('rainSound',false)); const s=$('#sRain'); if(s) s.checked=!!store.get('rainSound',false); } };
function setRain(v){ store.set('rainSound',!!v); Rain.sync(true); }
document.addEventListener('visibilitychange',()=>Rain.sync(false));
// iOS only lets audio start inside a user gesture: the first tap anywhere unlocks it (the context is created/resumed inside that tap)
['pointerup','touchend','keydown'].forEach(t=>document.addEventListener(t,()=>{ if(Rain.unlocked) return; Rain.unlocked=true; if(store.get('rainSound',false)){ if(!Rain.ctx) Rain.build(); try{ Rain.ctx&&Rain.ctx.resume(); }catch(e){} } Rain.sync(false); },{capture:true,passive:true}));
{ $('#rkNight').addEventListener('click',()=>setNight(!nightOn())); $('#rkRain').addEventListener('click',()=>setRain(!store.get('rainSound',false)));
  const st=$('#rkStage'); ['pointerdown','pointerup','pointercancel','wheel'].forEach(t=>st.addEventListener(t,e=>{ if(!e.target.closest('.rkmood')) rackTouched(); },{passive:true}));
  ['rkLeft','rkRight','rkPrev','rkNext'].forEach(id=>$('#'+id).addEventListener('click',rackTouched));
  addEventListener('keydown',()=>{ if(RK.on) rackTouched(); });
  rmq.addEventListener&&rmq.addEventListener('change',()=>{ stopAuto(); armAuto(false); });
  document.addEventListener('visibilitychange',()=>{ if(document.visibilityState!=='visible') stopAuto(); else armAuto(false); }); }
