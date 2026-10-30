"""v54: builds src/notes-data.js ("About this issue") from public wikis. Every fact keeps its source URL; anything unparseable is dropped.
Issue facts: Fandom comics wikis (Marvel / DC Database / Image). Month context: Wikipedia '<year> in the United States', '<year>' and Billboard Hot 100 lists."""
import html, json, re, sys, time, urllib.parse, urllib.request, os
HERE=os.path.dirname(os.path.abspath(__file__)); FILES=json.load(open('/tmp/files.json'))
UA={'User-Agent':'ComicShelf-notes/1.0 (personal app)'}
def get(url):
    for i in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=30))
        except Exception as e: time.sleep(2+i*3)
    return None
def wikitexts(host,titles):
    out={}
    for i in range(0,len(titles),40):
        q=urllib.parse.urlencode({'action':'query','prop':'revisions','rvprop':'content','rvslots':'main','format':'json','redirects':1,'titles':'|'.join(titles[i:i+40])})
        d=get(f'https://{host}/api.php?{q}') or {}; Q=d.get('query',{}); back={}
        for r in Q.get('normalized',[])+Q.get('redirects',[]): back[r['to']]=back.get(r['from'],r['from'])
        for p in Q.get('pages',{}).values():
            if 'revisions' in p:
                t=p['title']; orig=back.get(t,t); orig=back.get(orig,orig); out[orig]=(t,p['revisions'][0]['slots']['main']['*'])
    return out
MON=['january','february','march','april','may','june','july','august','september','october','november','december']
def field(wt,k):
    m=re.search(r'\|\s*'+k+r'\s*=([^\n]*)',wt); return m.group(1).strip() if m else ''
def ym(wt):
    y=field(wt,'Year'); mo=field(wt,'Month').lower()
    try: y=int(re.sub(r'\D','',y)[:4])
    except: return None
    m=int(mo) if mo.isdigit() else (MON.index(mo)+1 if mo in MON else 0); return (y,m)
def clean(s):
    s=re.sub(r'<ref[^>]*/>|<ref.*?</ref>','',s,flags=re.S); s=re.sub(r'<!--.*?-->','',s,flags=re.S); s=re.sub(r'<[^>]+>','',s)
    for _ in range(3): s=re.sub(r'\{\{[^{}]*\}\}',lambda m:tmpl(m.group(0)),s)
    s=re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]',r'\1',s); s=re.sub(r'\[https?://\S+ ([^\]]*)\]',r'\1',s); s=re.sub(r"'{2,}",'',s)
    s=re.sub(r'\s*\((?:Earth|Earth-\d+)[^)]*\)','',s); return html.unescape(re.sub(r'\s+',' ',s)).strip(' *:')
def tmpl(t):
    parts=t[2:-2].split('|'); n=parts[0].strip().lower()
    if n in('w','wp','wikipedia','cl','sic','c','m','a','apn','ml','cid','sld','g','r','mel') and len(parts)>1: return parts[-1] if n!='r' else parts[1]
    if len(parts)>1 and n in ('1st','death','mentioned','flashback','dies'): return parts[1]
    return ''
SKIP=re.compile(r'letters? (page|column)|letter column|bullpen|marvel age|checklist|advertis|reprint|pin-?up|recap|dedicated|soapbox|continued (from|in)|continues|takes place|chronolog|placement|this story|is set|occurs (before|after)|cover (is|was) (a )?homage|variant|newsstand|price|hype box|mail|published in|editorial|statement of ownership',re.I)
KEY=re.compile(r'\bfirst\b|debut|origin|death|dies|killed|final|last appearance|return|reveal|wedding|marri|join|introduc|becomes|identity|1st',re.I)
SAID=re.compile(r'\b(said|stated|recalled|explained|interview|according to|commented|admitted|wanted to)\b',re.I)
def section(wt,k):
    m=re.search(r'\|\s*'+k+r'\s*=(.*?)(?=\n\|\s*\w+\s*=|\n\}\}\s*$)',wt,re.S); return m.group(1) if m else ''
def issue_facts(wt):
    firsts=[];deaths=[]
    for m in re.finditer(r'\{\{1st(?: Dies| Full| Identified)?\|\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',wt):
        n=clean(m.group(2) or m.group(1)); 
        if n and n not in firsts: firsts.append(n)
    for m in re.finditer(r'\{\{Death\|\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',wt):
        n=clean(m.group(2) or m.group(1))
        if n and n not in deaths: deaths.append(n)
    facts=[];said=[]; names={clean(v) for v in re.findall(r'\|\s*(?:Writer|Penciler|Penciller|Artist|Inker)\d*(?:_\d+)?\s*=([^\n]+)',wt) if clean(v)}
    for k in ('Notes','Trivia'):
        for b in re.split(r'\n\s*\*+',section(wt,k)):
            t=clean(b)
            if not(20<=len(t)<=320) or SKIP.search(t): continue
            if not re.search(r'[.!?"”)]$',t): continue
            if SAID.search(t):
                if any(n.split()[-1] in t for n in names): said.append(t)
            elif KEY.search(t): facts.append(t)
    return firsts[:8],deaths[:4],facts[:4],said[:2]
SER=[(r'^ASMANN0*(\d+)$',['Amazing Spider-Man Annual Vol 1']),(r'^ASM0*(\d+)$',['Amazing Spider-Man Vol 1','Amazing Spider-Man Vol 2']),(r'^Amazing Spider-Man 0*(\d+)$',['Amazing Spider-Man Vol 1']),
 (r'^X-MEN0*(\d+)$',['Uncanny X-Men Vol 1','X-Men Vol 1']),(r'^Daredevil 0*(\d+)$',['Daredevil Vol 1']),(r'^Excalibur 0*(\d+)$',['Excalibur Vol 1']),
 (r'^Fantastic Four - Heroes Reborn 0*(\d+)$',['Fantastic Four Vol 2']),(r'^Kitty Pride Wolverine 0*(\d+)$',['Kitty Pryde and Wolverine Vol 1']),
 (r'^New Mutants Annual 0*(\d+)$',['New Mutants Annual Vol 1']),(r'^New Mutants 0*(\d+)$',['New Mutants Vol 1']),(r'^Punisher War Journal 0*(\d+)$',['Punisher War Journal Vol 1']),
 (r'^Spawn-0*(\d+)\b.*$',['Spawn Vol 1']),(r'^Spider-Man 0*(\d+)$',['Spider-Man Vol 1']),(r'^Wildcats-0*(\d+)$',['WildC.A.T.s Vol 1']),(r'^Wolverine 0*(\d+)$',['Wolverine Vol 2']),
 (r'^X-Factor 0*(\d+)$',['X-Factor Vol 1']),(r'^Marvel Comics Presents 0*(\d+)$',['Marvel Comics Presents Vol 1'])]
HOST=lambda t:'imagecomics.fandom.com' if t.startswith('Spawn') else 'dc.fandom.com' if t.startswith('WildC') else 'marvel.fandom.com'
cand={}
for o in FILES:
    b=o['f'][:-4]
    for rx,ts in SER:
        m=re.match(rx,b)
        if m: cand[o['f']]=[f'{t} {int(m.group(1))}' for t in ts]; break
byhost={}
for f,ts in cand.items():
    for t in ts: byhost.setdefault(HOST(t),set()).add(t)
pages={}
for h,ts in byhost.items(): 
    for k,v in wikitexts(h,sorted(ts)).items(): pages[(h,k)]=v
    print(h,len(ts),'fetched',sum(1 for x in pages if x[0]==h),file=sys.stderr)
I={}; stat={'mapped':0,'first':0,'death':0,'fact':0,'said':0}
for o in FILES:
    f=o['f']; y,mo=o['date']; best=None
    for t in cand.get(f,[]):
        pv=pages.get((HOST(t),t))
        if not pv: continue
        d=ym(pv[1])
        if d and d[0]==y and (not mo or not d[1] or d[1]==mo): best=(t,pv); break
    if not best: continue
    host=HOST(best[0]); title,wt=best[1]; url=f'https://{host}/wiki/'+urllib.parse.quote(title.replace(' ','_'))
    fi,de,fa,sa=issue_facts(wt); stat['mapped']+=1
    if not(fi or de or fa or sa): I[f]={'u':url}; continue
    I[f]={'u':url,**({'first':fi} if fi else {}),**({'death':de} if de else {}),**({'n':fa} if fa else {}),**({'s':sa} if sa else {})}
    for k,v in (('first',fi),('death',de),('fact',fa),('said',sa)):
        if v: stat[k]+=1
# month context
def wp(title):
    q=urllib.parse.urlencode({'action':'parse','page':title,'prop':'wikitext','format':'json','redirects':1}); d=get('https://en.wikipedia.org/w/api.php?'+q)
    return d['parse']['wikitext']['*'] if d and 'parse' in d else ''
def month_events(wt,mo,n):
    name=MON[mo-1].capitalize(); m=re.search(r'\n==+\s*'+name+r'\s*==+(.*?)(?=\n==+\s*[A-Z])',wt,re.S)
    if not m: return []
    out=[]
    for line in m.group(1).split('\n'):
        if not line.startswith('*') or line.startswith('**'): continue
        t=clean(line); dm=re.match(r'^(?:'+name+r' )?(\d{1,2})(?:\s*[–-]\s*\d{1,2})?\s*[–—-]\s*',t); day=f'{name} {dm.group(1)}' if dm else ''
        if dm: t=t[dm.end():]
        if 25<=len(t)<=260 and not re.search(r'\bborn\b|\bdies\b|died',t): out.append((day,t))
        if len(out)>=n: break
    return out
months=sorted({tuple(o['date']) for o in FILES if o['f'] in I and o['date'][1]})
M={}; cache={}
for (y,mo) in months:
    us=cache.setdefault(('us',y),wp(f'{y} in the United States')); world=cache.setdefault(('w',y),wp(str(y)))
    e={}
    a=month_events(us,mo,3)
    if a: e['us']=[[t,d] for d,t in a]; e['usu']=f'https://en.wikipedia.org/wiki/{y}_in_the_United_States#{MON[mo-1].capitalize()}'
    b=month_events(world,mo,3)
    if b: e['w']=[[t,d] for d,t in b]; e['wu']=f'https://en.wikipedia.org/wiki/{y}#{MON[mo-1].capitalize()}'
    if e: M[f'{y}-{mo}']=e
stat['months_with_events']=len(M); stat['issues']=len(FILES)
open(os.path.join(HERE,'..','src','notes-data.js'),'w').write('// v54: "About this issue" — sourced facts from the Fandom comics wikis (i: by file name) and Wikipedia month events (m: "year-month"). Built by tools/gen_notes.py; every entry links its source.\nconst NOTES='+json.dumps({'i':I,'m':M},ensure_ascii=False,separators=(',',':'))+';\n')
print(json.dumps(stat))
