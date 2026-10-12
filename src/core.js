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
function db(){ if(dbp) return dbp; dbp=new Promise((res,rej)=>{ const r=indexedDB.open('comic-reader',3);   // v2: + reading lists ('queues'); v3: + per-file overrides ('overrides': manual dates)
  r.onupgradeneeded=()=>{ const d=r.result; if(!d.objectStoreNames.contains('comics')) d.createObjectStore('comics',{keyPath:'id'}); if(!d.objectStoreNames.contains('chunks')) d.createObjectStore('chunks',{keyPath:['id','i']});
    if(!d.objectStoreNames.contains('queues')) d.createObjectStore('queues',{keyPath:'id'}); if(!d.objectStoreNames.contains('overrides')) d.createObjectStore('overrides',{keyPath:'k'}); };
  r.onsuccess=()=>res(r.result); r.onerror=()=>rej(r.error); }); return dbp; }
const req2p=r=>new Promise((res,rej)=>{ r.onsuccess=()=>res(r.result); r.onerror=()=>rej(r.error); });
const txDone=t=>new Promise((res,rej)=>{ t.oncomplete=()=>res(); t.onerror=()=>rej(t.error); t.onabort=()=>rej(t.error||new Error('aborted')); });
async function ovAll(){ const d=await db(); return req2p(d.transaction('overrides').objectStore('overrides').getAll()); }
async function ovPut(rec){ const d=await db(); const t=d.transaction('overrides','readwrite'); t.objectStore('overrides').put(rec); return txDone(t); }
async function ovDel(k){ const d=await db(); const t=d.transaction('overrides','readwrite'); t.objectStore('overrides').delete(k); return txDone(t); }
async function dbAll(){ const d=await db(); return req2p(d.transaction('comics').objectStore('comics').getAll()); }
async function dbPut(rec){ const d=await db(); const t=d.transaction('comics','readwrite'); t.objectStore('comics').put(rec); return txDone(t); }
async function dbPutChunk(id,i,data){ const d=await db(); const t=d.transaction('chunks','readwrite'); t.objectStore('chunks').put({id,i,data}); return txDone(t); }
async function dbGetChunk(id,i){ const d=await db(); const r=await req2p(d.transaction('chunks').objectStore('chunks').get([id,i])); return r&&r.data; }
// reading lists: {id, name, items:[comic ids in reading order], created, updated}
async function qAll(){ const d=await db(); return req2p(d.transaction('queues').objectStore('queues').getAll()); }
async function qPut(q){ const d=await db(); const t=d.transaction('queues','readwrite'); t.objectStore('queues').put(q); return txDone(t); }
async function qDel(id){ const d=await db(); const t=d.transaction('queues','readwrite'); t.objectStore('queues').delete(id); return txDone(t); }
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
// WebKit/iPadOS: images on the FIRST pdf.js document of a session may not paint (blank covers / pages). Rendering a tiny
// built-in PDF (a JPEG + a Flate image + text) once per session warms pdf.js up so real comics render fully.
const WARM_PDF='JVBERi0xLjMKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgKG9wZW5zb3VyY2UpCjEgMCBvYmoKPDwKL0YxIDIgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0aWNhIC9FbmNvZGluZyAvV2luQW5zaUVuY29kaW5nIC9OYW1lIC9GMSAvU3VidHlwZSAvVHlwZTEgL1R5cGUgL0ZvbnQKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0JpdHNQZXJDb21wb25lbnQgOCAvQ29sb3JTcGFjZSAvRGV2aWNlUkdCIC9GaWx0ZXIgWyAvQVNDSUk4NURlY29kZSAvRENURGVjb2RlIF0gL0hlaWdodCA4IC9MZW5ndGggNzg4IC9TdWJ0eXBlIC9JbWFnZSAKICAvVHlwZSAvWE9iamVjdCAvV2lkdGggOAo+PgpzdHJlYW0KczRJQTAhIl9hbDhPYFtcITw8KiMhISonInM0W05AISJdTUglTGBbVSVMaW1cJkosVG0tbE5wPCgpU2JOLG9uQnAxSGRpXDFINzxZODZlblQ2cnVmOTMpRkhoPSdvRUxCUDBNJ0VIdU02R1srZm1BLGs5YDZOSWMzJmY7PyMwLGJgXkBtVy5BQHEwIllAcTAiWUBxMCJZQHEwIllAcTAiWUBxMCJZQHEwIllAcTAiWUBxMCJZQHEwIllAcTAiWUBxMCJZQHE1UFMhImZKOiNRUCw0IT9xTEYmSE10RyFXVSg8KnJsOUEiVFxXKSE8RTMkeiEhISEiIVdyUS8icFlEPyQ0SG1QITQ8QDwhV2BCKiFYJlQvIlUici4hIS5LSyFXckUqJkhyZGowZ1EhVzsuMFxSRT4xMFpPZUUlKjZGIj9BO1VPdFoxTGJCViNtcUZhKGA9NTwtNzoyai5QcyJAMmBOZlk2VVhANDduPzNEO2NIYXQ9Jy9VL0BxOS5fQjR1IW9GKilQSkdCZUNaSzducjVMUFVlRVAqOyxxUUMhdSxSXEhSUVY1Qy9oV04qODFbJ2Q/T1xASzJmX28wTzZhMmxCRmRhUV5yZiU4Ui1nPlYmT2pRNU9la2lxQyZvKDJNSHBAbkBYcVoiSjYqcnU/RCE8RTMlITxFMyUhPDwqIiEhISEiIVdyUS8icFlEPyQ0SG1QITQ8Qz0hV2A/KiI5U2MzIlUici4hPFJIRiE8Tj84IjlmcicicWo0ISNAVlRjK3U0XVQnTElxVVosJF9rMUsqXVdAV0tqJygqa2BxLTFNY2cpJmFoTC1uLVcnMkUqVFUzXlo7KDdScCFAOGxKXGg8YGBDKz4lOylTQW5QZGtDMytLPkcnQTFWSEBnZCZLbmJBPU0ySUlbUGEuUSRSJGpEO1VTT2BgVmw2U3BaRXBwR1teV2NXXSMpQSdgUSNzPmFpYCZcZUNFLiVmXCwhPGo1Zj1ha05NMHFvKDJNSHBAbkBYcVojN0wkai1NMSFZR01IISdeSixVNUNJV3FJQlFZfj5lbmRzdHJlYW0KZW5kb2JqCjQgMCBvYmoKPDwKL0JpdHNQZXJDb21wb25lbnQgOCAvQ29sb3JTcGFjZSAvRGV2aWNlUkdCIC9GaWx0ZXIgWyAvQVNDSUk4NURlY29kZSAvRmxhdGVEZWNvZGUgXSAvSGVpZ2h0IDggL0xlbmd0aCAyMCAvU3VidHlwZSAvSW1hZ2UgCiAgL1R5cGUgL1hPYmplY3QgL1dpZHRoIDgKPj4Kc3RyZWFtCkdiITVCVHFPMyomSEhCMzdLRX4+ZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqCjw8Ci9Db250ZW50cyA5IDAgUiAvTWVkaWFCb3ggWyAwIDAgMTYgMTYgXSAvUGFyZW50IDggMCBSIC9SZXNvdXJjZXMgPDwKL0ZvbnQgMSAwIFIgL1Byb2NTZXQgWyAvUERGIC9UZXh0IC9JbWFnZUIgL0ltYWdlQyAvSW1hZ2VJIF0gL1hPYmplY3QgPDwKL0Zvcm1Yb2IuYWI3ZTUzNWE3OWY5MmRhNDZkYzIwOTc4YmRmMzE1NmYgMyAwIFIgL0Zvcm1Yb2IuZTRhZTQxZWUwYzMxMDYzMDg2NmJlZmI0OTdkOGJjOWUgNCAwIFIKPj4KPj4gL1JvdGF0ZSAwIC9UcmFucyA8PAoKPj4gCiAgL1R5cGUgL1BhZ2UKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL1BhZ2VNb2RlIC9Vc2VOb25lIC9QYWdlcyA4IDAgUiAvVHlwZSAvQ2F0YWxvZwo+PgplbmRvYmoKNyAwIG9iago8PAovQXV0aG9yIChhbm9ueW1vdXMpIC9DcmVhdGlvbkRhdGUgKEQ6MjAyNjEwMDMwNjMwMTctMDUnMDAnKSAvQ3JlYXRvciAoYW5vbnltb3VzKSAvS2V5d29yZHMgKCkgL01vZERhdGUgKEQ6MjAyNjEwMDMwNjMwMTctMDUnMDAnKSAvUHJvZHVjZXIgKFJlcG9ydExhYiBQREYgTGlicmFyeSAtIFwob3BlbnNvdXJjZVwpKSAKICAvU3ViamVjdCAodW5zcGVjaWZpZWQpIC9UaXRsZSAodW50aXRsZWQpIC9UcmFwcGVkIC9GYWxzZQo+PgplbmRvYmoKOCAwIG9iago8PAovQ291bnQgMSAvS2lkcyBbIDUgMCBSIF0gL1R5cGUgL1BhZ2VzCj4+CmVuZG9iago5IDAgb2JqCjw8Ci9GaWx0ZXIgWyAvQVNDSUk4NURlY29kZSAvRmxhdGVEZWNvZGUgXSAvTGVuZ3RoIDE5OQo+PgpzdHJlYW0KR2FxS2hdKzJcMyRxOW88YD5zTidgL1U4LE1QKFVqOz9rXTcjR2VBT0wjOGRbKTYsMzRZalteNyQkJD5oMUpQWyhqI2RzUUxUX2lnKSNmUGIoTjNga05icUwxKnA6bEFTNzxBMC4+Jk9qRVJqX0JZZzA1N2NJZU1iVS1WamNCQ1hYRUNcRS83Om1hazs4V2hMcD4tMjs2T2UnVFAtPEwxb29BV2MuNDU2aiYvW1loTDhHRUxIbWgsTyZJcDI6UDU+XGdIKT9+PmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDEwCjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDA2MSAwMDAwMCBuIAowMDAwMDAwMDkyIDAwMDAwIG4gCjAwMDAwMDAxOTkgMDAwMDAgbiAKMDAwMDAwMTE3MSAwMDAwMCBuIAowMDAwMDAxMzc2IDAwMDAwIG4gCjAwMDAwMDE2NzggMDAwMDAgbiAKMDAwMDAwMTc0NiAwMDAwMCBuIAowMDAwMDAyMDA3IDAwMDAwIG4gCjAwMDAwMDIwNjYgMDAwMDAgbiAKdHJhaWxlcgo8PAovSUQgCls8MjE2YmExYTQ1MGQyODg2NDc3Y2NkZmEzYmI4N2ZhOWI+PDIxNmJhMWE0NTBkMjg4NjQ3N2NjZGZhM2JiODdmYTliPl0KJSBSZXBvcnRMYWIgZ2VuZXJhdGVkIFBERiBkb2N1bWVudCAtLSBkaWdlc3QgKG9wZW5zb3VyY2UpCgovSW5mbyA3IDAgUgovUm9vdCA2IDAgUgovU2l6ZSAxMAo+PgpzdGFydHhyZWYKMjM1NQolJUVPRgo=';
let warmP=null;
function warmPdf(){ if(!warmP) warmP=(async()=>{ try{ const bin=atob(WARM_PDF), u8=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) u8[i]=bin.charCodeAt(i);
    const doc=await pdfjsLib.getDocument({data:u8,worker:sharedWorker,isEvalSupported:false,standardFontDataUrl:VENDOR+'standard_fonts/',verbosity:0}).promise;
    const page=await doc.getPage(1); const c=document.createElement('canvas'); c.width=16; c.height=16;
    await page.render({canvasContext:c.getContext('2d'),viewport:page.getViewport({scale:1})}).promise; freeCanvas(c); await doc.destroy(); }catch(e){ console.warn('pdf warm-up skipped',e); } })();
  return warmP; }
async function openPdf(src){
  if(!sharedWorker) sharedWorker=new pdfjsLib.PDFWorker({name:'cr'});
  await warmPdf();
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


/* ================= covers: wide-spread detection, half pick, black-margin trim ================= */
const COVER_V=2;
// stats of a region of a small RGBA sample: mean luminance, std-dev, share of "ink" (non-near-black/non-near-white) pixels
function regionStats(d,W,x0,y0,x1,y1){ let n=0,s=0,s2=0,ink=0;
  for(let y=y0;y<y1;y++) for(let x=x0;x<x1;x++){ const i=(y*W+x)*4, l=.299*d[i]+.587*d[i+1]+.114*d[i+2]; n++; s+=l; s2+=l*l; if(l>40&&l<235) ink++; }
  const m=s/Math.max(1,n); return {mean:m,std:Math.sqrt(Math.max(0,s2/Math.max(1,n)-m*m)),ink:ink/Math.max(1,n)}; }
const isBlank=st=>(st.mean<45&&st.std<28)||(st.mean>225&&st.std<22)||st.ink<0.04;
// find near-black bands at the edges of [x0,x1)x[y0,y1) in the sample; returns trimmed box (sample coords)
function trimBlack(d,W,x0,y0,x1,y1,cols=true){
  // letterbox = rows/cols that are essentially pure black (scanner bands), not just dark artwork
  const rowDark=y=>{ let lit=0,sum=0; for(let x=x0;x<x1;x++){ const i=(y*W+x)*4, v=d[i]+d[i+1]+d[i+2]; sum+=v; if(v>3*30) lit++; } return lit/(x1-x0)<0.01&&sum/(x1-x0)<3*9; };
  const colDark=x=>{ let lit=0,sum=0; for(let y=y0;y<y1;y++){ const i=(y*W+x)*4, v=d[i]+d[i+1]+d[i+2]; sum+=v; if(v>3*30) lit++; } return lit/(y1-y0)<0.01&&sum/(y1-y0)<3*9; };
  const mh=Math.floor((y1-y0)*0.3), mw=cols?Math.floor((x1-x0)*0.15):0; let t=y0,b=y1,l=x0,r=x1;
  while(t-y0<mh&&rowDark(t)) t++; while(y1-b<mh&&rowDark(b-1)) b--;
  while(l-x0<mw&&colDark(l)) l++; while(x1-r<mw&&colDark(r-1)) r--;
  if((r-l)<(x1-x0)*0.4||(b-t)<(y1-y0)*0.4) return [x0,y0,x1,y1];   // mostly black: don't trim
  return [l,t,r,b]; }
// mode: auto | right | left | full.  Returns {cover:ArrayBuffer(jpeg), crop:{mode,side,x,y,w,h} (fractions of page 1)}
async function makeCover(page,mode='auto'){
  const vp1=page.getViewport({scale:1}), maybe=vp1.width>vp1.height*0.95;
  const big=await renderToCanvas(page,maybe?820:420,640,1,maybe?900000:500000);
  const SW=maybe?128:64, SH=Math.max(8,Math.round(SW*big.height/big.width));
  const sm=document.createElement('canvas'); sm.width=SW; sm.height=SH; const sx=sm.getContext('2d',{willReadFrequently:true}); try{ big.getContext('2d').getImageData(0,0,1,1); }catch(e){}   // WebKit: force the rendered canvas to flush before copying it
  sx.drawImage(big,0,0,SW,SH);
  const d=sx.getImageData(0,0,SW,SH).data; freeCanvas(sm);
  // "wide" = a two-page spread scan: judged on the content after removing black letterbox bands
  const [,ty,,by]=trimBlack(d,SW,0,0,SW,SH,false); const wide=maybe&&vp1.width>vp1.height*((by-ty)/SH)*1.15;
  let side='full';
  if(mode==='right'||mode==='left') side=mode;
  else if(mode==='auto'&&wide){ const L=regionStats(d,SW,0,0,SW>>1,SH), Rr=regionStats(d,SW,SW>>1,0,SW,SH);
    side=(isBlank(Rr)&&!isBlank(L))?'left':'right'; }          // left usually the blank back cover; default right
  let x0=side==='right'?SW>>1:0, x1=side==='left'?SW>>1:SW;
  const [l,t,r,b]=trimBlack(d,SW,x0,0,x1,SH,side!=='full');
  const crop={mode,side,x:l/SW,y:t/SH,w:(r-l)/SW,h:(b-t)/SH};
  const px=crop.x*big.width, py=crop.y*big.height, pw=crop.w*big.width, ph=crop.h*big.height;
  const s=Math.min(1,360/pw,540/ph), out=document.createElement('canvas'); out.width=Math.max(1,Math.round(pw*s)); out.height=Math.max(1,Math.round(ph*s));
  out.getContext('2d',{alpha:false}).drawImage(big,px,py,pw,ph,0,0,out.width,out.height); freeCanvas(big);
  const cover=await (await toBlob(out,.82)).arrayBuffer(); freeCanvas(out);   // bytes (Blobs in IDB fail in some WebKit modes)
  return {cover,crop,wide}; }
// page-1 metadata for a new record; aspect comes from page 2 when page 1 is a wide spread scan
async function coverMeta(doc,mode='auto'){
  const page=await doc.getPage(1); const vp=page.getViewport({scale:1}); const cv=await makeCover(page,mode); page.cleanup();
  let aspect=vp.width/vp.height;
  if(cv.wide&&doc.numPages>1){ try{ const p2=await doc.getPage(2); const v2=p2.getViewport({scale:1}); aspect=v2.width/v2.height; p2.cleanup(); }catch(e){} }
  let metaDate=null; try{ metaDate=await pdfDate(doc); }catch(e){}
  return {cover:cv.cover,coverCrop:cv.crop,coverMode:mode,coverV:COVER_V,aspect,metaDate,dateV:DATE_V}; }

/* ================= release dates (Timeline) =================
   Order of trust: manual (set by David) > embedded metadata (ComicInfo.xml attached to the PDF, XMP prism:coverDate /
   publicationDate) > a year in the file name or title ("(1983)", "(Mar 1983)", "1983-03") > built-in table of well-known
   series (estimate from #1's cover date + monthly cadence) > Unknown.  PDF CreationDate/ModDate are NOT used: they are the
   scan/export date, not the cover date. */
const DATE_V=2, MON=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
const okY=y=>y>=1930&&y<=2039;
const monOf=t=>{ const i=MON.indexOf(String(t||'').slice(0,3).toLowerCase()); return i<0?0:i+1; };
function dateFromName(n){ const s=String(n||'').replace(/_/g,' ');
  let m=s.match(/[([]\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?[\s,-]*((?:19|20)\d\d)\s*[)\]]/i); if(m&&okY(+m[2])) return {y:+m[2],m:monOf(m[1]),src:'name'};
  m=s.match(/[([]\s*((?:19|20)\d\d)[-./](0?[1-9]|1[0-2])\s*[)\]]/); if(m&&okY(+m[1])) return {y:+m[1],m:+m[2],src:'name'};
  m=s.match(/[([]\s*((?:19|20)\d\d)\s*[)\]]/); if(m&&okY(+m[1])) return {y:+m[1],m:0,src:'name'};
  m=s.match(/(?:^|[\s-])((?:19|20)\d\d)-(0[1-9]|1[0-2])(?:[\s-]|$)/); if(m&&okY(+m[1])) return {y:+m[1],m:+m[2],src:'name'};
  return null; }
function comicInfoDate(xml){ const g=k=>{ const m=String(xml).match(new RegExp('<'+k+'>\\s*(\\d+)\\s*</'+k+'>','i')); return m?+m[1]:0; };
  const y=g('Year'), m=g('Month'); return okY(y)?{y,m:m>=1&&m<=12?m:0,src:'meta'}:null; }
function isoDate(v,src){ const m=String(v||'').match(/((?:19|20)\d\d)(?:-(\d\d))?/); return m&&okY(+m[1])?{y:+m[1],m:m[2]&&+m[2]<=12?+m[2]:0,src}:null; }
async function pdfDate(doc){
  try{ const at=await doc.getAttachments(); if(at) for(const k in at){ const a=at[k]; if(/comicinfo\.xml$/i.test(a.filename||k)){ const d=comicInfoDate(new TextDecoder().decode(a.content)); if(d) return d; } } }catch(e){}
  try{ const md=await doc.getMetadata(); const x=md&&md.metadata;
    if(x) for(const k of ['prism:coverdate','prism:coverDate','prism:publicationdate','prism:publicationDate']){ const v=x.get(k); const d=v&&isoDate(v,'meta'); if(d) return d; }
    const raw=md&&md.metadata&&md.metadata.getRaw&&md.metadata.getRaw(); if(raw){ const m=raw.match(/prism:(?:coverDate|publicationDate)[^>]*>\s*([^<]+)/i)||raw.match(/prism:(?:coverDate|publicationDate)="([^"]+)"/i); const d=m&&isoDate(m[1],'meta'); if(d) return d; }
    const ci=md&&md.info&&md.info.Custom; if(ci){ const y=+ci.Year||0, mo=+ci.Month||0; if(okY(y)) return {y,m:mo>=1&&mo<=12?mo:0,src:'meta'}; } }catch(e){}
  return null; }
// well-known series: cover date of #1, issues per year (estimate; shown with "≈"). Names matched case-insensitively, "The" ignored.
const SERIES_DATES=[['amazing spider-man',1963,3,12],['fantastic four',1961,11,12],['x-men',1963,9,12],['uncanny x-men',1963,9,12],['avengers',1963,9,12],
  ['daredevil',1964,4,12],['incredible hulk',1962,5,12],['watchmen',1986,9,12],['sandman',1989,1,12],['preacher',1995,4,12],['transmetropolitan',1997,9,12],
  ['y the last man',2002,9,12],['walking dead',2003,10,12],['saga',2012,3,12],['invincible',2003,1,12],['hellblazer',1988,1,12]];
const normSeries=s=>String(s||'').toLowerCase().replace(/\(.*?\)/g,' ').replace(/[:,.!']/g,' ').replace(/^\s*the\s+/,'').replace(/\s+/g,' ').trim();
/* hints that say WHICH run/volume an issue belongs to: "Vol 2", "v2", a start year "(1996)", or a known relaunch imprint.
   The built-in table only knows each title's FIRST volume, so any of these (other than Vol 1 / a year matching vol 1) means: don't estimate. */
const RELAUNCH=[[/heroes\s+reborn/i,1996],[/heroes\s+return/i,1998],[/marvel\s+now/i,2012],[/all[-\s]new/i,2014],[/\bnew\s*52\b/i,2011],[/\brebirth\b/i,2016],[/\blegacy\b/i,2017],[/\bultimate\b/i,2000],[/\bfresh\s+start\b/i,2018]];
function volHints(...texts){ const t=texts.filter(Boolean).join(' | ').replace(/_/g,' '); let vol=0, year=0, tag='';
  let m=t.match(/\bvol(?:ume)?\.?\s*(\d{1,2})\b/i)||t.match(/(?:^|[\s(])v(\d{1,2})(?=[\s)#]|$)/i); if(m) vol=+m[1];
  m=t.match(/[([]\s*((?:19|20)\d\d)(?:\s*[-–]\s*(?:\d{2,4}))?\s*[)\]]/); if(m&&okY(+m[1])) year=+m[1];
  for(const [re,y] of RELAUNCH) if(re.test(t)){ tag=t.match(re)[0]; if(!year) year=y; break; }
  return {vol,year,tag}; }
function lookupDate(series,issue,...hints){ const n=normSeries(String(series||'').replace(/\bvol(?:ume)?\.?\s*\d+\b/ig,' ')); if(!n||!(issue>=1)) return null; const r=SERIES_DATES.find(x=>x[0]===n); if(!r) return null;
  const h=volHints(series,...hints); if(h.vol>1||h.tag) return null;            // another volume / a relaunch: unknown, let online lookup decide
  const idx=(r[2]-1)+Math.round((Math.floor(issue)-1)*12/r[3]), y=r[1]+Math.floor(idx/12);
  if(h.year&&Math.abs(h.year-r[1])>1&&!(h.vol===1)) return null;                 // "(1996)" names a different run than the 1961 one
  return {y,m:idx%12+1,src:'lookup'}; }

/* ================= online release-date lookup (manual, from Settings or the Release Date sheet) =================
   Source: the Fandom comics wikis (Marvel Database, DC Database, Image Comics Database, Dark Horse Database) via the public
   MediaWiki API. Keyless and CORS-enabled (origin=* -> Access-Control-Allow-Origin: *), so it works straight from the app.
   Pages are named "<Series> Vol <n> <issue>"; the infobox has Month / Year (cover date). */
const WIKIS=[['marvel','Marvel Database'],['dc','DC Database'],['imagecomics','Image Comics Database'],['darkhorse','Dark Horse Database']];
const MONTHN={jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12,win:1,spr:4,sum:7,fal:10,aut:10,hol:12};
async function wikiApi(w,params,signal){ const u=`https://${w}.fandom.com/api.php?`+new URLSearchParams({format:'json',formatversion:'2',origin:'*',...params});
  const ctl=new AbortController(), t=setTimeout(()=>ctl.abort(),12000); if(signal) signal.addEventListener('abort',()=>ctl.abort());
  try{ const r=await fetch(u,{signal:ctl.signal,credentials:'omit'}); if(!r.ok) throw new Error('HTTP '+r.status); return await r.json(); } finally{ clearTimeout(t); } }
function wikiDate(txt){ const g=k=>{ const m=String(txt).match(new RegExp('\\|\\s*'+k+'\\s*=\\s*([^\\n|]*)','i')); return m?m[1].trim():''; };
  const y=parseInt(g('Year'),10); if(!okY(y)) return null; const mo=g('Month'); let m=parseInt(mo,10); if(!(m>=1&&m<=12)) m=MONTHN[mo.slice(0,3).toLowerCase()]||0; return {y,m}; }
// -> {found:{y,m,src:'online',wiki,title,url}} | {candidates:[...]} (several volumes, no hint to choose) | {none:true}
async function onlineDate(series,issue,hintTexts=[],signal){
  const h=volHints(series,...hintTexts); let base=String(series||'').replace(/\bvol(?:ume)?\.?\s*\d+\b/ig,' ').replace(/\(.*?\)/g,' ').replace(/[_]+/g,' ').replace(/\s+/g,' ').trim();
  if(!base||!(issue>=0)) return {none:true}; const num=String(issue).replace(/\.0+$/,'');
  const names=[...new Set([base,base.replace(/^the\s+/i,''),/^the\s/i.test(base)?null:'The '+base].filter(Boolean))];
  for(const [w,label] of WIKIS){
    let vols=h.vol?[h.vol]:[];
    if(!h.vol) vols=[1,2,3,4,5,6,7,8,9,10,11,12].slice(0,names.length>2?16:16);   // ask for every volume at once; the wiki says which exist
    const titles=[]; for(const n of names) for(const v of vols) titles.push(`${n} Vol ${v} ${num}`);
    const j=await wikiApi(w,{action:'query',prop:'revisions',rvprop:'content',rvslots:'main',redirects:'1',titles:titles.slice(0,50).join('|')},signal).catch(()=>null);
    const hits=[]; for(const pg of (j&&j.query&&j.query.pages)||[]){ if(pg.missing) continue; const c=pg.revisions&&pg.revisions[0]&&pg.revisions[0].slots.main.content; const d=c&&wikiDate(c); const vm=pg.title.match(/ Vol (\d+) /);
      if(d) hits.push({...d,src:'online',wiki:label,title:pg.title,vol:vm?+vm[1]:0,url:`https://${w}.fandom.com/wiki/${encodeURIComponent(pg.title.replace(/ /g,'_'))}`}); }
    const uniq=[...new Map(hits.map(x=>[x.title,x])).values()];
    if(!uniq.length) continue;
    if(uniq.length===1&&(h.vol||!h.year||Math.abs(uniq[0].y-h.year)<=3)) return {found:uniq[0]};
    if(h.year){ const best=uniq.slice().sort((a,b)=>Math.abs(a.y-h.year)-Math.abs(b.y-h.year))[0]; if(Math.abs(best.y-h.year)<=3) return {found:best}; return {candidates:uniq}; }
    if(uniq.length===1) return {found:uniq[0]};
    return {candidates:uniq.sort((a,b)=>a.vol-b.vol)}; }
  return {none:true}; }

/* ================= page-turn style: fold in the middle for wide two-page scans ================= */
// a page is "wide" if width > height*1.15 once black letterbox bands are ignored
async function pageIsWide(page){ const vp=page.getViewport({scale:1}), a=vp.width/vp.height; if(a>1.15) return true; if(a<=0.95) return false;
  const c=await renderToCanvas(page,96,96,1,12000); const W=c.width,H=c.height, d=c.getContext('2d',{willReadFrequently:true}).getImageData(0,0,W,H).data; freeCanvas(c);
  const [,t,,b]=trimBlack(d,W,0,0,W,H,false); return vp.width>vp.height*((b-t)/H)*1.15; }
// Auto: sample pages 2-6; most wide -> fold. Result cached on the record (turnMode 'standard'/'fold' override it).
async function turnIsFold(doc,c){ const m=c.turnMode||'auto'; if(m==='fold') return true; if(m==='standard') return false;
  if(typeof c.foldAuto==='boolean') return c.foldAuto;
  const idx=[]; for(let i=1;i<=5&&i<doc.numPages;i++) idx.push(i); let wide=0;
  for(const i of idx){ const pg=await doc.getPage(i+1); try{ if(await pageIsWide(pg)) wide++; } finally{ pg.cleanup(); } }
  c.foldAuto=idx.length>0&&wide>idx.length/2; dbPut(c).catch(()=>{}); return c.foldAuto; }

// Drive subfolder names that are just an issue range / era ('150-199', "300's", '1-50', '1990s', '#1-#25', '300+') aren't series names
function isRangeName(n){ const s=String(n||'').trim().replace(/[’‘]/g,"'");
  return /^(?:(?:issues?|nos?\.?|#)\s*)?#?\d{1,4}\s*(?:-|–|—|to|thru|through)\s*#?\d{1,4}$/i.test(s) || /^\d{1,4}\s*'?\s*s$/i.test(s) || /^#?\d{1,4}\s*\+?$/.test(s); }

/* ---- blank black pages (scanned "TM & ©" pages between ads) ----
   A page is "blank black" when, on a small render (page 1 never counts):
   - at least 95% of it is near-black (luma < 32), ignoring a thin 3% border (scanner edges);
   - everything bright is one small blob (the copyright box: at most 3.5% of the page), with almost nothing bright outside it (<= 0.03%: no stars, windows, rain);
   - the black outside that blob is flat: dark mean <= 22 and spread (std) <= 4.5. Night-scene art has gradients/texture (std 5.8+ on our dark test pages). */
const BLACK_V=2;   /* bump to re-check every comic */
function blackStats(d,W,H){
  const m=Math.round(Math.min(W,H)*.03), x0=m, y0=m, x1=W-m, y1=H-m, w=x1-x0, h=y1-y0, N=w*h, L=new Float32Array(N), bright=new Uint8Array(N);
  let dark=0; for(let y=0;y<h;y++) for(let x=0;x<w;x++){ const i=((y+y0)*W+(x+x0))*4, l=.299*d[i]+.587*d[i+1]+.114*d[i+2], k=y*w+x; L[k]=l; if(l<32) dark++; else bright[k]=1; }
  const share=dark/N; let best=null;
  if(share>=0.95){ const seen=new Uint8Array(N), st=[];                        // largest bright blob (4-connected)
    for(let k=0;k<N;k++){ if(!bright[k]||seen[k]) continue; let n=0,l=w,r=-1,t=h,b=-1; st.push(k); seen[k]=1;
      while(st.length){ const q=st.pop(), x=q%w, y=(q-x)/w; n++; if(x<l) l=x; if(x>r) r=x; if(y<t) t=y; if(y>b) b=y;
        for(const nb of [x>0?q-1:-1,x<w-1?q+1:-1,y>0?q-w:-1,y<h-1?q+w:-1]) if(nb>=0&&bright[nb]&&!seen[nb]){ seen[nb]=1; st.push(nb); } }
      if(!best||n>best.n) best={n,l,r,t,b}; } }
  const pad=2, bx=best?{l:best.l-pad,r:best.r+pad,t:best.t-pad,b:best.b+pad}:null, inBox=(x,y)=>bx&&x>=bx.l&&x<=bx.r&&y>=bx.t&&y<=bx.b;
  let out=0, sum=0, sq=0, nd=0; for(let y=0;y<h;y++) for(let x=0;x<w;x++){ if(inBox(x,y)) continue; const k=y*w+x; if(bright[k]) out++; else { const l=L[k]; sum+=l; sq+=l*l; nd++; } }
  const mean=nd?sum/nd:0, std=nd?Math.sqrt(Math.max(0,sq/nd-mean*mean)):0, boxArea=bx?((bx.r-bx.l+1)*(bx.b-bx.t+1))/N:0;
  const black=share>=0.95&&boxArea<=0.035&&out<=N*0.0003&&mean<=22&&std<=4.5;
  /* nearly white page (cr-v19 rule): inner 80%x84% is >84% light (luma>198) with <7% mid-tones. Light must also be near-neutral
     (channel spread <=18) so plain coloured pages (yellow ads, pale-blue sheets) are not taken for blank paper */
  const wx0=Math.floor(W*.1), wy0=Math.floor(H*.08), wx1=Math.ceil(W*.9), wy1=Math.ceil(H*.92); let wl=0, wm=0, wn=0;
  for(let y=wy0;y<wy1;y++) for(let x=wx0;x<wx1;x++){ const i=(y*W+x)*4, l=.299*d[i]+.587*d[i+1]+.114*d[i+2]; wn++; if(l>198){ if(Math.max(d[i],d[i+1],d[i+2])-Math.min(d[i],d[i+1],d[i+2])<=18) wl++; } else if(l>=72) wm++; }
  const white=wn>0&&wm/wn<0.07&&wl/wn>0.84;
  return {share,boxArea,outside:out/N,mean,std,black,white}; }
async function pageBlackStats(page){ const vp=page.getViewport({scale:1}), wide=vp.width>vp.height;
  const c=await renderToCanvas(page,wide?192:96,wide?144:144,1,40000); const x=c.getContext('2d',{willReadFrequently:true});
  const d=x.getImageData(0,0,c.width,c.height).data, s=blackStats(d,c.width,c.height); freeCanvas(c); return s; }
// blank pages of a document (never page 0): {black:[...], white:[...]}, or null if cancelled. Yields between pages.
// Scans from page `from` to the end first (where the reader is heading), then the rest. Black: gives up if a quarter of the pages look black.
async function scanBlack(doc,{alive=()=>true,pause=()=>new Promise(r=>setTimeout(r,16)),from=1}={}){ const n=doc.numPages, black=[], white=[], f=clamp(from|0,1,Math.max(1,n-1));
  const order=[]; for(let i=f;i<n;i++) order.push(i); for(let i=1;i<f;i++) order.push(i);
  for(const i of order){ if(!alive()) return null; await pause(); const page=await doc.getPage(i+1); try{ const s=await pageBlackStats(page); if(s.black) black.push(i); else if(s.white) white.push(i); } finally{ page.cleanup(); } }
  black.sort((a,b)=>a-b); white.sort((a,b)=>a-b); return {black:black.length>Math.max(3,n*.25)?[]:black, white}; }

/* ---- guided panel view: panel boxes by recursive XY-cut on gutters ----
   A gutter row/column is (almost) all paper-white or all black across the region. Rows split first (reading order is rows
   top-to-bottom), then columns (left-to-right; reversed for right-to-left comics). Leaves smaller than 1.2% of the page are noise
   (page numbers, specks). Detection "fails" (null) with <2 or >30 panels; the reader then uses page thirds.
   Boxes are fractions of the analysed image: {x,y,w,h}. */
const PANEL_V=1;   /* bump to re-detect every comic */
function detectPanels(d,W,H,rtl=false){
  const N=W*H, cls=new Uint8Array(N);   // 1 = paper white, 2 = black, 0 = art
  for(let k=0,i=0;k<N;k++,i+=4){ const l=.299*d[i]+.587*d[i+1]+.114*d[i+2]; cls[k]=l>=200?1:l<=40?2:0; }
  // the page's gutter colour = what its outer frame mostly is (paper or black): dark art next to a black panel border is then not taken for a gutter
  let fw=0,fb=0; const fm=Math.max(1,Math.round(Math.min(W,H)*.02));
  for(let y=0;y<H;y++) for(let x=0;x<W;x++){ if(y>=fm&&y<H-fm&&x>=fm&&x<W-fm) continue; const c=cls[y*W+x]; if(c===1) fw++; else if(c===2) fb++; }
  const GC=fb>fw*1.5?2:1;
  const minGapY=Math.max(2,Math.round(H*.006)), minGapX=Math.max(2,Math.round(W*.006)), TOL=.975;
  const rowGut=(y,x0,x1)=>{ let g=0; const o=y*W; for(let x=x0;x<x1;x++) if(cls[o+x]===GC) g++; return g>=(x1-x0)*TOL; };
  const colGut=(x,y0,y1)=>{ let g=0; for(let y=y0;y<y1;y++) if(cls[y*W+x]===GC) g++; return g>=(y1-y0)*TOL; };
  // runs of content along one axis; gutter runs shorter than minGap don't split (thin panel borders, art lines)
  const runs=(a0,a1,isGut,minGap)=>{ const out=[]; let s=-1, g=0;
    for(let a=a0;a<a1;a++){ if(isGut(a)){ g++; if(s>=0&&g>=minGap){ out.push([s,a-g+1]); s=-1; } } else { if(s<0) s=a; g=0; } }
    if(s>=0) out.push([s,a1-(g>0?g:0)]); return out; };
  const leaves=[];
  const cut=(x0,y0,x1,y1,depth)=>{ if(x1-x0<4||y1-y0<4) return;
    const rs=runs(y0,y1,y=>rowGut(y,x0,x1),minGapY); if(!rs.length) return;
    if(rs.length>1&&depth<10){ rs.forEach(([a,b])=>cut(x0,a,x1,b,depth+1)); return; }
    const [ty,by]=rs[0]; const cs=runs(x0,x1,x=>colGut(x,ty,by),minGapX); if(!cs.length) return;
    if(cs.length>1&&depth<10){ (rtl?cs.slice().reverse():cs).forEach(([a,b])=>cut(a,ty,b,by,depth+1)); return; }
    leaves.push({x0:cs[0][0],y0:ty,x1:cs[0][1],y1:by}); };
  cut(0,0,W,H,0);
  const big=leaves.filter(b=>(b.x1-b.x0)*(b.y1-b.y0)>=N*.012&&(b.x1-b.x0)>=W*.06&&(b.y1-b.y0)>=H*.04);
  if(big.length<2||big.length>30) return null;
  const r4=v=>Math.round(v*1e4)/1e4;
  return big.map(b=>({x:r4(b.x0/W),y:r4(b.y0/H),w:r4((b.x1-b.x0)/W),h:r4((b.y1-b.y0)/H)})); }
// fallback when detection fails: thirds (rows on upright pages, columns on wide ones), in reading order
function panelThirds(aspect,rtl){ if(aspect>1.2){ const c=[0,1,2].map(k=>({x:k/3,y:0,w:1/3,h:1})); return rtl?c.reverse():c; } return [0,1,2].map(k=>({x:0,y:k/3,w:1,h:1/3})); }
// analyse a rendered page canvas (whole, or its left/right half)
function panelsOfCanvas(c,half,rtl){ const x=c.getContext('2d',{willReadFrequently:true}); const hw=Math.ceil(c.width/2), sx=half==='R'?c.width-hw:0, w=half?hw:c.width;
  const d=x.getImageData(sx,0,w,c.height).data; return detectPanels(d,w,c.height,rtl); }
