"""cr-v70 suite: Inks darkens only the blacks; mid-grays stay at the v69 curve.
python3 test/e2e_v70.py [webkit]  (server on 127.0.0.1:8823)
Fixture: testpdfs/Ink_Tones_01.pdf — 0.12 scanned-black patch and 0.50 mid-gray patch."""
import sys, os, json
from PIL import Image
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILE=os.path.join(T,'Ink_Tones_01.pdf')
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,'' if cond else str(extra)[:800],flush=True)

def dismiss(pg):
    pg.evaluate("window.__crSplashHide&&window.__crSplashHide(true)")
    pg.wait_for_function("!document.getElementById('splash')||document.getElementById('splash').classList.contains('fly')||document.getElementById('splash').classList.contains('out')")
    pg.wait_for_timeout(200)
def wait_render(pg,t=20000):
    pg.wait_for_function('document.querySelectorAll(".view .pg.loading").length===0 && document.querySelectorAll(".view .pg canvas").length>0',timeout=t)
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
def open_c(pg,title='Ink Tones 01'):
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

# Expected outputs of the v70 table (and the v69 table, for the gray patch).
# Input 0.12 → ~0.056 (near black). Input 0.50 → 0.75, identical to v69.
V69_GRAY=0.75*255   # 191.25
V69_INK=0.346*255   # ~88, what v69 would have done to input 0.12
V70_INK=0.056*255   # ~14

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    w,h,lab,dpr,sat,sab=1024,1366,'ipad-portrait',2,24,20
    ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
    ctx.add_init_script(f"window.__crNoScan=true; window.__crNoBag=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}') if 'access control checks' not in str(e).lower() and 'cross-origin' not in str(e).lower() else None)
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    dismiss(pg)

    src=pg.evaluate("""()=>{
      const r=document.querySelector('#crInks feComponentTransfer[result="ink"] feFuncR')||document.querySelector('#crInks feFuncR');
      return {type:r&&r.getAttribute('type'), table:r&&r.getAttribute('tableValues'), n:r&&(r.getAttribute('tableValues')||'').trim().split(/\\s+/).length};
    }""")
    ok(f'{lab}: Inks table has a dark toe and keeps the v69 mid-grays (21 stops)',
       src['type']=='table' and src['n']==21 and src['table'].strip().startswith('0 0.02 0.04 0.08')
       and '0.75' in src['table'] and ' 0.60 ' in (' '+src['table']+' '),
       json.dumps(src))

    pg.set_input_files('#fileIn',[FILE]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==1 && !document.querySelector(".toast .tb")',timeout=120000)
    open_c(pg); wait_render(pg); wait_painted(pg); show_ui(pg)
    pg.click('#rInks'); pg.wait_for_timeout(300); wait_painted(pg); show_ui(pg)

    shot=os.path.join(SH,f'{ENG}-v70-inks-blacks-ipad-portrait.png')
    pg.screenshot(path=shot)
    box=pg.evaluate("""()=>{ const c=document.querySelector('.view .pg canvas')||document.querySelector('#stage canvas');
      const r=c.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; }""")
    clip=dict(x=max(0,box['x']), y=max(0,box['y']), width=min(box['w'], w-max(0,box['x'])), height=min(box['h'], h-max(0,box['y'])))
    page_path=shot.replace('.png','-page.png')
    pg.screenshot(path=page_path, clip=clip)
    im=Image.open(page_path).convert('RGB')
    # Patch interiors (avoid labels and the black strokes near the top/left of each patch)
    ink=mean_box(im, rel(im, 120, 360, 230, 520))
    gray=mean_box(im, rel(im, 400, 360, 510, 520))
    white=mean_box(im, rel(im, 280, 765, 440, 784))
    ink_lum, gray_lum, white_lum=lum(ink), lum(gray), lum(white)
    meas={'ink':[round(x,1) for x in ink],'ink_lum':round(ink_lum,1),
          'gray':[round(x,1) for x in gray],'gray_lum':round(gray_lum,1),
          'white':[round(x,1) for x in white],'white_lum':round(white_lum,1),
          'v69_ink_would_be':round(V69_INK,1),'v70_ink_expected':round(V70_INK,1),'v69_gray':round(V69_GRAY,1),
          'file':shot}
    print('MEASUREMENTS', json.dumps(meas), flush=True)
    ok(f'{lab}: scanned black at luma 0.12 comes out near black (not v69 charcoal ~88)',
       ink_lum<35 and ink_lum<V69_INK-30,
       json.dumps(meas))
    ok(f'{lab}: mid-gray 0.50 is unchanged from v69 (~191)',
       abs(gray_lum-V69_GRAY)<=20,
       json.dumps(meas))
    ok(f'{lab}: white caption stays white',
       white_lum>230,
       json.dumps(meas))

    ctx.close(); b.close()

print(); failed=sum(1 for x in res if not x)
print(f'{len(res)-failed}/{len(res)} passed', f'({failed} failed)' if failed else '')
if errors:
    print('page errors:'); [print(' ',e) for e in errors]
sys.exit(1 if failed or errors else 0)
