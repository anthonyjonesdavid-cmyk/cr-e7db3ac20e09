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
  return {cover:cv.cover,coverCrop:cv.crop,coverMode:mode,coverV:COVER_V,aspect}; }

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
const BLACK_V=1;
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
  return {share,boxArea,outside:out/N,mean,std,black}; }
async function pageBlackStats(page){ const vp=page.getViewport({scale:1}), wide=vp.width>vp.height;
  const c=await renderToCanvas(page,wide?192:96,wide?144:144,1,40000); const x=c.getContext('2d',{willReadFrequently:true});
  const d=x.getImageData(0,0,c.width,c.height).data, s=blackStats(d,c.width,c.height); freeCanvas(c); return s; }
// all blank-black page indices of a document (never page 0). Yields between pages; gives up (returns []) if a quarter of the pages look black.
async function scanBlack(doc,{alive=()=>true,pause=()=>new Promise(r=>setTimeout(r,16))}={}){ const n=doc.numPages, hits=[];
  for(let i=1;i<n;i++){ if(!alive()) return null; await pause(); const page=await doc.getPage(i+1); try{ if((await pageBlackStats(page)).black) hits.push(i); } finally{ page.cleanup(); } }
  return hits.length>Math.max(3,n*.25)?[]:hits; }
