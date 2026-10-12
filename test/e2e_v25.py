"""cr-v25 suite: spinner rack (Timeline).  python3 test/e2e_v25.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: original abstract comics (test/gen_dates.py, test/gen_pdfs.py). Standalone insets imitated via --sat/--sab."""
import sys, os, json, subprocess
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); D=os.path.join(T,'dates'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(os.path.join(D,'Deep_Signal_02.pdf')): subprocess.run([sys.executable,os.path.join(HERE,'gen_dates.py')],check=True)
FILES=[os.path.join(D,f) for f in sorted(os.listdir(D)) if f.endswith('.pdf')]+[os.path.join(T,f'Iron_Tide_0{i}.pdf') for i in range(1,6)]
MAN=[('Iron Tide 01',1984,1),('Iron Tide 05',1984,2),('Iron Tide 02',1984,4),('Iron Tide 04',1984,5),('Iron Tide 03',1984,9)]
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,(extra if not cond or len(str(extra))<160 else str(extra)[:160]),flush=True)
RS="""(()=>{const K=__cr.rack.RK; return {on:K.on,a:K.a,v:K.v,N:K.N,step:K.step,front:K.front,win:K.win,raf:!!K.raf,title:document.querySelector('#rkTitle').textContent,sub:document.querySelector('#rkSub').textContent,
  covers:document.querySelectorAll('#rkRotor .pkc').length,frontCovers:[...document.querySelectorAll('#rkRotor .rf.front .pkc')].map(b=>b.getAttribute('aria-label').split(',')[0]),
  empty:!document.querySelector('#rkEmpty').classList.contains('hidden'),overflow:document.documentElement.scrollWidth>innerWidth}})()"""
def rs(pg): return pg.evaluate(RS)
def drag(pg,dx,steps=6,hold=0):
    b=pg.locator('#rkStage').bounding_box(); x=b['x']+b['width']/2; y=b['y']+b['height']*.5
    pg.mouse.move(x,y); pg.mouse.down()
    for i in range(1,steps+1): pg.mouse.move(x+dx*i/steps,y)
    if hold: pg.wait_for_timeout(hold)
    pg.mouse.up()
def chrome(pg,lab,sat):
    g=pg.evaluate("""(()=>{const q=s=>document.querySelector(s).getBoundingClientRect();
      return {bg:getComputedStyle(document.querySelector('.rkbar')).backgroundColor, t:q('#rkTitle').top, sub:q('#rkSub').bottom<=q('.rkbar').bottom,
        btn:['#rkBack','#rkPrev','#rkNext','#rkLeft','#rkRight'].map(s=>{const r=q(s); return Math.min(r.width,r.height)}),
        stageTop:q('#rkStage').top>=q('.rkbar').bottom-1}})()""")
    ok(f'{lab}: rack bar solid black, title clear of the status bar',g['bg']=='rgb(0, 0, 0)' and g['t']>=sat and g['sub'] and g['stageTop'],json.dumps(g))
    ok(f'{lab}: rack buttons >=40px',min(g['btn'])>=40,json.dumps(g))
def setup(pg):
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=120000)
    for t,y,m in MAN: pg.evaluate(f"__cr.dates.set(__cr.comics.find(c=>c.title==='{t}'),{{y:{y},m:{m}}})")
    pg.wait_for_timeout(300); pg.click('#tabs [data-tab=home]'); pg.click('#tlOpen'); pg.wait_for_timeout(300)
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab,rm) in [(1024,1366,'ipad-portrait',2,24,20,'no-preference'),(1366,1024,'ipad-landscape',2,24,20,'no-preference'),(390,844,'iphone-390',3,47,34,'reduce'),(430,932,'iphone-430',3,59,34,'no-preference')]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr,reduced_motion=rm)
        ctx.add_init_script(f"window.__crNoScan=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e))); setup(pg); full=lab=='ipad-portrait'
        rb=pg.evaluate("[...document.querySelectorAll('.tlh .rkbtn')].map(b=>{const r=b.getBoundingClientRect(); return [b.closest('.tly').dataset.y,Math.min(r.width,r.height)]})")
        ok(f'{lab}: every year section has a rack button >=40px',len(rb)==len(pg.eval_on_selector_all('.tly[data-y]','e=>e')) and all(s>=40 for _,s in rb),json.dumps(rb))
        pg.click('.tly[data-y="1984"] .rkbtn'); pg.wait_for_timeout(500); s=rs(pg)
        ok(f'{lab}: opens "On the racks · Mar 1984"; few issues -> window widened to ±6 months',s['on'] and s['title']=='On the racks · Mar 1984' and s['win']==6 and s['sub'] in ('6 issues · Sep 1983 – Sep 1984 (widened)','6 issues · Sep ’83 – Sep ’84'),json.dumps(s))
        ok(f'{lab}: 4-sided rack, pockets hold the 6 covers (Jun 1983 issue outside the window)',s['N']==4 and s['covers']==6 and 'Comet Run 01 (1983)' not in s['frontCovers'],json.dumps(s))
        ok(f'{lab}: no horizontal overflow; subtitle not truncated',not s['overflow'] and pg.evaluate("(e=>e.scrollWidth<=e.clientWidth+1)(document.querySelector('#rkSub'))"))
        chrome(pg,lab,sat)
        pg.screenshot(path=f'{SH}/{ENG}-v25-rack-{lab}.png')
        if rm=='reduce':
            drag(pg,-260); pg.wait_for_timeout(30); s=rs(pg)
            ok(f'{lab}: reduced motion: no momentum, lands straight on a face',not s['raf'] and abs(s['a']/s['step']-round(s['a']/s['step']))<1e-6,json.dumps(s))
            pg.click('#rkRight'); s2=rs(pg); ok(f'{lab}: reduced motion: spin button jumps one face',abs(s2['a']-(s['a']-s['step']))<1e-6 and not s2['raf'],json.dumps(s2))
            pg.click('#rkLeft'); pg.click('#rkLeft'); ok(f'{lab}: back to the full front face',rs(pg)['front']==0)
        if full:
            drag(pg,-300,steps=4); pg.wait_for_timeout(60); a1=rs(pg); pg.wait_for_timeout(120); a2=rs(pg)
            ok('fast swipe spins with momentum (keeps turning after release)',a1['raf'] and abs(a2['a']-a1['a'])>0.5,json.dumps([a1['a'],a2['a']]))
            pg.wait_for_function('!__cr.rack.RK.raf',timeout=8000); s=rs(pg)
            ok('momentum settles squarely on a face',abs(s['a']/s['step']-round(s['a']/s['step']))<1e-3,json.dumps(s))
            drag(pg,-60,steps=10,hold=200); pg.wait_for_function('!__cr.rack.RK.raf',timeout=5000); s3=rs(pg)
            ok('slow drag + hold: no fling, snaps to nearest face',abs(s3['a']/s3['step']-round(s3['a']/s3['step']))<1e-3,json.dumps(s3))
            a0=rs(pg)['a']; pg.click('#rkLeft'); pg.wait_for_function('!__cr.rack.RK.raf',timeout=5000); ok('spin button turns exactly one face',abs(rs(pg)['a']-(round(a0/90)*90+90))<1e-3)
            pg.evaluate("__cr.rack.RK.a=0"); pg.click('#rkRight'); pg.wait_for_function('!__cr.rack.RK.raf'); pg.click('#rkLeft'); pg.wait_for_function('!__cr.rack.RK.raf'); s=rs(pg)
            ok('front face is full (first 6 by date: Jan…Sep 1984 & Mar 1984)',s['front']==0 and len(s['frontCovers'])==6,json.dumps(s))
            # tap a back-face cover: rotates it to the front instead of opening
            tgt=s['frontCovers'][2]; hl=pg.evaluate('history.length'); pg.locator(f'#rkRotor .rf.front .pkc[aria-label^="{tgt},"]').click(); pg.wait_for_timeout(120); pg.mouse.click(pg.viewport_size['width']/2,pg.viewport_size['height']/2)
            pull=pg.evaluate("!!document.querySelector('.rkpull')"); pg.screenshot(path=f'{SH}/{ENG}-v25-rack-pullout-{lab}.png')
            pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(700)
            ok('tap a cover: it pulls out (animated) and opens in the reader',pull and pg.evaluate('__cr.R.comic.title')==tgt,tgt)
            pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
            ok('a second tap during the pull-out does not open it twice',pg.evaluate('history.length')==hl+1,str(pg.evaluate('history.length')-hl))
            ok('closing the reader returns to the rack (same month)',pg.is_visible('#rack') and rs(pg)['title']=='On the racks · Mar 1984' and not pg.evaluate("!!document.querySelector('.rkpull')"))
            pg.click('#rkNext'); s=rs(pg); ok('next month arrow moves the window',s['title']=='On the racks · Apr 1984',s['title'])
            pg.click('#rkPrev'); pg.click('#rkPrev'); ok('prev month arrow',rs(pg)['title']=='On the racks · Feb 1984')
            pg.evaluate("__cr.rack.open(1940*12)"); pg.wait_for_timeout(200); s=rs(pg); ok('empty window: message, nothing on the rack',s['empty'] and s['covers']==0 and s['sub']=='Nothing dated near this month',json.dumps(s))
            pg.click('#rkBack'); ok('back returns to the Timeline',pg.is_visible('#timeline') and not pg.is_visible('#rack'))
            pg.click('.tly[data-y="1984"] .rkbtn'); pg.wait_for_timeout(300); pg.reload(); pg.wait_for_selector('html[data-ready]'); ok('relaunch: Home, rack closed',not pg.is_visible('#rack') and pg.is_visible('#homeScroll'))
        else:
            pg.wait_for_timeout(100)
            tgt=rs(pg)['frontCovers'][0]; pg.locator('#rkRotor .rf.front .pkc').first.click()
            pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(500)
            ok(f'{lab}: tap a front cover opens it'+(' (no pull-out animation with reduced motion)' if rm=='reduce' else ''),pg.evaluate('__cr.R.comic.title')==tgt)
            pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300); ok(f'{lab}: back to the rack',pg.is_visible('#rack'))
        ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
