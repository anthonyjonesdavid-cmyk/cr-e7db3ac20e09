# fixture: a scanned-style comic whose pages differ slightly in shape (triggers per-spread geometry differences)
import os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
OUT=os.path.join(os.path.dirname(__file__),'..','testpdfs','mixed'); os.makedirs(OUT,exist_ok=True)
W,H=663,1024; widths=[1.0,0.97,1.04,1.0,0.95,1.06,0.99,1.03,0.96,1.05]
c=canvas.Canvas(os.path.join(OUT,'Scanned_Mix_01.pdf')); c.setTitle('Scanned Mix 01')
cols=['#7a1f1f','#1f5a7a','#2f7a1f','#7a6a1f','#5a1f7a','#1f7a6a']
for i in range(24):
    w=W*widths[i%len(widths)]; c.setPageSize((w,H)); c.setFillColor(HexColor(cols[i%6])); c.rect(0,0,w,H,fill=1,stroke=0)
    c.setFillColor(white); c.setFont('Helvetica-Bold',160); c.drawCentredString(w/2,H/2-60,str(i+1)); c.showPage()
c.save()
# fixture: plain fold-in-middle sheets (no drawn spine line) for seam detection during turns
c=canvas.Canvas(os.path.join(OUT,'Plain_Fold_01.pdf')); c.setTitle('Plain Fold 01')
pal=['#e8e2d0','#d6e4ec','#e9d8d8','#dfe9d6','#ebe3c8','#dcd8ec']
for i in range(10):
    c.setPageSize((2*W+1,H)); c.setFillColor(HexColor(pal[i%6])); c.rect(0,0,2*W+1,H,fill=1,stroke=0); c.showPage()
c.save()
