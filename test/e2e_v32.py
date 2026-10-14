"""cr-v32 suite: page sharpness.  python3 test/e2e_v32.py [webkit]  (server on 127.0.0.1:8823)
Every visible page's canvas backing store must be >= its displayed CSS size x devicePixelRatio (after opening, page turns, fast turns
while renders are slow, jumps and rotation), with an iPad/iPhone user agent so the iOS memory caps apply. Fixtures: original abstract comics."""
import sys, os, json, glob, subprocess
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots')
SP=os.path.join(T,'spreads','Wide_Horizon_01.pdf')
if not os.path.exists(SP): subprocess.run([sys.executable,os.path.join(HERE,'gen_spreads.py')],check=True)
FILES=[SP,os.path.join(T,'Nightfall_01.pdf')]
UA='Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
Q="""(()=>[...document.querySelectorAll('#zoomer .view .pg')].filter(d=>d.dataset.p!=null&&+d.dataset.p<__cr.R.n).map(d=>{const c=d.querySelector('canvas:not(.tile)'); if(!c) return {p:+d.dataset.p,missing:1,r:0};
  const b0=c.getBoundingClientRect(), rot=!!d.closest('.view.rot'), b=rot?{width:b0.height,height:b0.width}:b0, dpr=Math.min(devicePixelRatio,2); return {p:+d.dataset.p,bw:c.width,bh:c.height,cw:Math.round(b.width*dpr),ch:Math.round(b.height*dpr),interim:!!d.dataset.interim,r:+Math.min(c.width/(b.width*dpr),c.height/(b.height*dpr)).toFixed(3)}}))()"""
def settle(pg): pg.wait_for_timeout(200); pg.wait_for_function('!__cr.animating && !__cr.flip && document.querySelectorAll(".view .pg.loading,.view .pg[data-interim]").length===0',timeout=20000); pg.wait_for_timeout(200)
def sharp(pg,lab,what):
    settle(pg); q=pg.evaluate(Q); ok(f'{lab}: {what}: every visible page backing >= CSS size x DPR ({len(q)} page{"s" if len(q)!=1 else ""})',q and all(x['r']>=0.995 and not x['interim'] for x in q),json.dumps(q)); return q
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr,user_agent=UA)
        ctx.add_init_script(f"window.__crNoScan=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        if lab=='ipad-landscape': ok('iOS caps active in this run (iPad user agent)',pg.evaluate("navigator.userAgent.includes('iPad')"))
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==2 && !document.querySelector(".toast .tb")',timeout=60000)
        for title in ['Nightfall 01','Wide Horizon 01']:
            pg.click('#tabs [data-tab=library]'); pg.click(f'#libGrid .lc[data-title="{title}"]'); pg.wait_for_selector('#reader:not(.hidden)')
            sharp(pg,lab,f'{title} open')
            pg.evaluate('__cr.jumpTo(2)'); q=sharp(pg,lab,f'{title} p3')
            if title=='Nightfall 01' and w>h: ok(f'{lab}: 2-up shows two pages',len(q)==2,json.dumps(q))
            for k in range(3): pg.evaluate('__cr.go(-1)'); sharp(pg,lab,f'{title} after turn {k+1}')
            pg.evaluate('__cr.go(1)'); sharp(pg,lab,f'{title} after turning back')
            pg.evaluate('__cr.jumpTo(1)'); settle(pg); pg.evaluate('window.__crSlow=300')
            for k in range(3): pg.evaluate('__cr.go(-1,120)'); pg.wait_for_timeout(140)
            sharp(pg,lab,f'{title} fast turns while renders are slow (placeholders upgraded)')
            pg.evaluate('__cr.jumpTo(1)'); pg.wait_for_timeout(60); pg.evaluate('__cr.jumpTo(5)'); sharp(pg,lab,f'{title} quick jumps'); pg.evaluate('window.__crSlow=0')
            if title=='Wide Horizon 01':
                pg.evaluate('__cr.jumpTo(2)'); q=sharp(pg,lab,'full-screen spread')
                if h>w:
                    pg.click('#rRotate'); sharp(pg,lab,'rotated spread (Rotate button)'); pg.click('#rRotate')
            pg.set_viewport_size({'width':h,'height':w}); pg.wait_for_timeout(500); sharp(pg,lab,f'{title} after device rotation')
            pg.evaluate('__cr.go(-1)'); sharp(pg,lab,f'{title} turn after rotation')
            pg.set_viewport_size({'width':w,'height':h}); pg.wait_for_timeout(500); sharp(pg,lab,f'{title} rotated back')
            if title=='Nightfall 01' and w>h:
                pg.evaluate('__cr.jumpTo(3)'); settle(pg); pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(300); pg.screenshot(path=f'{SH}/{ENG}-v32-2up-{lab}.png')
            if lab=='ipad-landscape' and title=='Wide Horizon 01':
                sr=pg.evaluate('Promise.all([__cr.srcRes(0),__cr.srcRes(2)])'); ok('diagnostic: embedded scan size per page (600x922 page, 1200x922 spread)',sr[0]['w']==600 and sr[0]['h']==922 and sr[1]['w']==1200,json.dumps(sr))
            pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
        ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
