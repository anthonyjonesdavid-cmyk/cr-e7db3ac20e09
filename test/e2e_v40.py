"""cr-v40 suite: back-issue bin + night at the comic shop (+ rain sound) in the Timeline tab.  python3 test/e2e_v40.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: original abstract comics (test/gen_pdfs.py, test/gen_dates.py). Standalone insets via --sat/--sab."""
import sys, os, json, glob, subprocess
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); D=os.path.join(T,'dates'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(os.path.join(D,'Deep_Signal_02.pdf')): subprocess.run([sys.executable,os.path.join(HERE,'gen_dates.py')],check=True)
FILES=sorted(glob.glob(os.path.join(T,'*.pdf')))+sorted(glob.glob(os.path.join(D,'*.pdf')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
VIS="""(()=>{ const W=window.__vis={hidden:false}; Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>W.hidden?'hidden':'visible'});
  W.set=h=>{ W.hidden=h; document.dispatchEvent(new Event('visibilitychange')); }; })()"""
BS="""(()=>{const B=__cr.bin.BIN, els=[...document.querySelectorAll('#binCards .bn-c')], shown=els.filter(e=>e.style.display!=='none'), lift=shown.filter(e=>e.classList.contains('lift')), r=e=>e.getBoundingClientRect();
  const L=lift[0], nxt=shown.find(e=>+e.dataset.k===Math.round(B.pos)+1);
  return {on:B.on,vis:!document.querySelector('#bin').classList.contains('hidden'),pos:B.pos,n:B.ids.length,slots:els.length,shown:shown.length,lift:lift.length,liftK:L?+L.dataset.k:null,liftId:L&&L.dataset.id,
    liftTop:L&&r(L).top,nextTop:nxt&&r(nxt).top,peek:shown.filter(e=>+e.dataset.k>Math.round(B.pos)&&r(e).top<(L?r(L).top:0)-4).length,liftH:L&&r(L).height,uniq:new Set(B.ids).size,raf:!!B.raf}})()"""
def swipe(pg,dy,steps=6,dt=14):
    pg.evaluate("""async ({dy,steps,dt})=>{ const st=document.querySelector('#binStage'), r=st.getBoundingClientRect(), x=r.left+r.width/2, y=r.top+r.height*.3; const sl=ms=>new Promise(q=>setTimeout(q,ms));
      const ev=(t,yy)=>st.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:9,pointerType:'touch',isPrimary:true,clientX:x,clientY:yy,buttons:t==='pointerup'?0:1}));
      ev('pointerdown',y); for(let i=1;i<=steps;i++){ await sl(dt); ev('pointermove',y+dy*i/steps); } ev('pointerup',y+dy); }""",{'dy':dy,'steps':steps,'dt':dt})
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(VIS); ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
        hm=pg.evaluate("({bin:!!document.querySelector('#homeScroll #tlBin,#homeScroll .bn-c'),night:document.querySelector('#homeScroll .rkmood')!==null})")
        ok(f'{lab}: Home unchanged (no bin / night controls on Home)',not hm['bin'] and not hm['night'],json.dumps(hm))
        pg.click('#tabs [data-tab=timeline]'); pg.wait_for_timeout(300)
        bb=pg.locator('#tlBin').bounding_box(); rb=pg.locator('#tlRack').bounding_box()
        ok(f'{lab}: Bin button beside the rack button in the Timeline bar, >=40px',bb['width']>=40 and bb['height']>=40 and abs(bb['y']-rb['y'])<2 and abs(bb['x']+bb['width']-rb['x'])<12,json.dumps([bb,rb]))
        # ---------- bin ----------
        pg.click('#tlBin'); pg.wait_for_timeout(400); s=pg.evaluate(BS)
        ok(f'{lab}: bin opens from the whole library, front comic lifted above the row (tops of the others showing)',s['vis'] and s['n']==len(FILES) and s['uniq']==s['n'] and s['lift']==1 and s['liftK']==0 and s['peek']>=3,json.dumps(s))
        cb=pg.locator('#binClose').bounding_box(); dg=pg.locator('#binDig').bounding_box()
        ok(f'{lab}: close and Dig buttons >=40px, below the status bar',cb['height']>=40 and cb['width']>=40 and dg['height']>=40 and cb['y']>=sat,json.dumps([cb,dg]))
        if lab in ('ipad-portrait','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v40-bin-{lab}.png')
        swipe(pg,90,steps=8,dt=30); pg.wait_for_function('!__cr.bin.BIN.raf',timeout=4000); pg.wait_for_timeout(50); s1=pg.evaluate(BS)
        ok(f'{lab}: slow drag riffles forward one card and snaps',s1['pos']==1 and s1['liftK']==1,json.dumps(s1))
        t=pg.evaluate("""(async()=>{ const B=__cr.bin.BIN, t0=performance.now(); __cr.bin.to(Math.round(B.pos)+1); while(B.raf) await new Promise(r=>requestAnimationFrame(r)); return {ms:Math.round(performance.now()-t0),pos:B.pos,dur:B.lastDur}})()""")
        ok(f'{lab}: a single flip is quick (120ms animation)',t['pos']==2 and t['dur']==120 and t['ms']<=700,json.dumps(t))
        swipe(pg,260,steps=4,dt=10); pg.wait_for_function('!__cr.bin.BIN.raf',timeout=4000); pg.wait_for_timeout(100); s2=pg.evaluate(BS)
        ok(f'{lab}: fast swipe carries momentum (several cards)',s2['pos']>=8 and s2['pos']==int(s2['pos']),json.dumps(s2))
        if lab=='ipad-portrait':
            mid=pg.evaluate("""(async()=>{ __cr.bin.to(__cr.bin.BIN.pos+1,400); await new Promise(r=>setTimeout(r,150)); return __cr.bin.BIN.pos })()"""); pg.screenshot(path=f'{SH}/{ENG}-v40-bin-flipping-{lab}.png'); pg.wait_for_timeout(500)
            ok('mid-flip frame captured between cards',mid%1!=0,mid)
            s2=pg.evaluate(BS)
        before=pg.evaluate("__cr.bin.BIN.ids.slice()"); pos=int(s2['pos'])
        pg.click('#binDig'); pg.wait_for_timeout(500); after=pg.evaluate("__cr.bin.BIN.ids.slice()"); s3=pg.evaluate(BS)
        ok(f'{lab}: Dig shuffles in a random handful right after the front comic and flips to it',sorted(after)==sorted(before) and after[:pos+1]==before[:pos+1] and after[pos+1:pos+9]!=before[pos+1:pos+9] and s3['pos']==pos+1,json.dumps([pos,s3['pos']]))
        lb=pg.locator('#binCards .bn-c.lift').bounding_box(); want=s3['liftId']
        pg.mouse.click(lb['x']+lb['width']/2,lb['y']+lb['height']*.35); pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(400)
        ok(f'{lab}: tapping the lifted comic opens it',pg.evaluate('__cr.R.comic.id')==want)
        pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
        ok(f'{lab}: back from the reader returns to the bin',pg.evaluate("!document.querySelector('#bin').classList.contains('hidden')"))
        pg.click('#binClose'); pg.wait_for_timeout(200); ok(f'{lab}: close button closes the bin (Timeline underneath)',pg.evaluate("document.querySelector('#bin').classList.contains('hidden')") and pg.is_visible('#timeline'))
        if lab=='ipad-landscape':
            v=pg.evaluate("""(async()=>{ const base=__cr.comics[0], keep=__cr.comics.slice(); for(let i=0;i<2000;i++) __cr.comics.push({...base,id:'syn'+i,title:'Syn '+i});
              const t0=performance.now(); __cr.bin.open(); const t1=performance.now(); const B=__cr.bin.BIN; let worst=0;
              for(let i=0;i<40;i++){ const a=performance.now(); __cr.bin.to(B.pos+1,1); await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))); worst=Math.max(worst,performance.now()-a); }
              const r={n:B.ids.length,slots:document.querySelectorAll('#binCards .bn-c').length,shown:[...document.querySelectorAll('#binCards .bn-c')].filter(e=>e.style.display!=='none').length,open:Math.round(t1-t0),pos:B.pos,worst:Math.round(worst)};
              __cr.bin.close(); __cr.comics.splice(0,__cr.comics.length,...keep); return r})()""")
            ok('large library (2,000+): virtualized to 30 cards, opens fast, flips stay cheap',v['n']>2000 and v['slots']==30 and v['shown']<=30 and v['open']<300 and v['pos']==40,json.dumps(v))
        # ---------- night at the comic shop ----------
        pg.click('#tlRack'); pg.wait_for_selector('#rack:not(.hidden)'); pg.wait_for_timeout(300)
        n0=pg.evaluate("({p:document.querySelector('#rkNight').getAttribute('aria-pressed'),cls:document.querySelector('#rack').classList.contains('night'),st:localStorage.getItem('cr.nightShop'),rain:document.querySelector('#rkRain').getAttribute('aria-pressed')})")
        ok(f'{lab}: Night and Rain toggles on the rack screen, both off by default',n0['p']=='false' and not n0['cls'] and n0['st'] is None and n0['rain']=='false',json.dumps(n0))
        nb=pg.locator('#rkNight').bounding_box(); rb2=pg.locator('#rkRain').bounding_box()
        ok(f'{lab}: Night / Rain tap targets >=40px, above the home indicator',nb['height']>=40 and nb['width']>=40 and rb2['height']>=40 and nb['y']+nb['height']<=h-sab,json.dumps([nb,rb2]))
        a0=pg.evaluate('__cr.rack.RK.a'); pg.wait_for_timeout(1500); ok(f'{lab}: night off: the rack does not auto-rotate',pg.evaluate('__cr.rack.RK.a')==a0)
        pg.click('#rkNight'); pg.wait_for_timeout(300)
        n1=pg.evaluate("""(()=>{const st=document.querySelector('#rkStage'), lamp=document.querySelector('.rklamp'), vig=document.querySelector('.rkvig');
          return {cls:document.querySelector('#rack').classList.contains('night'),st:localStorage.getItem('cr.nightShop'),lampIn:lamp.parentElement===st,vigIn:vig.parentElement===st,inRotor:!!document.querySelector('#rkRotor .rklamp,#rkRotor .rkvig'),
            lampBg:getComputedStyle(lamp).backgroundImage.includes('radial-gradient'),imgs:getComputedStyle(lamp).backgroundImage.includes('url('),z3d:getComputedStyle(lamp).transform}})()""")
        ok(f'{lab}: night on: dim shop + warm lamp (CSS gradients only), stored; glow layers are flat siblings of the 3D scene (not inside the rotor)',n1['cls'] and n1['st']=='true' and n1['lampIn'] and n1['vigIn'] and not n1['inRotor'] and n1['lampBg'] and not n1['imgs'] and n1['z3d']=='none',json.dumps(n1))
        pg.wait_for_timeout(1400); a1=pg.evaluate('__cr.rack.RK.a'); pg.wait_for_timeout(600); a2=pg.evaluate('({a:__cr.rack.RK.a,auto:__cr.rack.RK.auto})')
        ok(f'{lab}: night on + idle: the rack slowly auto-rotates',a2['auto'] and a1-a2['a']>=.4 and a1-a2['a']<12,json.dumps([a1,a2]))
        if lab in ('ipad-portrait','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v40-nightshop-{lab}.png')
        st=pg.locator('#rkStage').bounding_box(); pg.mouse.move(st['x']+20,st['y']+st['height']*.3); pg.mouse.down(); pg.wait_for_timeout(50)
        p1=pg.evaluate('({a:__cr.rack.RK.a,auto:__cr.rack.RK.auto})'); pg.wait_for_timeout(300); p2=pg.evaluate('__cr.rack.RK.a'); pg.mouse.up()
        ok(f'{lab}: touch pauses the auto-rotation',not p1['auto'] and abs(p2-p1['a'])<.01,json.dumps([p1,p2]))
        pg.wait_for_timeout(500); p3=pg.evaluate('__cr.rack.RK.auto'); pg.wait_for_timeout(1500); p4=pg.evaluate('__cr.rack.RK.auto')
        ok(f'{lab}: resumes after the idle delay (5s; 0.7s in tests)',not p3 and p4,json.dumps([p3,p4]))
        if lab=='ipad-portrait':
            pg.emulate_media(reduced_motion='reduce'); pg.wait_for_timeout(200); a3=pg.evaluate('__cr.rack.RK.a'); pg.wait_for_timeout(2000)
            ok('prefers-reduced-motion: no auto-rotate',not pg.evaluate('__cr.rack.RK.auto') and pg.evaluate('__cr.rack.RK.a')==a3); pg.emulate_media(reduced_motion='no-preference')
            # frame-to-frame stability while auto-rotating: the sign/glow layers never swap order (v37 lesson)
            pg.wait_for_timeout(1500); fl=pg.evaluate("""(async()=>{ const s=document.querySelector('.rksign'), out=[]; for(let i=0;i<30;i++){ await new Promise(r=>requestAnimationFrame(r)); const r=s.getBoundingClientRect(), e=document.elementFromPoint(r.left+r.width/2,r.top+r.height*.5); out.push(e===s||(e&&(e.className||e.tagName))); } return out })()""")
            ok('sign stays on top every frame while auto-rotating (no flicker)',all(x is True for x in fl),json.dumps(fl))
            # Settings mirror + persistence
            pg.click('#rkBack'); pg.wait_for_timeout(200); pg.click('#tabs [data-tab=home]'); pg.click('#settingsBtn'); pg.wait_for_selector('#sNight')
            ok('Settings mirrors the Night toggle (on) and has Rain (off)',pg.evaluate("document.querySelector('#sNight').checked") and not pg.evaluate("document.querySelector('#sRain').checked"))
            pg.locator('#sNight').evaluate("e=>e.closest('label').scrollIntoView({block:'center'})"); pg.wait_for_timeout(150); pg.screenshot(path=f'{SH}/{ENG}-v40-settings-night-{lab}.png')
            pg.locator('#sNight').evaluate("e=>e.closest('label').click()"); pg.wait_for_timeout(100); ok('turning Night off in Settings is stored',pg.evaluate("localStorage.getItem('cr.nightShop')")=='false')
            pg.locator('#sNight').evaluate("e=>e.closest('label').click()"); pg.click('[data-r=done]'); pg.wait_for_timeout(200)
            pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.click('#tabs [data-tab=timeline]'); pg.click('#tlRack'); pg.wait_for_selector('#rack:not(.hidden)'); pg.wait_for_timeout(300)
            ok('Night persists across reload',pg.evaluate("document.querySelector('#rack').classList.contains('night')"))
            # ---------- rain ----------
            ok('rain off by default: no audio',not pg.evaluate('__cr.rain.playing'))
            pg.click('#rkRain'); pg.wait_for_timeout(300); r1=pg.evaluate("({p:__cr.rain.playing,st:localStorage.getItem('cr.rainSound'),ctx:__cr.rain.ctx&&__cr.rain.ctx.state,btn:document.querySelector('#rkRain').getAttribute('aria-pressed')})")
            ok('Rain toggle (a tap) starts Web Audio filtered-noise rain; stored',r1['p'] and r1['st']=='true' and r1['btn']=='true' and r1['ctx'] in ('running','suspended'),json.dumps(r1))
            pg.evaluate('__vis.set(true)'); pg.wait_for_timeout(100); ok('app hidden: rain stops',not pg.evaluate('__cr.rain.playing'))
            pg.evaluate('__vis.set(false)'); pg.wait_for_timeout(100); ok('visible again on the rack: rain resumes',pg.evaluate('__cr.rain.playing'))
            pg.click('#rkBack'); pg.wait_for_timeout(100); ok('back on the Timeline list: still raining',pg.evaluate('__cr.rain.playing'))
            pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(100); ok('leaving Timeline stops the rain',not pg.evaluate('__cr.rain.playing'))
            pg.click('#tabs [data-tab=timeline]'); pg.wait_for_timeout(100); ok('back to Timeline (a tap): rain resumes',pg.evaluate('__cr.rain.playing'))
            pg.click('#tlRack'); pg.wait_for_timeout(300); pg.click('#rkRain'); pg.wait_for_timeout(100); ok('Rain toggle off stops it',not pg.evaluate('__cr.rain.playing') and pg.evaluate("localStorage.getItem('cr.rainSound')")=='false')
            pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.evaluate("localStorage.setItem('cr.rainSound','true')"); pg.reload(); pg.wait_for_selector('html[data-ready]')
            pg.evaluate("document.querySelector('#tabs [data-tab=timeline]').click()") ; pg.wait_for_timeout(100)
            ok('rain never starts without a user tap (programmatic open after reload)',not pg.evaluate('__cr.rain.playing'))
            pg.click('#tabs [data-tab=home]'); pg.click('#tabs [data-tab=timeline]'); pg.wait_for_timeout(150); ok('first real tap unlocks it',pg.evaluate('__cr.rain.playing'))
        ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
