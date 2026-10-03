"""Generate ORIGINAL test comics (painted-style covers, no real characters/logos/publisher marks).
Output: ../testpdfs/ (git-ignored).  Usage: python3 test/gen_pdfs.py [--big] | --drive"""
import os, io, sys, math, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor, white, black, Color
OUT = os.path.join(os.path.dirname(__file__), '..', 'testpdfs'); os.makedirs(OUT, exist_ok=True)
G = '/usr/share/fonts/truetype/sand-box/google/'
F = {'anton': G+'Anton/Anton-Regular.ttf', 'bebas': G+'Bebas Neue/BebasNeue-Regular.ttf', 'barlow': G+'Barlow Condensed/BarlowCondensed-SemiBold.ttf',
     'barlowb': G+'Barlow Condensed/BarlowCondensed-Black.ttf', 'staat': G+'Staatliches/Staatliches-Regular.ttf', 'jp': '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf'}
W, H = 663, 1019          # US comic trim ratio (points)
CW, CH = 1000, 1537       # cover raster

def font(k, s):
    try: return ImageFont.truetype(F[k], s)
    except Exception: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', s)
def lerp(a, b, t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
def hexrgb(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))

def gradient(w, h, top, bot):
    im = Image.new('RGB', (w, h)); d = ImageDraw.Draw(im)
    for y in range(h): d.line([(0,y),(w,y)], fill=lerp(top, bot, (y/h)**1.2))
    return im
def glow(im, cx, cy, r, col, alpha=200):
    lay = Image.new('RGBA', im.size, (0,0,0,0)); d = ImageDraw.Draw(lay)
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=col+(alpha,))
    lay = lay.filter(ImageFilter.GaussianBlur(r*0.6)); im.paste(lay, (0,0), lay)
def brush(im, rnd, cols, n=60):
    lay = Image.new('RGBA', im.size, (0,0,0,0)); d = ImageDraw.Draw(lay)
    for _ in range(n):
        x, y = rnd.randint(-100, im.width), rnd.randint(-100, im.height); w, h = rnd.randint(80, 420), rnd.randint(20, 110)
        d.ellipse([x, y, x+w, y+h], fill=rnd.choice(cols)+(rnd.randint(18, 60),))
    lay = lay.filter(ImageFilter.GaussianBlur(18)); im.paste(lay, (0,0), lay)
def grain(im, rnd, amt=18):
    n = Image.effect_noise(im.size, amt).convert('RGB'); return ImageChops.overlay(im, Image.blend(Image.new('RGB', im.size, (128,128,128)), n, .5))
def skyline(d, rnd, base, col, w, hmin, hmax, step=(30,90)):
    x = -10
    while x < w:
        bw = rnd.randint(*step); bh = rnd.randint(hmin, hmax); d.rectangle([x, base-bh, x+bw, base+400], fill=col)
        if rnd.random() < .3: d.rectangle([x+bw//2-2, base-bh-rnd.randint(20,70), x+bw//2+2, base-bh], fill=col)
        x += bw - rnd.randint(0, 8)
def windows(d, rnd, base, w, col, n=140):
    for _ in range(n):
        x, y = rnd.randint(0, w), base - rnd.randint(10, 380); d.rectangle([x, y, x+5, y+8], fill=col)
def figure(d, cx, base, s, col, cape=True, sword=False):
    d.ellipse([cx-18*s, base-230*s, cx+18*s, base-192*s], fill=col)                          # head
    body = [(cx-30*s, base-190*s), (cx+30*s, base-190*s), (cx+38*s, base-95*s), (cx+22*s, base), (cx+6*s, base), (cx, base-80*s), (cx-6*s, base), (cx-22*s, base), (cx-38*s, base-95*s)]
    d.polygon(body, fill=col)
    if cape: d.polygon([(cx-30*s, base-188*s), (cx-120*s, base+10*s), (cx-20*s, base-20*s)], fill=col); d.polygon([(cx+30*s, base-188*s), (cx+110*s, base+5*s), (cx+20*s, base-20*s)], fill=col)
    if sword: d.line([(cx+30*s, base-120*s), (cx+170*s, base-330*s)], fill=col, width=int(7*s))

SERIES = {
 'Nightfall':      dict(top='#06121f', bot='#1d3b57', glowc='#d9e6f2', accent='#e8f1f8', title='#f2f5f7', font='anton', motif='city', tag='THE CITY NEVER SLEEPS. NEITHER DOES SHE.', jp=False),
 'Iron Tide':      dict(top='#2a0c06', bot='#e0662a', glowc='#ffd08a', accent='#ffb347', title='#fff3e0', font='bebas', motif='sea', tag='WHEN THE OCEAN RISES, STEEL ANSWERS.', jp=False),
 'Starlight Ronin':dict(top='#12052a', bot='#7a1f6e', glowc='#ff9ed8', accent='#ff6fb5', title='#ffffff', font='staat', motif='ronin', tag='ONE BLADE. TEN THOUSAND STARS.', jp=True),
 'The Hollow':     dict(top='#0d1210', bot='#4b5a4e', glowc='#f6e7b0', accent='#f2d27a', title='#e9efe6', font='barlowb', motif='forest', tag='SOMETHING IS LISTENING IN THE TREES.', jp=False),
 'Glass Harbor':   dict(top='#04161a', bot='#3e8e8a', glowc='#c8fff4', accent='#7ff0dd', title='#f0fffb', font='anton', motif='sea2', tag='A ONE-SHOT', jp=False),
 'Ember Road':     dict(top='#1a0905', bot='#c2412b', glowc='#ffc58a', accent='#ff8a4c', title='#fff1e6', font='anton', motif='sea2', tag='THE LAST CARAVAN HEADS WEST.', jp=False),
 'Twin Moon':      dict(top='#050d1c', bot='#3a5fa0', glowc='#e8f0ff', accent='#9fc3ff', title='#f4f8ff', font='bebas', motif='city', tag='TWO MOONS. ONE NIGHT LEFT.', jp=False),
 'Atlas Omnibus':  dict(top='#120d05', bot='#8a6a2c', glowc='#ffe7a6', accent='#ffd166', title='#fff8e6', font='bebas', motif='city', tag='THE COMPLETE SAGA', jp=False),
}
NAMES = ['M. Okafor','R. Lindqvist','J. Moreau','S. Takeda','A. Varga','L. Castellanos','K. Whitfield','D. Achterberg']

def cover(series, issue, label, rnd):
    S = SERIES[series]; top, bot, gc, ac = map(hexrgb, (S['top'], S['bot'], S['glowc'], S['accent']))
    tints = [(200,60,60),(60,120,200),(220,160,60),(120,60,180),(40,160,120),(200,90,150)]
    tint = tints[issue % len(tints)]; bot = lerp(bot, tint, .35); gc = lerp(gc, tint, .25)
    im = gradient(CW, CH, top, bot); brush(im, rnd, [gc, bot, top, ac], 70)
    m = S['motif']; d = ImageDraw.Draw(im)
    dark = lerp(top, (0,0,0), .55)
    if m == 'city':
        glow(im, rnd.randint(300, 700), rnd.randint(380, 560), 230, gc, 230); d = ImageDraw.Draw(im)
        d.ellipse([CW*.5-120+rnd.randint(-120,120)]*1+[0,0,0], fill=None) if False else None
        skyline(d, rnd, 1240, lerp(top, bot, .35), CW, 200, 520); windows(d, rnd, 1240, CW, lerp(gc, (255,255,255), .3))
        skyline(d, rnd, 1360, dark, CW, 120, 300, (60, 140))
        figure(d, rnd.randint(380, 620), 1262, 1.35, (5, 6, 9))
        rain = Image.new('RGBA', im.size, (0,0,0,0)); rd = ImageDraw.Draw(rain)
        for _ in range(500): x, y = rnd.randint(0, CW), rnd.randint(0, CH); rd.line([(x, y), (x-12, y+46)], fill=(210, 225, 240, 55), width=2)
        im.paste(rain, (0,0), rain)
    elif m in ('sea', 'sea2'):
        hz = 900 + rnd.randint(-60, 60); glow(im, rnd.randint(350, 650), hz-40, 260, gc, 255); d = ImageDraw.Draw(im)
        if m == 'sea':  # colossal machine silhouette
            cx = rnd.randint(380, 620); mc = lerp(top, (0,0,0), .35)
            d.polygon([(cx-170, hz-470), (cx+170, hz-470), (cx+110, hz-180), (cx-110, hz-180)], fill=mc)          # torso
            d.rectangle([cx-95, hz-200, cx+95, hz+40], fill=mc)                                                    # hips into the sea
            d.polygon([(cx-60, hz-470), (cx+60, hz-470), (cx+48, hz-560), (cx-48, hz-560)], fill=mc)               # head
            d.rectangle([cx-38, hz-530, cx+38, hz-518], fill=ac)                                                   # visor glow
            d.polygon([(cx-170, hz-470), (cx-250, hz-430), (cx-275, hz-200), (cx-225, hz-120), (cx-205, hz-210), (cx-200, hz-420)], fill=mc)
            d.polygon([(cx+170, hz-470), (cx+250, hz-430), (cx+275, hz-200), (cx+225, hz-120), (cx+205, hz-210), (cx+200, hz-420)], fill=mc)
            for k in range(4): d.line([(cx-120+k*80, hz-440), (cx-100+k*66, hz-230)], fill=lerp(mc, ac, .25), width=3)
        else:
            for i in range(5): x = 150+i*180+rnd.randint(-30,30); d.polygon([(x, hz), (x+30, hz-rnd.randint(120,300)), (x+60, hz)], fill=lerp(top,(0,0,0),.2))
        for y in range(hz, CH, 6):
            t = (y-hz)/(CH-hz); d.line([(0, y), (CW, y)], fill=lerp(lerp(bot, top, .5), top, t), width=6)
        for _ in range(260): x, y = rnd.randint(0, CW), rnd.randint(hz, CH); d.line([(x, y), (x+rnd.randint(20, 90), y)], fill=lerp(gc, bot, rnd.random()), width=2)
        figure(d, rnd.randint(250, 750), CH-110, .9, (4, 4, 6), cape=False)
    elif m == 'ronin':
        for _ in range(260): x, y, r = rnd.randint(0, CW), rnd.randint(0, 1000), rnd.choice([1, 1, 2, 3]); d.ellipse([x-r, y-r, x+r, y+r], fill=(255, 240, 255))
        glow(im, rnd.randint(250, 750), 520, 300, gc, 150); d = ImageDraw.Draw(im)
        d.polygon([(0, 1230), (320, 1080), (620, 1190), (CW, 1050), (CW, CH), (0, CH)], fill=lerp(top, (0,0,0), .4))
        figure(d, rnd.randint(380, 600), 1160, 1.45, (8, 3, 14), cape=True, sword=True)
        for _ in range(90): x, y = rnd.randint(0, CW), rnd.randint(0, CH); d.ellipse([x, y, x+12, y+7], fill=(255, 170, 210))
    elif m == 'forest':
        glow(im, rnd.randint(300, 700), 1050, 120, gc, 255); d = ImageDraw.Draw(im)
        for layer, col in enumerate([lerp(bot, top, .3), lerp(bot, top, .6), (8, 10, 9)]):
            for _ in range(7 + layer*2):
                x = rnd.randint(-40, CW); w = rnd.randint(18, 50) + layer*12; d.rectangle([x, 0, x+w, CH], fill=col)
                for k in range(4): yy = rnd.randint(100, 900); d.line([(x+w//2, yy), (x+w//2+rnd.choice([-1,1])*rnd.randint(80, 220), yy-rnd.randint(60, 200))], fill=col, width=max(4, w//4))
            fog = Image.new('RGBA', im.size, gc+(0,)); fd = ImageDraw.Draw(fog); fd.rectangle([0, 900, CW, CH], fill=lerp(bot, gc, .3)+(60,)); fog = fog.filter(ImageFilter.GaussianBlur(60)); im.paste(fog, (0,0), fog); d = ImageDraw.Draw(im)
        figure(d, rnd.randint(380, 620), 1250, 1.1, (6, 7, 6), cape=False); d.ellipse([CW//2-20, 1080, CW//2+20, 1120], fill=None)
    im = grain(im, rnd, 22)
    # vignette
    v = Image.new('L', im.size, 0); vd = ImageDraw.Draw(v); vd.ellipse([-260, -200, CW+260, CH+260], fill=255); v = v.filter(ImageFilter.GaussianBlur(160))
    im = Image.composite(im, Image.new('RGB', im.size, (0,0,0)), v)
    d = ImageDraw.Draw(im)
    # typography
    title = series.upper(); f = font(S['font'], 210 if len(title) <= 10 else 150)
    tw = d.textlength(title, font=f)
    if tw > CW-80: f = font(S['font'], int(f.size*(CW-80)/tw)); tw = d.textlength(title, font=f)
    shadow = Image.new('RGBA', im.size, (0,0,0,0)); sd = ImageDraw.Draw(shadow); sd.text(((CW-tw)/2+6, 96), title, font=f, fill=(0,0,0,170)); shadow = shadow.filter(ImageFilter.GaussianBlur(8)); im.paste(shadow, (0,0), shadow); d = ImageDraw.Draw(im)
    d.text(((CW-tw)/2, 90), title, font=f, fill=hexrgb(S['title']))
    tb = d.textbbox(((CW-tw)/2, 90), title, font=f)
    fs = font('barlow', 34); d.text((CW/2, tb[3]+26), S['tag'], font=fs, fill=ac, anchor='ma')
    fi = font('barlowb', 64); d.text((48, 40), label, font=fi, fill=hexrgb(S['title']))
    if S['jp']:
        fj = font('jp', 52); y = 420
        for ch in 'スターライト浪人': d.text((CW-70, y), ch, font=fj, fill=(255, 220, 240)); y += 60
    fc = font('barlow', 30); d.text((CW/2, CH-62), f"{rnd.choice(NAMES).upper()}  ·  {rnd.choice(NAMES).upper()}", font=fc, fill=(230, 230, 230), anchor='ma')
    b = io.BytesIO(); im.save(b, 'JPEG', quality=86); b.seek(0); return ImageReader(b)

def interior(c, i, n, series, rnd, img=None):
    S = SERIES[series]; top, bot, ac = HexColor(S['top']), HexColor(S['bot']), HexColor(S['accent'])
    c.setFillColor(HexColor('#f4f1ea')); c.rect(0, 0, W, H, fill=1, stroke=0)
    if img is not None: c.drawImage(img, 0, 0, W, H)
    m, g = 30, 14; rows = rnd.choice([[1, 2, 1], [2, 1, 2], [1, 1, 2], [2, 2]])
    ph = (H - 2*m - 70 - g*(len(rows)-1)) / len(rows); y = H - m
    for r in rows:
        pw = (W - 2*m - g*(r-1)) / r
        for k in range(r):
            x = m + k*(pw+g); c.saveState(); p = c.beginPath(); p.rect(x, y-ph, pw, ph); c.clipPath(p, stroke=0)
            c.linearGradient(x, y, x, y-ph, (top, bot), extend=True)
            c.setFillColor(Color(0, 0, 0, .55)); bx = x
            while bx < x+pw: bh = rnd.uniform(.15, .6)*ph; c.rect(bx, y-ph, rnd.uniform(14, 40), bh, fill=1, stroke=0); bx += rnd.uniform(16, 44)
            c.restoreState(); c.setStrokeColor(black); c.setLineWidth(3); c.rect(x, y-ph, pw, ph, fill=0, stroke=1)
        y -= ph + g
    c.setFillColor(white); c.setStrokeColor(black); c.setLineWidth(2); c.rect(m+12, H-m-58, 250, 44, fill=1, stroke=1)
    c.setFillColor(black); c.setFont('Helvetica-Oblique', 15); c.drawString(m+22, H-m-42, f'{series.upper()} — page {i+1}')
    c.setFillColor(white); c.setFont('Helvetica-Bold', 190); c.drawCentredString(W/2, H*0.42, str(i+1))
    c.setFillColor(black); c.setFont('Helvetica-Bold', 30); c.drawCentredString(W/2, 24, f'{i+1} / {n}')
    c.showPage()

def make(fname, series, label, n, seed, big=False, wide=None):
    rnd = random.Random(seed); c = canvas.Canvas(os.path.join(OUT, fname), pagesize=(W, H)); c.setTitle(f'{series} {label}')
    if wide is not None:
        # scanner-style first page: two-page spread, black back cover on the left (tiny legal line), cover on the right,
        # optional black letterbox bands top/bottom
        band = wide; c.setPageSize((2*W, H+2*band)); c.setFillColor(black); c.rect(0, 0, 2*W, H+2*band, fill=1, stroke=0)
        c.setFillColor(HexColor('#5a5a5a')); c.setFont('Helvetica', 6); c.drawCentredString(W/2, band+26, f'{series.upper()} {label} · ALL CHARACTERS FICTIONAL · TEST FIXTURE · PRINTED NOWHERE')
        c.drawImage(cover(series, seed, label, rnd), W, band, W, H); c.showPage(); c.setPageSize((W, H))
    else:
        c.drawImage(cover(series, seed, label, rnd), 0, 0, W, H); c.showPage()
    for i in range(1, n):
        img = None
        if big:
            im = Image.frombytes('RGB', (1500, 2300), os.urandom(1500*2300*3)); im = Image.blend(im, Image.new('RGB', im.size, SERIES[series]['bot']), .8)
            b = io.BytesIO(); im.save(b, 'JPEG', quality=72); b.seek(0); img = ImageReader(b)
        interior(c, i, n, series, rnd, img)
    c.save(); print(fname, os.path.getsize(os.path.join(OUT, fname))//1024, 'KB', flush=True)

def make_wide(fname, series, label, sheets, seed):
    # scanner-style: every PDF page is a wide sheet holding two comic pages side by side (cover sheet: black back cover + cover)
    make_path = os.path.join(OUT, fname); rnd = random.Random(seed); c = canvas.Canvas(make_path, pagesize=(2*W, H)); c.setTitle(f'{series} {label}')
    c.setFillColor(black); c.rect(0, 0, 2*W, H, fill=1, stroke=0); c.setFillColor(HexColor('#5a5a5a')); c.setFont('Helvetica', 6)
    c.drawCentredString(W/2, 26, f'{series.upper()} {label} · ORIGINAL TEST FIXTURE'); c.drawImage(cover(series, seed, label, rnd), W, 0, W, H); c.showPage()
    real = c.showPage; n = 1 + sheets*2
    for k in range(sheets):
        c.setPageSize((2*W, H))
        for half in (0, 1):
            c.saveState(); c.translate(half*W, 0); c.showPage = lambda: None
            interior(c, 1 + k*2 + half, n, series, rnd, None); c.showPage = real; c.restoreState()
        c.setStrokeColor(HexColor('#00000033')); c.setLineWidth(1); c.line(W, 0, W, H)   # gutter
        c.showPage()
    c.save(); print(fname, os.path.getsize(make_path)//1024, 'KB', flush=True)

def drive_fixtures():
    # served by the throttled mock-Drive server in e2e.py: a multi-chunk (~22 MB) PDF + a broken "PDF"
    global OUT
    d = os.path.join(OUT, 'drive'); os.makedirs(d, exist_ok=True); old, OUT = OUT, d
    try:
        if not os.path.exists(os.path.join(d, 'Drive_Annual.pdf')): make('Drive_Annual.pdf', 'Atlas Omnibus', 'ANNUAL', 30, 21, big=True)
        open(os.path.join(d, 'Broken.pdf'), 'wb').write(b'this is not a pdf\n' * 5000)
    finally: OUT = old

if __name__ == '__main__' and '--drive' in sys.argv: drive_fixtures(); sys.exit(0)
if __name__ == '__main__':
    for f in os.listdir(OUT):
        if f.endswith('.pdf') and (f != 'Atlas_Omnibus.pdf' or '--big' in sys.argv): os.remove(os.path.join(OUT, f))
    plan = [('Nightfall', 5, '#{:02d}', 'Nightfall_{:02d}.pdf', 32), ('Iron Tide', 5, '#{:d}', 'Iron_Tide_{:02d}.pdf', 30),
            ('Starlight Ronin', 4, 'VOL. {:d}', 'Starlight_Ronin_v{:02d}.pdf', 44), ('The Hollow', 3, '#{:d}', 'The_Hollow_{:02d}.pdf', 36)]
    seed = 10
    for series, count, lab, fn, pages in plan:
        for k in range(1, count+1): seed += 1; make(fn.format(k), series, lab.format(k), pages + (k % 3)*4, seed)
    make('Glass_Harbor.pdf', 'Glass Harbor', 'ONE-SHOT', 40, 99)
    # wide two-page-spread first pages (black left half) — with/without letterbox bands
    for k, band in [(1, 70), (2, 0), (3, 110)]: make(f'Ember_Road_{k:02d}.pdf', 'Ember Road', f'#{k}', 28, 60+k, wide=band)
    # every page a two-page spread scan -> "fold in middle" page turns
    for k in (1, 2): make_wide(f'Twin_Moon_{k:02d}.pdf', 'Twin Moon', f'#{k}', 12, 80+k)
    if '--big' in sys.argv: make('Atlas_Omnibus.pdf', 'Atlas Omnibus', 'COMPLETE', 220, 7, big=True)
