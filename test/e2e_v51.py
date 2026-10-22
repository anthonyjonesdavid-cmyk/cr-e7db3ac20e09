"""cr-v51 suite: the Home carousel uses the same CoverFlow component and style as the series-page carousels (reflection, tilt, overlap, perspective);
Home still fits without scrolling with the spine shelf and Continue Reading (no heading/count/page labels).
python3 test/e2e_v51.py [webkit] (server on 127.0.0.1:8823). Original test art. 4 sizes, standalone insets via --sat/--sab."""
import sys, os, json, glob
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); SH=os.path.join(HERE,'..','shots'); FILES=sorted(glob.glob(os.path.join(HERE,'..','testpdfs','*.pdf')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:500] if not cond else '',flush=True)
STY="""(sel=>{ const el=document.querySelector(sel); if(!el) return null; const cs=getComputedStyle(el), r=el.getBoundingClientRect(), it=[...el.querySelectorAll('.cf-item')].filter(e=>e.style.display!=='none');
  const c0=it.reduce((a,e)=>(+e.style.zIndex>+a.style.zIndex?e:a),it[0]), cw=c0.offsetWidth, ic=getComputedStyle(c0), im=getComputedStyle(c0.querySelector('img'));
  const ang=e=>{ const m=new DOMMatrix(getComputedStyle(e).transform); return Math.round(Math.atan2(-m.m13,m.m11)*180/Math.PI); };
  const pos=Math.round(__cr[sel==='#cf'?'CF':'SCF']?.pos ?? 0);
  const po=cs.perspectiveOrigin.split(' ').map(parseFloat), to=ic.transformOrigin.split(' ').map(parseFloat);
  const angles=it.map(e=>ang(e)).filter(a=>a!==0).map(Math.abs);
  return {persp:cs.perspective, poX:+(po[0]/r.width).toFixed(2), poY:+(po[1]/r.height).toFixed(2), hRatio:+((r.height-4)/cw).toFixed(2), toX:+(to[0]/cw).toFixed(2), toY:+(to[1]/c0.offsetHeight).toFixed(2),
    fit:im.objectFit, reflect:im.webkitBoxReflect||im.getPropertyValue('-webkit-box-reflect'), shadow:im.boxShadow!=='none', side:angles.length?Math.max(...angles):0, n:it.length}; })"""
KEYS=['persp','poX','poY','hRatio','toX','toY','fit','reflect','shadow','side']
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        ok(f'{lab}: app launches on Home',pg.evaluate("!document.querySelector('#home').classList.contains('hidden')"))
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        x=pg.evaluate("(()=>{ const f=t=>__cr.comics.find(c=>c.title===t); Object.assign(f('Nightfall 02'),{page:5,progress:.2,lastRead:Date.now()}); Object.assign(f('Iron Tide 02'),{page:3,progress:.1,lastRead:Date.now()-9e3}); __cr.dates.render(); return f('Iron Tide 02').id })()")
        pg.click('#tabs [data-tab=home]'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(700)
        H=pg.evaluate(STY,'#cf')
        lay=pg.evaluate("""(()=>{ const hs=document.querySelector('#homeScroll'), hb=document.querySelector('#tabs').getBoundingClientRect().bottom, sh=hs.querySelector('.volshelf').getBoundingClientRect(), cr=hs.querySelector('#contRow');
          const ims=[...document.querySelectorAll('#cf .cf-item')].filter(e=>e.style.display!=='none').map(e=>e.querySelector('img').getBoundingClientRect()).filter(r=>r.right>0&&r.left<innerWidth);
          return {over:hs.scrollHeight-hs.clientHeight, whole:ims.every(r=>r.top>=hb-1&&r.bottom<=sh.top+1), gap:Math.round(cr.getBoundingClientRect().top-sh.bottom),
            head:!!cr.querySelector('h2,.row-h,.n'), sub:cr.querySelectorAll('.rc .s').length, titles:cr.querySelectorAll('.rc .t').length, n:__cr.CF.items.length, all:__cr.comics.length} })()""")
        ok(f'{lab}: Home: whole covers between the header and the shelf, fits without scrolling, normal gap to Continue Reading',lay['whole'] and lay['over']<=1 and 8<=lay['gap']<=20,json.dumps(lay))
        ok(f'{lab}: Continue Reading: no heading, count or page labels; titles kept',not lay['head'] and lay['sub']==0 and lay['titles']>=2,json.dumps(lay))
        ok(f'{lab}: Home carousel keeps its content (every issue up to 50)',lay['n']==min(50,lay['all']),json.dumps(lay))
        wrap=pg.evaluate("(async()=>{ const n=__cr.CF.items.length; __cr.CF.pos=0; __cr.CF.layout(); __cr.CF.to(-1,1); await new Promise(r=>setTimeout(r,200)); return __cr.CF.items[((Math.round(__cr.CF.pos)%n)+n)%n].id===__cr.CF.items[n-1].id })()")
        ok(f'{lab}: Home carousel still loops',wrap)
        pg.evaluate("__cr.CF.to(3,1)"); pg.wait_for_timeout(900)
        H=pg.evaluate(STY,'#cf')
        if lab=='ipad-portrait': pg.screenshot(path=f'{SH}/{ENG}-v51-home-ipad-portrait.png')
        else: pg.screenshot(path=f'{SH}/{ENG}-v51-home-{lab}.png')
        sel='#homeScroll .spine[data-series="Nightfall"]'
        pg.evaluate(f"document.querySelector('{sel}').scrollIntoView({{inline:'center',block:'nearest'}})"); pg.wait_for_timeout(200)
        bb=pg.locator(sel).bounding_box(); pg.touchscreen.tap(bb['x']+bb['width']/2,bb['y']+bb['height']/2); pg.wait_for_selector('#library:not(.hidden) #scf'); pg.wait_for_timeout(700)
        pg.evaluate("__cr.SCF && __cr.SCF.to(2,1)"); pg.wait_for_timeout(900)
        S=pg.evaluate(STY,'#scf')
        pg.screenshot(path=f'{SH}/{ENG}-v51-series-{lab}.png')
        diff={k:[H[k],S[k]] for k in KEYS if H[k]!=S[k]}
        ok(f'{lab}: Home and series carousels share the same CoverFlow style (perspective, origins, reflection, shadow, fit, side tilt, box ratio)',S and not diff and H['side']>=40 and H['reflect'] not in ('','none'),json.dumps({'diff':diff,'H':H,'S':S}))
        ctx.close()
    b.close()
print(f'\n{sum(res)}/{len(res)} passed'+(f'; page errors: {errors[:3]}' if errors else '')); sys.exit(0 if all(res) and not errors else 1)
