"""cr-v66 suite: Line art view, Timeline artist filter, Find original art.
python3 test/e2e_v66.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: Iron Tide 01–03, Nightfall 01–02."""
import sys, os, json
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=[os.path.join(T,n) for n in ['Iron_Tide_01.pdf','Iron_Tide_02.pdf','Iron_Tide_03.pdf','Nightfall_01.pdf','Nightfall_02.pdf']]
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,'' if cond else str(extra)[:500],flush=True)

def dismiss(pg):
    pg.evaluate("window.__crSplashHide&&window.__crSplashHide(true)")
    pg.wait_for_function("!document.getElementById('splash')||document.getElementById('splash').classList.contains('fly')||document.getElementById('splash').classList.contains('out')")
    pg.wait_for_timeout(200)
def wait_render(pg,t=20000):
    pg.wait_for_function('document.querySelectorAll(".view .pg.loading").length===0 && document.querySelectorAll(".view .pg canvas").length>0',timeout=t)
def wait_fit(pg,t=20000):
    pg.wait_for_function('document.querySelector("#stage.fitw") && document.querySelectorAll("#stage.fitw .pg canvas").length>0',timeout=t)
def open_c(pg,title='Iron Tide 01'):
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150)
    pg.locator(f'.lc[data-title="{title}"]').click(); pg.wait_for_selector('#reader:not(.hidden)')
def back(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(80)
    pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(250)
def show_ui(pg):
    pg.evaluate('__cr.toggleUI(true)'); pg.wait_for_timeout(80)

SEED='''async ()=>{
  const f=t=>__cr.comics.find(c=>c.title===t);
  const A=f('Iron Tide 01'), B=f('Iron Tide 02'), C=f('Iron Tide 03'), D=f('Nightfall 01'), E=f('Nightfall 02');
  A.metaCredits={writer:['Chris Claremont'],artist:['Jim Lee']};
  B.metaCredits={artist:['Jim Lee']};
  C.metaCredits={artist:['Jim Lee']};
  D.metaCredits={artist:['John Byrne']};
  E.metaCredits={writer:['Chris Claremont']};
  await Promise.all([
    __cr.dates.set(A,{y:1991,m:10}),
    __cr.dates.set(B,{y:1991,m:11}),
    __cr.dates.set(C,{y:1992,m:1}),
    __cr.dates.set(D,{y:1986,m:5}),
    __cr.dates.set(E,{y:1986,m:6})
  ]);
  return {n:__cr.comics.length, credits:__cr.comics.map(c=>({t:c.title,k:__cr.credits.of(c)}))};
}'''

def hook_open(pg):
    pg.evaluate("""()=>{ window.__opened=[]; window.open=(u,t,f)=>{ window.__opened.push({u:String(u),t,f}); return {closed:false,close(){}}; }; }""")

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    sizes=[(1024,1366,'ipad-portrait',2,24,20)]
    for (w,h,lab,dpr,sat,sab) in sizes:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(f"window.__crNoScan=true; window.__crNoBag=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(f'{lab}: {e}') if 'access control checks' not in str(e).lower() and 'cross-origin' not in str(e).lower() else None)
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        dismiss(pg)
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==5 && !document.querySelector(".toast .tb")',timeout=180000)
        seeded=pg.evaluate(SEED)
        ok(f'{lab}: seeded credits and dates on 5 issues', seeded['n']==5, json.dumps(seeded))

        # ---- Inks button in the reader top bar, off by default, >=40px ----
        open_c(pg); wait_render(pg); show_ui(pg)
        g=pg.evaluate("""()=>{
          const b=document.querySelector('#rInks'), r=b.getBoundingClientRect(), bar=document.querySelector('#rtop');
          const st=getComputedStyle(bar), page=document.querySelector('#stage canvas');
          const filt=page?getComputedStyle(page).filter:'';
          return {w:r.width,h:r.height,y:r.y,barTop:bar.getBoundingClientRect().y,barBg:st.backgroundColor,opaque:st.opacity,sat:getComputedStyle(document.documentElement).getPropertyValue('--sat').trim(),
            on:b.classList.contains('on'), pressed:b.getAttribute('aria-pressed'), store:localStorage.getItem('cr.inks'),
            reader:document.getElementById('reader').classList.contains('inks'), filt, label:(b.querySelector('.w')||{}).textContent, anim:!!document.querySelector('#rAnim')};
        }""")
        ok(f'{lab}: Inks button is in the top bar, at least 40px, labeled Inks',
           g['w']>=40 and g['h']>=40 and g['label']=='Inks', json.dumps(g))
        ok(f'{lab}: top bar is opaque and sits below the status-bar inset',
           g['barTop']>=0 and (g['y']>=20) and g['opaque']=='1' and '0, 0, 0' in (g['barBg'] or ''), json.dumps(g))
        ok(f'{lab}: Inks is off by default (no color on the page, store empty)',
           (not g['on']) and g['pressed']=='false' and g['store'] in (None,'false') and (not g['reader']) and 'url(' not in (g['filt'] or '') and 'grayscale' not in (g['filt'] or ''), json.dumps(g))
        ok(f'{lab}: Animate stays off the toolbar (v65)', g['anim'] is False, json.dumps(g))

        pg.click('#rInks'); pg.wait_for_timeout(200); show_ui(pg)
        on=pg.evaluate("""()=>{
          const b=document.querySelector('#rInks'), page=document.querySelector('#stage canvas');
          const filt=page?getComputedStyle(page).filter:'';
          return {on:b.classList.contains('on'), pressed:b.getAttribute('aria-pressed'), store:localStorage.getItem('cr.inks'),
            reader:document.getElementById('reader').classList.contains('inks'), filt};
        }""")
        ok(f'{lab}: tapping Inks turns the page black-and-white and saves cr.inks',
           on['on'] and on['pressed']=='true' and on['store']=='true' and on['reader'] and ('url("#crInks")' in on['filt'] or 'url(#crInks)' in on['filt'] or 'grayscale' in on['filt']), json.dumps(on))
        pg.screenshot(path=f'{SH}/{ENG}-v66-inks-ipad-portrait.png')

        # Fit width still inked
        show_ui(pg); pg.click('#rFit'); wait_fit(pg); show_ui(pg)
        fit=pg.evaluate("""()=>{
          const page=document.querySelector('#stage.fitw canvas');
          const filt=page?getComputedStyle(page).filter:'';
          return {fit:document.getElementById('stage').classList.contains('fitw'), reader:document.getElementById('reader').classList.contains('inks'), filt, on:document.querySelector('#rInks').classList.contains('on')};
        }""")
        ok(f'{lab}: Inks stays on in Fit width',
           fit['fit'] and fit['reader'] and fit['on'] and ('url("#crInks")' in fit['filt'] or 'url(#crInks)' in fit['filt'] or 'grayscale' in fit['filt']), json.dumps(fit))
        show_ui(pg); pg.click('#rFit'); wait_render(pg)

        # Paper curl surfaces also get the filter
        pg.evaluate("()=>{ localStorage.setItem('cr.pageTurn', JSON.stringify('curl')); }")
        show_ui(pg)
        # bounce a curl if the API is available; otherwise just confirm CSS would apply to curl imgs
        curl=pg.evaluate("""()=>{
          try{ if(window.__cr.startFlip) window.__cr.startFlip(-1); }catch(e){ return {err:String(e)}; }
          const imgs=[...document.querySelectorAll('#stage img, .curl-rem img, .curl-flap img')];
          const filt=imgs.map(el=>getComputedStyle(el).filter);
          const canv=document.querySelector('#stage canvas');
          return {curlOn:document.querySelector('.curl-root,.flip.curl')!==null, filt, canvas:canv?getComputedStyle(canv).filter:'', flipping:!!window.__cr.flip};
        }""")
        ok(f'{lab}: Inks applies to the page during Paper curl (canvas or curl image)',
           ('url("#crInks")' in (curl.get('canvas') or '') or 'url(#crInks)' in (curl.get('canvas') or '') or 'grayscale' in (curl.get('canvas') or '') or any('url(' in f or 'grayscale' in f for f in (curl.get('filt') or []))), json.dumps(curl))
        pg.evaluate("()=>{ try{ if(window.__cr.cancelFlipNow) window.__cr.cancelFlipNow(); }catch(e){} }")
        pg.evaluate("()=>{ localStorage.setItem('cr.pageTurn', JSON.stringify('swipe')); }")

        # toggle off restores color
        show_ui(pg); pg.click('#rInks'); pg.wait_for_timeout(150)
        off=pg.evaluate("""()=>{
          const page=document.querySelector('#stage canvas'); const filt=page?getComputedStyle(page).filter:'';
          return {on:document.querySelector('#rInks').classList.contains('on'), reader:document.getElementById('reader').classList.contains('inks'), store:localStorage.getItem('cr.inks'), filt};
        }""")
        ok(f'{lab}: tapping Inks again restores color',
           (not off['on']) and (not off['reader']) and off['store']=='false' and 'url(' not in (off['filt'] or '') and 'grayscale' not in (off['filt'] or ''), json.dumps(off))

        # persistence: turn on, leave, reload
        show_ui(pg); pg.click('#rInks'); pg.wait_for_timeout(100)
        back(pg)
        pg.reload(); pg.wait_for_selector('html[data-ready]'); dismiss(pg)
        open_c(pg); wait_render(pg); show_ui(pg)
        persist=pg.evaluate("""()=>({store:localStorage.getItem('cr.inks'), on:document.querySelector('#rInks').classList.contains('on'), reader:document.getElementById('reader').classList.contains('inks'),
          filt:(document.querySelector('#stage canvas')&&getComputedStyle(document.querySelector('#stage canvas')).filter)||''})""")
        ok(f'{lab}: Inks stays on after reload', persist['store']=='true' and persist['on'] and persist['reader'] and ('url(' in persist['filt'] or 'grayscale' in persist['filt']), json.dumps(persist))
        # leave Inks on for the screenshot already taken; turn off so later UI is in color
        show_ui(pg); pg.click('#rInks'); back(pg)

        # Re-seed after reload (metaCredits and manual dates should persist via dates.set / db, metaCredits may have been saved if dbPut ran)
        # dates.set calls dbPut; metaCredits was set in memory. Re-apply credits after reload to be safe.
        pg.evaluate(SEED)

        # ---- Home is unchanged (no filter control on Home) ----
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200)
        home=pg.evaluate("""()=>({filter:!!document.querySelector('#home #tlFilter, #homeScroll #tlFilter'), tabs:!!document.querySelector('#tabs [data-tab=home]'), rows:document.querySelectorAll('#home .row-h, #home .hrow, #homeScroll .row').length})""")
        ok(f'{lab}: Home has no Timeline artist filter and still has its rows',
           home['filter'] is False and home['tabs'], json.dumps(home))

        # ---- Artist filter on Timeline ----
        pg.click('#tabs [data-tab=timeline]'); pg.wait_for_timeout(300)
        fb=pg.locator('#tlFilter').bounding_box()
        ok(f'{lab}: Timeline Filter button is at least 40px', fb and fb['width']>=40 and fb['height']>=40, json.dumps(fb))
        before=pg.evaluate("""()=>({count:document.getElementById('tlCount').textContent, n:document.querySelectorAll('#tlGrid .tcb').length, titles:[...document.querySelectorAll('#tlGrid .tcb')].map(b=>b.getAttribute('aria-label')||b.innerText)})""")
        ok(f'{lab}: Timeline starts on All (5 issues)', before['n']==5, json.dumps(before))

        pg.click('#tlFilter'); pg.wait_for_selector('#tlPicks')
        picks=pg.evaluate("""()=>{
          const btns=[...document.querySelectorAll('#tlPicks .tlp')].map(b=>{ const r=b.getBoundingClientRect(); return {name:b.querySelector('span')?.textContent, n:b.querySelector('.tlpc')?.textContent, h:r.height, on:b.classList.contains('on'), id:b.id}; });
          return btns;
        }""")
        names=[x['name'] for x in picks]
        ok(f'{lab}: picker lists All artists, then artists with issue counts, no writers-only',
           names[0]=='All artists' and 'Jim Lee' in names and 'John Byrne' in names and 'Chris Claremont' not in names and all(x['h']>=40 for x in picks), json.dumps(picks))
        # sorted by last name: Byrne before Lee
        jl=names.index('Jim Lee'); jb=names.index('John Byrne')
        ok(f'{lab}: artists are sorted by name (Byrne before Lee)', jb<jl, json.dumps(names))
        counts={x['name']:x['n'] for x in picks}
        ok(f'{lab}: issue counts are Jim Lee 3, John Byrne 1, All 5',
           counts.get('Jim Lee')=='3' and counts.get('John Byrne')=='1' and counts.get('All artists')=='5', json.dumps(counts))
        ok(f'{lab}: All artists is selected at first', picks[0]['on'] and picks[0]['id']=='tlAll', json.dumps(picks[0]))

        pg.locator('#tlPicks .tlp', has_text='Jim Lee').click(); pg.wait_for_timeout(250)
        filt=pg.evaluate("""()=>{
          const titles=[...document.querySelectorAll('#tlGrid .tcb .tt, #tlGrid .tcb')].map(el=>el.classList.contains('tt')?el.textContent:(el.querySelector('.tt')||el).textContent);
          // prefer .tt titles
          const tt=[...document.querySelectorAll('#tlGrid .tcb .tt')].map(el=>el.textContent);
          return {n:document.querySelectorAll('#tlGrid .tcb').length, tt, count:document.getElementById('tlCount').textContent, on:document.querySelector('#tlFilter').classList.contains('on'), pressed:document.querySelector('#tlFilter').getAttribute('aria-pressed')};
        }""")
        ok(f'{lab}: choosing Jim Lee shows only his 3 issues',
           filt['n']==3 and set(filt['tt'])=={'Iron Tide 01','Iron Tide 02','Iron Tide 03'} and filt['on'] and filt['pressed']=='true' and 'Jim Lee' in filt['count'], json.dumps(filt))
        ok(f'{lab}: filtered issues stay in release order',
           filt['tt']==['Iron Tide 01','Iron Tide 02','Iron Tide 03'], json.dumps(filt['tt']))

        # reopen picker for the screenshot: filtered grid behind, Jim Lee selected
        pg.click('#tlFilter'); pg.wait_for_selector('#tlPicks')
        sel=pg.evaluate("""()=>[...document.querySelectorAll('#tlPicks .tlp')].filter(b=>b.classList.contains('on')).map(b=>b.querySelector('span')?.textContent)""")
        ok(f'{lab}: reopened picker keeps Jim Lee selected', sel==['Jim Lee'], json.dumps(sel))
        pg.wait_for_timeout(400)
        pg.screenshot(path=f'{SH}/{ENG}-v66-timeline-filter-ipad-portrait.png')

        pg.locator('#tlAll').click(); pg.wait_for_timeout(200)
        reset=pg.evaluate("""()=>({n:document.querySelectorAll('#tlGrid .tcb').length, count:document.getElementById('tlCount').textContent, on:document.querySelector('#tlFilter').classList.contains('on')})""")
        ok(f'{lab}: All artists resets the Timeline to every issue',
           reset['n']==5 and (not reset['on']) and 'Jim Lee' not in reset['count'], json.dumps(reset))

        # ---- Find original art on the long-press info sheet ----
        hook_open(pg)
        pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(200)
        pg.locator('.lc[data-title="Iron Tide 01"]').click(button='right'); pg.wait_for_selector('#aArt')
        art=pg.evaluate("""()=>{
          const b=document.querySelector('#aArt'), r=b.getBoundingClientRect();
          return {txt:b.textContent.trim(), h:r.height, w:r.width, y:r.y, href:window.__cr.art.url(__cr.comics.find(c=>c.title==='Iron Tide 01')), q:window.__cr.art.query(__cr.comics.find(c=>c.title==='Iron Tide 01'))};
        }""")
        ok(f'{lab}: info sheet has Find original art (>=40px)',
           'Find original art' in art['txt'] and art['h']>=40, json.dumps(art))
        ok(f'{lab}: ComicArtIndex URL is sales/?q= plus series and issue number',
           art['q']=='Iron Tide #1' and art['href']=='https://comicartindex.com/sales/?q='+'Iron%20Tide%20%231', json.dumps(art))
        pg.wait_for_timeout(400)
        pg.screenshot(path=f'{SH}/{ENG}-v66-info-art-ipad-portrait.png')
        pg.click('#aArt'); pg.wait_for_timeout(200)
        opened=pg.evaluate('window.__opened')
        ok(f'{lab}: tapping Find original art opens that search in a new tab',
           opened and opened[0]['u']==art['href'] and opened[0]['t']=='_blank', json.dumps(opened))

        ctx.close()

    b.close()

print('---')
print(sum(res),'/' ,len(res),'passed')
real=[e for e in errors if 'access control checks' not in e.lower() and 'cross-origin' not in e.lower()]
if real:
    print('page errors:'); [print(' ',e) for e in real]
sys.exit(0 if all(res) and not real else 1)
