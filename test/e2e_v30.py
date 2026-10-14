"""cr-v30 suite: shelf of volumes on Home.  python3 test/e2e_v30.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: original abstract comics from test/gen_pdfs.py + test/gen_dates.py. Standalone insets via --sat/--sab."""
import sys, os, json, glob
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=sorted(glob.glob(T+'/Iron_Tide_0*.pdf')+glob.glob(T+'/Ember_Road_0*.pdf')+glob.glob(T+'/Nightfall_0*.pdf')+glob.glob(T+'/The_Hollow_0*.pdf')+glob.glob(T+'/Twin_Moon_0*.pdf')+glob.glob(T+'/Starlight_Ronin_v0*.pdf')+glob.glob(T+'/dates/*.pdf'))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
SP="""(()=>{const s=document.querySelector('#homeScroll .volshelf'); if(!s) return null; const sc=s.querySelector('.vs-s'), r=e=>e.getBoundingClientRect(), cf=r(document.querySelector('#homeScroll .hero'));
  const sp=[...s.querySelectorAll('.spine')].map(b=>{const q=r(b), cs=getComputedStyle(b); return {n:b.dataset.series,w:q.width,h:q.height,bg:cs.backgroundColor,ink:cs.color,wm:getComputedStyle(b.querySelector('.sp-t')).writingMode,t:b.querySelector('.sp-t').textContent,m:(b.querySelector('.sp-m')||{}).textContent||'',cid:b.dataset.cid}});
  const nx=s.nextElementSibling; return {sp,h:r(s).height,gapTop:r(s).top-cf.bottom,next:nx&&(nx.classList.contains('otw')?'otw':nx.classList.contains('row')?'row':nx.className),over:sc.scrollWidth>sc.clientWidth+1,first:s===document.querySelector('#homeScroll .rows').firstElementChild,ox:document.documentElement.scrollWidth>innerWidth}})()"""
RGB="(s=>s.match(/\\d+/g).slice(0,3).map(Number))"
def wait_cols(pg): pg.wait_for_function("__cr.comics.filter(c=>c.series).every(c=>true) && [...document.querySelectorAll('#homeScroll .spine')].every(b=>{const c=__cr.comics.find(x=>x.id===b.dataset.cid); return c&&c.spineV})",timeout=30000); pg.wait_for_timeout(200)
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crNow=new Date('2026-06-10T12:00:00').getTime(); document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=180000)
        pg.click('#tabs [data-tab=home]'); wait_cols(pg); s=pg.evaluate(SP)
        groups=pg.evaluate("[...new Set(__cr.comics.map(c=>(c.series||'').trim()).filter(Boolean))].sort()")
        ok(f'{lab}: one spine per Library series/volume, directly under the carousel, above "This week in…"',s and sorted(x['n'] for x in s['sp'])==groups and s['first'] and s['next']=='otw',json.dumps([s and s['next'],groups,s and [x['n'] for x in s['sp']]]))
        ipad=w>=1000
        ok(f'{lab}: compact height ({"170-200" if ipad else "130-170"}px), no gap under the carousel, no page overflow',s['h']>=(170 if ipad else 130) and s['h']<=(200 if ipad else 170) and -1<=s['gapTop']<=10 and not s['ox'],json.dumps({k:s[k] for k in ('h','gapTop','ox')}))
        ok(f'{lab}: spines >=40px wide, vertical title text',all(x['w']>=40 for x in s['sp']) and all(x['wm'] in ('vertical-rl','tb-rl') for x in s['sp']),json.dumps([(x['n'],x['w'],x['wm']) for x in s['sp']]))
        cr=[pg.evaluate(f"__cr.vols.contrast({RGB}('{x['bg']}'),{RGB}('{x['ink']}'))") for x in s['sp']]
        ok(f'{lab}: spine text contrast >=4.5:1 on every sampled colour',min(cr)>=4.5,json.dumps(cr))
        if lab=='ipad-landscape':
            byn={x['n']:x for x in s['sp']}
            ok('thickness scales modestly with issue count (5 issues wider than 2, capped)',byn['Iron Tide']['w']>byn['Twin Moon']['w'] and max(x['w'] for x in s['sp'])<=76,json.dumps({k:v['w'] for k,v in byn.items()}))
            ok('year range from Timeline dates on the spine',any(x['n']=='Comet Run' and '1983–84' in x['m'] for x in s['sp']),json.dumps([(x['n'],x['m']) for x in s['sp']]))
            samp=pg.evaluate("""(async()=>{const c=__cr.comics.find(x=>x.title==='Iron Tide 01'); const b=document.querySelector('.spine[data-series="Iron Tide"]'); const again=await __cr.vols.dominant(c.cover instanceof Blob?c.cover:new Blob([c.cover]));
              return {c:c.spineC,v:c.spineV,again,bg:getComputedStyle(b).backgroundColor}})()""")
            ok('spine colour = dominant colour of the first cover, applied to the spine',samp['c']==samp['again'] and pg.evaluate(f"{RGB}('{samp['bg']}')")==[int(samp['c'][i:i+2],16) for i in (1,3,5)],json.dumps(samp))
            idb=pg.evaluate("new Promise(r=>{const q=indexedDB.open('comic-reader'); q.onsuccess=()=>{const t=q.result.transaction('comics').objectStore('comics').getAll(); t.onsuccess=()=>r(t.result.filter(c=>c.spineC).map(c=>c.title))}})")
            ok('sampled colours cached in IndexedDB (first issue of each volume)',len(idb)==len(groups),json.dumps(idb))
            pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(600)
            n=pg.evaluate("[...document.querySelectorAll('.spine')].filter(b=>!b.style.getPropertyValue('--sc').startsWith('#')).length")
            ok('after reload colours come from the cache (no resampling, applied on first paint)',n==0,n)
            pg.evaluate("__cr.series.move(['Ember Road'],'Ember Road Vol 2')"); pg.wait_for_timeout(400); s=pg.evaluate(SP)
            e=[x for x in s['sp'] if x['n']=='Ember Road Vol 2']
            ok('Move to Series choice regroups the shelf; volume number shown',e and 'Vol 2' in e[0]['m'] and e[0]['t']=='Ember Road' and not any(x['n']=='Ember Road' for x in s['sp']),json.dumps(e))
            pg.screenshot(path=f'{SH}/{ENG}-v30-home-{lab}.png')
            t=pg.evaluate("""(async()=>{const b=document.querySelector('.spine[data-series="Nightfall"]'); b.click(); await new Promise(r=>setTimeout(r,90)); const mid=getComputedStyle(b).transform; return {mid,cls:b.classList.contains('out')}})()""")
            pg.wait_for_timeout(400); lib=pg.evaluate("({vis:!document.querySelector('#library').classList.contains('hidden'),tab:document.querySelector('#tabs .on').dataset.tab,titles:[...document.querySelectorAll('#libGrid .lc')].map(e=>e.dataset.title)})")
            ok('tap a spine: it slides out, then the series issue view opens',t['cls'] and t['mid']!='none' and lib['vis'] and lib['titles'] and all(x.startswith('Nightfall') for x in lib['titles']),json.dumps([t,lib]))
            pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
            pg.emulate_media(reduced_motion='reduce'); pg.wait_for_timeout(100)
            t=pg.evaluate("""(()=>{const b=document.querySelector('.spine[data-series="Iron Tide"]'); b.click(); return {out:b.classList.contains('out'),lib:!document.querySelector('#library').classList.contains('hidden')}})()""")
            ok('reduced motion: no slide, opens immediately',not t['out'] and t['lib'],json.dumps(t)); pg.emulate_media(reduced_motion='no-preference'); pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
        if s['over']:
            pg.evaluate("document.querySelector('.vs-s').scrollLeft=0"); bb=pg.locator('.vs-s').bounding_box(); y=bb['y']+bb['height']/2
            pg.mouse.move(bb['x']+bb['width']*.8,y); pg.mouse.wheel(400,0); pg.wait_for_timeout(500)
            ok(f'{lab}: overflowing shelf scrolls horizontally',pg.evaluate("document.querySelector('.vs-s').scrollLeft")>50 and pg.evaluate("getComputedStyle(document.querySelector('.vs-s')).overflowX")=='auto')
            pg.evaluate("document.querySelector('.vs-s').scrollLeft=0")
        g=pg.evaluate("(()=>({tb:getComputedStyle(document.querySelector('.topbar')).backgroundColor,top:document.querySelector('#tabs').getBoundingClientRect().top}))()")
        ok(f'{lab}: solid top bar, nothing under the status bar',g['tb']=='rgb(0, 0, 0)' and g['top']>=sat,json.dumps(g))
        if lab!='ipad-landscape': pg.screenshot(path=f'{SH}/{ENG}-v30-home-{lab}.png')
        ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
