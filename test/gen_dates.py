"""ORIGINAL abstract test comics for the v24 Timeline (no real series, characters or logos).
Dates come from: file name '(1983)' / '(Mar 1984)', XMP prism:coverDate, an attached ComicInfo.xml, or nothing (Unknown).
Output: ../testpdfs/dates/   Usage: python3 test/gen_dates.py"""
import os, re, random
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
OUT=os.path.join(os.path.dirname(__file__),'..','testpdfs','dates'); os.makedirs(OUT,exist_ok=True)
FT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def art(title,seed):
    r=random.Random(seed); im=Image.new('RGB',(600,922),(r.randint(10,60),r.randint(10,60),r.randint(40,90))); d=ImageDraw.Draw(im)
    for _ in range(14):
        x,y,s=r.randint(0,600),r.randint(0,922),r.randint(30,160); d.rectangle([x,y,x+s,y+s*1.3],fill=(r.randint(80,255),r.randint(60,200),r.randint(40,220)))
    d.rectangle([0,0,600,150],fill=(0,0,0)); d.text((30,40),title.upper(),font=ImageFont.truetype(FT,46),fill=(255,255,255)); return im
def make(fn,title,seed,pages=3):
    p=os.path.join(OUT,fn); c=canvas.Canvas(p,pagesize=(600,922)); c.setCreator('gen_dates')
    for i in range(pages):
        c.drawImage(ImageReader(art(title if i==0 else f'{title} p{i+1}',seed*10+i)),0,0,600,922); c.showPage()
    c.save(); return p
def incremental(p,xmp=None,comicinfo=None):
    b=open(p,'rb').read(); sx=int(re.findall(rb'startxref\s+(\d+)',b)[-1]); tr=re.findall(rb'trailer\s*<<(.*?)>>\s*startxref',b,re.S)[-1]
    root=int(re.search(rb'/Root (\d+) 0 R',tr).group(1)); info=re.search(rb'/Info (\d+) 0 R',tr); size=int(re.search(rb'/Size (\d+)',tr).group(1))
    cat=re.search(rb'\n%d 0 obj\s*<<(.*?)>>\s*endobj'%root,b,re.S).group(1); objs={}; n=size; extra=b''
    if xmp is not None:
        x=f'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?><x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:prism="http://prismstandard.org/namespaces/basic/2.0/" xmlns:dc="http://purl.org/dc/elements/1.1/"><prism:coverDate>{xmp}</prism:coverDate><dc:title><rdf:Alt><rdf:li xml:lang="x-default">test</rdf:li></rdf:Alt></dc:title></rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'.encode()
        objs[n]=b'<< /Type /Metadata /Subtype /XML /Length %d >>\nstream\n'%len(x)+x+b'\nendstream'; extra+=b' /Metadata %d 0 R'%n; n+=1
    if comicinfo is not None:
        x=comicinfo.encode(); objs[n]=b'<< /Type /EmbeddedFile /Length %d >>\nstream\n'%len(x)+x+b'\nendstream'
        objs[n+1]=b'<< /Type /Filespec /F (ComicInfo.xml) /UF (ComicInfo.xml) /EF << /F %d 0 R >> >>'%n
        extra+=b' /Names << /EmbeddedFiles << /Names [(ComicInfo.xml) %d 0 R] >> >>'%(n+1); n+=2
    objs[root]=b'<<'+cat+extra+b' >>'
    out=bytearray(b if b.endswith(b'\n') else b+b'\n'); offs={}
    for k in sorted(objs): offs[k]=len(out); out+=b'%d 0 obj\n'%k+objs[k]+b'\nendobj\n'
    xr=len(out); out+=b'xref\n'
    for k in sorted(offs): out+=b'%d 1\n%010d 00000 n \n'%(k,offs[k])
    out+=b'trailer\n<< /Size %d /Root %d 0 R%s /Prev %d >>\nstartxref\n%d\n%%%%EOF\n'%(n,root,(b' /Info %s 0 R'%info.group(1)) if info else b'',sx,xr); open(p,'wb').write(out)
make('Comet_Run_01_(1983).pdf','Comet Run 1',1)
make('Comet_Run_02_(Mar_1984).pdf','Comet Run 2',2)
incremental(make('Deep_Signal_01.pdf','Deep Signal 1',3),xmp='1991-06-01')
incremental(make('Deep_Signal_02.pdf','Deep Signal 2',4),comicinfo='<?xml version="1.0"?><ComicInfo><Series>Deep Signal</Series><Number>2</Number><Year>1992</Year><Month>2</Month></ComicInfo>')
make('Paper_Moons_01.pdf','Paper Moons 1',5)
make('Paper_Moons_02.pdf','Paper Moons 2',6)
print('wrote',sorted(os.listdir(OUT)))
