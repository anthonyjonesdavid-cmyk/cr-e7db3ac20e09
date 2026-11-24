"""cr-v68 suite: '1 page' toggle in Fit width, realistic 1.32/1.45 facing-page scans.
python3 test/e2e_v68.py [webkit]  (server on 127.0.0.1:8823)
Fixture: testpdfs/spreads/Facing_Pages_01.pdf (cover, 1.32 spread, page, 1.45 spread)."""
import sys, os, json
from PIL import Image
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILE=os.path.join(T,'spreads','Facing_Pages_01.pdf')
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,'' if cond else str(extra)[:800],flush=True)

def dismiss(pg):
    pg.evaluate("window.__crSplashHide&&window.__crSplashHide(true)")
    pg.wait_for_function("!document.getElementById('splash')||document.getElementById('splash').classList.contains('fly')||document.getElementById('splash').classList.contains('out')")
    pg.wait_for_timeout(200)
def wait_fit(pg,t=20000):
    pg.wait_for_function('document.querySelector("#stage.fitw") && document.querySelectorAll("#stage.fitw .pg canvas").length>0',timeout=t)
def wait_painted(pg,t=20000):
    pg.wait_for_function("""()=>{
      const c=document.querySelector('#stage.fitw .pg canvas');
      if(!c||!c.width||!c.height) return false;
      try{
        const x=c.getContext('2d',{willReadFrequently:true}); if(!x) return false;
        const mid=x.getImageData(c.width>>1,c.height>>1,8,8).data;
        let min=765,max=0;
        for(let i=0;i<mid.length;i+=4){ const s=mid[i]+mid[i+1]+mid[i+2]; if(s<min)min=s; if(s>max)max=s; }
        return max>0 && min<750;
      }catch(e){ return c.width>10; }
    }""",timeout=t)
def open_c(pg,title='Facing Pages 01'):
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150)
    pg.locator(f'.lc[data-title="{title}"]').click(); pg.wait_for_selector('#reader:not(.hidden)')
def show_ui(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(80)

# LEFT page is warm orange; RIGHT page is cool blue. Used to prove only one half is on screen.
LEFT_ORANGE=(210,92,42)
RIGHT_BLUE=(42,86,186)
def mean_box(im, box):
    x0,y0,x1,y1=[int(v) for v in box]
    x0,y0=max(0,x0),max(0,y0); x1,y1=min(im.size[0],x1),min(im.size[1],y1)
    if x1<=x0 or y1<=y0: return (0,0,0)
    c=im.crop((x0,y0,x1,y1)).resize((1,1), Image.Resampling.BOX)
    return c.getpixel((0,0))[:3]
def dist(a,b):
    return ((a[0]-b[0])**2+(a[1]-b[1])**2+(a[2]-b[2])**2)**0.5
def is_orange(rgb): return dist(rgb,LEFT_ORANGE)<90 or (rgb[0]>140 and rgb[0]>rgb[2]+40)
def is_blue(rgb): return dist(rgb,RIGHT_BLUE)<90 or (rgb[2]>140 and rgb[2]>rgb[0]+40)

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    w,h,lab,dpr,sat,sab=1366,1024,'ipad-landscape',2,24,20
    ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
    ctx.add_init_script(f"window.__crNoScan=true; window.__crNoBag=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}') if 'access control checks' not in str(e).lower() and 'cross-origin' not in str(e).lower() else None)
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    dismiss(pg)
    pg.set_input_files('#fileIn',[FILE]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==1 && !document.querySelector(".toast .tb")',timeout=120000)

    open_c(pg); show_ui(pg)
    pg.click('#rFit'); wait_fit(pg); wait_painted(pg); show_ui(pg)

    # Aspects of the two scanned spreads (PDF pages 2 and 4 → indices 1 and 3)
    aspects=pg.evaluate("()=>({a:window.__cr.R.aspects.slice(), n:window.__cr.R.n})")
    ok(f'{lab}: fixture has a ~1.32 spread and a ~1.45 spread',
       aspects['n']==4 and len(aspects['a'])>=4 and abs(aspects['a'][1]-1.32)<0.02 and abs(aspects['a'][3]-1.45)<0.02 and aspects['a'][1]>1.2 and aspects['a'][3]>1.2,
       json.dumps(aspects))

    # Default: 1 page is OFF, label still says "1 page", not highlighted; the 1.32 sheet is one full-width strip (both facing pages)
    pg.evaluate('__cr.fit.goTo(1)'); wait_fit(pg); wait_painted(pg); show_ui(pg)
    two=pg.evaluate("""()=>{
      const stage=document.getElementById('stage');
      const wide=[...stage.querySelectorAll('.pg')].filter(d=>+d.dataset.p===1);
      const boxes=wide.map(el=>{ const r=el.getBoundingClientRect(); return {p:+el.dataset.p, half:el.dataset.half||null, w:Math.round(r.width), h:Math.round(r.height), y:Math.round(r.y)}; });
      const b=document.querySelector('#rSpread'), br=b.getBoundingClientRect(), fit=document.querySelector('#rFit'), fr=fit.getBoundingClientRect();
      return {fit:stage.classList.contains('fitw'), boxes, tw:stage.clientWidth, th:stage.clientHeight,
        store:localStorage.getItem('cr.fitSingle'), hidden:b.classList.contains('hidden'),
        txt:document.getElementById('rSpreadTxt').textContent, on:b.classList.contains('on'),
        pressed:b.getAttribute('aria-pressed'), label:(b.getAttribute('aria-label')||'')+(b.title||''),
        bw:Math.round(br.width), bh:Math.round(br.height), bx:Math.round(br.x), by:Math.round(br.y), fx:Math.round(fr.x)};
    }""")
    ok(f'{lab}: 1 page button is labeled "1 page", off by default, next to Width, >=40px',
       two['txt'].strip()=='1 page' and not two['on'] and two['pressed']=='false' and 'One page' in two['label']
       and not two['hidden'] and two['bw']>=40 and two['bh']>=40 and two['by']>=-2 and two['bx']<two['fx']
       and two['store'] in (None,'false'), json.dumps(two))
    ok(f'{lab}: with 1 page off, the 1.32 sheet is one full-width strip (both facing pages)',
       two['fit'] and len(two['boxes'])==1 and two['boxes'][0]['half'] is None
       and abs(two['boxes'][0]['w']-two['tw'])<=2
       and abs(two['boxes'][0]['h']-round(two['tw']/aspects['a'][1]))<=4,
       json.dumps(two))

    # Turn 1 page ON
    pg.click('#rSpread'); wait_fit(pg); wait_painted(pg); show_ui(pg)
    one=pg.evaluate("""()=>{
      const stage=document.getElementById('stage');
      const wide=[...stage.querySelectorAll('.pg')].filter(d=>+d.dataset.p===1);
      const boxes=wide.map(el=>{ const r=el.getBoundingClientRect(); return {p:+el.dataset.p, half:el.dataset.half||null, w:Math.round(r.width), h:Math.round(r.height), top:el.offsetTop}; });
      const b=document.querySelector('#rSpread');
      const vis=[...stage.querySelectorAll('.pg')].map(el=>{ const r=el.getBoundingClientRect(), sr=stage.getBoundingClientRect();
        const visible=Math.max(0, Math.min(r.bottom,sr.bottom)-Math.max(r.top,sr.top));
        return {p:+el.dataset.p, half:el.dataset.half||null, vis:Math.round(visible), w:Math.round(r.width)}; });
      return {boxes, tw:stage.clientWidth, th:stage.clientHeight, store:localStorage.getItem('cr.fitSingle'),
        txt:document.getElementById('rSpreadTxt').textContent, on:b.classList.contains('on'),
        pressed:b.getAttribute('aria-pressed'), cur:window.__cr.fit.cur, curH:window.__cr.fit.curH,
        pgText:document.getElementById('pgText').textContent, vis};
    }""")
    stacked=len(one['boxes'])==2 and one['boxes'][0]['top']<one['boxes'][1]['top']
    fullw=all(abs(box['w']-one['tw'])<=2 for box in one['boxes'])
    # each half of a 1.32 sheet is aspect 0.66, so height ≈ width/0.66, taller than the landscape viewport
    tall=all(box['h']>one['th']*1.1 for box in one['boxes'])
    order=[box['half'] for box in one['boxes']]
    # only the current half should be meaningfully visible (the next half is below the fold)
    vis_halves=[v for v in one['vis'] if v['p']==1 and v['vis']>40]
    ok(f'{lab}: turning 1 page on highlights the button and saves cr.fitSingle',
       one['txt'].strip()=='1 page' and one['on'] and one['pressed']=='true' and one['store']=='true',
       json.dumps({k:one[k] for k in ('txt','on','pressed','store','pgText','cur','curH')}))
    ok(f'{lab}: the 1.32 sheet splits into two stacked full-width halves (L then R), each taller than the screen',
       stacked and fullw and tall and order==['L','R'] and one['curH'] in ('L','R'),
       json.dumps(one['boxes']))
    ok(f'{lab}: only one half of the 1.32 sheet is on screen at a time',
       len(vis_halves)==1 and vis_halves[0]['half'] in ('L','R') and abs(vis_halves[0]['w']-one['tw'])<=2,
       json.dumps(one['vis']))

    # Land on the left half and take the landscape screenshot (UI visible so the 1 page button can be seen)
    pg.evaluate('__cr.fit.goTo(1,"L")'); wait_fit(pg); wait_painted(pg); show_ui(pg)
    pg.wait_for_timeout(300)
    shot=os.path.join(SH,f'{ENG}-v68-fitwidth-1page-ipad-landscape.png')
    pg.screenshot(path=shot)
    im=Image.open(shot).convert('RGB')
    W,H=im.size
    # Sample a mid-left patch and a mid-right patch of the page area (below the top bar, above the bottom bar)
    left=mean_box(im,(int(W*0.12), int(H*0.28), int(W*0.32), int(H*0.55)))
    right=mean_box(im,(int(W*0.68), int(H*0.28), int(W*0.88), int(H*0.55)))
    mid=mean_box(im,(int(W*0.42), int(H*0.28), int(W*0.58), int(H*0.55)))
    # The whole visible page should be the LEFT (orange) page — both left and right sides of the viewport.
    # The RIGHT (blue) page must not appear beside it.
    ok(f'{lab}: screenshot shows only the LEFT page at full width (no blue RIGHT page beside it)',
       is_orange(left) and is_orange(right) and is_orange(mid) and not is_blue(left) and not is_blue(right) and not is_blue(mid),
       json.dumps({'left':list(left),'right':list(right),'mid':list(mid),'file':shot}))

    # Scroll down: the RIGHT half should become the page on screen
    pg.evaluate("""()=>{
      const stage=document.getElementById('stage');
      const b=stage.querySelector('.pg[data-p="1"][data-half="R"]');
      if(b) stage.scrollTop=b.offsetTop;
    }""")
    pg.wait_for_timeout(350); wait_painted(pg)
    right_state=pg.evaluate("""()=>({cur:window.__cr.fit.cur, curH:window.__cr.fit.curH, pgText:document.getElementById('pgText').textContent})""")
    ok(f'{lab}: scrolling down lands on the RIGHT half of the same sheet, still in 1 page mode',
       right_state['cur']==1 and right_state['curH']=='R' and '/' in right_state['pgText'],
       json.dumps(right_state))
    show_ui(pg)
    shot_r=os.path.join(SH,f'{ENG}-v68-fitwidth-1page-right-ipad-landscape.png')
    pg.screenshot(path=shot_r)
    imr=Image.open(shot_r).convert('RGB')
    Wr,Hr=imr.size
    r_left=mean_box(imr,(int(Wr*0.12), int(Hr*0.28), int(Wr*0.32), int(Hr*0.55)))
    r_right=mean_box(imr,(int(Wr*0.68), int(Hr*0.28), int(Wr*0.88), int(Hr*0.55)))
    ok(f'{lab}: the RIGHT half also fills the width by itself (blue, no orange LEFT page beside it)',
       is_blue(r_left) and is_blue(r_right) and not is_orange(r_left) and not is_orange(r_right),
       json.dumps({'left':list(r_left),'right':list(r_right),'file':shot_r}))

    # The 1.45 spread must split the same way
    pg.evaluate('__cr.fit.goTo(3,"L")'); wait_fit(pg); wait_painted(pg)
    a145=pg.evaluate("""()=>{
      const stage=document.getElementById('stage');
      const wide=[...stage.querySelectorAll('.pg')].filter(d=>+d.dataset.p===3);
      const boxes=wide.map(el=>{ const r=el.getBoundingClientRect(); return {half:el.dataset.half||null, w:Math.round(r.width), h:Math.round(r.height), top:el.offsetTop}; });
      const vis=[...wide].filter(el=>{ const r=el.getBoundingClientRect(), sr=stage.getBoundingClientRect();
        return Math.max(0, Math.min(r.bottom,sr.bottom)-Math.max(r.top,sr.top))>40; }).map(el=>el.dataset.half||null);
      return {boxes, tw:stage.clientWidth, th:stage.clientHeight, aspect:window.__cr.R.aspects[3], vis, curH:window.__cr.fit.curH};
    }""")
    ok(f'{lab}: the 1.45 sheet also splits into two stacked full-width halves, one on screen',
       abs(a145['aspect']-1.45)<0.02 and len(a145['boxes'])==2 and [b['half'] for b in a145['boxes']]==['L','R']
       and all(abs(b['w']-a145['tw'])<=2 for b in a145['boxes']) and all(b['h']>a145['th']*1.05 for b in a145['boxes'])
       and a145['vis']==['L'] and a145['curH']=='L',
       json.dumps(a145))

    ctx.close(); b.close()

print(); failed=sum(1 for x in res if not x)
print(f'{len(res)-failed}/{len(res)} passed', f'({failed} failed)' if failed else '')
if errors:
    print('page errors:'); [print(' ',e) for e in errors]
sys.exit(1 if failed or errors else 0)
