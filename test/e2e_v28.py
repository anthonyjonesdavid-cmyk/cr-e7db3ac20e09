"""cr-v28 suite: 'This week in…' Home row.  python3 test/e2e_v28.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: original abstract comics from test/gen_dates.py. 'Today' is pinned with window.__crNow. Standalone insets via --sat/--sab."""
import sys, os, json, subprocess
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); D=os.path.join(HERE,'..','testpdfs','dates'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(os.path.join(D,'Deep_Signal_02.pdf')): subprocess.run([sys.executable,os.path.join(HERE,'gen_dates.py')],check=True)
DATED=[os.path.join(D,f) for f in sorted(os.listdir(D)) if f.endswith('.pdf')]
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:220] if not cond else '',flush=True)
ROW="""(()=>{const s=document.querySelector('#homeScroll .otw'); if(!s) return null; const r=e=>e.getBoundingClientRect();
  return {kind:s.dataset.kind,title:s.querySelector('h2').textContent,tiles:[...s.querySelectorAll('.rc')].map(b=>b.querySelector('.t').textContent+'|'+b.querySelector('.yr').textContent),
    first:s===document.querySelector('#homeScroll .rows').firstElementChild||(s.previousElementSibling&&s.previousElementSibling.classList.contains('volshelf')&&s.previousElementSibling===document.querySelector('#homeScroll .rows').firstElementChild), tap:Math.min(...[...s.querySelectorAll('.rc')].map(b=>Math.min(r(b).width,r(b).height))),
    h:r(s.querySelector('.row-h')).height, sameH:r(s.querySelector('.rc .cvr')).height===r(document.querySelector('#homeScroll .row:not(.otw) .rc .cvr')||s.querySelector('.rc .cvr')).height}})()"""
SETN="(([t,k,v])=>{const c=__cr.comics.find(x=>x.title===t); if(v===null) delete c[k]; else c[k]=v; __cr.dates.render()})"
def now(pg,iso): pg.evaluate(f"window.__crNow=new Date('{iso}T12:00:00').getTime(); sessionStorage.crNow=window.__crNow; __cr.dates.render()"); pg.wait_for_timeout(150)
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; if(sessionStorage.crNow) window.__crNow=+sessionStorage.crNow; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        pg.set_input_files('#fileIn',DATED); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(DATED)} && !document.querySelector(".toast .tb")',timeout=120000)
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
        full=lab=='ipad-landscape'
        if full:
            u=pg.evaluate("[__cr.dates.comicInfo('<Year>1990</Year><Month>6</Month><Day>12</Day>'),__cr.dates.comicInfo('<Year>1990</Year><Month>6</Month><Day>1</Day>'),__cr.dates.weekDate({title:'Saga 7',series:'Saga',fileName:'Saga_07.pdf'})]")
            ok('ComicInfo <Day> kept as an exact day; Day 1 placeholder stays month-level; ≈ estimates are not used',u[0]=={'y':1990,'m':6,'d':12,'src':'meta'} and u[1]=={'y':1990,'m':6,'src':'meta'} and u[2] is None,json.dumps(u))
            now(pg,'2026-01-10'); ok('no issue from this week or month -> row hidden',pg.evaluate(ROW) is None)
            now(pg,'2026-06-10'); r=pg.evaluate(ROW)
            ok('month fallback: June 1991 (XMP) shown as "On sale this month in past years" with its year',r and r['kind']=='month' and r['title']=='On sale this month in past years' and r['tiles']==['Deep Signal 01|1991'],json.dumps(r))
            pg.evaluate("__cr.dates.set(__cr.comics.find(c=>c.title==='Paper Moons 01'),{y:1980,m:6})"); pg.wait_for_timeout(300); r=pg.evaluate(ROW)
            ok('hand-set date joins the month row, newest year first',r['tiles']==['Deep Signal 01|1991','Paper Moons 01|1980'],json.dumps(r))
            pg.evaluate(SETN,['Comet Run 01 (1983)','onlineDate',{'y':1983,'m':6,'d':12,'src':'online'}]); r=pg.evaluate(ROW)
            ok('exact-day match within this week wins: "This week in past years"',r['kind']=='week' and r['title']=='This week in past years' and r['tiles']==['Comet Run 01 (1983)|1983'],json.dumps(r))
            ok('tile shows year and day',pg.text_content('#homeScroll .otw .rc .s').strip()=='1983 · Jun 12')
            pg.evaluate(SETN,['Comet Run 01 (1983)','onlineDate',{'y':1983,'m':6,'d':20,'src':'online'}]); r=pg.evaluate(ROW)
            ok('a day outside ±3 days falls back to the month row',r['kind']=='month' and 'Comet Run 01 (1983)|1983' in r['tiles'],json.dumps(r))
            pg.evaluate(SETN,['Deep Signal 01','onlineDate',{'y':1991,'m':7,'src':'online'}]); r=pg.evaluate(ROW)
            ok('priority: online date beats embedded metadata',not any(t.startswith('Deep Signal 01') for t in r['tiles']),json.dumps(r))
            pg.evaluate("__cr.dates.set(__cr.comics.find(c=>c.title==='Deep Signal 01'),{y:1975,m:6})"); pg.wait_for_timeout(300); r=pg.evaluate(ROW)
            ok('priority: hand-set beats online',any(t=='Deep Signal 01|1975' for t in r['tiles']),json.dumps(r))
            pg.evaluate(SETN,['Comet Run 01 (1983)','onlineDate',{'y':1983,'m':6,'d':12,'src':'online'}])
            pg.click('#homeScroll .otw .rc'); pg.wait_for_selector('#reader:not(.hidden)'); ok('tap a tile opens the issue',pg.evaluate('__cr.R.comic.title')=='Comet Run 01 (1983)')
            pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
            pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(400)
            ok('launch on Home; row computed at open from saved dates (no background task)',pg.is_visible('#homeScroll') and (pg.evaluate(ROW) or {}).get('tiles')==['Comet Run 01 (1983)|1983'],json.dumps(pg.evaluate(ROW)))
        else:
            pg.evaluate("__cr.dates.set(__cr.comics.find(c=>c.title==='Paper Moons 01'),{y:1980,m:6})"); now(pg,'2026-06-10')
        r=pg.evaluate(ROW)
        ok(f'{lab}: row is first under the carousel (after the v30 shelf of volumes), same row style, tiles >=40px',r and r['first'] and r['sameH'] and r['tap']>=40 and r['h']>=34,json.dumps(r))
        g=pg.evaluate("(()=>({tb:getComputedStyle(document.querySelector('.topbar')).backgroundColor,top:document.querySelector('#tabs').getBoundingClientRect().top,ov:document.documentElement.scrollWidth>innerWidth}))()")
        ok(f'{lab}: solid top bar, tabs clear of status bar, no overflow',g['tb']=='rgb(0, 0, 0)' and g['top']>=sat and not g['ov'],json.dumps(g))
        pg.evaluate("document.querySelector('#homeScroll .otw').scrollIntoView({block:'center'})"); pg.wait_for_timeout(200)
        pg.screenshot(path=f'{SH}/{ENG}-v28-thisweek-{lab}.png'); ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
