"""cr-v30/v31 suite: shelf of volumes on Home (v31: spine typography, full names, contrast).  python3 test/e2e_v30.py [webkit]  (server on 127.0.0.1:8823)
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
  const sp=[...s.querySelectorAll('.spine')].map(b=>{const q=r(b), cs=getComputedStyle(b); return {n:b.dataset.series,w:q.width,h:q.height,bg:cs.backgroundColor,ink:cs.color,wm:getComputedStyle(b.querySelector('.sp-t')).writingMode,ff:getComputedStyle(b.querySelector('.sp-t')).fontFamily,font:b.dataset.font,tw:b.querySelector('.sp-t').getBoundingClientRect().width,fs:parseFloat(getComputedStyle(b.querySelector('.sp-t')).fontSize),t:b.querySelector('.sp-t').textContent,m:(b.querySelector('.sp-m')||{}).textContent||'',cid:b.dataset.cid}});
  const ks=[...s.querySelectorAll('.spine')].map(r), gaps=ks.slice(1).map((q,k)=>+(q.left-ks[k].right).toFixed(1)); const nx=s.nextElementSibling; return {sp,gaps,h:r(s).height,gapTop:r(s).top-cf.bottom,next:nx&&(nx.classList.contains('otw')?'otw':nx.classList.contains('row')?'row':nx.className),over:sc.scrollWidth>sc.clientWidth+1,first:s===document.querySelector('#homeScroll .rows').firstElementChild,ox:document.documentElement.scrollWidth>innerWidth}})()"""
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
        pg.evaluate("document.fonts.ready"); fl=pg.evaluate("(async()=>{await document.fonts.ready; const F=__cr.vols.FONTS; const used=[...new Set([...document.querySelectorAll('.spine')].map(b=>b.dataset.font))]; await Promise.all(used.map(k=>document.fonts.load('14px \"'+F[k].f+'\"','ABC'))); return used.map(k=>[k,document.fonts.check('14px \"'+F[k].f+'\"','ABC')])})()")
        ok(f'{lab}: v31 bundled spine fonts load locally',fl and all(x[1] for x in fl),json.dumps(fl)); s=pg.evaluate(SP)
        ok(f'{lab}: v31 each spine title uses its series font; text fits the spine width; legible size',all(pg.evaluate(f"__cr.vols.FONTS['{x['font']}'].f") in x['ff'] for x in s['sp']) and all(x['tw']<=x['w']+.5 for x in s['sp']) and min(x['fs'] for x in s['sp'])>=11,json.dumps([(x['n'],x['font'],x['ff'][:30],x['tw'],x['w'],x['fs']) for x in s['sp']]))
        pg.wait_for_timeout(300); tr=pg.evaluate("[...document.querySelectorAll('.spine .sp-t')].map(t=>{const h=t.getBoundingClientRect().height; t.style.maxInlineSize='none'; const n=t.getBoundingClientRect().height; t.style.maxInlineSize=''; return [t.textContent,+h.toFixed(1),+n.toFixed(1),parseFloat(getComputedStyle(t).fontSize)]})")
        ok(f'{lab}: v34 titles shrink to fit instead of truncating',all(x[2]<=x[1]+1 or x[3]<=11 for x in tr),json.dumps(tr))
        groups=pg.evaluate("[...new Set(__cr.comics.map(c=>(c.series||'').trim()).filter(Boolean))].sort()")
        ok(f'{lab}: one spine per Library series/volume, directly under the carousel, above "This week in…"',s and sorted(x['n'] for x in s['sp'])==groups and s['first'] and s['next']=='otw',json.dumps([s and s['next'],groups,s and [x['n'] for x in s['sp']]]))
        ipad=w>=1000
        ok(f'{lab}: v34 bigger books ({"235-265" if ipad else "180-210"}px shelf: ~{"220" if ipad else "165"}px spines), no gap under the carousel, no page overflow',s['h']>=(235 if ipad else 180) and s['h']<=(265 if ipad else 210) and -1<=s['gapTop']<=10 and not s['ox'],json.dumps({k:s[k] for k in ('h','gapTop','ox')}))
        ok(f'{lab}: v34 spines 50-90px wide, vertical title text, 4-6px gaps',all(50<=x['w']<=90 for x in s['sp']) and all(x['wm'] in ('vertical-rl','tb-rl') for x in s['sp']) and all(4<=g<=6.5 for g in s['gaps']),json.dumps([(x['n'],x['w'],x['wm']) for x in s['sp']]+[s['gaps']]))
        cr=[pg.evaluate(f"__cr.vols.contrast({RGB}('{x['bg']}'),{RGB}('{x['ink']}'))") for x in s['sp']]
        ok(f'{lab}: v34 title contrast >=7:1 on every nearly-black spine body',min(cr)>=7,json.dumps(cr))
        if lab=='ipad-landscape':
            byn={x['n']:x for x in s['sp']}
            ok('thickness scales with issue count (5 issues wider than 2), 50-90px',byn['Iron Tide']['w']>byn['Twin Moon']['w'] and max(x['w'] for x in s['sp'])<=90 and min(x['w'] for x in s['sp'])>=50,json.dumps({k:v['w'] for k,v in byn.items()}))
            ok('v34: volume/years line only on spines >=60px (year range from Timeline dates)',all((x['m']=='')==(x['w']<60) or (x['w']>=60 and x['m']=='') for x in s['sp']) and all(x['m']=='' for x in s['sp'] if x['w']<60) and pg.evaluate("__cr.vols.info('Comet Run',__cr.comics.filter(c=>c.series==='Comet Run')).yr")=='1983–84' and byn['Comet Run']['w']<60,json.dumps([(x['n'],x['w'],x['m']) for x in s['sp']]))
            sweep=pg.evaluate("""(()=>{let worst=99,at=''; for(let r=0;r<256;r+=15)for(let g=0;g<256;g+=15)for(let b=0;b<256;b+=15){ const h='#'+[r,g,b].map(v=>v.toString(16).padStart(2,'0')).join(''), k=__cr.vols.inks(h), c=__cr.vols.contrast(__cr.vols.hexRGB(h),__cr.vols.hexRGB(k.ink)); if(c<worst){worst=c;at=h} } return {worst,at}})()""")
            ok('v31: ink passes WCAG 4.5:1 on every spine colour (4,913-colour sweep incl. all mid-tones)',sweep['worst']>=4.5,json.dumps(sweep))
            mid=pg.evaluate("['#777777','#7f7f7f','#808080','#8a6d5a','#5f7f9f','#b05a5a','#6a8f3f'].map(h=>{const k=__cr.vols.inks(h); return [h,k.ink,+__cr.vols.contrast(__cr.vols.hexRGB(h),__cr.vols.hexRGB(k.ink)).toFixed(2)]})")
            ok('v31: mid-tone spines get readable ink',all(x[2]>=4.5 for x in mid),json.dumps(mid))
            nm=pg.evaluate("['ASM','UXM','FF','X Men','asm vol 2','TMNT','ASM Annual','Iron Tide'].map(__cr.vols.name)")
            ok('v31: abbreviations expand to full names on spines',nm==['Amazing Spider-Man','Uncanny X-Men','Fantastic Four','X-Men','Amazing Spider-Man','Teenage Mutant Ninja Turtles','Amazing Spider-Man Annual','Iron Tide'],json.dumps(nm))
            st=pg.evaluate("['Amazing Spider-Man','Uncanny X-Men','Batman','The Walking Dead','Star Wars','Fantastic Four','Hellboy','The Sandman'].map(__cr.vols.style)")
            ok('v31: known series map to fitting styles (Spider-Man comic face, X-Men blocky italic, Batman/Hellboy/Sandman gothic serif, horror, sci-fi geometric, FF heavy retro)',st==['bangers','bungee','cinzel','creep','orb','lucky','cinzel','cinzel'],json.dumps(st))
            fb=pg.evaluate("['Glass Harbor','Atlas Omnibus','Quiet Engines','Lantern Bay','Hollow Pines','Velvet Rook'].map(__cr.vols.style).concat([__cr.vols.style('Velvet Rook')])")
            ok('v31: deterministic fallback style for unknown series',fb[-1]==fb[-2] and all(f in pg.evaluate("Object.keys(__cr.vols.FONTS)") for f in fb),json.dumps(fb))
            ok('v31: spines use varied styles (>=4 faces on this shelf)',len(set(x['font'] for x in s['sp']))>=4,json.dumps([x['font'] for x in s['sp']]))
            fr=pg.evaluate("Promise.all(['Bangers','Bungee','LuckiestGuy','BlackOpsOne','Creepster','CinzelDecorative','Orbitron','PermanentMarker'].map(f=>fetch('fonts/'+f+'.woff2').then(r=>[f,r.status,+r.headers.get('content-length')||0])))")
            ok('v31: font files bundled and small (<40KB each, subset)',all(x[1]==200 for x in fr) and all(0<x[2]<40000 for x in fr),json.dumps(fr))
            sw=pg.evaluate("fetch('sw.js').then(r=>r.text())"); ok('v31: service worker caches the fonts',all(f"fonts/{f}.woff2" in sw for f in ['Bangers','Bungee','LuckiestGuy','BlackOpsOne','Creepster','CinzelDecorative','Orbitron','PermanentMarker']))
            pg.evaluate("__cr.series.move(['Twin Moon'],'ASM')"); pg.wait_for_timeout(400); s2=pg.evaluate(SP); a=[x for x in s2['sp'] if x['n']=='ASM']
            libn=pg.evaluate("[...new Set(__cr.comics.map(c=>c.series))].includes('ASM')")
            ok('v31: "ASM" series shows "Amazing Spider-Man" on its spine, Library name unchanged, comic-style face',a and a[0]['t']=='Amazing Spider-Man' and a[0]['font']=='bangers' and libn,json.dumps(a))
            pg.evaluate("__cr.series.move(['ASM'],'Twin Moon')"); pg.wait_for_timeout(400)
            samp=pg.evaluate("""(async()=>{const c=__cr.comics.find(x=>x.title==='Iron Tide 01'); const b=document.querySelector('.spine[data-series="Iron Tide"]'); const again=await __cr.vols.dominant(c.cover instanceof Blob?c.cover:new Blob([c.cover]));
              const t=b.querySelector('.sp-t'), ru=b.querySelector('.sp-rule'), rr=ru.getBoundingClientRect(), br=b.getBoundingClientRect(), tr=t.getBoundingClientRect();
              return {c:c.spineC,again,body:c.spineB,acc:c.spineAcc,bodyExp:__cr.vols.bodyOf(c.spineC),inkExp:__cr.vols.titleInk(c.spineAcc,c.spineB),bg:getComputedStyle(b).backgroundColor,ink:getComputedStyle(t).color,ts:getComputedStyle(t).textShadow,
                rule:getComputedStyle(ru).backgroundColor,ruleTop:rr.top-br.top,ruleH:rr.height,art:!!b.querySelector('.sp-art'),stored:!!c.spineArt||!!c.spineCrop,fill:tr.width/br.width,meta:getComputedStyle(b.querySelector('.sp-m')||b).color,n:b.querySelector('.sp-n').textContent}})()""")
            hx=lambda h:[int(h[i:i+2],16) for i in (1,3,5)]
            ok('v34: nearly black body from the cover colour; title = near-white tint of the cover accent with a soft dark glow',samp['c']==samp['again'] and samp['body']==samp['bodyExp'] and pg.evaluate(f"{RGB}('{samp['bg']}')")==hx(samp['body']) and pg.evaluate(f"{RGB}('{samp['ink']}')")==hx(samp['inkExp']) and sum(hx(samp['body']))<70 and min(hx(samp['inkExp']))>=190 and '8px' in samp['ts'],json.dumps(samp))
            ok('v34: no cover-art panel (nothing cropped or stored); thin accent rule at the top; issue count at the foot',not samp['art'] and not samp['stored'] and pg.evaluate(f"{RGB}('{samp['rule']}')")==hx(samp['acc']) and samp['ruleTop']<=14 and samp['ruleH']<=3 and samp['n']=='5',json.dumps(samp))
            ok('v34: big titles fill most of the spine width',samp['fill']>=.38,json.dumps(samp))
            mc=[pg.evaluate(f"__cr.vols.contrast({RGB}('{x}'),{RGB}('{samp['bg']}'))") for x in (samp['meta'],)]
            ok('v34: subtitle (Vol/years) light grey, readable on the dark body',min(mc)>=4.5,json.dumps(mc))
            sw2=pg.evaluate("""(()=>{let worst=99,at=''; for(let r=0;r<256;r+=15)for(let g=0;g<256;g+=15)for(let b=0;b<256;b+=15){ const h='#'+[r,g,b].map(v=>v.toString(16).padStart(2,'0')).join(''), body=__cr.vols.bodyOf(h), a=__cr.vols.lift(h,body), t=__cr.vols.titleInk(a,body), c=__cr.vols.contrast(__cr.vols.hexRGB(t),__cr.vols.hexRGB(body)); if(c<worst){worst=c;at=h} } return {worst,at}})()""")
            ok('v34: title passes 7:1 on the body for every cover colour (4,913-colour sweep)',sw2['worst']>=7,json.dumps(sw2))
            hs=[x['h'] for x in s['sp']]; ok('v34: trade-like uniform heights (within 4px)',max(hs)-min(hs)<=4,json.dumps(hs))
            idb=pg.evaluate("new Promise(r=>{const q=indexedDB.open('comic-reader'); q.onsuccess=()=>{const t=q.result.transaction('comics').objectStore('comics').getAll(); t.onsuccess=()=>r(t.result.filter(c=>c.spineC&&c.spineAcc&&!c.spineArt).map(c=>c.title))}})")
            ok('colours and accent cached in IndexedDB (no art crop) (first issue of each volume)',len(idb)==len(groups),json.dumps(idb))
            pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(600)
            n=pg.evaluate("[...document.querySelectorAll('.spine')].filter(b=>!b.style.getPropertyValue('--sb').startsWith('#')||b.style.getPropertyValue('--sb')==='#111114').length")
            ok('after reload colours come from the cache (no resampling, applied on first paint)',n==0,n)
            pg.evaluate("__cr.series.move(['Ember Road'],'Ember Road Vol 2')"); pg.wait_for_timeout(400); s=pg.evaluate(SP)
            e=[x for x in s['sp'] if x['n']=='Ember Road Vol 2']
            ok('Move to Series choice regroups the shelf; volume number shown',e and 'Vol 2' in e[0]['m'] and e[0]['t']=='Ember Road' and not any(x['n']=='Ember Road' for x in s['sp']),json.dumps(e))
            pg.screenshot(path=f'{SH}/{ENG}-v34-home-{lab}.png'); bb=pg.locator('.volshelf').bounding_box(); pg.screenshot(path=f'{SH}/{ENG}-v34-spines-closeup-{lab}.png',clip={'x':0,'y':bb['y'],'width':min(w,700),'height':bb['height']+10})
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
        if lab!='ipad-landscape':
            pg.screenshot(path=f'{SH}/{ENG}-v34-home-{lab}.png'); bb=pg.locator('.volshelf').bounding_box(); pg.screenshot(path=f'{SH}/{ENG}-v34-spines-closeup-{lab}.png',clip={'x':0,'y':bb['y'],'width':min(w,700),'height':bb['height']+10})
        ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
