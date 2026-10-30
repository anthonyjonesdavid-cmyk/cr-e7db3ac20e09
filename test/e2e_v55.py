"""cr-v55: Animate page. Phase 1 (mocked server, 4 sizes, standalone insets): Animate button in the reader top bar, plan sheet with
cost, player with per-panel notes, a refused panel handled. Phase 2 (REAL=1): one real run against the live Worker (2 panels x 5s).
python3 test/e2e_v55.py [webkit]  (server on 127.0.0.1:8824)"""
import sys, os, json, re, time, urllib.request
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8824/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'; API='https://cr-animate.djapps.workers.dev'
HERE=os.path.dirname(os.path.abspath(__file__)); SH='/workspace/cr-anim-shots'; os.makedirs(SH,exist_ok=True)
PDF=os.path.join(HERE,'..','testpdfs','panels','Panel_Lab_01.pdf'); MP4=open('/tmp/mock.mp4','rb').read()
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:400] if not cond else '',flush=True)
PLAN={'mood':'Tense, stormy night chase','score':'Low strings build to a brass hit on the last panel.','panels':[
 {'box':[0.05,0.03,0.9,0.3],'what':'A figure leaps between rooftops','prompt':'p','camera':'Slow push-in','sound':'Wind, distant thunder, low cello','pacing':'Hold, then leap at 2s','seconds':6},
 {'box':[0.05,0.35,0.43,0.3],'what':'Close on the eyes','prompt':'p','camera':'Static, rack focus','sound':'Heartbeat','pacing':'Quick','seconds':5},
 {'box':[0.52,0.35,0.43,0.3],'what':'An explosion lights the sky','prompt':'p','camera':'Whip pan right','sound':'Brass hit, boom','pacing':'Sudden','seconds':5}]}
def mock(route):
    u=route.request.url; m=route.request.method
    J=lambda o,s=200: route.fulfill(status=s,content_type='application/json',headers={'access-control-allow-origin':'*'},body=json.dumps(o))
    if u.endswith('/status'): return J({'ok':True,'configured':True,'spent':1.2,'cap':10})
    if u.endswith('/check'): return J({'ok':True})
    if u.endswith('/plan'): return J({'plan':PLAN,'spent':1.2,'cap':10})
    if u.endswith('/clip') and m=='POST':
        b=json.loads(route.request.post_data); 
        if 'Whip' in b['prompt']: return J({'error':'Generated video rejected by content moderation.','refused':True},400)
        return J({'id':'m'+str(b['seconds'])})
    if '/clip/' in u: return J({'status':'done','url':'https://vidgen.x.ai/m.mp4'})
    if '/video' in u: return route.fulfill(status=200,content_type='video/mp4',headers={'access-control-allow-origin':'*'},body=MP4)
    route.fallback()
def openReader(pg):
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    pg.set_input_files('#fileIn',[PDF]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==1 && !document.querySelector(".toast .tb")',timeout=120000)
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(400); pg.click('#libGrid .lc')
    pg.wait_for_selector('#reader:not(.hidden) #zoomer canvas',timeout=30000); pg.wait_for_timeout(600)
    pg.evaluate("__cr.jumpTo(1)")
    pg.wait_for_timeout(900); pg.evaluate("document.querySelector('#reader').classList.add('ui')")
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    if os.environ.get('REAL')!='1':
     for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr,service_workers='block')
        ctx.add_init_script(f"window.__crNoScan=true; localStorage.setItem('cr.animPass','\"test-pass\"'); document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        ctx.route(API+'/**',mock)
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e))); pg.on('console',lambda m:print('console',m.type,m.text))
        openReader(pg)
        g=pg.evaluate("""(()=>{ const a=document.querySelector('#rAnim').getBoundingClientRect(), row=document.querySelector('#rtop .rrow'); const bs=[...row.children].map(e=>e.getBoundingClientRect());
          return {w:a.width,h:a.height,vis:a.width>0&&a.right<=innerWidth&&a.left>=0, over:row.scrollWidth-row.clientWidth, title:document.querySelector('#rTitle').getBoundingClientRect().width, lbl:getComputedStyle(document.querySelector('#rAnim .w')).display} })()""")
        ok(f'{lab}: Animate button visible in reader top bar, >=40px, no overflow',g['vis'] and g['w']>=40 and g['h']>=40 and g['over']<=0,json.dumps(g))
        pg.screenshot(path=f'{SH}/{lab}-1-reader.png')
        pg.evaluate("document.querySelector('#rAnim').click()"); pg.wait_for_selector('.anmodal .anrow',timeout=30000); pg.wait_for_timeout(300)
        t=pg.evaluate("document.querySelector('.anmodal').innerText")
        ok(f'{lab}: plan sheet lists 3 panels with camera/sound and cost $0.51',pg.locator('.anrow').count()==3 and '$0.51' in t and 'Whip pan right' in t,t)
        pg.screenshot(path=f'{SH}/{lab}-2-plan.png')
        pg.click('.anmodal [data-r=go]'); pg.wait_for_selector('#anim')
        pg.wait_for_function("document.querySelectorAll('#anim .anchip[data-st=ready]').length==2 && document.querySelectorAll('#anim .anchip[data-st=fail]').length==1",timeout=60000)
        pg.wait_for_timeout(800)
        s=pg.evaluate("""(()=>{ const v=document.querySelector('#anVid'), bar=document.querySelector('.anbar').getBoundingClientRect(); return {src:!!v.src, notes:document.querySelector('#anNotes').innerText, barTop:bar.top, barBg:getComputedStyle(document.querySelector('.anbar')).backgroundColor,
           chips:[...document.querySelectorAll('.anchip')].map(c=>c.getBoundingClientRect().height)} })()""")
        ok(f'{lab}: player: clip 1 loaded, notes shown, opaque bar, chips >=40px',s['src'] and 'Camera' in s['notes'] and 'Music' in s['notes'] and s['barBg']=='rgb(17, 17, 17)' and min(s['chips'])>=40,json.dumps(s))
        pg.screenshot(path=f'{SH}/{lab}-3-player.png')
        pg.click('.anchip[data-k="2"]'); pg.wait_for_timeout(300)
        r=pg.evaluate("document.querySelector('#anWait').innerText")
        ok(f'{lab}: refused panel shows a clear message',('declined' in r),r)
        if lab=='ipad-landscape': pg.screenshot(path=f'{SH}/{lab}-4-refused.png')
        pg.click('#anClose'); pg.wait_for_timeout(200)
        pg.evaluate("document.querySelector('#rAnim').click()"); pg.wait_for_selector('.anmodal .anrow, .mwrap .modal',timeout=20000)
        ctx.close()
    else:
        PASS=os.environ['TPASS']
        ctx=b.new_context(viewport={'width':1366,'height':1024},has_touch=True,device_scale_factor=2,service_workers='block')
        ctx.add_init_script("window.__crNoScan=true; localStorage.setItem('cr.animPass',%s)"%json.dumps(json.dumps(PASS)))
        def trim(route):
            r=route.fetch(); j=r.json()
            if 'plan' in j: j['plan']['panels']=j['plan']['panels'][:2]; [q.__setitem__('seconds',5) for q in j['plan']['panels']]; open('/workspace/cr-anim-shots/real-plan.json','w').write(json.dumps(j,indent=1))
            route.fulfill(response=r,body=json.dumps(j),headers={**r.headers,'access-control-allow-origin':'*'})
        ctx.route(API+'/plan',trim)
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e))); pg.on('console',lambda m: print('console',m.text) if m.type=='error' else None)
        openReader(pg); pg.evaluate("document.querySelector('#rAnim').click()"); pg.wait_for_selector('.anmodal .anrow',timeout=90000); pg.wait_for_timeout(400); pg.screenshot(path=f'{SH}/real-1-plan.png')
        print(pg.evaluate("document.querySelector('.anmodal').innerText"))
        pg.click('.anmodal [data-r=go]'); t0=time.time()
        pg.wait_for_function("[...document.querySelectorAll('#anim .anchip')].every(c=>c.dataset.st==='ready'||c.dataset.st==='fail')",timeout=600000,polling=2000)
        print('clips took',round(time.time()-t0),'s'); pg.wait_for_timeout(1500)
        st=pg.evaluate("[...document.querySelectorAll('#anim .anchip')].map(c=>c.dataset.st)"); ok('real: both panels animated',all(x=='ready' for x in st),st)
        dur=pg.evaluate("document.querySelector('#anVid').duration"); print('clip1 duration',dur)
        pg.screenshot(path=f'{SH}/real-2-player.png'); pg.click('.anchip[data-k="1"]'); pg.wait_for_timeout(2500); pg.screenshot(path=f'{SH}/real-3-player-panel2.png')
        pg.click('#anClose'); pg.evaluate("document.querySelector('#rAnim').click()"); pg.wait_for_selector('.mwrap .modal'); txt=pg.evaluate("document.querySelector('.mwrap .modal').innerText"); ok('real: cached page offers Play',('Play' in txt),txt)
        ctx.close()
    b.close()
print(f'\n{sum(res)}/{len(res)} passed'+(f'; page errors: {errors[:3]}' if errors else '')); sys.exit(0 if all(res) and not errors else 1)
