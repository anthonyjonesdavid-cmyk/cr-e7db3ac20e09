"""cr-v54 suite B: About this issue page (sourced notes, month events, Look up button, reader Issue Info entry)."""
import sys, os, glob
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots')
FILES=sorted(glob.glob(os.path.join(T,'*.pdf'))); res=[]; errors=[]
def ok(n,c,x=''): res.append(bool(c)); print(('PASS' if c else 'FAIL'),f'[{ENG}]',n,'' if c else str(x)[:300],flush=True)
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        ctx.route('**/*fandom.com/**',lambda r:r.abort()); ctx.route('**/*wikipedia.org/**',lambda r:r.abort())
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        pg.set_input_files('#fileIn',FILES[:3]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==3 && !document.querySelector(".toast .tb")',timeout=120000)
        ids=pg.evaluate("""()=>{ const C=__cr.comics; C[0].fileName='Daredevil 181.pdf'; C[0].series='Daredevil'; C[0].dateManual={y:1982,m:4}; C[1].fileName='zz-none.pdf'; C[1].dateManual={y:1982,m:4}; return C.map(c=>c.id); }""")
        pg.click('#tabs [data-tab=library]'); pg.evaluate("id=>{ __cr.credits.sheet(id); return 1 }",ids[0]); pg.wait_for_timeout(250)
        bb=pg.locator('#aAbout').bounding_box(); ok(f'{lab}: info sheet has About this issue (>=40px)',bb and bb['height']>=40)
        pg.locator('#aAbout').tap(); pg.wait_for_timeout(300)
        t=pg.evaluate("({on:__cr.credits.about.AB.on,txt:document.querySelector('#abBody').innerText,src:[...document.querySelectorAll('#abBody .ntg li')].every(li=>li.querySelector('a.ntsrc[href^=\"https://\"]')),h:[...document.querySelectorAll('#abBody .ntg h3')].map(e=>e.textContent)})")
        ok(f'{lab}: About page: first appearances, Elektra death, April 1982 events, every item has a source link','First appearance' in t['txt'] and 'Elektra' in t['txt'] and 'April 1982' in t['h'] and t['src'],t)
        hd=pg.evaluate("(()=>{const r=document.querySelector('#about .rkbar');return {bg:getComputedStyle(r).backgroundColor,top:document.querySelector('#abName').getBoundingClientRect().top}})()")
        ok(f'{lab}: opaque bar, title clear of status bar',hd['bg']=='rgb(0, 0, 0)' and hd['top']>=sat,hd)
        pg.screenshot(path=f'{SH}/{ENG}-v54-about-{lab}.png')
        pg.locator('#about .crn').first.tap(); pg.wait_for_timeout(250); ok(f'{lab}: creator name on About opens creator page',pg.evaluate("__cr.credits.CRP.on"))
        pg.locator('#crClose').tap(); pg.wait_for_timeout(500); ok(f'{lab}: back returns to About',pg.evaluate("!__cr.credits.CRP.on&&__cr.credits.about.AB.on"))
        pg.locator('#abClose').tap(); pg.wait_for_timeout(150)
        pg.evaluate("id=>{ __cr.credits.about.open(id); return 1 }",ids[1]); pg.wait_for_timeout(200)
        t=pg.evaluate("document.querySelector('#abBody').innerText"); ok(f'{lab}: unknown issue: no guessed facts, month events still shown, Look up button',"No notes for this issue yet" in t and 'Look up' in t and 'April 1982' in t,t)
        bb=pg.locator('#abLook').bounding_box(); ok(f'{lab}: Look up >=40px',bb['height']>=40,bb)
        pg.locator('#abLook').tap(); pg.wait_for_function("!__cr.credits.about.AB.busy",timeout=20000); pg.wait_for_timeout(200)
        ok(f'{lab}: Look up offline fails gracefully (nothing invented)',"No notes for this issue yet" in pg.evaluate("document.querySelector('#abBody').innerText"))
        ctx.close()
    b.close()
ok('no page errors',not errors,errors); print(f'{sum(res)}/{len(res)} passed'); sys.exit(0 if all(res) else 1)
