"""cr-v43 suite: Continue Reading row on Home (under the spine shelf). python3 test/e2e_v43.py [webkit] (server on 127.0.0.1:8823).
Fixtures: original abstract comics (test/gen_pdfs.py). Standalone insets via --sat/--sab."""
import sys, os, json, glob
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=sorted(glob.glob(os.path.join(T,'*.pdf')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
ROW="""(()=>{ const r=document.querySelector('#contRow'); if(!r) return null; const prev=r.previousElementSibling, next=r.nextElementSibling;
  return {ids:[...r.querySelectorAll('.rc')].map(b=>b.dataset.id),sub:[...r.querySelectorAll('.rc .s')].map(s=>s.textContent),al:[...r.querySelectorAll('.rc')].map(b=>b.getAttribute('aria-label')),bars:[...r.querySelectorAll('.rc .pl')].map(p=>!p.classList.contains('none')),
    prev:prev&&prev.className,next:next&&next.className,h:r.getAttribute('aria-label')||(r.querySelector('h2')||{}).textContent,sz:[...r.querySelectorAll('.rc')].map(b=>{const q=b.getBoundingClientRect(); return [q.width,q.height]})}; })()"""
SETUP="""async()=>{ const C=__cr.comics, f=t=>C.find(c=>c.title===t), now=Date.now();
  const A=f('Nightfall 02'), B=f('Ember Road 01'), I1=f('Iron Tide 01'), I2=f('Iron Tide 02'), H=f('The Hollow 01');
  Object.assign(A,{page:11,progress:11/(A.pages-1),lastRead:now-1000}); Object.assign(B,{page:2,progress:2/(B.pages-1),lastRead:now-5000});
  Object.assign(I1,{page:I1.pages-1,progress:1,lastRead:now-500});   // finished -> Iron Tide 02 (unread) is next
  Object.assign(H,{page:H.pages-1,progress:1,lastRead:now-9000});    // finished, and so is the rest of its series? no: The Hollow 02 unread -> next
  __cr.dates.render(); await new Promise(r=>setTimeout(r,200)); return {A:A.id,B:B.id,I2:I2.id,H2:f('The Hollow 02').id,pa:A.pages,pb:B.pages,pi:I2.pages,ph:f('The Hollow 02').pages}; }"""
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; if(localStorage.getItem('cr.homeRows')==null) localStorage.setItem('cr.homeRows','true'); window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        ok(f'{lab}: app launches on Home',pg.evaluate("!document.querySelector('#home').classList.contains('hidden')"))
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
        ok(f'{lab}: nothing started -> no Continue Reading row',pg.evaluate(ROW) is None)
        x=pg.evaluate(SETUP); r=pg.evaluate(ROW)
        ok(f'{lab}: row right below the spine shelf, above the series rows',r and (r['prev'] or '')=='volshelf' and (r['next'] or '').startswith('row') and r['h']=='Continue Reading',json.dumps(r))
        ok(f'{lab}: in-progress most recently read first, plus the next unread issue of a series whose current issue is finished',r['ids']==[x['I2'],x['A'],x['B'],x['H2']],json.dumps([r['ids'],x]))
        ok(f"{lab}: (v50) no page subtitle under covers, page kept in the label; thin progress bar on started issues",r['sub']==[] and f"page 12 of {x['pa']}" in r['al'][1] and r['bars']==[False,True,True,False],json.dumps(r))
        ok(f'{lab}: covers are big tap targets (>=40px)',all(s[0]>=40 and s[1]>=40 for s in r['sz']),r['sz'])
        if lab in ('ipad-portrait','iphone-390'):
            pg.evaluate("document.querySelector('#contRow').scrollIntoView({block:'center'})"); pg.wait_for_timeout(400); pg.screenshot(path=f'{SH}/{ENG}-v43-home-{lab}.png')
        cb=pg.locator(f'#contRow .rc[data-id="{x["A"]}"]'); cb.scroll_into_view_if_needed(); bb=cb.bounding_box()
        pg.touchscreen.tap(bb['x']+bb['width']/2,bb['y']+bb['height']/3); pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(800)
        st=pg.evaluate("(()=>{const R=__cr.R, v=R.views[R.vi]||[]; return {id:R.comic.id,first:v.filter(x=>x!=null)[0]}})()")
        ok(f'{lab}: tapping resumes at the saved page (p. 12)',st['id']==x['A'] and st['first']==11,json.dumps(st))
        pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
        before=pg.evaluate(f"(()=>{{const c=__cr.comics.find(c=>c.id==='{x['B']}'); return [c.page,c.progress,c.lastRead]}})()")
        cb=pg.locator(f'#contRow .rc[data-id="{x["B"]}"]'); cb.scroll_into_view_if_needed(); cb.click(button='right'); pg.wait_for_selector('#aContHide'); pg.click('#aContHide'); pg.wait_for_timeout(300)
        r2=pg.evaluate(ROW); after=pg.evaluate(f"(()=>{{const c=__cr.comics.find(c=>c.id==='{x['B']}'); return [c.page,c.progress,c.lastRead]}})()")
        ok(f'{lab}: long-press > Remove from Continue Reading hides it, progress unchanged',x['B'] not in r2['ids'] and before==after,json.dumps([r2['ids'],before,after]))
        lp=pg.evaluate("(()=>{ return !!document.querySelector('#aContHide') })()")
        ok(f'{lab}: the remove action only appears from the Continue Reading row',not lp)
        pg.evaluate(f"(()=>{{const c=__cr.comics.find(c=>c.id==='{x['B']}'); c.lastRead=Date.now(); __cr.dates.render(); }})()"); pg.wait_for_timeout(200)
        ok(f'{lab}: reading it again brings it back (first, most recent)',pg.evaluate(ROW)['ids'][0]==x['B'])
        pg.evaluate("(()=>{ __cr.comics.forEach(c=>{ c.progress=0; c.page=0; c.lastRead=0; }); __cr.dates.render(); })()"); pg.wait_for_timeout(200)
        ok(f'{lab}: row hidden when empty',pg.evaluate(ROW) is None)
        ok(f'{lab}: Home carousel still there',pg.evaluate("__cr.CF.items.length")==len(FILES))
        ctx.close()
    b.close()
print(f'\n{sum(res)}/{len(res)} passed'+(f'; page errors: {errors[:3]}' if errors else '')); sys.exit(0 if all(res) and not errors else 1)
