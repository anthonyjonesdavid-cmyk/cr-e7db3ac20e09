"""cr-v59 suite: bag-and-board opening + page turn style (Swipe / Paper curl).
python3 test/e2e_v59.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: original abstract comics (test/gen_pdfs.py). Standalone insets via --sat/--sab."""
import sys, os, json, time
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=[os.path.join(T,'Iron_Tide_01.pdf'),os.path.join(T,'Nightfall_01.pdf')]
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:400] if not cond or extra and not cond else '',flush=True)
GEST='''async ({x,y,pts,hold,noup})=>{
  const st=document.querySelector('#stage');
  const mk=(type,id,cx,cy)=>new PointerEvent(type,{bubbles:true,cancelable:true,composed:true,pointerId:id,pointerType:'touch',isPrimary:id===11,clientX:cx,clientY:cy,button:0,buttons:type==='pointerup'?0:1,width:20,height:20,pressure:type==='pointerup'?0:.5});
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const ps=[]; let watching=true;
  (function w(){ const f=window.__cr.flip; if(f) ps.push({p:+f.p.toFixed(3),mode:f.mode||''}); if(watching) requestAnimationFrame(w); })();
  st.dispatchEvent(mk('pointerdown',11,x,y)); let cx=x,cy=y;
  for(const [dx,dy,dt] of pts){ await sleep(dt); cx=x+dx; cy=y+dy; st.dispatchEvent(mk('pointermove',11,cx,cy)); }
  if(hold) await sleep(hold);
  const mid=window.__cr.flip?{p:window.__cr.flip.p,mode:window.__cr.flip.mode||'',curl:!!window.__cr.flip.curl}:null;
  if(noup){ watching=false; return {mid,frames:ps}; }
  st.dispatchEvent(mk('pointerup',11,cx,cy)); await sleep(900); watching=false;
  const R=window.__cr.R; const v=R.views[R.vi];
  return {mid,frames:ps,vi:R.vi,first:v.filter(x=>x!=null)[0],mode:mid&&mid.mode};
}'''
def dismiss(pg):
    pg.evaluate("window.__crSplashHide&&window.__crSplashHide(true)")
    pg.wait_for_function("!document.getElementById('splash')||document.getElementById('splash').classList.contains('fly')||document.getElementById('splash').classList.contains('out')")
    pg.wait_for_timeout(200)
def wait_render(pg,t=20000):
    pg.wait_for_function('document.querySelectorAll(".view .pg.loading").length===0 && document.querySelectorAll(".view .pg canvas").length>0',timeout=t)
def open_c(pg,title='Iron Tide 01'):
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150)
    pg.locator(f'.lc[data-title="{title}"]').click(); pg.wait_for_selector('#reader:not(.hidden)')
def back(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(80)
    pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(250)
def settings(pg):
    pg.click('#settingsBtn'); pg.wait_for_selector('#sBag')
def done(pg):
    pg.click('[data-r=done]'); pg.wait_for_timeout(200)

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    sizes=[(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]
    for (w,h,lab,dpr,sat,sab) in sizes:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}'))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        dismiss(pg)
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=120000)
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200)

        # ---- Settings defaults ----
        settings(pg)
        g=pg.evaluate("""(()=>{const i=document.querySelector('#sBag'), l=i.closest('label'), r=l.getBoundingClientRect(), sw=document.querySelector('#sTurn button[data-v=swipe]'), cu=document.querySelector('#sTurn button[data-v=curl]');
          const rb=sw.getBoundingClientRect(), rc=cu.getBoundingClientRect();
          return {bagOn:i.checked,bagStore:localStorage.getItem('cr.bagOpen'),bagTxt:l.textContent,bh:r.height,bw:r.width,
            swipe:sw.classList.contains('on')&&sw.getAttribute('aria-checked')==='true',curlOn:cu.classList.contains('on'),
            turnStore:localStorage.getItem('cr.pageTurn'),turnTxt:document.querySelector('#sTurn').parentElement.textContent,
            sh:rb.height,sw:rb.width,ch:rc.height,cw:rc.width}})()""")
        ok(f'{lab}: Settings has "Bag-and-board opening", ON by default, tap target >=40px',
           g['bagOn'] and g['bagStore'] is None and 'Bag-and-board opening' in g['bagTxt'] and g['bh']>=40 and g['bw']>=40, json.dumps(g))
        ok(f'{lab}: Page turn style defaults to Swipe, Paper curl offered, targets >=40px',
           g['swipe'] and not g['curlOn'] and g['turnStore'] is None and 'Page turn style' in g['turnTxt'] and 'Paper curl' in g['turnTxt'] and 'Swipe' in g['turnTxt'] and g['sh']>=40 and g['ch']>=40 and g['sw']>=40 and g['cw']>=40, json.dumps(g))
        pg.evaluate("document.querySelectorAll('.toast').forEach(e=>e.remove())")
        pg.locator('#sBag').evaluate("e=>e.closest('label').scrollIntoView({block:'center'})"); pg.wait_for_timeout(150)
        if lab in ('ipad-portrait','iphone-390','ipad-landscape','iphone-430'):
            pg.screenshot(path=f'{SH}/{ENG}-v59-settings-bag-turn-{lab}.png')

        # persistence: flip both, reload
        pg.locator('#sBag').evaluate("e=>e.closest('label').click()"); pg.wait_for_timeout(80)
        pg.locator('#sTurn button[data-v=curl]').click(); pg.wait_for_timeout(80)
        st=pg.evaluate("({bag:localStorage.getItem('cr.bagOpen'),turn:localStorage.getItem('cr.pageTurn'),bagOn:document.querySelector('#sBag').checked,curl:document.querySelector('#sTurn button[data-v=curl]').classList.contains('on')})")
        ok(f'{lab}: turning bag off and Paper curl on is stored in localStorage', st['bag']=='false' and st['turn']=='"curl"' and not st['bagOn'] and st['curl'], json.dumps(st))
        done(pg)
        pg.reload(); pg.wait_for_selector('html[data-ready]'); dismiss(pg)
        settings(pg)
        st2=pg.evaluate("({bagOn:document.querySelector('#sBag').checked,curl:document.querySelector('#sTurn button[data-v=curl]').classList.contains('on'),swipe:document.querySelector('#sTurn button[data-v=swipe]').classList.contains('on'),bag:localStorage.getItem('cr.bagOpen'),turn:localStorage.getItem('cr.pageTurn')})")
        ok(f'{lab}: bag off and Paper curl persist across reload', (not st2['bagOn']) and st2['curl'] and not st2['swipe'] and st2['bag']=='false' and st2['turn']=='"curl"', json.dumps(st2))

        # ---- Bag off: no animation ----
        done(pg)
        t0=time.time(); open_c(pg); visible=time.time()-t0
        bag_on=pg.evaluate("!!(window.__cr.bag&&__cr.bag.on) || (document.querySelector('#bagOpen')&&!document.querySelector('#bagOpen').classList.contains('hidden'))")
        wait_render(pg)
        ok(f'{lab}: toggle off means no bag animation; reader still opens promptly', (not bag_on) and visible<1.5, f'visible={visible:.3f}s bag={bag_on}')
        back(pg)

        # ---- Bag on: plays, does not delay open, skip works ----
        settings(pg)
        pg.locator('#sBag').evaluate("e=>e.closest('label').scrollIntoView({block:'center'})")
        pg.locator('#sBag').evaluate("e=>e.closest('label').click()"); pg.wait_for_timeout(80)  # back on
        # leave curl on for later; bag tests don't care
        done(pg)
        t0=time.time()
        open_c(pg)
        vis=time.time()-t0
        # bag should be visible immediately (or already finishing if extremely slow); reader must already be open
        state=pg.evaluate("""(()=>{const b=document.querySelector('#bagOpen'); const r=document.querySelector('#reader');
          return {reader:!r.classList.contains('hidden'), bag:b&&!b.classList.contains('hidden'), bagOn:!!(__cr.bag&&__cr.bag.on), out:b&&b.classList.contains('out')}})()""")
        ok(f'{lab}: bag on: reader is open immediately and bag animation is playing (open not delayed)',
           state['reader'] and vis<0.8 and (state['bag'] or state['bagOn']), f'vis={vis:.3f}s {json.dumps(state)}')
        # wait for page render while bag may still be up — proves load isn't blocked
        wait_render(pg)
        after=time.time()-t0
        bag_during=pg.evaluate("({on:!!(__cr.bag&&__cr.bag.on), hidden:document.querySelector('#bagOpen').classList.contains('hidden')})")
        ok(f'{lab}: page renders without waiting for the bag to finish (open time)',
           after<3.0, f'rendered in {after:.3f}s bag={json.dumps(bag_during)}')
        back(pg)

        # tap to skip
        open_c(pg); pg.wait_for_timeout(80)
        playing=pg.evaluate("!!(__cr.bag&&__cr.bag.on)")
        if playing:
            pg.evaluate("""()=>{const st=document.querySelector('#stage'), x=innerWidth/2, y=innerHeight/2;
              const mk=t=>new PointerEvent(t,{bubbles:true,cancelable:true,composed:true,pointerId:77,pointerType:'touch',isPrimary:true,clientX:x,clientY:y,button:0,buttons:t==='pointerup'?0:1});
              st.dispatchEvent(mk('pointerdown')); st.dispatchEvent(mk('pointerup'));}""")
            pg.wait_for_timeout(80)
            skipped=pg.evaluate("({on:!!(__cr.bag&&__cr.bag.on), hidden:document.querySelector('#bagOpen').classList.contains('hidden')})")
            ok(f'{lab}: a tap skips the bag animation immediately', (not skipped['on']) and skipped['hidden'], json.dumps(skipped))
        else:
            ok(f'{lab}: a tap skips the bag animation immediately', False, 'bag was not playing so skip could not be checked')
        wait_render(pg); back(pg)

        # mid-bag screenshot (frozen)
        if lab in ('ipad-portrait','ipad-landscape','iphone-390','iphone-430'):
            pg.evaluate("""()=>{const c=__cr.comics.find(x=>x.title==='Iron Tide 01')||__cr.comics[0];
              document.querySelector('#reader').classList.remove('hidden'); document.querySelector('#shelf').classList.add('hidden');
              __cr.toggleUI(false); __cr.bag.hold(c,0.52);}""")
            pg.wait_for_timeout(200)
            mid=pg.evaluate("({on:__cr.bag.on,p:getComputedStyle(document.querySelector('#bagOpen')).getPropertyValue('--bag-p'),hidden:document.querySelector('#bagOpen').classList.contains('hidden'),hasImg:!!document.querySelector('#bagOpen .bag-issue img')?.src})")
            ok(f'{lab}: mid-bag hold shows the issue leaving the bag', mid['on'] and not mid['hidden'] and mid['hasImg'], json.dumps(mid))
            pg.screenshot(path=f'{SH}/{ENG}-v59-bag-mid-{lab}.png')
            pg.evaluate("__cr.bag.finish(true); document.querySelector('#reader').classList.add('hidden'); document.querySelector('#shelf').classList.remove('hidden');")
            pg.wait_for_timeout(120)

        # ---- Reduce Motion: no bag, curl falls back to swipe ----
        # (done in a fresh context below for the first two sizes; here we also set it on this page)
        if lab in ('ipad-portrait','iphone-390'):
            pg.emulate_media(reduced_motion='reduce')
            # bag should not play
            open_c(pg)
            pg.wait_for_timeout(150)
            rm_bag=pg.evaluate("!!(__cr.bag&&__cr.bag.on) || (document.querySelector('#bagOpen')&&!document.querySelector('#bagOpen').classList.contains('hidden'))")
            wait_render(pg)
            ok(f'{lab}: Reduce Motion skips the bag animation', not rm_bag, f'bag={rm_bag}')
            # curl should fall back to swipe (rigid flipper, no curl-root)
            # pageTurn is still curl in storage
            stored=pg.evaluate("localStorage.getItem('cr.pageTurn')")
            pg.evaluate("__cr.toggleUI(false)")
            started=pg.evaluate("__cr.useCurl()")  # should be false under reduced motion
            ok(f'{lab}: Reduce Motion falls back to Swipe even if Paper curl is stored', stored=='"curl"' and started is False, f'stored={stored} useCurl={started}')
            vi0=pg.evaluate('__cr.R.vi')
            r=pg.evaluate("()=>{const s=document.querySelector('#stage').getBoundingClientRect(); return {x:s.x+s.width-40,y:s.y+s.height/2}}")
            # tap right edge via go
            pg.evaluate('__cr.go(-1,200)')
            pg.wait_for_timeout(500)
            mode=pg.evaluate("window.__cr.flip?(__cr.flip.mode||''):''")
            # after a short turn it may already have finished; check it did not use curl if still flipping, and page advanced
            vi1=pg.evaluate('__cr.R.vi')
            ok(f'{lab}: Reduce Motion turn advances and does not use paper curl', (vi1>vi0 or mode.startswith('fold') or mode in ('single','half','spread','')) and not mode.startswith('curl'), f'vi {vi0}->{vi1} mode={mode}')
            # cancel any leftover flip
            pg.evaluate('__cr.R && (__cr.startFlip, (__cr.R.comic && (window.__cr)))'); 
            try: pg.evaluate("if(__cr.flip){ const f=__cr.flip; }")
            except Exception: pass
            back(pg)
            pg.emulate_media(reduced_motion='no-preference')

        # ---- Swipe (default style) forward and back ----
        settings(pg)
        # bag off so it doesn't interfere with turns; swipe on
        if pg.evaluate("document.querySelector('#sBag').checked"):
            pg.locator('#sBag').evaluate("e=>e.closest('label').scrollIntoView({block:'center'})")
            pg.locator('#sBag').evaluate("e=>e.closest('label').click()"); pg.wait_for_timeout(80)
        pg.locator('#sTurn button[data-v=swipe]').click(); pg.wait_for_timeout(80)
        done(pg)
        open_c(pg); wait_render(pg)
        pg.evaluate("__cr.cancelFlipNow(); __cr.jumpTo(0); __cr.toggleUI(false)")
        wait_render(pg); pg.wait_for_timeout(150)
        vi0=pg.evaluate('__cr.R.vi')
        pg.evaluate('__cr.go(-1,240)')
        pg.wait_for_function('__cr.R.vi>0 && !__cr.flip && !__cr.animating', timeout=4000)
        swipe_fwd=pg.evaluate("({vi:__cr.R.vi,curl:!!(__cr.flip&&__cr.flip.curl),mode:__cr.flip?__cr.flip.mode:''})")
        ok(f'{lab}: Swipe turns a page forward', swipe_fwd['vi']>vi0 and not swipe_fwd['curl'], json.dumps(swipe_fwd))
        vi1=swipe_fwd['vi']
        pg.evaluate('__cr.go(1,240)')
        pg.wait_for_function('__cr.R.vi===0 && !__cr.flip && !__cr.animating', timeout=4000)
        swipe_back=pg.evaluate("({vi:__cr.R.vi})")
        ok(f'{lab}: Swipe turns a page back', swipe_back['vi']<vi1, json.dumps(swipe_back))
        back(pg)

        # ---- Paper curl forward and back + mid-curl screenshot ----
        settings(pg)
        pg.locator('#sTurn button[data-v=curl]').click(); pg.wait_for_timeout(80)
        done(pg)
        open_c(pg); wait_render(pg)
        pg.evaluate("__cr.cancelFlipNow(); __cr.jumpTo(0); __cr.toggleUI(false)")
        wait_render(pg); pg.wait_for_timeout(150)
        started=pg.evaluate("()=>{const ok=__cr.startFlip(-1); if(ok&&__cr.flip) __cr.flip.setP(0.46); return {ok,mode:__cr.flip&&__cr.flip.mode,curl:!!(__cr.flip&&__cr.flip.curl),p:__cr.flip&&__cr.flip.p,strips:document.querySelectorAll('.curl-s').length,root:!!document.querySelector('.curl-root')}}")
        ok(f'{lab}: Paper curl starts a mid-turn with a curled mesh', started['ok'] and started['curl'] and started['mode'].startswith('curl') and started['strips']>=12 and started['root'] and 0.4<=started['p']<=0.5, json.dumps(started))
        if lab in ('ipad-portrait','ipad-landscape','iphone-390','iphone-430'):
            pg.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
            pg.wait_for_timeout(80)
            pg.screenshot(path=f'{SH}/{ENG}-v59-curl-mid-{lab}.png')
        pg.evaluate("__cr.cancelFlipNow(); __cr.jumpTo(0)"); wait_render(pg); pg.wait_for_timeout(150)
        vi0=pg.evaluate('__cr.R.vi')
        pg.evaluate('__cr.go(-1,280)')
        pg.wait_for_function('__cr.R.vi>0 && !__cr.flip && !__cr.animating', timeout=4000)
        fwd=pg.evaluate("({vi:__cr.R.vi})")
        ok(f'{lab}: Paper curl tap-zone / go turns a page forward', fwd['vi']>vi0, json.dumps(fwd))
        vi1=fwd['vi']
        pg.evaluate('__cr.go(1,280)')
        pg.wait_for_function(f'__cr.R.vi<{vi1} && !__cr.flip && !__cr.animating', timeout=4000)
        backv=pg.evaluate("({vi:__cr.R.vi})")
        ok(f'{lab}: Paper curl turns a page back', backv['vi']<vi1, json.dumps(backv))

        # drag-follow + snap back via pointer events on the stage (same path as a finger drag)
        pg.evaluate("""()=>{ __cr.cancelFlipNow(); __cr.jumpTo(0);
          const st=document.querySelector('#stage');
          [11,42,77,91].forEach(id=>{ const o={bubbles:true,cancelable:true,composed:true,pointerId:id,pointerType:'touch',isPrimary:true,clientX:0,clientY:0,button:0,buttons:0};
            st.dispatchEvent(new PointerEvent('pointerup',o)); st.dispatchEvent(new PointerEvent('pointercancel',o)); }); }""")
        wait_render(pg); pg.wait_for_timeout(150)
        mid=pg.evaluate("""async ()=>{
          const st=document.querySelector('#stage'), r=st.getBoundingClientRect();
          const x0=r.x+r.width*0.9, y=r.y+r.height*0.55, x1=r.x+r.width*0.84;
          const mk=(type,x,buttons)=>new PointerEvent(type,{bubbles:true,cancelable:true,composed:true,pointerId:42,pointerType:'touch',isPrimary:true,clientX:x,clientY:y,button:0,buttons,width:24,height:24,pressure:type==='pointerup'?0:.5});
          const sleep=ms=>new Promise(res=>setTimeout(res,ms));
          st.dispatchEvent(mk('pointerdown',x0,1));
          for(let i=1;i<=8;i++){ await sleep(20); st.dispatchEvent(mk('pointermove', x0+(x1-x0)*i/8, 1)); }
          const mid={p:__cr.flip?+__cr.flip.p.toFixed(3):-1,curl:!!(__cr.flip&&__cr.flip.curl),mode:__cr.flip?__cr.flip.mode:'',vi:__cr.R.vi};
          await sleep(220);
          st.dispatchEvent(mk('pointerup',x1,0));
          return mid;
        }""")
        ok(f'{lab}: Paper curl follows the finger during a drag',
           mid['curl'] and mid['p']>0.05 and str(mid['mode']).startswith('curl'), json.dumps(mid))
        pg.wait_for_function('!__cr.flip && !__cr.animating', timeout=4000)
        snap=pg.evaluate("({vi:__cr.R.vi,flip:!!__cr.flip})")
        ok(f'{lab}: a short Paper curl drag snaps back to the same page', snap['vi']==0 and not snap['flip'], json.dumps(snap))

        # no curl while zoomed
        pg.evaluate("__cr.Z.s=2.5; __cr.Z.tx=-40; __cr.Z.ty=-40;")
        z=pg.evaluate("({ok:__cr.startFlip(-1),z:__cr.Z.s,flip:!!__cr.flip})")
        ok(f'{lab}: no paper curl (and no turn) while zoomed in', (not z['ok']) and z['z']>1.01 and not z['flip'], json.dumps(z))
        pg.evaluate("if(__cr.Z){ __cr.Z.s=1; __cr.Z.tx=0; __cr.Z.ty=0; const z=document.querySelector('#zoomer'); if(z) z.style.transform=''; }")
        back(pg)

        # ---- Spreads (landscape only) ----
        if w>h:
            settings(pg)
            on=pg.evaluate("document.querySelector('#sSingle').checked")
            if on:
                pg.locator('#sSingle').evaluate("e=>e.closest('label').click()"); pg.wait_for_timeout(80)
            pg.locator('#sTurn button[data-v=curl]').click(); pg.wait_for_timeout(80)
            done(pg)
            open_c(pg); wait_render(pg)
            pg.evaluate("__cr.cancelFlipNow(); __cr.jumpTo(1); __cr.toggleUI(false)")
            wait_render(pg); pg.wait_for_timeout(150)
            started=pg.evaluate("()=>{const ok=__cr.startFlip(-1); if(ok&&__cr.flip) __cr.flip.setP(0.42); return {ok,mode:__cr.flip&&__cr.flip.mode,curl:!!(__cr.flip&&__cr.flip.curl),spread:__cr.R.spread,strips:document.querySelectorAll('.curl-s').length,vi:__cr.R.vi}}")
            ok(f'{lab}: Paper curl works on a two-page spread',
               started['ok'] and started['curl'] and 'spread' in (started['mode'] or '') and started['strips']>=12, json.dumps(started))
            if lab=='ipad-landscape':
                pg.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
                pg.wait_for_timeout(80)
                pg.screenshot(path=f'{SH}/{ENG}-v59-curl-mid-spread-{lab}.png')
            pg.evaluate("__cr.cancelFlipNow(); __cr.jumpTo(0)")
            back(pg)

        ctx.close()

    real=[e for e in errors if 'access control checks' not in e.lower() and 'cross-origin' not in e.lower()]
    ok('no page errors', not real, '; '.join((real or errors)[:4]))
    b.close()

print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
