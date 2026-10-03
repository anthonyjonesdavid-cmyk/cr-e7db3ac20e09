/* ================= Google Drive import (GIS token client + Picker; streamed into chunked IndexedDB) =================
   The access token lives in memory only. Files are downloaded straight from Google to this device; nothing is uploaded. */
const Drive=(()=>{
  const SCOPE=DRIVE_FOLDER_IMPORT?'https://www.googleapis.com/auth/drive.readonly':'https://www.googleapis.com/auth/drive.file';
  const APP_ID=GOOGLE_APP_ID||(GOOGLE_CLIENT_ID.match(/^(\d+)-/)||[])[1]||'';
  const configured=()=>!!(GOOGLE_CLIENT_ID&&GOOGLE_API_KEY);
  const FOLDER='application/vnd.google-apps.folder';
  const REDIRECT=new URL('./',location.href).href.split('#')[0].split('?')[0];
  let tok=null;                 // {t, exp}
  let mode='pick';              // 'pick' (Picker) | 'folder' (Import Entire Folder)
  const folder=()=>store.get('driveFolder',null)||DRIVE_DEFAULT_FOLDER;
  // accepts a Drive folder link (…/folders/ID?resourcekey=KEY, …open?id=ID) or a bare ID
  function parseFolderLink(txt){ txt=String(txt||'').trim(); if(!txt) return null; let id=null, rk=null;
    try{ const u=new URL(txt); const m=u.pathname.match(/\/folders\/([\w-]{10,})/); id=m?m[1]:u.searchParams.get('id'); rk=u.searchParams.get('resourcekey'); }
    catch(e){ const m=txt.match(/^[\w-]{10,}$/); id=m?m[0]:null; }
    return id?{id,resourceKey:rk||''}:null; }
  const rkHeader=(keys)=>{ const v=[...new Set(keys.filter(Boolean))].join(','); return v?{'X-Goog-Drive-Resource-Keys':v}:{}; };
  const folderKey=()=>{ const f=folder(); return f.resourceKey?`${f.id}/${f.resourceKey}`:''; };
  let tokenClient=null, loadP=null, pickerReady=false;
  const tokOK=()=>tok&&tok.exp>Date.now()+60000;

  // pick up a token returned by the redirect fallback (Home Screen app), then strip it from the URL
  let resumePicker=false;
  (()=>{ const h=location.hash; if(!/[#&](access_token|error)=/.test(h)) return;
    const p=new URLSearchParams(h.slice(1)); let want=null; try{ want=sessionStorage.getItem('cr.oauthState'); sessionStorage.removeItem('cr.oauthState'); }catch(e){}
    try{ history.replaceState(null,'',location.pathname+location.search); }catch(e){}
    try{ mode=sessionStorage.getItem('cr.oauthMode')||'pick'; sessionStorage.removeItem('cr.oauthMode'); }catch(e){}
    if(p.get('access_token')&&want&&p.get('state')===want){ tok={t:p.get('access_token'),exp:Date.now()+(+p.get('expires_in')||3600)*1000}; resumePicker=true; }
    else if(p.get('error')) setTimeout(()=>toast(p.get('error')==='access_denied'?'Google sign-in was cancelled':'Google sign-in failed: '+p.get('error')),600); })();

  function script(src){ return new Promise((res,rej)=>{ const s=document.createElement('script'); s.src=src; s.async=true; s.onload=res; s.onerror=()=>rej(new Error('Could not load '+src)); document.head.appendChild(s); }); }
  function load(){ if(!configured()) return Promise.reject(new Error('not configured'));
    if(!loadP) loadP=Promise.all([
      script('https://accounts.google.com/gsi/client').then(()=>{ tokenClient=google.accounts.oauth2.initTokenClient({client_id:GOOGLE_CLIENT_ID,scope:SCOPE,callback:()=>{},error_callback:()=>{}}); }),
      script('https://apis.google.com/js/api.js').then(()=>new Promise((res,rej)=>gapi.load('picker',{callback:res,onerror:rej}))).then(()=>{ pickerReady=true; })
    ]).catch(e=>{ loadP=null; throw e; });
    return loadP; }
  const ready=()=>!!(tokenClient&&pickerReady);
  function preload(){ if(configured()&&navigator.onLine) load().catch(()=>{}); }

  const notSetUp=()=>modal(`<div class="mh"><h3>Drive import not set up yet</h3></div><div class="mb"><p class="confirm-msg">Importing straight from Google Drive needs a one-time Google sign-in setup that hasn't been added to this app yet.</p><p class="confirm-msg" style="margin-top:10px">Until then, use <b>From Files</b>.</p></div><div class="mf"><button class="btn" data-r="ok" id="dNotSetOk">OK</button></div>`,null,'drv');

  // entry point: must run synchronously inside the user's tap so the sign-in popup isn't blocked
  const afterToken=()=>mode==='folder'?folderFlow():showPicker();
  function start(m){ mode=m||'pick';
    if(!configured()){ notSetUp(); return; }
    if(!navigator.onLine){ toast("You're offline. Connect to the internet to import from Google Drive."); return; }
    if(tokOK()){ if(mode==='folder') folderFlow(); else ensureLoaded().then(showPicker).catch(e=>toast("Couldn't load Google Picker: "+e.message)); return; }
    if(ready()){ requestToken(); return; }
    // scripts still loading: show a sheet whose button gives us a fresh tap for the popup
    modal(`<div class="mh"><h3>Google Drive</h3></div><div class="mb"><p class="confirm-msg" id="dConnMsg">Connecting to Google…</p></div><div class="mf"><button class="btn ghost" data-r="no">Cancel</button><button class="btn" id="dConnGo" disabled>Continue</button></div>`,(w,close)=>{
      load().then(()=>{ if(!w.isConnected) return; w.querySelector('#dConnMsg').textContent=`Ready. Sign in with Google to ${mode==='folder'?'list the comics in your Drive folder':'choose comics from your Drive'}.`; const b=w.querySelector('#dConnGo'); b.disabled=false; b.onclick=()=>{ close('go'); requestToken(); }; })
        .catch(()=>{ if(w.isConnected) w.querySelector('#dConnMsg').textContent="Couldn't reach Google. Check your connection and try again."; }); },'drv'); }
  const ensureLoaded=()=>ready()?Promise.resolve():load();

  function requestToken(){
    tokenClient.callback=r=>{ if(r.error){ signInHelp(r.error==='access_denied'?'cancelled':'error',r.error_description||r.error); return; }
      if(!google.accounts.oauth2.hasGrantedAllScopes(r,SCOPE)){ signInHelp('scope'); return; }
      tok={t:r.access_token,exp:Date.now()+(+r.expires_in||3600)*1000}; afterToken(); };
    tokenClient.error_callback=e=>signInHelp(e&&e.type||'unknown');
    try{ tokenClient.requestAccessToken({prompt:''}); }catch(e){ signInHelp('popup_failed_to_open'); } }

  // popups are unreliable in iPad Home Screen apps: explain, offer a retry and a same-window (redirect) sign-in
  function signInHelp(kind,detail){
    const standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone;
    const msg=kind==='popup_failed_to_open'?"The Google sign-in window couldn't open (it may have been blocked as a pop-up)."
      :kind==='popup_closed'?'The Google sign-in window was closed before sign-in finished.'
      :kind==='cancelled'?'Google sign-in was cancelled.'
      :kind==='scope'?'Drive access wasn\'t granted. Tick the Google Drive permission when signing in.'
      :'Google sign-in failed'+(detail?`: ${detail}`:'.');
    modal(`<div class="mh"><h3>Sign in to Google Drive</h3></div><div class="mb"><p class="confirm-msg">${esc(msg)}</p>
      <p class="confirm-msg" style="margin-top:10px">${standalone?'In the Home Screen app, the sign-in window sometimes can\'t report back. Use <b>Sign in here</b> to sign in in this window. You\'ll come straight back to your library.':'Try again, or use <b>Sign in here</b> to sign in in this window. If pop-ups are blocked, allow them for this site in Settings → Safari.'}</p></div>
      <div class="mf"><button class="btn ghost" data-r="no">Cancel</button><button class="btn ghost" id="dRetry">Try Again</button><button class="btn" id="dRedirect">Sign in here</button></div>`,(w,close)=>{
        w.querySelector('#dRetry').onclick=()=>{ close('retry'); requestToken(); };
        w.querySelector('#dRedirect').onclick=()=>{ close('redirect'); redirectSignIn(); }; },'drv'); }
  function redirectSignIn(){ const state=uid(); try{ sessionStorage.setItem('cr.oauthState',state); sessionStorage.setItem('cr.oauthMode',mode); }catch(e){}
    const q=new URLSearchParams({client_id:GOOGLE_CLIENT_ID,redirect_uri:REDIRECT,response_type:'token',scope:SCOPE,state,include_granted_scopes:'true',prompt:'select_account'});
    location.assign('https://accounts.google.com/o/oauth2/v2/auth?'+q); }

  function showPicker(){ const P=google.picker;
    const view=new P.DocsView(P.ViewId.DOCS).setMimeTypes(DRIVE_FOLDER_IMPORT?'application/pdf,'+FOLDER:'application/pdf').setIncludeFolders(true).setSelectFolderEnabled(DRIVE_FOLDER_IMPORT).setMode(P.DocsViewMode.LIST);
    if(folder().id) view.setParent(folder().id);   // open directly in the comics folder; subfolders stay navigable
    const b=new P.PickerBuilder().addView(view).enableFeature(P.Feature.MULTISELECT_ENABLED).setOAuthToken(tok.t).setDeveloperKey(GOOGLE_API_KEY)
      .setTitle(DRIVE_FOLDER_IMPORT?'Choose comics or a folder':'Choose comics (PDF)').setCallback(onPicked).setMaxItems(200);
    if(APP_ID) b.setAppId(APP_ID); try{ b.setOrigin(location.origin); }catch(e){}
    const pk=b.build(); pk.setVisible(true); }
  async function onPicked(d){ const P=google.picker; if(d[P.Response.ACTION]!==P.Action.PICKED) return;
    const docs=d[P.Response.DOCUMENTS]||[]; let items=[];
    for(const x of docs){ const id=x[P.Document.ID], name=x[P.Document.NAME]||'Untitled.pdf', mt=x[P.Document.MIME_TYPE];
      if(mt===FOLDER){ try{ toast(`Listing “${name}”…`,{sticky:true}); items=items.concat(await listFolder(id,0,name,[folderKey(),x.resourceKey?`${id}/${x.resourceKey}`:''])); hideToast(); }catch(e){ toast(`Couldn't open folder “${name}”: ${e.message}`); } }
      else items.push({id,name,size:+(x.sizeBytes||x[P.Document.SIZE_BYTES]||0),resourceKey:x.resourceKey||''}); }
    if(items.length) importRemote(items); else toast('No PDFs found in that selection'); }
  // recursive listing (PDFs + subfolders); subfolder name becomes the series
  async function listFolder(fid,depth,series,keys){ keys=keys||[folderKey()]; let out=[], page='';
    do{ const q=new URLSearchParams({q:`'${fid}' in parents and trashed=false and (mimeType='application/pdf' or mimeType='${FOLDER}')`,fields:'nextPageToken,files(id,name,size,mimeType,resourceKey)',pageSize:'1000',orderBy:'folder,name_natural',supportsAllDrives:'true',includeItemsFromAllDrives:'true'}); if(page) q.set('pageToken',page);
      const r=await fetch('https://www.googleapis.com/drive/v3/files?'+q,{headers:{Authorization:'Bearer '+tok.t,...rkHeader(keys)}});
      if(r.status===401){ tok=null; throw new Error('Google session expired. Try again.'); } if(!r.ok) throw new Error(r.status===404?'Folder not found or no access (HTTP 404)':'HTTP '+r.status); const j=await r.json();
      for(const f of j.files||[]){ const k=f.resourceKey?`${f.id}/${f.resourceKey}`:'';
        if(f.mimeType===FOLDER){ if(depth<4) out=out.concat(await listFolder(f.id,depth+1,f.name,k?keys.concat(k):keys)); }
        else out.push({id:f.id,name:f.name,size:+f.size||0,resourceKey:f.resourceKey||'',series:series||'',keys:k?keys.concat(k):keys}); }
      page=j.nextPageToken||''; }while(page);
    return out; }
  const inLib=it=>comics.some(c=>(c.driveId&&c.driveId===it.id)||(it.size&&c.size===it.size&&c.fileName===it.name));

  /* ---------- Import Entire Folder: list, then a checklist sheet ---------- */
  async function folderFlow(){ const f=folder();
    toast(`Listing “${f.name||'Drive folder'}”…`,{sticky:true});
    let items, fname=f.name||'Drive folder';
    try{ const mr=await fetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(f.id)}?fields=name&supportsAllDrives=true`,{headers:{Authorization:'Bearer '+tok.t,...rkHeader([folderKey()])}});
      if(mr.ok) fname=(await mr.json()).name||fname;
      items=await listFolder(f.id,0,''); hideToast(); }
    catch(e){ toast(`Couldn't list the Drive folder: ${e.message}`); return; }
    if(!items.length){ toast(`No PDFs found in “${fname}”`); return; }
    checklist(items,fname); }
  function checklist(items,fname){
    items.forEach((it,i)=>{ it.k=i; it.dup=inLib(it); it.on=!it.dup; });
    const groups=[]; for(const it of items){ let g=groups.find(x=>x.s===it.series); if(!g) groups.push(g={s:it.series,list:[]}); g.list.push(it); }
    const row=it=>`<label class="ckr${it.dup?' dup':''}"><input type="checkbox" data-k="${it.k}" ${it.on?'checked':''}><span class="ckt"><b>${esc(titleFromName(it.name))}</b><small>${it.size?fmtBytes(it.size):''}${it.dup?' · In library':''}</small></span></label>`;
    return modal(`<div class="mh"><h3>${esc(fname)}</h3><p class="dlsub" id="ckSub"></p>
        <div class="ckbar"><button class="lnk" id="ckAll">Select All</button><button class="lnk" id="ckNone">Select None</button></div></div>
      <div class="dllist ck">${groups.map(g=>`${g.s?`<div class="ckg">${esc(g.s)}</div>`:''}${g.list.map(row).join('')}`).join('')}</div>
      <div class="mf"><button class="btn ghost" data-r="no">Cancel</button><button class="btn" id="ckGo">Import</button></div>`,(w,close)=>{
        const sync=()=>{ const sel=items.filter(x=>x.on); const T=sel.reduce((a,x)=>a+(x.size||0),0);
          w.querySelector('#ckSub').textContent=`${items.length} PDFs · ${items.filter(x=>x.dup).length} already in library · ${sel.length} selected (${fmtBytes(T)})`;
          const b=w.querySelector('#ckGo'); b.textContent=sel.length?`Import ${sel.length}`:'Import'; b.disabled=!sel.length; };
        w.addEventListener('change',e=>{ const c=e.target.closest('input[data-k]'); if(c){ items[+c.dataset.k].on=c.checked; sync(); } });
        const setAll=v=>{ items.forEach(x=>{ x.on=v&&!x.dup; }); w.querySelectorAll('input[data-k]').forEach(c=>c.checked=items[+c.dataset.k].on); sync(); };
        w.querySelector('#ckAll').onclick=()=>setAll(true); w.querySelector('#ckNone').onclick=()=>setAll(false);
        w.querySelector('#ckGo').onclick=()=>{ const sel=items.filter(x=>x.on); close('go'); importRemote(sel); };
        sync(); },'drv ckm'); }

  /* ---------- streamed download -> 4 MB IndexedDB chunks (bounded memory), with a progress sheet ---------- */
  async function streamToChunks(id,resp,onProg,signal){
    let ci=0, got=0;
    if(!resp.body||!resp.body.getReader){ const ab=await resp.arrayBuffer(); for(let o=0;o<ab.byteLength;o+=CHUNK){ await dbPutChunk(id,ci++,ab.slice(o,o+CHUNK)); } onProg(ab.byteLength); return ab.byteLength; }
    const rd=resp.body.getReader(); let buf=new Uint8Array(CHUNK), fill=0;
    try{ for(;;){ if(signal.aborted) throw new DOMException('Cancelled','AbortError');
        const {done,value}=await rd.read(); if(done) break; let off=0;
        while(off<value.length){ const n=Math.min(CHUNK-fill,value.length-off); buf.set(value.subarray(off,off+n),fill); fill+=n; off+=n;
          if(fill===CHUNK){ await dbPutChunk(id,ci++,buf.buffer); buf=new Uint8Array(CHUNK); fill=0; } }
        got+=value.length; onProg(got); }
    }catch(e){ try{ rd.cancel().catch(()=>{}); }catch(_){} throw e; }
    if(fill) await dbPutChunk(id,ci++,buf.slice(0,fill).buffer);
    return got; }

  let ctl=null;
  async function importRemote(items,{auth=true}={}){
    if(importing){ toast('Already importing…'); return; } importing=true; ctl=new AbortController(); const signal=ctl.signal;
    try{ if(navigator.storage&&navigator.storage.persist) navigator.storage.persist().catch(()=>{}); }catch(e){}
    const rows=items.map((it,k)=>({...it,k,got:0,st:'wait',msg:'Waiting'}));
    const w=document.createElement('div'); w.className='mwrap dlwrap'; w.innerHTML=`<div class="modal dl" role="dialog" aria-modal="true" aria-label="Importing from Google Drive">
      <div class="mh"><h3 id="dlHead">Importing from Google Drive</h3><p class="dlsub" id="dlSub"></p><div class="dlbar all"><i id="dlAll"></i></div></div>
      <div class="dllist">${rows.map(r=>`<div class="dlr" data-k="${r.k}"><div class="dlt"><b>${esc(titleFromName(r.name))}</b><span class="dlp">0%</span></div><div class="dlbar"><i></i></div><div class="dls">Waiting</div></div>`).join('')}</div>
      <div class="mf"><button class="btn ghost" id="dlCancel">Cancel</button></div></div>`; document.body.appendChild(w);
    const total=()=>rows.reduce((a,r)=>a+(r.size||0),0);
    let last=0; const paint=(force)=>{ const now=performance.now(); if(!force&&now-last<90) return; last=now;
      for(const r of rows){ const el=w.querySelector(`.dlr[data-k="${r.k}"]`); const p=r.st==='done'?1:r.size?Math.min(1,r.got/r.size):0;
        el.className='dlr '+r.st; el.querySelector('.dlbar i').style.width=(p*100).toFixed(1)+'%'; el.querySelector('.dlp').textContent=r.st==='skip'?'—':r.st==='fail'||r.st==='cancel'?'':Math.round(p*100)+'%'; el.querySelector('.dls').textContent=r.msg; }
      const T=total(), G=rows.reduce((a,r)=>a+(r.st==='done'||r.st==='skip'?(r.size||r.got):Math.min(r.got,r.size||r.got)),0); const fin=rows.filter(r=>/done|skip|fail|cancel/.test(r.st)).length;
      w.querySelector('#dlAll').style.width=(T?Math.min(1,G/T)*100:fin/rows.length*100).toFixed(1)+'%';
      w.querySelector('#dlSub').textContent=`${Math.min(fin+1,rows.length)} of ${rows.length}`+(T?` · ${fmtBytes(G)} of ${fmtBytes(T)}`:''); };
    w.querySelector('#dlCancel').onclick=()=>{ if(ctl&&!signal.aborted) ctl.abort(); else w.remove(); };
    paint(true); let ok=0,skip=0,fail=0, wl=null; try{ if(navigator.wakeLock) wl=await navigator.wakeLock.request('screen'); }catch(e){}
    for(const r of rows){
      if(signal.aborted){ r.st='cancel'; r.msg='Cancelled'; paint(true); continue; }
      if(inLib(r)){ r.st='skip'; r.msg='Already in your library'; skip++; paint(true); continue; }
      const id=uid(); let doc=null; r.st='dl'; r.msg='Downloading…'; paint(true);
      try{
        const resp=await fetch(r.url||`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(r.id)}?alt=media&supportsAllDrives=true`,{headers:auth&&tok?{Authorization:'Bearer '+tok.t,...rkHeader((r.keys||[folderKey()]).concat(r.resourceKey?[`${r.id}/${r.resourceKey}`]:[]))}:{},signal,cache:'no-store'});
        if(!resp.ok){ if(resp.status===401){ tok=null; throw new Error('Google session expired. Tap From Google Drive again.'); }
          throw new Error(resp.status===403||resp.status===404?"No access to this file (HTTP "+resp.status+")":'HTTP '+resp.status); }
        if(!r.size) r.size=+resp.headers.get('content-length')||0;
        const got=await streamToChunks(id,resp,n=>{ r.got=n; r.msg=`${fmtBytes(n)}${r.size?' of '+fmtBytes(r.size):''}`; paint(); },signal);
        r.size=got; r.st='proc'; r.msg='Preparing cover…'; paint(true);
        doc=await openPdf(new IDBSource(id,got));
        const page=await doc.getPage(1); const vp=page.getViewport({scale:1});
        const cc=await renderToCanvas(page,360,540,1,400000); const coverBlob=await (await toBlob(cc,.82)).arrayBuffer(); freeCanvas(cc); page.cleanup();
        const pages=doc.numPages; await doc.destroy(); doc=null;
        const t0=titleFromName(r.name); const rec={id,title:t0,series:r.series||seriesGuess(t0),fileName:r.name,size:got,pages,aspect:vp.width/vp.height,cover:coverBlob,added:Date.now()+r.k,lastRead:0,page:0,progress:0,rtl:false,driveId:r.id,source:'drive'};
        await dbPut(rec); comics.push(rec); ok++; r.st='done'; r.msg=`${pages} pages · ${fmtBytes(got)}`; renderShelf();
      }catch(err){ try{ if(doc) await doc.destroy(); }catch(e){} try{ await dbDelete(id); }catch(e){}
        if(signal.aborted||err.name==='AbortError'){ r.st='cancel'; r.msg='Cancelled'; }
        else { fail++; r.st='fail'; const quota=err&&(err.name==='QuotaExceededError'||/quota/i.test(err.message||'')); r.msg=quota?'Out of storage space':/Invalid PDF|PDF header|InvalidPDF/i.test(err.message||'')?'Not a valid PDF':(err.message||'Download failed'); console.warn('drive import failed',err); } }
      paint(true);
    }
    importing=false; ctl=null; renderShelf(); try{ wl&&wl.release(); }catch(e){}
    w.querySelector('#dlHead').textContent=signal.aborted?'Import cancelled':fail?'Import finished with problems':'Import complete';
    w.querySelector('#dlSub').textContent=[ok&&`${ok} imported`,skip&&`${skip} already in library`,fail&&`${fail} failed`,signal.aborted&&'cancelled'].filter(Boolean).join(' · ')||'Nothing imported';
    const b=w.querySelector('#dlCancel'); b.textContent='Done'; b.className='btn'; b.id='dlDone'; b.onclick=()=>w.remove();
    if(ok&&!fail&&!signal.aborted&&!skip) setTimeout(()=>w.isConnected&&w.remove(),1600);
    return {ok,skip,fail}; }

  if(resumePicker&&configured()) addEventListener('load',()=>load().then(afterToken).catch(e=>toast("Couldn't load Google Picker: "+e.message)));
  const setFolder=f=>{ if(f) store.set('driveFolder',f); else { try{ localStorage.removeItem('cr.driveFolder'); }catch(e){} } };
  return {start,preload,importRemote,configured,folder,setFolder,parseFolderLink,checklist,get scope(){return SCOPE},get busy(){return !!ctl},_setToken:t=>{tok=t?{t,exp:Date.now()+3600e3}:null;}};
})();

/* + button: small import menu */
const IC_DRIVE='<svg class="i" viewBox="0 0 24 24"><path d="M8.5 3h7l6 10.5-3.5 6h-12L2.5 13.5z"/><path d="M8.5 3 12 9.5m3.5-6L9 15H2.5m19-1.5H12L8.5 19.5"/></svg>';
const IC_FOLDER='<svg class="i" viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M12 10v6m-3-3 3 3 3-3"/></svg>';
const IC_FILES='<svg class="i" viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>';
function importMenu(anchor){ Drive.preload();
  openMenu(anchor,[{label:'From Google Drive',icon:IC_DRIVE,id:'miDrive',run:()=>Drive.start('pick')},{label:'Import Entire Drive Folder',icon:IC_FOLDER,id:'miFolder',run:()=>Drive.start('folder')},{label:'From Files',icon:IC_FILES,id:'miFiles',run:()=>$('#fileIn').click()}],'imp'); }
$('#importBtn').onclick=e=>importMenu(e.currentTarget);
