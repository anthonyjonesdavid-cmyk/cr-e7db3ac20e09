"""ORIGINAL abstract test comic for cr-v68 Fit-width 1-page mode (no real series or logos).
Page 1 and 3 are portrait (660x1000, 6.6:10). Pages 2 and 4 are scanned two-page
spreads at aspects 1.32 and 1.45, each a left (orange, "LEFT PAGE") and right
(blue, "RIGHT PAGE") sheet joined at a thin spine.
Output: ../testpdfs/spreads/Facing_Pages_01.pdf
Usage: python3 test/gen_facing_pages.py"""
import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
OUT=os.path.join(os.path.dirname(__file__),'..','testpdfs','spreads'); os.makedirs(OUT,exist_ok=True)
FT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def fonts():
    return ImageFont.truetype(FT,22), ImageFont.truetype(FT,64), ImageFont.truetype(FT,36)
def comic_page(w,h,side):
    font_sm,font_lg,_=fonts()
    if side=='L':
        bg,panel,ink=(210,92,42),(168,48,28),(20,8,4)
        label,credit='LEFT PAGE','TM  &  ©  2005  LEFT'
    else:
        bg,panel,ink=(42,86,186),(24,52,128),(4,8,24)
        label,credit='RIGHT PAGE','TM  &  ©  2005  RIGHT'
    im=Image.new('RGB',(w,h),bg); d=ImageDraw.Draw(im)
    d.rectangle([0,0,w,48], fill=(12,8,8) if side=='L' else (8,8,20))
    d.text((16,12), credit, font=font_sm, fill=(245,245,245))
    m=36
    d.rectangle([m,68,w-m,h-88], fill=panel, outline=ink, width=12)
    cx,cy=w//2, h//2-20
    d.ellipse([cx-70,cy-140,cx+70,cy-10], outline=(245,245,245), width=10)
    d.line([(cx,cy-10),(cx,cy+140)], fill=(245,245,245), width=10)
    d.line([(cx,cy+40),(cx-110,cy-10)], fill=(245,245,245), width=8)
    d.line([(cx,cy+40),(cx+110,cy-10)], fill=(245,245,245), width=8)
    d.line([(cx,cy+140),(cx-90,cy+260)], fill=(245,245,245), width=8)
    d.line([(cx,cy+140),(cx+90,cy+260)], fill=(245,245,245), width=8)
    tw=d.textlength(label, font=font_lg)
    d.rectangle([cx-tw/2-16, h-200, cx+tw/2+16, h-118], fill=(250,250,248), outline=ink, width=4)
    d.text((cx-tw/2, h-188), label, font=font_lg, fill=ink)
    return im
def facing(W,H,tag):
    font_sm,_,_=fonts()
    im=Image.new('RGB',(W,H),(18,16,14)); half=W//2
    im.paste(comic_page(half,H,'L'),(0,0)); im.paste(comic_page(W-half,H,'R'),(half,0))
    d=ImageDraw.Draw(im); d.rectangle([half-5,0,half+5,H], fill=(28,24,20))
    d.text((12,H-36), tag, font=font_sm, fill=(240,240,240)); return im
def portrait(w,h,title):
    *_,font_md=fonts()
    im=Image.new('RGB',(w,h),(244,236,220)); d=ImageDraw.Draw(im)
    d.rectangle([24,24,w-24,h-24], fill=(80,40,40), outline=(0,0,0), width=8)
    d.text((40,48), title, font=font_md, fill=(250,250,248)); return im
pages=[portrait(660,1000,'COVER'), facing(1320,1000,'SPREAD  1.32'), portrait(660,1000,'PAGE  3'), facing(1450,1000,'SPREAD  1.45')]
p=os.path.join(OUT,'Facing_Pages_01.pdf'); c=canvas.Canvas(p)
for im in pages:
    w,h=im.size; c.setPageSize((w,h)); c.drawImage(ImageReader(im),0,0,w,h); c.showPage()
c.save(); print('wrote',p)
