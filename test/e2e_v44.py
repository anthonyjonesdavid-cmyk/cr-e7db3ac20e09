"""cr-v44 suite: Home without category rows (Settings toggle 'Show category rows on Home', off by default); every series, reading list,
Mini-Series and Misc reachable from the shelf spines and Library. python3 test/e2e_v44.py [webkit] (server on 127.0.0.1:8823). Original test art."""
import sys, os, json, glob
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=sorted(glob.glob(os.path.join(T,'*.pdf')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
HOME="""(()=>{ const h=document.querySelector('#homeScroll'), kids=[...h.children].map(e=>e.className), rows=[...h.querySelector('.rows').children].map(e=>e.id||e.className);
  const sp=[...h.querySelectorAll('.spine')].map(s=>({s:s.dataset.series,q:s.dataset.q||null,misc:!!s.dataset.misc,h:s.getBoundingClientRect().height,w:s.getBoundingClientRect().width}));
  const last=h.querySelector('.rows').lastElementChild.getBoundingClientRect().bottom, hb=h.getBoundingClientRect();
  return {kids,rows,sp,cat:h.querySelectorAll('.row:not(.cont),.qrow').length,gap:Math.round(hb.bottom-last),sh:h.scrollHeight,ch:h.clientHeight}; })()"""
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        ok(f'{lab}: app launches on Home',pg.evaluate("!document.querySelector('#home').classList.contains('hidden')"))
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        x=pg.evaluate("""async()=>{ const C=__cr.comics, f=t=>C.find(c=>c.title===t); const A=f('Nightfall 02'); Object.assign(A,{page:5,progress:.2,lastRead:Date.now()});
          ['Twin Moon 01','Twin Moon 02'].forEach(t=>f(t).series='Mini-Series'); f('Glass Harbor').series=''; f('Atlas Omnibus').series='';
          const q=await __cr.qs.create('Inferno',[f('Iron Tide 02').id,f('Nightfall 01').id,f('Ember Road 03').id]); __cr.dates.render(); await new Promise(r=>setTimeout(r,300));
          return {q:q.id,qitems:q.items,series:[...new Set(C.map(c=>c.series||'').filter(Boolean))].sort(),misc:C.filter(c=>!c.series).map(c=>c.id).sort()}; }""")
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(400); s=pg.evaluate(HOME)
        ok(f'{lab}: Home = carousel, shelf, Continue Reading only (category rows off by default)',s['cat']==0 and s['rows']==['volshelf','contRow'] and s['kids'][0]=='hero' and pg.evaluate("localStorage.getItem('cr.homeRows')") is None,json.dumps(s))
        have=sorted(z['s'] for z in s['sp'] if z['s'] and not z['q'])
        ok(f'{lab}: a spine for every series (incl. Mini-Series), every reading list, and Misc',have==x['series'] and 'Mini-Series' in have and [z['q'] for z in s['sp'] if z['q']]==[x['q']] and sum(z['misc'] for z in s['sp'])==1,json.dumps([have,x['series'],s['sp']]))
        ok(f'{lab}: spines are >=40px tap targets',all(z['w']>=40 and z['h']>=40 for z in s['sp']),s['sp'])
        ok(f'{lab}: no awkward empty band at the bottom (content fills the screen)',s['sh']>=s['ch'] and s['gap']<=sab+110,json.dumps(s))
        if lab in ('ipad-portrait','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v44-home-{lab}.png')
        def tapspine(sel):
            pg.evaluate(f"document.querySelector('{sel}').scrollIntoView({{inline:'center',block:'nearest'}})"); pg.wait_for_timeout(200)
            bb=pg.locator(sel).bounding_box(); pg.touchscreen.tap(bb['x']+bb['width']/2,bb['y']+bb['height']/2); pg.wait_for_selector('#library:not(.hidden)'); pg.wait_for_timeout(500)
        tapspine('#homeScroll .spine[data-series="Mini-Series"]')
        ok(f'{lab}: Mini-Series spine opens that series',pg.evaluate("__cr.dates.TL&&[...document.querySelectorAll('#libGrid .lc')].map(e=>e.dataset.title)")==['Twin Moon 01','Twin Moon 02'])
        pg.click('#libBack'); pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
        tapspine('#homeScroll .spine[data-misc]')
        mi=pg.evaluate("({ids:[...document.querySelectorAll('#libGrid .lc')].map(e=>e.dataset.id).sort(),h:document.querySelector('.scoph h2')?.textContent})")
        ok(f'{lab}: Misc spine opens the issues without a series',mi['ids']==x['misc'] and mi['h']=='Misc',json.dumps([mi,x['misc']]))
        pg.click('#libBack'); pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
        tapspine(f'#homeScroll .spine[data-q="{x["q"]}"]')
        qi=pg.evaluate("({ids:[...document.querySelectorAll('#libGrid .lc')].map(e=>e.dataset.id),qs:[...document.querySelectorAll('#libGrid .lc')].map(e=>e.dataset.q),h:document.querySelector('.scoph h2')?.textContent,back:getComputedStyle(document.querySelector('#libBack')).display})")
        ok(f'{lab}: reading-list spine opens the list in its order, with a back button',qi['ids']==x['qitems'] and qi['h']=='Inferno' and all(q==x['q'] for q in qi['qs']) and qi['back']!='none',json.dumps(qi))
        pg.locator('#libGrid .lc').first.click(); pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(500)
        ok(f'{lab}: an issue opened from the list continues in the list order',pg.evaluate('__cr.R.queue')==x['q'])
        pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
        if pg.is_visible('#libBack'): pg.click('#libBack')
        pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(300)
        ok(f'{lab}: Library still lists every issue',pg.evaluate("document.querySelectorAll('#libGrid .lc').length")==len(FILES))
        # reversible: Settings toggle brings the rows back, and off again
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200); pg.click('#settingsBtn'); pg.wait_for_selector('#sRows')
        tb=pg.locator('#sRows').locator('xpath=..').bounding_box()
        ok(f'{lab}: Settings toggle "Show category rows on Home", off by default, >=40px',not pg.is_checked('#sRows') and tb['height']>=40,json.dumps(tb))
        pg.locator('#sRows').locator('xpath=..').click(); pg.wait_for_timeout(300); pg.click('.mwrap [data-r=done]'); pg.wait_for_timeout(300); s2=pg.evaluate(HOME)
        ok(f'{lab}: toggle on -> series and reading-list rows come back under Continue Reading',s2['cat']>=len(x['series']) and s2['rows'][:2]==['volshelf','contRow'] and pg.evaluate("localStorage.getItem('cr.homeRows')")=='true',json.dumps(s2['rows']))
        pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(600)
        ok(f'{lab}: the choice persists after relaunch',pg.evaluate(HOME)['cat']>0)
        pg.evaluate("localStorage.setItem('cr.homeRows','false')"); pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(600)
        ok(f'{lab}: off again -> rows gone',pg.evaluate(HOME)['cat']==0)
        ctx.close()
    b.close()
print(f'\n{sum(res)}/{len(res)} passed'+(f'; page errors: {errors[:3]}' if errors else '')); sys.exit(0 if all(res) and not errors else 1)
