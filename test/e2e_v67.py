"""cr-v67 suite: lighter Inks levels, and 1-up / 2-up in Fit width for wide scanned spreads.
python3 test/e2e_v67.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: Dark_Inks_01.pdf, testpdfs/spreads/Wide_Horizon_01.pdf."""
import sys, os, json
from PIL import Image
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
DARK=os.path.join(T,'Dark_Inks_01.pdf')
WIDE=os.path.join(T,'spreads','Wide_Horizon_01.pdf')
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,'' if cond else str(extra)[:800],flush=True)

def dismiss(pg):
    pg.evaluate("window.__crSplashHide&&window.__crSplashHide(true)")
    pg.wait_for_function("!document.getElementById('splash')||document.getElementById('splash').classList.contains('fly')||document.getElementById('splash').classList.contains('out')")
    pg.wait_for_timeout(200)
def wait_render(pg,t=20000):
    pg.wait_for_function('document.querySelectorAll(".view .pg.loading").length===0 && document.querySelectorAll(".view .pg canvas").length>0',timeout=t)
def wait_fit(pg,t=20000):
    pg.wait_for_function('document.querySelector("#stage.fitw") && document.querySelectorAll("#stage.fitw .pg canvas").length>0',timeout=t)
def wait_painted(pg,t=20000):
    pg.wait_for_function("""()=>{
      const c=document.querySelector('.view .pg canvas');
      if(!c||!c.width||!c.height) return false;
      try{
        const x=c.getContext('2d',{willReadFrequently:true}); if(!x) return false;
        const mid=x.getImageData(c.width>>1,c.height>>1,8,8).data;
        let min=765,max=0;
        for(let i=0;i<mid.length;i+=4){ const s=mid[i]+mid[i+1]+mid[i+2]; if(s<min)min=s; if(s>max)max=s; }
        return max>0 && min<750;
      }catch(e){ return c.width>10; }
    }""",timeout=t)
def open_c(pg,title):
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150)
    pg.locator(f'.lc[data-title="{title}"]').click(); pg.wait_for_selector('#reader:not(.hidden)')
def back(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(80)
    pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(250)
def show_ui(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(80)

def mean_box(im, box):
    x0,y0,x1,y1=box
    c=im.crop((x0,y0,x1,y1))
    small=c.resize((1,1), Image.Resampling.BOX); return small.getpixel((0,0))[:3]
def lum(rgb): return 0.2126*rgb[0]+0.7152*rgb[1]+0.0722*rgb[2]

OLD_FILTER='''()=>{
  const set=(el)=>{ if(!el) return;
    ['feFuncR','feFuncG','feFuncB'].forEach(t=>{
      const f=el.querySelector(t); if(!f) return;
      f.setAttribute('type','linear'); f.setAttribute('slope','5'); f.setAttribute('intercept','-2');
      f.removeAttribute('tableValues');
    });
  };
  set(document.getElementById('crInks'));
}'''
NEW_FILTER='''()=>{
  const vals='0 0.31 0.49 0.60 0.68 0.75 0.82 0.90 0.95 0.98 1';
  const set=(el)=>{ if(!el) return;
    ['feFuncR','feFuncG','feFuncB'].forEach(t=>{
      const f=el.querySelector(t); if(!f) return;
      f.setAttribute('type','table'); f.setAttribute('tableValues',vals);
      f.removeAttribute('slope'); f.removeAttribute('intercept');
    });
  };
  set(document.getElementById('crInks'));
}'''

with sync_playwright() as p:
    b=getattr(p,ENG).launch()

    # ---- Portrait: lighter Inks on a dark page ----
    w,h,lab,dpr,sat,sab=1024,1366,'ipad-portrait',2,24,20
    ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
    ctx.add_init_script(f"window.__crNoScan=true; window.__crNoBag=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}') if 'access control checks' not in str(e).lower() and 'cross-origin' not in str(e).lower() else None)
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    dismiss(pg)
    pg.set_input_files('#fileIn',[DARK,WIDE]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==2 && !document.querySelector(".toast .tb")',timeout=120000)

    # Filter source is the gentler table, not the old crush
    src=pg.evaluate("""()=>{
      const f=document.getElementById('crInks'), r=f&&f.querySelector('feFuncR');
      const css=getComputedStyle(document.documentElement).cssText;
      const tag=[...document.styleSheets].flatMap(s=>{ try{ return [...s.cssRules].map(r=>r.cssText); }catch(e){ return []; } }).filter(t=>t.includes('crInks')||t.includes('grayscale')).join('\\n');
      return {type:r&&r.getAttribute('type'), table:r&&r.getAttribute('tableValues'), slope:r&&r.getAttribute('slope'), intercept:r&&r.getAttribute('intercept'), css:tag};
    }""")
    ok(f'{lab}: Inks SVG filter is a gentle table, not slope-5 crush',
       src['type']=='table' and src['table'] and '0.31' in src['table'] and '0.36' not in src['table'] and src['slope'] in (None,'') and src['intercept'] in (None,''),
       json.dumps(src))
    ok(f'{lab}: CSS fallback no longer uses contrast(3.2)',
       'contrast(3.2)' not in (src['css'] or '') and 'brightness(1.4)' not in (src['css'] or '') and ('contrast(1.4)' in (src['css'] or '') or 'brightness(1.2)' in (src['css'] or '') or 'url("#crInks")' in (src['css'] or '') or 'url(#crInks)' in (src['css'] or '')),
       src['css'][:400] if src['css'] else 'no css')

    open_c(pg,'Dark Inks 01'); wait_render(pg); wait_painted(pg)
    pg.evaluate('__cr.jumpTo(0)'); wait_render(pg); wait_painted(pg); show_ui(pg)
    here=pg.evaluate("()=>({pg:document.getElementById('pgText').textContent, vi:window.__cr.R.vi, n:window.__cr.R.n})")
    ok(f'{lab}: Dark Inks opens on the dark first page', here['pg'].startswith('1 /') and here['vi']==0, json.dumps(here))
    pg.click('#rInks'); pg.wait_for_timeout(250); pg.evaluate('__cr.jumpTo(0)'); wait_render(pg); wait_painted(pg); show_ui(pg)
    on=pg.evaluate("""()=>{
      const b=document.querySelector('#rInks'), page=document.querySelector('#stage canvas');
      const filt=page?getComputedStyle(page).filter:'';
      return {on:b.classList.contains('on'), store:localStorage.getItem('cr.inks'), reader:document.getElementById('reader').classList.contains('inks'), filt};
    }""")
    ok(f'{lab}: Inks still applies url(#crInks) and saves cr.inks',
       on['on'] and on['store']=='true' and on['reader'] and ('url("#crInks")' in on['filt'] or 'url(#crInks)' in on['filt'] or 'grayscale' in on['filt']),
       json.dumps(on))

    # Viewport clip of the visible page (composited, so the CSS/SVG filter is included)
    def shot_page(path, with_ui=True):
        if with_ui: show_ui(pg)
        else: pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(80)
        box=pg.evaluate("""()=>{ const c=document.querySelector('.view .pg canvas')||document.querySelector('#stage canvas');
          const r=c.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height, pg:document.getElementById('pgText').textContent}; }""")
        # full reader shot for inspection (includes chrome)
        if with_ui:
            pg.screenshot(path=path)
        clip=dict(x=max(0,box['x']), y=max(0,box['y']), width=min(box['w'], w-max(0,box['x'])), height=min(box['h'], h-max(0,box['y'])))
        page_path=path.replace('.png','-page.png')
        pg.screenshot(path=page_path, clip=clip)
        return box, page_path

    # Before: temporarily restore the old crush, shoot, then put the new curve back
    pg.evaluate(OLD_FILTER); pg.wait_for_timeout(700); wait_painted(pg)
    before_path=os.path.join(SH,f'{ENG}-v67-inks-dark-before-ipad-portrait.png')
    before_box, before_page=shot_page(before_path, True)
    pg.evaluate(NEW_FILTER); pg.wait_for_timeout(700); wait_painted(pg)
    after_path=os.path.join(SH,f'{ENG}-v69-inks-dark-ipad-portrait.png')
    after_box, after_page=shot_page(after_path, True)

    ok(f'{lab}: Inks before/after shots are of page 1',
       before_box['pg'].startswith('1 /') and after_box['pg'].startswith('1 /'),
       json.dumps({'before':before_box,'after':after_box}))

    bim,aim=Image.open(before_page).convert('RGB'),Image.open(after_page).convert('RGB')
    # Design is 600x922. Sample the first panel's open fill (left of the figure) and a thick ink stroke.
    def rel(im,x0,y0,x1,y1,src_w=600,src_h=922):
        W,H=im.size
        return (int(x0/src_w*W), int(y0/src_h*H), int(x1/src_w*W), int(y1/src_h*H))
    fill_b,fill_a=mean_box(bim,rel(bim,80,320,140,400)), mean_box(aim,rel(aim,80,320,140,400))
    # ink stroke: darkest 3px-wide column in the left 15% of the mid-page (PDF crop can shift a few px)
    def darkest_ink(im):
        W,H=im.size; y0,y1=int(H*0.2),int(H*0.5); best=(999,0)
        for x in range(int(W*0.03), int(W*0.15)):
            s=0; n=0
            for y in range(y0,y1,2):
                p=im.getpixel((x,y)); s+=0.2126*p[0]+0.7152*p[1]+0.0722*p[2]; n+=1
            avg=s/max(n,1)
            if avg<best[0]: best=(avg,x)
        x=best[1]; return mean_box(im,(max(0,x-1),y0,min(W,x+2),y1))
    ink_a=darkest_ink(aim)
    # white caption box in the lower-right panel
    white_a=mean_box(aim,rel(aim,360,800,500,840))
    ok(f'{lab}: old Inks crushed the dark fill to near-black',
       lum(fill_b)<25, json.dumps({'fill_before':[round(x,1) for x in fill_b],'lum':round(lum(fill_b),1)}))
    ok(f'{lab}: new Inks lifts the dark fill to mid gray (line work can read against it)',
       lum(fill_a)>=70 and lum(fill_a)<=200 and lum(fill_a)-lum(fill_b)>=40,
       json.dumps({'fill_after':[round(x,1) for x in fill_a],'fill_before':[round(x,1) for x in fill_b],'lum_a':round(lum(fill_a),1),'lum_b':round(lum(fill_b),1)}))
    ok(f'{lab}: new Inks keeps black ink dark and white captions light',
       lum(ink_a)<55 and lum(white_a)>180,
       json.dumps({'ink':[round(x,1) for x in ink_a],'ink_lum':round(lum(ink_a),1),'white':[round(x,1) for x in white_a],'white_lum':round(lum(white_a),1)}))

    back(pg)
    ctx.close()

    # ---- Landscape: 1-up / 2-up in Fit width for a wide scanned spread ----
    w,h,lab,dpr,sat,sab=1366,1024,'ipad-landscape',2,24,20
    ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
    ctx.add_init_script(f"window.__crNoScan=true; window.__crNoBag=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}') if 'access control checks' not in str(e).lower() and 'cross-origin' not in str(e).lower() else None)
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    dismiss(pg)
    pg.set_input_files('#fileIn',[WIDE]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==1 && !document.querySelector(".toast .tb")',timeout=120000)

    open_c(pg,'Wide Horizon 01'); wait_render(pg); show_ui(pg)
    # Turn Width on (default 2-up: a wide sheet stays one full-width strip)
    pg.click('#rFit'); wait_fit(pg); show_ui(pg)
    # Jump to the first wide spread (PDF page index 2, "SPREAD 3")
    pg.evaluate('__cr.fit.goTo(2)'); pg.wait_for_timeout(400); wait_fit(pg); show_ui(pg)
    two=pg.evaluate("""()=>{
      const stage=document.getElementById('stage');
      const pgs=[...stage.querySelectorAll('.pg')];
      const wide=pgs.filter(d=>+d.dataset.p===2);
      const boxes=wide.map(el=>{ const r=el.getBoundingClientRect(); return {p:+el.dataset.p, half:el.dataset.half||null, w:Math.round(r.width), h:Math.round(r.height), x:Math.round(r.x), y:Math.round(r.y)}; });
      const b=document.querySelector('#rSpread'), br=b?b.getBoundingClientRect():{};
      const fit=document.querySelector('#rFit'), fr=fit.getBoundingClientRect();
      const aspects=(window.__cr.R.aspects||[])[2];
      return {fit:stage.classList.contains('fitw'), n:pgs.length, wide:boxes, tw:stage.clientWidth, th:stage.clientHeight,
        store:localStorage.getItem('cr.fitSingle'), hidden:b?b.classList.contains('hidden'):true,
        txt:b?document.getElementById('rSpreadTxt').textContent:'', on:b?b.classList.contains('on'):false,
        bw:Math.round(br.width||0), bh:Math.round(br.height||0), bx:Math.round(br.x||0), by:Math.round(br.y||0),
        fx:Math.round(fr.x||0), aspect:aspects, cur:window.__cr.fit.cur, curH:window.__cr.fit.curH,
        pgText:document.getElementById('pgText').textContent};
    }""")
    ok(f'{lab}: Width default keeps a wide sheet as one full-width page (2-up)',
       two['fit'] and two['aspect'] and two['aspect']>1.2 and len(two['wide'])==1 and two['wide'][0]['half'] is None
       and abs(two['wide'][0]['w']-two['tw'])<=2 and abs(two['wide'][0]['h']-round(two['tw']/two['aspect']))<=3
       and two['store'] in (None,'false') and two['txt']=='1 page' and not two['on'] and not two['hidden'],
       json.dumps(two))
    ok(f'{lab}: 1-up / 2-up button is in the top bar next to Width, tap target >=40px',
       not two['hidden'] and two['bw']>=40 and two['bh']>=40 and two['by']>=-2 and two['bx']<two['fx'],
       json.dumps({k:two[k] for k in ('hidden','txt','on','bw','bh','bx','by','fx')}))

    # Tap 1-up: the wide sheet splits into two stacked full-width halves
    pg.click('#rSpread'); pg.wait_for_timeout(400); wait_fit(pg); show_ui(pg)
    one=pg.evaluate("""()=>{
      const stage=document.getElementById('stage');
      const wide=[...stage.querySelectorAll('.pg')].filter(d=>+d.dataset.p===2);
      const boxes=wide.map(el=>{ const r=el.getBoundingClientRect(); return {p:+el.dataset.p, half:el.dataset.half||null, w:Math.round(r.width), h:Math.round(r.height), top:el.offsetTop, x:Math.round(r.x), y:Math.round(r.y)}; });
      const b=document.querySelector('#rSpread');
      const items=window.__cr.fit.items().filter(x=>x.p<window.__cr.R.n);
      return {boxes, tw:stage.clientWidth, th:stage.clientHeight, store:localStorage.getItem('cr.fitSingle'),
        txt:b?document.getElementById('rSpreadTxt').textContent:'', hidden:b.classList.contains('hidden'),
        cur:window.__cr.fit.cur, curH:window.__cr.fit.curH, pgText:document.getElementById('pgText').textContent,
        nItems:items.length, nPdf:window.__cr.R.seq.length, halves:items.filter(x=>x.h).length};
    }""")
    stacked=len(one['boxes'])==2 and one['boxes'][0]['top']<one['boxes'][1]['top']
    fullw=all(abs(box['w']-one['tw'])<=2 for box in one['boxes'])
    tall=all(box['h']>one['th']*0.7 for box in one['boxes'])  # each half is roughly portrait at full width
    order=[box['half'] for box in one['boxes']]
    ok(f'{lab}: 1-up splits the wide sheet into two stacked full-width pages (L then R)',
       stacked and fullw and tall and order==['L','R'] and one['store']=='true' and one['txt']=='1 page' and one['halves']==4
       and one['nItems']>one['nPdf'] and one['curH'] in ('L','R'),
       json.dumps(one))

    # Continuous scroll: from the first half, the second half is the next strip
    mid=pg.evaluate("""()=>{
      const stage=document.getElementById('stage');
      const a=stage.querySelector('.pg[data-p="2"][data-half="L"]');
      const b=stage.querySelector('.pg[data-p="2"][data-half="R"]');
      if(!a||!b) return {ok:false};
      const target=b.offsetTop - Math.round(stage.clientHeight*0.45);
      stage.scrollTop=Math.max(0,target);
      return {ok:true};
    }""")
    pg.wait_for_timeout(250)
    mid2=pg.evaluate("""()=>{
      const stage=document.getElementById('stage');
      const a=stage.querySelector('.pg[data-p="2"][data-half="L"]');
      const b=stage.querySelector('.pg[data-p="2"][data-half="R"]');
      const ra=a.getBoundingClientRect(), rb=b.getBoundingClientRect(), sr=stage.getBoundingClientRect();
      return {cur:window.__cr.fit.cur, curH:window.__cr.fit.curH, pgText:document.getElementById('pgText').textContent,
        flip:!!window.__cr.flip, gap:Math.round(rb.top-ra.bottom),
        aVis:ra.bottom>sr.top+20 && ra.top<sr.bottom-20, bVis:rb.bottom>sr.top+20 && rb.top<sr.bottom-20};
    }""")
    ok(f'{lab}: scrolling in 1-up flows from the left half into the right half, no page turn',
       mid['ok'] and mid2['aVis'] and mid2['bVis'] and mid2['gap']>=0 and mid2['gap']<=8 and not mid2['flip']
       and mid2['cur']==2 and mid2['curH'] in ('L','R') and '/' in mid2['pgText'],
       json.dumps(mid2))

    # Land cleanly on the left half for the screenshot
    pg.evaluate('__cr.fit.goTo(2,"L")'); pg.wait_for_timeout(350); wait_fit(pg); show_ui(pg)
    pg.screenshot(path=os.path.join(SH,f'{ENG}-v67-fitwidth-1up-ipad-landscape.png'))

    # RTL: halves swap to R then L
    pg.click('#rRtl'); pg.wait_for_timeout(350); wait_fit(pg); show_ui(pg)
    rtl=pg.evaluate("""()=>{
      const wide=[...document.querySelectorAll('#stage.fitw .pg')].filter(d=>+d.dataset.p===2);
      return {order:wide.map(d=>d.dataset.half), rtl:window.__cr.R.rtl, curH:window.__cr.fit.curH};
    }""")
    ok(f'{lab}: RTL 1-up shows the right half first, then the left',
       rtl['order']==['R','L'] and rtl['rtl'] is True, json.dumps(rtl))
    # back to LTR so the rest stays predictable
    pg.click('#rRtl'); pg.wait_for_timeout(250)

    # Toggle back to 2-up: one element again
    show_ui(pg); pg.click('#rSpread'); pg.wait_for_timeout(350); wait_fit(pg)
    back2=pg.evaluate("""()=>{
      const wide=[...document.querySelectorAll('#stage.fitw .pg')].filter(d=>+d.dataset.p===2);
      return {n:wide.length, half:wide[0]&&(wide[0].dataset.half||null), store:localStorage.getItem('cr.fitSingle'),
        txt:document.getElementById('rSpreadTxt').textContent, curH:window.__cr.fit.curH};
    }""")
    ok(f'{lab}: turning 2-up back on shows the wide sheet whole again',
       back2['n']==1 and back2['half'] is None and back2['store']=='false' and back2['txt']=='1 page' and back2['curH'] is None,
       json.dumps(back2))

    # Persist 1-up across close/reopen
    show_ui(pg); pg.click('#rSpread'); pg.wait_for_timeout(200)
    back(pg)
    open_c(pg,'Wide Horizon 01'); wait_fit(pg); show_ui(pg)
    persist=pg.evaluate("""()=>({store:localStorage.getItem('cr.fitSingle'), fit:document.getElementById('stage').classList.contains('fitw'),
      txt:document.getElementById('rSpreadTxt').textContent, single:window.__cr.fit.wantSingle(),
      hasHalves:[...document.querySelectorAll('#stage.fitw .pg')].some(d=>d.dataset.half)});""")
    ok(f'{lab}: cr.fitSingle persists and Width reopens in 1-up',
       persist['store']=='true' and persist['fit'] and persist['txt']=='1 page' and persist['single'] and persist['hasHalves'],
       json.dumps(persist))

    # Home is unchanged: back to shelf, home tab still has the usual layout hooks
    back(pg)
    pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200)
    home=pg.evaluate("""()=>({tab:document.getElementById('home') && !document.getElementById('home').classList.contains('hidden'),
      shelf:!!document.getElementById('shelf') && !document.getElementById('shelf').classList.contains('hidden'),
      reader:document.getElementById('reader').classList.contains('hidden')});""")
    ok(f'{lab}: Home / shelf layout is still the home screen (reader closed)',
       home['tab'] and home['shelf'] and home['reader'], json.dumps(home))

    ctx.close(); b.close()

print(); failed=sum(1 for x in res if not x)
print(f'{len(res)-failed}/{len(res)} passed', f'({failed} failed)' if failed else '')
if errors:
    print('page errors:'); [print(' ',e) for e in errors]
sys.exit(1 if failed or errors else 0)
