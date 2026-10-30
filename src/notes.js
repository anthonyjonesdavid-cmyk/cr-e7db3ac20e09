/* ================= v54: About this issue — sourced notes (built-in NOTES + live Look up), each fact with its source link ================= */
const NT_MON=['January','February','March','April','May','June','July','August','September','October','November','December'];
const ntHost=u=>{ try{ return new URL(u).hostname.replace(/^www\./,'').replace('en.wikipedia.org','Wikipedia').replace('marvel.fandom.com','Marvel Database').replace('dc.fandom.com','DC Database').replace('imagecomics.fandom.com','Image Comics Database'); }catch(e){ return 'source'; } };
const ntSrc=u=>`<a class="ntsrc" href="${esc(u)}" target="_blank" rel="noopener">${esc(ntHost(u))}</a>`;
function notesOf(c){ return c.notesLive||(c.fileName&&NOTES.i[c.fileName])||null; }
function monthOf(c){ const d=dateOf(c); if(!d||!d.m||d.src==='est') return null; const k=d.y+'-'+d.m; return {d,k,e:(c.monthLive&&c.monthLive.k===k?c.monthLive.e:null)||NOTES.m[k]||null}; }
function aboutBody(c){ const n=notesOf(c), mo=monthOf(c); let h='', m='';
  const li=(t,u)=>`<li>${esc(t)} ${ntSrc(u)}</li>`;
  if(n){ const L=[]; if(n.first) L.push(li('First appearance'+(n.first.length>1?'s':'')+': '+n.first.join(', ')+'.',n.u)); if(n.death) L.push(li('Death of '+n.death.join(', ')+'.',n.u)); (n.n||[]).forEach(t=>L.push(li(t,n.u)));
    if(L.length) h+=`<section class="ntg"><h3>Noteworthy</h3><ul>${L.join('')}</ul></section>`;
    if(n.s&&n.s.length) h+=`<section class="ntg"><h3>From the creators</h3><ul>${n.s.map(t=>li(t,n.u)).join('')}</ul></section>`; }
  if(mo&&mo.e){ const L=[]; (mo.e.us||[]).forEach(([t,d])=>L.push(li((d?d+': ':'')+t,mo.e.usu))); const W=(mo.e.w||[]).map(([t,d])=>li((d?d+': ':'')+t,mo.e.wu));
    if(L.length||W.length) m=`<section class="ntg"><h3>${NT_MON[mo.d.m-1]} ${mo.d.y}</h3>${L.length?`<h4>In the U.S.</h4><ul>${L.join('')}</ul>`:''}${W.length?`<h4>In the world</h4><ul>${W.join('')}</ul>`:''}</section>`; }
  return {h,m}; }
const AB={on:false,id:null,busy:false};
function openAbout(id){ const c=comics.find(x=>x.id===id); if(!c) return; const mw=document.querySelector('.mwrap'); if(mw){ const x=mw.querySelector('[data-r=cancel],[data-r=done]'); if(x) x.click(); else mw.remove(); }
  AB.id=id; $('#abName').textContent=c.title; const d=dateOf(c); $('#abSub').textContent=[c.series,d?fmtDate(d):''].filter(Boolean).join(' · '); renderAbout(); $('#abBody').scrollTop=0; $('#about').classList.remove('hidden'); AB.on=true; }
function renderAbout(){ const c=comics.find(x=>x.id===AB.id); if(!c) return; const {h,m}=aboutBody(c), n=notesOf(c);
  $('#abBody').innerHTML=`<div class="rinfo"><img src="${cover(c)}" alt=""><div>${creditsHTML(c)||'<p class="fhint">No creator credits for this issue.</p>'}</div></div>`+(h||`<p class="fhint ntnone">${n?'Nothing noteworthy on record for this issue.':'No notes for this issue yet.'} Only facts with a source are shown.</p>`)+m+
   `<div class="ntfoot"><button class="pillbtn" id="abLook">${AB.busy?'Looking up…':n?'Refresh':'Look up'}</button>${n&&n.u?`<span class="fhint">Issue facts from ${ntSrc(n.u)}</span>`:''}</div>`;
  $('#abLook').disabled=AB.busy; }
function closeAbout(){ $('#about').classList.add('hidden'); AB.on=false; }
// live look-up (Fandom + Wikipedia, both allow browser requests with origin=*)
const ntClean=s=>{ s=String(s).replace(/<ref[^>]*\/>|<ref[\s\S]*?<\/ref>|<!--[\s\S]*?-->|<[^>]+>/g,''); for(let i=0;i<3;i++) s=s.replace(/\{\{([^{}]*)\}\}/g,(m,b)=>{ const p=b.split('|'), k=p[0].trim().toLowerCase(); return ['1st','death','mentioned','flashback','dies'].includes(k)&&p[1]?p[1]:['w','wp','wikipedia','cl','sic','c','m','a','apn','ml','g','mel'].includes(k)&&p.length>1?p[p.length-1]:''; });
  return s.replace(/\[\[(?:[^\]|]*\|)?([^\]]*)\]\]/g,'$1').replace(/\[https?:\/\/\S+ ([^\]]*)\]/g,'$1').replace(/'{2,}/g,'').replace(/\s*\((?:Earth|Earth-\d+)[^)]*\)/g,'').replace(/\s+/g,' ').replace(/&(#?\w+);/g,(m)=>{ const t=document.createElement('textarea'); t.innerHTML=m; return t.value; }).replace(/^[\s*:]+|[\s*:]+$/g,''); };
const NT_SKIP=/letters? (page|column)|letter column|bullpen|marvel age|checklist|advertis|reprint|pin-?up|recap|dedicated|soapbox|continued (from|in)|continues|takes place|chronolog|placement|this story|is set|occurs (before|after)|variant|newsstand|price|hype box|mail|published in|editorial|statement of ownership/i;
const NT_KEY=/\bfirst\b|debut|origin|death|dies|killed|final|last appearance|return|reveal|wedding|marri|join|introduc|becomes|identity|1st/i, NT_SAID=/\b(said|stated|recalled|explained|interview|according to|commented|admitted|wanted to)\b/i;
function ntParse(wt,url){ const uniq=a=>[...new Set(a.filter(Boolean))]; const first=uniq([...wt.matchAll(/\{\{1st(?: Dies| Full| Identified)?\|\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g)].map(m=>ntClean(m[2]||m[1]))).slice(0,8);
  const names=[...wt.matchAll(/\|\s*(?:Writer|Penciler|Penciller|Artist|Inker)\d*(?:_\d+)?\s*=([^\n]+)/g)].map(m=>ntClean(m[1])).filter(Boolean);
  const death=uniq([...wt.matchAll(/\{\{Death\|\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g)].map(m=>ntClean(m[2]||m[1]))).slice(0,4); const n=[], s=[];
  for(const k of ['Notes','Trivia']){ const m=wt.match(new RegExp('\\|\\s*'+k+'\\s*=([\\s\\S]*?)(?=\\n\\|\\s*\\w+\\s*=|\\n\\}\\}\\s*$)')); if(!m) continue;
    for(const b of m[1].split(/\n\s*\*+/)){ const t=ntClean(b); if(t.length<20||t.length>320||NT_SKIP.test(t)||!/[.!?"”)]$/.test(t)) continue; if(NT_SAID.test(t)){ if(names.some(x=>t.includes(x.split(' ').pop()))) s.push(t); } else if(NT_KEY.test(t)) n.push(t); } }
  const o={u:url}; if(first.length) o.first=first; if(death.length) o.death=death; if(n.length) o.n=n.slice(0,4); if(s.length) o.s=s.slice(0,2); return o; }
async function ntWiki(host,titles){ const r=await fetch(`https://${host}/api.php?`+new URLSearchParams({action:'query',prop:'revisions',rvprop:'content',rvslots:'main',format:'json',redirects:1,origin:'*',titles:titles.join('|')})); const j=await r.json();
  return Object.values((j.query||{}).pages||{}).filter(p=>p.revisions).map(p=>({title:p.title,wt:p.revisions[0].slots.main['*']})); }
async function lookupNotes(c){ const d=dateOf(c), no=issueNo(c.title); const ser=(c.series||c.title.replace(/[\s#-]*\d+.*$/,'')).replace(/\(.*?\)/g,'').replace(/\s+/g,' ').trim();
  let found=null;
  if(ser&&no<1e6&&isFinite(no)){ const T=[1,2,3,4,5].map(v=>`${ser} Vol ${v} ${no}`);
    for(const host of ['marvel.fandom.com','dc.fandom.com','imagecomics.fandom.com']){ let P=[]; try{ P=await ntWiki(host,T); }catch(e){ continue; }
      const ok=P.filter(p=>{ const y=+(p.wt.match(/\|\s*Year\s*=\s*(\d{4})/)||[])[1]; return d?y===d.y:P.length===1; });
      if(ok.length){ found=ntParse(ok[0].wt,`https://${host}/wiki/`+encodeURIComponent(ok[0].title.replace(/ /g,'_'))); break; } } }
  if(found) c.notesLive=found;
  if(d&&d.m&&d.src!=='est'&&!NOTES.m[d.y+'-'+d.m]){ try{ const name=NT_MON[d.m-1], e={};
    for(const [k,pg] of [['us',`${d.y} in the United States`],['w',String(d.y)]]){ const j=await (await fetch('https://en.wikipedia.org/w/api.php?'+new URLSearchParams({action:'parse',page:pg,prop:'wikitext',format:'json',redirects:1,origin:'*'}))).json(); const wt=j.parse?j.parse.wikitext['*']:'';
      const m=wt.match(new RegExp('\\n==+\\s*'+name+'\\s*==+([\\s\\S]*?)(?=\\n==+\\s*[A-Z])')); if(!m) continue; const L=[];
      for(const line of m[1].split('\n')){ if(!/^\*[^*]/.test(line)) continue; const dm=line.match(new RegExp('^\\*\\s*\\[\\[('+name+' \\d+)')); const t=ntClean(line).replace(new RegExp('^'+name+' \\d+(?:–\\d+)?\\s*[–-]\\s*'),''); if(t.length>=25&&t.length<=260&&!/\bborn\b|\bdies\b|died/.test(t)) L.push([t,dm?dm[1]:'']); if(L.length>=3) break; }
      if(L.length){ e[k]=L; e[k==='us'?'usu':'wu']=`https://en.wikipedia.org/wiki/${encodeURIComponent(pg.replace(/ /g,'_'))}#${name}`; } }
    if(Object.keys(e).length) c.monthLive={k:d.y+'-'+d.m,e}; }catch(e){} }
  await dbPut(c); return !!found; }
$('#abClose').addEventListener('click',closeAbout);
$('#about').addEventListener('click',async e=>{ if(e.target.closest('#abLook')){ const c=comics.find(x=>x.id===AB.id); if(!c||AB.busy) return; AB.busy=true; renderAbout(); let ok=false; try{ ok=await lookupNotes(c); }catch(err){} AB.busy=false; renderAbout(); toast(ok?'Updated from the comics wiki':'No sourced page found for this issue'); } });
document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&AB.on&&!CRP.on) closeAbout(); });
edgeBack($('#about'),closeAbout);
