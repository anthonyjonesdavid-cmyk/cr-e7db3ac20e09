"""End-to-end test: python3 test/e2e.py [chromium|webkit] [--big]  (server on 127.0.0.1:8823)"""
import sys, os, json, time
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'
ENG=sys.argv[1] if len(sys.argv)>1 else 'chromium'
BIG='--big' in sys.argv
T=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','testpdfs'))
SH=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','shots'))
os.makedirs(SH,exist_ok=True)
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,extra,flush=True)
GEST='''async ({x,y,pts,hold,noup})=>{
  const st=document.querySelector('#stage');
  const mk=(type,id,cx,cy)=>new PointerEvent(type,{bubbles:true,cancelable:true,composed:true,pointerId:id,pointerType:'touch',isPrimary:id===11,clientX:cx,clientY:cy,button:0,buttons:type==='pointerup'?0:1,width:20,height:20,pressure:type==='pointerup'?0:.5});
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const ps=[]; let watching=true;
  (function w(){ const f=window.__cr.flip; if(f) ps.push(+f.p.toFixed(3)); if(watching) requestAnimationFrame(w); })();
  const t0=performance.now();
  st.dispatchEvent(mk('pointerdown',11,x,y)); let cx=x,cy=y;
  for(const [dx,dy,dt] of pts){ await sleep(dt); cx=x+dx; cy=y+dy; st.dispatchEvent(mk('pointermove',11,cx,cy)); }
  if(hold) await sleep(hold);
  if(noup){ await sleep(60); watching=false; return {p: window.__cr.flip? window.__cr.flip.p : -1}; }
  st.dispatchEvent(mk('pointerup',11,cx,cy)); const dur=performance.now()-t0;
  await sleep(950); watching=false;
  const R=window.__cr.R; const v=R.views[R.vi];
  return {dur:Math.round(dur),frames:ps.length,maxP:Math.max(0,...ps),distinct:new Set(ps.filter(p=>p>0.05&&p<0.99)).size,vi:R.vi,first:v.filter(x=>x!=null)[0]};
}'''
UP='''([x,y])=>{ const st=document.querySelector('#stage'); st.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:11,pointerType:'touch',isPrimary:true,clientX:x,clientY:y})); }'''
TAP='''async ({x,y,n})=>{ const st=document.querySelector('#stage'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  for(let k=0;k<n;k++){ const o={bubbles:true,cancelable:true,pointerId:20+k,pointerType:'touch',isPrimary:true,clientX:x,clientY:y,button:0};
    st.dispatchEvent(new PointerEvent('pointerdown',{...o,buttons:1})); await sleep(40); st.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0})); await sleep(90); } await sleep(450); }'''
PINCH='''async ({cx,cy,d0,d1})=>{ const st=document.querySelector('#stage'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const ev=(t,id,x,y)=>st.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:id,pointerType:'touch',isPrimary:id===31,clientX:x,clientY:y,buttons:t==='pointerup'?0:1}));
  ev('pointerdown',31,cx-d0/2,cy); await sleep(10); ev('pointerdown',32,cx+d0/2,cy);
  for(let i=1;i<=10;i++){ const d=d0+(d1-d0)*i/10; await sleep(16); ev('pointermove',31,cx-d/2,cy); ev('pointermove',32,cx+d/2,cy); }
  ev('pointerup',31,cx-d1/2,cy); ev('pointerup',32,cx+d1/2,cy); await sleep(400); return window.__cr.Z.s; }'''
def state(pg): return pg.evaluate('(()=>{const R=__cr.R;const v=R.views[R.vi]||[];return {vi:R.vi,first:v.filter(x=>x!=null)[0],len:v.length,spread:R.spread,rtl:R.rtl,n:R.n,ui:document.querySelector("#reader").classList.contains("ui"),z:__cr.Z.s,cache:__cr.cache()}})()')
def shot(pg,name): pg.screenshot(path=f'{SH}/{ENG}-{name}.png')
def wait_render(pg,t=15000): pg.wait_for_function('document.querySelectorAll(".view .pg.loading").length===0 && document.querySelectorAll(".view .pg canvas").length>0',timeout=t)
def open_comic(pg,title):
    pg.locator('.card',has_text=title).locator('.cv').click(); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg); pg.wait_for_timeout(300)
def back(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)')
def geo(pg):
    b=pg.locator('#stage').bounding_box(); return b['x'],b['y'],b['width'],b['height']
def flicks(pg,tag):
    x0,y0,W,H=geo(pg); x=x0+W*0.6; y=y0+H*0.45
    g=lambda pts,hold=0: pg.evaluate(GEST,{'x':x,'y':y,'pts':pts,'hold':hold,'noup':False})
    s0=state(pg)['vi']
    r=g([[-5,0,15],[-10,0,15],[-15,0,15],[-20,0,15]]); ok(f'{tag} flick 20px/60ms forward turns page (animated fold)',r['vi']==s0+1 and r['distinct']>=5,json.dumps(r))
    r=g([[5,0,15],[10,0,15],[15,0,15],[20,0,15]]); ok(f'{tag} flick 20px/60ms backward turns page',r['vi']==s0,json.dumps(r))
    r=g([[-15,0,15],[-22,0,20]]); ok(f'{tag} 2-event quick flick turns',r['vi']==s0+1,json.dumps(r))
    g([[6,0,15],[14,0,15],[22,0,15]]); pg.wait_for_timeout(100)
    r=g([[-i*3,0,60] for i in range(1,11)],hold=160); ok(f'{tag} slow short drag (30px) + pause cancels',r['vi']==s0,json.dumps(r))
    pw=pg.evaluate('(()=>{const v=__cr.R.views[__cr.R.vi];const g=document.querySelectorAll(".view .pg");let w=0;g.forEach(e=>w+=e.offsetWidth);return w})()')
    dist=pw*0.15; r=g([[-dist*i/16,0,50] for i in range(1,17)],hold=150); ok(f'{tag} slow drag past 13% commits',r['vi']==s0+1,json.dumps(r))
    r=g([[1,-8,16],[2,-20,16],[3,-35,16],[4,-55,16],[5,-80,16]]); ok(f'{tag} vertical pan does not turn',r['vi']==s0+1 and r['frames']==0,json.dumps(r))
    r=g([[-3,-10,16],[-6,-24,16],[-9,-40,16]]); ok(f'{tag} diagonal mostly-vertical does not turn',r['vi']==s0+1 and r['frames']==0,json.dumps(r))
    g([[6,0,15],[14,0,15],[22,0,15]])
    return s0

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    ctx=b.new_context(viewport={'width':820,'height':1180},has_touch=True,device_scale_factor=2)
    pg=ctx.new_page()
    pg.on('pageerror',lambda e:errors.append('pageerror: '+str(e)))
    pg.on('console',lambda m: errors.append(f'console.{m.type}: {m.text}') if m.type=='error' else None)
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    ok('robots meta present',pg.evaluate("document.querySelector('meta[name=robots]').content")=='noindex, nofollow')
    shot(pg,'01-empty-shelf')
    files=[f'{T}/Captain_Comet_01.pdf',f'{T}/Captain_Comet_02.pdf',f'{T}/Night_Owl_Tales.pdf',f'{T}/Robo_Pals_Manga.pdf']+([f'{T}/Mega_Omnibus_Big.pdf'] if BIG else [])
    t0=time.time(); pg.set_input_files('#fileIn',files)
    pg.wait_for_function(f'document.querySelectorAll(".card").length=={len(files)} && !document.querySelector(".toast .tb")',timeout=(400000 if BIG else 60000))
    ok(f'import {len(files)} PDFs',True,f'{time.time()-t0:.1f}s'); pg.wait_for_timeout(500)
    ok('shelf shows covers + page counts',pg.locator('.card img').count()==len(files) and 'pages' in pg.inner_text('.card .s'))
    # assign series via edit modal
    for t in ['Captain Comet 01','Captain Comet 02']:
        pg.locator('.card',has_text=t).locator('.more').click(); pg.fill('#eSeries','Captain Comet'); pg.click('#eSave'); pg.wait_for_timeout(150)
    pg.locator('.card',has_text='Night Owl Tales').locator('.more').click(); pg.fill('#eTitle','Night Owl Tales #1'); pg.click('#eSave'); pg.wait_for_timeout(150)
    ok('title editable',pg.locator('.card',has_text='Night Owl Tales #1').count()==1)

    # ---- reader, portrait single page ----
    open_comic(pg,'Captain Comet 01')
    s=state(pg); ok('portrait = single page',s['len']==1 and not s['spread'],json.dumps(s))
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(300); shot(pg,'03-reader-portrait-cover')
    flicks(pg,'portrait')
    pg.evaluate('__cr.jumpTo(4)'); wait_render(pg)
    x0,y0,W,H=geo(pg)
    r=pg.evaluate(GEST,{'x':x0+W*0.8,'y':y0+H*0.5,'pts':[[-W*0.05*i,0,30] for i in range(1,9)],'hold':0,'noup':True}); pg.wait_for_timeout(120)
    shot(pg,'04-mid-page-turn-portrait'); ok('mid page-turn in progress',0.2<r['p']<0.9,json.dumps(r))
    pg.evaluate(UP,[x0+W*0.4,y0+H*0.5]); pg.wait_for_timeout(900)
    ok('page turn committed after drag',state(pg)['first']==5)
    # toolbar via center tap
    pg.evaluate(TAP,{'x':x0+W/2,'y':y0+H/2,'n':1}); s=state(pg); ok('center tap shows toolbars',s['ui'],json.dumps(s)); shot(pg,'05-toolbar-shown')
    pg.evaluate(TAP,{'x':x0+W/2,'y':y0+H/2,'n':1}); ok('center tap hides toolbars',not state(pg)['ui'])
    pg.evaluate(TAP,{'x':x0+W*0.93,'y':y0+H/2,'n':1}); pg.wait_for_timeout(500); ok('right-edge tap turns forward',state(pg)['first']==6)
    pg.evaluate(TAP,{'x':x0+W*0.07,'y':y0+H/2,'n':1}); pg.wait_for_timeout(500); ok('left-edge tap turns back',state(pg)['first']==5)
    # scrubber with thumbnail bubble
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(250)
    pg.evaluate("(()=>{const s=document.querySelector('#scrub'); s.value=18; s.dispatchEvent(new Event('input',{bubbles:true}));})()")
    pg.wait_for_function("document.querySelector('#bubble img').complete && document.querySelector('#bubble img').naturalWidth>0",timeout=10000); pg.wait_for_timeout(150)
    shot(pg,'06-scrubber-thumb')
    pg.evaluate("document.querySelector('#scrub').dispatchEvent(new Event('change',{bubbles:true}))"); wait_render(pg)
    ok('scrubber jumps to page 18',state(pg)['first']==17)
    pg.click('#rGrid'); pg.wait_for_function("document.querySelectorAll('#pgrid img').length>8",timeout=15000); pg.wait_for_timeout(300); shot(pg,'07-pages-grid')
    pg.locator('#pgrid button[data-p="9"]').click(); wait_render(pg); ok('page grid jump to 10',state(pg)['first']==9)
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250)
    # zoom: double tap, re-render sharp, no turns while zoomed, pinch
    pg.evaluate(TAP,{'x':x0+W*0.5,'y':y0+H*0.35,'n':2}); pg.wait_for_timeout(900)
    s=state(pg); hi=pg.evaluate("Math.max(...[...document.querySelectorAll('.view .pg canvas')].map(c=>c.width))")
    ok('double-tap zooms 2.5x',abs(s['z']-2.5)<0.01,json.dumps(s)); ok('zoomed page re-rendered at higher resolution',hi>1600,f'canvas width {hi}')
    shot(pg,'08-zoomed')
    r=pg.evaluate(GEST,{'x':x0+W*0.6,'y':y0+H*0.5,'pts':[[-5,0,15],[-10,0,15],[-15,0,15],[-20,0,15]],'hold':0,'noup':False})
    ok('no page turn while zoomed (pans instead)',r['first']==9 and r['frames']==0,json.dumps(r))
    pg.evaluate(TAP,{'x':x0+W*0.5,'y':y0+H*0.5,'n':2}); ok('double-tap resets zoom',state(pg)['z']==1)
    z=pg.evaluate(PINCH,{'cx':x0+W/2,'cy':y0+H/2,'d0':100,'d1':260}); ok('pinch zoom',z>2,f'z={z:.2f}')
    pg.evaluate(TAP,{'x':x0+W*0.5,'y':y0+H*0.5,'n':2})
    # resume after reload
    pg.evaluate('__cr.jumpTo(12)'); wait_render(pg); pg.wait_for_timeout(500)
    pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg)
    s=state(pg); ok('resumes same page after reload (in reader)',s['first']==12,json.dumps(s))
    back(pg); pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(400)
    ok('continue-reading card shows page 13',pg.locator('.cont').count()==1 and 'Page 13 of 32' in pg.inner_text('.cont'))
    shot(pg,'02-shelf-portrait')
    pg.click('#groupBtn'); pg.wait_for_timeout(200); ok('series grouping',pg.locator('.sect h2',has_text='Captain Comet').count()==1); shot(pg,'09-shelf-series'); pg.click('#groupBtn')
    pg.fill('#q','owl'); pg.wait_for_timeout(100); ok('search filters',pg.locator('.card').count()==1); pg.fill('#q','')
    pg.locator('.cont .btn').click(); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg); ok('continue reading opens at page 13',state(pg)['first']==12)

    # ---- landscape spread ----
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(500); wait_render(pg)
    s=state(pg); ok('landscape = two-page spread',s['spread'] and s['len']==2,json.dumps(s))
    pg.evaluate('__cr.jumpTo(0)'); wait_render(pg); pg.wait_for_timeout(200)
    vis=pg.evaluate("[...document.querySelectorAll('.view .pg')].map(e=>({blank:e.classList.contains('blank'),x:e.offsetLeft}))")
    ok('cover alone on the right',vis[0]['blank'] and not vis[1]['blank'],json.dumps(vis)); shot(pg,'10-landscape-cover')
    flicks(pg,'landscape')
    pg.evaluate('__cr.jumpTo(3)'); wait_render(pg); pg.wait_for_timeout(200); shot(pg,'11-landscape-spread')
    ok('spread shows pages 4-5',pg.text_content('#pgText').startswith('4–5'),pg.text_content('#pgText'))
    x0,y0,W,H=geo(pg)
    r=pg.evaluate(GEST,{'x':x0+W*0.85,'y':y0+H*0.5,'pts':[[-W*0.06*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(120)
    shot(pg,'12-landscape-mid-turn'); ok('spread mid-turn',0.2<r['p']<0.95,json.dumps(r)); pg.evaluate(UP,[x0+W*0.4,y0+H*0.5]); pg.wait_for_timeout(900)
    ok('spread turn lands on 6-7',pg.text_content('#pgText').startswith('6–7'),pg.text_content('#pgText'))
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(250); shot(pg,'13-landscape-toolbar')
    pg.click('#rSpread'); pg.wait_for_timeout(300); wait_render(pg); s=state(pg); ok('toggle single page in landscape',s['len']==1,json.dumps(s))
    pg.click('#rSpread'); pg.wait_for_timeout(300); wait_render(pg); ok('toggle back to spread',state(pg)['len']==2)
    back(pg)

    # ---- RTL ----
    open_comic(pg,'Robo Pals')
    pg.evaluate('__cr.toggleUI(true)'); pg.click('#rRtl'); pg.wait_for_timeout(300); pg.evaluate('__cr.jumpTo(5)'); wait_render(pg)
    vis=pg.evaluate("[...document.querySelectorAll('.view .pg')].map(e=>+e.dataset.p)")
    ok('RTL spread: lower page on the right',vis==[6,5],json.dumps(vis))
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250)
    x0,y0,W,H=geo(pg); x=x0+W*0.4; y=y0+H*0.45
    r=pg.evaluate(GEST,{'x':x,'y':y,'pts':[[5,0,15],[10,0,15],[15,0,15],[20,0,15]],'hold':0,'noup':False}); ok('RTL: flick right goes forward',r['first']==7,json.dumps(r))
    r=pg.evaluate(GEST,{'x':x,'y':y,'pts':[[-5,0,15],[-10,0,15],[-15,0,15],[-20,0,15]],'hold':0,'noup':False}); ok('RTL: flick left goes back',r['first']==5,json.dumps(r))
    r=pg.evaluate(GEST,{'x':x0+W*0.2,'y':y,'pts':[[W*0.06*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(120); shot(pg,'14-rtl-mid-turn'); pg.evaluate(UP,[x0+W*0.6,y]); pg.wait_for_timeout(900)
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(500); wait_render(pg)
    r=pg.evaluate(GEST,{'x':x0+300,'y':500,'pts':[[5,0,15],[10,0,15],[15,0,15],[20,0,15]],'hold':0,'noup':False}); s=state(pg); ok('RTL single page: flick right goes forward',s['first']==8 and s['rtl'],json.dumps(r))
    r=pg.evaluate(GEST,{'x':200,'y':500,'pts':[[W*0.05*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(120); shot(pg,'15-rtl-portrait-mid-turn'); pg.evaluate(UP,[500,500]); pg.wait_for_timeout(900)
    back(pg); ok('RTL saved per comic',pg.locator('.card',has_text='Robo Pals').locator('.tag.rtl').count()==1)

    if BIG:
        t0=time.time(); open_comic(pg,'Mega Omnibus'); ok('big PDF opens',True,f'{time.time()-t0:.1f}s, {state(pg)["n"]} pages')
        t0=time.time(); pg.evaluate('__cr.jumpTo(150)'); wait_render(pg,60000); ok('big PDF random-access page 151',state(pg)['first']==150,f'{time.time()-t0:.2f}s')
        for i in range(12): pg.evaluate('__cr.go(-1,200)'); pg.wait_for_timeout(260)
        wait_render(pg,60000); c=state(pg)['cache']; ok('LRU bounded after many turns',c['px']<=c['budget'],json.dumps(c)); pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(250); shot(pg,'16-big-pdf'); back(pg)

    # ---- phone ----
    pg.set_viewport_size({'width':390,'height':844}); pg.wait_for_timeout(300); shot(pg,'17-phone-shelf')
    open_comic(pg,'Night Owl'); pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(250); shot(pg,'18-phone-reader')
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250); flicks(pg,'phone')
    x0,y0,W,H=geo(pg); r=pg.evaluate(GEST,{'x':x0+W*0.8,'y':y0+H*0.5,'pts':[[-W*0.07*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(120); shot(pg,'19-phone-mid-turn'); pg.evaluate(UP,[x0+W*0.3,y0+H*0.5]); pg.wait_for_timeout(900)
    if ENG=='chromium':
        cdp=ctx.new_cdp_session(pg); x=x0+W*0.6; y=y0+H*0.45
        def touch(tp,px,py): cdp.send('Input.dispatchTouchEvent',{'type':tp,'touchPoints':[] if tp=='touchEnd' else [{'x':px,'y':py,'id':1}]})
        for sign,name in [(-1,'forward'),(1,'back')]:
            before=state(pg)['first']; touch('touchStart',x,y)
            for i in range(1,5): time.sleep(0.015); touch('touchMove',x+sign*5*i,y)
            touch('touchEnd',x+sign*20,y); pg.wait_for_timeout(900)
            ok(f'REAL CDP touch flick 20px {name}',state(pg)['first']==before-sign,f"{before}->{state(pg)['first']}")
    back(pg)
    # ---- delete ----
    pg.set_viewport_size({'width':820,'height':1180}); n0=pg.locator('.card').count()
    pg.locator('.card',has_text='Captain Comet 02').locator('.more').click(); pg.click('#eDelete'); pg.wait_for_selector('#confirmOk'); shot(pg,'20-delete-confirm'); pg.click('#confirmOk'); pg.wait_for_timeout(400)
    ok('delete with confirm',pg.locator('.card').count()==n0-1)
    pg.click('#settingsBtn'); pg.wait_for_selector('.stor'); pg.wait_for_timeout(200); shot(pg,'21-settings'); ok('settings shows storage used',' MB' in pg.inner_text('.stor')); pg.keyboard.press('Escape')
    b.close()
ok('no console errors / page errors',not errors,'\n'.join(errors[:10]))
print(f'{sum(res)}/{len(res)} passed')
sys.exit(0 if all(res) else 1)
