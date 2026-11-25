"""ORIGINAL abstract test page for cr-v71 Inks line-work boost (no real series or logos).
One primary page: thin, scan-like (anti-aliased) lettering and balloon outlines, figure
contours, and hatching over a mid-gray (luma 0.50) fill, plus a white balloon interior.
Stroke cores sit around luma 0.23-0.35 so the v70 tone curve alone leaves them mid-gray.
Two extra similar pages let Fit-width scroll and page-turn perf be timed.
Output: ../testpdfs/Ink_Lines_01.pdf
Usage: python3 test/gen_ink_lines.py"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

OUT=os.path.join(os.path.dirname(__file__),'..','testpdfs'); os.makedirs(OUT,exist_ok=True)
FT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
W,H=600,922
SX=3
PAPER=(248,246,242)
FILL=(128,128,128)
INK=(70,70,70)
BORDER=(65,65,65)
HATCH=(55,55,55)

def render_page(caption='INK  LINES  ·  THIN  LETTERING'):
    w,h=W*SX,H*SX
    im=Image.new('RGB',(w,h),PAPER)
    d=ImageDraw.Draw(im)
    font_bubble=ImageFont.truetype(FT, 26*SX)
    font_big=ImageFont.truetype(FT, 32*SX)
    font_sm=ImageFont.truetype(FT, 14*SX)
    m=24*SX
    y_split=int(H*0.52)*SX
    gap=16*SX
    top=(m, 40*SX, w-m, y_split-gap//2)
    bot=(m, y_split+gap//2, w-m, h-48*SX)
    # fills
    d.rectangle([top[0],top[1],top[2],top[3]], fill=FILL)
    d.rectangle([bot[0],bot[1],bot[2],bot[3]], fill=FILL)
    # hatching, clipped to the bottom panel (inset so the border stays clean)
    hatch=Image.new('RGB',(w,h),FILL)
    hd=ImageDraw.Draw(hatch)
    hx0,hy0,hx1,hy1=bot[0]+4*SX, bot[1]+4*SX, bot[2]-4*SX, bot[3]-4*SX
    span=hy1-hy0
    for i in range(-1200, 2400, 10*SX):
        hd.line([(hx0+i,hy0),(hx0+i+span,hy1)], fill=HATCH, width=max(1,int(1.15*SX)))
    mask=Image.new('L',(w,h),0)
    ImageDraw.Draw(mask).rectangle([hx0,hy0,hx1,hy1], fill=255)
    im.paste(hatch,(0,0),mask)
    # panel borders
    d.rectangle([top[0],top[1],top[2],top[3]], outline=BORDER, width=2*SX)
    d.rectangle([bot[0],bot[1],bot[2],bot[3]], outline=BORDER, width=2*SX)
    # top balloon + lettering
    bx0,by0,bx1,by1=80*SX, 68*SX, 520*SX, 250*SX
    d.ellipse([bx0,by0,bx1,by1], fill=(255,255,255), outline=BORDER, width=2*SX)
    y=128*SX
    for line in ("WATCH  OUT,","WOLVERINE!"):
        tw=d.textlength(line, font=font_bubble)
        d.text(((w-tw)/2, y), line, font=font_bubble, fill=INK)
        y+=46*SX
    # figure contour, fully inside the top panel
    cx,cy=300*SX, 350*SX
    lw=max(1,int(1.6*SX))
    d.ellipse([cx-40*SX, cy-80*SX, cx+40*SX, cy-8*SX], outline=INK, width=lw)
    d.line([(cx,cy-8*SX),(cx,cy+62*SX)], fill=INK, width=lw)
    d.line([(cx,cy+16*SX),(cx-58*SX,cy-8*SX)], fill=INK, width=lw)
    d.line([(cx,cy+16*SX),(cx+58*SX,cy-8*SX)], fill=INK, width=lw)
    d.line([(cx,cy+62*SX),(cx-42*SX,cy+112*SX)], fill=INK, width=lw)
    d.line([(cx,cy+62*SX),(cx+42*SX,cy+112*SX)], fill=INK, width=lw)
    # bottom balloon
    d.ellipse([90*SX, y_split+70*SX, 360*SX, y_split+215*SX], fill=(255,255,255), outline=BORDER, width=2*SX)
    d.text((125*SX, y_split+122*SX), "SNIKT!", font=font_big, fill=INK)
    # margin caption (paper, not in the gray fill)
    d.text((24*SX, h-36*SX), caption, font=font_sm, fill=(40,40,40))
    # scanner-like AA: slight blur at high res, then downscale
    im=im.filter(ImageFilter.GaussianBlur(radius=1.15))
    return im.resize((W,H), Image.Resampling.LANCZOS)

p1=render_page('INK  LINES  ·  THIN  LETTERING')
p2=render_page('INK  LINES  ·  PAGE  2')
p3=render_page('INK  LINES  ·  PAGE  3')
p=os.path.join(OUT,'Ink_Lines_01.pdf')
c=canvas.Canvas(p, pagesize=(W,H))
for im in (p1,p2,p3):
    c.drawImage(ImageReader(im),0,0,W,H); c.showPage()
c.save()
print('wrote',p)
# also stash a source PNG next to the script's tmp for local debug; tests use the PDF
dbg=os.path.join(OUT,'..','shots'); os.makedirs(dbg,exist_ok=True)
# don't write into shots by default (gitignored anyway); just confirm luma
import numpy as np
g=np.array(p1.convert('L'),dtype=np.float32)/255.0
print('lettering min/med (dark <0.55)', g[128:175,150:450][g[128:175,150:450]<0.55].min(),
      float(np.median(g[128:175,150:450][g[128:175,150:450]<0.55])))
print('fill mean', float(g[300:360, 70:140].mean()))
print('white mean', float(g[100:130, 250:350].mean()))
