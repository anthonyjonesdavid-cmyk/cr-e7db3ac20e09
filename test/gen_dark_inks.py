"""ORIGINAL abstract test comic for cr-v67 Inks (no real series, characters or logos).
Page 1 is a dark-heavy line-art page (black ink on dark fills) used to check that
Inks lifts fills to mid gray instead of crushing them to black.
Output: ../testpdfs/Dark_Inks_01.pdf   Usage: python3 test/gen_dark_inks.py"""
import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
OUT=os.path.join(os.path.dirname(__file__),'..','testpdfs'); os.makedirs(OUT,exist_ok=True)
FT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
W,H=600,922
def page1():
    im=Image.new('RGB',(W,H),(28,16,52)); d=ImageDraw.Draw(im)
    d.rectangle([0,0,W,36], fill=(12,8,24))
    font_sm=ImageFont.truetype(FT,16); font_lg=ImageFont.truetype(FT,28)
    d.text((16,8),'TM  &  ©  TEST  ·  DARK  ISSUE', font=font_sm, fill=(240,240,240))
    panels=[(24,52,288,460,(36,22,72)),(312,52,576,460,(22,40,58)),(24,476,288,870,(64,24,28)),(312,476,576,870,(18,18,42))]
    INK=(0,0,0)
    for x0,y0,x1,y1,fill in panels:
        d.rectangle([x0,y0,x1,y1], fill=fill, outline=INK, width=10)
        d.line([(x0+16,y0+8),(x1-16,y0+8)], fill=INK, width=4)
    cx,cy=156,220
    d.ellipse([cx-48,cy-48,cx+48,cy+48], outline=INK, width=8)
    d.line([(cx,cy+48),(cx,cy+150)], fill=INK, width=8)
    d.line([(cx,cy+80),(cx-70,cy+40)], fill=INK, width=7)
    d.line([(cx,cy+80),(cx+70,cy+40)], fill=INK, width=7)
    d.line([(cx,cy+150),(cx-50,cy+230)], fill=INK, width=7)
    d.line([(cx,cy+150),(cx+50,cy+230)], fill=INK, width=7)
    d.ellipse([cx-18,cy-12,cx-6,cy], fill=(245,245,245))
    d.ellipse([cx+6,cy-12,cx+18,cy], fill=(245,245,245))
    d.rectangle([328,790,560,854], fill=(250,250,248), outline=INK, width=4)
    d.text((340,806),'LINE  WORK', font=font_lg, fill=(0,0,0))
    d.text((24,H-40),'PAGE 1', font=font_sm, fill=(230,230,230))
    return im
def page2():
    im=Image.new('RGB',(W,H),(248,246,240)); d=ImageDraw.Draw(im)
    font_lg=ImageFont.truetype(FT,28)
    d.rectangle([30,40,570,880], fill=(236,220,190), outline=(0,0,0), width=8)
    d.text((40,60),'PAGE 2', font=font_lg, fill=(0,0,0))
    d.rectangle([60,140,540,800], fill=(40,80,140), outline=(0,0,0), width=6)
    return im
p=os.path.join(OUT,'Dark_Inks_01.pdf'); c=canvas.Canvas(p, pagesize=(W,H))
c.drawImage(ImageReader(page1()),0,0,W,H); c.showPage()
c.drawImage(ImageReader(page2()),0,0,W,H); c.showPage()
c.save(); print('wrote',p)
