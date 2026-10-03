"""End-to-end test (Kindle-style shelf + reader): python3 test/e2e.py [chromium|webkit] [--big]  (server on 127.0.0.1:8823)"""
import sys, os, json, time, re
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'
ENG=sys.argv[1] if len(sys.argv)>1 else 'chromium'
BIG='--big' in sys.argv
T=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','testpdfs'))
SH=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','shots'))
os.makedirs(SH,exist_ok=True)
res=[]; errors=[]
# ---- mock "Google Drive" download server: streams files slowly (chunked reads), with CORS, like alt=media ----
import threading, http.server, socketserver, subprocess
DRV=os.path.join(T,'drive')
if not os.path.exists(os.path.join(DRV,'Drive_Annual.pdf')): subprocess.run([sys.executable,os.path.join(os.path.dirname(__file__),'gen_pdfs.py'),'--drive'],check=True)
class SlowH(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u=urlparse(self.path); q=parse_qs(u.query); fp=os.path.join(DRV,os.path.basename(u.path))
        if not u.path.startswith('/f/') or not os.path.exists(fp): self.send_response(404); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers(); return
        delay=float(q.get('d',['0.03'])[0]); sz=os.path.getsize(fp)
        self.send_response(200); self.send_header('Content-Type','application/pdf'); self.send_header('Content-Length',str(sz)); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
        try:
            with open(fp,'rb') as f:
                while True:
                    b=f.read(262144)
                    if not b: break
                    self.wfile.write(b); self.wfile.flush(); time.sleep(delay)
        except (BrokenPipeError,ConnectionResetError): pass
class TS(socketserver.ThreadingMixIn,http.server.HTTPServer): daemon_threads=True; allow_reuse_address=True
DPORT=8824 if ENG=='chromium' else 8825
threading.Thread(target=TS(('127.0.0.1',DPORT),SlowH).serve_forever,daemon=True).start()
DS=f'http://127.0.0.1:{DPORT}'
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
  if(noup) return null; ev('pointerup',x+dx); await sleep(1000); return __cr.CF.items[Math.round(__cr.CF.pos)].title; }'''
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
    # hermetic: Google (GIS / Picker) is blocked here; the live check exercises the real sign-in popup
    import re as _re; GRE=_re.compile(r'https://([a-z0-9-]+\.)*(google|googleapis|gstatic)\.com/')
    ctx.route(GRE,lambda r:r.abort())
    pg.on('console',lambda m: errors.append(f'console.{m.type}: {m.text}') if m.type=='error' and not GRE.match((m.location or {}).get('url','') or '') and not GRE.search(m.text) else None)
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    ok('robots meta present',pg.evaluate("document.querySelector('meta[name=robots]').content")=='noindex, nofollow')
    ok('no comic display font / halftone left',pg.evaluate("!document.documentElement.outerHTML.includes('Bangers')"))
    shot(pg,'01-empty-home')
    ok('empty state offers From Google Drive + From Files',pg.locator('#homeScroll [data-act=drive]').count()==1 and pg.locator('#homeScroll [data-act=import]').count()==1)
    t0=time.time(); pg.set_input_files('#fileIn',[f'{T}/{f}' for f in FILES])
    pg.wait_for_function(f'document.querySelectorAll(".lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=(400000 if BIG else 90000))
    ok(f'import {len(FILES)} PDFs',True,f'{time.time()-t0:.1f}s'); pg.wait_for_timeout(600)
    heads=pg.eval_on_selector_all('.row-h h2','els=>els.map(e=>e.textContent)')
    ok('home rows: Recently Added + auto-detected series rows',heads[0]=='Recently Added' and all(s in heads for s in ['Nightfall','Iron Tide','Starlight Ronin','The Hollow','Twin Moon']),json.dumps(heads))
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
    ctr=pg.evaluate("(()=>{const i=Math.round(__cr.CF.pos), el=document.querySelector('#cf .cf-item[data-i=\"'+i+'\"]'); return {t:__cr.CF.items[i].title, aria:el.getAttribute('aria-label')}})()")
    ok('carousel centers most recent',ctr['t']=='Nightfall 01' and f'page 13 of {N}' in ctr['aria'],str(ctr))
    ok('no caption block under the carousel',pg.evaluate("!document.querySelector('#cfInfo,.cf-info') && !/CONTINUE READING/i.test(document.querySelector('.hero').innerText)"))
    gap=pg.evaluate("(()=>{const i=Math.round(__cr.CF.pos); const c=document.querySelector('#cf .cf-item[data-i=\"'+i+'\"]').getBoundingClientRect(); return document.querySelector('.row-h').getBoundingClientRect().top-c.bottom})()")
    ok('rows sit just below carousel (room for reflection, no big gap)',25<gap<75,str(round(gap)))
    ok('now-reading pill shows last comic + %',pg.is_visible('#nowPill') and 'Nightfall 01' in pg.inner_text('#nowPill') and '%' in pg.inner_text('#nowPill'))
    shot(pg,'10-home-portrait')
    pg.evaluate("document.querySelector('#homeScroll').scrollTop=520"); pg.wait_for_timeout(300); shot(pg,'11-home-rows-portrait')
    sx=pg.evaluate("(()=>{const r=document.querySelectorAll('.row-s')[0]; r.scrollLeft=300; return r.scrollLeft})()"); ok('rows scroll horizontally (free scroll)',sx>0,str(sx))
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
    cb=pg.locator(f'#cf .cf-item[data-i="{cur+1}"]').bounding_box(); want=pg.evaluate('__cr.CF.items[Math.round(__cr.CF.pos)].title')
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
    first=pg.locator('.lc').first.get_attribute('data-title'); ok('title sort A→Z',first.startswith('Atlas' if BIG else 'Ember'),first)
    zb=pg.locator('#azIndex span[data-l="T"]').bounding_box(); pg.mouse.click(zb['x']+zb['width']/2,zb['y']+zb['height']/2); pg.wait_for_timeout(300)
    st=pg.evaluate("(()=>{const s=document.querySelector('#libScroll'),t=document.querySelector('#libGrid [data-letter=T]');return [s.scrollTop,Math.min(t.offsetTop-8,s.scrollHeight-s.clientHeight)]})()"); shot(pg,'14-library-az'); ok('A-Z index jumps to letter',st[0]>0 and abs(st[0]-st[1])<=2,str(st))
    pg.click('#sortBtn'); pg.click('.menu button:has-text("Recent")'); pg.wait_for_timeout(100)
    tab(pg,'home'); pg.locator('.row-h',has_text='The Hollow').click(); pg.wait_for_timeout(300)
    ok('series heading opens series grid',pg.locator('.lc').count()==3 and pg.locator('.chip.scope').count()==1); pg.click('.chip.scope'); pg.wait_for_timeout(100)
    tab(pg,'home'); pg.locator('.row').first.locator('.seeall').click(); pg.wait_for_timeout(300); ok('See all opens library',pg.is_visible('#libGrid') and pg.locator('.lc').count()==len(FILES))

    # ---- landscape ----
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(400)
    cols=pg.evaluate("getComputedStyle(document.querySelector('#libGrid')).gridTemplateColumns.split(' ').length"); ok('library grid: 7 columns landscape',cols==7,str(cols)); shot(pg,'15-library-landscape')
    tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.evaluate('__cr.CF.to(0,10)'); pg.wait_for_timeout(500); shot(pg,'16-home-landscape'); g=pg.evaluate("(()=>{const i=Math.round(__cr.CF.pos); const c=document.querySelector('#cf .cf-item[data-i=\"'+i+'\"]').getBoundingClientRect(); return document.querySelector('.row-h').getBoundingClientRect().top-c.bottom})()"); ok('landscape: rows close under carousel',20<g<80,str(round(g)))
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
    # ---- FOLD IN THE MIDDLE: wide two-page scans hinge at the centre of the sheet ----
    FOLDINFO="""(()=>{const f=__cr.flip, fl=document.querySelector('.flip .flipper'), st=document.querySelector('#stage').getBoundingClientRect(), v=document.querySelector('.view .pg').getBoundingClientRect();
      return {mode:f&&f.mode,p:f&&f.p,origin:fl&&fl.style.transformOrigin,hinge:fl&&(fl.style.transformOrigin.startsWith('0')?parseFloat(fl.style.left):parseFloat(fl.style.left)+parseFloat(fl.style.width))+st.left,
        center:v.left+v.width/2, halves:[...document.querySelectorAll('.flip .face.half')].map(e=>e.dataset.p+e.dataset.half+(e.classList.contains('front')?'*':'')), halfw:fl&&parseFloat(fl.style.width), pagew:v.width}})()"""
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(300)
    open_comic(pg,'Twin Moon 01'); s=state(pg)
    ok('Auto: wide two-page scans -> Fold in middle',pg.evaluate('__cr.R.fold')==True and s['len']==1 and not s['spread'],json.dumps(s))
    pg.evaluate('__cr.jumpTo(2)'); wait_render(pg); pg.wait_for_timeout(300)
    fit=pg.evaluate("(()=>{const st=document.querySelector('#stage').getBoundingClientRect(),p=document.querySelector('.view .pg').getBoundingClientRect();return {sw:st.width,pw:p.width,ph:p.height,cy:(p.top+p.bottom)/2,scy:(st.top+st.bottom)/2}})()")
    ok('fold mode portrait: full wide page fitted to screen',abs(fit['pw']-fit['sw'])<=2 and fit['pw']>fit['ph']*1.2 and abs(fit['cy']-fit['scy'])<=2,json.dumps(fit))
    x0,y0,W,H=geo(pg)
    r=pg.evaluate(GEST,{'x':x0+W*0.92,'y':y0+H*0.5,'pts':[[-W*0.045*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(150)
    fi=pg.evaluate(FOLDINFO); shot(pg,'40-fold-mid-portrait')
    ok('mid-fold (portrait): right half lifts, hinge at the centre of the wide page',fi['mode']=='fold' and fi['origin'].startswith('0') and abs(fi['hinge']-fi['center'])<=1.5 and 0.15<fi['p']<0.95 and abs(fi['halfw']-fi['pagew']/2)<=1,json.dumps(fi))
    ok('fold faces: current L stays, current R turns (front), next sheet R underneath, next L on the back',sorted(fi['halves'])==sorted(['2L','3R','2R*','3L']),json.dumps(fi['halves']))
    pg.evaluate(UP,[x0+W*0.3,y0+H*0.5]); pg.wait_for_timeout(900); ok('fold completes to next sheet',state(pg)['first']==3)
    flicks(pg,'fold portrait')
    # zoomed: no turns
    z=pg.evaluate(PINCH,{'cx':x0+W/2,'cy':y0+H/2,'d0':100,'d1':260}); b4=state(pg)['first']
    r=pg.evaluate(GEST,{'x':x0+W*0.6,'y':y0+H*0.45,'pts':[[-5,0,15],[-10,0,15],[-15,0,15],[-20,0,15]],'hold':0,'noup':False})
    ok('fold mode: no page turn while zoomed',z>1.5 and state(pg)['first']==b4,f'z={z:.2f}'); pg.evaluate(TAP,{'x':x0+W*0.5,'y':y0+H*0.5,'n':2}); pg.wait_for_timeout(500)
    # landscape: still one wide sheet, no 2-up toggle
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(500); wait_render(pg); s=state(pg)
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(200); hid=pg.evaluate("document.querySelector('#rSpread').classList.contains('hidden')"); pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250)
    fit=pg.evaluate("(()=>{const st=document.querySelector('#stage').getBoundingClientRect(),p=document.querySelector('.view .pg').getBoundingClientRect();return {sh:st.height,sw:st.width,pw:p.width,ph:p.height,cx:(p.left+p.right)/2,scx:(st.left+st.right)/2}})()")
    ok('fold mode landscape: one wide sheet fitted to screen, 2-up toggle hidden',s['len']==1 and not s['spread'] and hid and (abs(fit['ph']-fit['sh'])<=2 or abs(fit['pw']-fit['sw'])<=2) and abs(fit['cx']-fit['scx'])<=2,json.dumps([s,fit,hid]))
    x0,y0,W,H=geo(pg); b4=state(pg)['first']
    r=pg.evaluate(GEST,{'x':x0+W*0.8,'y':y0+H*0.5,'pts':[[-W*0.04*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(150)
    fi=pg.evaluate(FOLDINFO); shot(pg,'41-fold-mid-landscape')
    ok('mid-fold (landscape): hinge at the centre of the wide page',fi['mode']=='fold' and abs(fi['hinge']-fi['center'])<=1.5 and 0.15<fi['p']<0.95,json.dumps(fi))
    pg.evaluate(UP,[x0+W*0.3,y0+H*0.5]); pg.wait_for_timeout(900); ok('landscape fold completes',state(pg)['first']==b4+1)
    flicks(pg,'fold landscape')
    # RTL: hinge mirrored (left half lifts going forward = swipe right)
    pg.evaluate('__cr.toggleUI(true)'); pg.click('#rRtl'); pg.wait_for_timeout(300); pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250)
    b4=state(pg)['first']; r=pg.evaluate(GEST,{'x':x0+W*0.2,'y':y0+H*0.5,'pts':[[W*0.04*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(150)
    fi=pg.evaluate(FOLDINFO); shot(pg,'42-fold-mid-rtl')
    ok('RTL fold: left half lifts (hinge mirrored) going forward',fi['mode']=='fold' and fi['origin'].startswith('100%') and abs(fi['hinge']-fi['center'])<=1.5 and f"{b4}L*" in fi['halves'],json.dumps(fi))
    pg.evaluate(UP,[x0+W*0.8,y0+H*0.5]); pg.wait_for_timeout(900); ok('RTL fold goes forward',state(pg)['first']==b4+1)
    pg.evaluate('__cr.toggleUI(true)'); pg.click('#rRtl'); pg.wait_for_timeout(300); back(pg)
    # standard comics are untouched; Edit sheet override
    open_comic(pg,'Nightfall 03'); ok('portrait-page comic: Auto -> Standard turn',pg.evaluate('__cr.R.fold')==False and state(pg)['spread'],json.dumps(state(pg)))
    x0,y0,W,H=geo(pg); r=pg.evaluate(GEST,{'x':x0+W*0.85,'y':y0+H*0.5,'pts':[[-W*0.06*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(120)
    ok('standard comic still uses the spread turn',pg.evaluate('__cr.flip&&__cr.flip.mode')=='spread'); pg.evaluate(UP,[x0+W*0.4,y0+H*0.5]); pg.wait_for_timeout(900); back(pg)
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(300)
    sheet(pg,'Twin Moon 01','aEdit'); pg.wait_for_selector('#eTurn')
    ok('Edit sheet: Page turn Auto / Standard / Fold in middle',pg.eval_on_selector_all('#eTurn button','b=>b.map(x=>x.textContent)')==['Auto','Standard','Fold in middle'] and pg.locator('#eTurn button.on').text_content()=='Auto' and 'detected: fold in middle' in pg.inner_text('.fhint'))
    pg.click('#eTurn [data-v=standard]'); shot(pg,'43-edit-page-turn'); pg.click('#eSave'); pg.wait_for_timeout(300)
    open_comic(pg,'Twin Moon 01'); ok('Page turn = Standard overrides Auto',pg.evaluate('__cr.R.fold')==False); back(pg)
    sheet(pg,'Nightfall 05','aEdit'); pg.click('#eTurn [data-v=fold]'); pg.click('#eSave'); pg.wait_for_timeout(300)
    open_comic(pg,'Nightfall 05'); ok('Page turn = Fold in middle forces fold',pg.evaluate('__cr.R.fold')==True); back(pg)
    for t in ('Twin Moon 01','Nightfall 05'):
        sheet(pg,t,'aEdit'); pg.click('#eTurn [data-v=auto]'); pg.click('#eSave'); pg.wait_for_timeout(250)
    open_comic(pg,'Twin Moon 01'); ok('back to Auto -> fold',pg.evaluate('__cr.R.fold')==True); back(pg)
    if BIG:
        t0=time.time(); open_comic(pg,'Atlas Omnibus'); ok('big PDF opens',True,f'{time.time()-t0:.1f}s, {state(pg)["n"]} pages, {os.path.getsize(T+"/Atlas_Omnibus.pdf")//1048576} MB')
        t0=time.time(); pg.evaluate('__cr.jumpTo(150)'); wait_render(pg,60000); ok('big PDF random-access page 151',state(pg)['first']==150,f'{time.time()-t0:.2f}s')
        for i in range(12): pg.evaluate('__cr.go(-1,200)'); pg.wait_for_timeout(260)
        wait_render(pg,60000); c=state(pg)['cache']; ok('LRU bounded after many turns',c['px']<=c['budget'],json.dumps(c)); back(pg)
    # ---- phone ----
    pg.set_viewport_size({'width':390,'height':844}); tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.evaluate('__cr.CF.to(0,10)'); pg.wait_for_timeout(500); shot(pg,'20-phone-home'); g=pg.evaluate("(()=>{const i=Math.round(__cr.CF.pos); const c=document.querySelector('#cf .cf-item[data-i=\"'+i+'\"]').getBoundingClientRect(); return document.querySelector('.row-h').getBoundingClientRect().top-c.bottom})()"); ok('phone: rows close under carousel',20<g<80,str(round(g)))
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
    # ---- import menu + Google Drive (Drive itself mocked: unconfigured message, then streamed import from a throttled local URL) ----
    pg.set_viewport_size({'width':820,'height':1180}); tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(300)
    pg.click('#importBtn'); pg.wait_for_selector('.menu.imp'); pg.wait_for_timeout(200)
    ok('+ opens import menu: From Google Drive / Entire Folder / From Files',pg.inner_text('#miDrive').strip()=='From Google Drive' and 'Entire Drive Folder' in pg.inner_text('#miFolder') and pg.inner_text('#miFiles').strip()=='From Files')
    shot(pg,'25-import-menu')
    pops=[]; ctx.on('page',lambda q:pops.append(q))
    pg.click('#miDrive')
    for _ in range(150):
        if pops or pg.evaluate('(()=>{const m=document.querySelector("#dConnMsg"); return !!(m&&m.textContent.includes("reach Google"))})()'): break
        pg.wait_for_timeout(100)
    if pops:   # (Playwright WebKit doesn't always honour the route block: the real GIS popup opened instead)
        ok('Drive configured: sign-in popup opens from the tap',True,'popup'); [q.close() for q in pops]; pg.wait_for_timeout(1200)
        pg.evaluate("document.querySelectorAll('.mwrap').forEach(m=>m.remove())")   # sign-in help sheet shown after the popup closes
    else:
        ok('Drive configured: Google unreachable is handled with a clear message',pg.locator('#dConnGo').is_disabled()); shot(pg,'26-drive-unreachable'); pg.click('.modal.drv [data-r=no]')
    ok('requested scope is drive.readonly (as configured)',pg.evaluate('__cr.drive.scope').endswith('/drive.readonly'))
    with pg.expect_file_chooser(timeout=3000) as fc:
        pg.click('#importBtn'); pg.click('#miFiles')
    ok('From Files opens the system file picker',fc.value is not None)
    AS=os.path.getsize(f'{DRV}/Drive_Annual.pdf'); NS=os.path.getsize(f'{T}/Nightfall_02.pdf')
    items=[{'id':'drv-annual','name':'Drive_Annual.pdf','size':AS,'url':f'{DS}/f/Drive_Annual.pdf?d=0.04'},
           {'id':'drv-dup','name':'Nightfall_02.pdf','size':NS,'url':f'{DS}/f/Nightfall_02.pdf'},
           {'id':'drv-bad','name':'Broken.pdf','size':90000,'url':f'{DS}/f/Broken.pdf'},
           {'id':'drv-404','name':'Missing_Issue.pdf','size':5000,'url':f'{DS}/f/nope.pdf'}]
    n0=pg.evaluate('document.querySelectorAll("#libGrid .lc").length')
    pg.evaluate('(it)=>{ window.__dr=__cr.drive.importRemote(it,{auth:false}); }',items)
    pg.wait_for_selector('.modal.dl'); pg.wait_for_function('parseFloat(document.querySelector(".dlr[data-k=\'0\'] .dlbar i").style.width)>=40',timeout=60000)
    shot(pg,'27-drive-progress')
    mid=pg.evaluate('({p:document.querySelector(".dlr[data-k=\'0\'] .dlp").textContent,s:document.querySelector(".dlr[data-k=\'0\'] .dls").textContent,sub:document.querySelector("#dlSub").textContent,all:document.querySelector("#dlAll").style.width})')
    ok('progress sheet: per-file % + bytes + overall',mid['p'].endswith('%') and ' of ' in mid['s'] and '1 of 4' in mid['sub'] and float(mid['all'][:-1])>0,json.dumps(mid))
    r=pg.evaluate('window.__dr'); errors[:]=[e for e in errors if 'status of 404' not in e]  # the deliberate mock-Drive 404 above
    ok('drive import result: 1 imported, 1 duplicate skipped, 2 failed',r=={'ok':1,'skip':1,'fail':2},json.dumps(r))
    sts=pg.eval_on_selector_all('.dlr','els=>els.map(e=>e.className.replace("dlr ","")+": "+e.querySelector(".dls").textContent)')
    ok('per-file statuses (done / skip / invalid PDF / HTTP 404)',sts[0].startswith('done') and sts[1]=='skip: Already in your library' and sts[2]=='fail: Not a valid PDF' and sts[3].startswith('fail') and '404' in sts[3],json.dumps(sts))
    shot(pg,'28-drive-done')
    chunks=pg.evaluate('''()=>new Promise(res=>{const r=indexedDB.open('comic-reader');r.onsuccess=()=>{const d=r.result;const out={};const c=d.transaction('chunks').objectStore('chunks').openKeyCursor();c.onsuccess=()=>{const cur=c.result;if(!cur){res(out);return;}out[cur.key[0]]=(out[cur.key[0]]||0)+1;cur.continue();};};})''')
    rec=pg.evaluate("(async()=>{const r=indexedDB.open('comic-reader');await new Promise(x=>r.onsuccess=x);const all=await new Promise(x=>{const q=r.result.transaction('comics').objectStore('comics').getAll();q.onsuccess=()=>x(q.result)});const a=all.find(c=>c.driveId==='drv-annual');return a&&{id:a.id,size:a.size,pages:a.pages,title:a.title,series:a.series,n:all.length}})()")
    ok('streamed into 4 MB IndexedDB chunks (no orphan chunks from failures)',rec and chunks.get(rec['id'])==-(-AS//(4*1024*1024)) and len(chunks)==rec['n'] and rec['size']==AS,f"{rec} chunks={chunks.get(rec['id']) if rec else None} ids={len(chunks)}")
    ok('title from Drive filename',rec and rec['title']=='Drive Annual' and rec['pages']==30,json.dumps(rec))
    pg.click('#dlDone'); pg.wait_for_timeout(200); ok('library grew by one',pg.evaluate('document.querySelectorAll("#libGrid .lc").length')==n0+1)
    open_comic(pg,'Drive Annual'); pg.evaluate('__cr.jumpTo(20)'); wait_render(pg); ok('Drive-imported comic opens + renders deep page',state(pg)['first']==20); back(pg)
    r=pg.evaluate('(it)=>__cr.drive.importRemote(it,{auth:false})',[{'id':'drv-annual','name':'Renamed In Drive.pdf','size':AS,'url':f'{DS}/f/Drive_Annual.pdf'}])
    ok('re-import of same Drive file id is skipped',r=={'ok':0,'skip':1,'fail':0},json.dumps(r)); pg.click('#dlDone')
    pg.evaluate('(it)=>{ window.__dr=__cr.drive.importRemote(it,{auth:false}); }',[{'id':'drv-c1','name':'Cancel_Me.pdf','size':AS,'url':f'{DS}/f/Drive_Annual.pdf?d=0.06'},{'id':'drv-c2','name':'Never_Started.pdf','size':AS,'url':f'{DS}/f/Drive_Annual.pdf'}])
    pg.wait_for_function('parseFloat(document.querySelector(".dlr[data-k=\'0\'] .dlbar i").style.width)>=25',timeout=60000); pg.click('#dlCancel')
    r=pg.evaluate('window.__dr'); sts=pg.eval_on_selector_all('.dlr','els=>els.map(e=>e.className.replace("dlr ",""))')
    chunks2=pg.evaluate('''()=>new Promise(res=>{const r=indexedDB.open('comic-reader');r.onsuccess=()=>{const out=new Set();const c=r.result.transaction('chunks').objectStore('chunks').openKeyCursor();c.onsuccess=()=>{const cur=c.result;if(!cur){res(out.size);return;}out.add(cur.key[0]);cur.continue();};};})''')
    ok('cancel stops download, cleans partial chunks, skips the rest',r['ok']==0 and sts==['cancel','cancel'] and chunks2==rec['n'] and 'cancelled' in pg.inner_text('#dlHead').lower(),f'{r} {sts} ids={chunks2}')
    shot(pg,'29-drive-cancelled'); pg.click('#dlDone')
    sheet(pg,'Drive Annual','aDelete'); pg.click('#confirmOk'); pg.wait_for_timeout(300)

    # ---- wide two-page-spread first pages: cropped covers, Edit > Cover, migration ----
    RECS='''(async()=>{const r=indexedDB.open('comic-reader');await new Promise(x=>r.onsuccess=x);const all=await new Promise(x=>{const q=r.result.transaction('comics').objectStore('comics').getAll();q.onsuccess=()=>x(q.result)});
      const out={}; for(const c of all){ const b=new Blob([c.cover],{type:'image/jpeg'}); const bm=await createImageBitmap(b); out[c.title]={crop:c.coverCrop,mode:c.coverMode,v:c.coverV,aspect:c.aspect,cw:bm.width,ch:bm.height,id:c.id}; bm.close&&bm.close(); } return out;})()'''
    recs=pg.evaluate(RECS); e1,e2,e3=recs.get('Ember Road 01'),recs.get('Ember Road 02'),recs.get('Ember Road 03')
    ok('wide first page -> right half used',all(e and e['crop']['side']=='right' for e in (e1,e2,e3)),json.dumps([e and e['crop'] for e in (e1,e2,e3)]))
    ok('letterbox bands trimmed (top/bottom)',e1['crop']['y']>0.03 and e1['crop']['h']<0.94 and e3['crop']['y']>0.06 and e2['crop']['y']<0.02,json.dumps([e1['crop'],e2['crop'],e3['crop']]))
    ok('cropped cover thumbnail is portrait (~comic ratio)',all(0.55<e['cw']/e['ch']<0.75 for e in (e1,e2,e3)),json.dumps([(e['cw'],e['ch']) for e in (e1,e2,e3)]))
    ok('reader page aspect taken from page 2 for wide covers',0.6<e1['aspect']<0.7,str(e1['aspect']))
    n1=recs['Nightfall 01']; ok('normal portrait cover stays full page',n1['crop']['side']=='full' and n1['crop']['w']>0.95,json.dumps(n1['crop']))
    # Edit sheet: Cover = Full page, then back to Auto
    sheet(pg,'Ember Road 01','aEdit'); pg.wait_for_selector('#eCover'); ok('Edit sheet has Cover: Auto / Right half / Left half / Full page',pg.eval_on_selector_all('#eCover button','b=>b.map(x=>x.textContent)')==['Auto','Right half','Left half','Full page'] and pg.locator('#eCover button.on').text_content()=='Auto')
    pg.click('#eCover [data-v=full]'); shot(pg,'34-edit-cover-mode'); pg.click('#eSave'); pg.wait_for_function("document.querySelector('.toast')&&document.querySelector('.toast').textContent.includes('Cover updated')",timeout=20000)
    r1=pg.evaluate(RECS)['Ember Road 01']; ok('Cover = Full page regenerates a wide thumbnail',r1['mode']=='full' and r1['crop']['side']=='full' and r1['crop']['w']>0.99 and r1['cw']>r1['ch'],json.dumps(r1))
    pg.wait_for_timeout(2700); sheet(pg,'Ember Road 01','aEdit'); pg.click('#eCover [data-v=left]'); pg.click('#eSave'); pg.wait_for_function("document.querySelector('.toast')&&document.querySelector('.toast').textContent.includes('Cover updated')",timeout=20000)
    r1=pg.evaluate(RECS)['Ember Road 01']; ok('Cover = Left half',r1['crop']['side']=='left' and r1['crop']['x']+r1['crop']['w']<=0.5001,json.dumps(r1['crop']))
    pg.wait_for_timeout(2700); sheet(pg,'Ember Road 01','aEdit'); pg.click('#eCover [data-v=auto]'); pg.click('#eSave'); pg.wait_for_function("document.querySelector('.toast')&&document.querySelector('.toast').textContent.includes('Cover updated')",timeout=20000)
    r1=pg.evaluate(RECS)['Ember Road 01']; ok('Cover = Auto again -> right half',r1['crop']['side']=='right' and r1['mode']=='auto')
    # migration: an old-style record (no crop info, coverV<2) is regenerated on next launch
    pg.evaluate('''(id)=>new Promise(res=>{const r=indexedDB.open('comic-reader');r.onsuccess=()=>{const st=r.result.transaction('comics','readwrite').objectStore('comics');const g=st.get(id);g.onsuccess=()=>{const c=g.result;delete c.coverCrop;delete c.coverV;delete c.coverMode;st.put(c).onsuccess=()=>res(1);};};})''',e3['id'])
    pg.reload(); pg.wait_for_selector('html[data-ready]')
    pg.wait_for_function(f'''(async()=>{{const r=indexedDB.open('comic-reader');await new Promise(x=>r.onsuccess=x);const c=await new Promise(x=>{{const q=r.result.transaction('comics').objectStore('comics').get('{e3['id']}');q.onsuccess=()=>x(q.result)}});return c.coverV===2&&c.coverCrop&&c.coverCrop.side==='right'}})()''',timeout=30000,polling=500)
    ok('old covers re-generated on next launch (migration)',pg.evaluate("localStorage.getItem('cr.coverMig')")=='2')
    # screenshots: carousel + rows with the cropped wide covers, library grid
    open_comic(pg,'Ember Road 02'); back(pg); open_comic(pg,'Ember Road 01'); back(pg)
    tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(700); shot(pg,'32-home-wide-covers')
    pg.evaluate("(()=>{const h=[...document.querySelectorAll('.row-h h2')].find(e=>e.textContent==='Ember Road'); const sc=document.querySelector('#homeScroll'); sc.scrollTop=h.closest('.row').offsetTop-80;})()"); pg.wait_for_timeout(400); shot(pg,'33-home-ember-row')
    tab(pg,'library'); pg.click('#sortBtn'); pg.click('.menu button:has-text("Title")'); pg.wait_for_timeout(300); pg.evaluate("document.querySelector('#libScroll').scrollTop=0"); pg.wait_for_timeout(300); shot(pg,'35-library-wide-covers')
    pg.click('#sortBtn'); pg.click('.menu button:has-text("Recent")'); pg.wait_for_timeout(200)

    # ---- delete + settings ----
    pg.set_viewport_size({'width':820,'height':1180}); tab(pg,'library'); n0=pg.locator('.lc').count()
    sheet(pg,'Iron Tide 05','aDelete'); pg.wait_for_selector('#confirmOk'); shot(pg,'23-delete-confirm'); pg.click('#confirmOk'); pg.wait_for_timeout(400)
    ok('delete with confirm',pg.locator('.lc').count()==n0-1)
    pg.click('#settingsBtn'); pg.wait_for_selector('.stor'); pg.wait_for_timeout(200); shot(pg,'24-settings'); ok('settings shows storage used',' MB' in pg.inner_text('.stor')); pg.keyboard.press('Escape')

    # ---- Import Entire Drive Folder (Drive API mocked via routes; SW blocked so routes apply in every engine) ----
    c2=b.new_context(viewport={'width':820,'height':1180},has_touch=True,device_scale_factor=2,service_workers='block'); p2=c2.new_page()
    p2.on('pageerror',lambda e:errors.append('pageerror(folder): '+str(e)))
    p2.on('console',lambda m: errors.append(f'console(folder): {m.text}') if m.type=='error' and not GRE.search(m.text) and not GRE.match((m.location or {}).get('url','') or '') else None)
    c2.route(GRE,lambda r:r.abort())
    seen=[]
    FOLD={'0ByhXYqPJBamsS2h2X01uS29uaU0':[{'id':'f-nf2','name':'Nightfall_02.pdf','size':str(os.path.getsize(f'{T}/Nightfall_02.pdf')),'mimeType':'application/pdf'},
              {'id':'f-gh','name':'Glass_Harbor.pdf','size':str(os.path.getsize(f'{T}/Glass_Harbor.pdf')),'mimeType':'application/pdf'},
              {'id':'sub-asm','name':'Amazing Spiderman','mimeType':'application/vnd.google-apps.folder','resourceKey':'0-subkey'}],
          'sub-asm':[{'id':'f-a1','name':'ASM_001.pdf','size':str(os.path.getsize(f'{T}/Iron_Tide_01.pdf')),'mimeType':'application/pdf','resourceKey':'0-filekey'},
                     {'id':'f-a2','name':'ASM_002.pdf','size':str(os.path.getsize(f'{T}/Iron_Tide_02.pdf')),'mimeType':'application/pdf'}]}
    SRC={'f-nf2':'Nightfall_02.pdf','f-gh':'Glass_Harbor.pdf','f-a1':'Iron_Tide_01.pdf','f-a2':'Iron_Tide_02.pdf'}
    def drive_api(route):
        from urllib.parse import urlparse, parse_qs
        rq=route.request; u=urlparse(rq.url); q=parse_qs(u.query); h=rq.headers; seen.append((u.path,h.get('authorization'),h.get('x-goog-drive-resource-keys')))
        cors={'Access-Control-Allow-Origin':'*'}
        if u.path=='/drive/v3/files':
            fid=q['q'][0].split("'")[1]; return route.fulfill(status=200,headers=cors,content_type='application/json',body=json.dumps({'files':FOLD.get(fid,[])}))
        fid=u.path.rsplit('/',1)[1]
        if q.get('alt')==['media']: return route.fulfill(status=200,headers=cors,content_type='application/pdf',path=f'{T}/{SRC[fid]}')
        return route.fulfill(status=200,headers=cors,content_type='application/json',body=json.dumps({'name':'Comics'}))
    c2.route(re.compile(r'https://www\.googleapis\.com/drive/v3/files.*'),drive_api)
    p2.goto(URL); p2.wait_for_selector('html[data-ready]')
    p2.set_input_files('#fileIn',[f'{T}/Nightfall_02.pdf']); p2.wait_for_function('document.querySelectorAll(".lc").length==1 && !document.querySelector(".toast .tb")',timeout=60000)
    ok('default Drive folder from config',p2.evaluate('__cr.drive.folder().id')=='0ByhXYqPJBamsS2h2X01uS29uaU0')
    p2.evaluate("__cr.drive._setToken('test-token')"); p2.click('#importBtn'); p2.click('#miFolder')
    p2.wait_for_selector('.modal.ckm #ckGo'); p2.wait_for_timeout(300)
    ok('folder listing sends resource-key header',any(x[0]=='/drive/v3/files' and x[2] and '0ByhXYqPJBamsS2h2X01uS29uaU0/0-jrOuagpWxzlX6dXlyqbz5Q' in x[2] and x[1]=='Bearer test-token' for x in seen),json.dumps(seen[:3]))
    ok('subfolder listed with its own resource key too',any(x[0]=='/drive/v3/files' and x[2] and 'sub-asm/0-subkey' in x[2] for x in seen))
    ok('checklist groups subfolder as series',p2.inner_text('.ckg').strip().lower()=='amazing spiderman')
    ok('checklist: 4 PDFs, duplicate marked + unchecked, others checked',p2.locator('.ckr').count()==4 and p2.locator('.ckr.dup input:checked').count()==0 and 'In library' in p2.inner_text('.ckr.dup') and p2.locator('.ckr input:checked').count()==3 and p2.inner_text('#ckGo')=='Import 3')
    shot(p2,'30-drive-folder-checklist')
    p2.click('#ckNone'); ok('Select None disables Import',p2.locator('#ckGo').is_disabled())
    p2.click('#ckAll'); ok('Select All re-selects all new files',p2.inner_text('#ckGo')=='Import 3')
    p2.locator('.ckr').nth(1).click(); ok('toggle one file off',p2.inner_text('#ckGo')=='Import 2')
    p2.locator('.ckr').nth(1).click(); p2.click('#ckGo')
    p2.wait_for_function('document.querySelectorAll(".lc").length==4',timeout=60000)
    sers=p2.evaluate("(async()=>{const r=indexedDB.open('comic-reader');await new Promise(x=>r.onsuccess=x);const all=await new Promise(x=>{const q=r.result.transaction('comics').objectStore('comics').getAll();q.onsuccess=()=>x(q.result)});return all.map(c=>[c.title,c.series,c.driveId||''])})()")
    asm=[x for x in sers if x[1]=='Amazing Spiderman']
    ok('folder import: subfolder files get series = subfolder name',len(asm)==2,json.dumps(sers))
    dl=[x for x in seen if x[0]=='/drive/v3/files/f-a1']
    ok('download sends token + file/folder resource keys',dl and dl[-1][1]=='Bearer test-token' and 'f-a1/0-filekey' in (dl[-1][2] or '') and 'sub-asm/0-subkey' in (dl[-1][2] or ''),json.dumps(dl))
    p2.wait_for_timeout(1800)
    # Settings: change folder by pasting a link
    p2.evaluate("document.querySelectorAll('.mwrap').forEach(m=>m.remove())")
    p2.click('#settingsBtn'); p2.wait_for_selector('#sFolder'); p2.fill('#sFolder','https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrSt?resourcekey=0-XyZ123&usp=sharing'); p2.click('#sFolderSave'); p2.wait_for_timeout(200)
    f=p2.evaluate('__cr.drive.folder()'); ok('Settings: paste folder link -> id + resourcekey parsed',f['id']=='1AbCdEfGhIjKlMnOpQrSt' and f['resourceKey']=='0-XyZ123',json.dumps(f))
    shot(p2,'31-settings-drive-folder')
    p2.keyboard.press('Escape'); p2.click('#settingsBtn'); p2.wait_for_selector('#sFolderReset'); p2.click('#sFolderReset'); p2.wait_for_timeout(200)
    ok('Settings: reset to default folder',p2.evaluate('__cr.drive.folder().id')=='0ByhXYqPJBamsS2h2X01uS29uaU0')
    c2.close()
    b.close()
ok('no console errors / page errors',not errors,'\n'.join(errors[:10]))
print(f'{sum(res)}/{len(res)} passed')
sys.exit(0 if all(res) else 1)
