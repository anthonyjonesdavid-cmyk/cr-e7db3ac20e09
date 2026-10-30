/* ---------- Animate page (Grok Imagine): plan panels with Grok vision, make one clip per panel, play them in order ---------- */
const Anim=(()=>{
  const API='https://cr-animate.djapps.workers.dev', PRICE={sec:0.03,img:0.01};
  const pass=()=>store.get('animPass','');
  const call=async(path,body)=>{ const r=await fetch(API+path,{method:body?'POST':'GET',headers:{'content-type':'application/json','x-pass':pass()},body:body?JSON.stringify(body):undefined}); let j={}; try{ j=await r.json(); }catch(e){} if(!r.ok){ const e=new Error(j.error||('Server error '+r.status)); e.j=j; e.status=r.status; throw e; } return j; };
  // clip + plan cache: its own IndexedDB so it never touches the comics database version
  let dbp; const adb=()=>dbp||(dbp=new Promise((res,rej)=>{ const r=indexedDB.open('cr-anim',1); r.onupgradeneeded=()=>{ r.result.createObjectStore('clips'); r.result.createObjectStore('plans'); }; r.onsuccess=()=>res(r.result); r.onerror=()=>rej(r.error); }));
  const idb=async(st,mode,fn)=>{ const d=await adb(); return new Promise((res,rej)=>{ const t=d.transaction(st,mode); const q=fn(t.objectStore(st)); t.oncomplete=()=>res(q&&q.result); t.onerror=()=>rej(t.error); }); };
  const get=(st,k)=>idb(st,'readonly',s=>s.get(k)), put=(st,k,v)=>idb(st,'readwrite',s=>s.put(v,k));
  const money=v=>'$'+(Math.round(v*100)/100).toFixed(2);
  const costOf=pl=>pl.panels.reduce((a,q)=>a+q.seconds*PRICE.sec+PRICE.img,0);

  async function passSheet(msg){ let st={configured:true}; try{ st=await call('/status'); }catch(e){ toast('Can’t reach the Animate server. Are you online?'); return false; }
    const set=!st.configured;
    const {r,vals}=await modal(`<div class="mh"><h3>Animate passcode</h3></div><div class="mb">
      <p class="confirm-msg">${msg?esc(msg)+' ':''}${set?'Choose a passcode for Animate page. Only devices with this passcode can spend your xAI credits.':'Enter your Animate passcode for this device.'}</p>
      ${!set&&pass()?'<label class="fld"><span>Current passcode (to change it)</span><input id="aOld" type="password" autocomplete="off"></label>':''}
      <label class="fld"><span>${set?'New passcode (6+ characters)':'Passcode'}</span><input id="aPass" type="password" autocomplete="off" autocapitalize="off" enterkeyhint="done"></label>
      <p class="fhint">Daily limit: ${money(st.cap||10)}. Used today: ${money(st.spent||0)}.</p></div>
      <div class="mf"><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="ok">${set?'Set Passcode':'Save'}</button></div>`,
      w=>{ setTimeout(()=>w.querySelector('#aPass').focus(),50); w._vals=()=>({p:w.querySelector('#aPass').value.trim(),old:w.querySelector('#aOld')?.value.trim()||''}); });
    if(r!=='ok'||!vals.p) return false;
    try{ if(set||vals.old){ await call('/setup',{pass:vals.p,old:vals.old}); } store.set('animPass',vals.p); await call('/check'); toast(set?'Passcode set':'Passcode saved on this device'); return true; }
    catch(e){ if(e.status===401) store.set('animPass',''); toast(e.message); return false; } }

  async function pageImage(i){ const pg=await R.doc.getPage(i+1); const c=await renderToCanvas(pg,1500,2200,1,3.4e6); pg.cleanup(); return c; }
  function crop(cv,box){ let [x,y,w,h]=box; const pad=0; x=Math.max(0,x-pad); y=Math.max(0,y-pad); w=Math.min(1-x,w+pad*2); h=Math.min(1-y,h+pad*2);
    const sx=x*cv.width, sy=y*cv.height, sw=Math.max(8,w*cv.width), sh=Math.max(8,h*cv.height), k=Math.min(2.5,Math.max(1,720/Math.min(sw,sh)));
    const c=document.createElement('canvas'); c.width=Math.round(sw*k); c.height=Math.round(sh*k); const g=c.getContext('2d',{alpha:false}); g.imageSmoothingQuality='high'; g.drawImage(cv,sx,sy,sw,sh,0,0,c.width,c.height); return c; }

  async function start(){ const c=R.comic; if(!c||!R.doc) return; let ps=pagesOf(R.views[R.vi]).filter(p=>p<R.n); if(!ps.length){ toast('Pick a comic page to animate'); return; }
    const page=ps[0], key=c.id+':'+page; const cached=await get('plans',key).catch(()=>null);
    if(cached&&cached.done){ const {r}=await modal(`<div class="mh"><h3>Animated page</h3></div><div class="mb"><p class="confirm-msg">Page ${ordOf(page)+1} already has ${cached.panels.length} clips saved on this iPad.</p></div><div class="mf"><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn ghost" data-r="redo">Make New (${money(costOf(cached))})</button><button class="btn" data-r="play">Play</button></div>`);
      if(r==='play') return player(c,page,cached); if(r!=='redo') return; }
    if(!pass()&&!await passSheet()) return;
    toast('Grok is reading the page…',{sticky:true}); let res, cv;
    try{ cv=await pageImage(page); res=await call('/plan',{image:cv.toDataURL('image/jpeg',.85),title:c.title,rtl:!!R.rtl}); hideToast(); }
    catch(e){ hideToast(); toast(e.message); if(e.status===401) passSheet(e.message); return; }
    const pl=res.plan; if(!pl.panels.length){ toast('Grok didn’t find any panels on this page'); return; }
    pl.panels.forEach(q=>{ q.thumb=crop(cv,q.box).toDataURL('image/jpeg',.88); });
    const total=costOf(pl), left=(res.cap||10)-(res.spent||0);
    const {r}=await modal(`<div class="mh"><h3>Animate page ${ordOf(page)+1}</h3><p class="dlsub">${esc(pl.mood)}</p></div><div class="mb anplan">
      <p class="anscore">${IC_NOTE}${esc(pl.score)}</p>
      ${pl.panels.map((q,k)=>`<div class="anrow"><img src="${q.thumb}" alt=""><div><b>${k+1}. ${esc(q.what)}</b><span>${esc(q.camera)} · ${q.seconds}s</span><small>${esc(q.sound)}</small></div></div>`).join('')}
      <p class="fhint">${pl.panels.length} clips · ${pl.panels.reduce((a,q)=>a+q.seconds,0)}s of 720p video · about ${money(total)} of xAI credit. Used today: ${money(res.spent||0)} of ${money(res.cap||10)}.</p></div>
      <div class="mf"><button class="btn ghost" data-r="cancel">Cancel</button><button class="btn" data-r="go" ${total>left?'disabled':''}>${total>left?'Over today’s limit':'Animate · '+money(total)}</button></div>`,null,'anmodal');
    if(r!=='go') return;
    pl.page=page; pl.at=Date.now(); await put('plans',key,pl).catch(()=>{});
    player(c,page,pl,cv); }

  let P2=null;
  function player(c,page,pl,cv){ close(); const el=document.createElement('div'); el.id='anim'; el.innerHTML=`<header class="anbar"><button class="icbtn" id="anClose" aria-label="Close"><svg class="i" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg></button><div class="antitle"><b>${esc(c.title)}</b><small>Page ${ordOf(page)+1} · ${pl.panels.length} panels</small></div><button class="rbtn" id="anSave" aria-label="Save clip"><svg class="i" viewBox="0 0 24 24"><path d="M12 4v11m0 0-4-4m4 4 4-4M5 19h14"/></svg>Save</button></header>
      <div class="anstage"><video id="anVid" playsinline controls preload="auto"></video><div class="anwait" id="anWait"></div></div>
      <div class="annotes" id="anNotes"></div><div class="anstrip" id="anStrip">${pl.panels.map((q,k)=>`<button class="anchip" data-k="${k}"><img src="${q.thumb}" alt=""><i>${k+1}</i><em></em></button>`).join('')}</div>`;
    document.body.appendChild(el); const S={el,c,page,pl,cv,cur:-1,urls:[],state:pl.panels.map(()=>'wait'),err:[],gen:{}}; P2=S;
    const vid=el.querySelector('#anVid');
    el.querySelector('#anClose').onclick=close;
    el.querySelector('#anStrip').onclick=e=>{ const b=e.target.closest('.anchip'); if(b) show(+b.dataset.k,true); };
    el.querySelector('#anSave').onclick=()=>save(S);
    vid.onended=()=>{ const n=S.cur+1; if(n<pl.panels.length) show(n,true); };
    S.show=show; function show(k,play){ S.cur=k; const q=pl.panels[k];
      el.querySelectorAll('.anchip').forEach((b,i)=>b.classList.toggle('on',i===k));
      el.querySelector('#anNotes').innerHTML=`<b>${k+1}. ${esc(q.what)}</b><div class="annote"><span>Camera</span>${esc(q.camera)}</div><div class="annote"><span>Music &amp; sound</span>${esc(q.sound)}</div><div class="annote"><span>Pacing</span>${esc(q.pacing)}</div>`;
      const w=el.querySelector('#anWait'), st=S.state[k];
      if(st==='ready'){ w.classList.add('hidden'); vid.classList.remove('hidden'); if(vid.dataset.k!==String(k)){ vid.src=S.urls[k]; vid.dataset.k=k; } if(play) vid.play().catch(()=>{}); }
      else { vid.pause(); vid.classList.add('hidden'); w.classList.remove('hidden'); w.style.backgroundImage=`url(${q.thumb})`; w.innerHTML=`<span>${st==='fail'?esc(S.err[k]||'This panel couldn’t be animated'):st==='make'?'<i class="spin"></i>Animating panel…':'<i class="spin"></i>Waiting its turn…'}</span>`; } }
    function mark(k,st,err){ S.state[k]=st; if(err) S.err[k]=err; const b=el.querySelectorAll('.anchip')[k]; if(b){ b.dataset.st=st; } if(S.cur===k) show(k,st==='ready'&&(vid.paused||vid.ended)); else if(st==='ready'&&S.cur>=0&&S.state[S.cur]!=='ready'&&k===S.cur+1) {} }
    S.mark=mark; show(0,false); run(S); }

  async function run(S){ const {c,page,pl}=S, base=c.id+':'+page; let next=0, live=true; S.stop=()=>{ live=false; };
    // cached clips first
    for(let k=0;k<pl.panels.length;k++){ const b=await get('clips',base+':'+k).catch(()=>null); if(b&&b.blob){ S.urls[k]=URL.createObjectURL(b.blob); S.mark(k,'ready'); } }
    if(S.state[0]==='ready') S.show(0,true);
    const todo=pl.panels.map((q,k)=>k).filter(k=>S.state[k]!=='ready'); if(!todo.length){ pl.done=true; return; }
    if(!S.cv) S.cv=await pageImage(page);
    const one=async k=>{ const q=pl.panels[k]; S.mark(k,'make');
      try{ const img=crop(S.cv,q.box).toDataURL('image/jpeg',.9);
        const prompt=`${q.prompt} Camera: ${q.camera}. Sound: ${q.sound}. Pacing: ${q.pacing}. Keep the original comic book art style, inks and colors.`;
        const {id}=await call('/clip',{image:img,prompt,seconds:q.seconds});
        for(let i=0;i<120&&live;i++){ await new Promise(r=>setTimeout(r,5000)); const s=await call('/clip/'+id).catch(()=>({status:'pending'}));
          if(s.status==='done'&&s.url){ const r=await fetch(API+'/video?u='+encodeURIComponent(s.url),{headers:{'x-pass':pass()}}); if(!r.ok) throw new Error('Couldn’t download the clip');
            const blob=await r.blob(); await put('clips',base+':'+k,{blob,at:Date.now()}).catch(()=>{}); S.urls[k]=URL.createObjectURL(blob); S.mark(k,'ready'); if(S.cur===k||S.state.slice(0,k).every(x=>x==='fail')) S.show(k,true); return; }
          if(s.status==='failed'||s.status==='expired') throw new Error(s.moderated?'Grok Imagine declined this panel (content rules)':(s.error||'Grok Imagine couldn’t make this clip'));
          if(s.moderated) throw new Error('Grok Imagine declined this panel (content rules)'); }
        if(live) throw new Error('Timed out waiting for this clip'); }
      catch(e){ if(!live) return; const msg=e.j&&e.j.refused?'Grok Imagine declined this panel: '+e.message:e.message; S.mark(k,'fail',msg); if(e.j&&e.j.cap){ live=false; toast(e.message); } } };
    // 3 at a time, in reading order
    const lanes=[0,1,2].map(async(l)=>{ await new Promise(r=>setTimeout(r,l*1500)); while(live&&next<todo.length){ await one(todo[next++]); } }); await Promise.all(lanes);
    if(S.state.every(s=>s!=='wait'&&s!=='make')){ pl.done=S.state.every(s=>s==='ready'); await put('plans',base,{...pl,done:pl.done}).catch(()=>{}); const f=S.state.filter(s=>s==='fail').length; if(P2===S) toast(f?`${pl.panels.length-f} of ${pl.panels.length} panels animated`:'All panels animated'); } }

  async function save(S){ const k=S.cur; if(S.state[k]!=='ready'){ toast('This clip isn’t ready yet'); return; }
    const blob=await (await fetch(S.urls[k])).blob(), name=`${(S.c.title||'comic').replace(/[^\w\- ]+/g,'').trim()} p${ordOf(S.page)+1} panel ${k+1}.mp4`;
    const f=new File([blob],name,{type:'video/mp4'});
    if(navigator.canShare&&navigator.canShare({files:[f]})){ try{ await navigator.share({files:[f]}); }catch(e){} return; }
    const a=document.createElement('a'); a.href=S.urls[k]; a.download=name; document.body.appendChild(a); a.click(); a.remove(); }
  function close(){ if(!P2) return; P2.stop&&P2.stop(); P2.urls.forEach(u=>u&&URL.revokeObjectURL(u)); P2.el.remove(); P2=null; }
  const IC_NOTE='<svg class="i" viewBox="0 0 24 24"><path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/></svg>';
  return {start,passSheet,close,isOpen:()=>!!P2};
})();
$('#rAnim').onclick=e=>{ e.stopPropagation(); Anim.start(); };
