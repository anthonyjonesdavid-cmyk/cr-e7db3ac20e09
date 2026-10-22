"""cr-v42 suite: creator credits (writer + artist on the issue info sheet and the reader's Issue Info, tappable) and the creator page.
python3 test/e2e_v42.py [webkit]  (server on 127.0.0.1:8823). Fixtures: original abstract comics, mapped in memory onto real library ids
from test/v42_ids.json so the built-in credits/dates apply. Standalone insets via --sat/--sab."""
import sys, os, json, glob, subprocess
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); D=os.path.join(T,'dates'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(os.path.join(D,'Deep_Signal_02.pdf')): subprocess.run([sys.executable,os.path.join(HERE,'gen_dates.py')],check=True)
FILES=sorted(glob.glob(os.path.join(T,'*.pdf')))+sorted(glob.glob(os.path.join(D,'*.pdf')))
IDS=json.load(open(os.path.join(HERE,'v42_ids.json')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
MAP="""ids=>{ const C=__cr.comics.slice().sort((a,b)=>a.title.localeCompare(b.title)); ids.forEach(([d,s,f],i)=>{ const c=C[i]; c.driveId=d; c.series=s; c.title=f.replace(/\\.pdf$/,''); delete c.dateManual; c.metaDate=null; c.onlineDate=null; });
  __cr.dates.render(); return C.slice(0,ids.length).map(c=>c.id); }"""
PAGE="""(()=>{ const el=document.querySelector('#creator'), r=el.getBoundingClientRect(), hb=el.querySelector('.rkbar').getBoundingClientRect(), cb=document.querySelector('#crClose').getBoundingClientRect();
  const groups=[...el.querySelectorAll('.crg')].map(g=>({s:g.querySelector('h3').firstChild.textContent,ids:[...g.querySelectorAll('.crc')].map(b=>b.dataset.id)}));
  return {vis:!el.classList.contains('hidden'),full:r.width===innerWidth&&r.height===innerHeight,bg:getComputedStyle(el).backgroundColor,name:document.querySelector('#crName').textContent,sub:document.querySelector('#crSub').textContent,groups,barTop:hb.top,closeH:cb.height,closeW:cb.width,closeTop:cb.top}; })()"""
EXP="""name=>{ const key=__cr.credits.norm(name).toLowerCase(), by={}; const t=c=>{ const d=__cr.dates.of(c); return d?d.y*12+((d.m||6)-1):1e9; };
  for(const c of __cr.comics){ const k=__cr.credits.of(c); if(!k||![...k.writer,...k.artist].some(n=>n.toLowerCase()===key)) continue; (by[c.series||'Other']=by[c.series||'Other']||[]).push(c); }
  return Object.entries(by).map(([s,L])=>({s,L:L.sort((a,b)=>t(a)-t(b)).map(c=>({id:c.id,t:t(c)}))})).sort((a,b)=>a.L[0].t-b.L[0].t).map(g=>({s:g.s,ids:g.L.map(x=>x.id)})); }"""
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    SZ=[(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]
    if os.environ.get('ONLY'): SZ=[z for z in SZ if z[2]==os.environ['ONLY']]
    for (w,h,lab,dpr,sat,sab) in SZ or [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        ok(f'{lab}: app launches on Home',pg.evaluate("!document.querySelector('#home').classList.contains('hidden')"))
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        mapped=pg.evaluate(MAP,IDS)
        ho=pg.evaluate("""(()=>{ const L=__cr.CF.items, t=c=>{ const d=__cr.dates.of(c); return d?d.y*12+((d.m||6)-1):Infinity; }, v=L.map(t);
          const fin=v.filter(x=>x!==Infinity), und=v.indexOf(Infinity); return {n:L.length,all:__cr.comics.length,sorted:fin.every((x,i)=>!i||fin[i-1]<=x),undEnd:und<0||v.slice(und).every(x=>x===Infinity),pos:__cr.CF.pos,start:__cr.credits.heroStart(L)}; })()""")
        ok(f'{lab}: Home carousel holds every issue in release order, oldest first, undated at the end; opens on the oldest when nothing was read',ho['n']==ho['all'] and ho['sorted'] and ho['undEnd'] and ho['pos']==0 and ho['start']==0,json.dumps(ho))
        wrap=pg.evaluate("""(async()=>{ const n=__cr.CF.items.length; __cr.CF.to(-1,1); await new Promise(r=>setTimeout(r,400)); const c=document.querySelector('#cf .cf-item[data-slot="0"]'); return {n,id:__cr.CF.items[((Math.round(__cr.CF.pos)%n)+n)%n].id,last:__cr.CF.items[n-1].id}; })()""")
        ok(f'{lab}: circular: one step back from the oldest is the newest / last',wrap['id']==wrap['last'],json.dumps(wrap))
        rr=pg.evaluate("""(async()=>{ const L=__cr.CF.items, c=L[Math.floor(L.length/2)]; c.lastRead=Date.now(); c.progress=.4; c.page=3; __cr.dates.render(); await new Promise(r=>setTimeout(r,200)); const M=__cr.CF.items; return {want:c.id,at:M[((Math.round(__cr.CF.pos)%M.length)+M.length)%M.length].id,same:M.map(x=>x.id).join()===L.map(x=>x.id).join()}; })()""")
        ok(f'{lab}: after reading, Home opens centred on the most recently read issue (order unchanged)',rr['want']==rr['at'],json.dumps(rr))
        ok(f'{lab}: Home has no credits UI',pg.evaluate("!document.querySelector('#home .crn,#home .credits')"))
        st=pg.evaluate("""(()=>{ const k=__cr.credits; return {jim:k.norm('James Lee'),jr:k.norm('John Romita, Jr.'),erik:k.norm('Erik J. Larsen'),names:k.data.n.length,ids:Object.keys(k.data.d).length,dup:k.data.n.length-new Set(k.data.n.map(n=>k.norm(n).toLowerCase())).size} })()""")
        ok(f'{lab}: name variants normalised (James Lee -> Jim Lee, John Romita, Jr. -> John Romita Jr., Erik J. Larsen -> Erik Larsen); no duplicate creators in the data',st['jim']=='Jim Lee' and st['jr']=='John Romita Jr.' and st['erik']=='Erik Larsen' and st['dup']==0 and st['ids']>700,json.dumps(st))
        # ---- issue info sheet (long-press menu) ----
        pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(300)
        cid=mapped[0]; pg.evaluate("id=>{ __cr.credits.sheet(id); return 1 }",cid)
        if not pg.query_selector('.mwrap'):
            card=pg.locator(f'[data-id="{cid}"]').first; card.scroll_into_view_if_needed(); bb=card.bounding_box()
            pg.mouse.move(bb['x']+bb['width']/2,bb['y']+bb['height']/2); pg.mouse.down(); pg.wait_for_timeout(700); pg.mouse.up()
        pg.wait_for_selector('.mwrap .credits',timeout=5000)
        info=pg.evaluate("""(()=>{ const rows=[...document.querySelectorAll('.mwrap .crrow')].map(r=>[r.querySelector('.crl').textContent,[...r.querySelectorAll('.crn')].map(b=>b.textContent)]);
          const sz=[...document.querySelectorAll('.mwrap .crn')].map(b=>{const r=b.getBoundingClientRect(); return [r.width,r.height]}); return {rows,sz}; })()""")
        exp=pg.evaluate("id=>__cr.credits.of(__cr.comics.find(c=>c.id===id))",cid)
        ok(f'{lab}: issue info sheet shows Writer and Artist as tappable names (>=40px)',info['rows']==[['Writer',exp['writer']],['Artist',exp['artist']]] and all(s[0]>=40 and s[1]>=40 for s in info['sz']),json.dumps([info,exp]))
        if lab in ('ipad-portrait','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v42-issue-info-{lab}.png')
        nm='Jim Lee' if 'Jim Lee' in exp['writer']+exp['artist'] else (exp['artist'] or exp['writer'])[0]
        bb=pg.locator(f'.mwrap .crn[data-creator="{nm}"]').first.bounding_box(); pg.touchscreen.tap(bb['x']+bb['width']/2,bb['y']+bb['height']/2); pg.wait_for_timeout(300)
        s=pg.evaluate(PAGE); e=pg.evaluate(EXP,nm)
        ok(f'{lab}: tapping a name opens the dark full-screen creator page; info sheet closed',s['vis'] and s['full'] and s['bg']=='rgb(0, 0, 0)' and s['name']==nm and not pg.query_selector('.mwrap'),json.dumps(s))
        ok(f'{lab}: creator page lists every issue by the creator, grouped by series, oldest first',[g['ids'] for g in s['groups']]==[g['ids'] for g in e] and [g['s'] for g in s['groups']]==[g['s'] for g in e] and len(s['groups'])>=2,json.dumps([s['groups'],e]))
        ok(f'{lab}: creator bar below the status bar, back button >=40px',s['closeTop']>=sat and s['closeH']>=40 and s['closeW']>=40,json.dumps(s))
        if lab in ('ipad-portrait','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v42-creator-{lab}.png')
        same=pg.evaluate("()=>{ __cr.credits.open('James Lee'); return document.querySelector('#crName').textContent }")
        ok(f'{lab}: "James Lee" opens the same Jim Lee page',same=='Jim Lee')
        pg.evaluate(f"__cr.credits.open({json.dumps(nm)})")
        first=s['groups'][0]['ids'][0]; cb=pg.locator(f'#crBody .crc[data-id="{first}"]').bounding_box(); pg.touchscreen.tap(cb['x']+cb['width']/2,cb['y']+cb['height']/3)
        pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(400)
        ok(f'{lab}: tapping a cover opens that issue',pg.evaluate('__cr.R.comic.id')==first and pg.evaluate("document.querySelector('#creator').classList.contains('hidden')"))
        # ---- reader Issue Info ----
        pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(200); pg.click('#rMore'); pg.wait_for_timeout(200); pg.click('#rmInfo'); pg.wait_for_selector('.mwrap .rinfo')
        ri=pg.evaluate("[...document.querySelectorAll('.mwrap .crn')].map(b=>b.textContent)"); ex2=pg.evaluate("__cr.credits.of(__cr.R.comic)")
        ok(f"{lab}: reader's More > Issue Info shows the credits as tappable names",ri==ex2['writer']+ex2['artist'],json.dumps([ri,ex2]))
        if lab=='iphone-390': pg.screenshot(path=f'{SH}/{ENG}-v42-reader-info-{lab}.png')
        bb=pg.locator('.mwrap .crn').last.bounding_box(); pg.touchscreen.tap(bb['x']+bb['width']/2,bb['y']+bb['height']/2); pg.wait_for_timeout(300)
        s2=pg.evaluate(PAGE); top=pg.evaluate("document.elementFromPoint(innerWidth/2,innerHeight/2).closest('#creator')!==null")
        ok(f'{lab}: from the reader, a name opens the creator page above the reader',s2['vis'] and top and s2['name']==ri[-1],json.dumps(s2))
        pg.click('#crClose'); pg.wait_for_timeout(200)
        ok(f'{lab}: back closes the creator page (reader underneath)',pg.evaluate("document.querySelector('#creator').classList.contains('hidden') && !document.querySelector('#reader').classList.contains('hidden')"))
        nc=pg.evaluate("(()=>{ const c=__cr.comics.find(c=>!c.driveId&&!__cr.credits.of(c)); return c?__cr.credits.of(c):'none' })()")
        ok(f'{lab}: issues without credits show none (no empty rows)',nc is None,nc)
        ctx.close()
    b.close()
print(f'\n{sum(res)}/{len(res)} passed'+(f'; page errors: {errors[:3]}' if errors else '')); sys.exit(0 if all(res) and not errors else 1)
