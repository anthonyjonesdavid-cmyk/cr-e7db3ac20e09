"""Generate original test comics (no real artwork). Output: ../testpdfs/ (git-ignored)."""
import os, io, random, math, sys
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.utils import ImageReader
OUT = os.path.join(os.path.dirname(__file__), '..', 'testpdfs'); os.makedirs(OUT, exist_ok=True)
PAL = ['#E63946','#F4A261','#2A9D8F','#264653','#E9C46A','#8338EC','#3A86FF','#FB5607','#06D6A0','#FF006E']
W, H = 663, 1019  # standard US comic trim ratio (6.625x10.1875in)

def burst(c, cx, cy, r1, r2, n, col):
    p = c.beginPath()
    for i in range(n*2):
        a = math.pi*i/n; r = r1 if i%2==0 else r2
        x, y = cx+r*math.cos(a), cy+r*math.sin(a)
        (p.moveTo if i==0 else p.lineTo)(x, y)
    p.close(); c.setFillColor(HexColor(col)); c.setStrokeColor(black); c.setLineWidth(4); c.drawPath(p, fill=1, stroke=1)

def page(c, i, n, title, rnd, img=None):
    bg = PAL[i % len(PAL)]
    c.setFillColor(HexColor(bg)); c.rect(0, 0, W, H, fill=1, stroke=0)
    if img is not None:
        c.drawImage(img, 0, 0, W, H)
    # halftone dots
    c.setFillColor(HexColor('#00000022'))
    for y in range(0, H, 22):
        for x in range(0, W, 22):
            c.circle(x + (11 if (y//22)%2 else 0), y, 3.2, fill=1, stroke=0)
    # panels
    c.setLineWidth(6); c.setStrokeColor(black); c.setFillColor(white)
    m = 26
    c.rect(m, H*0.62, W-2*m, H*0.38-m, fill=1, stroke=1)
    c.rect(m, H*0.30, W/2-m-8, H*0.30, fill=1, stroke=1)
    c.rect(W/2+8, H*0.30, W/2-m-8, H*0.30, fill=1, stroke=1)
    if i == 0:
        burst(c, W/2, H*0.5, 300, 210, 14, '#FFD60A')
        c.setFillColor(black); c.setFont('Helvetica-Bold', 58)
        c.drawCentredString(W/2, H*0.53, title.upper()[:16])
        c.setFont('Helvetica-Bold', 30); c.drawCentredString(W/2, H*0.46, 'ISSUE #%d · %d PAGES' % (rnd.randint(1, 99), n))
    else:
        burst(c, W*0.72, H*0.8, 120, 80, 11, PAL[(i+3) % len(PAL)])
        c.setFillColor(black); c.setFont('Helvetica-Bold', 230)
        c.drawCentredString(W/2, H*0.36, str(i+1))
        c.setFont('Helvetica-Bold', 26)
        c.drawString(m+16, H*0.62+20, f'{title} — page {i+1} of {n}')
        c.setFont('Helvetica-Bold', 40); c.drawCentredString(W*0.72, H*0.79, ['POW!','ZAP!','BAM!','WHOOSH','KRAK!'][i % 5])
        # speech bubble
        c.setFillColor(white); c.setLineWidth(4); c.ellipse(m+30, H*0.80, m+300, H*0.95, fill=1, stroke=1)
        c.setFillColor(black); c.setFont('Helvetica', 20); c.drawString(m+60, H*0.87, 'Turn the page!' if i % 2 else 'Meanwhile...')
    # page number band at bottom
    c.setFillColor(black); c.rect(0, 0, W, 64, fill=1, stroke=0)
    c.setFillColor(white); c.setFont('Helvetica-Bold', 36); c.drawCentredString(W/2, 18, f'{i+1} / {n}')
    c.showPage()

def make(name, title, n, big=False, seed=1):
    rnd = random.Random(seed)
    c = canvas.Canvas(os.path.join(OUT, name), pagesize=(W, H)); c.setTitle(title)
    for i in range(n):
        img = None
        if big:
            from PIL import Image
            # a fresh noisy high-res raster per page so the file is genuinely large (~0.5MB/page)
            im = Image.frombytes('RGB', (1500, 2300), os.urandom(1500*2300*3)).resize((1500, 2300))
            tint = Image.new('RGB', im.size, PAL[i % len(PAL)])
            im = Image.blend(im, tint, 0.78)
            b = io.BytesIO(); im.save(b, 'JPEG', quality=72); b.seek(0); img = ImageReader(b)
        page(c, i, n, title, rnd, img)
    c.save(); print(name, os.path.getsize(os.path.join(OUT, name))//1024, 'KB')

if __name__ == '__main__':
    make('Captain_Comet_01.pdf', 'Captain Comet', 32, seed=1)
    make('Captain_Comet_02.pdf', 'Captain Comet 2', 36, seed=2)
    make('Night_Owl_Tales.pdf', 'Night Owl Tales', 48, seed=3)
    make('Robo_Pals_Manga.pdf', 'Robo Pals', 40, seed=4)
    if '--nobig' not in sys.argv:
        make('Mega_Omnibus_Big.pdf', 'Mega Omnibus', 220, big=True, seed=5)
