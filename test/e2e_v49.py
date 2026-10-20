"""cr-v49 suite: pin issues to the front of Continue Reading (long-press / info sheet), pin order, badge, stays when finished, persisted in prefs (cr.contPin).
python3 test/e2e_v49.py [webkit] (server on 127.0.0.1:8823). Original test art. 4 sizes + iPad 768x1024. Standalone insets via --sat/--sab."""
import sys, os, json, glob
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); SH=os.path.join(HERE,'..','shots'); FILES=sorted(glob.glob(os.path.join(HERE,'..','testpdfs','*.pdf')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:400] if not cond else '',flush=True)
IDS="[...document.querySelectorAll('#contRow .rc')].map(e=>e.dataset.id)"
def pin(pg,cid):
    pg.click('#tabs [data-tab=home]'); b=pg.locator(f'#contRow .rc[data-id="{cid}"]'); b.scroll_into_view_if_needed(); b.click(button='right'); pg.wait_for_selector('#aPin'); t=pg.inner_text('#aPin'); pg.click('#aPin'); pg.wait_for_timeout(300); return t
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34),(768,1024,'ipad-768',2,24,20)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        x=pg.evaluate("""(()=>{ const f=t=>__cr.comics.find(c=>c.title===t), now=Date.now(); const L=['Nightfall 02','Iron Tide 02','Nightfall 04'].map(f).filter(Boolean); L.forEach((c,i)=>Object.assign(c,{page:3,progress:.1,lastRead:now-i*1e4})); __cr.dates.render(); return L.map(c=>c.id) })()""")
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(500)
        ok(f'{lab}: Continue Reading most-recent-first before pinning',pg.evaluate(IDS)[:3]==x,json.dumps([pg.evaluate(IDS),x]))
        t1=pin(pg,x[2]); t2=pin(pg,x[1])
        ids=pg.evaluate(IDS)
        ok(f'{lab}: long-press offers Pin; pinned issues lead in pin order, rest most-recent-first',t1.strip().startswith('Pin') and ids[:3]==[x[2],x[1],x[0]],json.dumps([t1,ids]))
        bd=pg.evaluate("[...document.querySelectorAll('#contRow .rc')].map(e=>!!e.querySelector('.pinb'))")
        ok(f'{lab}: pin badge only on pinned covers',bd[:3]==[True,True,False],json.dumps(bd))
        ok(f'{lab}: pins stored with the other prefs (cr.contPin)',pg.evaluate("JSON.parse(localStorage.getItem('cr.contPin'))")==[x[2],x[1]])
        tg=pg.evaluate("(()=>{ const r=document.querySelector('#contRow .rc').getBoundingClientRect(); return [r.width,r.height] })()")
        ok(f'{lab}: Continue Reading covers are >=40px tap targets',min(tg)>=40,json.dumps(tg))
        pg.evaluate(f"(async()=>{{ const c=__cr.comics.find(c=>c.id==='{x[2]}'); c.progress=1; c.page=c.pages-1; __cr.dates.render(); }})()"); pg.wait_for_timeout(300)
        pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(800)
        ok(f'{lab}: pins survive reload and a finished pinned issue stays first',pg.evaluate(IDS)[:2]==[x[2],x[1]],json.dumps(pg.evaluate(IDS)))
        if lab=='ipad-768':
            pg.screenshot(path=f'{SH}/{ENG}-v49-home-ipad-768-pinned.png')
            b2=pg.locator(f'#contRow .rc[data-id="{x[1]}"]'); b2.scroll_into_view_if_needed(); b2.click(button='right'); pg.wait_for_selector('#aPin'); pg.wait_for_timeout(400)
            pg.screenshot(path=f'{SH}/{ENG}-v49-home-ipad-768-pin-menu.png'); pg.keyboard.press('Escape'); pg.click('.mwrap [data-r=cancel]') if pg.locator('.mwrap [data-r=cancel]').count() else None; pg.wait_for_timeout(300)
        t3=pin(pg,x[2]); ids=pg.evaluate(IDS)
        ok(f'{lab}: Unpin from the menu removes it from the front',t3.strip().startswith('Unpin') and ids[0]==x[1] and not pg.evaluate("JSON.parse(localStorage.getItem('cr.contPin'))").count(x[2]),json.dumps([t3,ids]))
        pg.click('#tabs [data-tab=library]'); lc=pg.locator(f'#libGrid .lc[data-id="{x[0]}"]'); lc.scroll_into_view_if_needed(); lc.click(button='right'); pg.wait_for_selector('#aPin'); pg.click('#aPin'); pg.wait_for_timeout(300); pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
        ok(f'{lab}: Pin from the issue info sheet (Library) also works',pg.evaluate(IDS)[:2]==[x[1],x[0]],json.dumps(pg.evaluate(IDS)))
        hs=pg.evaluate("(()=>{const hs=document.querySelector('#homeScroll'); return [hs.scrollHeight-hs.clientHeight, Math.round(hs.querySelector('#contRow').getBoundingClientRect().top-hs.querySelector('.volshelf').getBoundingClientRect().bottom)]})()")
        ok(f'{lab}: Home layout rules hold (fits, normal gap)',hs[0]<=1 and 8<=hs[1]<=20,json.dumps(hs))
        ctx.close()
    b.close()
print(f'\n{sum(res)}/{len(res)} passed'+(f'; page errors: {errors[:3]}' if errors else '')); sys.exit(0 if all(res) and not errors else 1)
