"""cr-v54 suite: Creators list (Library button), roles incl. Cover, series creators, metadata fill, edge-swipe back."""
import sys, os, glob, json
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=sorted(glob.glob(os.path.join(T,'*.pdf'))); res=[]; errors=[]
def ok(n,c,x=''): res.append(bool(c)); print(('PASS' if c else 'FAIL'),f'[{ENG}]',n,'' if c else str(x)[:300],flush=True)
SEED="""()=>{ const C=__cr.comics.slice().sort((a,b)=>a.title.localeCompare(b.title)); C.forEach(c=>{delete c.driveId; c.metaCredits=null;});
 C.forEach((c,i)=>{ if(i%3===0) c.metaCredits={writer:['Chris Claremont'],artist:['Jim Lee'],cover:i%2?['Jim Lee']:[]}; else if(i%3===1) c.metaCredits={writer:['Ann Nocenti'],artist:['James Lee'],cover:['Arthur Adams']}; });
 return C.filter(c=>c.metaCredits).length; }"""
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        n=pg.evaluate(SEED)
        pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(200)
        bb=pg.locator('#crlBtn').bounding_box(); ok(f'{lab}: Creators button visible in Library, >=40px',bb and bb['width']>=40 and bb['height']>=40 and bb['x']+bb['width']<=w,bb)
        if lab in('ipad-landscape','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v54-library-{lab}.png')
        pg.locator('#crlBtn').tap(); pg.wait_for_timeout(200)
        rows=pg.evaluate("[...document.querySelectorAll('.crlr')].map(r=>({t:r.innerText,h:r.getBoundingClientRect().height,bg:getComputedStyle(r).backgroundColor}))")
        ok(f'{lab}: list merges variants (Jim Lee/James Lee) -> 4 creators',len(rows)==4,rows)
        ok(f'{lab}: rows uniform, >=44px',len({r['bg'] for r in rows})==1 and all(r['h']>=44 for r in rows),rows)
        hd=pg.evaluate("(()=>{const r=document.querySelector('#creators .rkbar').getBoundingClientRect(), h2=document.querySelector('#creators h2').getBoundingClientRect(); return {bg:getComputedStyle(document.querySelector('#creators .rkbar')).backgroundColor,h2top:h2.top,hh:r.height}})()")
        ok(f'{lab}: opaque bar, title below status bar, compact',hd['bg']=='rgb(0, 0, 0)' and hd['h2top']>=sat and hd['hh']-sat<=110,hd)
        if lab in('ipad-portrait','iphone-390','ipad-landscape','iphone-430'): pg.screenshot(path=f'{SH}/{ENG}-v54-creators-{lab}.png')
        pg.fill('#crlQ','lee'); pg.wait_for_timeout(100); ok(f'{lab}: search filters',pg.evaluate("document.querySelectorAll('.crlr').length")==1)
        pg.fill('#crlQ',''); pg.locator('#crlSort [data-s=count]').tap(); first=pg.evaluate("document.querySelector('.crln').firstChild.textContent")
        ok(f'{lab}: most-issues sort puts Jim Lee first',first=='Jim Lee',first)
        pg.locator('.crlr').first.tap(); pg.wait_for_timeout(250)
        info=pg.evaluate("({on:__cr.credits.CRP.on,name:document.querySelector('#crName').textContent,sub:document.querySelector('#crSub').textContent,roles:[...document.querySelectorAll('.crc .tr')].map(e=>e.textContent)})")
        ok(f'{lab}: creator page opens with roles incl. Cover',info['on'] and info['name']=='Jim Lee' and 'Cover' in info['sub'] and any('Cover' in r for r in info['roles']),info)
        if lab in('ipad-landscape','iphone-390','ipad-portrait','iphone-430'): pg.screenshot(path=f'{SH}/{ENG}-v54-creator-page-{lab}.png')
        # edge swipe back
        cdp=None
        pg.evaluate("""()=>{ const el=document.querySelector('#creator'); const mk=(t,x)=>{ const tt={identifier:1,target:el,clientX:x,clientY:400}; const ev=new Event(t,{bubbles:true}); Object.defineProperty(ev,'touches',{value:t==='touchend'?[]:[tt]}); el.dispatchEvent(ev); };
          mk('touchstart',8); mk('touchmove',60); mk('touchmove',200); mk('touchend',200); }"""); pg.wait_for_timeout(400)
        ok(f'{lab}: left-edge swipe closes creator page back to Creators list',pg.evaluate("!__cr.credits.CRP.on && !document.querySelector('#creators').classList.contains('hidden')"))
        pg.locator('#crlClose').tap(); pg.wait_for_timeout(150); ok(f'{lab}: back closes list',pg.evaluate("document.querySelector('#creators').classList.contains('hidden')"))
        # info sheet shows Cover row
        cid=pg.evaluate("__cr.comics.find(c=>c.metaCredits&&c.metaCredits.cover.length).id"); pg.evaluate("id=>{ __cr.credits.sheet(id); return 1 }",cid); pg.wait_for_timeout(250)
        ok(f'{lab}: info sheet shows Writer/Artist/Cover names',pg.evaluate("[...document.querySelectorAll('.mwrap .crl')].map(e=>e.textContent).join()")=='Writer,Artist,Cover')
        if lab=='iphone-390': pg.screenshot(path=f'{SH}/{ENG}-v54-info-{lab}.png')
        pg.evaluate("(document.querySelector(\".mwrap [data-r=cancel]\")||{click(){}}).click()"); pg.wait_for_timeout(150)
        # built-in precedence: driveId credits win over metadata for writer
        r=pg.evaluate("""()=>{ const c=__cr.comics[0], id=Object.keys(__cr.credits.data.d)[0]; c.driveId=id; c.metaCredits={writer:['Nobody Here'],artist:[],cover:['X Y']}; const k=__cr.credits.of(c); delete c.driveId; return k; }""")
        ok(f'{lab}: built-in names never replaced by metadata; metadata only fills gaps',r and 'Nobody Here' not in r['writer'] and r['cover']==['X Y'],r)
        ctx.close()
    b.close()
ok('no page errors',not errors,errors); print(f'{sum(res)}/{len(res)} passed'); sys.exit(0 if all(res) else 1)
