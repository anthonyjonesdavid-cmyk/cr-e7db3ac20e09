# fixtures for "skip black pages": original synthetic art only.
# Midnight Run 01: cover, story pages, dark night scenes (must NOT be skipped), ads, and two blank black "TM & (c)" pages (must be skipped).
import os, io, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
OUT=os.path.join(os.path.dirname(__file__),'..','testpdfs','mixed'); os.makedirs(OUT,exist_ok=True)
W,H=663,1024; S=2
def font(sz):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        if os.path.exists(f): return ImageFont.truetype(f,sz)
    return ImageFont.load_default()
def put(c,im,w=W,h=H):
    b=io.BytesIO(); im.convert('RGB').save(b,'JPEG',quality=85); b.seek(0); c.setPageSize((w,h)); c.drawImage(ImageReader(b),0,0,w,h); c.showPage()
def blank_black(rnd,noise=False,edge=False,w=W,h=H,year='2026'):
    im=Image.new('RGB',(w*S,h*S),(4,4,4))
    if noise:
        px=im.load()
        for y in range(0,h*S,2):
            band=rnd.randint(0,3)
            for x in range(0,w*S,2):
                v=8+rnd.randint(0,7)+band; px[x,y]=(v,v,v)
        im=im.filter(ImageFilter.BoxBlur(1))
    d=ImageDraw.Draw(im); t=f'TM & \u00a9 {year} SHELF COMICS'; f=font(11*S); tw=d.textlength(t,font=f)
    bw,bh=tw+28*S,26*S; x0=(w*S-bw)/2; y0=h*S-70*S; d.rectangle([x0,y0,x0+bw,y0+bh],fill=(246,246,246)); d.text((x0+14*S,y0+7*S),t,fill=(10,10,10),font=f)
    if edge: d.rectangle([w*S-int(w*S*.012),0,w*S,h*S],fill=(222,220,214))     # light scanner-bed strip on the right edge
    return im
def night(rnd,kind):
    im=Image.new('RGB',(W*S,H*S)); d=ImageDraw.Draw(im)
    for y in range(H*S):   # sky gradient, very dark
        t=y/(H*S); v=(int(3+18*t),int(5+20*t),int(12+30*t)); d.line([(0,y),(W*S,y)],fill=v)
    if kind in ('stars','city'):
        for _ in range(220): x,y=rnd.randint(0,W*S),rnd.randint(0,int(H*S*.6)); r=rnd.choice([1,1,2,3]); d.ellipse([x,y,x+r,y+r],fill=(200,205,220))
        d.ellipse([W*S*.68,H*S*.1,W*S*.68+90*S,H*S*.1+90*S],fill=(230,228,210))
    if kind in ('city','rain'):
        x=0
        while x<W*S:
            bw=rnd.randint(40,110)*S; bh=rnd.randint(180,520)*S; d.rectangle([x,H*S-bh,x+bw,H*S],fill=(10,12,18))
            for _ in range(rnd.randint(2,10)):
                wx=x+rnd.randint(6,max(7,bw-16)); wy=H*S-bh+rnd.randint(10,bh-20); d.rectangle([wx,wy,wx+8*S,wy+11*S],fill=(255,214,120))
            x+=bw+rnd.randint(4,20)*S
    if kind=='rain':
        for _ in range(1400): x,y=rnd.randint(0,W*S),rnd.randint(0,H*S); d.line([(x,y),(x-6*S,y+26*S)],fill=(40,46,60),width=S)
        d.rectangle([W*S*.42,H*S*.55,W*S*.42+16*S,H*S*.55+20*S],fill=(255,230,150))
    if kind=='alley':    # mostly black: one lamp + figure + faint brick texture
        im.paste((6,6,8),[0,0,W*S,H*S]); d=ImageDraw.Draw(im)
        for y in range(0,H*S,18*S):
            for x in range((y//(18*S))%2*20*S,W*S,40*S): d.rectangle([x,y,x+38*S,y+16*S],outline=(26,24,26))
        d.polygon([(W*S*.45,H*S*.2),(W*S*.25,H*S*.95),(W*S*.75,H*S*.95)],fill=(70,64,50)); d.ellipse([W*S*.43,H*S*.17,W*S*.47,H*S*.21],fill=(255,240,190))
        d.rectangle([W*S*.48,H*S*.62,W*S*.52,H*S*.9],fill=(0,0,0))
    return im
def story(rnd,i):
    im=Image.new('RGB',(W*S,H*S),(240,236,226)); d=ImageDraw.Draw(im); m=24*S
    for r in range(3):
        y0=m+r*(H*S-2*m)//3; y1=y0+(H*S-2*m)//3-12*S; c=(rnd.randint(30,90),rnd.randint(40,100),rnd.randint(90,160)); d.rectangle([m,y0,W*S-m,y1],fill=c,outline=(0,0,0),width=3*S)
    d.text((W*S/2-40*S,H*S/2-50*S),str(i+1),fill=(255,255,255),font=font(90*S)); return im
def ad(i):
    im=Image.new('RGB',(W*S,H*S),(250,214,40)); d=ImageDraw.Draw(im); d.text((60*S,400*S),'BUY\nSPACE\nGUM',fill=(200,20,40),font=font(80*S)); d.text((60*S,80*S),f'AD {i+1}',fill=(0,0,0),font=font(30*S)); return im
def cover():
    im=Image.new('RGB',(W*S,H*S),(18,22,40)); d=ImageDraw.Draw(im); d.rectangle([0,0,W*S,H*S*.3],fill=(220,60,40)); d.text((40*S,60*S),'MIDNIGHT RUN',fill=(255,255,255),font=font(56*S)); d.text((40*S,150*S),'#1',fill=(255,255,255),font=font(40*S)); return im
rnd=random.Random(7)
# page plan (0-based): 0 cover, 1-4 story, 5 night city, 6 story, 7 rain, 8 alley, 9 stars, 10 story, 11 ad, 12 BLACK, 13 ad, 14 BLACK(noisy+edge), 15 story
plan=['cover','s','s','s','s','city','s','rain','alley','stars','s','ad','black','ad','black2','s']
c=canvas.Canvas(os.path.join(OUT,'Midnight_Run_01.pdf')); c.setTitle('Midnight Run 01')
for i,k in enumerate(plan):
    im={'cover':cover,'s':lambda:story(rnd,i),'city':lambda:night(rnd,'city'),'rain':lambda:night(rnd,'rain'),'alley':lambda:night(rnd,'alley'),'stars':lambda:night(rnd,'stars'),
        'ad':lambda:ad(i),'black':lambda:blank_black(rnd),'black2':lambda:blank_black(rnd,noise=True,edge=True,year='2000')}[k]()
    put(c,im)
c.save()
# fold comic: wide sheets (two pages side by side); sheet 5 is a blank black sheet with the copyright box on its right half
c=canvas.Canvas(os.path.join(OUT,'Midnight_Fold_01.pdf')); c.setTitle('Midnight Fold 01')
for s in range(8):
    if s==5: im=blank_black(rnd,w=2*W)
    elif s==3: L=night(rnd,'city'); R=night(rnd,'rain'); im=Image.new('RGB',(2*W*S,H*S)); im.paste(L,(0,0)); im.paste(R,(W*S,0))
    else: L=story(rnd,2*s); R=story(rnd,2*s+1) if s else cover(); im=Image.new('RGB',(2*W*S,H*S)); im.paste(L,(0,0)); im.paste(R,(W*S,0))
    put(c,im,2*W,H)
c.save()
print('ok')
