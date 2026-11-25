"""cr-v71 suite: Inks line-work boost darkens thin AA strokes, leaves gray fills.
python3 test/e2e_v71.py [webkit]  (server on 127.0.0.1:8823)
Fixture: testpdfs/Ink_Lines_01.pdf — scan-like lettering and hatching over a 0.50 gray fill."""
import sys, os, json, statistics
from PIL import Image
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILE=os.path.join(T,'Ink_Lines_01.pdf')
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
        const pts=[[c.width>>1,c.height>>1],[c.width*0.25,c.height*0.4],[c.width*0.75,c.height*0.4],[16,16]];
        for(const p of pts){
          const mid=x.getImageData(p[0]|0,p[1]|0,8,8).data;
          for(let i=0;i<mid.length;i+=4){ if(mid[i]+mid[i+1]+mid[i+2]<750) return true; }
        }
        return c.classList.contains('inks-baked') && c.width>10;
      }catch(e){ return c.width>10; }
    }""",timeout=t)
def open_c(pg,title='Ink Lines 01'):
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150)
    pg.locator(f'.lc[data-title="{title}"]').click(); pg.wait_for_selector('#reader:not(.hidden)')
def show_ui(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(80)
def lum(rgb): return 0.2126*rgb[0]+0.7152*rgb[1]+0.0722*rgb[2]
def mean_box(im, box):
    x0,y0,x1,y1=[int(v) for v in box]
    x0,y0=max(0,x0),max(0,y0); x1,y1=min(im.size[0],x1),min(im.size[1],y1)
    if x1<=x0 or y1<=y0: return (0,0,0)
    c=im.crop((x0,y0,x1,y1)).resize((1,1), Image.Resampling.BOX)
    return c.getpixel((0,0))[:3]
def rel(im,x0,y0,x1,y1,src_w=600,src_h=922):
    W,H=im.size
    return (int(x0/src_w*W), int(y0/src_h*H), int(x1/src_w*W), int(y1/src_h*H))
def luma_arr(im, box):
    x0,y0,x1,y1=rel(im,*box) if len(box)==4 and not isinstance(box[0],int) else box
    # accept design box via rel when called as luma_arr(im, (x0,y0,x1,y1), design=True)
    return None

def crop_luma(im, dbox):
    x0,y0,x1,y1=rel(im,*dbox)
    c=im.crop((x0,y0,x1,y1)).convert('RGB')
    px=list(c.getdata())
    return [0.2126*p[0]+0.7152*p[1]+0.0722*p[2] for p in px]

def dark_percentile(vals, p=8):
    if not vals: return 255.0
    s=sorted(vals)
    i=max(0, min(len(s)-1, int(len(s)*p/100.0)))
    return s[i]

def frame_stats(ms):
    if not ms: return {}
    s=sorted(ms)
    def pct(p):
        i=min(len(s)-1, max(0, int(round((p/100)*(len(s)-1)))))
        return s[i]
    return {'n':len(s),'med':round(statistics.median(s),2),'p95':round(pct(95),2),'max':round(max(s),2),'mean':round(statistics.mean(s),2)}

# Design-space sample boxes on Ink_Lines page 1 (600x922)
TEXT=(160,132,440,200)          # WATCH OUT / WOLVERINE lettering
FILL=(70,300,140,360)           # uniform mid-gray panel fill
WHITE=(250,100,350,130)         # balloon interior
OUTLINE=(200,66,400,80)         # top of the balloon stroke
HATCH=(420,800,540,860)         # hatching over gray, away from the balloon
HALO=(200,275,400,295)          # gray fill just below the balloon, clear of the outline
V70_GRAY=0.75*255               # 191.25

DISABLE_BOOST='''()=>{
  const el=document.querySelector('#crInks feComposite[result="unsharp"]');
  if(el){ el.setAttribute('k2','1'); el.setAttribute('k3','0'); }
}'''
ENABLE_BOOST='''()=>{
  const el=document.querySelector('#crInks feComposite[result="unsharp"]');
  if(el){ el.setAttribute('k2','5'); el.setAttribute('k3','-4'); }
}'''

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    w,h,lab,dpr,sat,sab=1024,1366,'ipad-portrait',2,24,20
    ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
    ctx.add_init_script(f"window.__crNoScan=true; window.__crNoBag=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}') if 'access control checks' not in str(e).lower() and 'cross-origin' not in str(e).lower() else None)
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    dismiss(pg)

    src=pg.evaluate("""()=>{
      const f=document.getElementById('crInks');
      const ink=f&&f.querySelector('feComponentTransfer[result="ink"] feFuncR');
      const blur=f&&f.querySelector('feGaussianBlur');
      const morph=f&&f.querySelector('feMorphology');
      const boost=f&&f.querySelector('feComposite[result="unsharp"]');
      const css=[...document.styleSheets].flatMap(s=>{ try{ return [...s.cssRules].map(r=>r.cssText); }catch(e){ return []; } }).filter(t=>t.includes('crInks')||t.includes('grayscale')).join('\\n');
      return {
        table:ink&&ink.getAttribute('tableValues'),
        n:ink&&(ink.getAttribute('tableValues')||'').trim().split(/\\s+/).length,
        blur:blur&&blur.getAttribute('stdDeviation'),
        morph:!!morph,
        k2:boost&&boost.getAttribute('k2'), k3:boost&&boost.getAttribute('k3'),
        css
      };
    }""")
    ok(f'{lab}: Inks filter keeps the v70 21-stop table and adds a ~1-2px blur boost (no erode)',
       src['table'] and src['table'].strip().startswith('0 0.02 0.04') and src['n']==21 and '0.75' in src['table']
       and src['blur'] is not None and 1.0<=float(str(src['blur']).split()[0])<=2.0
       and not src['morph'] and src.get('k2') and src['k3'] and float(src['k2'])>=2 and float(src['k3'])<=-1.0,
       json.dumps(src))
    ok(f'{lab}: CSS fallback is still the v70-ish grayscale (no contrast(3.2))',
       'contrast(3.2)' not in (src['css'] or '') and ('contrast(1.5)' in (src['css'] or '') or 'brightness(1.2)' in (src['css'] or '') or 'url(#crInks)' in (src['css'] or '') or 'url("#crInks")' in (src['css'] or '')),
       (src['css'] or '')[:400])

    pg.set_input_files('#fileIn',[FILE]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==1 && !document.querySelector(".toast .tb")',timeout=120000)
    open_c(pg); wait_render(pg); wait_painted(pg); show_ui(pg)
    pg.click('#rInks'); pg.wait_for_timeout(300); wait_painted(pg); show_ui(pg)
    on=pg.evaluate("""()=>{
      const b=document.querySelector('#rInks'), page=document.querySelector('#stage canvas');
      const filt=page?getComputedStyle(page).filter:'';
      return {on:b.classList.contains('on'), store:localStorage.getItem('cr.inks'), reader:document.getElementById('reader').classList.contains('inks'), filt,
              baked:!!(page&&page.classList.contains('inks-baked'))};
    }""")
    ok(f'{lab}: Inks is on and the page is baked (or still uses url(#crInks))',
       on['on'] and on['store']=='true' and on['reader'] and (on['baked'] or 'url("#crInks")' in on['filt'] or 'url(#crInks)' in on['filt'] or 'grayscale' in on['filt']),
       json.dumps(on))

    def shot_pair(path):
        show_ui(pg)
        pg.screenshot(path=path)
        box=pg.evaluate("""()=>{ const c=document.querySelector('.view .pg canvas')||document.querySelector('#stage canvas');
          const r=c.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height, pg:document.getElementById('pgText').textContent}; }""")
        clip=dict(x=max(0,box['x']), y=max(0,box['y']), width=min(box['w'], w-max(0,box['x'])), height=min(box['h'], h-max(0,box['y'])))
        page_path=path.replace('.png','-page.png')
        pg.screenshot(path=page_path, clip=clip)
        return box, page_path

    # Before: boost off (v70 curve only)
    pg.evaluate(DISABLE_BOOST); pg.evaluate('window.__cr.inks.refresh()'); pg.wait_for_timeout(500); wait_painted(pg)
    before_path=os.path.join(SH,f'{ENG}-v71-inks-lines-before-ipad-portrait.png')
    before_box, before_page=shot_pair(before_path)
    # After: boost on
    pg.evaluate(ENABLE_BOOST); pg.evaluate('window.__cr.inks.refresh()'); pg.wait_for_timeout(500); wait_painted(pg)
    after_path=os.path.join(SH,f'{ENG}-v71-inks-lines-after-ipad-portrait.png')
    after_box, after_page=shot_pair(after_path)

    ok(f'{lab}: before/after shots are of page 1',
       before_box['pg'].startswith('1 /') and after_box['pg'].startswith('1 /'),
       json.dumps({'before':before_box,'after':after_box}))

    bim,aim=Image.open(before_page).convert('RGB'),Image.open(after_page).convert('RGB')
    def meas(im):
        text=crop_luma(im, TEXT)
        hatch=crop_luma(im, HATCH)
        outline=crop_luma(im, OUTLINE)
        fill=lum(mean_box(im, rel(im,*FILL)))
        white=lum(mean_box(im, rel(im,*WHITE)))
        halo=lum(mean_box(im, rel(im,*HALO)))
        return {
            'stroke':round(dark_percentile(text,8),1),
            'stroke_p20':round(dark_percentile(text,20),1),
            'hatch':round(dark_percentile(hatch,8),1),
            'outline':round(dark_percentile(outline,8),1),
            'fill':round(fill,1),
            'white':round(white,1),
            'halo':round(halo,1),
        }
    mb,ma=meas(bim),meas(aim)
    print('MEASUREMENTS', json.dumps({'before':mb,'after':ma,'before_shot':before_path,'after_shot':after_path}), flush=True)

    ok(f'{lab}: before boost, thin lettering is mid-gray (the v70 problem)',
       mb['stroke']>70,
       json.dumps(mb))
    ok(f'{lab}: after boost, lettering reads as near-black (<~40)',
       ma['stroke']<40,
       json.dumps(ma))
    ok(f'{lab}: balloon outline and hatching also go near-black',
       ma['outline']<50 and ma['hatch']<50,
       json.dumps(ma))
    ok(f'{lab}: broad mid-gray fill stays within ~5 levels of v70 (~191) and of the before shot',
       abs(ma['fill']-V70_GRAY)<=8 and abs(ma['fill']-mb['fill'])<=5,
       json.dumps({'before':mb['fill'],'after':ma['fill'],'v70':V70_GRAY}))
    ok(f'{lab}: whites stay white',
       ma['white']>230 and mb['white']>230,
       json.dumps({'before':mb['white'],'after':ma['white']}))
    ok(f'{lab}: no dark halo in the gray fill just outside the balloon',
       abs(ma['halo']-ma['fill'])<=12,
       json.dumps({'halo':ma['halo'],'fill':ma['fill']}))

    # ---- Perf: static frames, Fit-width scroll, a swipe page turn ----
    # Static, Inks on (baked canvases: no live SVG blur)
    static=pg.evaluate("""()=>new Promise(r=>{
      const ts=[]; let n=0, last=0;
      const tick=t=>{ if(last) ts.push(t-last); last=t; n++; if(n<50) requestAnimationFrame(tick); else r(ts); };
      requestAnimationFrame(tick);
    })""")
    st=frame_stats(static)

    # Fit width continuous scroll with Inks on (3 pages). Warm up once so first-bake cost
    # isn't counted, then measure a second pass — this is the reading-scroll path.
    pg.evaluate('window.__cr.fit.set(true)'); wait_fit(pg); pg.wait_for_timeout(800)
    SCROLL="""(ms)=>new Promise(r=>{
      const stage=document.getElementById('stage');
      stage.scrollTop=0;
      const max=Math.max(1, stage.scrollHeight-stage.clientHeight);
      const ts=[]; let last=0;
      const t0=performance.now();
      const tick=t=>{
        if(last) ts.push(t-last);
        last=t;
        const u=Math.min(1, (t-t0)/ms);
        stage.scrollTop=max*u;
        if(u<1) requestAnimationFrame(tick);
        else r({ts, elapsed:t-t0, scrollHeight:stage.scrollHeight, clientHeight:stage.clientHeight, canvases:stage.querySelectorAll('canvas').length,
                baked:[...stage.querySelectorAll('canvas')].filter(c=>c.classList.contains('inks-baked')).length,
                filt:getComputedStyle(document.querySelector('#stage canvas')||document.body).filter});
      };
      requestAnimationFrame(tick);
    })"""
    warm=pg.evaluate(SCROLL, 900)
    scroll=pg.evaluate(SCROLL, 900)
    sc=frame_stats(scroll['ts'])
    sc['elapsed']=round(scroll['elapsed'],1)
    sc['canvases']=scroll['canvases']
    sc['baked']=scroll['baked']
    sc['filt']=scroll['filt']
    sc['scrollHeight']=scroll['scrollHeight']
    sc['warm_n']=len(warm['ts'])
    sc['warm_p95']=frame_stats(warm['ts']).get('p95')

    # Page turns with Width off (back to swipe), Inks still on
    pg.evaluate('window.__cr.fit.goTo(0); window.__cr.fit.set(false)'); pg.wait_for_timeout(500); wait_render(pg); wait_painted(pg)
    turns=pg.evaluate("""()=>new Promise(async r=>{
      const times=[];
      for(let i=0;i<2;i++){
        const t0=performance.now();
        window.__cr.jumpTo(i+1);
        await new Promise(res=>{
          const start=performance.now();
          const wait=()=>{
            const c=document.querySelector('.view .pg canvas');
            if(c&&c.width>10 && document.querySelectorAll('.view .pg.loading').length===0) res();
            else if(performance.now()-start>4000) res();
            else requestAnimationFrame(wait);
          };
          requestAnimationFrame(wait);
        });
        times.push(performance.now()-t0);
      }
      r(times);
    })""")

    perf={'static':st,'scroll':sc,'turns_ms':[round(x,1) for x in turns],
          'note':'desktop WebKit (not a physical iPad); long frames would suggest baking the filter to a canvas cache'}
    print('PERF', json.dumps(perf), flush=True)
    # Steady scroll should look like Inks-off (baked bitmaps, no live blur). Fail only if pathological.
    ok(f'{lab}: Inks stays interactive (baked canvases, static p95 < 50ms, Fit-width scroll p95 < 80ms, turns < 2.5s)',
       sc.get('baked',0)>=1 and 'none' in (sc.get('filt') or 'none')
       and st.get('p95',999)<50 and sc.get('n',0)>=10 and sc.get('p95',999)<80 and all(t<2500 for t in turns),
       json.dumps(perf))

    ctx.close(); b.close()

print(); failed=sum(1 for x in res if not x)
print(f'{len(res)-failed}/{len(res)} passed', f'({failed} failed)' if failed else '')
if errors:
    print('page errors:'); [print(' ',e) for e in errors]
sys.exit(1 if failed or errors else 0)
