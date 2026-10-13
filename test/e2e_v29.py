"""cr-v29 suite: two-page spreads.  python3 test/e2e_v29.py [webkit]  (server on 127.0.0.1:8823)
Fixture: original abstract comic from test/gen_spreads.py (pages 3 and 6 are wide spreads). Standalone insets via --sat/--sab."""
import sys, os, json, subprocess
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); F=os.path.join(HERE,'..','testpdfs','spreads','Wide_Horizon_01.pdf'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(F): subprocess.run([sys.executable,os.path.join(HERE,'gen_spreads.py')],check=True)
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:260] if not cond else '',flush=True)
PINCH='''async ({cx,cy,d0,d1})=>{ const st=document.querySelector('#stage'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const ev=(t,id,x,y)=>st.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:id,pointerType:'touch',isPrimary:id===31,clientX:x,clientY:y,buttons:t==='pointerup'?0:1}));
  ev('pointerdown',31,cx-d0/2,cy); await sleep(10); ev('pointerdown',32,cx+d0/2,cy);
  for(let i=1;i<=10;i++){ const d=d0+(d1-d0)*i/10; await sleep(16); ev('pointermove',31,cx-d/2,cy); ev('pointermove',32,cx+d/2,cy); }
  ev('pointerup',31,cx-d1/2,cy); ev('pointerup',32,cx+d1/2,cy); await sleep(400); return window.__cr.Z.s; }'''
ST="""(()=>{const st=document.querySelector('#stage').getBoundingClientRect(), v=document.querySelector('#zoomer .view'), pgs=[...v.querySelectorAll('.pg')].map(e=>{const r=e.getBoundingClientRect(); return {p:+e.dataset.p,x:r.x,y:r.y,w:r.width,h:r.height}});
  const rb=document.querySelector('#rRotate'), rr=rb.getBoundingClientRect(); return {W:st.width,H:st.height,vi:__cr.R.vi,view:__cr.R.views[__cr.R.vi],views:__cr.R.views,rot:v.classList.contains('rot'),pgs,
  btn:!rb.classList.contains('hidden')&&rb.offsetParent!==null,bw:rr.width,bh:rr.height,bb:rr.bottom,pressed:rb.getAttribute('aria-pressed'),bg:getComputedStyle(document.querySelector('#stage')).backgroundColor,txt:document.querySelector('#pgText').textContent}})()"""
def wait(pg): pg.wait_for_timeout(250); pg.wait_for_function('!__cr.animating && !__cr.flip && document.querySelectorAll(".view .pg.loading").length===0',timeout=15000); pg.wait_for_timeout(250)
def jump(pg,p): pg.evaluate(f'__cr.jumpTo({p})'); wait(pg); return pg.evaluate(ST)
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1024,1366,'ipad-portrait',2,24,20),(1366,1024,'ipad-landscape',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        pg.set_input_files('#fileIn',[F]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==1 && !document.querySelector(".toast .tb")',timeout=60000)
        pg.click('#tabs [data-tab=library]'); pg.click('#libGrid .lc'); pg.wait_for_selector('#reader:not(.hidden)'); wait(pg)
        land=w>h
        s=jump(pg,1)
        ok(f'{lab}: ordinary page -> no Rotate button',not s['btn'],json.dumps(s))
        s=jump(pg,2); g=s['pgs'][0]
        if land:
            ok(f'{lab}: 2-up views: spreads stand alone, never paired with a neighbour',s['views']==[[None,0],[1,None],[2],[3,4],[5],[6,7],[8]],json.dumps(s['views']))
            ok(f'{lab}: spread shown full screen as one page (fills width or height, centred)',len(s['pgs'])==1 and (g['w']>=s['W']-2 or g['h']>=s['H']-2) and abs(g['x']+g['w']/2-s['W']/2)<2 and abs(g['y']+g['h']/2-s['H']/2)<2,json.dumps(s['pgs']))
            ok(f'{lab}: no Rotate button in landscape',not s['btn'])
            seq=[]; pg.evaluate('__cr.jumpTo(1)'); wait(pg)
            for k in range(5): pg.evaluate('__cr.go(-1)'); wait(pg); seq.append(pg.evaluate('__cr.R.views[__cr.R.vi]'))
            for k in range(3): pg.evaluate('__cr.go(1)'); wait(pg); seq.append(pg.evaluate('__cr.R.views[__cr.R.vi]'))
            ok(f'{lab}: page turns step pair -> spread -> pair -> spread and back',seq==[[2],[3,4],[5],[6,7],[8],[6,7],[5],[3,4]],json.dumps(seq))
            s=jump(pg,5); pg.screenshot(path=f'{SH}/{ENG}-v29-spread-{lab}.png')
        else:
            ok(f'{lab}: spread fitted to full width, centred vertically, black around',len(s['pgs'])==1 and abs(g['w']-s['W'])<=2 and abs(g['y']+g['h']/2-s['H']/2)<2 and g['h']<s['H']*.8 and s['bg'] in ('rgb(0, 0, 0)',) and s['view']==[2],json.dumps(s))
            ok(f'{lab}: Rotate button shown on the spread, >=40px, above the home indicator',s['btn'] and s['bw']>=40 and s['bh']>=40 and s['bb']<=s['H']-sab,json.dumps(s))
            if lab=='ipad-portrait': pg.screenshot(path=f'{SH}/{ENG}-v29-spread-portrait-{lab}.png')
            pg.click('#rRotate'); wait(pg); s=pg.evaluate(ST); g=s['pgs'][0]
            ok(f'{lab}: Rotate turns the spread 90° in the view and it fills the portrait screen',s['rot'] and s['pressed']=='true' and g['h']>g['w']*1.2 and (g['h']>=s['H']*.9 or g['w']>=s['W']-2) and g['h']<=s['H']+1 and g['w']<=s['W']+1 and abs(g['x']+g['w']/2-s['W']/2)<2,json.dumps(s))
            if lab=='ipad-portrait':
                pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(300); pg.screenshot(path=f'{SH}/{ENG}-v29-spread-rotated-{lab}.png')
            z=pg.evaluate(PINCH,{'cx':s['W']/2,'cy':s['H']/2,'d0':100,'d1':240}); ok(f'{lab}: pinch zoom on the rotated spread',z>1.5,f'z={z}')
            pg.wait_for_timeout(500); hi=pg.evaluate("document.querySelectorAll('.view.rot .pg canvas.tile').length"); ok(f'{lab}: sharp re-render while zoomed (rotated)',hi>=1,hi)
            pg.evaluate('__cr.toggleUI(true)'); pg.click('#rRotate'); wait(pg); s=pg.evaluate(ST)
            ok(f'{lab}: tap Rotate again -> upright, zoom reset',not s['rot'] and s['pressed']=='false' and pg.evaluate('__cr.Z.s')==1,json.dumps(s))
            z=pg.evaluate(PINCH,{'cx':s['W']/2,'cy':s['H']/2,'d0':100,'d1':240}); ok(f'{lab}: pinch zoom on the upright spread',z>1.5,f'z={z}')
            pg.evaluate('__cr.Z.s=1;__cr.Z.tx=0;__cr.Z.ty=0'); s=jump(pg,2); pg.click('#rRotate'); wait(pg)
            pg.evaluate('__cr.go(-1)'); wait(pg); s=pg.evaluate(ST)
            ok(f'{lab}: page turn from a rotated spread -> next page upright, no Rotate button',s['view']==[3] and not s['rot'] and not s['btn'],json.dumps(s))
            pg.evaluate('__cr.go(1)'); wait(pg); s=pg.evaluate(ST); ok(f'{lab}: turning back lands on the spread (upright, button back)',s['view']==[2] and not s['rot'] and s['btn'],json.dumps(s))
            pg.click('#rRotate'); wait(pg)
            pe=pg.evaluate("__cr.panels.enter({x:innerWidth/2,y:innerHeight/2}).then(()=>new Promise(r=>setTimeout(r,900))).then(()=>({on:__cr.panels.P.on,rot:!!document.querySelector('.view.rot')}))")
            ok(f'{lab}: panel view works on a spread (rotation drops for panel view)',pe['on'] and not pe['rot'],json.dumps(pe))
            pg.evaluate('__cr.panels.exit(false)'); wait(pg)
            if lab=='ipad-portrait':
                ctx2=pg; pg.set_viewport_size({'width':1366,'height':1024}); pg.wait_for_timeout(700); wait(pg); s=pg.evaluate(ST)
                ok('rotating the iPad to landscape: spread full screen, alone, no Rotate button',s['view']==[2] and not s['btn'] and not s['rot'],json.dumps(s))
        ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
