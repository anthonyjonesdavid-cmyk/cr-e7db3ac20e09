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
EDGE="""(()=>{const C=__cr.CF; C.stop(); C.pos=Math.min(10,C.items.length-1); C.layout(); const vw=innerWidth;
  const r=[...document.querySelectorAll('#cf .cf-item')].filter(e=>e.style.display!=='none').map(e=>e.getBoundingClientRect());
  const L=Math.min(...r.map(b=>b.left)), R=Math.max(...r.map(b=>b.right)); C.pos=0; C.layout(); return {L:Math.round(L),R:Math.round(R),vw,n:r.length}})()"""
def edge_ok(pg,lab):
    e=pg.evaluate(EDGE); ok(f'{lab}: carousel side stacks reach/bleed past both screen edges',e['L']<=0 and e['R']>=e['vw'] and e['n']<=21,str(e))
def bar_black(pg,lab,sel,clip_fn):
    """computed style + pixel check: bar region (incl. emulated 44px status-bar inset) is pure #000 while content is scrolled under it"""
    st=pg.evaluate(f"""(()=>{{const e=document.querySelector('{sel}'); const c=getComputedStyle(e); return {{bg:c.backgroundColor,bf:c.backdropFilter||c.webkitBackdropFilter||'none',op:c.opacity}}}})()""")
    from PIL import Image; import io
    x,y,w,h=clip_fn(); im=Image.open(io.BytesIO(pg.screenshot(clip={'x':x,'y':y,'width':w,'height':h}))).convert('RGB')
    mx=max(max(px) for px in im.getdata())
    ok(f'{lab}: top bar solid #000 (no blur/translucency), nothing shows through',st['bg']=='rgb(0, 0, 0)' and st['bf'] in ('none','') and st['op']=='1' and mx<=2,f'{st} maxpx={mx}')
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
    ok('no now-reading pill on Home',pg.locator('#nowPill').count()==0)
    shot(pg,'10-home-portrait')
    ok('status-bar-style black + theme-color #000',pg.evaluate("document.querySelector('meta[name=apple-mobile-web-app-status-bar-style]').content")=='black' and pg.evaluate("document.querySelector('meta[name=theme-color]').content").lower() in ('#000','#000000'))
    pg.evaluate("document.documentElement.style.setProperty('--sat','44px'); __cr.CF.size()"); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('#homeScroll').scrollTop=700"); pg.wait_for_timeout(300); shot(pg,'13-home-scrolled-under-bar')
    bar_black(pg,'Home (scrolled, 44px inset)','.topbar',lambda:(70,0,170,44+8))
    tab(pg,'library'); pg.evaluate("document.querySelector('#libScroll').scrollTop=600"); pg.wait_for_timeout(300); shot(pg,'14-library-scrolled-under-bar')
    bar_black(pg,'Library (scrolled, 44px inset)','.topbar',lambda:(70,0,170,44+8))
    bar_black(pg,'Library search bar area','.libbar',lambda:(pg.locator('.libbar').bounding_box()['x']+2,pg.locator('.libbar').bounding_box()['y']+1,6,8))
    open_comic(pg,'Nightfall 01'); pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(400); shot(pg,'15-reader-bar-solid')
    bar_black(pg,'Reader toolbar (44px inset)','.rbar.top',lambda:(0,0,40,44))
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(400)
    from PIL import Image; import io
    im=Image.open(io.BytesIO(pg.screenshot(clip={'x':0,'y':0,'width':820,'height':44}))).convert('RGB'); mx=max(max(px) for px in im.getdata())
    ok('Reader: status-bar inset stays solid black when toolbar is hidden',mx<=2,f'maxpx={mx}')
    pg.evaluate('__cr.toggleUI(true)'); back(pg)
    pg.evaluate("document.documentElement.style.removeProperty('--sat'); __cr.CF.size()"); tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(400)
    sharp=pg.evaluate("(()=>{const C=__cr.CF; const chk=()=>[...document.querySelectorAll('#cf .cf-item')].filter(e=>e.style.display!=='none').every(e=>{const f=getComputedStyle(e.firstChild).filter, g=getComputedStyle(e).filter; return (f==='none'||!f)&&(g==='none'||!g)}); const rest=chk(); C.moving(true); C.pos=1.4; C.layout(); const mv=chk(); C.moving(false); C.pos=0; C.layout(); const dim=+document.querySelector('#cf .cf-item[data-i=\"1\"] .dim').style.opacity; return {rest,mv,dim}})()")
    ok('carousel covers sharp (no blur) at rest and while moving, light dim on sides',sharp['rest'] and sharp['mv'] and 0.15<=sharp['dim']<=0.45,str(sharp))
    edge_ok(pg,'portrait')
    hr=pg.evaluate("(()=>{const h=[...document.querySelectorAll('#homeScroll .row-h')]; return {t:h.map(e=>e.querySelector('h2').textContent),k:h.map(e=>e.dataset.kind)}})()")
    ok('Home rows = Recently Added then one per series (no Unread/Finished)',hr['t'][0]=='Recently Added' and all(k=='series' for k in hr['k'][1:]) and len(hr['k'])>2 and 'Unread' not in hr['t'] and 'Finished' not in hr['t'],str(hr['t']))
    pg.evaluate("document.querySelector('#homeScroll').scrollTop=520"); pg.wait_for_timeout(300); shot(pg,'11-home-rows-portrait')
    sx=pg.evaluate("(()=>{const r=document.querySelectorAll('.row-s')[0]; r.scrollLeft=300; return r.scrollLeft})()"); ok('rows scroll horizontally (free scroll)',sx>0,str(sx))
    pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(300)
    # carousel: swipe with momentum + snap, mid-swipe, tap side, tap center
    t1=pg.evaluate(CFSWIPE,{'dx':-150,'steps':6,'dt':16,'noup':False}); pos=pg.evaluate('__cr.CF.pos')
    ok('carousel swipe moves + snaps to a whole cover',t1!='Nightfall 01' and abs(pos-round(pos))<1e-6 and pos>=1,f'{t1} pos={pos}')
    pg.evaluate(CFSWIPE,{'dx':-700,'steps':5,'dt':12,'noup':False}); pos2=pg.evaluate('__cr.CF.pos'); ok('fast fling carries momentum further',pos2>=pos+2,f'{pos}->{pos2}')
    pg.wait_for_function('!__cr.CF.raf',timeout=5000)
    cfs=pg.evaluate('''(()=>{const C=__cr.CF, L=C.items, total=+document.querySelector('.row-h .n').textContent;
      const ip=c=>(c.progress||0)<1&&(c.lastRead||(c.progress||0)>0); let phase=0, okOrder=true, prev=null;
      L.forEach(c=>{ const ph=ip(c)?0:c.lastRead?1:2; if(ph<phase) okOrder=false;
        if(ph===phase&&prev){ if(ph<2&&c.lastRead>prev.lastRead) okOrder=false; if(ph===2&&c.added>prev.added) okOrder=false; } phase=ph; prev=c; });
      return {n:L.length,total,uniq:new Set(L.map(c=>c.id)).size,okOrder,first:L[0].title,ph:L.map(c=>ip(c)?0:c.lastRead?1:2).join('')}})()''')
    ok('carousel holds up to 50 (all comics when fewer), no duplicates',cfs['n']==min(50,cfs['total']) and cfs['uniq']==cfs['n'],str(cfs))
    ok('carousel order: in-progress (recent first) > other read > newest unread',cfs['okOrder'] and cfs['first']=='Nightfall 01',cfs['ph'])
    pg.reload(); pg.wait_for_selector('html[data-ready]'); tab(pg,'home'); pg.wait_for_function('__cr.CF.items.length>0'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(600)   # fresh mount
    v=pg.evaluate('''(()=>{const k=[...document.querySelectorAll('#cf .cf-item')]; return {shown:k.filter(e=>e.style.display!=='none').map(e=>+e.dataset.i), loaded:k.filter(e=>e.firstChild.getAttribute('src')).map(e=>+e.dataset.i)}})()''')
    ok('carousel virtualized: only covers within ±10 of centre displayed',max(v['shown'])<=10 and (cfs['n']<=11 or 11 not in v['shown']),str(v['shown']))
    ok('carousel covers lazy-loaded (only near centre have src)',max(v['loaded'])<=12 and (cfs['n']<=13 or len(v['loaded'])<cfs['n']),str(v['loaded']))
    pg.evaluate(CFSWIPE,{'dx':-320,'steps':5,'dt':14,'noup':False}); pg.wait_for_function('!__cr.CF.raf',timeout=5000); fl=pg.evaluate('__cr.CF.pos')
    ok('one flick travels several covers',fl>=min(5,cfs['n']-1),str(fl))
    v2=pg.evaluate('''(()=>{const k=[...document.querySelectorAll('#cf .cf-item')], p=Math.round(__cr.CF.pos); return k.filter(e=>e.style.display!=='none').every(e=>Math.abs(+e.dataset.i-p)<=10) && !!k[p].firstChild.getAttribute('src')})()''')
    ok('after flick: window follows centre and its cover is loaded',v2)
    pg.evaluate('__cr.CF.to(0,10)'); pg.wait_for_timeout(300)
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
    pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(300)
    ok('last-read comic becomes carousel centre (resume point)',pg.evaluate('__cr.CF.items[Math.round(__cr.CF.pos)].title')==want and round(pg.evaluate('__cr.CF.pos'))==0,want)
    cb=pg.locator('#cf .cf-item[data-i="0"]').bounding_box(); pg.mouse.click(cb['x']+cb['width']/2,cb['y']+cb['height']/2); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg)
    ok('tapping centre cover resumes last comic',pg.text_content('#rTitle')==want); back(pg)
    tab(pg,'library'); pg.wait_for_timeout(200); ok('no now-reading pill in Library',pg.locator('#nowPill').count()==0)
    pad=pg.evaluate("parseFloat(getComputedStyle(document.querySelector('#libGrid')).paddingBottom)"); ok('no bottom space reserved for a pill',pad<40,str(pad))
    tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(200)
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
    ok('series heading opens series grid',pg.locator('.lc').count()==3 and pg.evaluate("document.querySelector('#shelf').classList.contains('scoped')"))
    cl=pg.evaluate('''(()=>{const vis=s=>{const e=document.querySelector(s); return !!e&&e.getClientRects().length>0&&getComputedStyle(e).display!=='none';};
      const tb=document.querySelector('.topbar').getBoundingClientRect(), h=document.querySelector('#seriesHero .hero'), g=document.querySelector('#libGrid').getBoundingClientRect();
      return {search:vis('#q'),sort:vis('#sortBtn'),chips:vis('#chips'),scope:!!document.querySelector('.chip.scope'),rename:!!document.querySelector('#seriesEdit'),merge:!!document.querySelector('#seriesMerge'),
        filters:[...document.querySelectorAll('#chips [data-act=filter]')].some(e=>e.getClientRects().length>0),back:vis('#libBack'),gear:vis('#settingsBtn'),seg:vis('#tabs'),plus:vis('#importBtn'),
        heroTop:h?Math.round(h.getBoundingClientRect().top):-1,tbBottom:Math.round(tb.bottom),gridBelow:h?g.top>=h.getBoundingClientRect().bottom-1:false,az:vis('#azIndex')}})()''')
    ok('series page: no search / sort / series chip / Rename / Merge / filter chips',not any(cl[k] for k in ('search','sort','chips','scope','rename','merge','filters','az')),json.dumps(cl))
    ok('series page: top bar keeps Home/Library + "+", back chevron replaces the gear',cl['seg'] and cl['plus'] and cl['back'] and not cl['gear'],json.dumps(cl))
    ok('series page: carousel sits right under the top bar, grid below',abs(cl['heroTop']-cl['tbBottom'])<=1 and cl['gridBelow'],json.dumps(cl))
    shot(pg,'59-series-page-clean')
    pg.click('#libBack'); pg.wait_for_timeout(200)
    ok('back chevron returns to the full Library (search/sort/filters back, gear back)',pg.locator('.lc').count()==len(FILES) and pg.is_visible('#q') and pg.is_visible('#sortBtn') and pg.locator('#chips [data-act=filter]').count()==4 and pg.is_visible('#settingsBtn') and not pg.is_visible('#libBack') and pg.locator('#scf').count()==0)
    tab(pg,'home'); pg.locator('.row-h',has_text='The Hollow').click(); pg.wait_for_timeout(300); tab(pg,'library'); pg.wait_for_timeout(200)
    ok('Library tab from a series page shows the full Library',pg.locator('.lc').count()==len(FILES) and pg.is_visible('#q'))
    tab(pg,'home'); pg.locator('.row').first.locator('.seeall').click(); pg.wait_for_timeout(300); ok('See all opens library',pg.is_visible('#libGrid') and pg.locator('.lc').count()==len(FILES))

    # ---- landscape ----
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(400)
    cols=pg.evaluate("getComputedStyle(document.querySelector('#libGrid')).gridTemplateColumns.split(' ').length"); ok('library grid: 7 columns landscape',cols==7,str(cols)); shot(pg,'15-library-landscape')
    tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.evaluate('__cr.CF.to(0,10)'); pg.wait_for_timeout(500); shot(pg,'16-home-landscape'); g=pg.evaluate("(()=>{const i=Math.round(__cr.CF.pos); const c=document.querySelector('#cf .cf-item[data-i=\"'+i+'\"]').getBoundingClientRect(); return document.querySelector('.row-h').getBoundingClientRect().top-c.bottom})()"); ok('landscape: rows close under carousel',20<g<80,str(round(g))); edge_ok(pg,'landscape')
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
    # ---- PORTRAIT HALF PAGES (default for fold comics): one half at a time, standard page turn ----
    HS="(()=>{const R=__cr.R, el=document.querySelector('.view .pg'), r=el.getBoundingClientRect(), st=document.querySelector('#stage').getBoundingClientRect(); return {half:R.half,n:R.views.length-1,sheets:R.n,vi:R.vi,s:R.views[R.vi][0],h:R.vh[R.vi]||null,dh:el.dataset.half||null,pw:r.width,ph:r.height,sw:st.width,sh:st.height,ar:R.aspects[1],txt:document.querySelector('#pgText').textContent,max:+document.querySelector('#scrub').max}})()"
    open_comic(pg,'Twin Moon 01'); pg.wait_for_timeout(400); h=pg.evaluate(HS)
    ok('fold comic in portrait opens in half-page mode, cover sheet shows only the cover half',h['half'] and h['vi']==0 and h['s']==0 and h['h']=='R' and h['dh']=='R' and h['n']==1+2*(h['sheets']-1),json.dumps(h))
    lum=pg.evaluate("(()=>{const c=document.querySelector('.view .pg canvas'); const x=c.getContext('2d').getImageData(0,0,c.width,c.height).data; let t=0; for(let i=0;i<x.length;i+=4*97) t+=x[i]+x[i+1]+x[i+2]; return t/(x.length/(4*97))/3})()")
    ok('cover half is the art, not the black back cover',lum>25,f'{lum:.1f}')
    ok('page counter + scrubber count halves',h['txt']==f"1 / {h['n']}" and h['max']==h['n'],json.dumps(h))
    shot(pg,'44-half-cover-portrait')
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(900); h1=pg.evaluate(HS); pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(900); h2=pg.evaluate(HS)
    ok('reading order: sheet 1 left half, then right half',(h1['s'],h1['h'],h2['s'],h2['h'])==(1,'L',1,'R'),json.dumps([h1,h2]))
    ok('half fitted to the screen like a single page',(abs(h2['pw']-h2['sw'])<=2 or abs(h2['ph']-h2['sh'])<=2) and abs(h2['pw']/h2['ph']-h2['ar']/2)<0.02,json.dumps(h2))
    shot(pg,'45-half-page-portrait')
    x0,y0,W,H=geo(pg)
    pg.evaluate(GEST,{'x':x0+W*0.9,'y':y0+H*0.5,'pts':[[-W*0.06*i,0,30] for i in range(1,8)],'hold':0,'noup':True}); pg.wait_for_timeout(150)
    mt=pg.evaluate("(()=>{const f=__cr.flip; return {mode:f&&f.mode,p:f&&f.p,faces:[...document.querySelectorAll('.flip .face')].map(e=>e.dataset.p+(e.dataset.half||'')+(e.classList.contains('front')?'*':''))}})()")
    shot(pg,'46-half-mid-turn')
    ok('turn between halves uses the standard page-turn (mid-turn)',mt['mode']=='half' and 0.1<mt['p']<0.95 and '1R*' in mt['faces'] and '2L' in mt['faces'],json.dumps(mt))
    pg.evaluate(UP,[x0+W*0.3,y0+H*0.5]); pg.wait_for_timeout(900); h3=pg.evaluate(HS); ok('turn completes to next sheet left half',(h3['s'],h3['h'])==(2,'L'),json.dumps(h3))
    flicks(pg,'half portrait')
    pg.evaluate("(()=>{const s=document.querySelector('#scrub'); s.value=8; s.dispatchEvent(new Event('input')); s.dispatchEvent(new Event('change'));})()"); pg.wait_for_timeout(700); h4=pg.evaluate(HS)
    ok('scrubber jumps by halves',h4['vi']==7 and (h4['s'],h4['h'])==(4,'L') and h4['txt']==f"8 / {h4['n']}",json.dumps(h4))
    z=pg.evaluate(PINCH,{'cx':x0+W/2,'cy':y0+H/2,'d0':100,'d1':260}); pg.wait_for_timeout(1500)
    zh=pg.evaluate("(()=>{const d=document.querySelector('.view .pg'); const c=d.querySelector('canvas'); return {hi:d.dataset.hi||null,half:d.dataset.half,cw:c.width,w:+d.dataset.w}})()")
    ok('zoom works on the half (sharper half re-render)',z>1.5 and zh['half']=='L' and zh['hi'] and zh['cw']>zh['w']*1.4,json.dumps([z,zh]))
    pg.evaluate(TAP,{'x':x0+W*0.5,'y':y0+H*0.5,'n':2}); pg.wait_for_timeout(500)
    # rotation keeps the place: half <-> sheet
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(600); wait_render(pg); l=pg.evaluate(HS)
    ok('rotate to landscape: same sheet, full wide sheet (fold), no halves',not l['half'] and l['s']==4 and l['dh'] is None and l['pw']>l['ph']*1.2,json.dumps(l))
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(600); wait_render(pg); b2=pg.evaluate(HS)
    ok('rotate back to portrait: same half restored (sheet 4, left half)',b2['half'] and (b2['s'],b2['h'],b2['vi'])==(4,'L',7),json.dumps(b2))
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(600); wait_render(pg); pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(900)
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(600); wait_render(pg); b3=pg.evaluate(HS)
    ok('turn in landscape then rotate: next sheet opens at its first half',(b3['s'],b3['h'])==(5,'L'),json.dumps(b3))
    # RTL: right half first
    pg.evaluate('__cr.toggleUI(true)'); pg.click('#rRtl'); pg.wait_for_timeout(400); pg.evaluate('__cr.toggleUI(false)'); r1=pg.evaluate(HS)
    pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(900); r2=pg.evaluate(HS)
    ok('RTL half pages: same half kept on toggle; next sheet starts with its right half',(r1['s'],r1['h'])==(5,'L') and (r2['s'],r2['h'])==(6,'R') and pg.evaluate('[__cr.R.vh[1],__cr.R.vh[2]]')==['R','L'],json.dumps([r1,r2]))
    pg.evaluate('__cr.toggleUI(true)'); pg.click('#rRtl'); pg.wait_for_timeout(400); pg.evaluate('__cr.toggleUI(false)')
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(900); keep=pg.evaluate(HS); back(pg); pg.wait_for_timeout(300)
    open_comic(pg,'Twin Moon 01'); pg.wait_for_timeout(400); ro=pg.evaluate(HS)
    ok('reopening resumes the same half',(ro['s'],ro['h'])==(keep['s'],keep['h']),json.dumps([keep,ro])); back(pg)
    sheet(pg,'Twin Moon 01','aEdit'); pg.wait_for_selector('#eFoldP')
    ok('Edit sheet (fold comic): Portrait = Half pages / Full sheet, default Half pages',pg.is_visible('#eFoldP') and pg.eval_on_selector_all('#eFoldP button','b=>b.map(x=>x.textContent)')==['Half pages','Full sheet'] and pg.locator('#eFoldP button.on').text_content()=='Half pages')
    shot(pg,'47-edit-portrait-half'); pg.click('#eFoldP [data-v=full]'); pg.click('#eSave'); pg.wait_for_timeout(300)
    sheet(pg,'Nightfall 03','aEdit'); pg.wait_for_selector('#eTurn'); ok('Portrait option hidden for standard comics',not pg.is_visible('#eFoldP')); pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    open_comic(pg,'Twin Moon 01'); s=state(pg); ok('Portrait = Full sheet: whole wide sheet in portrait',not pg.evaluate('__cr.R.half'),json.dumps(s))
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
        sheet(pg,t,'aEdit'); pg.click('#eTurn [data-v=auto]')
        if t=='Twin Moon 01': pg.click('#eFoldP [data-v=half]')
        pg.click('#eSave'); pg.wait_for_timeout(250)
    open_comic(pg,'Twin Moon 01'); ok('back to Auto -> fold',pg.evaluate('__cr.R.fold')==True); ok('back to Half pages in portrait',pg.evaluate('__cr.R.half')==True); back(pg)
    # ---- REGRESSION: no flicker after a turn lands (landscape 2-up + fold, after portrait halves + rotation, normal + slow renders) ----
    STAB="""async ({ms,go})=>{ const R=__cr.R; const out={frames:0,blank:0,changes:0,overlay:0,seq:[]}; let last=null; const t0=performance.now();
      if(go) __cr.go(go);
      await new Promise(res=>{ const tick=()=>{ const ov=document.querySelector('.flip'); const v=R.viewEl, vis=v&&v.style.visibility!=='hidden';
        const pg=v?[...v.querySelectorAll('.pg')].map(e=>e.dataset.p||'-').join(','):'';
        const unpainted=v?[...v.querySelectorAll('.pg:not(.blank)')].some(e=>!e.querySelector('canvas')):true;
        if(!ov&&(!vis||unpainted)) out.blank++; if(ov) out.overlay++;
        if(!ov){ if(last!==null&&pg!==last){ out.changes++; out.seq.push(pg); } last=pg; }
        out.frames++; if(performance.now()-t0<ms) requestAnimationFrame(tick); else res(); }; requestAnimationFrame(tick); });
      out.final=last; return out; }"""
    LANDCHK="""async ()=>{ const R=__cr.R; __cr.go(-1,2400); const tgt=new Set(); const t=R.vi+1;
      await new Promise(res=>{ const tick=()=>{ const f=__cr.flip; if(f&&f.p>0.97){ res(); return; } requestAnimationFrame(tick); }; requestAnimationFrame(tick); });
      const tv=R.views[__cr.flip.t].filter(x=>x!=null).map(String);
      const faces=[...document.querySelectorAll('.flip .face')].filter(e=>tv.includes(e.dataset.p)&&!e.classList.contains('front')).map(e=>{ const c=e.querySelector('canvas'); const r=e.getBoundingClientRect(); return {p:e.dataset.p,back:e.classList.contains('back'),half:e.classList.contains('half'),cw:c&&c.width,ch:c&&c.height,x:Math.round(r.left),w:Math.round(r.width),h:Math.round(r.height)}; });
      await new Promise(res=>{ const tick=()=>{ if(!__cr.flip&&!document.querySelector('.flip')){ res(); return; } requestAnimationFrame(tick); }; requestAnimationFrame(tick); });
      const view=[...R.viewEl.querySelectorAll('.pg')].map(e=>{ const c=e.querySelector('canvas'); const r=e.getBoundingClientRect(); return {p:e.dataset.p,cw:c&&c.width,ch:c&&c.height,x:Math.round(r.left),w:Math.round(r.width),h:Math.round(r.height)}; });
      return {faces,view}; }"""
    def stable(tag,expect_overlay=True,slow=0):
        if slow: pg.evaluate(f'window.__crSlow={slow}')
        r=pg.evaluate(STAB,{'ms':3000,'go':-1})
        if slow: pg.evaluate('window.__crSlow=0')
        ok(f'{tag}: no blank/flash frame after the turn lands, page stays put for 3s',r['blank']==0 and r['changes']==0 and r['frames']>60 and (r['overlay']>=1 or not expect_overlay),json.dumps({k:r[k] for k in ('frames','blank','changes','overlay','final','seq')}))
        return r
    def same_render(tag):
        r=pg.evaluate(LANDCHK); v={x['p']:x for x in r['view']}
        good=bool(r['faces']) and all(f['p'] in v and (f['cw']==v[f['p']]['cw'] or (f['half'] and abs(2*f['cw']-v[f['p']]['cw'])<=1)) and f['ch']==v[f['p']]['ch'] and (f['back'] or f['half'] or (abs(f['x']-v[f['p']]['x'])<=1 and abs(f['w']-v[f['p']]['w'])<=1 and abs(f['h']-v[f['p']]['h'])<=1)) for f in r['faces'])
        ok(f'{tag}: last frame of the turn uses the same render + position as the settled page',good,json.dumps(r))
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(400)
    open_comic(pg,'Nightfall 04'); pg.evaluate('__cr.jumpTo(5)'); wait_render(pg); pg.wait_for_timeout(600)
    ok('landscape standard comic is 2-up',state(pg)['spread'] and state(pg)['len']==2)
    for k in range(3): stable(f'2-up landscape turn {k+1}')
    same_render('2-up landscape')
    sp=pg.evaluate("(()=>{const g=__cr.R.views.slice(1,6).map(v=>[...document.querySelectorAll('.view .pg')].length); const s=new Set([...document.querySelectorAll('.view .pg')].map(e=>e.style.width+'x'+e.style.height)); return [...s]})()")
    ok('2-up: both pages of a spread share one box size',len(sp)==1,str(sp))
    pg.evaluate('__cr.jumpTo(20)'); pg.wait_for_timeout(150); stable('2-up landscape turn with slow renders (500ms) just after a jump',slow=500)
    pg.wait_for_timeout(2500); back(pg)
    # fold comic: portrait halves first, rotate, then landscape turns
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(300); open_comic(pg,'Twin Moon 01'); pg.evaluate('__cr.jumpTo(3)'); wait_render(pg); pg.wait_for_timeout(500)
    stable('portrait half-page turn')
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(700); wait_render(pg)
    for k in range(2): stable(f'fold landscape turn after rotating {k+1}')
    same_render('fold landscape')
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(700); wait_render(pg); pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(700); wait_render(pg)
    stable('fold landscape turn after rotating twice')
    stable('fold landscape turn with slow renders (500ms)',slow=500); pg.wait_for_timeout(2500)
    back(pg); pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(300)
    # ---- end of comic: next-issue card / End page ----
    CARD="""(()=>{ const R=__cr.R, d=document.querySelector('.view .pg[data-p="'+R.n+'"]'); if(!d) return null; const c=d.querySelector('canvas'); if(!c) return {loading:true};
      const x=c.getContext('2d'), W=c.width, H=c.height, im=x.getImageData(0,0,W,H).data, bg=[im[0],im[1],im[2]];
      const diff=(i)=>Math.abs(im[i]-bg[0])+Math.abs(im[i+1]-bg[1])+Math.abs(im[i+2]-bg[2])>30;
      const rows=[]; for(let y=0;y<H;y++){ let n=0,l=W,r=-1,run=0,best=0; for(let xx=0;xx<W;xx++){ if(diff((y*W+xx)*4)){ n++; run++; if(run>best) best=run; if(xx<l) l=xx; r=xx; } else run=0; } rows.push([n,l,r,best]); }
      let t=-1,b=-1; for(let y=0;y<H;y++) if(rows[y][3]>Math.min(W,H)*0.3){ if(t<0) t=y; b=y; }       // cover = wide rows of content
      let gap=-1; for(let y=b+1;y<H;y++) if(rows[y][0]>0){ gap=y-b; break; }
      let cap=0, capL=W, capR=0; for(let y=b+2;y<H;y++) if(rows[y][0]>0){ cap++; capL=Math.min(capL,rows[y][1]); capR=Math.max(capR,rows[y][2]); }
      const r=c.getBoundingClientRect(), st=document.querySelector('#stage').getBoundingClientRect();
      return {gap,W,H,cssW:r.width,cssH:r.height,dpr:devicePixelRatio,bg,coverTop:t/H,coverBottom:b/H,coverH:(b-t)/H,capRows:cap,capL:capL/W,capR:capR/W,
        inView:r.left>=st.left-1&&r.right<=st.right+1&&r.top>=st.top-1&&r.bottom<=st.bottom+1,next:R.next&&R.next.title,view:R.views[R.vi],last:R.vi===R.views.length-1,n:R.n,pg:document.querySelector('#pgText').textContent}; })()"""
    def card(wait=True):
        if wait: pg.wait_for_function('(()=>{const d=document.querySelector(\'.view .pg[data-p="\'+__cr.R.n+\'"]\'); return !!(d&&d.querySelector("canvas"))})()',timeout=20000); pg.wait_for_timeout(300)
        return pg.evaluate(CARD)
    def to_end(title):
        open_comic(pg,title); pg.evaluate('__cr.jumpTo(__cr.R.n)'); return card()
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(300)
    c=to_end('Iron Tide 04')
    ok('end card (landscape 2-up): last page on the left, next-issue card on the right',c and c['last'] and c['view']==[c['n']-1,c['n']] and c['next']=='Iron Tide 05',json.dumps(c and {k:c[k] for k in ('view','n','next','last')}))
    ok('end card: cover large + sharp, caption under it, all on screen',c['coverH']>0.7 and c['capRows']>10 and c['coverBottom']<0.95 and c['inView'] and abs(c['W']-round(c['cssW']*c['dpr']))<=2,json.dumps(c))
    ok('end card: page counter ignores the card',c['pg'].endswith(f"{c['n']} / {c['n']}") and str(c['n']+1) not in c['pg'],c['pg'])
    pg.evaluate('__cr.go(1)'); pg.wait_for_timeout(900); ok('can turn back from the card',state(pg)['vi']==pg.evaluate('__cr.R.views.length')-2)
    pg.evaluate('__cr.go(-1)'); pg.wait_for_timeout(900); pg.evaluate('__cr.go(-1)')
    pg.wait_for_function("document.querySelector('#rTitle').textContent==='Iron Tide 05' && __cr.R.views.length>0",timeout=20000); wait_render(pg)
    ok('turning past the card opens the next issue at page 1',state(pg)['first']==0 and state(pg)['vi']==0,json.dumps(state(pg)))
    back(pg); tab(pg,'library'); pg.click('.chip[data-f=finished]'); pg.wait_for_timeout(200)
    ok('reaching the card marks the comic finished',pg.locator('.lc[data-title="Iron Tide 04"]').count()==1)
    pg.click('.chip[data-f=all]'); pg.wait_for_timeout(100)
    # End page (no later issue)
    c=to_end('Iron Tide 05')
    ok('End page when there is no next issue',c['next'] is None and pg.evaluate('!!__cr.R.endBtn') and c['coverH']<0.2,json.dumps(c))
    bx=pg.evaluate("(()=>{const c=document.querySelector('.view .pg[data-p=\"'+__cr.R.n+'\"] canvas').getBoundingClientRect(), b=__cr.R.endBtn; return [c.left+(b.x+b.w/2)*c.width, c.top+(b.y+b.h/2)*c.height]})()")
    pg.mouse.click(*bx); pg.wait_for_selector('#shelf:not(.hidden)',timeout=5000); ok('End page: Back to Library returns to the shelf',pg.is_visible('#shelf'))
    pg.wait_for_timeout(300)
    # portrait: the card is a page of its own
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(300)
    c=to_end('Iron Tide 04')
    ok('end card (portrait): its own page after the last page, cover centred',c['view']==[c['n']] and c['next']=='Iron Tide 05' and c['coverH']>0.7 and c['inView'] and abs((c['capL']+c['capR'])/2-0.5)<0.06,json.dumps(c))
    pg.evaluate('__cr.go(1)'); pg.wait_for_timeout(900); ok('portrait: page before the card is the last page',state(pg)['first']==c['n']-1)
    back(pg)
    # fold comics: landscape (wide sheets) + portrait halves
    pg.set_viewport_size({'width':1180,'height':820}); pg.wait_for_timeout(300)
    c=to_end('Twin Moon 01')
    ok('fold comic (landscape): card after the last sheet, next = Twin Moon 02',c['view']==[c['n']] and c['next']=='Twin Moon 02' and c['coverH']>0.7 and c['inView'],json.dumps(c))
    pg.evaluate('__cr.go(1)'); pg.wait_for_timeout(1000); pg.evaluate('__cr.go(-1)'); pg.wait_for_timeout(1000)
    ok('fold comic: fold turn onto the card lands on it',pg.evaluate('__cr.R.vi===__cr.R.views.length-1'))
    back(pg); pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(300)
    c=to_end('Twin Moon 01')
    ok('fold comic (portrait halves): card is its own page after the last half',c['view']==[c['n']] and pg.evaluate('__cr.R.half') and c['coverH']>0.7,json.dumps(c))
    pg.evaluate('__cr.go(-1)'); pg.wait_for_function("document.querySelector('#rTitle').textContent==='Twin Moon 02'",timeout=20000); wait_render(pg)
    ok('fold comic: turning past the card opens Twin Moon 02 at the start',state(pg)['first']==0)
    back(pg)
    # design checklist: iPad Pro landscape/portrait + iPhone
    for (vw,vh,nm) in ((1366,1024,'ipad-landscape'),(1024,1366,'ipad-portrait'),(390,844,'iphone')):
        pg.set_viewport_size({'width':vw,'height':vh}); pg.wait_for_timeout(300); pg.evaluate("document.documentElement.style.setProperty('--sat','24px')")
        c=to_end('Iron Tide 04'); pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(500); shot(pg,f'60-end-card-{nm}')
        sb=pg.evaluate("(()=>{const r=document.querySelector('#stage').getBoundingClientRect(); return r.top})()")
        good=(c['inView'] and c['coverH']>(0.6 if nm=='iphone' else 0.7) and c['capRows']>10 and c['gap']>=8 and c['capL']>0.02 and c['capR']<0.98 and abs(c['W']-round(c['cssW']*c['dpr']))<=2
              and (c['bg']==[11,11,11] if c['view']==[c['n']-1,c['n']] else c['bg']==[0,0,0]))
        ok(f'design checklist {nm} {vw}x{vh}: sharp canvas, cover dominant, caption under cover unclipped, dark bg, on screen',good,json.dumps(c))
        px=pg.evaluate("(async()=>{ const top=getComputedStyle(document.querySelector('#reader'),'::before'); return [top.backgroundColor,top.height]; })()")
        ok(f'design checklist {nm}: solid black status-bar strip over the reader',px[0] in ('rgb(0, 0, 0)','rgba(0, 0, 0, 1)'),json.dumps(px))
        back(pg); pg.evaluate("document.documentElement.style.removeProperty('--sat')")
    pg.set_viewport_size({'width':820,'height':1180}); pg.wait_for_timeout(300)
    if BIG:
        t0=time.time(); open_comic(pg,'Atlas Omnibus'); ok('big PDF opens',True,f'{time.time()-t0:.1f}s, {state(pg)["n"]} pages, {os.path.getsize(T+"/Atlas_Omnibus.pdf")//1048576} MB')
        t0=time.time(); pg.evaluate('__cr.jumpTo(150)'); wait_render(pg,60000); ok('big PDF random-access page 151',state(pg)['first']==150,f'{time.time()-t0:.2f}s')
        for i in range(12): pg.evaluate('__cr.go(-1,200)'); pg.wait_for_timeout(260)
        wait_render(pg,60000); c=state(pg)['cache']; ok('LRU bounded after many turns',c['px']<=c['budget'],json.dumps(c)); back(pg)
    # ---- phone ----
    pg.set_viewport_size({'width':390,'height':844}); tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.evaluate('__cr.CF.to(0,10)'); pg.wait_for_timeout(500); shot(pg,'20-phone-home'); g=pg.evaluate("(()=>{const i=Math.round(__cr.CF.pos); const c=document.querySelector('#cf .cf-item[data-i=\"'+i+'\"]').getBoundingClientRect(); return document.querySelector('.row-h').getBoundingClientRect().top-c.bottom})()"); ok('phone: rows close under carousel',20<g<80,str(round(g))); edge_ok(pg,'phone')
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
    # ---- series: issue sort, range names, rename (+merge on existing name), merge sheet ----
    ok('issue number parsing',pg.evaluate("[__cr.issueNo('X-MEN177'),__cr.issueNo('Uncanny X-Men 001 (1981)'),__cr.issueNo('#12 Annual 2020'),__cr.issueNo('Starlight Ronin v04'),__cr.issueNo('Oneshot')]")==[177,1,12,4,None] or pg.evaluate("[__cr.issueNo('X-MEN177'),__cr.issueNo('Uncanny X-Men 001 (1981)'),__cr.issueNo('#12 Annual 2020'),__cr.issueNo('Starlight Ronin v04'),__cr.issueNo('Oneshot')===Infinity]")==[177,1,12,4,True])
    rn=pg.evaluate("['150-199',\"300's\",'1-50','300s','1990s','#1-#25','300+','Uncanny X-Men','X-Men 1-50','Amazing Spiderman'].map(__cr.isRangeName)")
    ok('range/era folder names detected',rn==[True,True,True,True,True,True,True,False,False,False],str(rn))
    tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(200)
    ok('series rows have a … button',pg.locator('.row-more[data-series="Ember Road"]').count()==1 and pg.locator('.row-more').count()==len(pg.evaluate('__cr.series.counts()'))+1 and pg.locator('.row-more[data-kind=added]').count()==1)
    pg.locator('.row-more[data-series="Ember Road"]').scroll_into_view_if_needed(); pg.click('.row-more[data-series="Ember Road"]'); pg.wait_for_selector('#smRename'); shot(pg,'50-series-menu'); pg.click('#smRename')
    pg.wait_for_selector('#srName'); shot(pg,'51-rename-series'); pg.fill('#srName','Ember Trail'); pg.click('#srSave'); pg.wait_for_timeout(400)
    heads=pg.evaluate("[...document.querySelectorAll('#homeScroll .row-h h2')].map(e=>e.textContent)")
    ok('rename series from Home row …',('Ember Trail' in heads) and ('Ember Road' not in heads) and dict(pg.evaluate('__cr.series.counts()')).get('Ember Trail')==3,str(heads))
    pg.locator('.row-h[data-series="Ember Trail"]').dispatch_event('contextmenu'); pg.wait_for_timeout(200)
    ok('long-press / context menu on series heading opens series menu',pg.locator('#smRename').count()==1); pg.click('#smRename'); pg.wait_for_selector('#srName'); shot(pg,'52-series-rename')
    pg.fill('#srName','iron tide'); pg.click('#srSave'); pg.wait_for_timeout(500)
    cnt=dict(pg.evaluate('__cr.series.counts()'))
    ok('renaming onto an existing name merges (case-insensitive)',cnt.get('Iron Tide')==7 and 'Ember Trail' not in cnt and 'iron tide' not in cnt,str(cnt))
    pg.wait_for_timeout(300); pg.click('.row-h[data-series="Iron Tide"]'); pg.wait_for_timeout(400)
    ok('merged series page shows all 7',pg.locator('.lc').count()==7 and pg.evaluate("document.querySelector('#shelf').classList.contains('scoped')"))
    tl=pg.evaluate("[...document.querySelectorAll('#libGrid .lc')].map(e=>e.dataset.title)")
    ok('merged series sorted by issue number, then title',tl==['Ember Road 01','Iron Tide 01','Ember Road 02','Iron Tide 02','Ember Road 03','Iron Tide 03','Iron Tide 04'],str(tl))
    # ---- series page carousel (same style as Home), strictly by issue number ----
    pg.evaluate("document.querySelector('#libScroll').scrollTop=0"); pg.wait_for_timeout(400)
    sc=pg.evaluate('''(()=>{const C=__cr.SCF, el=document.querySelector('#scf'); if(!el) return null; const h=document.querySelector('#seriesHero .hero').getBoundingClientRect();
      const vis=[...el.querySelectorAll('.cf-item')].filter(e=>e.style.display!=='none'); const r=vis.map(e=>e.getBoundingClientRect());
      return {t:C.items.map(c=>c.title),pos:C.pos,hl:h.left,hw:h.width,vw:innerWidth,R:Math.max(...r.map(b=>b.right)),sharp:vis.every(e=>getComputedStyle(e.firstChild).filter==='none'),gridBelow:document.querySelector('#libGrid').getBoundingClientRect().top>=h.bottom-1}})()''')
    ok('series page shows its own carousel above the grid',sc is not None and sc['gridBelow'],str(sc))
    ok('series carousel strictly by issue number (ascending)',sc and sc['t']==['Ember Road 01','Iron Tide 01','Ember Road 02','Iron Tide 02','Ember Road 03','Iron Tide 03','Iron Tide 04'],str(sc and sc['t']))
    ok('series carousel edge-to-edge, stack runs past the screen edge, sharp covers',sc and sc['hl']==0 and abs(sc['hw']-sc['vw'])<1 and sc['R']>=sc['vw'] and sc['sharp'],str(sc))
    shot(pg,'58-series-carousel')
    cb=pg.locator('#scf .cf-item[data-i="0"]').bounding_box(); pg.mouse.click(cb['x']+cb['width']/2,cb['y']+cb['height']/2); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg)
    ok('tapping the centred series cover opens it',pg.text_content('#rTitle')=='Ember Road 01'); back(pg); pg.wait_for_timeout(300)
    ok('back from reader: still on the series page with its carousel',pg.locator('#scf').count()==1 and pg.locator('.lc').count()==7 and pg.is_visible('#libBack'))
    sb=pg.locator('#scf .cf-item[data-i="1"]').bounding_box(); pg.mouse.click(sb['x']+sb['width']*0.8,sb['y']+sb['height']/2); pg.wait_for_timeout(700); ok('series carousel: tap side cover centres it',round(pg.evaluate('__cr.SCF.pos'))==1)
    pg.click('#libBack'); pg.wait_for_timeout(300); ok('no series carousel in the full Library',pg.locator('#scf').count()==0)
    pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200); pg.wait_for_timeout(300)
    pg.click('#settingsBtn'); pg.wait_for_selector('#sMerge'); pg.click('#sMerge'); pg.wait_for_selector('#mgGo')
    ok('merge sheet: Merge disabled until 2 series picked',pg.locator('#mgGo').is_disabled())
    for nm in ['The Hollow','Twin Moon']: pg.locator('#mgList .ckr',has_text=nm).click()
    ok('merge sheet suggests a name',pg.input_value('#mgName')!='' and not pg.locator('#mgGo').is_disabled(),pg.input_value('#mgName'))
    pg.fill('#mgName','Hollow Moon'); shot(pg,'53-merge-series'); pg.click('#mgGo'); pg.wait_for_timeout(500)
    cnt=dict(pg.evaluate('__cr.series.counts()'))
    ok('merge sheet merges selected series into new name',cnt.get('Hollow Moon')==5 and 'The Hollow' not in cnt and 'Twin Moon' not in cnt,str(cnt))
    tab(pg,'home'); heads=pg.evaluate("[...document.querySelectorAll('#homeScroll .row-h h2')].map(e=>e.textContent)")
    ok('Home rows updated after merge',heads.count('Hollow Moon')==1 and 'Twin Moon' not in heads and 'The Hollow' not in heads,str(heads))
    # ---- Arrange Categories: order, touch drag, arrows, hide, persist, rename/merge carry, new series append, reset ----
    HEADS="[...document.querySelectorAll('#homeScroll .row-h h2')].map(e=>e.textContent)"
    AKEYS="[...document.querySelectorAll('#arrList li')].map(e=>e.dataset.k)"
    tab(pg,'home'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(200)
    pg.click('.row-more[data-kind=added]'); pg.wait_for_selector('#smArrange'); pg.click('#smArrange'); pg.wait_for_selector('#arrList li'); pg.wait_for_timeout(250)
    ok('Arrange sheet lists Recently Added + every series (from Recently Added …)',pg.evaluate(AKEYS)==['added','s:Hollow Moon','s:Iron Tide','s:Nightfall','s:Starlight Ronin'],str(pg.evaluate(AKEYS)))
    shot(pg,'54-arrange-categories')
    hb=pg.locator('#arrList li[data-k="s:Starlight Ronin"] .ah').bounding_box(); tb=pg.locator('#arrList li[data-k="added"]').bounding_box()
    x0,y0=hb['x']+hb['width']/2,hb['y']+hb['height']/2; y1=tb['y']+4
    if ENG=='chromium':   # real touch input (CDP) -> genuine touch pointer events
        cdp=ctx.new_cdp_session(pg)
        def tch(tp,px,py): cdp.send('Input.dispatchTouchEvent',{'type':tp,'touchPoints':[] if tp=='touchEnd' else [{'x':px,'y':py,'id':1}]})
        tch('touchStart',x0,y0)
        for k in range(1,13): pg.wait_for_timeout(16); tch('touchMove',x0,y0+(y1-y0)*k/12)
        pg.wait_for_timeout(60); shot(pg,'55-arrange-dragging'); tch('touchEnd',0,0); cdp.detach()
    else:                    # WebKit: touch-type pointer events on the handle
        pg.evaluate("""async ({x0,y0,y1})=>{ const h=document.querySelector('#arrList li[data-k="s:Starlight Ronin"] .ah'); const sl=ms=>new Promise(r=>setTimeout(r,ms));
          const ev=(t,y)=>h.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:77,pointerType:'touch',isPrimary:true,clientX:x0,clientY:y,buttons:t==='pointerup'?0:1}));
          ev('pointerdown',y0); for(let k=1;k<=12;k++){ await sl(16); ev('pointermove',y0+(y1-y0)*k/12); } await sl(40); ev('pointerup',y1); }""",{'x0':x0,'y0':y0,'y1':y1})
    pg.wait_for_timeout(200)
    ok('touch drag reorders (Starlight Ronin dragged to top)',pg.evaluate(AKEYS)==['s:Starlight Ronin','added','s:Hollow Moon','s:Iron Tide','s:Nightfall'],str(pg.evaluate(AKEYS)))
    ok('drag leaves no transform / drag state',pg.evaluate("![...document.querySelectorAll('#arrList li')].some(e=>e.style.transform||e.classList.contains('drag'))"))
    ok('first row up-arrow disabled, last row down-arrow disabled',pg.locator('#arrList li').first.locator('[data-mv="-1"]').is_disabled() and pg.locator('#arrList li').last.locator('[data-mv="1"]').is_disabled())
    pg.click('#arrList li[data-k="s:Nightfall"] [data-mv="-1"]'); pg.wait_for_timeout(100)
    ok('up arrow moves a row up',pg.evaluate(AKEYS)==['s:Starlight Ronin','added','s:Hollow Moon','s:Nightfall','s:Iron Tide'],str(pg.evaluate(AKEYS)))
    pg.click('#arrList li[data-k="added"] [data-mv="1"]'); pg.click('#arrList li[data-k="added"] [data-mv="-1"]'); pg.wait_for_timeout(100)
    ok('down then up returns to place',pg.evaluate(AKEYS)[1]=='added')
    pg.click('#arrList li[data-k="s:Iron Tide"] .tgl'); pg.wait_for_timeout(100)
    ok('show/hide toggle (Iron Tide off)',pg.locator('#arrList li[data-k="s:Iron Tide"].off').count()==1)
    shot(pg,'56-arrange-edited'); pg.click('#arrDone'); pg.wait_for_timeout(400)
    ok('Home follows arranged order, hidden row gone',pg.evaluate(HEADS)==['Starlight Ronin','Recently Added','Hollow Moon','Nightfall'],str(pg.evaluate(HEADS)))
    shot(pg,'57-home-arranged')
    pg.reload(); pg.wait_for_selector('html[data-ready]'); tab(pg,'home'); pg.wait_for_timeout(500)
    ok('arrangement persists after relaunch',pg.evaluate(HEADS)==['Starlight Ronin','Recently Added','Hollow Moon','Nightfall'],str(pg.evaluate(HEADS)))
    pg.click('.row-more[data-series="Hollow Moon"]'); pg.wait_for_selector('#smRename'); pg.click('#smRename'); pg.wait_for_selector('#srName'); pg.fill('#srName','Aardvark'); pg.click('#srSave'); pg.wait_for_timeout(400)
    ok('renamed series keeps its position',pg.evaluate(HEADS)==['Starlight Ronin','Recently Added','Aardvark','Nightfall'],str(pg.evaluate(HEADS)))
    sheet(pg,'Nightfall 05','aEdit'); pg.wait_for_selector('#eSeries'); pg.fill('#eSeries','Abyss'); pg.click('#eSave'); pg.wait_for_timeout(400); tab(pg,'home'); pg.wait_for_timeout(200)
    ok('new series appends at the end (not alphabetically first)',pg.evaluate(HEADS)==['Starlight Ronin','Recently Added','Aardvark','Nightfall','Abyss'],str(pg.evaluate(HEADS)))
    pg.click('.row-more[data-series="Abyss"]'); pg.wait_for_selector('#smRename'); pg.click('#smRename'); pg.wait_for_selector('#srName'); pg.fill('#srName','Starlight Ronin'); pg.click('#srSave'); pg.wait_for_timeout(400)
    ok('merged series takes the topmost position of those merged',pg.evaluate(HEADS)==['Starlight Ronin','Recently Added','Aardvark','Nightfall'],str(pg.evaluate(HEADS)))
    pg.locator('#homeScroll .row-h[data-kind=added]').dispatch_event('contextmenu'); pg.wait_for_timeout(200)
    ok('long-press on Recently Added heading offers Arrange',pg.locator('#smArrange').count()==1 and pg.locator('#smRename').count()==0); pg.evaluate("document.querySelector('.menu')?.remove()")
    pg.click('#settingsBtn'); pg.wait_for_selector('#sArrange'); pg.click('#sArrange'); pg.wait_for_selector('#arrList li'); pg.wait_for_timeout(200)
    ok('Settings > Arrange Categories opens sheet with current order',pg.evaluate(AKEYS)==['s:Starlight Ronin','added','s:Aardvark','s:Nightfall','s:Iron Tide'],str(pg.evaluate(AKEYS)))
    pg.click('#arrReset'); pg.wait_for_timeout(150)
    ok('Reset to alphabetical (Recently Added first, series A–Z)',pg.evaluate(AKEYS)==['added','s:Aardvark','s:Iron Tide','s:Nightfall','s:Starlight Ronin'],str(pg.evaluate(AKEYS)))
    pg.click('#arrList li[data-k="s:Iron Tide"] .tgl'); pg.click('#arrDone'); pg.wait_for_timeout(400)
    ok('Home after reset + re-show',pg.evaluate(HEADS)==['Recently Added','Aardvark','Iron Tide','Nightfall','Starlight Ronin'],str(pg.evaluate(HEADS)))

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
                     {'id':'f-a2','name':'ASM_002.pdf','size':str(os.path.getsize(f'{T}/Iron_Tide_02.pdf')),'mimeType':'application/pdf'},
                     {'id':'sub-rng','name':'150-199','mimeType':'application/vnd.google-apps.folder'}],
          'sub-rng':[{'id':'f-a3','name':'ASM_150.pdf','size':str(os.path.getsize(f'{T}/Iron_Tide_03.pdf')),'mimeType':'application/pdf'}],
          'sub-300':[{'id':'f-a4','name':'X-MEN300.pdf','size':str(os.path.getsize(f'{T}/Iron_Tide_04.pdf')),'mimeType':'application/pdf'}]}
    FOLD['0ByhXYqPJBamsS2h2X01uS29uaU0'].append({'id':'sub-300','name':"300's",'mimeType':'application/vnd.google-apps.folder'})
    SRC={'f-nf2':'Nightfall_02.pdf','f-gh':'Glass_Harbor.pdf','f-a1':'Iron_Tide_01.pdf','f-a2':'Iron_Tide_02.pdf','f-a3':'Iron_Tide_03.pdf','f-a4':'Iron_Tide_04.pdf'}
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
    ok('checklist: 6 PDFs, duplicate marked + unchecked, others checked',p2.locator('.ckr').count()==6 and p2.locator('.ckr.dup input:checked').count()==0 and 'In library' in p2.inner_text('.ckr.dup') and p2.locator('.ckr input:checked').count()==5 and p2.inner_text('#ckGo')=='Import 5')
    shot(p2,'30-drive-folder-checklist')
    p2.click('#ckNone'); ok('Select None disables Import',p2.locator('#ckGo').is_disabled())
    p2.click('#ckAll'); ok('Select All re-selects all new files',p2.inner_text('#ckGo')=='Import 5')
    p2.locator('.ckr').nth(1).click(); ok('toggle one file off',p2.inner_text('#ckGo')=='Import 4')
    p2.locator('.ckr').nth(1).click(); p2.click('#ckGo')
    p2.wait_for_function('document.querySelectorAll(".lc").length==6',timeout=90000)
    sers=p2.evaluate("(async()=>{const r=indexedDB.open('comic-reader');await new Promise(x=>r.onsuccess=x);const all=await new Promise(x=>{const q=r.result.transaction('comics').objectStore('comics').getAll();q.onsuccess=()=>x(q.result)});return all.map(c=>[c.title,c.series,c.driveId||''])})()")
    asm=[x for x in sers if x[1]=='Amazing Spiderman']
    ok('folder import: subfolder files get series = subfolder name',len(asm)==3,json.dumps(sers))
    ok('range-named subfolder (150-199) inside a series folder keeps parent series',['ASM 150','Amazing Spiderman','f-a3'] in sers,json.dumps(sers))
    ok("range-named subfolder (300's) at top level uses parent (Drive folder) name",['X-MEN300','Comics','f-a4'] in sers,json.dumps(sers))
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
    # mixed-shape (scanned) pages: neighbouring spreads used to get different box sizes -> blank flash on landing
    c3=b.new_context(viewport={'width':1180,'height':820},has_touch=True,device_scale_factor=2,service_workers='block'); pg_main=pg; pg=c3.new_page()
    pg.on('pageerror',lambda e:errors.append('pageerror: '+str(e))); pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    pg.set_input_files('#fileIn',[f'{T}/mixed/Scanned_Mix_01.pdf']); pg.wait_for_function('document.querySelectorAll(".lc").length==1 && !document.querySelector(".toast .tb")',timeout=60000)
    open_comic(pg,'Scanned Mix 01'); wait_render(pg); pg.wait_for_timeout(800)
    for j in (5,9,13,17):
        pg.evaluate(f'__cr.jumpTo({j})'); wait_render(pg); pg.wait_for_timeout(500); stable(f'mixed-shape pages: landscape 2-up turn from p{j+1}')
    pg.evaluate('__cr.jumpTo(7)'); wait_render(pg); pg.wait_for_timeout(500); same_render('mixed-shape pages')
    bx=pg.evaluate("(async()=>{const s=new Set(); for(const j of [3,7,11,15]){ __cr.jumpTo(j); await new Promise(r=>setTimeout(r,250)); document.querySelectorAll('.view .pg').forEach(e=>s.add(e.style.width+'x'+e.style.height)); } return [...s]; })()")
    ok('mixed-shape pages: every spread uses the same page box',len(bx)==1,str(bx))
    pg.evaluate('__cr.jumpTo(9)'); pg.wait_for_timeout(60); stable('mixed-shape pages: turn with slow renders (600ms) right after a jump',slow=600)
    pg.wait_for_timeout(2500); back(pg)
    # fold sheet: no seam/line at the spine at any point of a landscape turn (odd sheet widths used to leave a 1-device-px black column)
    pg.set_input_files('#fileIn',[f'{T}/mixed/Plain_Fold_01.pdf']); pg.wait_for_function('document.querySelectorAll(".lc").length==2 && !document.querySelector(".toast .tb")',timeout=60000)
    import io as _io
    from PIL import Image as _Im
    import numpy as _np
    def spine_dip(png,g):
        a=_np.asarray(_Im.open(_io.BytesIO(png)).convert('L'),dtype=float)[int(g[1]*2)+40:int(g[2]*2)-40]; cx=int(round(g[0]*2)); col=a[:,cx-12:cx+13].mean(0)
        return round(max(min(col[i-3],col[i+3])-col[i] for i in range(3,22)),1)
    for HH in (819,823):
        pg.set_viewport_size({'width':1180,'height':HH}); pg.wait_for_timeout(300); open_comic(pg,'Plain Fold 01'); pg.evaluate('__cr.jumpTo(4)'); wait_render(pg); pg.wait_for_timeout(600)
        g=pg.evaluate("(()=>{const r=document.querySelector('.view .pg').getBoundingClientRect(); return [r.left+r.width/2,r.top,r.bottom]})()"); dips=[]
        for d in (-1,1):
            pg.evaluate(f'__cr.go({d},6000)'); t=0
            for at in (300,1500,3000,4500,5800):
                pg.wait_for_timeout(at-t); t=at; dips.append(spine_dip(pg.screenshot(),g))
            pg.wait_for_timeout(1500)
        ok(f'fold turn at 1180x{HH}: no seam line at the spine during the turn',max(dips)<40,str(dips)); back(pg)
    c3.close(); pg=pg_main
    b.close()
ok('no console errors / page errors',not errors,'\n'.join(errors[:10]))
print(f'{sum(res)}/{len(res)} passed')
sys.exit(0 if all(res) else 1)
