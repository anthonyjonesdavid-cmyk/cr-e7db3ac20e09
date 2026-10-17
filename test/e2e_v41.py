"""cr-v41 suite: Timeline decade chips (real touch taps, every chip, after strip / grid scrolls, empty decades) + built-in release list.
python3 test/e2e_v41.py [webkit]  (server on 127.0.0.1:8823). Fixtures: original abstract comics. Standalone insets via --sat/--sab."""
import sys, os, json, glob, subprocess
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); D=os.path.join(T,'dates'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(os.path.join(D,'Deep_Signal_02.pdf')): subprocess.run([sys.executable,os.path.join(HERE,'gen_dates.py')],check=True)
FILES=sorted(glob.glob(os.path.join(T,'*.pdf')))+sorted(glob.glob(os.path.join(D,'*.pdf')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
# 1970s x3, 1980s none (empty), 1990s x8, 2000s x many, 2010s x2 (too few to reach the top), 3 unknown
SEED="""(()=>{ const B=__cr.comics[0]; for(let i=0;i<150;i++) __cr.comics.push({...B,id:'syn'+i,title:'Syn '+String(i).padStart(3,'0'),fileName:'Syn_'+i+'.pdf'}); const C=__cr.comics.slice().sort((a,b)=>a.title.localeCompare(b.title)); const n=C.length;
  C.forEach((c,i)=>{ c.metaDate=null; c.onlineDate=null; delete c.driveId;
    let y; if(i<3) y=1975+i; else if(i<11) y=1990+i-3; else if(i<n-5) y=(i<60?1990:2000)+(i%10); else if(i<n-3) y=2014+(i-(n-5)); else y=0;
    if(y) c.dateManual={y,m:1+(i%12)}; else { delete c.dateManual; c.fileName='Untitled_'+i+'.pdf'; c.title='Untitled '+i; } });
  __cr.dates.render(); return n; })()"""
ST="""(()=>{ const el=document.querySelector('#tlScroll'), er=el.getBoundingClientRect(); const on=[...document.querySelectorAll('#tlDec .chip.on')].map(b=>b.dataset.dec);
  let first=null; for(const c of el.querySelectorAll('.tc')){ const r=c.getBoundingClientRect(); if(r.bottom>er.top+8){ first=c.dataset.dec; break; } }
  return {top:el.scrollTop,max:el.scrollHeight-el.clientHeight,on,first}; })()"""
def target(pg,dec):
    return pg.evaluate("""d=>{ const el=document.querySelector('#tlScroll'), er=el.getBoundingClientRect(), s=el.querySelector(`.tc[data-dec="${d}"]`); if(!s) return null; const r=s.getBoundingClientRect(); return {dy:r.top-er.top,vis:r.top>=er.top-1&&r.top<er.bottom-20}; }""",dec)
def settle(pg):
    pg.evaluate("""async()=>{ const el=document.querySelector('#tlScroll'); let last=-1,same=0; for(let i=0;i<200&&same<8;i++){ await new Promise(r=>requestAnimationFrame(r)); if(el.scrollTop===last) same++; else { same=0; last=el.scrollTop; } } }""")
def tapchip(pg,dec):
    pg.evaluate("d=>{ const b=document.querySelector(`#tlDec .chip[data-dec=\"${d}\"]`); const st=document.querySelector('#tlDec'); const l=b.offsetLeft-st.offsetLeft; if(l<st.scrollLeft||l+b.offsetWidth>st.scrollLeft+st.clientWidth) st.scrollLeft=l-10; }",dec)
    pg.wait_for_timeout(60); bb=pg.locator(f'#tlDec .chip[data-dec="{dec}"]').bounding_box()
    hit=pg.evaluate("([x,y,d])=>{ const e=document.elementFromPoint(x,y); return !!(e&&e.closest(`.chip[data-dec=\"${d}\"]`)); }",[bb['x']+bb['width']/2,bb['y']+bb['height']/2,dec])
    pg.touchscreen.tap(bb['x']+bb['width']/2,bb['y']+bb['height']/2); settle(pg); return bb,hit
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        ok(f'{lab}: app launches on Home',pg.evaluate("!document.querySelector('#home').classList.contains('hidden')"))
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        pg.click('#tabs [data-tab=timeline]'); pg.wait_for_timeout(300); pg.evaluate(SEED); pg.wait_for_timeout(300)
        chips=pg.evaluate("[...document.querySelectorAll('#tlDec .chip')].map(b=>b.dataset.dec)")
        ok(f'{lab}: chips cover every decade in range, incl. the empty 1980s, + Unknown',chips==['1970','1980','1990','2000','2010','unk'],chips)
        sizes=pg.evaluate("""[...document.querySelectorAll('#tlDec .chip')].map(b=>{const r=b.getBoundingClientRect(); return [r.width,r.height,r.top]})""")
        ok(f'{lab}: chips >=40px tall/wide and below the status bar',all(s[0]>=40 and s[1]>=40 and s[2]>=sat for s in sizes),sizes)
        ta=pg.evaluate("[getComputedStyle(document.querySelector('#tlDec')).touchAction,getComputedStyle(document.querySelector('#tlDec .chip')).touchAction]")
        ok(f'{lab}: strip pans horizontally only, chips use manipulation (no tap delay / no vertical swallow)',ta[0]=='pan-x' and ta[1]=='manipulation',ta)
        order=['2010','1970','unk','1990','2000','1980','2010','1990','1970']
        for k,dec in enumerate(order):
            if k==3: pg.evaluate("document.querySelector('#tlScroll').scrollTop=document.querySelector('#tlScroll').scrollHeight"); settle(pg)
            if k==5: pg.evaluate("document.querySelector('#tlScroll').scrollTop=200"); settle(pg)
            if k in (4,7): pg.evaluate("document.querySelector('#tlDec').scrollLeft=9999"); pg.wait_for_timeout(80)
            bb,hit=tapchip(pg,dec); s=pg.evaluate(ST); land='1970' if dec=='1980' else dec   # 1970s and 1990s are equally near: the later... see below
            if dec=='1980': land=s['on'][0] if s['on'] else None
            t=target(pg,land) if land else None
            good=hit and t and (abs(t['dy']-8)<=3 or (s['top']>=s['max']-1 and t['vis'])) and s['on']==[land]
            ok(f'{lab}: tap {dec}s chip ({["fresh","fresh","fresh","after grid scrolled to end","after strip scrolled","after grid scrolled","fresh","after strip scrolled","fresh"][k]}) jumps to the first issue and lights only that chip',good,json.dumps([dec,hit,t,s]))
            if dec=='1980':
                note=pg.evaluate("document.querySelector('.toast')?.textContent||''")
                ok(f'{lab}: empty 1980s jumps to the nearest decade with a brief note',land in ('1970','1990') and 'No issues from the 1980s' in note,json.dumps([land,note]))
        # pin holds while idle, user scroll returns control to scroll-spy
        pg.wait_for_timeout(500); s=pg.evaluate(ST); ok(f'{lab}: highlight stays on the tapped chip after the jump settles',s['on']==['1970'],json.dumps(s))
        pg.evaluate("""()=>{ const el=document.querySelector('#tlScroll'); el.dispatchEvent(new Event('touchstart',{bubbles:true})); el.scrollTop=el.scrollHeight; }"""); settle(pg); pg.wait_for_timeout(100); s=pg.evaluate(ST)
        ok(f'{lab}: after a manual scroll the scroll-spy follows the grid again',s['on']==[s['first']] and s['first']!='1970',json.dumps(s))
        tapchip(pg,'2000'); pg.wait_for_timeout(200)
        bar=pg.locator('.tlbar').bounding_box()
        ok(f'{lab}: solid Timeline bar below the status bar',bar['y']>=sat-1 and pg.evaluate("getComputedStyle(document.querySelector('.tlbar')).backgroundColor")=='rgb(0, 0, 0)',json.dumps(bar))
        if lab in ('ipad-portrait','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v41-timeline-{lab}.png')
        # built-in release list: used for unknowns, never over a manual date
        e=pg.evaluate("""(()=>{ const C=__cr.comics, u=C.find(c=>!c.dateManual), m=C.find(c=>c.dateManual); u.driveId='1hTTYDPO-sample'; m.driveId='1hTTYDPO-sample';
          __cr.dates.embed.d['1hTTYDPO-sample']=[1987,6]; const a=__cr.dates.of(u), b=__cr.dates.of(m); delete u.driveId; delete m.driveId; return {a,b,n:Object.keys(__cr.dates.embed.d).length}; })()""")
        ok(f'{lab}: built-in release list dates an unknown issue (src catalog) but never overrides a hand-set date',e['a']['src']=='catalog' and e['a']['y']==1987 and e['b']['src']=='manual' and e['n']>700,json.dumps(e))
        ctx.close()
    b.close()
print(f'\n{sum(res)}/{len(res)} passed'+(f'; page errors: {errors[:3]}' if errors else '')); sys.exit(0 if all(res) and not errors else 1)
