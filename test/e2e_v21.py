"""cr-v21 suite: guided panel view, sharp zoom tiles, reading lists.  python3 test/e2e_v21.py [webkit|chromium]  (server on 127.0.0.1:8823)
Fixtures are original abstract panel pages (test/gen_panels.py) plus the original test comics (test/gen_pdfs.py)."""
import sys, os, json, io, subprocess
from playwright.sync_api import sync_playwright
from PIL import Image, ImageFilter, ImageStat
URL='http://127.0.0.1:8823/'; ENG=sys.argv[1] if len(sys.argv)>1 else 'webkit'
HERE=os.path.dirname(os.path.abspath(__file__)); T=os.path.join(HERE,'..','testpdfs'); PN=os.path.join(T,'panels'); SH=os.path.join(HERE,'..','shots'); os.makedirs(SH,exist_ok=True)
if not os.path.exists(os.path.join(PN,'truth.json')): subprocess.run([sys.executable,os.path.join(HERE,'gen_panels.py')],check=True)
TRUTH=json.load(open(os.path.join(PN,'truth.json')))
res=[]; errors=[]
def ok(name,cond,extra=''):
    res.append(bool(cond)); print(('PASS' if cond else 'FAIL'),f'[{ENG}]',name,(extra if not cond or len(str(extra))<160 else str(extra)[:160]),flush=True)
def iou(a,b):
    bx,by,bw,bh=b; ix=max(0,min(a['x']+a['w'],bx+bw)-max(a['x'],bx)); iy=max(0,min(a['y']+a['h'],by+bh)-max(a['y'],by)); I=ix*iy; return I/(a['w']*a['h']+bw*bh-I)
TAP='''async ({x,y,n})=>{ const st=document.querySelector('#stage'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  for(let k=0;k<n;k++){ const o={bubbles:true,cancelable:true,pointerId:20+k,pointerType:'touch',isPrimary:true,clientX:x,clientY:y,button:0};
    st.dispatchEvent(new PointerEvent('pointerdown',{...o,buttons:1})); await sleep(40); st.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0})); await sleep(90); } await sleep(500); }'''
SWIPE='''async ({x,y,dx,dy,dt})=>{ const st=document.querySelector('#stage'); const sleep=ms=>new Promise(r=>setTimeout(r,ms)); dy=dy||0;
  const ev=(t,cx,cy)=>st.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:11,pointerType:'touch',isPrimary:true,clientX:cx,clientY:cy,buttons:t==='pointerup'?0:1}));
  ev('pointerdown',x,y); for(let i=1;i<=5;i++){ await sleep(dt||16); ev('pointermove',x+dx*i/5,y+dy*i/5); } ev('pointerup',x+dx,y+dy); await sleep(700); }'''
PINCH='''async ({cx,cy,d0,d1})=>{ const st=document.querySelector('#stage'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const ev=(t,id,x,y)=>st.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:id,pointerType:'touch',isPrimary:id===31,clientX:x,clientY:y,buttons:t==='pointerup'?0:1}));
  ev('pointerdown',31,cx-d0/2,cy); await sleep(10); ev('pointerdown',32,cx+d0/2,cy);
  for(let i=1;i<=10;i++){ const d=d0+(d1-d0)*i/10; await sleep(16); ev('pointermove',31,cx-d/2,cy); ev('pointermove',32,cx+d/2,cy); }
  ev('pointerup',31,cx-d1/2,cy); ev('pointerup',32,cx+d1/2,cy); await sleep(400); return window.__cr.Z.s; }'''
PS='''(()=>{const P=__cr.panels.P, R=__cr.R, v=R.views[R.vi]||[], m=document.querySelector('#pmask'), b=document.querySelector('#pExit'), st=document.querySelector('#stage').getBoundingClientRect();
  const mr=m.getBoundingClientRect(), br=b.getBoundingClientRect();
  return {on:P.on,i:P.i,n:P.list.length,keys:P.list.map(p=>p.key+':'+p.bi),fb:P.list.map(p=>p.fb),vi:R.vi,first:v.filter(x=>x!=null)[0],z:__cr.Z.s,rtl:R.rtl,
    mask:m.classList.contains('hidden')?null:{x:mr.left-st.left,y:mr.top-st.top,w:mr.width,h:mr.height},W:st.width,H:st.height,
    btn:b.classList.contains('hidden')?null:{w:br.width,h:br.height,bottom:innerHeight-br.bottom,txt:b.textContent}}})()'''
def ps(pg): return pg.evaluate(PS)
def wait_render(pg,t=15000): pg.wait_for_function('document.querySelectorAll(".view .pg.loading").length===0 && document.querySelectorAll(".view .pg canvas").length>0',timeout=t)
def geo(pg): b=pg.locator('#stage').bounding_box(); return b['x'],b['y'],b['width'],b['height']
def settle(pg,ms=650): pg.wait_for_timeout(ms); pg.wait_for_function('!__cr.panels.P.busy',timeout=8000)
def open_comic(pg,title):
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150); pg.locator(f'.lc[data-title="{title}"]').click(); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg); pg.wait_for_timeout(300)
def back(pg): pg.evaluate('__cr.toggleUI(true)'); pg.click('#rBack'); pg.wait_for_selector('#shelf:not(.hidden)'); pg.wait_for_timeout(200)
def panel_center(pg,k):   # stage coords of panel k on the current (unzoomed) view
    return pg.evaluate(f"__cr.panels.list(__cr.R.vi).then(L=>{{const p=L[{k}]; const st=document.querySelector('#stage').getBoundingClientRect(); return {{x:st.left+p.r.x+p.r.w/2,y:st.top+p.r.y+p.r.h/2,n:L.length}}}})")
def enter(pg,k):
    c=panel_center(pg,k); pg.evaluate(TAP,{'x':c['x'],'y':c['y'],'n':2}); settle(pg); return ps(pg)
def fits(s,lab):
    m=s['mask']; ok(f'{lab}: panel fills the screen, centred, nothing cut off',m and m['x']>=-1 and m['y']>=-1 and m['x']+m['w']<=s['W']+1 and m['y']+m['h']<=s['H']+1 and (m['w']>=s['W']*.86 or m['h']>=s['H']*.86) and abs(m['x']+m['w']/2-s['W']/2)<3 and abs(m['y']+m['h']/2-s['H']/2)<3,json.dumps(m))
def sharp(im): g=im.convert('L').filter(ImageFilter.FIND_EDGES); return ImageStat.Stat(g).mean[0]

with sync_playwright() as p:
    b=getattr(p,ENG).launch()
    ctx=b.new_context(viewport={'width':1024,'height':1366},has_touch=True,device_scale_factor=2)
    ctx.add_init_script("window.__crNoScan=true; document.addEventListener('DOMContentLoaded',()=>{document.documentElement.style.setProperty('--sat','24px');document.documentElement.style.setProperty('--sab','20px')})")   # iPad standalone insets
    pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append('pageerror: '+str(e)))
    pg.on('console',lambda m: errors.append(f'console.error: {m.text}') if m.type=='error' and 'google' not in m.text else None)
    ctx.route(__import__('re').compile(r'https://([a-z0-9-]+\.)*(google|googleapis|gstatic)\.com/'),lambda r:r.abort())
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')

    # ======== 1. panel detection (XY-cut) against the generated ground truth ========
    for name in ['Panel_Lab_01','Panel_Lab_02']:
        det=pg.evaluate(f"__cr.panels.detectUrl('testpdfs/panels/{name}.pdf')")
        for i,(d,t) in enumerate(zip(det,TRUTH[name])):
            if name=='Panel_Lab_02' and i==0: continue
            pairs=[(d[h],t[h],f'{name} p{i+1}{h}') for h in 'LR'] if isinstance(t,dict) else [(d,t,f'{name} p{i+1}')]
            for dd,tt,lab in pairs:
                if tt is None: ok(f'detect {lab}: splash page (no gutters) -> detection fails -> thirds fallback',dd is None,json.dumps(dd)); continue
                ious=[iou(a,b2) for a,b2 in zip(dd or [],tt)]
                ok(f'detect {lab}: {len(tt)} panels in reading order (IoU>=0.9 each)',dd is not None and len(dd)==len(tt) and min(ious)>=.9,json.dumps([len(dd or []),[round(x,2) for x in ious]]))
    rt=pg.evaluate("__cr.panels.detectUrl('testpdfs/panels/Panel_Lab_01.pdf',true)")[1]
    ok('detect RTL: the two side-by-side panels come right-first',rt and rt[1]['x']>rt[2]['x'] and rt[0]['y']<rt[1]['y'],json.dumps(rt))
    ok('thirds fallback = 3 rows (upright) / 3 columns (wide, RTL reversed)',pg.evaluate("JSON.stringify(__cr.panels.thirds(.65,false).map(b=>[b.y,b.h]))")=='[[0,0.3333333333333333],[0.3333333333333333,0.3333333333333333],[0.6666666666666666,0.3333333333333333]]' and pg.evaluate("__cr.panels.thirds(1.5,true)[0].x")>.6)

    # ======== import fixtures ========
    files=[os.path.join(PN,'Panel_Lab_01.pdf'),os.path.join(PN,'Panel_Lab_02.pdf')]+[os.path.join(T,f) for f in ['Nightfall_01.pdf','Nightfall_02.pdf','Iron_Tide_01.pdf','Iron_Tide_02.pdf']]
    pg.set_input_files('#fileIn',files); pg.wait_for_function(f'document.querySelectorAll(".lc").length=={len(files)} && !document.querySelector(".toast .tb")',timeout=120000); pg.wait_for_timeout(500)
    ok('imported fixtures',True)

    # ======== 2. guided panel view: iPad portrait 1024x1366 ========
    open_comic(pg,'Panel Lab 01'); pg.evaluate('__cr.jumpTo(1)'); wait_render(pg); pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(300)
    s=enter(pg,1); ok('double-tap a panel enters panel view on THAT panel',s['on'] and s['i']==1 and s['n']==4 and s['z']>1.2,json.dumps(s)); fits(s,'iPad portrait')
    ok('Full Page button: shown, >=40px tall, counter, above the home indicator inset',s['btn'] and s['btn']['h']>=40 and s['btn']['bottom']>=20 and '2 / 4' in s['btn']['txt'],json.dumps(s['btn']))
    pg.wait_for_timeout(500); pg.screenshot(path=f'{SH}/{ENG}-v21-panel-ipad-portrait.png')
    x0,y0,W,H=geo(pg)
    pg.evaluate(SWIPE,{'x':x0+W*.6,'y':y0+H*.5,'dx':-90}); settle(pg); s=ps(pg); ok('swipe left -> next panel (glides)',s['on'] and s['i']==2,json.dumps(s)); fits(s,'after swipe')
    pg.evaluate(SWIPE,{'x':x0+W*.4,'y':y0+H*.5,'dx':90}); settle(pg); ok('swipe right -> previous panel',ps(pg)['i']==1)
    pg.evaluate(SWIPE,{'x':x0+W*.6,'y':y0+H*.5,'dx':-20,'dt':120}); pg.wait_for_timeout(200); settle(pg); ok('tiny drag (20px, slow) snaps back to the same panel',ps(pg)['i']==1)
    pg.evaluate(SWIPE,{'x':x0+W*.5,'y':y0+H*.5,'dx':4,'dy':-120}); settle(pg); s=ps(pg); ok('vertical drag pans, stays in panel view on the same panel',s['on'] and s['i']==1,json.dumps(s))
    pg.evaluate(TAP,{'x':x0+W*.95,'y':y0+H*.5,'n':1}); settle(pg); ok('tap right edge -> next panel',ps(pg)['i']==2)
    pg.keyboard.press('ArrowRight'); settle(pg); ok('arrow key -> next panel',ps(pg)['i']==3)
    pg.evaluate(SWIPE,{'x':x0+W*.6,'y':y0+H*.5,'dx':-90}); settle(pg,900); s=ps(pg)
    ok('after the last panel: next page, first panel (still in panel view)',s['on'] and s['first']==2 and s['i']==0 and s['n']==5,json.dumps(s)); fits(s,'next page')
    pg.evaluate(SWIPE,{'x':x0+W*.4,'y':y0+H*.5,'dx':90}); settle(pg,900); s=ps(pg)
    ok('back from the first panel: previous page, LAST panel',s['on'] and s['first']==1 and s['i']==3,json.dumps(s))
    c=pg.evaluate("JSON.stringify(Object.keys(__cr.R.comic.panels||{}).sort())"); ok('panel boxes cached per page on the comic record',set(['1','2'])<=set(json.loads(c)),c)
    # splash page -> thirds
    pg.evaluate('__cr.panels.exit(false)'); pg.evaluate('__cr.jumpTo(4)'); wait_render(pg); s=enter(pg,0)
    ok('splash page (no gutters): thirds fallback, top third first',s['on'] and s['n']==3 and all(s['fb']) and s['i']==0 or (s['on'] and s['n']==3 and all(s['fb'])),json.dumps(s))
    # double-tap exits
    pg.evaluate(TAP,{'x':x0+W*.5,'y':y0+H*.5,'n':2}); pg.wait_for_timeout(500); s=ps(pg); ok('double-tap again -> full page',not s['on'] and s['z']==1 and s['mask'] is None and s['btn'] is None,json.dumps(s))
    s=enter(pg,1); pg.click('#pExit'); pg.wait_for_timeout(500); s=ps(pg); ok('Full Page button exits',not s['on'] and s['z']==1)
    # pinch takes over
    s=enter(pg,1); z=pg.evaluate(PINCH,{'cx':x0+W/2,'cy':y0+H/2,'d0':120,'d1':200}); s=ps(pg); ok('pinch in panel view -> free zoom (panel view off, zoom kept)',not s['on'] and z>1.2 and s['mask'] is None,json.dumps([z,s]))
    pg.evaluate(TAP,{'x':x0+W*.5,'y':y0+H*.5,'n':2}); pg.wait_for_timeout(400); ok('double-tap resets the free zoom',ps(pg)['z']==1)
    # page turns still work at full page
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(900); ok('normal page turn still works after panel view',ps(pg)['first']==5)
    # rotation keeps the panel
    pg.evaluate('__cr.jumpTo(1)'); wait_render(pg); s=enter(pg,2); pg.set_viewport_size({'width':1366,'height':1024}); pg.wait_for_timeout(900); settle(pg)
    s=ps(pg); ok('rotate to landscape (2-up): stays in panel view on the same panel',s['on'] and s['keys'][s['i']]=='1:2',json.dumps(s)); fits(s,'iPad landscape 1366x1024')
    pg.screenshot(path=f'{SH}/{ENG}-v21-panel-ipad-landscape.png')
    ok('landscape 2-up: panels of both visible pages, left page first',s['n']>=8 and s['keys'][0].startswith('1:') and s['keys'][-1].startswith('2:'),json.dumps(s['keys']))
    pg.evaluate('__cr.panels.exit(false)'); pg.set_viewport_size({'width':1024,'height':1366}); pg.wait_for_timeout(700)
    # RTL
    pg.evaluate('__cr.toggleUI(true)'); pg.click('#rRtl'); pg.wait_for_timeout(300); pg.evaluate('__cr.toggleUI(false)'); pg.evaluate('__cr.jumpTo(1)'); wait_render(pg); pg.wait_for_timeout(300)
    s=enter(pg,0); pg.evaluate(SWIPE,{'x':x0+W*.4,'y':y0+H*.5,'dx':90}); settle(pg); s=ps(pg)
    ok('RTL: swipe right -> next panel; side-by-side panels right-first',s['on'] and s['i']==1 and s['keys']==['1:0','1:1','1:2','1:3'],json.dumps(s))
    pr=pg.evaluate("(()=>{const L=__cr.panels.P.list; return [L[1].r.x,L[2].r.x]})()"); ok('RTL: panel 2 sits right of panel 3',pr[0]>pr[1],str(pr))
    pg.evaluate('__cr.panels.exit(false)'); pg.evaluate('__cr.toggleUI(true)'); pg.click('#rRtl'); pg.wait_for_timeout(300); pg.evaluate('__cr.toggleUI(false)')
    # setting off
    pg.evaluate("localStorage.setItem('cr.panelView','false')"); pg.evaluate(TAP,{'x':x0+W*.5,'y':y0+H*.4,'n':2}); pg.wait_for_timeout(500); s=ps(pg)
    ok('setting off: double-tap = plain 2.5x zoom',not s['on'] and abs(s['z']-2.5)<.01,json.dumps(s)); pg.evaluate(TAP,{'x':x0+W*.5,'y':y0+H*.4,'n':2}); pg.wait_for_timeout(400)
    pg.evaluate("localStorage.removeItem('cr.panelView')")

    # ======== 3. sharp zoom tiles ========
    pg.evaluate('__cr.jumpTo(1)'); wait_render(pg); pg.wait_for_timeout(300)
    lab=pg.evaluate("(()=>{const c=document.querySelector('.view .pg canvas'), r=c.getBoundingClientRect(); return {x:r.left+r.width*.18,y:r.top+r.height*.055}})()")   # caption 'PANEL 1 · TEST TEXT Aa'
    pg.evaluate("([x,y])=>{ const Z=__cr.Z; const st=document.querySelector('#stage').getBoundingClientRect(); const px=x-st.left, py=y-st.top; Z.s=4; Z.tx=st.width/2-px*4; Z.ty=st.height/2-py*4; document.querySelector('#zoomer').style.transform=`translate3d(${Z.tx}px,${Z.ty}px,0) scale(4)`; }",[lab['x'],lab['y']])
    pg.evaluate("__cr.scheduleHi(); __cr.scheduleHi(); __cr.scheduleHi()")   # rapid re-requests: older renders are cancelled
    pg.wait_for_function("document.querySelector('.view .pg canvas.tile')",timeout=15000); pg.wait_for_timeout(300)
    ti=pg.evaluate("(()=>{const t=[...document.querySelectorAll('.view .pg canvas.tile')], c=document.querySelector('.view .pg canvas:not(.tile)'); return {n:t.length,px:t.map(x=>x.width*x.height),k:t[0].width/parseFloat(t[0].style.width),base:c.width/parseFloat(c.style.width)}})()")
    ok('one tile per page after rapid re-requests (stale renders cancelled)',ti['n']==1,json.dumps(ti))
    ok('tile rendered at devicePixelRatio x zoom (2 x 4 = 8 px per CSS px), capped <= 16 MP',abs(ti['k']-8)<.6 and max(ti['px'])<=16e6,json.dumps(ti))
    W2,H2=pg.viewport_size['width'],pg.viewport_size['height']; clip={'x':W2/2-200,'y':H2/2-60,'width':400,'height':120}
    a=Image.open(io.BytesIO(pg.screenshot(clip=clip))); a.save(f'{SH}/{ENG}-v21-zoom-tile.png')
    pg.evaluate("document.querySelectorAll('canvas.tile').forEach(t=>t.style.visibility='hidden')"); pg.wait_for_timeout(150)
    bimg=Image.open(io.BytesIO(pg.screenshot(clip=clip))); bimg.save(f'{SH}/{ENG}-v21-zoom-stretched.png')
    pg.evaluate("document.querySelectorAll('canvas.tile').forEach(t=>t.style.visibility='')")
    sa,sb=sharp(a),sharp(bimg); ok('zoomed text is crisp: edge energy with the tile >= 1.5x the stretched page',sa>=sb*1.5,f'tile {sa:.2f} vs stretched {sb:.2f}')
    pg.evaluate(TAP,{'x':x0+W*.5,'y':y0+H*.5,'n':2}); pg.wait_for_timeout(500)
    ok('zoom reset discards the tile',pg.evaluate("document.querySelectorAll('canvas.tile').length")==0 and ps(pg)['z']==1)
    s=enter(pg,0); pg.wait_for_function("document.querySelector('.view .pg canvas.tile')",timeout=15000); ok('panel view zoom also gets a sharp tile',True)
    pg.evaluate('__cr.panels.exit(false)'); pg.wait_for_timeout(300); ok('exit panel view discards the tile',pg.evaluate("document.querySelectorAll('canvas.tile').length")==0)
    back(pg)

    # ======== 4. fold / half pages ========
    open_comic(pg,'Panel Lab 02'); pg.evaluate("__cr.jumpTo(1)"); wait_render(pg); pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(300)
    u=pg.evaluate("JSON.stringify(__cr.panels.units(__cr.R.vi))"); s=enter(pg,0)
    ok('fold comic, portrait half page: panels of that half only',s['on'] and s['n']==3 and s['keys'][0]=='1L:0',json.dumps([u,s['keys']])); fits(s,'half page')
    pg.evaluate(SWIPE,{'x':x0+W*.6,'y':y0+H*.5,'dx':-90}); settle(pg); pg.evaluate(SWIPE,{'x':x0+W*.6,'y':y0+H*.5,'dx':-90}); settle(pg); pg.evaluate(SWIPE,{'x':x0+W*.6,'y':y0+H*.5,'dx':-90}); settle(pg,900)
    s=ps(pg); ok('half page: after its last panel -> the other half of the sheet',s['on'] and s['keys'][s['i']]=='1R:0',json.dumps(s['keys']))
    pg.evaluate('__cr.panels.exit(false)'); pg.set_viewport_size({'width':1366,'height':1024}); pg.wait_for_timeout(900); wait_render(pg)
    s=enter(pg,0); ok('fold comic, landscape full sheet: left page panels then right page panels',s['on'] and s['n']==6 and s['keys'][0]=='1L:0' and s['keys'][3]=='1R:0',json.dumps(s['keys'])); fits(s,'fold sheet landscape')
    pg.evaluate('__cr.panels.exit(false)'); pg.set_viewport_size({'width':1024,'height':1366}); pg.wait_for_timeout(700); back(pg)

    # ======== 5. reading lists ========
    def sheet(title,act): pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(150); pg.locator(f'.lc[data-title="{title}"]').click(button='right'); pg.wait_for_selector(f'#{act}'); pg.click(f'#{act}'); pg.wait_for_timeout(250)
    sheet('Nightfall 02','aQueue'); ok('long-press sheet: Add to Reading List',pg.locator('#qaName').count()==1)
    pg.fill('#qaName','Inferno'); pg.click('#qaDone'); pg.wait_for_timeout(400)
    sheet('Iron Tide 01','aQueue'); ok('existing list offered as a checkbox',pg.locator('#qaList input[data-q]').count()==1); pg.check('#qaList input[data-q]'); pg.click('#qaDone'); pg.wait_for_timeout(300)
    open_comic(pg,'Nightfall 01'); pg.evaluate('__cr.toggleUI(true)'); pg.click('#rMore'); pg.click('#rmQueue'); pg.wait_for_selector('#qaList'); pg.check('#qaList input[data-q]'); pg.click('#qaDone'); pg.wait_for_timeout(300); back(pg)
    q=pg.evaluate("__cr.queues.map(q=>({name:q.name,items:q.items.map(id=>__cr.comics.find(c=>c.id===id).title)}))")
    ok('reader ••• also adds; list keeps the order added',q==[{'name':'Inferno','items':['Nightfall 02','Iron Tide 01','Nightfall 01']}],json.dumps(q))
    pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300)
    row=pg.evaluate("(()=>{const r=document.querySelector('.qrow'); const rows=[...document.querySelectorAll('#homeScroll .row-h h2')].map(h=>h.textContent); return r&&{h:r.querySelector('h2').textContent,n:r.querySelector('.qprog').textContent,t:[...r.querySelectorAll('.rc')].map(e=>e.getAttribute('aria-label')),rows}})()")
    ok('Home row for the list with progress "0 of 3", right under Recently Added',row and row['h']=='Inferno' and row['n']=='0 of 3' and row['rows'][1]=='Inferno' and row['t'][0]=='1. Nightfall 02',json.dumps(row))
    pg.evaluate("document.querySelector('#homeScroll').scrollTop=300"); pg.wait_for_timeout(200); pg.screenshot(path=f'{SH}/{ENG}-v21-home-reading-list.png'); pg.evaluate("document.querySelector('#homeScroll').scrollTop=0")
    # reorder by dragging the handle
    pg.click('.qrow .row-h'); pg.wait_for_selector('#qeList'); pg.wait_for_timeout(200)
    h=pg.locator('#qeList li').nth(2).locator('.ah').bounding_box(); t0=pg.locator('#qeList li').nth(0).bounding_box()
    pg.evaluate('''async ([x,y,ty])=>{ const el=document.elementFromPoint(x,y); const sleep=ms=>new Promise(r=>setTimeout(r,ms)); const o={bubbles:true,cancelable:true,pointerId:61,pointerType:'touch',isPrimary:true,clientX:x};
      el.dispatchEvent(new PointerEvent('pointerdown',{...o,clientY:y,buttons:1})); for(let i=1;i<=12;i++){ await sleep(16); el.dispatchEvent(new PointerEvent('pointermove',{...o,clientY:y+(ty-y)*i/12,buttons:1})); }
      el.dispatchEvent(new PointerEvent('pointerup',{...o,clientY:ty,buttons:0})); }''',[h['x']+h['width']/2,h['y']+h['height']/2,t0['y']+5])
    pg.wait_for_timeout(200); ok('drag ≡ reorders the list',pg.eval_on_selector_all('#qeList li .at b','e=>e.map(x=>x.textContent)')==['Nightfall 01','Nightfall 02','Iron Tide 01'])
    bx=pg.locator('#qeList .qx').first.bounding_box(); ok('editor buttons are >=40px tap targets',bx['width']>=40 and bx['height']>=40,json.dumps(bx))
    pg.screenshot(path=f'{SH}/{ENG}-v21-reading-list-editor.png'); pg.click('#qeDone'); pg.wait_for_timeout(300)
    # next-issue card follows the list when opened from it
    pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200); pg.locator('.qrow .rc').nth(1).click(); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg)
    nx=pg.evaluate("(()=>{const R=__cr.R; return {cur:R.comic.title,next:R.next&&R.next.title,q:R.queue}})()")
    ok('opened from the list: next issue = next in the list (not series order)',nx['cur']=='Nightfall 02' and nx['next']=='Iron Tide 01' and nx['q'],json.dumps(nx))
    pg.evaluate("__cr.jumpTo(__cr.R.n)"); wait_render(pg); pg.wait_for_timeout(400); pg.screenshot(path=f'{SH}/{ENG}-v21-next-in-list.png')
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(1500); wait_render(pg); nx=pg.evaluate("({cur:__cr.R.comic.title,next:__cr.R.next&&__cr.R.next.title})")
    ok('turning past the card opens the list\'s next comic; the list continues (Iron Tide 01 is last -> End)',nx['cur']=='Iron Tide 01' and nx['next'] is None,json.dumps(nx))
    pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg)
    ok('reload keeps the list context',pg.evaluate("!!__cr.R.queue&&__cr.R.comic.title==='Iron Tide 01'"))
    back(pg); open_comic(pg,'Nightfall 02'); nx=pg.evaluate("({next:__cr.R.next&&__cr.R.next.title,q:__cr.R.queue})")
    ok('opened from the Library: series order again',nx['next'] is None or nx['next']!='Iron Tide 01',json.dumps(nx)); back(pg)
    # progress x of y + persistence in IndexedDB
    pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200)
    p0=pg.text_content('.qrow .qprog'); pg.locator('.qrow .rc').nth(0).click(button='right'); pg.click('#aToggle'); pg.wait_for_timeout(300)
    ok('progress x of y counts finished comics (read-through Nightfall 02 = 1 of 3, then mark Nightfall 01 finished = 2 of 3)',p0=='1 of 3' and pg.text_content('.qrow .qprog')=='2 of 3',p0+' -> '+pg.text_content('.qrow .qprog'))
    idb=pg.evaluate("(async()=>{const r=indexedDB.open('comic-reader');await new Promise(x=>r.onsuccess=x);const d=r.result;const v=d.version, names=[...d.objectStoreNames];const all=await new Promise(x=>{const q=d.transaction('queues').objectStore('queues').getAll();q.onsuccess=()=>x(q.result)});d.close();return {v,names,all:all.map(q=>({name:q.name,n:q.items.length}))}})()")
    ok('stored in IndexedDB (v2, "queues" store)',idb['v']==2 and 'queues' in idb['names'] and idb['all']==[{'name':'Inferno','n':3}],json.dumps(idb))
    pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300); ok('list survives a reload',pg.locator('.qrow').count()==1)
    # deleting a comic removes it from lists; delete list
    pg.click('.qrow .row-more'); pg.click('#qmDelete'); pg.click('#confirmOk'); pg.wait_for_timeout(300); ok('delete reading list (comics stay)',pg.locator('.qrow').count()==0 and pg.evaluate('__cr.comics.length')==len(files))

    # ======== 5b. cr-v22: every launch lands on Home; in-session navigation unchanged ========
    TABST="(()=>({tab:document.querySelector('#tabs .on').dataset.tab,home:!document.querySelector('#home').classList.contains('hidden'),lib:!document.querySelector('#library').classList.contains('hidden'),scoped:document.querySelector('#shelf').classList.contains('scoped'),hash:location.hash,saved:localStorage.getItem('cr.tab'),reader:!document.querySelector('#reader').classList.contains('hidden')}))()"
    def home_ok(st): return st['tab']=='home' and st['home'] and not st['lib'] and not st['scoped'] and not st['reader']
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(200); open_comic(pg,'Panel Lab 01'); back(pg); st=pg.evaluate(TABST)
    ok('in session: closing a comic opened from Library returns to Library (unchanged)',st['tab']=='library' and st['lib'],json.dumps(st))
    ok('the last tab is no longer saved',st['saved'] is None,json.dumps(st))
    pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(400); st=pg.evaluate(TABST); ok('reopen after leaving it on Library -> Home',home_ok(st),json.dumps(st))
    pg.click('#tabs [data-tab=home]'); pg.locator('.row-h',has_text='Nightfall').click(); pg.wait_for_timeout(300); ok('series page (scoped Library) in session',pg.evaluate(TABST)['scoped'])
    pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(400); st=pg.evaluate(TABST); ok('reopen from a series page -> Home',home_ok(st),json.dumps(st))
    pg.evaluate("localStorage.setItem('cr.tab',JSON.stringify('library'))"); pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(400); st=pg.evaluate(TABST)
    ok('old saved last-tab ("library" from cr-v21) is ignored and cleared -> Home',home_ok(st) and st['saved'] is None,json.dumps(st))
    pg.goto(URL+'#/library'); pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(400); st=pg.evaluate(TABST); ok('unknown restored hash -> Home, hash cleared',home_ok(st) and st['hash']=='',json.dumps(st))
    pg.goto(URL+'#/read/no-such-comic'); pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_timeout(400); st=pg.evaluate(TABST); ok('stale reader hash (deleted comic) -> Home',home_ok(st) and st['hash']=='',json.dumps(st))
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(200); pg.evaluate("dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))"); pg.wait_for_timeout(300); st=pg.evaluate(TABST)
    ok('restore from the back-forward cache (pageshow persisted) -> Home',home_ok(st),json.dumps(st))
    pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(200); p3=ctx.new_page(); p3.goto(URL); p3.wait_for_selector('html[data-ready]'); p3.wait_for_timeout(600); st=p3.evaluate(TABST)
    ok('fresh open (new window, same storage) -> Home',home_ok(st),json.dumps(st)); p3.evaluate("document.querySelector('#homeScroll').scrollTop=0"); p3.wait_for_timeout(500)
    p3.screenshot(path=f'{SH}/{ENG}-v22-launch-home-ipad-portrait.png'); p3.close()
    pg.goto(URL); pg.wait_for_selector('html[data-ready]')
    open_comic(pg,'Panel Lab 01'); pg.evaluate('__cr.jumpTo(3)'); wait_render(pg); pg.wait_for_timeout(500); pg.reload(); pg.wait_for_selector('html[data-ready]'); pg.wait_for_selector('#reader:not(.hidden)'); wait_render(pg)
    ok('in-page reload while reading still resumes the comic (Home underneath)',pg.evaluate("__cr.R.comic.title==='Panel Lab 01'&&document.querySelector('#tabs .on').dataset.tab==='home'"))
    back(pg); st=pg.evaluate(TABST); ok('closing it then shows Home',home_ok(st),json.dumps(st))

    # ======== 5c. cr-v23: multi-select + Move to Series / Remove from Series ========
    def lib(): pg.click('#tabs [data-tab=library]'); pg.wait_for_timeout(200)
    SNAP="(t=>{const c=__cr.comics.find(x=>x.title===t); return {series:c.series||'',manual:!!c.seriesManual,progress:c.progress||0,page:c.page||0,panels:Object.keys(c.panels||{}).length,blackV:c.blackV||0,lists:__cr.queues.filter(q=>q.items.includes(c.id)).map(q=>q.name)}})"
    SELST="(()=>({on:__cr.series.SEL.on,n:__cr.series.SEL.ids.size,count:document.querySelector('#selCount').textContent,all:document.querySelector('#selAll').textContent,bar:!document.querySelector('#selBar').classList.contains('hidden'),checked:[...document.querySelectorAll('#libGrid .lc.on')].map(e=>e.dataset.title)}))()"
    lib(); pg.locator('.lc[data-title="Nightfall 01"]').click(button='right'); pg.click('#aQueue'); pg.wait_for_selector('#qaName'); pg.fill('#qaName','Crossover'); pg.click('#qaDone'); pg.wait_for_timeout(300)
    open_comic(pg,'Nightfall 01'); pg.evaluate('__cr.jumpTo(6)'); wait_render(pg); pg.wait_for_timeout(500); back(pg)
    pg.evaluate("(()=>{const c=__cr.comics.find(x=>x.title==='Iron Tide 02'); c.blackV=c.blackV||2; c.blackPages=[5];})()")
    before={t:pg.evaluate(SNAP,t) for t in ['Panel Lab 01','Nightfall 01','Iron Tide 02']}
    ok('home: no Select button (Library / series pages only)',not pg.is_visible('#selBtn') if pg.evaluate("document.querySelector('#tabs .on').dataset.tab")=='home' else (pg.click('#tabs [data-tab=home]') or not pg.is_visible('#selBtn')))
    lib(); bb=pg.locator('#selBtn').bounding_box(); ok('Library: Select button in the top bar, >=40px',pg.is_visible('#selBtn') and bb['height']>=40 and bb['width']>=40,json.dumps(bb))
    pg.click('#selBtn'); pg.wait_for_timeout(200); st=pg.evaluate(SELST); ok('Select enters selection mode (bar, "0 selected", Done)',st['on'] and st['bar'] and st['count']=='0 selected' and pg.text_content('#selBtn')=='Done',json.dumps(st))
    for t in ['Panel Lab 01','Nightfall 01','Iron Tide 02']: pg.locator(f'.lc[data-title="{t}"]').click()
    pg.wait_for_timeout(200); st=pg.evaluate(SELST); ok('tap covers to check them; count updates; no comic opens',st['n']==3 and st['count']=='3 selected' and pg.is_visible('#shelf') and set(st['checked'])=={'Panel Lab 01','Nightfall 01','Iron Tide 02'},json.dumps(st))
    pg.locator('.lc[data-title="Iron Tide 02"]').click(); ok('tap again unchecks',pg.evaluate(SELST)['n']==2); pg.locator('.lc[data-title="Iron Tide 02"]').click()
    pg.screenshot(path=f'{SH}/{ENG}-v23-selection-mode-ipad-portrait.png')
    sb=pg.evaluate("[...document.querySelectorAll('#selBar button')].map(b=>{const r=b.getBoundingClientRect(); return [r.width,r.height]})"); ok('selection bar buttons >=40px',all(w>=40 and h>=40 for w,h in sb),str(sb))
    bar_bg=pg.evaluate("getComputedStyle(document.querySelector('#selBar')).backgroundColor"); ok('selection bar is solid black',bar_bg=='rgb(0, 0, 0)',bar_bg)
    pg.click('#selAll'); st=pg.evaluate(SELST); ok('Select All selects every visible comic, label flips to Select None',st['n']==len(files) and st['all']=='Select None',json.dumps(st))
    pg.click('#selAll'); st=pg.evaluate(SELST); ok('Select None clears',st['n']==0 and st['all']=='Select All' and pg.is_disabled('#selMove'),json.dumps(st))
    for t in ['Panel Lab 01','Nightfall 01','Iron Tide 02']: pg.locator(f'.lc[data-title="{t}"]').click()
    pg.click('#selMove'); pg.wait_for_selector('#mvList'); ok('Move sheet lists existing series + New Series',pg.locator('#mvList input[name=mvs]').count()==len(pg.evaluate('__cr.series.counts()'))+1)
    pg.fill('#mvName','Uncanny Tests'); pg.fill('#mvVol','2'); pg.wait_for_timeout(150)
    ok('new series name + volume preview',pg.text_content('#mvPrev').startswith('→ “Uncanny Tests Vol. 2”') and pg.text_content('#mvGo')=='Move 3',pg.text_content('#mvPrev'))
    pg.screenshot(path=f'{SH}/{ENG}-v23-move-sheet-ipad-portrait.png')
    pg.click('#mvGo'); pg.wait_for_timeout(500)
    after={t:pg.evaluate(SNAP,t) for t in before}
    ok('moved: series set by hand on all three',all(after[t]['series']=='Uncanny Tests Vol. 2' and after[t]['manual'] for t in after),json.dumps(after))
    ok('moved issues keep progress, reading lists, blank-page + panel caches',all({k:v for k,v in after[t].items() if k not in('series','manual')}=={k:v for k,v in before[t].items() if k not in('series','manual')} for t in after),json.dumps([before,after]))
    ok('selection mode ends after the move',not pg.evaluate(SELST)['on'])
    pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(300); rows=pg.eval_on_selector_all('#homeScroll .row-h h2','e=>e.map(x=>x.textContent)')
    ok('Home: new series row appears',('Uncanny Tests Vol. 2' in rows),json.dumps(rows))
    pg.locator('.row-h',has_text='Uncanny Tests Vol. 2').click(); pg.wait_for_timeout(400)
    cf=pg.evaluate("__cr.SCF.items.map(c=>c.title)"); ok('series page carousel in issue order (ties by title)',cf==['Nightfall 01','Panel Lab 01','Iron Tide 02'],json.dumps(cf))
    # series page: select all -> move the rest of Iron Tide here; the emptied source disappears
    pg.click('#tabs [data-tab=home]'); pg.locator('.row-h',has_text='Iron Tide').click(); pg.wait_for_timeout(300)
    ok('series page has Select',pg.is_visible('#selBtn')); pg.click('#selBtn'); pg.click('#selAll'); ok('series page: Select All = that series only',pg.evaluate(SELST)['n']==1)
    pg.click('#selMove'); pg.wait_for_selector('#mvList'); i=pg.evaluate("[...document.querySelectorAll('#mvList .mvr b')].findIndex(b=>b.textContent==='Uncanny Tests Vol. 2')"); pg.locator('#mvList input[name=mvs]').nth(i).check(); pg.click('#mvGo'); pg.wait_for_timeout(500)
    st=pg.evaluate("({series:__cr.series.counts(),scope:document.querySelector('#shelf').classList.contains('scoped'),cards:[...document.querySelectorAll('#libGrid .lc')].map(e=>e.dataset.title)})")
    ok('empty source series disappears; the page follows its comics to the destination',not any(s0=='Iron Tide' for s0,_ in st['series']) and st['scope'] and len(st['cards'])==4,json.dumps(st))
    pg.click('#tabs [data-tab=home]'); pg.wait_for_timeout(200); ok('Home: Iron Tide row gone','Iron Tide' not in pg.eval_on_selector_all('#homeScroll .row-h h2','e=>e.map(x=>x.textContent)'))
    # rename integrates: the manual series follows the new name
    pg.locator('.row-top',has_text='Uncanny Tests Vol. 2').locator('.row-more').click(); pg.click('#smRename'); pg.fill('#srName','Uncanny Tests Vol. 3'); pg.click('#srSave'); pg.wait_for_timeout(400)
    ov=pg.evaluate("__cr.series.ov()"); ok('Rename keeps them manual and updates the saved override',set(ov.values())=={'Uncanny Tests Vol. 3'} and pg.evaluate(SNAP,'Iron Tide 01')['series']=='Uncanny Tests Vol. 3',json.dumps(ov))
    # re-import / Drive re-sync keeps the manual series
    lib(); pg.locator('.lc[data-title="Iron Tide 02"]').click(button='right'); pg.click('#aDelete'); pg.click('#confirmOk'); pg.wait_for_timeout(400)
    pg.set_input_files('#fileIn',[os.path.join(T,'Iron_Tide_02.pdf')]); pg.wait_for_function(f'document.querySelectorAll(".lc").length=={len(files)} && !document.querySelector(".toast .tb")',timeout=60000); pg.wait_for_timeout(300)
    r2=pg.evaluate(SNAP,'Iron Tide 02'); ok('re-imported file keeps its manual series (not re-grouped by file name)',r2['series']=='Uncanny Tests Vol. 3' and r2['manual'],json.dumps(r2))
    dr=pg.evaluate("(()=>{const r=__cr.series.override({driveId:'drv-x',fileName:'Iron_Tide_01.pdf',size:__cr.comics.find(c=>c.title==='Iron Tide 01').size,series:'Iron Tide'}); return [r.series,r.autoSeries,!!r.seriesManual]})()")
    ok('Drive import of the same file keeps the manual series',dr==['Uncanny Tests Vol. 3','Iron Tide',True],json.dumps(dr))
    # remove from series -> back to automatic grouping
    pg.click('#selBtn'); pg.locator('.lc[data-title="Iron Tide 01"]').click(); pg.locator('.lc[data-title="Iron Tide 02"]').click(); pg.click('#selRemove'); pg.wait_for_timeout(400)
    r3=pg.evaluate(SNAP,'Iron Tide 01'); ok('Remove from Series -> automatic series again (Iron Tide), override dropped',r3['series']=='Iron Tide' and not r3['manual'] and not any(k.startswith('f:Iron_Tide_01') for k in pg.evaluate('__cr.series.ov()')),json.dumps(r3))
    pg.click('#selBtn'); pg.locator('.lc[data-title="Nightfall 02"]').click(); ok('tabs, + and settings are hidden while selecting',not pg.is_visible('#tabs') and not pg.is_visible('#importBtn'))
    pg.click('#selBtn'); pg.wait_for_timeout(200); ok('Done leaves selection mode, nothing changed',not pg.evaluate(SELST)['on'] and pg.is_visible('#tabs') and pg.evaluate(SNAP,'Nightfall 02')['series']=='Nightfall')
    # persisted
    pg.reload(); pg.wait_for_selector('html[data-ready]'); ok('series changes persisted in IndexedDB',pg.evaluate(SNAP,'Panel Lab 01')['series']=='Uncanny Tests Vol. 3' and pg.evaluate(SNAP,'Iron Tide 01')['series']=='Iron Tide')

    # ======== 6. phones (standalone insets) ========
    for (w,h,lab) in [(390,844,'iphone-390'),(430,932,'iphone-430')]:
        c2=b.new_context(viewport={'width':w,'height':h},has_touch=True,device_scale_factor=3,is_mobile=(ENG=='chromium'))
        c2.add_init_script("window.__crNoScan=true; document.addEventListener('DOMContentLoaded',()=>{document.documentElement.style.setProperty('--sat','47px');document.documentElement.style.setProperty('--sab','34px')})")
        p2=c2.new_page(); p2.goto(URL); p2.wait_for_selector('html[data-ready]'); p2.set_input_files('#fileIn',[files[0]]); p2.wait_for_function('document.querySelectorAll(".lc").length==1 && !document.querySelector(".toast .tb")',timeout=60000)
        pg_=pg; pg=p2; open_comic(pg,'Panel Lab 01'); pg.evaluate('__cr.jumpTo(2)'); wait_render(pg); pg.evaluate('__cr.toggleUI(false)'); pg.wait_for_timeout(300)
        s=enter(pg,2); ok(f'{lab}: panel view',s['on'] and s['i']==2,json.dumps(s)); fits(s,lab)
        ok(f'{lab}: Full Page button >=40px, clear of the home indicator',s['btn'] and s['btn']['h']>=40 and s['btn']['bottom']>=34,json.dumps(s['btn']))
        top=Image.open(io.BytesIO(pg.screenshot(clip={'x':0,'y':0,'width':w,'height':47}))).convert('RGB'); mx=max(max(px) for px in top.get_flattened_data())
        ok(f'{lab}: nothing under the status bar in panel view',mx<=2,f'maxpx={mx}')
        pg.wait_for_timeout(300); pg.screenshot(path=f'{SH}/{ENG}-v21-panel-{lab}.png')
        pg.evaluate('__cr.panels.exit(false)'); back(pg); pg.click('#tabs [data-tab=library]'); pg.click('#selBtn'); pg.locator('.lc').first.click(); pg.wait_for_timeout(200)
        fit=pg.evaluate("(()=>{const b=document.querySelector('#selBar .sb-row'), r=document.querySelector('#selBar').getBoundingClientRect(); return {sw:b.scrollWidth,cw:b.clientWidth,bottom:innerHeight-r.bottom,btn:Math.min(...[...b.querySelectorAll('button')].map(x=>x.getBoundingClientRect().height))}})()")
        ok(f'{lab}: selection bar fits, buttons >=40px',fit['sw']<=fit['cw']+1 and fit['btn']>=40 and fit['bottom']<=1,json.dumps(fit)); pg.screenshot(path=f'{SH}/{ENG}-v23-selection-{lab}.png')
        pg=pg_; c2.close()

    ok('no page errors',not errors,json.dumps(errors[:5]))
    b.close()
print(f'\n{sum(res)}/{len(res)} passed [{ENG}]')
sys.exit(0 if all(res) else 1)
