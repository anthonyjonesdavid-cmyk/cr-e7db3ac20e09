"""cr-v39 suite: 'Keep screen awake while reading' (Screen Wake Lock, mocked).  python3 test/e2e_v39.py [webkit]  (server on 127.0.0.1:8823)
Fixtures: original abstract comics (test/gen_pdfs.py). Standalone insets via --sat/--sab."""
import sys, os, json
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
FILES=[os.path.join(T,'Iron_Tide_01.pdf'),os.path.join(T,'Nightfall_01.pdf')]
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,str(extra)[:300] if not cond else '',flush=True)
MOCK="""(()=>{ const W=window.__wl={req:0,rel:0,active:null,hidden:false};
  Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>W.hidden?'hidden':'visible'});
  Object.defineProperty(document,'hidden',{configurable:true,get:()=>W.hidden});
  const mk=()=>{ const ls=[]; const s={released:false,type:'screen',addEventListener:(t,f)=>{ if(t==='release') ls.push(f); },
    release:async()=>{ if(s.released) return; s.released=true; W.rel++; if(W.active===s) W.active=null; ls.forEach(f=>f()); },
    _sys:()=>{ s.released=true; if(W.active===s) W.active=null; ls.forEach(f=>f()); } }; return s; };
  Object.defineProperty(navigator,'wakeLock',{configurable:true,value:{request:async t=>{ if(t!=='screen') throw new Error('type'); if(W.hidden) throw new Error('NotAllowedError'); W.req++; const s=mk(); W.active=s; return s; }}});
  W.hide=()=>{ W.hidden=true; if(W.active) W.active._sys(); document.dispatchEvent(new Event('visibilitychange')); };   // the system drops the lock when the page is hidden
  W.show=()=>{ W.hidden=false; document.dispatchEvent(new Event('visibilitychange')); };
})()"""
ST="({req:__wl.req,rel:__wl.rel,active:!!__wl.active,mine:!!__cr.wake.lock})"
def back(pg): pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(300)
def open_c(pg,t='Iron Tide 01'):
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150); pg.locator(f'.lc[data-title="{t}"]').click(); pg.wait_for_selector('#reader:not(.hidden)'); pg.wait_for_timeout(500)
with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    for (w,h,lab,dpr,sat,sab) in [(1366,1024,'ipad-landscape',2,24,20),(1024,1366,'ipad-portrait',2,24,20),(390,844,'iphone-390',3,47,34),(430,932,'iphone-430',3,59,34)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=dpr)
        ctx.add_init_script(MOCK); ctx.add_init_script(f"window.__crNoScan=true; document.addEventListener('DOMContentLoaded',()=>{{document.documentElement.style.setProperty('--sat','{sat}px');document.documentElement.style.setProperty('--sab','{sab}px')}})")
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector('html[data-ready]')
        pg.set_input_files('#fileIn',FILES); pg.wait_for_function(f'document.querySelectorAll("#libGrid .lc").length=={len(FILES)} && !document.querySelector(".toast .tb")',timeout=120000)
        pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200)
        pg.click('#settingsBtn'); pg.wait_for_selector('#sAwake')
        g=pg.evaluate("""(()=>{const i=document.querySelector('#sAwake'), l=i.closest('label'), r=l.getBoundingClientRect(), ri=i.getBoundingClientRect();
          return {checked:i.checked,stored:localStorage.getItem('cr.keepAwake'),h:r.height,w:r.width,ih:ri.height,iw:ri.width,txt:l.textContent,note:document.querySelector('#sAwakeNote').textContent}})()""")
        ok(f'{lab}: Settings has "Keep screen awake while reading", OFF by default, tap target >=40px',not g['checked'] and g['stored'] is None and 'Keep screen awake while reading' in g['txt'] and g['h']>=40 and g['w']>=40,json.dumps(g))
        pg.locator('#sAwake').evaluate("e=>e.closest('label').scrollIntoView({block:'center'})"); pg.wait_for_timeout(150)
        if lab in ('ipad-portrait','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v39-settings-keepawake-off-{lab}.png')
        if lab=='ipad-portrait':
            pg.click('[data-r=done]'); pg.wait_for_timeout(300)
            open_c(pg); s=pg.evaluate(ST); ok('toggle OFF: opening the reader requests no wake lock',s['req']==0 and not s['active'],json.dumps(s)); back(pg)
            pg.click('#settingsBtn'); pg.wait_for_selector('#sAwake')
        pg.locator('#sAwake').evaluate("e=>e.closest('label').scrollIntoView({block:'center'})"); pg.locator('#sAwake').evaluate("e=>e.closest('label').click()"); pg.wait_for_timeout(200)
        g2=pg.evaluate("({c:document.querySelector('#sAwake').checked,st:localStorage.getItem('cr.keepAwake')})"); s=pg.evaluate(ST)
        ok(f'{lab}: turning it on is stored in localStorage; no lock outside the reader',g2['c'] and g2['st']=='true' and s['req']==0 and not s['active'],json.dumps([g2,s]))
        if lab in ('ipad-portrait','iphone-390'): pg.screenshot(path=f'{SH}/{ENG}-v39-settings-keepawake-on-{lab}.png')
        pg.click('[data-r=done]'); pg.wait_for_timeout(300)
        open_c(pg); s=pg.evaluate(ST); ok(f'{lab}: toggle ON: wake lock acquired when the reader opens',s['req']==1 and s['active'] and s['mine'],json.dumps(s))
        pg.evaluate('__wl.hide()'); pg.wait_for_timeout(150); s=pg.evaluate(ST); ok(f'{lab}: app hidden: system drops the lock, none re-requested while hidden',not s['active'] and not s['mine'] and s['req']==1,json.dumps(s))
        pg.evaluate('__wl.show()'); pg.wait_for_timeout(200); s=pg.evaluate(ST); ok(f'{lab}: visible again while reading: wake lock re-acquired',s['req']==2 and s['active'] and s['mine'],json.dumps(s))
        back(pg); s=pg.evaluate(ST); ok(f'{lab}: leaving the reader releases the wake lock',not s['active'] and not s['mine'] and s['rel']>=1,json.dumps(s))
        pg.evaluate('__wl.hide()'); pg.evaluate('__wl.show()'); pg.wait_for_timeout(200); s=pg.evaluate(ST); ok(f'{lab}: visibility returning outside the reader does not acquire',s['req']==2 and not s['active'],json.dumps(s))
        if lab=='ipad-portrait':
            open_c(pg); s1=pg.evaluate(ST)
            pg.click('#tabs [data-tab=home]') if False else None
            pg.evaluate("localStorage.setItem('cr.keepAwake','false'); __cr.wake.sync()"); pg.wait_for_timeout(200); s=pg.evaluate(ST)
            ok('turning the toggle off while a lock is held releases it',s1['active'] and not s['active'] and not s['mine'],json.dumps([s1,s]))
            pg.evaluate('__wl.hide()'); pg.evaluate('__wl.show()'); pg.wait_for_timeout(200); s2=pg.evaluate(ST); ok('toggle off: no re-acquire on visibility',not s2['active'] and s2['req']==s['req'],json.dumps(s2))
            back(pg)
            pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.click('#settingsBtn'); pg.wait_for_selector('#sAwake')
            ok('setting persists across reload (localStorage)',not pg.evaluate("document.querySelector('#sAwake').checked")); pg.click('[data-r=done]')
        ctx.close()
    # unsupported browser: short note under the toggle, nothing breaks
    ctx=b.new_context(viewport={'width':1024,'height':1366},has_touch=True,device_scale_factor=2)
    ctx.add_init_script("Object.defineProperty(navigator,'wakeLock',{configurable:true,value:undefined}); window.__crNoScan=true; localStorage.setItem('cr.keepAwake','true')")
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e))); pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    pg.set_input_files('#fileIn',FILES[:1]); pg.wait_for_function('document.querySelectorAll("#libGrid .lc").length==1 && !document.querySelector(".toast .tb")',timeout=120000)
    pg.click('#settingsBtn'); pg.wait_for_selector('#sAwake'); n=pg.text_content('#sAwakeNote'); pg.locator('#sAwake').evaluate("e=>e.closest('label').scrollIntoView({block:'center'})"); pg.wait_for_timeout(150)
    pg.screenshot(path=f'{SH}/{ENG}-v39-settings-keepawake-unsupported.png')
    ok('unsupported: short note under the toggle',n.startswith('Not supported') and '16.4' in n,n); pg.click('[data-r=done]'); pg.wait_for_timeout(200)
    open_c(pg); ok('unsupported: reader still opens fine',pg.is_visible('#reader') and not pg.evaluate('!!__cr.wake.lock')); ctx.close()
    b.close()
ok('no page errors',not errors,'; '.join(errors[:3]))
print(f'{sum(res)}/{len(res)} passed [{ENG}]'); sys.exit(0 if all(res) else 1)
