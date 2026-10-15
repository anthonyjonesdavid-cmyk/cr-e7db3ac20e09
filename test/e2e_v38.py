"""cr-v38 suite: Recent tab (4th segment) + removed Home rows ('This week in…' and 'Recently Added').
python3 test/e2e_v38.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: original abstract comics (test/gen_pdfs.py, test/gen_dates.py). Standalone insets via --sat/--sab. Replaces the v28 'This week in…' suite."""
import sys, os, json, subprocess, glob
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); D=os.path.join(T,'dates'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(os.path.join(D,'Deep_Signal_02.pdf')): subprocess.run([sys.executable,os.path.join(HERE,'gen_dates.py')],check=True)
FILES=sorted(glob.glob(os.path.join(T,'*.pdf')))+sorted(glob.glob(os.path.join(D,'*.pdf')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
TABS="""(()=>{const r=e=>e.getBoundingClientRect(); const tb=[...document.querySelectorAll('#tabs button')]; const q=tb.map(r);
  const row=document.querySelector('.topbar .tb-row'), other=[...row.querySelectorAll('.icbtn,.txtbtn,button')].filter(b=>!b.closest('#tabs')&&b.offsetParent&&getComputedStyle(b).visibility!=='hidden').map(r).filter(x=>x.width>0);
  const lbl=tb.map(b=>[...b.childNodes].filter(n=>n.nodeType===3||(n.offsetParent!==null&&getComputedStyle(n).display!=='none')).map(n=>n.textContent).join('').trim());
  return {n:tb.length,keys:tb.map(b=>b.dataset.tab),lbl,minH:Math.min(...q.map(x=>x.height)),minW:Math.min(...q.map(x=>x.width)),inView:q.every(x=>x.left>=0&&x.right<=innerWidth),
    clip:tb.some(b=>b.scrollWidth>b.clientWidth+1),clash:other.some(o=>q.some(x=>o.left<x.right-1&&o.right>x.left+1&&o.top<x.bottom&&o.bottom>x.top)),top:r(document.querySelector('#tabs')).top,
    tb:getComputedStyle(document.querySelector('.topbar')).backgroundColor,ov:document.documentElement.scrollWidth>innerWidth}})()"""
REC="""(()=>{const g=document.querySelector('#recGrid'), cs=[...g.querySelectorAll('.lc')], exp=__cr.comics.slice().sort((a,b)=>b.added-a.added).map(c=>c.id), r=cs[0]&&cs[0].getBoundingClientRect();
  return {vis:!document.querySelector('#recent').classList.contains('hidden'),n:cs.length,total:__cr.comics.length,order:JSON.stringify(cs.map(e=>e.dataset.id))===JSON.stringify(exp),
    cols:getComputedStyle(g).gridTemplateColumns.split(' ').length,w:r&&r.width,h:r&&r.height,top:r&&r.top}})()"""
CFW="""(()=>{const C=__cr.CF,n=C.items.length,i=((Math.round(C.pos)%n)+n)%n,vis=[...document.querySelectorAll('#cf .cf-item')].filter(e=>e.style.display!=='none'),r=e=>e.getBoundingClientRect(),mid=innerWidth/2;
  const L=vis.filter(e=>r(e).right<mid-10), R=vis.filter(e=>r(e).left>mid+10), ctr=vis.find(e=>Math.abs(r(e).left+r(e).width/2-mid)<4);
  return {n,pos:C.pos,i,left:L.length,right:R.length,minL:Math.min(...vis.map(e=>r(e).left)),maxR:Math.max(...vis.map(e=>r(e).right)),vw:innerWidth,ctr:ctr&&+ctr.dataset.i,
    leftNearest:L.length?+L.sort((a,b)=>r(b).right-r(a).right)[0].dataset.i:null}})()"""
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crNow=new Date('2026-06-12T12:00:00').getTime(); document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        # a dated issue exactly "this week" in a past year: the old row would have shown it
        pg.evaluate("(()=>{const c=__cr.comics.find(x=>x.title.startsWith('Comet Run 01')); if(c){ c.onlineDate={y:1983,m:6,d:12,src:'online'}; } __cr.dates.render()})()")
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(400)
        hm=pg.evaluate("(()=>({otw:document.querySelectorAll('#homeScroll .otw').length,heads:[...document.querySelectorAll('#homeScroll .row-h h2')].map(e=>e.textContent),added:document.querySelectorAll('#homeScroll [data-kind=added]').length,txt:document.querySelector('#homeScroll').textContent}))()")
        ok(f'{lab}: Home has no "This week in…/On sale this month" row and no "Recently Added" row',hm['otw']==0 and hm['added']==0 and 'Recently Added' not in hm['heads'] and 'past years' not in hm['txt'] and len(hm['heads'])>0,json.dumps(hm['heads']))
        pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(700); c=pg.evaluate(CFW)
        ok(f'{lab}: v38 Home carousel filled edge to edge on first load (circular: last items to the left of the first)',c['pos']==0 and c['ctr']==0 and c['left']>=2 and c['right']>=2 and c['minL']<=0 and c['maxR']>=c['vw'] and c['leftNearest']==c['n']-1,json.dumps(c))
        pg.screenshot(path=f'{SH}/{ENG}-v38-home-carousel-{lab}.png')
        pg.evaluate('__cr.CF.to(-3,200)'); pg.wait_for_timeout(500); c2=pg.evaluate(CFW)
        ok(f'{lab}: flicking past the start keeps cycling (lands on item n-3, both sides still full)',c2['i']==c2['n']-3 and 0<=c2['pos']<c2['n'] and c2['left']>=2 and c2['right']>=2,json.dumps(c2))
        pg.evaluate('__cr.CF.to(0,10)'); pg.wait_for_timeout(200)
        t=pg.evaluate(TABS); wide=w>=700
        ok(f'{lab}: switcher reads Home | Library | Timeline | {"Recently Added" if wide else "Recent"}',t['n']==4 and t['keys']==['home','library','timeline','recent'] and t['lbl']==['Home','Library','Timeline','Recently Added' if wide else 'Recent'],json.dumps(t))
        ok(f'{lab}: compact switcher: all 4 tap targets >=40px, in view, no clipping, no clash with bar buttons, nothing under the status bar',t['minH']>=40 and t['minW']>=40 and t['inView'] and not t['clip'] and not t['clash'] and t['top']>=sat and t['tb']=='rgb(0, 0, 0)' and not t['ov'],json.dumps(t))
        t0=pg.evaluate('performance.now()'); pg.click('#tabs [data-tab=recent]'); pg.wait_for_timeout(250); r=pg.evaluate(REC)
        ok(f'{lab}: Recent tab = every comic, newest first, compact grid ({r["cols"]} cols), tiles >=40px',r['vis'] and r['n']==r['total']==len(FILES) and r['order'] and r['cols']>=(4 if w<600 else 7) and r['w']>=40 and r['h']>=40 and r['top']>=sat,json.dumps(r))
        pg.screenshot(path=f'{SH}/{ENG}-v38-recent-{lab}.png')
        sc=pg.evaluate("(()=>{const s=document.querySelector('#recScroll'); s.scrollTop=Math.min(240,s.scrollHeight-s.clientHeight); return {top:s.scrollTop,can:s.scrollHeight>s.clientHeight}})()"); pg.wait_for_timeout(150)
        tgt=pg.evaluate("(()=>{const s=document.querySelector('#recScroll').getBoundingClientRect(); const e=[...document.querySelectorAll('#recGrid .lc')].find(x=>{const r=x.getBoundingClientRect(); return r.top>=s.top&&r.bottom<=s.bottom}); return e&&{id:e.dataset.id,title:e.dataset.title}})()")
        pg.click(f'#recGrid .lc[data-id="{tgt["id"]}"]'); pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(300)
        ok(f'{lab}: tapping a Recent tile opens that issue',pg.evaluate('__cr.R.comic.id')==tgt['id'],json.dumps(tgt))
        pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
        st=pg.evaluate("({tab:document.querySelector('#tabs .on').dataset.tab,top:document.querySelector('#recScroll').scrollTop})")
        ok(f'{lab}: closing the reader returns to the Recent tab at the same scroll position',st['tab']=='recent' and abs(st['top']-sc['top'])<=2,json.dumps([sc,st]))
        pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150); pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(150); pg.click('#tabs [data-tab=recent]'); pg.wait_for_timeout(200)
        ok(f'{lab}: Recent remembers its scroll position across tab switches',abs(pg.evaluate("document.querySelector('#recScroll').scrollTop")-sc['top'])<=2 and (sc['can'] or w>=1000 or sc['top']==0),json.dumps(sc))
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0"); pg.wait_for_timeout(200)
        pg.screenshot(path=f'{SH}/{ENG}-v38-home-{lab}.png')
        if lab=='ipad-landscape':
            # perf: a 980-issue list renders quickly (synthetic records, reusing one cover)
            perf=pg.evaluate("""(async()=>{ const base=__cr.comics[0], keep=__cr.comics.slice(); for(let i=0;i<980-keep.length;i++) __cr.comics.push({...base,id:'syn'+i,title:'Syn '+i,added:base.added-1000-i});
              document.querySelector('#tabs [data-tab=home]').click(); const t0=performance.now(); document.querySelector('#tabs [data-tab=recent]').click(); const t1=performance.now(); await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
              const n=document.querySelectorAll('#recGrid .lc').length, t2=performance.now(); __cr.comics.splice(0,__cr.comics.length,...keep); document.querySelector('#tabs [data-tab=home]').click(); return {n,ms:Math.round(t1-t0),paint:Math.round(t2-t0)}})()""")
            ok('980-issue Recent tab renders in well under a second',perf['n']==980 and perf['paint']<1000,json.dumps(perf))
        ctx.close()
    # very few comics: the list repeats so both sides stay full
    ctx=b.new_context(viewport={'width':1024,'height':1366},has_touch=True,device_scale_factor=2); pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
    pg.goto(URL); pg.wait_for_selector('html[data-ready]'); two=FILES[:2]; pg.set_input_files('#fileIn',two); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==2 && !document.querySelector(".toast .tb")',timeout=60000)
    pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(500); c=pg.evaluate(CFW)
    ok('2 comics: carousel repeats them so both sides of the centre are filled',c['n']==2 and c['left']>=2 and c['right']>=2 and c['minL']<=0 and c['maxR']>=c['vw'],json.dumps(c))
    pg.screenshot(path=f'{SH}/{ENG}-v38-home-carousel-2-comics.png'); ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
