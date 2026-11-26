"""cr-v73 suite: smooth Inks slider — thumb tracks a drag, no long frames mid-drag,
final bake matches v72 at the same setting, and the setting persists.
python3 test/e2e_v73.py [webkit]  (server on 127.0.0.1:8823)
Fixture: testpdfs/Ink_Lines_01.pdf — scan-like lettering and hatching over a 0.50 gray fill."""
import sys, os, json
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
def wait_settled(pg):
    pg.evaluate("()=>window.__cr&&window.__cr.inks&&window.__cr.inks.whenSettled?window.__cr.inks.whenSettled():Promise.resolve()")
    wait_painted(pg)
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
def crop_luma(im, dbox):
    x0,y0,x1,y1=rel(im,*dbox)
    c=im.crop((x0,y0,x1,y1)).convert('RGB')
    try:
        px=list(c.get_flattened_data())
        # RGB triples from flattened
        out=[]
        data=list(c.getdata()) if False else None
    except Exception:
        px=None
    if px is None:
        data=list(c.getdata())
        return [0.2126*p[0]+0.7152*p[1]+0.0722*p[2] for p in data]
    # fallback already handled
    data=list(c.getdata())
    return [0.2126*p[0]+0.7152*p[1]+0.0722*p[2] for p in data]
def dark_percentile(vals, p=8):
    if not vals: return 255.0
    s=sorted(vals)
    i=max(0, min(len(s)-1, int(len(s)*p/100.0)))
    return s[i]
def mean_luma(im):
    c=im.convert('RGB').resize((1,1), Image.Resampling.BOX)
    return lum(c.getpixel((0,0))[:3])

TEXT=(160,132,440,200)
FILL=(70,300,140,360)
WHITE=(250,100,350,130)
V70_GRAY=0.75*255
V71_TABLE='0 0.02 0.04 0.08 0.18 0.36 0.60 0.64 0.68 0.715 0.75 0.785 0.82 0.86 0.90 0.925 0.95 0.965 0.98 0.99 1'

def filter_state(pg):
    return pg.evaluate("""()=>{
      const f=document.getElementById('crInks');
      const ink=f&&f.querySelector('feComponentTransfer[result="ink"] feFuncR');
      const blur=f&&f.querySelector('feGaussianBlur');
      const boost=f&&f.querySelector('feComposite[result="unsharp"]');
      const sl=document.getElementById('rInksStrength');
      const row=document.getElementById('inksRow');
      const cs=row?getComputedStyle(row):null;
      const r=row?row.getBoundingClientRect():null;
      const reader=document.getElementById('reader');
      const page=document.querySelector('#stage canvas');
      return {
        table:ink&&ink.getAttribute('tableValues'),
        n:ink&&(ink.getAttribute('tableValues')||'').trim().split(/\\s+/).length,
        blur:blur&&blur.getAttribute('stdDeviation'),
        k2:boost&&boost.getAttribute('k2'), k3:boost&&boost.getAttribute('k3'),
        contrast:reader&&getComputedStyle(reader).getPropertyValue('--inks-contrast').trim(),
        brightness:reader&&getComputedStyle(reader).getPropertyValue('--inks-brightness').trim(),
        slider:sl&&{value:sl.value,min:sl.min,max:sl.max,aria:sl.getAttribute('aria-label')},
        row:{hidden:row&&row.classList.contains('hidden'), aria:row&&row.getAttribute('aria-hidden'),
             display:cs&&cs.display, vis:cs&&cs.visibility,
             x:r&&r.x, y:r&&r.y, w:r&&r.width, h:r&&r.height},
        on:document.querySelector('#rInks')?.classList.contains('on'),
        storeInks:localStorage.getItem('cr.inks'),
        storeStrength:localStorage.getItem('cr.inksStrength'),
        strength:window.__cr&&window.__cr.inks&&window.__cr.inks.strength(),
        baked:!!(page&&page.classList.contains('inks-baked')),
        dragging:!!(reader&&reader.classList.contains('inks-dragging')),
        ui:reader&&reader.classList.contains('ui'),
        css:[...document.querySelectorAll('style')].map(s=>s.textContent||'').join(String.fromCharCode(10))
      };
    }""")

def shot_pair(pg, w, h, path):
    show_ui(pg)
    pg.screenshot(path=path)
    box=pg.evaluate("""()=>{ const c=document.querySelector('.view .pg canvas.inks-baked')||document.querySelector('.view .pg canvas')||document.querySelector('#stage canvas');
      const r=c.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height, pg:document.getElementById('pgText').textContent}; }""")
    clip=dict(x=max(0,box['x']), y=max(0,box['y']), width=min(box['w'], w-max(0,box['x'])), height=min(box['h'], h-max(0,box['y'])))
    page_path=path.replace('.png','-page.png')
    pg.screenshot(path=page_path, clip=clip)
    return box, page_path

def meas(im):
    text=crop_luma(im, TEXT)
    fill=lum(mean_box(im, rel(im,*FILL)))
    white=lum(mean_box(im, rel(im,*WHITE)))
    return {
        'stroke':round(dark_percentile(text,8),1),
        'fill':round(fill,1),
        'white':round(white,1),
        'mean':round(mean_luma(im),1),
    }

def set_strength(pg, s):
    pg.evaluate("(s)=>{ window.__cr.inks.setStrength(s, true); return window.__cr.inks.whenSettled(); }", s)
    wait_painted(pg)

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    w,h,lab,dpr,sat,sab=1024,1366,'ipad-portrait',2,24,20
    ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
    ctx.add_init_script(f"window.__crNoScan=true; window.__crNoBag=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}') if 'access control checks' not in str(e).lower() and 'cross-origin' not in str(e).lower() else None)
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    dismiss(pg)

    src=filter_state(pg)
    ok(f'{lab}: default SVG filter is exactly the v71 table + boost (blur 1.2, k2=5, k3=-4)',
       src['table'] and ' '.join(src['table'].split())==V71_TABLE and src['n']==21
       and src['blur'] is not None and abs(float(str(src['blur']).split()[0])-1.2)<1e-6
       and src.get('k2') is not None and abs(float(src['k2'])-5)<1e-6 and abs(float(src['k3'])+4)<1e-6,
       json.dumps({k:src[k] for k in ('table','n','blur','k2','k3')}))
    ok(f'{lab}: CSS fallback scales contrast via --inks-contrast (no contrast(3.2))',
       'contrast(3.2)' not in (src['css'] or '') and '--inks-contrast' in (src['css'] or '') and 'grayscale(1)' in (src['css'] or ''),
       'missing fallback')
    ok(f'{lab}: slider starts hidden while Inks is off',
       src['row']['hidden'] and src['row']['display']=='none' and not src['on']
       and (src['storeStrength'] in (None,'0.5') or src['strength']==0.5),
       json.dumps({'row':src['row'],'on':src['on'],'store':src['storeStrength'],'strength':src['strength']}))

    pg.set_input_files('#fileIn',[FILE]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==1 && !document.querySelector(".toast .tb")',timeout=120000)
    open_c(pg); wait_render(pg); wait_painted(pg); show_ui(pg)

    off=filter_state(pg)
    ok(f'{lab}: opening a comic does not show the slider until Inks is on',
       off['row']['hidden'] and off['row']['display']=='none' and not off['on'],
       json.dumps(off['row']))

    pg.click('#rInks'); wait_settled(pg); show_ui(pg)
    on=filter_state(pg)
    row=on['row']
    ok(f'{lab}: slider appears under the top bar when Inks is on, default 50',
       on['on'] and on['storeInks']=='true' and not row['hidden'] and row['display']!='none'
       and row['w'] and row['w']>80 and row['h'] and row['h']>10
       and row['y'] is not None and 20<=row['y']<=140
       and on['slider'] and on['slider']['value']=='50' and on['slider']['min']=='0' and on['slider']['max']=='100'
       and on['strength']==0.5 and (on['storeStrength'] in (None,'0.5'))
       and on['table'] and ' '.join(on['table'].split())==V71_TABLE
       and abs(float(on['k2'])-5)<1e-6 and abs(float(on['k3'])+4)<1e-6 and abs(float(str(on['blur']).split()[0])-1.2)<1e-6
       and on['baked'] and not on['dragging'],
       json.dumps({k:on[k] for k in ('on','storeInks','storeStrength','strength','slider','row','table','k2','k3','blur','baked','dragging')}))

    mid_path=os.path.join(SH,f'{ENG}-v73-inks-slider-ipad-portrait.png')
    mid_box, mid_page=shot_pair(pg,w,h,mid_path)
    ok(f'{lab}: default shot is of page 1 with the chrome up',
       mid_box['pg'].startswith('1 /') and on['ui'],
       json.dumps(mid_box))

    mim=Image.open(mid_page).convert('RGB')
    mm=meas(mim)
    ok(f'{lab}: default strength matches v71/v72 (lettering near-black, mid-gray fill ~191, whites stay white)',
       mm['stroke']<40 and abs(mm['fill']-V70_GRAY)<=10 and mm['white']>230,
       json.dumps(mm))

    hit=pg.evaluate("""()=>{
      const sl=document.getElementById('rInksStrength'), row=document.getElementById('inksRow');
      const cs=getComputedStyle(sl), rs=getComputedStyle(row), r=sl.getBoundingClientRect();
      return {h:r.height, touch:cs.touchAction, rowTouch:rs.touchAction};
    }""")
    ok(f'{lab}: slider has a >=44px hit area and touch-action:none',
       hit['h']>=44 and hit['touch']=='none' and hit['rowTouch']=='none',
       json.dumps(hit))

    show_ui(pg)
    drag=pg.evaluate("""()=>new Promise(async r=>{
      const sl=document.getElementById('rInksStrength'), reader=document.getElementById('reader');
      const raf=()=>new Promise(res=>requestAnimationFrame(t=>res(t)));
      // Idle baseline: rAF in this WebKit can already sit near 50ms, so compare against it.
      let last=await raf();
      const idle=[];
      for(let i=0;i<20;i++){ const t=await raf(); idle.push(t-last); last=t; }
      const frames=[], values=[], handlers=[];
      sl.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));
      sl.value='50';
      let t0=performance.now(); sl.dispatchEvent(new Event('input',{bubbles:true})); handlers.push(performance.now()-t0);
      last=await raf();
      const start=last;
      for(let v=50; v>=8; v-=2){
        sl.value=String(v);
        t0=performance.now(); sl.dispatchEvent(new Event('input',{bubbles:true})); handlers.push(performance.now()-t0);
        const t=await raf(); frames.push(t-last); last=t;
        values.push({v:+sl.value, live:window.__cr.inks.strength(), pct:reader.style.getPropertyValue('--inks-pct'), drag:reader.classList.contains('inks-dragging')});
      }
      sl.dispatchEvent(new Event('change',{bubbles:true}));
      sl.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}));
      await (window.__cr.inks.whenSettled()||Promise.resolve());
      r({frames, idle, handlers, values, elapsed:last-start, final:window.__cr.inks.strength(), store:localStorage.getItem('cr.inksStrength')});
    })""")
    def pctile(xs, p):
        if not xs: return 999
        s=sorted(xs)
        return s[max(0, min(len(s)-1, int(round((len(s)-1)*p/100))))]
    vals=drag['values']
    lives=[round(v['live']*100) for v in vals]
    pcts=[]
    for v in vals:
        raw=(v['pct'] or '').strip()
        try: pcts.append(float(raw.replace('%','')))
        except Exception: pcts.append(None)
    followed=len(vals)>=8 and all(v['drag'] for v in vals) and lives==sorted(lives, reverse=True) and lives[0]>=40 and lives[-1]<=20
    pct_ok=all(p is not None for p in pcts) and pcts==sorted(pcts, reverse=True)
    idle, frames, handlers=drag['idle'][2:], drag['frames'][2:], drag['handlers']
    idle_p95, drag_p95=pctile(idle,95), pctile(frames,95)
    hand_p95, hand_max=pctile(handlers,95), (max(handlers) if handlers else 999)
    drag_max=max(frames) if frames else 999
    print('DRAG', json.dumps({'n':len(vals),'lives':lives,'pcts':pcts,
                              'idle_p95':round(idle_p95,2),'drag_p95':round(drag_p95,2),'drag_max':round(drag_max,2),
                              'hand_p95':round(hand_p95,2),'hand_max':round(hand_max,2),
                              'elapsed':round(drag['elapsed'],1),'final':drag['final'],'store':drag['store']}), flush=True)
    ok(f'{lab}: thumb/value/--inks-pct follow a simulated drag (and inks-dragging stays on)',
       followed and pct_ok,
       json.dumps({'lives':lives,'pcts':pcts,'drag':[v['drag'] for v in vals]}))
    # The input handler must stay tiny (no bake on input) — that is what keeps the thumb at 60fps.
    # rAF intervals in this WebKit can include software paints of the page; a mid-drag full bake
    # would be well over 80ms, so treat that as the spike ceiling.
    ok(f'{lab}: input handler stays under 8ms and no mid-drag bake spike (frames < 80ms)',
       handlers and hand_p95<8 and hand_max<16 and frames and drag_max<80,
       json.dumps({'hand_p95':round(hand_p95,2),'hand_max':round(hand_max,2),'idle_p95':round(idle_p95,2),'drag_p95':round(drag_p95,2),'drag_max':round(drag_max,2),'idle':[round(x,1) for x in idle],'frames':[round(x,1) for x in frames]}))

    # Finish at Light 0 and measure — must match the v72 Light results
    set_strength(pg, 0); show_ui(pg)
    light=filter_state(pg)
    light_path=os.path.join(SH,f'{ENG}-v73-inks-light-ipad-portrait.png')
    _, light_page=shot_pair(pg,w,h,light_path)
    lm=meas(Image.open(light_page).convert('RGB'))
    ok(f'{lab}: Light (0) is saved and weakens the boost (k2 near 1, k3 near 0)',
       light['slider']['value']=='0' and abs(light['strength']-0)<1e-9 and light['storeStrength']=='0'
       and abs(float(light['k2'])-1)<1e-6 and abs(float(light['k3'])-0)<1e-6,
       json.dumps({k:light[k] for k in ('slider','strength','storeStrength','k2','k3','table')}))

    set_strength(pg, 1); show_ui(pg)
    dark=filter_state(pg)
    dark_path=os.path.join(SH,f'{ENG}-v73-inks-dark-ipad-portrait.png')
    _, dark_page=shot_pair(pg,w,h,dark_path)
    dm=meas(Image.open(dark_page).convert('RGB'))
    print('MEASUREMENTS', json.dumps({'mid':mm,'light':lm,'dark':dm,
                                      'slider':mid_path,'light_shot':light_path,'dark_shot':dark_path}), flush=True)
    ok(f'{lab}: Dark (1) uses a stronger boost than v71 (k2>5, k3<-4)',
       dark['slider']['value']=='100' and abs(dark['strength']-1)<1e-9 and dark['storeStrength']=='1'
       and float(dark['k2'])>5.5 and float(dark['k3'])<-4.5,
       json.dumps({k:dark[k] for k in ('slider','strength','storeStrength','k2','k3')}))
    ok(f'{lab}: final bake at Light and Dark matches v72 (Light lighter, Dark darker, whites stay white)',
       lm['stroke']>mm['stroke']+20 and lm['mean']>mm['mean']+5
       and dm['fill']<mm['fill']-8 and dm['mean']<mm['mean']-4 and dm['stroke']<=mm['stroke']+2
       and lm['white']>230 and dm['white']>220
       and abs(lm['stroke']-147)<40 and abs(lm['fill']-192)<=12
       and abs(dm['fill']-174)<=14 and dm['stroke']<15,
       json.dumps({'light':lm,'mid':mm,'dark':dm}))

    # Persist Dark=1 across reload
    pg.reload(); pg.wait_for_selector('html[data-ready]'); dismiss(pg)
    pg.wait_for_selector('#reader:not(.hidden)', timeout=60000)
    wait_render(pg); wait_settled(pg); show_ui(pg)
    after=filter_state(pg)
    ok(f'{lab}: after reload, Inks stays on at strength 1 and the slider shows 100',
       after['on'] and after['storeInks']=='true' and after['storeStrength']=='1'
       and after['strength']==1 and after['slider']['value']=='100'
       and not after['row']['hidden'] and after['row']['display']!='none'
       and float(after['k2'])>5.5,
       json.dumps({k:after[k] for k in ('on','storeInks','storeStrength','strength','slider','row','k2','k3')}))
    _, persist_page=shot_pair(pg,w,h,os.path.join(SH,f'{ENG}-v73-inks-persist-ipad-portrait.png'))
    pm=meas(Image.open(persist_page).convert('RGB'))
    ok(f'{lab}: reloaded page is still the darker look, not the v71 default',
       pm['fill']<mm['fill']-8 and pm['mean']<mm['mean']-4,
       json.dumps({'persist':pm,'mid':mm,'dark':dm}))

    pg.click('#rInks'); pg.wait_for_timeout(200); show_ui(pg)
    hidden=filter_state(pg)
    ok(f'{lab}: turning Inks off hides the slider and keeps the saved strength',
       not hidden['on'] and hidden['row']['hidden'] and hidden['row']['display']=='none'
       and hidden['storeStrength']=='1' and hidden['strength']==1,
       json.dumps({k:hidden[k] for k in ('on','row','storeStrength','strength')}))

    pg.click('#rInks'); wait_settled(pg)
    pg.evaluate('window.__cr.fit.set(true)'); wait_fit(pg); pg.wait_for_timeout(200); show_ui(pg)
    set_strength(pg, 0.5)
    show_ui(pg)
    fit=filter_state(pg)
    ok(f'{lab}: slider still shows in Width, and resetting to 50 restores the v71 filter',
       fit['on'] and not fit['row']['hidden'] and fit['slider']['value']=='50'
       and ' '.join((fit['table'] or '').split())==V71_TABLE
       and abs(float(fit['k2'])-5)<1e-6,
       json.dumps({k:fit[k] for k in ('on','row','slider','table','k2','k3')}))

    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250)
    gone=pg.evaluate("""()=>{
      const top=document.getElementById('rtop'), row=document.getElementById('inksRow');
      const t=getComputedStyle(top), r=row.getBoundingClientRect();
      return {ui:document.getElementById('reader').classList.contains('ui'), vis:t.visibility, transform:t.transform, y:r.y, h:r.height};
    }""")
    ok(f'{lab}: slider auto-hides with the reader bars when the chrome is off',
       not gone['ui'] and (gone['vis']=='hidden' or gone['y']+gone['h']<=0 or 'matrix' in (gone['transform'] or '') and gone['y']<0),
       json.dumps(gone))

    def check_viewport(vw,vh,name):
        pg.set_viewport_size({'width':vw,'height':vh})
        pg.wait_for_timeout(400)
        pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(150)
        st=pg.evaluate("""()=>{
          const row=document.getElementById('inksRow'), sl=document.getElementById('rInksStrength');
          const r=row.getBoundingClientRect(), s=sl.getBoundingClientRect();
          const W=window.innerWidth, H=window.innerHeight;
          return {hidden:row.classList.contains('hidden'), display:getComputedStyle(row).display,
                  r:{x:r.x,y:r.y,w:r.width,h:r.height}, s:{x:s.x,y:s.y,w:s.width,h:s.height},
                  W,H, overflow:r.right>W+1||r.left<-1||r.bottom>H+1};
        }""")
        ok(f'{name}: slider is visible and stays on screen',
           not st['hidden'] and st['display']!='none' and st['s']['w']>60 and st['s']['h']>=44 and not st['overflow'],
           json.dumps(st))

    show_ui(pg)
    check_viewport(390,844,'iphone-portrait')
    check_viewport(1180,820,'ipad-landscape')
    check_viewport(320,568,'iphone-se')
    check_viewport(700,1024,'ipad-splitish')

    ctx.close(); b.close()

print(); failed=sum(1 for x in res if not x)
print(f'{len(res)-failed}/{len(res)} passed', f'({failed} failed)' if failed else '')
if errors:
    print('page errors:'); [print(' ',e) for e in errors]
sys.exit(1 if failed or errors else 0)
