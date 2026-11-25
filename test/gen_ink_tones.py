"""ORIGINAL abstract test page for cr-v70 Inks blacks vs grays (no real series or logos).
One page: a scanned-black patch at luma 0.12 (rgb 31) and a mid-gray patch at luma 0.50
(rgb 128), plus pure-black strokes and a white caption.
Output: ../testpdfs/Ink_Tones_01.pdf
Usage: python3 test/gen_ink_tones.py"""
import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
OUT=os.path.join(os.path.dirname(__file__),'..','testpdfs'); os.makedirs(OUT,exist_ok=True)
FT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
W,H=600,922
font_sm=ImageFont.truetype(FT,18); font_md=ImageFont.truetype(FT,28); font_lg=ImageFont.truetype(FT,22)
im=Image.new('RGB',(W,H),(248,246,242)); d=ImageDraw.Draw(im)
d.rectangle([0,0,W,44], fill=(16,16,16))
d.text((16,10),'INK  TONES  ·  0.12  BLACK   /   0.50  GRAY', font=font_sm, fill=(245,245,245))
d.rectangle([30,64,290,720], fill=(31,31,31), outline=(0,0,0), width=8)
d.line([(60,120),(260,120)], fill=(0,0,0), width=10)
d.line([(60,120),(60,640)], fill=(0,0,0), width=10)
d.rectangle([70,200,160,280], outline=(0,0,0), width=8)
d.rectangle([48,680,272,708], fill=(0,0,0))
d.text((58,684),'SCANNED  BLACK  0.12', font=font_lg, fill=(250,250,248))
d.rectangle([310,64,570,720], fill=(128,128,128), outline=(0,0,0), width=8)
d.line([(340,120),(540,120)], fill=(0,0,0), width=10)
d.line([(340,120),(340,640)], fill=(0,0,0), width=10)
d.rectangle([350,200,440,280], outline=(0,0,0), width=8)
d.rectangle([328,680,552,708], fill=(0,0,0))
d.text((348,684),'MID  GRAY  0.50', font=font_lg, fill=(250,250,248))
d.rectangle([120,760,480,860], fill=(255,255,255), outline=(0,0,0), width=4)
d.text((150,790),'WHITES  STAY  WHITE', font=font_md, fill=(0,0,0))
p=os.path.join(OUT,'Ink_Tones_01.pdf'); c=canvas.Canvas(p, pagesize=(W,H))
c.drawImage(ImageReader(im),0,0,W,H); c.showPage(); c.save(); print('wrote',p)
