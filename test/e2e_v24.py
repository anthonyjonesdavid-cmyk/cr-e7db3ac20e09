"""cr-v24 suite: Timeline (release dates).  python3 test/e2e_v24.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: original abstract comics from test/gen_dates.py (+ test/gen_pdfs.py). Standalone insets imitated via --sat/--sab."""
import sys, os, json, subprocess
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); D=os.path.join(T,'dates'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(os.path.join(D,'Deep_Signal_02.pdf')): subprocess.run([sys.executable,os.path.join(HERE,'gen_dates.py')],check=True)
DATED=[os.path.join(D,f) for f in sorted(os.listdir(D)) if f.endswith('.pdf')]
EXTRA=[os.path.join(T,f'Iron_Tide_0{i}.pdf') for i in range(1,6)]
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,(extra if not cond or len(str(extra))<160 else str(extra)[:160]),flush=True)
DOF="(t=>{const c=__cr.comics.find(x=>x.title===t); return __cr.dates.of(c)})"
TLS="""(()=>{const sc=document.querySelector('#tlScroll'), r=sc.getBoundingClientRect(); return {secs:[...sc.querySelectorAll('.tyr')].map(s=>/^\d{4}/.test(s.textContent)?s.textContent.slice(0,4):'unk'),
  chips:[...document.querySelectorAll('#tlDec .chip')].map(b=>b.textContent), on:(document.querySelector('#tlDec .chip.on')||{}).textContent,
  overflow:document.documentElement.scrollWidth>innerWidth||sc.scrollWidth>sc.clientWidth+1, scrollable:sc.scrollHeight>sc.clientHeight}})()"""
def importf(pg,files,total):
    pg.set_input_files('#fileIn',files); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={total} && !document.querySelector(".toast .tb")',timeout=120000); pg.wait_for_timeout(300)
def chrome(pg,lab,sat):
    g=pg.evaluate("""(()=>{const q=s=>document.querySelector(s).getBoundingClientRect(), bar=document.querySelector('.tlbar');
      return {bg:getComputedStyle(bar).backgroundColor, h2:q('#timeline h2').top, back:[q('#tlBack').width,q('#tlBack').height],
        chips:[...document.querySelectorAll('#tlDec .chip')].map(b=>{const r=b.getBoundingClientRect(); return Math.min(r.width,r.height)}),
        cards:[...document.querySelectorAll('#tlScroll .tcb')].slice(0,6).map(b=>{const r=b.getBoundingClientRect(); return Math.min(r.width,r.height)}),
        hbg:getComputedStyle(document.querySelector('.tyr')).backgroundColor}})()""")
    ok(f'{lab}: Timeline bar solid black, title clear of the status bar',g['bg']=='rgb(0, 0, 0)' and g['h2']>=sat and g['hbg']=='rgb(0, 0, 0)',json.dumps(g))
    ok(f'{lab}: tap targets >=40px (back, decade chips, issue cards)',min(g['back'])>=40 and min(g['chips'])>=40 and min(g['cards'])>=40,json.dumps(g))
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1024,1366,'ipad-portrait',2,24,20),(1366,1024,'ipad-landscape',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]'); full=lab=='ipad-portrait'
        importf(pg,DATED+(EXTRA if full else []),len(DATED)+(len(EXTRA) if full else 0))
        if full:
            got={t:pg.evaluate(DOF,t) for t in ['Comet Run 01 (1983)','Comet Run 02 (Mar 1984)','Deep Signal 01','Deep Signal 02','Paper Moons 01']}
            ok('file name "(1983)" -> 1983',got['Comet Run 01 (1983)']=={'y':1983,'m':0,'src':'name'},json.dumps(got))
            ok('file name "(Mar 1984)" -> March 1984',got['Comet Run 02 (Mar 1984)']=={'y':1984,'m':3,'src':'name'})
            ok('XMP prism:coverDate -> June 1991',got['Deep Signal 01']=={'y':1991,'m':6,'src':'meta'})
            ok('attached ComicInfo.xml -> February 1992',got['Deep Signal 02']=={'y':1992,'m':2,'src':'meta'})
            ok('no date anywhere -> Unknown',got['Paper Moons 01'] is None)
            u=pg.evaluate("""[__cr.dates.lookup('Saga',7),__cr.dates.lookup('The Amazing Spider-Man',1),__cr.dates.lookup('Uncanny X-Men',13),__cr.dates.lookup('Nightfall',2),__cr.dates.lookup('Saga',null),
              __cr.dates.fromName('Ember Road 01'),__cr.dates.fromName('Thing_(2019-11)'),__cr.dates.fromName('X 1999 issue'),__cr.dates.fromName('Old (1871)'),__cr.dates.comicInfo('<Year>2001</Year><Month>13</Month>')]""")
            ok('built-in series table estimates (Saga #7 ≈ Sep 2012, ASM #1 = Mar 1963, X-Men #13 ≈ Sep 1964)',u[0]=={'y':2012,'m':9,'src':'lookup'} and u[1]=={'y':1963,'m':3,'src':'lookup'} and u[2]=={'y':1964,'m':9,'src':'lookup'},json.dumps(u))
            ok('unknown series / no issue -> no estimate',u[3] is None and u[4] is None)
            ok('name parser: no false years, (YYYY-MM) works, out-of-range ignored',u[5] is None and u[6]=={'y':2019,'m':11,'src':'name'} and u[7] is None and u[8] is None and u[9]=={'y':2001,'m':0,'src':'meta'},json.dumps(u[5:]))
            for t,y in [('Iron Tide 01',1962),('Iron Tide 02',1968),('Iron Tide 03',1974),('Iron Tide 04',2003)]:
                pg.evaluate(f"__cr.dates.set(__cr.comics.find(c=>c.title==='{t}'),{{y:{y},m:5}})")
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200)
        hb=pg.locator('#tlOpen').bounding_box(); ok(f'{lab}: Home has a compact Timeline entry (>=40px, shows the year range)',hb and hb['height']>=40 and hb['height']<=52 and ('1983' in pg.text_content('#tlOpen') or '1962' in pg.text_content('#tlOpen')),json.dumps(hb)+pg.text_content('#tlOpen'))
        pg.click('#tlOpen'); pg.wait_for_timeout(300); st=pg.evaluate(TLS)
        if full:
            ok('Timeline: years ascending, Unknown last',st['secs']==['1962','1968','1974','1983','1984','1991','1992','2003','unk'],json.dumps(st))
            ok('decade chips',st['chips']==['1960s','1970s','1980s','1990s','2000s','Unknown'] and st['on']=='1960s',json.dumps(st))
            order=pg.eval_on_selector_all('.tcb','e=>e.map(x=>x.getAttribute("aria-label")).filter(t=>t.startsWith("Comet"))'); ok('cards labelled with month/year',order==['Comet Run 01 (1983), 1983','Comet Run 02 (Mar 1984), Mar 1984'],json.dumps(order))
            pg.screenshot(path=f'{SH}/{ENG}-v24-timeline-ipad-portrait.png')
            pg.click('#tlDec .chip:has-text("1990s")'); pg.wait_for_timeout(900)
            g=pg.evaluate("(()=>{const sc=document.querySelector('#tlScroll').getBoundingClientRect().top, h=document.querySelector('.tc[data-dec=\"1990\"]').getBoundingClientRect().top; return {d:h-sc,on:document.querySelector('#tlDec .chip.on').textContent,scrollable:document.querySelector('#tlScroll').scrollHeight>document.querySelector('#tlScroll').clientHeight}})()")
            ok('decade chip jumps to that decade',(abs(g['d'])<14 or not g['scrollable']),json.dumps(g))
            g=pg.evaluate("(()=>{const cs=[...document.querySelectorAll('#tlGrid .tc')].map(e=>e.getBoundingClientRect()); const rows=[...new Set(cs.map(r=>Math.round(r.top)))]; return {n:cs.length,rows:rows.length,perRow:Math.floor(document.querySelector('#tlGrid').clientWidth/cs[0].width),gaps:rows.slice(1).map((t,k)=>t-rows[k]-cs[0].height)}})()")
            ok('one continuous compact grid: issues flow across rows, no per-year breaks or big gaps',g['rows']==-(-g['n']//g['perRow']) and all(x<=14 for x in g['gaps']),json.dumps(g))
            pg.screenshot(path=f'{SH}/{ENG}-v24-timeline-sticky-ipad-portrait.png'); pg.evaluate("document.querySelector('#tlScroll').scrollTop=0")
            pg.click('.tcb:has-text("Deep Signal 01")'); pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(500)
            ok('tap an issue opens it',pg.evaluate("__cr.R.comic&&__cr.R.comic.title")=='Deep Signal 01')
            pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
            ok('closing the reader returns to the Timeline',pg.is_visible('#timeline'))
            pg.locator('.tcb:has-text("Paper Moons 01")').click(button='right'); pg.wait_for_selector('#aDate'); ok('long-press sheet shows Release Date (Unknown)','Unknown' in pg.text_content('#aDate'))
            pg.click('#aDate'); pg.wait_for_selector('#dYear'); ok('Save disabled until a 4-digit year',pg.is_disabled('#dSave'))
            pg.select_option('#dMonth','4'); pg.fill('#dYear','1977'); pg.wait_for_timeout(100); pg.click('#dSave'); pg.wait_for_timeout(500)
            st=pg.evaluate(TLS); ok('set month/year -> issue moves into 1977',pg.evaluate(DOF,'Paper Moons 01')=={'y':1977,'m':4,'src':'manual'} and '1977' in st['secs'],json.dumps(st['secs']))
            pg.screenshot(path=f'{SH}/{ENG}-v24-date-set-ipad-portrait.png')
            idb=pg.evaluate("new Promise(r=>{const q=indexedDB.open('comic-reader'); q.onsuccess=()=>{const d=q.result; const t=d.transaction('overrides').objectStore('overrides').getAll(); t.onsuccess=()=>r({v:d.version,n:t.result.filter(o=>o.k.includes('Paper_Moons_01')).map(o=>o.date)})}})")
            ok('manual date stored in IndexedDB (v3 overrides store)',idb['v']==3 and idb['n']==[{'y':1977,'m':4}],json.dumps(idb))
            pg.click('#tlBack'); pg.click('#tabs [data-tab=library]'); pg.locator('.lc[data-title="Paper Moons 01"]').click(button='right'); pg.click('#aDelete'); pg.click('#confirmOk'); pg.wait_for_timeout(400)
            n=pg.evaluate('__cr.comics.length'); importf(pg,[os.path.join(D,'Paper_Moons_01.pdf')],n+1)
            ok('manual date survives delete + re-import',pg.evaluate(DOF,'Paper Moons 01')=={'y':1977,'m':4,'src':'manual'})
            pg.reload(); pg.wait_for_selector('html[data-ready]'); ok('reload: launch lands on Home, timeline closed; date persisted',pg.is_visible('#homeScroll') and not pg.is_visible('#timeline') and pg.evaluate(DOF,'Paper Moons 01')['y']==1977)
            pg.click('#tabs [data-tab=library]'); pg.locator('.lc[data-title="Paper Moons 01"]').click(button='right'); pg.click('#aDate'); pg.wait_for_selector('#dClear'); pg.click('#dClear'); pg.wait_for_timeout(400)
            ok('"Automatic" clears the manual date (back to Unknown)',pg.evaluate(DOF,'Paper Moons 01') is None and not any('Paper_Moons_01' in k for k in pg.evaluate('[...__cr.dates.ov().keys()]')))
            pg.click('#tabs [data-tab=home]'); pg.click('#tlOpen'); pg.wait_for_timeout(300); st=pg.evaluate(TLS)
        ok(f'{lab}: no horizontal overflow',not st['overflow'],json.dumps(st))
        chrome(pg,lab,sat)
        pg.screenshot(path=f'{SH}/{ENG}-v24-timeline-{lab}.png')
        ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
