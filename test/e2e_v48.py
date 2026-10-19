"""cr-v48 suite: carousel grows to fill spare height; shelf-to-Continue Reading gap is normal section spacing (8-20px). Also v47: every visible Home carousel cover keeps its tilt and its bottom-left corner is level with the others, on the shelf top (within 2px); covers still whole (v46).
python3 test/e2e_v48.py [webkit] (server on 127.0.0.1:8823). Original test art. 4 sizes + iPad 1180x820. Standalone insets via --sat/--sab."""
import sys, os, json, glob
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=sorted(glob.glob(os.path.join(T,'*.pdf')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:400] if not cond else '',flush=True)
# every displayed carousel cover: its full image box must be inside every clipping ancestor and the viewport (vertically), below the header, above the shelf
CHK="""(()=>{ const hs=document.querySelector('#homeScroll'), hdr=document.querySelector('#tabs').closest('header,.topbar')||document.querySelector('#tabs'), hb=hdr.getBoundingClientRect().bottom, sh=hs.querySelector('.volshelf').getBoundingClientRect().top;
  const clipRects=el=>{ const out=[]; for(let a=el.parentElement;a;a=a.parentElement){ const cs=getComputedStyle(a); if(cs.overflow!=='visible'||cs.overflowY!=='visible') out.push(a.getBoundingClientRect()); } return out; };
  const items=[...document.querySelectorAll('#cf .cf-item')].filter(e=>e.style.display!=='none'), bad=[]; let center=null, best=1e9;
  for(const e of items){ const im=e.querySelector('img'), r=im.getBoundingClientRect(); if(r.width<2) continue; const cl=clipRects(im);
    const vClip=cl.some(c=>r.top<c.top-0.5||r.bottom>c.bottom+0.5)||r.top<0||r.bottom>innerHeight;
    if(vClip||r.top<hb-0.5||r.bottom>sh+0.5) bad.push({t:r.top,b:r.bottom,hb,sh});
    const d=Math.abs(r.left+r.width/2-innerWidth/2); if(d<best){ best=d; center={t:r.top,b:r.bottom,l:r.left,r:r.right,w:r.width,h:r.height,clipH:cl.some(c=>r.left<c.left-0.5||r.right>c.right+0.5)}; } }
  const im=document.querySelector('#cf .cf-item img'), cs=getComputedStyle(im), cr=hs.querySelector('#contRow .rc .cvr');
  return {n:items.length,bad,center,shelfTop:sh,hdr:hb,fit:cs.objectFit,flush:center?sh-center.b:null,crH:cr?cr.getBoundingClientRect().height:0,vh:innerHeight}; })()"""
CORN="""(()=>{ const cf=document.querySelector('#cf'), sh=document.querySelector('#homeScroll .volshelf').getBoundingClientRect().top, cfr=cf.getBoundingClientRect(), ccs=getComputedStyle(cf), P=parseFloat(ccs.perspective), po=ccs.perspectiveOrigin.split(' ').map(parseFloat), out=[];
  for(const e of [...cf.querySelectorAll('.cf-item')].filter(e=>e.style.display!=='none')){ const cs=getComputedStyle(e), w=e.offsetWidth, h=e.offsetHeight, ox=e.offsetLeft, oy=e.offsetTop, to=cs.transformOrigin.split(' ').map(parseFloat);
    const M=new DOMMatrix().translate(ox+to[0],oy+to[1]).multiply(new DOMMatrix(cs.transform==='none'?undefined:cs.transform)).translate(-to[0],-to[1]);
    const proj=(lx,ly)=>{ const q=M.transformPoint(new DOMPoint(lx,ly,0,1)), f=P/(P-q.z); return {x:cfr.left+po[0]+(q.x-po[0])*f, y:cfr.top+po[1]+(q.y-po[1])*f}; };
    const BL=proj(0,h), BR=proj(w,h); if(Math.max(BL.x,BR.x)<0||Math.min(BL.x,BR.x)>innerWidth) continue;
    const im=e.querySelector('img'), nw=im.naturalWidth||2, nh=im.naturalHeight||3, ah=nh*Math.min(w/nw,h/nh), op=parseFloat(getComputedStyle(im).objectPosition.split(' ')[1]||'50');
    out.push({i:e.dataset.i,bl:+BL.y.toFixed(2),br:+BR.y.toFixed(2),artGap:+((h-ah)*(1-op/100)).toFixed(2),rot:cs.transform.startsWith('matrix3d')}); }
  return {sh,out}; })()"""
def corners(pg,lab,when):
    r=pg.evaluate(CORN); c=r['out']; sh=r['sh']; ys=[x['bl'] for x in c]
    ok(f'{lab}: {when}: all visible covers\' bottom-left corners within 2px of each other and of the shelf top (tilt kept)',len(c)>=3 and max(ys)-min(ys)<=2 and all(-1<=sh-y<=2 for y in ys) and all(x['artGap']<=1 for x in c) and any(x['rot'] for x in c),json.dumps(r))
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1180,820,'ipad-1180',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34),(834,1194,'ipad-834',2,24,20),(768,1024,'ipad-768',2,24,20)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        ok(f'{lab}: app launches on Home',pg.evaluate("!document.querySelector('#home').classList.contains('hidden')"))
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        pg.evaluate("(()=>{ const f=t=>__cr.comics.find(c=>c.title===t); Object.assign(f('Nightfall 02'),{page:5,progress:.2,lastRead:Date.now()}); Object.assign(f('Iron Tide 02'),{page:3,progress:.1,lastRead:Date.now()-9e3}); __cr.dates.render(); })()")
        pg.click('#tabs [data-tab=home]'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(700)
        s=pg.evaluate(CHK)
        ok(f'{lab}: every carousel cover is whole: not clipped top or bottom, clear of the header, above the shelf',s['n']>=3 and not s['bad'],json.dumps(s))
        ok(f'{lab}: centre cover fully visible (also left/right) and not cropped (object-fit: contain)',s['center'] and not s['center']['clipH'] and s['center']['l']>=0 and s['center']['r']<=w and s['fit']=='contain',json.dumps(s))
        ok(f'{lab}: carousel sits flush on the spine shelf (0-8px)',0<=s['flush']<=8,json.dumps(s))
        ok(f'{lab}: Home fits the screen (no scrolling needed to see carousel, shelf and Continue Reading)',pg.evaluate("(()=>{ const hs=document.querySelector('#homeScroll'); return hs.scrollHeight<=hs.clientHeight+1 })()"))
        if w>h: ok(f'{lab}: Continue Reading thumbnails compact in landscape (<=20% of the height)',0<s['crH']<=h*.2,json.dumps(s))
        corners(pg,lab,'at rest')
        g=pg.evaluate("(()=>{const hs=document.querySelector('#homeScroll'); return Math.round(hs.querySelector('#contRow').getBoundingClientRect().top-hs.querySelector('.volshelf').getBoundingClientRect().bottom)})()")
        ok(f'{lab}: no empty band: shelf to Continue Reading gap is normal spacing (8-20px)',8<=g<=20,str(g))
        mv=pg.evaluate("""(async()=>{ __cr.CF.to(Math.round(__cr.CF.pos)+3,1); await new Promise(r=>setTimeout(r,300)); return 1 })()"""); s2=pg.evaluate(CHK)
        ok(f'{lab}: still whole after moving the carousel',not s2['bad'] and 0<=s2['flush']<=8,json.dumps(s2))
        corners(pg,lab,'after moving')
        if lab in ('ipad-landscape','ipad-portrait','iphone-390','ipad-1180','ipad-834','ipad-768'): pg.screenshot(path=f'{SH}/{ENG}-v48-home-{lab}.png')
        pg.evaluate("localStorage.setItem('cr.homeRows','true')"); pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(900); s3=pg.evaluate(CHK)
        ok(f'{lab}: with category rows on, covers are still whole above the shelf',not s3['bad'] and 0<=s3['flush']<=8,json.dumps(s3))
        corners(pg,lab,'category rows on')
        ctx.close()
    b.close()
print(f'\n{sum(res)}/{len(res)} passed'+(f'; page errors: {errors[:3]}' if errors else '')); sys.exit(0 if all(res) and not errors else 1)
