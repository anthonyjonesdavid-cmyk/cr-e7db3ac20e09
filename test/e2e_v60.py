"""cr-v60 suite: cleaner Paper curl on two-up / spreads, Home menus stay on screen.
python3 test/e2e_v60.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: Iron Tide 01, Wide Horizon 01 (spreads/)."""
import sys, os, json
from playwright.sync_api import sync_playwright
from PIL import Image
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=[os.path.join(T,'Iron_Tide_01.pdf'),os.path.join(T,'spreads','Wide_Horizon_01.pdf')]
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,'' if cond else str(extra)[:400],flush=True)

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
    pg.click('#settingsBtn'); pg.wait_for_selector('#sTurn')
def done(pg):
    pg.click('[data-r=done]'); pg.wait_for_timeout(200)

def prep_curl(pg):
    settings(pg)
    if pg.evaluate("document.querySelector('#sBag')&&document.querySelector('#sBag').checked"):
        pg.locator('#sBag').evaluate("e=>e.closest('label').scrollIntoView({block:'center'})")
        pg.locator('#sBag').evaluate("e=>e.closest('label').click()"); pg.wait_for_timeout(80)
    on=pg.evaluate("document.querySelector('#sSingle')&&document.querySelector('#sSingle').checked")
    if on:
        pg.locator('#sSingle').evaluate("e=>e.closest('label').click()"); pg.wait_for_timeout(80)
    pg.locator('#sTurn button[data-v=curl]').click(); pg.wait_for_timeout(80)
    done(pg)

def mid_curl(pg,p=0.46):
    return pg.evaluate(f"""()=>{{
      const ok=__cr.startFlip(-1);
      if(ok&&__cr.flip) __cr.flip.setP({p});
      const pgs=[...document.querySelectorAll('.view .pg')].map(el=>{{
        const r=el.getBoundingClientRect(), cs=getComputedStyle(el);
        return {{vis:cs.visibility, hidden:el.style.visibility, x:Math.round(r.x), w:Math.round(r.width), hasCv:!!el.querySelector('canvas')}};
      }});
      return {{ok,mode:__cr.flip&&__cr.flip.mode,curl:!!(__cr.flip&&__cr.flip.curl),p:__cr.flip&&__cr.flip.p,
        strips:document.querySelectorAll('.curl-s').length, imgs:document.querySelectorAll('.curl-front img').length,
        vi:__cr.R.vi, view:__cr.R.views[__cr.R.vi], next:__cr.R.views[__cr.R.vi+1],
        viewVis:__cr.R.viewEl&&getComputedStyle(__cr.R.viewEl).visibility, pgs}};
    }}""")

def not_black(path, box, min_var=12, min_mean=8):
    """box = (x0,y0,x1,y1) in image pixels. True if the region isn't a flat black field."""
    im=Image.open(path).convert('RGB')
    w,h=im.size
    x0,y0,x1,y1=box
    x0,y0=max(0,int(x0)),max(0,int(y0)); x1,y1=min(w,int(x1)),min(h,int(y1))
    if x1<=x0 or y1<=y0: return False, 'empty box'
    crop=im.crop((x0,y0,x1,y1))
    px=list(crop.getdata()); n=len(px)
    if n<50: return False, f'few pixels {n}'
    mean=tuple(sum(c[i] for c in px)/n for i in range(3))
    var=sum((c[0]-mean[0])**2+(c[1]-mean[1])**2+(c[2]-mean[2])**2 for c in px)/n
    # also reject "almost all near-black"
    dark=sum(1 for c in px if c[0]<12 and c[1]<12 and c[2]<12)/n
    return (var>=min_var and mean[0]+mean[1]+mean[2]>=min_mean and dark<0.85), {'mean':[round(x,1) for x in mean],'var':round(var,1),'dark':round(dark,3),'box':[x0,y0,x1,y1],'wh':[w,h]}

def low_seam_score(path, box, step=8):
    """Vertical-seam detector on column-mean differences. Flat art can have a 0 median, so
    judge by the 95th percentile and the mean, not a ratio against the median."""
    im=Image.open(path).convert('L')
    x0,y0,x1,y1=[int(v) for v in box]
    x0,y0=max(0,x0),max(0,y0); x1,y1=min(im.size[0],x1),min(im.size[1],y1)
    crop=im.crop((x0,y0,x1,y1))
    w,h=crop.size
    if w<20 or h<20: return 0, {'w':w,'h':h}
    pix=crop.load(); cols=[sum(pix[x,y] for y in range(h))/h for x in range(w)]
    diffs=[abs(cols[i]-cols[i-1]) for i in range(1,w)]
    mean_d=sum(diffs)/len(diffs)
    sd=sorted(diffs); med=sd[len(sd)//2]; top=sd[int(len(sd)*0.95)]
    return top, {'mean_d':round(mean_d,2),'med':round(med,2),'p95':round(top,2),'wh':[w,h]}

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    sizes=[(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34)]
    for (w,h,lab,dpr,sat,sab) in sizes:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crNoBag=true; localStorage.setItem('cr.homeRows','true'); document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}') if 'access control checks' not in str(e).lower() and 'cross-origin' not in str(e).lower() else None)
        pg.goto(URL); pg.wait_for_selector('html[data-ready]',timeout=60000); dismiss(pg)
        pg.set_input_files('#fileIn',FILES)
        pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=120000)

        prep_curl(pg)

        # ---- portrait / iPhone: mid-curl from the cover (single-page curl, should stay as clean as v59) ----
        if lab in ('ipad-portrait','iphone-390'):
            open_c(pg); wait_render(pg)
            pg.evaluate("__cr.cancelFlipNow(); __cr.jumpTo(0); __cr.toggleUI(false)"); wait_render(pg); pg.wait_for_timeout(200)
            started=mid_curl(pg,0.46)
            ok(f'{lab}: Paper curl mid-turn mesh', started['ok'] and started['curl'] and started['strips']>=12 and started['imgs']>=12, json.dumps(started))
            pg.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))"); pg.wait_for_timeout(80)
            path=f'{SH}/{ENG}-v60-curl-mid-{lab}.png'
            pg.screenshot(path=path)
            im=Image.open(path); ww,hh=im.size
            # the curled sheet + revealed page should not be a black field
            good,st=not_black(path,(ww*0.08,hh*0.12,ww*0.92,hh*0.88))
            ok(f'{lab}: mid-curl screenshot is a visible page curl (not a black frame)', good, json.dumps(st))
            pg.evaluate("__cr.cancelFlipNow(); __cr.jumpTo(0)")
            back(pg)

        # ---- landscape two-up: jump to the first interior pair (both slots filled) ----
        if lab=='ipad-landscape':
            open_c(pg,'Iron Tide 01'); wait_render(pg)
            info=pg.evaluate("""()=>{
              const R=__cr.R; let vi=-1;
              for(let k=0;k<R.views.length;k++){ const v=R.views[k]; if(v&&v.length===2&&v[0]!=null&&v[1]!=null){ vi=k; break; } }
              return {vi,view:vi>=0?R.views[vi]:null,spread:R.spread,n:R.views.length};
            }""")
            ok(f'{lab}: found an interior two-up view', info['vi']>=0 and info['spread'], json.dumps(info))
            pg.evaluate(f"__cr.cancelFlipNow(); __cr.jumpToView({info['vi']}); __cr.toggleUI(false)")
            wait_render(pg); pg.wait_for_timeout(200)
            started=mid_curl(pg,0.46)
            ok(f'{lab}: two-up Paper curl starts (curl-spread mode)', started['ok'] and started['curl'] and 'spread' in (started['mode'] or '') and started['strips']>=12, json.dumps(started))
            # the left neighbour in the current view must remain visible (not hidden with the turning right page)
            left_ok=started['viewVis']=='visible' and started['pgs'] and started['pgs'][0]['vis']=='visible' and started['pgs'][0]['hasCv']
            right_hidden=len(started['pgs'])>1 and started['pgs'][1]['vis']=='hidden'
            ok(f'{lab}: left page of the pair stays visible during the two-up curl', left_ok and right_hidden, json.dumps(started['pgs']))
            pg.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))"); pg.wait_for_timeout(80)
            path=f'{SH}/{ENG}-v60-curl-mid-{lab}.png'
            pg.screenshot(path=path)
            # left half of the pair should have real page pixels, not a black field
            # two-up pages are centred; sample the left page's inner area
            stg=pg.evaluate("(()=>{const r=document.querySelector('#stage').getBoundingClientRect(), d=window.devicePixelRatio||1; return {x:r.x*d,y:r.y*d,w:r.width*d,h:r.height*d,d};})()")
            lx,ly,lw,lh=stg['x'],stg['y'],stg['w'],stg['h']
            good,st=not_black(path,(lx+lw*0.08, ly+lh*0.18, lx+lw*0.42, ly+lh*0.82))
            ok(f'{lab}: mid-curl left neighbour is a real page (not black)', good, json.dumps(st))
            # turning (right) page should also have content and not look like a flat field
            goodR,stR=not_black(path,(lx+lw*0.55, ly+lh*0.18, lx+lw*0.92, ly+lh*0.82))
            ok(f'{lab}: mid-curl turning page has visible artwork', goodR, json.dumps(stR))
            ratio,seam=low_seam_score(path,(lx+lw*0.55, ly+lh*0.18, lx+lw*0.92, ly+lh*0.82))
            ok(f'{lab}: mid-curl turning page has no strong vertical strip seams', ratio<18, json.dumps({'p95':round(ratio,2),**seam}))
            pg.evaluate("__cr.cancelFlipNow()"); wait_render(pg)
            back(pg)

            # ---- landscape true spread (wide page, full width) ----
            open_c(pg,'Wide Horizon 01'); wait_render(pg)
            sp=pg.evaluate("""()=>{
              const R=__cr.R; let vi=-1;
              for(let k=0;k<R.views.length;k++){ const v=R.views[k]; if(v&&v.length===1&&v[0]<R.n&&(R.aspects[v[0]]||0)>1.2){ vi=k; break; } }
              return {vi,view:vi>=0?R.views[vi]:null,aspect:vi>=0?R.aspects[R.views[vi][0]]:null,spread:R.spread};
            }""")
            ok(f'{lab}: found a full-width spread view in Wide Horizon', sp['vi']>=0, json.dumps(sp))
            pg.evaluate(f"__cr.cancelFlipNow(); __cr.jumpToView({sp['vi']}); __cr.toggleUI(false)")
            wait_render(pg); pg.wait_for_timeout(200)
            started=mid_curl(pg,0.42)
            ok(f'{lab}: Paper curl works on a full-width spread', started['ok'] and started['curl'] and started['strips']>=12, json.dumps(started))
            pg.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))"); pg.wait_for_timeout(80)
            path=f'{SH}/{ENG}-v60-curl-mid-spread-{lab}.png'
            pg.screenshot(path=path)
            good,st=not_black(path,(lx+lw*0.08, ly+lh*0.12, lx+lw*0.92, ly+lh*0.88))
            ok(f'{lab}: mid-curl spread screenshot shows the turning spread', good, json.dumps(st))
            ratio,seam=low_seam_score(path,(lx+lw*0.15, ly+lh*0.18, lx+lw*0.85, ly+lh*0.82))
            ok(f'{lab}: mid-curl spread has no strong vertical strip seams', ratio<18, json.dumps({'p95':round(ratio,2),**seam}))
            pg.evaluate("__cr.cancelFlipNow()")
            back(pg)

        # Swipe still turns (regression) on this size
        settings(pg)
        pg.locator('#sTurn button[data-v=swipe]').click(); pg.wait_for_timeout(80)
        done(pg)
        open_c(pg); wait_render(pg)
        pg.evaluate("__cr.cancelFlipNow(); __cr.jumpTo(0); __cr.toggleUI(false)"); wait_render(pg)
        vi0=pg.evaluate('__cr.R.vi')
        pg.evaluate('__cr.go(-1,200)')
        pg.wait_for_function('__cr.R.vi>0 && !__cr.flip && !__cr.animating', timeout=4000)
        ok(f'{lab}: Swipe still turns a page forward', pg.evaluate('__cr.R.vi')>vi0)
        back(pg)

        # ---- Home menu stays inside the viewport (reading-list Delete) ----
        if lab=='ipad-portrait':
            # make a list so .qrow exists, then park the ••• near the bottom of the screen
            pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(200)
            pg.locator('.lc[data-title="Iron Tide 01"]').click(button='right'); pg.wait_for_selector('#aQueue'); pg.click('#aQueue'); pg.wait_for_timeout(200)
            if pg.locator('#qaName').count():
                pg.fill('#qaName','Inferno'); pg.click('#qaDone'); pg.wait_for_timeout(300)
            pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
            pg.wait_for_selector('.qrow .row-more')
            # scroll the row-more to the bottom of the home scroller so a downward menu would overflow
            pg.evaluate("""()=>{
              const row=document.querySelector('.qrow .row-more'), sc=document.querySelector('#homeScroll');
              if(!row||!sc) return;
              const rr=row.getBoundingClientRect(), sr=sc.getBoundingClientRect();
              sc.scrollTop += (rr.bottom - (sr.bottom - 28));
            }""")
            pg.wait_for_timeout(120)
            pg.locator('.qrow .row-more').click(); pg.wait_for_selector('#qmDelete')
            box=pg.evaluate("""()=>{
              const b=document.querySelector('#qmDelete').getBoundingClientRect();
              const m=document.querySelector('.menu').getBoundingClientRect();
              const sab=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--sab'))||0;
              return {b:{t:b.top,b:b.bottom,l:b.left,r:b.right}, m:{t:m.top,b:m.bottom,l:m.left,r:m.right},
                vw:innerWidth, vh:innerHeight, sab, inView: b.top>=0 && b.left>=0 && b.bottom<=innerHeight && b.right<=innerWidth};
            }""")
            ok('ipad-portrait: Delete in the reading-list menu stays inside the viewport',
               box['inView'] and box['m']['b']<=box['vh']-box['sab']+1 and box['m']['t']>=-1, json.dumps(box))
            pg.keyboard.press('Escape'); pg.evaluate("document.querySelector('.menu')?.remove()")

        ctx.close()

    real=[e for e in errors if 'access control checks' not in e.lower() and 'cross-origin' not in e.lower()]
    ok('no page errors', not real, '; '.join((real or errors)[:4]))
    b.close()

print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
