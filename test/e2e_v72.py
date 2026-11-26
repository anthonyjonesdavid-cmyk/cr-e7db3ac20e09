"""cr-v72 suite: Inks strength slider shows only when Inks is on, default matches v71,
persists after reload, and light/dark settings change pixel darkness.
python3 test/e2e_v72.py [webkit]  (server on 127.0.0.1:8823)
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
    px=list(c.getdata())
    return [0.2126*p[0]+0.7152*p[1]+0.0722*p[2] for p in px]
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
        ui:reader&&reader.classList.contains('ui'),
        css:[...document.querySelectorAll('style')].map(s=>s.textContent||'').join(String.fromCharCode(10))
      };
    }""")

def shot_pair(pg, w, h, path):
    show_ui(pg)
    pg.screenshot(path=path)
    box=pg.evaluate("""()=>{ const c=document.querySelector('.view .pg canvas')||document.querySelector('#stage canvas');
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
    pg.evaluate('(s)=>window.__cr.inks.setStrength(s, true)', s)
    pg.wait_for_timeout(400)
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
       'contrast(3.2)' not in (src['css'] or '') and ('--inks-contrast' in (src['css'] or '') or 'contrast(var(--inks-contrast' in (src['css'] or '') or 'contrast(1.5)' in (src['css'] or '')),
       (src['css'] or '')[:500])
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

    pg.click('#rInks'); pg.wait_for_timeout(400); wait_painted(pg); show_ui(pg)
    on=filter_state(pg)
    row=on['row']
    ok(f'{lab}: slider appears under the top bar when Inks is on, default 50',
       on['on'] and on['storeInks']=='true' and not row['hidden'] and row['display']!='none'
       and row['w'] and row['w']>80 and row['h'] and row['h']>10
       and row['y'] is not None and 20<=row['y']<=120
       and on['slider'] and on['slider']['value']=='50' and on['slider']['min']=='0' and on['slider']['max']=='100'
       and on['strength']==0.5 and (on['storeStrength'] in (None,'0.5'))
       and on['table'] and ' '.join(on['table'].split())==V71_TABLE
       and abs(float(on['k2'])-5)<1e-6 and abs(float(on['k3'])+4)<1e-6 and abs(float(str(on['blur']).split()[0])-1.2)<1e-6
       and on['baked'],
       json.dumps({k:on[k] for k in ('on','storeInks','storeStrength','strength','slider','row','table','k2','k3','blur','baked')}))

    # Screenshot with the slider visible at the default
    mid_path=os.path.join(SH,f'{ENG}-v72-inks-slider-ipad-portrait.png')
    mid_box, mid_page=shot_pair(pg,w,h,mid_path)
    ok(f'{lab}: default shot is of page 1 with the chrome up',
       mid_box['pg'].startswith('1 /') and on['ui'],
       json.dumps(mid_box))

    mim=Image.open(mid_page).convert('RGB')
    mm=meas(mim)
    ok(f'{lab}: default strength matches v71 (lettering near-black, mid-gray fill ~191, whites stay white)',
       mm['stroke']<40 and abs(mm['fill']-V70_GRAY)<=10 and mm['white']>230,
       json.dumps(mm))

    # Light end via the actual slider control
    show_ui(pg)
    pg.fill('#rInksStrength','0')
    pg.wait_for_timeout(500); wait_painted(pg); show_ui(pg)
    light_path=os.path.join(SH,f'{ENG}-v72-inks-light-ipad-portrait.png')
    _, light_page=shot_pair(pg,w,h,light_path)
    light=filter_state(pg)
    lim=Image.open(light_page).convert('RGB')
    lm=meas(lim)
    ok(f'{lab}: Light (0) is saved and weakens the boost (k2 near 1, k3 near 0)',
       light['slider']['value']=='0' and abs(light['strength']-0)<1e-9 and light['storeStrength']=='0'
       and abs(float(light['k2'])-1)<1e-6 and abs(float(light['k3'])-0)<1e-6,
       json.dumps({k:light[k] for k in ('slider','strength','storeStrength','k2','k3','table')}))

    # Dark end
    set_strength(pg, 1)
    show_ui(pg)
    dark_path=os.path.join(SH,f'{ENG}-v72-inks-dark-ipad-portrait.png')
    _, dark_page=shot_pair(pg,w,h,dark_path)
    dark=filter_state(pg)
    dim=Image.open(dark_page).convert('RGB')
    dm=meas(dim)
    print('MEASUREMENTS', json.dumps({'mid':mm,'light':lm,'dark':dm,
                                      'slider':mid_path,'light_shot':light_path,'dark_shot':dark_path}), flush=True)
    ok(f'{lab}: Dark (1) uses a stronger boost than v71 (k2>5, k3<-4)',
       dark['slider']['value']=='100' and abs(dark['strength']-1)<1e-9 and dark['storeStrength']=='1'
       and float(dark['k2'])>5.5 and float(dark['k3'])<-4.5,
       json.dumps({k:dark[k] for k in ('slider','strength','storeStrength','k2','k3')}))
    ok(f'{lab}: Light is measurably lighter than the default (lettering and overall)',
       lm['stroke']>mm['stroke']+20 and lm['mean']>mm['mean']+5,
       json.dumps({'light':lm,'mid':mm}))
    ok(f'{lab}: Dark is measurably darker than the default (fill and overall)',
       dm['fill']<mm['fill']-8 and dm['mean']<mm['mean']-4 and dm['stroke']<=mm['stroke']+2,
       json.dumps({'dark':dm,'mid':mm}))
    ok(f'{lab}: whites stay white at Light and Dark',
       lm['white']>230 and dm['white']>220,
       json.dumps({'light':lm['white'],'dark':dm['white']}))

    # Persist Dark=1 across reload
    pg.reload(); pg.wait_for_selector('html[data-ready]'); dismiss(pg)
    pg.wait_for_selector('#reader:not(.hidden)', timeout=60000)
    wait_render(pg); wait_painted(pg); show_ui(pg)
    after=filter_state(pg)
    ok(f'{lab}: after reload, Inks stays on at strength 1 and the slider shows 100',
       after['on'] and after['storeInks']=='true' and after['storeStrength']=='1'
       and after['strength']==1 and after['slider']['value']=='100'
       and not after['row']['hidden'] and after['row']['display']!='none'
       and float(after['k2'])>5.5,
       json.dumps({k:after[k] for k in ('on','storeInks','storeStrength','strength','slider','row','k2','k3')}))
    # Confirm pixels are still the dark look, not the default
    _, persist_page=shot_pair(pg,w,h,os.path.join(SH,f'{ENG}-v72-inks-persist-ipad-portrait.png'))
    pm=meas(Image.open(persist_page).convert('RGB'))
    ok(f'{lab}: reloaded page is still the darker look, not the v71 default',
       pm['fill']<mm['fill']-8 and pm['mean']<mm['mean']-4,
       json.dumps({'persist':pm,'mid':mm,'dark':dm}))

    # Turning Inks off hides the slider; strength is kept
    pg.click('#rInks'); pg.wait_for_timeout(200); show_ui(pg)
    hidden=filter_state(pg)
    ok(f'{lab}: turning Inks off hides the slider and keeps the saved strength',
       not hidden['on'] and hidden['row']['hidden'] and hidden['row']['display']=='none'
       and hidden['storeStrength']=='1' and hidden['strength']==1,
       json.dumps({k:hidden[k] for k in ('on','row','storeStrength','strength')}))

    # Width mode: slider still available and can be changed
    pg.click('#rInks'); pg.wait_for_timeout(300); wait_painted(pg)
    pg.evaluate('window.__cr.fit.set(true)'); wait_fit(pg); pg.wait_for_timeout(400); show_ui(pg)
    set_strength(pg, 0.5)
    show_ui(pg)
    fit=filter_state(pg)
    ok(f'{lab}: slider still shows in Width, and resetting to 50 restores the v71 filter',
       fit['on'] and not fit['row']['hidden'] and fit['slider']['value']=='50'
       and ' '.join((fit['table'] or '').split())==V71_TABLE
       and abs(float(fit['k2'])-5)<1e-6,
       json.dumps({k:fit[k] for k in ('on','row','slider','table','k2','k3')}))

    # Auto-hide with the other chrome
    pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(250)
    gone=pg.evaluate("""()=>{
      const top=document.getElementById('rtop'), row=document.getElementById('inksRow');
      const t=getComputedStyle(top), r=row.getBoundingClientRect();
      return {ui:document.getElementById('reader').classList.contains('ui'), vis:t.visibility, transform:t.transform, y:r.y, h:r.height};
    }""")
    ok(f'{lab}: slider auto-hides with the reader bars when the chrome is off',
       not gone['ui'] and (gone['vis']=='hidden' or gone['y']+gone['h']<=0 or 'matrix' in (gone['transform'] or '') and gone['y']<0),
       json.dumps(gone))

    # iPhone and landscape: slider stays on screen and usable
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
           not st['hidden'] and st['display']!='none' and st['s']['w']>60 and st['s']['h']>16 and not st['overflow'],
           json.dumps(st))

    show_ui(pg)
    check_viewport(390,844,'iphone-portrait')
    check_viewport(1180,820,'ipad-landscape')
    check_viewport(320,568,'iphone-se')  # tight split-ish / small phone
    check_viewport(700,1024,'ipad-splitish')

    ctx.close(); b.close()

print(); failed=sum(1 for x in res if not x)
print(f'{len(res)-failed}/{len(res)} passed', f'({failed} failed)' if failed else '')
if errors:
    print('page errors:'); [print(' ',e) for e in errors]
sys.exit(1 if failed or errors else 0)
