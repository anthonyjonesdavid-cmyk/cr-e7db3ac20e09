"""End-to-end test (Kindle-style shelf + reader): python3 test/e2e.py [chromium|webkit] [--big]  (server on 127.0.0.1:8823)"""
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
CFSWIPE='''async ({dx,steps,dt,noup})=>{ const el=document.querySelector('#cf'); const r=el.getBoundingClientRect(); const x=r.left+r.width/2, y=r.top+r.height*0.5;
  const sleep=ms=>new Promise(r=>setTimeout(r,ms)); const tgt=document.elementFromPoint(x,y)||el;
  const ev=(t,cx)=>tgt.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:41,pointerType:'touch',isPrimary:true,clientX:cx,clientY:y,buttons:t==='pointerup'?0:1}));
  ev('pointerdown',x); for(let i=1;i<=steps;i++){ await sleep(dt); ev('pointermove',x+dx*i/steps); }
  if(noup) return null; ev('pointerup',x+dx); await sleep(1000); return document.querySelector('#cfInfo .cf-title').textContent; }'''
def state(pg): return pg.evaluate('(()=>{const R=__cr.R;const v=R.views[R.vi]||[];return {vi:R.vi,first:v.filter(x=>x!=null)[0],len:v.length,spread:R.spread,rtl:R.rtl,n:R.n,ui:document.querySelector("#reader").classList.contains("ui"),z:__cr.Z.s,cache:__cr.cache()}})()')
def shot(pg,name): pg.screenshot(path=f'{SH}/{ENG}-{name}.png')
def wait_render(pg,t=15000): pg.wait_for_function('document.querySelectorAll(".view .pg.loading").length===0 && document.querySelectorAll(".view .pg canvas").length>0',timeout=t)
def tab(pg,t): pg.click(f'#tabs [data-tab={t}]'); pg.wait_for_timeout(150)
def lib_card(pg,title): return pg.locator(f'.lc[data-title="{title}"]')
def open_comic(pg,title):
    tab(pg,'library'); lib_card(pg,title).click(); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg); pg.wait_for_timeout(300)
def back(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(200)
def sheet(pg,title,act):
    tab(pg,'library'); lib_card(pg,title).click(button='right'); pg.wait_for_selector(f'#{act}'); pg.click(f'#{act}'); pg.wait_for_timeout(200)
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
    pw=pg.evaluate('(()=>{let w=0;document.querySelectorAll(".view .pg").forEach(e=>w+=e.offsetWidth);return w})()')
    dist=pw*0.15; r=g([[-dist*i/16,0,50] for i in range(1,17)],hold=150); ok(f'{tag} slow drag past 13% commits',r['vi']==s0+1,json.dumps(r))
    r=g([[1,-8,16],[2,-20,16],[3,-35,16],[4,-55,16],[5,-80,16]]); ok(f'{tag} vertical pan does not turn',r['vi']==s0+1 and r['frames']==0,json.dumps(r))
    r=g([[-3,-10,16],[-6,-24,16],[-9,-40,16]]); ok(f'{tag} diagonal mostly-vertical does not turn',r['vi']==s0+1 and r['frames']==0,json.dumps(r))
    g([[6,0,15],[14,0,15],[22,0,15]])

FILES=sorted(f for f in os.listdir(T) if f.endswith('.pdf') and (BIG or f!='Atlas_Omnibus.pdf'))
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    ctx=b.new_context(viewport={'width':820,'height':1180},has_touch=True,device_scale_factor=2)
    pg=ctx.new_page()
    pg.on('pageerror',lambda e:errors.append('pageerror: '+str(e)))
    pg.on('console',lambda m: errors.append(f'console.{m.type}: {m.text}') if m.type=='error' else None)
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    ok('robots meta present',pg.evaluate("document.querySelector('meta[name=robots]').content")=='noindex, nofollow')
    ok('no comic display font / halftone left',pg.evaluate("!document.documentElement.outerHTML.includes('Bangers')"))
    shot(pg,'01-empty-home')
    t0=time.time(); pg.set_input_files('#fileIn',[f'{T}/{f}' for f in FILES])
    pg.wait_for_function(f'document.querySelectorAll(".lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=(400000 if BIG else 90000))
    ok(f'import {len(FILES)} PDFs',True,f'{time.time()-t0:.1f}s'); pg.wait_for_timeout(600)
    heads=pg.eval_on_selector_all('.row-h h2','els=>els.map(e=>e.textContent)')
    ok('home rows: Recently Added + auto-detected series rows',heads[0]=='Recently Added' and all(s in heads for s in ['Nightfall','Iron Tide','Starlight Ronin','The Hollow']),json.dumps(heads))
    ok('see-all tile ends each row',pg.locator('.row').first.locator('.seeall').count()==1)
    ok('row cards show title under cover',pg.locator('.rc .t').first.inner_text()!='')
    # edit via long-press/context sheet
    sheet(pg,'Glass Harbor','aEdit'); pg.fill('#eTitle','Glass Harbor (One-Shot)'); pg.click('#eSave'); pg.wait_for_timeout(200)
    ok('title editable via action sheet',lib_card(pg,'Glass Harbor (One-Shot)').count()==1)
    # long press (touch) opens the sheet
    bb=lib_card(pg,'Nightfall 03').bounding_box()
    pg.evaluate('''([x,y])=>{const t=document.elementFromPoint(x,y);t.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:51,pointerType:'touch',isPrimary:true,clientX:x,clientY:y,buttons:1}));}''',[bb['x']+40,bb['y']+60])
    pg.wait_for_timeout(700); ok('long-press opens action sheet',pg.locator('#aEdit').count()==1)
    pg.evaluate('''([x,y])=>document.elementFromPoint(x,y).dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:51,pointerType:'touch',clientX:x,clientY:y}))''',[bb['x']+40,bb['y']+60])
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)

    # ---- reader, portrait single page ----
    open_comic(pg,'Nightfall 01'); N=state(pg)['n']
    s=state(pg); ok('portrait = single page',s['len']==1 and not s['spread'],json.dumps(s))
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(300); shot(pg,'03-reader-portrait-cover')
    flicks(pg,'portrait')
    pg.evaluate('__cr.jumpTo(4)'); wait_render(pg)
    x0,y0,W,H=geo(pg)
    r=pg.evaluate(GEST,{'x':x0+W*0.8,'y':y0+H*0.5,'pts':[[-W*0.05*i,0,30] for i in range(1,9)],'hold':0,'noup':True}); pg.wait_for_timeout(120)
    shot(pg,'04-mid-page-turn-portrait'); ok('mid page-turn in progress',0.15<r['p']<0.9,json.dumps(r))
    pg.evaluate(UP,[x0+W*0.4,y0+H*0.5]); pg.wait_for_timeout(900); ok('page turn committed after drag',state(pg)['first']==5)
    pg.evaluate(TAP,{'x':x0+W/2,'y':y0+H/2,'n':1}); s=state(pg); ok('center tap shows toolbars',s['ui'],json.dumps(s)); shot(pg,'05-toolbar-shown')
    pg.evaluate(TAP,{'x':x0+W/2,'y':y0+H/2,'n':1}); ok('center tap hides toolbars',not state(pg)['ui'])
    pg.evaluate(TAP,{'x':x0+W*0.93,'y':y0+H/2,'n':1}); pg.wait_for_timeout(500); ok('right-edge tap turns forward',state(pg)['first']==6)
    pg.evaluate(TAP,{'x':x0+W*0.07,'y':y0+H/2,'n':1}); pg.wait_for_timeout(500); ok('left-edge tap turns back',state(pg)['first']==5)
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(250)
    pg.evaluate("(()=>{const s=document.querySelector('#scrub'); s.value=18; s.dispatchEvent(new Event('input',{bubbles:true}));})()")
    pg.wait_for_function("document.querySelector('#bubble img').complete && document.querySelector('#bubble img').naturalWidth>0",timeout=10000); pg.wait_for_timeout(150)
    shot(pg,'06-scrubber-thumb')
    pg.evaluate("document.querySelector('#scrub').dispatchEvent(new Event('change',{bubbles:true}))"); wait_render(pg); ok('scrubber jumps to page 18',state(pg)['first']==17)
    pg.click('#rGrid'); pg.wait_for_function("document.querySelectorAll('#pgrid img').length>8",timeout=15000); pg.wait_for_timeout(300); shot(pg,'07-pages-grid')
    pg.locator('#pgrid button[data-p="9"]').click(); wait_render(pg); ok('page grid jump to 10',state(pg)['first']==9)
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250)
    pg.evaluate(TAP,{'x':x0+W*0.5,'y':y0+H*0.35,'n':2}); pg.wait_for_timeout(900)
    s=state(pg); hi=pg.evaluate("Math.max(...[...document.querySelectorAll('.view .pg canvas')].map(c=>c.width))")
    ok('double-tap zooms 2.5x',abs(s['z']-2.5)<0.01,json.dumps(s)); ok('zoomed page re-rendered at higher resolution',hi>1600,f'canvas width {hi}'); shot(pg,'08-zoomed')
    r=pg.evaluate(GEST,{'x':x0+W*0.6,'y':y0+H*0.5,'pts':[[-5,0,15],[-10,0,15],[-15,0,15],[-20,0,15]],'hold':0,'noup':False})
    ok('no page turn while zoomed (pans instead)',r['first']==9 and r['frames']==0,json.dumps(r))
    pg.evaluate(TAP,{'x':x0+W*0.5,'y':y0+H*0.5,'n':2}); ok('double-tap resets zoom',state(pg)['z']==1)
    z=pg.evaluate(PINCH,{'cx':x0+W/2,'cy':y0+H/2,'d0':100,'d1':260}); ok('pinch zoom',z>2,f'z={z:.2f}')
    pg.evaluate(TAP,{'x':x0+W*0.5,'y':y0+H*0.5,'n':2})
    pg.evaluate('__cr.jumpTo(12)'); wait_render(pg); pg.wait_for_timeout(500)
    pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg)
    s=state(pg); ok('resumes same page after reload (in reader)',s['first']==12,json.dumps(s))
    back(pg)
    # build some reading history for the carousel / pill
    for t,pgn in [('Iron Tide 02',20),('The Hollow 01',8),('Starlight Ronin v02',30),('Nightfall 04',3),('Iron Tide 01',11)]:
        open_comic(pg,t); pg.evaluate(f'__cr.jumpTo({pgn})'); wait_render(pg); pg.wait_for_timeout(350); back(pg)
    open_comic(pg,'Nightfall 01'); back(pg)
    sheet(pg,'Nightfall 02','aToggle')
    # ---- Home (portrait) ----
    tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(700)
    ok('carousel centers most recent (Continue Reading)',pg.inner_text('#cfInfo .cf-title')=='Nightfall 01' and f'Page 13 of {N}' in pg.inner_text('#cfInfo'),pg.inner_text('#cfInfo'))
    ok('now-reading pill shows last comic + %',pg.is_visible('#nowPill') and 'Nightfall 01' in pg.inner_text('#nowPill') and '%' in pg.inner_text('#nowPill'))
    shot(pg,'10-home-portrait')
    pg.evaluate("document.querySelector('#homeScroll').scrollTop=520"); pg.wait_for_timeout(300); shot(pg,'11-home-rows-portrait')
    sx=pg.evaluate("(()=>{const r=document.querySelectorAll('.row-s')[1]; r.scrollLeft=300; return r.scrollLeft})()"); ok('rows scroll horizontally (free scroll)',sx>0,str(sx))
    pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(300)
    # carousel: swipe with momentum + snap, mid-swipe, tap side, tap center
    t1=pg.evaluate(CFSWIPE,{'dx':-150,'steps':6,'dt':16,'noup':False}); pos=pg.evaluate('__cr.CF.pos')
    ok('carousel swipe moves + snaps to a whole cover',t1!='Nightfall 01' and abs(pos-round(pos))<1e-6 and pos>=1,f'{t1} pos={pos}')
    pg.evaluate(CFSWIPE,{'dx':-700,'steps':5,'dt':12,'noup':False}); pos2=pg.evaluate('__cr.CF.pos'); ok('fast fling carries momentum further',pos2>=pos+2,f'{pos}->{pos2}')
    pg.wait_for_function('!__cr.CF.raf',timeout=5000); pg.evaluate('(()=>{const C=__cr.CF; C.stop(); C.pos=2; C.layout();})()'); pg.wait_for_timeout(200)
    pg.evaluate(CFSWIPE,{'dx':-110,'steps':6,'dt':30,'noup':True}); pg.wait_for_timeout(150)
    shot(pg,'12-carousel-mid-swipe'); mid=pg.evaluate('__cr.CF.pos'); ok('carousel tracks finger mid-swipe',2.2<mid<3,str(mid))
    pg.evaluate('''()=>{const el=document.querySelector('#cf .cf-item'); el.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:41,pointerType:'touch',clientX:300,clientY:300}));}'''); pg.wait_for_timeout(900)
    cur=round(pg.evaluate('__cr.CF.pos'))
    side=pg.evaluate(f'''(()=>{{const it=document.querySelector('#cf .cf-item[data-i="{cur+1}"]'); const r=it.getBoundingClientRect(); return [r.left+r.width*0.6,r.top+r.height/2]}})()''')
    pg.mouse.click(side[0],side[1]); pg.wait_for_timeout(700); ok('tap side cover brings it to center',round(pg.evaluate('__cr.CF.pos'))==cur+1)
    cb=pg.locator(f'#cf .cf-item[data-i="{cur+1}"]').bounding_box(); want=pg.inner_text('#cfInfo .cf-title')
    pg.mouse.click(cb['x']+cb['width']/2,cb['y']+cb['height']/2); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg)
    ok('tap center cover opens it',pg.text_content('#rTitle')==want,want); back(pg)
    pg.click('#nowPill'); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg); ok('pill resumes last comic',pg.text_content('#rTitle')==want); back(pg)
    # ---- Library ----
    tab(pg,'library'); pg.evaluate("document.querySelector('#libScroll').scrollTop=0"); pg.wait_for_timeout(500)
    cols=pg.evaluate("getComputedStyle(document.querySelector('#libGrid')).gridTemplateColumns.split(' ').length"); ok('library grid: 5 columns on iPad portrait',cols==5,str(cols))
    ok('finished check badge',pg.locator('.lc .done').count()==1); ok('progress line under in-progress covers',pg.locator('.lc .pl').count()>=5)
    shot(pg,'13-library-portrait')
    pg.click('.chip[data-f=finished]'); ok('filter Finished',pg.locator('.lc').count()==1)
    pg.click('.chip[data-f=progress]'); ok('filter In Progress',pg.locator('.lc').count()==6,str(pg.locator('.lc').count()))
    pg.click('.chip[data-f=unread]'); ok('filter Unread',pg.locator('.lc').count()==len(FILES)-7)
    pg.click('.chip[data-f=all]'); pg.fill('#q','hollow'); pg.wait_for_timeout(100); ok('search filters',pg.locator('.lc').count()==3); pg.fill('#q',''); pg.wait_for_timeout(100)
    pg.click('#sortBtn'); pg.click('.menu button:has-text("Title")'); pg.wait_for_timeout(200)
    ok('A-Z index shown for title sort',pg.is_visible('#azIndex'))
    first=pg.locator('.lc').first.get_attribute('data-title'); ok('title sort A→Z',first.startswith('Atlas' if BIG else 'Glass'),first)
    zb=pg.locator('#azIndex span[data-l="T"]').bounding_box(); pg.mouse.click(zb['x']+zb['width']/2,zb['y']+zb['height']/2); pg.wait_for_timeout(300)
    st=pg.evaluate("(()=>{const s=document.querySelector('#libScroll'),t=document.querySelector('#libGrid [data-letter=T]');return [s.scrollTop,Math.min(t.offsetTop-8,s.scrollHeight-s.clientHeight)]})()"); shot(pg,'14-library-az'); ok('A-Z index jumps to letter',st[0]>0 and abs(st[0]-st[1])<=2,str(st))
    pg.click('#sortBtn'); pg.click('.menu button:has-text("Recent")'); pg.wait_for_timeout(100)
    tab(pg,'home'); pg.locator('.row-h',has_text='The Hollow').click(); pg.wait_for_timeout(300)
    ok('series heading opens series grid',pg.locator('.lc').count()==3 and pg.locator('.chip.scope').count()==1); pg.click('.chip.scope'); pg.wait_for_timeout(100)
    tab(pg,'home'); pg.locator('.row').first.locator('.seeall').click(); pg.wait_for_timeout(300); ok('See all opens library',pg.is_visible('#libGrid') and pg.locator('.lc').count()==len(FILES))

    # ---- landscape ----
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(400)
    cols=pg.evaluate("getComputedStyle(document.querySelector('#libGrid')).gridTemplateColumns.split(' ').length"); ok('library grid: 7 columns landscape',cols==7,str(cols)); shot(pg,'15-library-landscape')
    tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.evaluate('__cr.CF.to(0,10)'); pg.wait_for_timeout(500); shot(pg,'16-home-landscape')
    open_comic(pg,'Nightfall 01')
    s=state(pg); ok('landscape = two-page spread',s['spread'] and s['len']==2,json.dumps(s))
    pg.evaluate('__cr.jumpTo(0)'); wait_render(pg); pg.wait_for_timeout(200)
    vis=pg.evaluate("[...document.querySelectorAll('.view .pg')].map(e=>({blank:e.classList.contains('blank')}))"); ok('cover alone on the right',vis[0]['blank'] and not vis[1]['blank'])
    flicks(pg,'landscape')
    pg.evaluate('__cr.jumpTo(3)'); wait_render(pg); pg.wait_for_timeout(200); ok('spread shows pages 4-5',pg.text_content('#pgText').startswith('4–5'),pg.text_content('#pgText'))
    x0,y0,W,H=geo(pg)
    r=pg.evaluate(GEST,{'x':x0+W*0.85,'y':y0+H*0.5,'pts':[[-W*0.06*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(120)
    shot(pg,'17-landscape-mid-turn'); ok('spread mid-turn',0.2<r['p']<0.95,json.dumps(r)); pg.evaluate(UP,[x0+W*0.4,y0+H*0.5]); pg.wait_for_timeout(900)
    ok('spread turn lands on 6-7',pg.text_content('#pgText').startswith('6–7'),pg.text_content('#pgText'))
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(250); shot(pg,'18-landscape-toolbar')
    pg.click('#rSpread'); pg.wait_for_timeout(300); wait_render(pg); ok('toggle single page in landscape',state(pg)['len']==1)
    pg.click('#rSpread'); pg.wait_for_timeout(300); wait_render(pg); ok('toggle back to spread',state(pg)['len']==2)
    back(pg)
    # ---- RTL ----
    open_comic(pg,'Starlight Ronin v01')
    pg.evaluate('__cr.toggleUI(true)'); pg.click('#rRtl'); pg.wait_for_timeout(300); pg.evaluate('__cr.jumpTo(5)'); wait_render(pg)
    vis=pg.evaluate("[...document.querySelectorAll('.view .pg')].map(e=>+e.dataset.p)"); ok('RTL spread: lower page on the right',vis==[6,5],json.dumps(vis))
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250)
    x0,y0,W,H=geo(pg); x=x0+W*0.4; y=y0+H*0.45
    r=pg.evaluate(GEST,{'x':x,'y':y,'pts':[[5,0,15],[10,0,15],[15,0,15],[20,0,15]],'hold':0,'noup':False}); ok('RTL: flick right goes forward',r['first']==7,json.dumps(r))
    r=pg.evaluate(GEST,{'x':x,'y':y,'pts':[[-5,0,15],[-10,0,15],[-15,0,15],[-20,0,15]],'hold':0,'noup':False}); ok('RTL: flick left goes back',r['first']==5,json.dumps(r))
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(500); wait_render(pg)
    r=pg.evaluate(GEST,{'x':300,'y':500,'pts':[[5,0,15],[10,0,15],[15,0,15],[20,0,15]],'hold':0,'noup':False}); s=state(pg); ok('RTL single page: flick right goes forward',s['first']==6 and s['rtl'],json.dumps(r))
    r=pg.evaluate(GEST,{'x':200,'y':500,'pts':[[41*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(120); shot(pg,'19-rtl-portrait-mid-turn'); pg.evaluate(UP,[500,500]); pg.wait_for_timeout(900)
    back(pg)
    if BIG:
        t0=time.time(); open_comic(pg,'Atlas Omnibus'); ok('big PDF opens',True,f'{time.time()-t0:.1f}s, {state(pg)["n"]} pages, {os.path.getsize(T+"/Atlas_Omnibus.pdf")//1048576} MB')
        t0=time.time(); pg.evaluate('__cr.jumpTo(150)'); wait_render(pg,60000); ok('big PDF random-access page 151',state(pg)['first']==150,f'{time.time()-t0:.2f}s')
        for i in range(12): pg.evaluate('__cr.go(-1,200)'); pg.wait_for_timeout(260)
        wait_render(pg,60000); c=state(pg)['cache']; ok('LRU bounded after many turns',c['px']<=c['budget'],json.dumps(c)); back(pg)
    # ---- phone ----
    pg.set_viewport_size({'width':390,'height':844}); tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.evaluate('__cr.CF.to(0,10)'); pg.wait_for_timeout(500); shot(pg,'20-phone-home')
    tab(pg,'library'); pg.wait_for_timeout(200); cols=pg.evaluate("getComputedStyle(document.querySelector('#libGrid')).gridTemplateColumns.split(' ').length"); ok('library grid: 3 columns phone',cols==3,str(cols)); shot(pg,'21-phone-library')
    open_comic(pg,'The Hollow 02'); pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(250); shot(pg,'22-phone-reader')
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250); flicks(pg,'phone')
    if ENG=='chromium':
        cdp=ctx.new_cdp_session(pg); x0,y0,W,H=geo(pg); x=x0+W*0.6; y=y0+H*0.45
        def touch(tp,px,py): cdp.send('Input.dispatchTouchEvent',{'type':tp,'touchPoints':[] if tp=='touchEnd' else [{'x':px,'y':py,'id':1}]})
        for sign,name in [(-1,'forward'),(1,'back')]:
            before=state(pg)['first']; touch('touchStart',x,y)
            for i in range(1,5): time.sleep(0.015); touch('touchMove',x+sign*5*i,y)
            touch('touchEnd',x+sign*20,y); pg.wait_for_timeout(900)
            ok(f'REAL CDP touch flick 20px {name}',state(pg)['first']==before-sign,f"{before}->{state(pg)['first']}")
    back(pg)
    # ---- delete + settings ----
    pg.set_viewport_size({'width':820,'height':1180}); tab(pg,'library'); n0=pg.locator('.lc').count()
    sheet(pg,'Iron Tide 05','aDelete'); pg.wait_for_selector('#confirmOk'); shot(pg,'23-delete-confirm'); pg.click('#confirmOk'); pg.wait_for_timeout(400)
    ok('delete with confirm',pg.locator('.lc').count()==n0-1)
    pg.click('#settingsBtn'); pg.wait_for_selector('.stor'); pg.wait_for_timeout(200); shot(pg,'24-settings'); ok('settings shows storage used',' MB' in pg.inner_text('.stor')); pg.keyboard.press('Escape')
    b.close()
ok('no console errors / page errors',not errors,'\n'.join(errors[:10]))
print(f'{sum(res)}/{len(res)} passed')
sys.exit(0 if all(res) else 1)
