import * as pdfjsLib from './vendor/pdf.min.mjs';
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('./vendor/pdf.worker.min.mjs', import.meta.url).href;
const VENDOR = new URL('./vendor/', import.meta.url).href;

/* ================= utils ================= */
const $=s=>document.querySelector(s);
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const uid=()=>(crypto.randomUUID?crypto.randomUUID():Date.now().toString(36)+Math.random().toString(36).slice(2));
const fmtBytes=b=>b<1024?b+' B':b<1048576?(b/1024).toFixed(0)+' KB':b<1073741824?(b/1048576).toFixed(1)+' MB':(b/1073741824).toFixed(2)+' GB';
const IS_IOS=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
const DPR=Math.min(window.devicePixelRatio||1, 2);
const BASE_MAX_PX = IS_IOS? 4.2e6 : 6e6;   // per page bitmap
const HI_MAX_PX   = IS_IOS? 12e6 : 16e6;   // zoomed re-render (iOS canvas limit is 16.7 MP)
const CACHE_BUDGET= IS_IOS? 30e6 : 70e6;   // total pixels kept in the bitmap LRU (~4 bytes each)
const CHUNK=4*1024*1024;                    // PDFs are stored in 4 MB chunks and read by range
const store={get:(k,d)=>{try{const v=localStorage.getItem('cr.'+k);return v==null?d:JSON.parse(v)}catch(e){return d}},set:(k,v)=>{try{localStorage.setItem('cr.'+k,JSON.stringify(v))}catch(e){}}};
function titleFromName(n){ return n.replace(/\.pdf$/i,'').replace(/_+/g,' ').replace(/\s+/g,' ').trim()||'Untitled'; }

/* ================= IndexedDB ================= */
let dbp=null;
function db(){ if(dbp) return dbp; dbp=new Promise((res,rej)=>{ const r=indexedDB.open('comic-reader',1);
  r.onupgradeneeded=()=>{ const d=r.result; if(!d.objectStoreNames.contains('comics')) d.createObjectStore('comics',{keyPath:'id'}); if(!d.objectStoreNames.contains('chunks')) d.createObjectStore('chunks',{keyPath:['id','i']}); };
  r.onsuccess=()=>res(r.result); r.onerror=()=>rej(r.error); }); return dbp; }
const req2p=r=>new Promise((res,rej)=>{ r.onsuccess=()=>res(r.result); r.onerror=()=>rej(r.error); });
const txDone=t=>new Promise((res,rej)=>{ t.oncomplete=()=>res(); t.onerror=()=>rej(t.error); t.onabort=()=>rej(t.error||new Error('aborted')); });
async function dbAll(){ const d=await db(); return req2p(d.transaction('comics').objectStore('comics').getAll()); }
async function dbPut(rec){ const d=await db(); const t=d.transaction('comics','readwrite'); t.objectStore('comics').put(rec); return txDone(t); }
async function dbPutChunk(id,i,data){ const d=await db(); const t=d.transaction('chunks','readwrite'); t.objectStore('chunks').put({id,i,data}); return txDone(t); }
async function dbGetChunk(id,i){ const d=await db(); const r=await req2p(d.transaction('chunks').objectStore('chunks').get([id,i])); return r&&r.data; }
async function dbDelete(id){ const d=await db(); const t=d.transaction(['comics','chunks'],'readwrite'); t.objectStore('comics').delete(id); t.objectStore('chunks').delete(IDBKeyRange.bound([id,0],[id,Infinity])); return txDone(t); }

/* ================= PDF sources: range reads, never the whole file in memory ================= */
class FileSource{ constructor(f){this.f=f;this.size=f.size} read(a,b){ return this.f.slice(a,b).arrayBuffer(); } }
class IDBSource{
  constructor(id,size){ this.id=id; this.size=size; this.cache=new Map(); }
  async chunk(i){ if(this.cache.has(i)){ const c=this.cache.get(i); this.cache.delete(i); this.cache.set(i,c); return c; }
    let c=await dbGetChunk(this.id,i); if(!c) throw new Error('Missing data chunk '+i);
    if(c instanceof Blob) c=await c.arrayBuffer();
    this.cache.set(i,c); while(this.cache.size>3) this.cache.delete(this.cache.keys().next().value); return c; }
  async read(a,b){ b=Math.min(b,this.size); const out=new Uint8Array(Math.max(0,b-a)); let pos=a;
    while(pos<b){ const ci=Math.floor(pos/CHUNK), off=pos-ci*CHUNK; const c=await this.chunk(ci); const n=Math.min(c.byteLength-off,b-pos); if(n<=0) break; out.set(new Uint8Array(c,off,n),pos-a); pos+=n; }
    return out.buffer; }
}
let sharedWorker=null;
async function openPdf(src){
  if(!sharedWorker) sharedWorker=new pdfjsLib.PDFWorker({name:'cr'});
  const first=await src.read(0,Math.min(src.size,65536));
  class T extends pdfjsLib.PDFDataRangeTransport{ requestDataRange(a,b){ src.read(a,b).then(buf=>this.onDataRange(a,new Uint8Array(buf))).catch(e=>console.warn('range read failed',e)); } }
  const transport=new T(src.size,new Uint8Array(first));
  const task=pdfjsLib.getDocument({range:transport,length:src.size,worker:sharedWorker,disableAutoFetch:true,disableStream:true,rangeChunkSize:524288,
    cMapUrl:VENDOR+'cmaps/',cMapPacked:true,standardFontDataUrl:VENDOR+'standard_fonts/',isEvalSupported:false,verbosity:pdfjsLib.VerbosityLevel.ERRORS});
  return task.promise;
}
async function renderToCanvas(page,maxW,maxH,dpr,maxPx){
  const vp1=page.getViewport({scale:1});
  let s=Math.min(maxW/vp1.width,maxH/vp1.height)*dpr; const px=vp1.width*s*vp1.height*s; if(px>maxPx) s*=Math.sqrt(maxPx/px);
  const vp=page.getViewport({scale:s}); const c=document.createElement('canvas'); c.width=Math.max(1,Math.floor(vp.width)); c.height=Math.max(1,Math.floor(vp.height));
  const ctx=c.getContext('2d',{alpha:false}); ctx.fillStyle='#fff'; ctx.fillRect(0,0,c.width,c.height);
  await page.render({canvasContext:ctx,viewport:vp,intent:'display'}).promise;
  return c;
}
const toBlob=(c,q=.8)=>new Promise(r=>c.toBlob(b=>r(b),'image/jpeg',q));
const freeCanvas=c=>{ if(c){ c.width=0; c.height=0; } };

