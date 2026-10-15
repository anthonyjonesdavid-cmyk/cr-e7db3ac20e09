"""cr-v26 suite: realistic spinner rack (always full), compact Timeline, online release-date lookup, volume-aware estimates.
python3 test/e2e_v26.py [webkit]  (server on 127.0.0.1:8823). Fixtures: original abstract comics (test/gen_dates.py, test/gen_pdfs.py).
The Fandom wiki API is mocked for the UI tests; one extra check calls the real API from the page (skipped when offline)."""
import sys, os, json, subprocess, re, urllib.parse
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); D=os.path.join(T,'dates'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(os.path.join(D,'Deep_Signal_02.pdf')): subprocess.run([sys.executable,os.path.join(HERE,'gen_dates.py')],check=True)
FILES=[os.path.join(D,f) for f in sorted(os.listdir(D)) if f.endswith('.pdf')]+[os.path.join(T,f'Iron_Tide_0{i}.pdf') for i in range(1,6)]
MAN=[('Iron Tide 01',1984,1),('Iron Tide 05',1984,2),('Iron Tide 02',1984,4),('Iron Tide 04',1984,5),('Iron Tide 03',1984,9)]
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,(extra if not cond or len(str(extra))<160 else str(extra)[:160]),flush=True)
# ---- mock of the MediaWiki API on *.fandom.com: fake original series only
WIKI={'marvel':{'Paper Moons Vol 1 1':(7,1979),'Paper Moons Vol 1 2':(9,1979),'Paper Moons Vol 2 2':(3,2004)}}
CALLS=[]
def wiki_route(route):
    u=urllib.parse.urlparse(route.request.url); w=u.netloc.split('.')[0]; q=dict(urllib.parse.parse_qsl(u.query)); CALLS.append((w,q.get('titles','')))
    pages=[]
    for t in q.get('titles','').split('|'):
        if not t: continue
        if t in WIKI.get(w,{}): m,y=WIKI[w][t]; pages.append({'pageid':1,'ns':0,'title':t,'revisions':[{'slots':{'main':{'content':f'{{{{Comic Template\n| Month = {m}\n| Year = {y}\n}}}}'}}}]})
        else: pages.append({'ns':0,'title':t,'missing':True})
    route.fulfill(status=200,headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'},body=json.dumps({'batchcomplete':True,'query':{'pages':pages}}))
RS="""(()=>{const K=__cr.rack.RK, st=document.querySelector('#rkStage').getBoundingClientRect(), sc=document.querySelector('#rkScene').getBoundingClientRect();
  const pk=[...document.querySelectorAll('#rkRotor .pk')]; const vis=pk.filter(e=>e.style.visibility!=='hidden');
  const xs=vis.map(e=>{const r=e.getBoundingClientRect(); return r.left+r.width/2-(st.left+st.width/2)});
  return {on:K.on,a:K.a,raf:!!K.raf,N:K.N,T:K.T,step:K.step,front:K.front,repeats:K.repeats,title:document.querySelector('#rkTitle').textContent,sub:document.querySelector('#rkSub').textContent,
    pockets:pk.length,filled:pk.filter(e=>e.querySelector('img[src^="blob:"]')).length,wingsVisible:new Set(vis.map(e=>e.dataset.w)).size,left:xs.filter(x=>x<-20).length,right:xs.filter(x=>x>20).length,
    fill:sc.height/st.height,sign:(document.querySelector('.rksign')||{}).textContent,
    tilt:(()=>{const e=pk.find(e=>e.classList.contains('front')); if(!e) return null; const m=new DOMMatrix(getComputedStyle(e).transform), h=e.offsetHeight, top=m.transformPoint(new DOMPoint(0,-h,0)), bot=m.transformPoint(new DOMPoint(0,0,0)); return {topZ:top.z,botZ:bot.z,R:K.R}})(),
    cream:getComputedStyle(document.querySelector('.rkpole')).backgroundImage,
    frontIds:pk.filter(e=>e.dataset.w==='0').map(e=>e.querySelector('.pkc').dataset.rk), overflow:document.documentElement.scrollWidth>innerWidth}})()"""
def rs(pg): return pg.evaluate(RS)
def drag(pg,dx,steps=6,hold=0):
    b=pg.locator('#rkStage').bounding_box(); x=b['x']+b['width']/2; y=b['y']+b['height']*.5
    pg.mouse.move(x,y); pg.mouse.down()
    for i in range(1,steps+1): pg.mouse.move(x+dx*i/steps,y)
    if hold: pg.wait_for_timeout(hold)
    pg.mouse.up()
def bars(pg,lab,sat,which):
    sel={'rack':('.rkbar','#rkTitle',['#rkBack','#rkPrev','#rkNext','#rkLeft','#rkRight']),'tl':('.tlbar','#tabs',['#tabs button','#tlRack','#tlDec .chip','.tyr','.tcb'])}[which]
    g=pg.evaluate("""([bar,t,bs])=>({bg:getComputedStyle(document.querySelector(bar)).backgroundColor,t:document.querySelector(t).getBoundingClientRect().top,
      btn:bs.map(s=>Math.min(...[...document.querySelectorAll(s)].slice(0,8).map(b=>{const r=b.getBoundingClientRect(); return Math.min(r.width,r.height)})))})""",list(sel))
    ok(f'{lab}: {which} bar solid black, nothing under the status bar, tap targets >=40px',g['bg']=='rgb(0, 0, 0)' and g['t']>=sat and min(g['btn'])>=40,json.dumps(g))
def setup(pg):
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=120000)
    for t,y,m in MAN: pg.evaluate(f"__cr.dates.set(__cr.comics.find(c=>c.title==='{t}'),{{y:{y},m:{m}}})")
    pg.wait_for_timeout(300); pg.click('#tabs [data-tab=home]'); pg.click('#tabs [data-tab=timeline]'); pg.wait_for_timeout(300)
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab,rm) in [(1024,1366,'ipad-portrait',2,24,20,'no-preference'),(1366,1024,'ipad-landscape',2,24,20,'no-preference'),(390,844,'iphone-390',3,47,34,'reduce'),(430,932,'iphone-430',3,59,34,'no-preference')]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr,reduced_motion=rm,service_workers='block')   # routes can't see SW-controlled fetches
        ctx.add_init_script(f"window.__crNoScan=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        ctx.route(re.compile(r'https://[a-z]+\.fandom\.com/api\.php.*'),wiki_route)
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e))); setup(pg); full=lab=='ipad-portrait'
        # ---- Timeline: one compact grid
        g=pg.evaluate("(()=>{const cs=[...document.querySelectorAll('#tlGrid .tc')]; const r=cs.map(e=>e.getBoundingClientRect()); const rows=[...new Set(r.map(x=>Math.round(x.top)))]; return {n:cs.length,rows:rows.length,per:Math.round(document.querySelector('#tlGrid').clientWidth/r[0].width),gaps:rows.slice(1).map((t,k)=>Math.round(t-rows[k]-r[0].height)),labels:[...document.querySelectorAll('.tyr')].map(e=>e.textContent),sections:document.querySelectorAll('.tly,.tlh').length}})()")
        ok(f'{lab}: Timeline is one continuous compact grid, small inline year labels only',g['sections']==0 and g['rows']==-(-g['n']//max(1,g['per'])) and all(x<=14 for x in g['gaps']) and g['labels']==['1983','1984','1991','1992','Unknown'],json.dumps(g))
        bars(pg,lab,sat,'tl')
        pg.screenshot(path=f'{SH}/{ENG}-v27-timeline-{lab}.png'); pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300); pg.evaluate('__cr.CF.to(0,10)'); pg.wait_for_timeout(400); pg.screenshot(path=f'{SH}/{ENG}-v27-home-{lab}.png'); pg.click('#tabs [data-tab=timeline]'); pg.wait_for_timeout(300)
        pg.click('.tyr:has-text("1984")'); pg.wait_for_timeout(500); s=rs(pg)
        ok(f'{lab}: tap a year label opens its rack ("On the racks · Jan 1984")',s['on'] and s['title']=='On the racks · Jan 1984',s['title'])
        ok(f'{lab}: every pocket filled (6 wings × 8 tiers); small library repeats to fill',s['pockets']==48 and s['filled']==48 and s['repeats'] and 'repeats' in s['sub'] and pg.evaluate("(e=>e.scrollWidth<=e.clientWidth+1)(document.querySelector('#rkSub'))"),json.dumps(s))
        ok(f'{lab}: tall rack: fills most of the screen height, v36 sign "COMICS FOR ALL AGES", several wings visible around the pole',s['fill']>=.8 and s['sign']=='COMICSFOR ALL AGES' and s['wingsVisible']>=5 and s['left']>0 and s['right']>0,json.dumps(s))
        ok(f'{lab}: no horizontal overflow',not s['overflow'])
        bars(pg,lab,sat,'rack')
        ok(f'{lab}: v36 tilt: front comics sit in the pocket by the pole and their TOP leans OUT away from it',s['tilt'] and s['tilt']['topZ']>s['tilt']['botZ']+5 and abs(s['tilt']['botZ']-s['tilt']['R'])<3,json.dumps(s['tilt']))
        ok(f'{lab}: v36 cream wire frame / pole',('246, 241, 228' in s['cream']),s['cream'])
        pg.screenshot(path=f'{SH}/{ENG}-v36-rack-{lab}.png')
        if full:
            near=pg.evaluate("""(()=>{const K=__cr.rack.RK, d=c=>__cr.dates.of(c), ym=K.ym; const dist=c=>{const x=d(c); return x?Math.abs(x.y*12+(x.m||6)-1-ym):1e9};
              const ids=new Set([...document.querySelectorAll('#rkRotor .pk[data-w="0"] .pkc')].map(b=>b.dataset.rk)); const all=__cr.comics.slice().sort((a,b)=>dist(a)-dist(b));
              return {front:[...ids].map(i=>dist(__cr.comics.find(c=>c.id===i))).sort((a,b)=>a-b),nearest:all.slice(0,8).map(dist)}})()""")
            ok('fills outward from the month: the front wing holds the 8 nearest-dated issues',near['front']==near['nearest'],json.dumps(near))
            u=pg.evaluate("(()=>{const r=__cr.rack.items(1984*12,5); return {n:r.L.length,uniq:new Set(r.L.map(x=>x.c.id)).size,rep:r.repeats}})()")
            ok('no repeats when the library has enough issues for the rack',u=={'n':5,'uniq':5,'rep':False},json.dumps(u))
            drag(pg,-300,steps=4); pg.wait_for_timeout(60); a1=rs(pg); pg.wait_for_timeout(120); a2=rs(pg)
            ok('swipe spins around the pole with momentum',a1['raf'] and abs(a2['a']-a1['a'])>0.5,json.dumps([a1['a'],a2['a']]))
            pg.wait_for_function('!__cr.rack.RK.raf',timeout=8000); s=rs(pg); ok('settles facing a wing (60° steps)',abs(s['a']/60-round(s['a']/60))<1e-3,json.dumps(s['a']))
            pg.screenshot(path=f'{SH}/{ENG}-v36-rack-turned-{lab}.png')
            pg.evaluate("__cr.rack.RK.a=0"); pg.click('#rkLeft'); pg.wait_for_function('!__cr.rack.RK.raf'); ok('spin button turns one wing',abs(rs(pg)['a']-60)<1e-3)
            pg.click('#rkRight'); pg.wait_for_function('!__cr.rack.RK.raf')
            side=pg.locator('#rkRotor .pk[data-w="1"] .pkc').first; side.click(); pg.wait_for_timeout(80); pg.wait_for_function('!__cr.rack.RK.raf'); s=rs(pg)
            ok('tap a cover on a side wing turns it to the front (does not open)',s['front']==1 and pg.is_visible('#rack') and not pg.is_visible('#reader'),json.dumps(s['front']))
            tgt=pg.locator('#rkRotor .pk.front .pkc').nth(3); tid=tgt.get_attribute('data-rk'); tgt.click(); pg.wait_for_timeout(120); pull=pg.evaluate("!!document.querySelector('.rkpull')")
            pg.screenshot(path=f'{SH}/{ENG}-v36-rack-pullout-{lab}.png'); pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(500)
            ok('tap a front cover: pulls out (animated) and opens in the reader',pull and pg.evaluate('__cr.R.comic.id')==tid)
            pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
            ok('closing the reader returns to the rack',pg.is_visible('#rack') and rs(pg)['title']=='On the racks · Jan 1984')
            pg.click('#rkNext'); ok('next month arrow moves the window and keeps the rack full',rs(pg)['title']=='On the racks · Feb 1984' and rs(pg)['filled']==48)
            pg.click('#rkBack'); pg.wait_for_timeout(200)
            pg.click('#tlRack'); pg.wait_for_timeout(300); ok('rack button in the Timeline bar opens the rack',pg.is_visible('#rack')); pg.click('#rkBack')
            # ---- volume-aware estimates (David's Heroes Reborn Fantastic Four)
            e=pg.evaluate("""(()=>{const L=__cr.online.lookupDate, of=c=>__cr.dates.of(c);
              return {v2file:of({title:'Fantastic Four 003',series:'Fantastic Four',fileName:'Fantastic_Four_v2_003.pdf'}),
                v2series:of({title:'Fantastic Four 003',series:'Fantastic Four Vol. 2',fileName:'ff3.pdf'}),
                reborn:of({title:'Fantastic Four 003',series:'Fantastic Four (Heroes Reborn)',fileName:'Fantastic Four - Heroes Reborn 03.pdf'}),
                year96:L('Fantastic Four (1996)',3), year62:L('Fantastic Four',3,'(1962)'), vol1:L('Fantastic Four Vol. 1',3), plain:L('Fantastic Four',3)}})()""")
            ok('Vol 2 / v2 in the series or file name: no 1960s estimate (Unknown)',e['v2file'] is None and e['v2series'] is None,json.dumps(e))
            ok('"Heroes Reborn" / a (1996) start year: no estimate',e['reborn'] is None and e['year96'] is None,json.dumps(e))
            ok('plain / Vol 1 / matching year still get the ≈ estimate',e['plain']=={'y':1962,'m':1,'src':'lookup'} and e['vol1']==e['plain'] and e['year62']==e['plain'],json.dumps(e))
            # ---- online lookup (mocked wiki): Settings button
            pg.evaluate("__cr.dates.set(__cr.comics.find(c=>c.title==='Iron Tide 04'),null)")   # Iron Tide 04 becomes unknown: eligible, but not on the mock wiki
            pg.click('#tabs [data-tab=home]'); pg.click('#settingsBtn'); pg.wait_for_selector('#sLookup'); ok('Settings: "Look Up Release Dates…" button with the count',pg.is_visible('#sLookup') and '3 issues' in pg.text_content('.sgrp:has(#sLookup)'),pg.text_content('.sgrp:has(#sLookup)'))
            CALLS.clear(); pg.click('#sLookup'); pg.wait_for_function("document.querySelector('#lkDone')&&document.querySelector('#lkDone').textContent==='Done'",timeout=30000)
            rows=pg.eval_on_selector_all('#lkRes .lkr','e=>e.map(x=>x.textContent)')
            pg.screenshot(path=f'{SH}/{ENG}-v26-lookup-{lab}.png')
            ok('lookup shows results per issue',any('Paper Moons 01' in r and 'Jul 1979' in r and 'Marvel Database' in r for r in rows) and any('Iron Tide 04' in r and 'Not found' in r for r in rows),json.dumps(rows))
            ok('several volumes match and nothing hints which: not saved, asks to pick',any('Paper Moons 02' in r and 'pick' in r for r in rows) and pg.evaluate("__cr.dates.of(__cr.comics.find(c=>c.title==='Paper Moons 02'))") is None,json.dumps(rows))
            ok('only unknown/≈ issues were looked up (files with dates and your dates are skipped)',not any('Comet' in t or 'Deep' in t for _,t in CALLS) and not any('Iron Tide 01' in r for r in rows),json.dumps(CALLS[:3]))
            pg.click('#lkDone'); pg.wait_for_timeout(200)
            d=pg.evaluate("__cr.dates.of(__cr.comics.find(c=>c.title==='Paper Moons 01'))"); ok('saved with source "online"',d['y']==1979 and d['m']==7 and d['src']=='online',json.dumps(d))
            pg.reload(); pg.wait_for_selector('html[data-ready]'); ok('online date persisted (IndexedDB)',pg.evaluate("__cr.dates.of(__cr.comics.find(c=>c.title==='Paper Moons 01'))")['src']=='online')
            # per-issue Look Up: pick a volume
            pg.click('#tabs [data-tab=library]'); pg.locator('.lc[data-title="Paper Moons 02"]').click(button='right'); pg.click('#aDate'); pg.click('#dLook'); pg.wait_for_selector('#dLookRes button[data-i]')
            ch=pg.eval_on_selector_all('#dLookRes .lkr','e=>e.map(x=>x.textContent)'); pg.screenshot(path=f'{SH}/{ENG}-v26-lookup-sheet-{lab}.png')
            ok('Release Date sheet: Look Up Online lists the matching volumes',len(ch)==3 and 'Paper Moons Vol 1 2' in ch[1] and 'Paper Moons Vol 2 2' in ch[2],json.dumps(ch))
            pg.click('#dLookRes button[data-i="1"]'); pg.wait_for_timeout(300); d=pg.evaluate("__cr.dates.of(__cr.comics.find(c=>c.title==='Paper Moons 02'))")
            ok('picking a volume saves it',d=={'y':2004,'m':3,'src':'online','wiki':'Marvel Database','title':'Paper Moons Vol 2 2','url':'https://marvel.fandom.com/wiki/Paper_Moons_Vol_2_2','at':d.get('at')},json.dumps(d))
            pg.click('.mwrap [data-r="cancel"]'); pg.wait_for_timeout(200)
            # never overrides a manual date
            pg.evaluate("__cr.dates.set(__cr.comics.find(c=>c.title==='Paper Moons 01'),{y:1980,m:2})")
            pg.locator('.lc[data-title="Paper Moons 01"]').click(button='right'); pg.click('#aDate'); pg.click('#dLook'); pg.wait_for_selector('#dLookRes .lkr'); pg.wait_for_timeout(200)
            ok('a date you set by hand is kept',('Your date is kept' in pg.text_content('#dLookRes')) and pg.evaluate("__cr.dates.of(__cr.comics.find(c=>c.title==='Paper Moons 01'))")=={'y':1980,'m':2,'src':'manual'},pg.text_content('#dLookRes'))
            pg.click('.mwrap [data-r="cancel"]')
        elif rm=='reduce':
            drag(pg,-260); pg.wait_for_timeout(30); s=rs(pg)
            ok(f'{lab}: reduced motion: no momentum, lands on a wing',not s['raf'] and abs(s['a']/60-round(s['a']/60))<1e-6,json.dumps(s['a']))
            pg.evaluate("__cr.rack.RK.a=0"); pg.click('#rkLeft'); pg.click('#rkRight'); pg.locator('#rkRotor .pk.front .pkc').first.click(); pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(300)
            ok(f'{lab}: reduced motion: tap opens without the pull-out animation',not pg.evaluate("!!document.querySelector('.rkpull')"))
        ctx.close()
    # ---- live check: the real Fandom API from a browser origin (CORS), skipped when offline
    ctx=b.new_context(); pg=ctx.new_page(); pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    live=pg.evaluate("__cr.online.onlineDate('Fantastic Four',3,['Heroes Reborn']).then(r=>r.found?{y:r.found.y,m:r.found.m,t:r.found.title}:r).catch(e=>({error:String(e)}))")
    if live.get('error') or live.get('none'): print('SKIP [live] Fandom API not reachable:',live)
    else: ok('LIVE: real Marvel Database lookup from the page: Heroes Reborn Fantastic Four #3 -> Vol 2, Jan 1997',live=={'y':1997,'m':1,'t':'Fantastic Four Vol 2 3'},json.dumps(live))
    ctx.close(); b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
