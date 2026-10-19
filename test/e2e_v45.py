"""cr-v45 suite: 'Also on sale this month' at the bottom of the end-of-issue / up-next page (after finishing an issue).
python3 test/e2e_v45.py [webkit] (server on 127.0.0.1:8823). Original test art; dates set in memory. Standalone insets via --sat/--sab."""
import sys, os, json, glob
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=sorted(glob.glob(os.path.join(T,'*.pdf')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
def wait_render(pg,t=15000): pg.wait_for_function('document.querySelectorAll(".view .pg.loading").length===0 && document.querySelectorAll(".view .pg canvas").length>0',timeout=t)
SEED="""()=>{ const C=__cr.comics.slice().sort((a,b)=>a.title.localeCompare(b.title)); C.forEach(c=>{ delete c.dateManual; c.metaDate=null; c.onlineDate=null; delete c.driveId; });
  const f=t=>C.find(c=>c.title===t), M=(c,y,m)=>c.dateManual={y,m};
  const A=f('Ember Road 01'), B=f('Iron Tide 03'), Cc=f('Nightfall 04'), K=f('Glass Harbor'), D=f('Twin Moon 01'), E=f('The Hollow 03'), F=f('Starlight Ronin v02'), G=f('Starlight Ronin v03'), I=f('Atlas Omnibus'), J=f('Twin Moon 02');
  M(A,1987,3); B.onlineDate={y:1987,m:3,src:'online',wiki:'Marvel Database',title:'x'}; M(Cc,1987,3); M(K,1987,3); M(D,1987,4); M(E,1990,0); M(F,1990,5); M(G,1990,11); M(I,2001,6);
  __cr.dates.render(); const id=c=>c.id; return {A:id(A),B:id(B),C:id(Cc),K:id(K),D:id(D),E:id(E),F:id(F),G:id(G),I:id(I),J:id(J),t:{A:A.title,K:K.title,E:E.title,I:I.title,J:J.title}}; }"""
EXP="""id=>{ const c=__cr.comics.find(x=>x.id===id), d=__cr.dates.of(c); if(!d) return null; return __cr.comics.filter(x=>x.id!==id).filter(x=>{ const e=__cr.dates.of(x); return e&&e.y===d.y&&(d.m?e.m===d.m:true); }).sort((a,b)=>(a.series||'').localeCompare(b.series||'')||__cr.issueNo(a.title)-__cr.issueNo(b.title)||a.title.localeCompare(b.title)).map(x=>x.id); }"""
def to_end(pg,title):
    pg.evaluate("t=>{ const el=document.querySelector('#reader'); if(!el.classList.contains('hidden')){ __cr.toggleUI(true); document.querySelector('#rBack').click(); } }",title); pg.wait_for_selector('#shelf:not(.hidden)')
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150); pg.locator(f'.lc[data-title="{title}"]').click(); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg)
    pg.evaluate('__cr.jumpTo(__cr.R.n)'); wait_render(pg); pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_function('__cr.R.saleHits!==null && !!document.querySelector(`.view .pg[data-p="${__cr.R.n}"] canvas`)',timeout=15000); pg.wait_for_timeout(350)
    return pg.evaluate("""(()=>{ const R=__cr.R, cv=document.querySelector(`.view .pg[data-p="${R.n}"] canvas`), r=cv.getBoundingClientRect();
      return {next:!!R.next,hits:(R.saleHits||[]).map(h=>({id:h.id||null,more:!!h.more,x:r.left+(h.x+h.w/2)*r.width,y:r.top+(h.y+h.h/2)*r.height,w:h.w*r.width,h:h.h*r.height}))}; })()""")
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crIdle=700; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        ok(f'{lab}: app launches on Home',pg.evaluate("!document.querySelector('#home').classList.contains('hidden')"))
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        x=pg.evaluate(SEED)
        pg.click('#tabs [data-tab=library]'); pg.evaluate("id=>{ __cr.credits.sheet(id); return 1 }",x['A']); pg.wait_for_timeout(250)
        ok(f'{lab}: no Also-on-sale button in the issue info sheet (placement moved to the end page)',pg.evaluate("!document.querySelector('.mwrap .salebtn,.salebtn')")); pg.click('.mwrap [data-r=cancel]'); pg.wait_for_timeout(150)
        ok(f'{lab}: Home unchanged',pg.evaluate("!document.querySelector('#home .salebtn')"))
        # up-next card (Ember Road 01 -> next Ember Road 02), Mar 1987: B (looked up), C, K (hand-set)
        e=to_end(pg,x['t']['A']); want=pg.evaluate(EXP,x['A'])
        ok(f'{lab}: up-next page ends with "Also on sale this month": the other Mar 1987 issues (hand-set + looked-up), not Apr, not itself',e['next'] and [z['id'] for z in e['hits']]==want and sorted(want)==sorted([x['B'],x['C'],x['K']]),json.dumps([e,want]))
        ok(f'{lab}: covers are >=40px tap targets',all(z['w']>=40 and z['h']>=40 for z in e['hits']),e['hits'])
        if lab in ('ipad-portrait','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v45-next-issue-{lab}.png')
        t=[z for z in e['hits'] if z['id']==x['C']][0]; pg.touchscreen.tap(t['x'],t['y']); pg.wait_for_function(f"__cr.R.comic&&__cr.R.comic.id==='{x['C']}'",timeout=8000); wait_render(pg)
        ok(f'{lab}: a cover opens that issue',pg.evaluate('__cr.R.comic.id')==x['C'] and pg.evaluate("location.hash").endswith(x['C']))
        # End page (no next issue): Glass Harbor (one-shot), also Mar 1987
        e=to_end(pg,x['t']['K']); want=pg.evaluate(EXP,x['K'])
        ok(f'{lab}: End page (no next issue) has the section too',not e['next'] and [z['id'] for z in e['hits']]==want and len(want)==3,json.dumps([e,want]))
        if lab=='iphone-390': pg.screenshot(path=f'{SH}/{ENG}-v45-end-page-{lab}.png')
        bk=pg.evaluate("""(()=>{ const R=__cr.R, cv=document.querySelector(`.view .pg[data-p="${R.n}"] canvas`), r=cv.getBoundingClientRect(), b=R.endBtn; return b?{x:r.left+(b.x+b.w/2)*r.width,y:r.top+(b.y+b.h/2)*r.height}:null })()""")
        lowest=min(z['y']-z['h']/2 for z in e['hits'])
        ok(f'{lab}: Back to Library button stays above the section',bk and bk['y']<lowest,json.dumps([bk,lowest]))
        # year-only date: around 1990 -> F, G
        e=to_end(pg,x['t']['E']); ok(f'{lab}: year-only date: the whole year ("around 1990")',sorted(z['id'] for z in e['hits'])==sorted([x['F'],x['G']]),json.dumps(e))
        # nothing else that month / no date: section hidden
        e=to_end(pg,x['t']['I']); ok(f'{lab}: no other issue that month -> no section',e['hits']==[],json.dumps(e))
        e=to_end(pg,x['t']['J']); ok(f'{lab}: no usable date -> no section',e['hits']==[],json.dumps(e))
        # many matches -> "+N more" opens the full grid page; back returns to the reader
        n=pg.evaluate("""id=>{ const C=__cr.comics.filter(c=>c.id!==id&&!c.dateManual&&!c.onlineDate); C.slice(0,14).forEach(c=>c.dateManual={y:1987,m:3}); return C.slice(0,14).length }""",x['A'])
        e=to_end(pg,x['t']['K']); mo=[z for z in e['hits'] if z['more']]
        ok(f'{lab}: more than fit -> "+N more" tile',len(mo)==1 and len(e['hits'])>=3,json.dumps(e))
        pg.touchscreen.tap(mo[0]['x'],mo[0]['y']); pg.wait_for_timeout(600)
        g=pg.evaluate("({vis:!document.querySelector('#creator').classList.contains('hidden'),n:document.querySelectorAll('#crBody .crc').length,t:document.querySelector('#crName').textContent})")
        ok(f'{lab}: "+N more" opens the full grid of that month',g['vis'] and g['n']==3+n and g['t']=='Also on sale · Mar 1987',json.dumps(g))
        pg.click('#crClose'); pg.wait_for_timeout(200); ok(f'{lab}: back returns to the reader',pg.is_visible('#reader') and pg.evaluate('__cr.R.comic.id')==x['K'])
        ctx.close()
    b.close()
print(f'\n{sum(res)}/{len(res)} passed'+(f'; page errors: {errors[:3]}' if errors else '')); sys.exit(0 if all(res) and not errors else 1)
