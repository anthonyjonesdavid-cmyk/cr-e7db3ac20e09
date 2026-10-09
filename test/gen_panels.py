"""ORIGINAL panel-layout test comics for guided panel view (abstract shapes only; no characters, logos or publisher marks).
Writes testpdfs/panels/Panel_Lab_01.pdf (portrait pages), Panel_Lab_02.pdf (two-page spread scans) and truth.json (expected boxes,
fractions of the page, top-left origin, in reading order; null = no gutters -> page thirds)."""
import os, json, random
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color, black, white
OUT = os.path.join(os.path.dirname(__file__), '..', 'testpdfs', 'panels'); os.makedirs(OUT, exist_ok=True)
W, H = 663, 1019; M, G = 30, 14
PAL = [('#1d3557', '#457b9d'), ('#6a040f', '#e85d04'), ('#283618', '#606c38'), ('#3c096c', '#9d4edd'), ('#003049', '#2a9d8f'), ('#5f0f40', '#fb8b24')]

def art(c, x, y, w, h, rnd, label):
    """x,y = top-left in page coords (points, y down)"""
    top, bot = rnd.choice(PAL); Y = H - y
    c.saveState(); p = c.beginPath(); p.rect(x, Y - h, w, h); c.clipPath(p, stroke=0)
    c.linearGradient(x, Y, x, Y - h, (HexColor(top), HexColor(bot)), extend=True)
    for _ in range(7):   # hills / discs / slabs
        k = rnd.random(); c.setFillColor(Color(rnd.random()*.3, rnd.random()*.3, rnd.random()*.4, .55))
        if k < .4: c.circle(x + rnd.uniform(0, w), Y - h + rnd.uniform(0, h), rnd.uniform(12, min(w, h)*.35), fill=1, stroke=0)
        else: c.rect(x + rnd.uniform(-20, w), Y - h, rnd.uniform(18, 60), rnd.uniform(.15, .7)*h, fill=1, stroke=0)
    c.setFillColor(HexColor('#fff8e7')); c.setStrokeColor(black); c.setLineWidth(1.5)
    bw = min(w - 20, 210); c.rect(x + 10, Y - 40, bw, 28, fill=1, stroke=1)
    c.setFillColor(black); c.setFont('Helvetica-Bold', 11); c.drawString(x + 18, Y - 30, label)
    c.restoreState(); c.setStrokeColor(black); c.setLineWidth(3); c.rect(x, Y - h, w, h, fill=0, stroke=1)

def page(c, rows, rnd, n, dark=False, rtl=False, ox=0, pw=W):
    """rows: list of lists of column weights. Returns truth boxes (fractions of the pw x H page) in reading order."""
    c.setFillColor(black if dark else HexColor('#f4f1ea')); c.rect(ox, 0, pw, H, fill=1, stroke=0)
    avail = H - 2*M - 40 - G*(len(rows)-1); rh = avail/len(rows); y = M; out = []; k = 0
    for r in rows:
        tw = pw - 2*M - G*(len(r)-1); x = M; boxes = []
        for wt in r:
            w = tw*wt/sum(r); k += 1; art(c, ox + x, y, w, rh, rnd, f'PANEL {k}  ·  TEST TEXT Aa'); boxes.append([x/pw, y/H, w/pw, rh/H]); x += w + G
        out += (boxes[::-1] if rtl else boxes); y += rh + G
    c.setFillColor(white if dark else black); c.setFont('Helvetica', 9); c.drawCentredString(ox + pw/2, 16, f'page {n}')
    # relabel in reading order isn't needed for detection; return truth
    return out

def splash(c, rnd, ox=0, pw=W):
    top, bot = rnd.choice(PAL); c.linearGradient(ox, H, ox, 0, (HexColor(top), HexColor(bot)), extend=True)
    for _ in range(14): c.setFillColor(Color(rnd.random(), rnd.random()*.6, rnd.random(), .4)); c.circle(ox + rnd.uniform(0, pw), rnd.uniform(0, H), rnd.uniform(30, 160), fill=1, stroke=0)
    c.setFillColor(white); c.setFont('Helvetica-Bold', 54); c.drawCentredString(ox + pw/2, H*.55, 'PANEL LAB')
    return None

LAYOUTS = [None, [[1], [1, 1], [1]], [[1, 1], [1, 1, 1]], ('dark', [[1, 1], [1], [1, 1]]), None, [[1], [2, 1], [1, 1, 1]], [[1, 1], [1, 1]], [[1], [1, 2], [1]], [[2, 1], [1], [1, 1]]]

def lab1():
    rnd = random.Random(7); c = canvas.Canvas(os.path.join(OUT, 'Panel_Lab_01.pdf'), pagesize=(W, H)); c.setTitle('Panel Lab 01'); truth = []
    for i, L in enumerate(LAYOUTS):
        if L is None: truth.append(splash(c, rnd))
        elif isinstance(L, tuple): truth.append(page(c, L[1], rnd, i+1, dark=True))
        else: truth.append(page(c, L, rnd, i+1))
        c.showPage()
    c.save(); return truth

def lab2():
    """two-page spread scans (fold in the middle): cover sheet, then 3 sheets of two panel pages each"""
    rnd = random.Random(11); c = canvas.Canvas(os.path.join(OUT, 'Panel_Lab_02.pdf'), pagesize=(2*W, H)); c.setTitle('Panel Lab 02'); truth = []
    c.setFillColor(black); c.rect(0, 0, 2*W, H, fill=1, stroke=0); splash(c, rnd, W, W); c.showPage(); truth.append(None)
    sheets = [([[1], [1, 1]], [[1, 1], [1]]), ([[1, 1], [1, 1]], [[1], [1], [1]]), ([[1], [1, 1, 1]], [[1, 1], [1]])]
    for n, (a, b) in enumerate(sheets):
        L = page(c, a, rnd, 2*n+2, ox=0); R = page(c, b, rnd, 2*n+3, ox=W); c.showPage(); truth.append({'L': L, 'R': R})
    c.save(); return truth

if __name__ == '__main__':
    t = {'Panel_Lab_01': lab1(), 'Panel_Lab_02': lab2()}
    json.dump(t, open(os.path.join(OUT, 'truth.json'), 'w')); print('panel fixtures ->', OUT)
