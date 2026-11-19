"""cr-v63 suite: Fit width continuous vertical scroll.
python3 test/e2e_v63.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: Iron Tide 01 (34 pages)."""
import sys, os, json
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=[os.path.join(T,'Iron_Tide_01.pdf')]
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,'' if cond else str(extra)[:500],flush=True)

def dismiss(pg):
    pg.evaluate("window.__crSplashHide&&window.__crSplashHide(true)")
    pg.wait_for_function("!document.getElementById('splash')||document.getElementById('splash').classList.contains('fly')||document.getElementById('splash').classList.contains('out')")
    pg.wait_for_timeout(200)
def wait_render(pg,t=20000):
    pg.wait_for_function('document.querySelectorAll(".view .pg.loading").length===0 && document.querySelectorAll(".view .pg canvas").length>0',timeout=t)
def wait_fit(pg,t=20000):
    pg.wait_for_function('document.querySelector("#stage.fitw") && document.querySelectorAll("#stage.fitw .pg canvas").length>0',timeout=t)
def open_c(pg,title='Iron Tide 01'):
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150)
    pg.locator(f'.lc[data-title="{title}"]').click(); pg.wait_for_selector('#reader:not(.hidden)')
def back(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(80)
    pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(250)
def show_ui(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(80)

GEST='''async ({x,y,pts,hold})=>{
  const st=document.querySelector('#stage');
  const mk=(type,id,cx,cy)=>new PointerEvent(type,{bubbles:true,cancelable:true,composed:true,pointerId:id,pointerType:'touch',isPrimary:true,clientX:cx,clientY:cy,button:0,buttons:type==='pointerup'?0:1,width:20,height:20,pressure:type==='pointerup'?0:.5});
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  st.dispatchEvent(mk('pointerdown',11,x,y)); let cx=x,cy=y;
  for(const [dx,dy,dt] of pts){ await sleep(dt); cx=x+dx; cy=y+dy; st.dispatchEvent(mk('pointermove',11,cx,cy)); }
  if(hold) await sleep(hold);
  st.dispatchEvent(mk('pointerup',11,cx,cy)); await sleep(80);
  return {vi:window.__cr.R.vi, cur:window.__cr.fit&&window.__cr.fit.cur, flip:!!window.__cr.flip, ui:document.getElementById('reader').classList.contains('ui')};
}'''

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    sizes=[(1024,1366,'ipad-portrait',2,24,20),(1366,1024,'ipad-landscape',2,24,20)]
    for (w,h,lab,dpr,sat,sab) in sizes:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crNoBag=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}') if 'access control checks' not in str(e).lower() and 'cross-origin' not in str(e).lower() else None)
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        dismiss(pg)
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==1 && !document.querySelector(".toast .tb")',timeout=120000)

        # ---- Button is in the reader top bar, off by default, >=40px ----
        open_c(pg); wait_render(pg); show_ui(pg)
        g=pg.evaluate("""()=>{
          const b=document.querySelector('#rFit'), r=b.getBoundingClientRect(), bar=document.querySelector('#rtop');
          const br=bar.getBoundingClientRect(), cs=getComputedStyle(bar);
          return {exists:!!b, label:(b.getAttribute('aria-label')||'')+(b.getAttribute('title')||'')+(b.textContent||''),
            pressed:b.getAttribute('aria-pressed'), on:b.classList.contains('on'),
            w:Math.round(r.width), h:Math.round(r.height), x:Math.round(r.x), y:Math.round(r.y),
            barBg:cs.backgroundColor, barOpacity:cs.opacity, barTop:Math.round(br.top),
            store:localStorage.getItem('cr.fitWidth'), stageFit:document.getElementById('stage').classList.contains('fitw')};
        }""")
        ok(f'{lab}: Fit width button in the top bar, off by default, tap target >=40px',
           g['exists'] and 'Fit width' in g['label'] and g['pressed']=='false' and not g['on'] and not g['stageFit']
           and g['store'] is None and g['w']>=40 and g['h']>=40 and g['y']>=0, json.dumps(g))
        ok(f'{lab}: reader top bar is opaque and sits below the status inset',
           g['barTop']>=0 and g['barOpacity'] in ('1',1) and '0, 0, 0' in (g['barBg'] or ''), json.dumps(g))

        # ---- Turn Fit width on: pages stack at full width ----
        # start from page 0, then later from a later page
        pg.click('#rFit'); wait_fit(pg); show_ui(pg)
        st=pg.evaluate("""()=>{
          const stage=document.getElementById('stage'), pgs=[...stage.querySelectorAll('.pg')];
          const boxes=pgs.slice(0,4).map(el=>{ const r=el.getBoundingClientRect(); return {p:+el.dataset.p, x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height), top:el.offsetTop}; });
          const cvs=stage.querySelectorAll('.pg canvas').length, total=pgs.length;
          const b=document.querySelector('#rFit');
          return {fit:stage.classList.contains('fitw'), overflow:getComputedStyle(stage).overflowY, tw:stage.clientWidth,
            n:total, canvases:cvs, boxes, store:localStorage.getItem('cr.fitWidth'),
            on:b.classList.contains('on'), pressed:b.getAttribute('aria-pressed'),
            cur:window.__cr.fit.cur, vi:window.__cr.R.vi, pgText:document.getElementById('pgText').textContent,
            spread:window.__cr.R.spread};
        }""")
        stacked=len(st['boxes'])>=2 and all(st['boxes'][i]['top']<st['boxes'][i+1]['top'] for i in range(len(st['boxes'])-1))
        fullw=all(abs(box['w']-st['tw'])<=2 for box in st['boxes'])
        ok(f'{lab}: turning Fit width on stacks pages at full width and persists',
           st['fit'] and st['store']=='true' and st['on'] and st['pressed']=='true' and st['n']>8
           and st['overflow'] in ('auto','scroll') and stacked and fullw and st['cur']==0
           and st['pgText'].startswith('1 /') and not st['spread'], json.dumps({k:st[k] for k in st if k!='boxes'})+str(st['boxes']))
        ok(f'{lab}: long issues lazy-load (not every page painted at once)',
           st['canvases']>=1 and st['canvases']<st['n'] and st['canvases']<=12, json.dumps({'canvases':st['canvases'],'n':st['n']}))

        # ---- Scroll is continuous: page 2 starts below page 1, counter follows ----
        # Scroll so the boundary between page 0 and 1 sits mid-viewport
        mid=pg.evaluate("""()=>{
          const stage=document.getElementById('stage'), a=stage.querySelector('.pg[data-p="0"]'), b=stage.querySelector('.pg[data-p="1"]');
          const target=b.offsetTop - Math.round(stage.clientHeight*0.45);
          stage.scrollTop=Math.max(0,target);
          return {scroll:stage.scrollTop, aBottom:a.offsetTop+a.offsetHeight, bTop:b.offsetTop, H:stage.clientHeight,
            cur:window.__cr.fit.cur, pgText:document.getElementById('pgText').textContent, flip:!!window.__cr.flip};
        }""")
        pg.wait_for_timeout(200)
        mid2=pg.evaluate("""()=>{
          const stage=document.getElementById('stage'), a=stage.querySelector('.pg[data-p="0"]'), b=stage.querySelector('.pg[data-p="1"]');
          const ra=a.getBoundingClientRect(), rb=b.getBoundingClientRect(), sr=stage.getBoundingClientRect();
          return {cur:window.__cr.fit.cur, vi:window.__cr.R.vi, pgText:document.getElementById('pgText').textContent,
            flip:!!window.__cr.flip, aBottom:Math.round(ra.bottom), bTop:Math.round(rb.top),
            stageTop:Math.round(sr.top), stageBot:Math.round(sr.bottom), gap:Math.round(rb.top-ra.bottom),
            aVis:ra.bottom>sr.top+20 && ra.top<sr.bottom-20, bVis:rb.bottom>sr.top+20 && rb.top<sr.bottom-20,
            canvases:stage.querySelectorAll('.pg canvas').length, n:stage.querySelectorAll('.pg').length};
        }""")
        ok(f'{lab}: scrolling down flows into the next page without a page turn, counter tracks scroll',
           mid2['bVis'] and mid2['aVis'] and mid2['gap']>=0 and mid2['gap']<=8 and not mid2['flip']
           and mid2['cur'] in (0,1) and ('/' in mid2['pgText']), json.dumps(mid2))

        show_ui(pg)
        if lab in ('ipad-portrait','ipad-landscape'):
            pg.screenshot(path=f'{SH}/{ENG}-v63-fitwidth-scroll-{lab}.png')

        # ---- Jump / scroll further: current page updates, still no flip ----
        pg.evaluate('__cr.fit.goTo(8)')
        pg.wait_for_function("!!document.querySelector('.pg[data-p=\"8\"] canvas')", timeout=20000)
        jumped=pg.evaluate("""()=>{
          const d=document.querySelector('.pg[data-p="8"]'), r=d&&d.getBoundingClientRect(), sr=document.getElementById('stage').getBoundingClientRect();
          return {cur:window.__cr.fit.cur, vi:window.__cr.R.vi, pgText:document.getElementById('pgText').textContent,
            flip:!!window.__cr.flip, atTop:d && Math.abs(d.offsetTop-document.getElementById('stage').scrollTop)<=4,
            visible:r && r.top<sr.bottom && r.bottom>sr.top, hasCv:!!(d&&d.querySelector('canvas')),
            canvases:document.querySelectorAll('#stage.fitw .pg canvas').length, n:document.querySelectorAll('#stage.fitw .pg').length};
        }""")
        ok(f'{lab}: jumping to page 9 lands at the top, counter says 9, page is painted, others still lazy',
           jumped['cur']==8 and jumped['pgText'].startswith('9 /') and jumped['atTop'] and jumped['visible']
           and jumped['hasCv'] and not jumped['flip'] and jumped['canvases']<jumped['n'], json.dumps(jumped))

        # go() / startFlip must be no-ops
        noop=pg.evaluate("""()=>{ const cur=window.__cr.fit.cur, vi=window.__cr.R.vi; const okFlip=__cr.startFlip(-1); __cr.go(-1,200);
          return {okFlip, flip:!!window.__cr.flip, cur:window.__cr.fit.cur, vi:window.__cr.R.vi, same:window.__cr.fit.cur===cur && window.__cr.R.vi===vi}; }""")
        ok(f'{lab}: Swipe and Paper curl do not run while Fit width is on',
           noop['okFlip'] is False and not noop['flip'] and noop['same'], json.dumps(noop))

        # vertical pointer pan does not toggle UI or start a flip
        show_ui(pg)
        pan=pg.evaluate(GEST, {'x':w//2,'y':h//2,'pts':[[0,40,20],[0,120,20],[0,240,20]],'hold':0})
        ok(f'{lab}: a vertical scroll gesture does not toggle the bars or start a page turn',
           pan['ui'] is True and not pan['flip'] and pan['cur'] is not None, json.dumps(pan))

        # ---- Turn off: returns to the page we were on ----
        was=pg.evaluate('({cur:window.__cr.fit.cur, text:document.getElementById("pgText").textContent})')
        pg.click('#rFit')
        wait_render(pg)
        off=pg.evaluate("""()=>{
          const b=document.querySelector('#rFit');
          const ps=(window.__cr.R.views[window.__cr.R.vi]||[]).filter(x=>x!=null);
          return {fit:document.getElementById('stage').classList.contains('fitw'), on:b.classList.contains('on'),
            pressed:b.getAttribute('aria-pressed'), store:localStorage.getItem('cr.fitWidth'),
            vi:window.__cr.R.vi, pages:ps, pgText:document.getElementById('pgText').textContent,
            hasView:!!document.querySelector('.view .pg canvas')};
        }""")
        ok(f'{lab}: turning Fit width off returns to the same page and restores normal view',
           not off['fit'] and not off['on'] and off['pressed']=='false' and off['store']=='false'
           and was['cur'] in off['pages'] and off['hasView'], json.dumps({'was':was,'off':off}))

        # Swipe still works when off
        vi0=pg.evaluate('__cr.R.vi')
        pg.evaluate('__cr.go(-1,200)')
        pg.wait_for_function('!__cr.flip && !__cr.animating', timeout=4000)
        vi1=pg.evaluate('__cr.R.vi')
        ok(f'{lab}: Swipe still turns a page when Fit width is off', vi1>vi0, f'vi {vi0}->{vi1}')

        # ---- Turn on from a later page: stays on that page ----
        show_ui(pg)
        pg.click('#rFit'); wait_fit(pg)
        stay=pg.evaluate("""()=>{
          const cur=window.__cr.fit.cur, d=document.querySelector(`.pg[data-p="${cur}"]`);
          const at=d && Math.abs(d.offsetTop-document.getElementById('stage').scrollTop)<=6;
          return {cur, at, pgText:document.getElementById('pgText').textContent, vi:window.__cr.R.vi};
        }""")
        ok(f'{lab}: turning Fit width on keeps you on the current page',
           stay['cur']==vi1 or stay['vi']==vi1 or stay['at'], json.dumps({'vi1':vi1,'stay':stay}))
        # more precise: the page we had been on should be at (or very near) the top
        ok(f'{lab}: the kept page is scrolled to the top of the stack',
           stay['at'] is True, json.dumps(stay))

        # persistence across reload
        back(pg)
        pg.reload(); pg.wait_for_selector('html[data-ready]'); dismiss(pg)
        open_c(pg); wait_fit(pg)
        persist=pg.evaluate("""()=>({fit:document.getElementById('stage').classList.contains('fitw'),
          store:localStorage.getItem('cr.fitWidth'), on:document.querySelector('#rFit').classList.contains('on')})""")
        ok(f'{lab}: Fit width stays on after reload', persist['fit'] and persist['store']=='true' and persist['on'], json.dumps(persist))

        # landscape: still a vertical stack (not a 2-up row)
        if lab=='ipad-landscape':
            lay=pg.evaluate("""()=>{
              const pgs=[...document.querySelectorAll('#stage.fitw .pg')].slice(0,3).map(el=>{const r=el.getBoundingClientRect(); return {p:+el.dataset.p,x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width)};});
              return {spread:window.__cr.R.spread, tw:document.getElementById('stage').clientWidth, pgs};
            }""")
            ok(f'{lab}: landscape Fit width still stacks pages vertically at full width, not 2-up',
               not lay['spread'] and len(lay['pgs'])>=2 and lay['pgs'][0]['w']>=lay['tw']-2 and lay['pgs'][1]['y']>lay['pgs'][0]['y']+40, json.dumps(lay))

        back(pg)
        ctx.close()

    b.close()

print('---')
print(sum(res),'/' ,len(res),'passed')
real=[e for e in errors if 'access control checks' not in e.lower() and 'cross-origin' not in e.lower()]
if real:
    print('page errors:'); [print(' ',e) for e in real]
sys.exit(0 if all(res) and not real else 1)
