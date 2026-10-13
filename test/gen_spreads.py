"""ORIGINAL abstract test comic for v29 two-page spreads (no real series, characters or logos).
Pages 1,2,4,5,7,8 are portrait (600x922); pages 3 and 6 are wide two-page spreads (1200x922) with a few clear 'panels'.
Output: ../testpdfs/spreads/Wide_Horizon_01.pdf   Usage: python3 test/gen_spreads.py"""
import os, random
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
OUT=os.path.join(os.path.dirname(__file__),'..','testpdfs','spreads'); os.makedirs(OUT,exist_ok=True)
FT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def page(w,h,label,seed,wide):
    r=random.Random(seed); im=Image.new('RGB',(w,h),(250,250,246)); d=ImageDraw.Draw(im)
    cols=4 if wide else 2
    for k in range(cols*2):
        cx,cy=k%cols,k//cols; x0=30+cx*(w-60)//cols; y0=30+cy*(h-60)//2; x1=x0+(w-60)//cols-24; y1=y0+(h-60)//2-24
        d.rectangle([x0,y0,x1,y1],fill=(r.randint(30,200),r.randint(30,200),r.randint(60,230)),outline=(0,0,0),width=6)
    d.text((40,h-80),label,font=ImageFont.truetype(FT,40),fill=(0,0,0)); return im
p=os.path.join(OUT,'Wide_Horizon_01.pdf'); c=canvas.Canvas(p)
for i in range(8):
    wide=i in (2,5); w,h=(1200,922) if wide else (600,922); c.setPageSize((w,h))
    c.drawImage(ImageReader(page(w,h,('SPREAD ' if wide else 'PAGE ')+str(i+1),i,wide)),0,0,w,h); c.showPage()
c.save(); print('wrote',p)
