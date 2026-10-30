// Comic Shelf "Animate page" server (Cloudflare Worker). Holds the xAI key as a secret (env.XAI_API_KEY),
// requires the device passcode set once in the app, and enforces a daily spend cap.
const X='https://api.x.ai/v1', PLAN_MODEL='grok-4.3', VIDEO_MODEL='grok-imagine-video-1.5-lite';
const PRICE={sec:0.03,img:0.01,plan:0.03}, CAP=10, MAX_FAILS=20;
const H={'access-control-allow-origin':'*','access-control-allow-headers':'content-type,x-pass','access-control-allow-methods':'GET,POST,OPTIONS','access-control-max-age':'86400'};
const J=(o,s=200)=>new Response(JSON.stringify(o),{status:s,headers:{...H,'content-type':'application/json'}});
const day=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago'}).format(new Date());
const hex=b=>[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');
async function sha(s){ return hex(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))); }
async function spent(env){ return +(await env.KV.get('spend:'+day())||0); }
async function addSpend(env,v){ const k='spend:'+day(); const n=Math.max(0,(+(await env.KV.get(k)||0))+v); await env.KV.put(k,n.toFixed(4),{expirationTtl:86400*40}); return n; }
async function auth(req,env){ const a=await env.KV.get('auth',{type:'json'}); if(!a) return 'setup';
  const fk='fail:'+day(), fails=+(await env.KV.get(fk)||0); if(fails>=MAX_FAILS) return 'locked';
  const p=req.headers.get('x-pass')||''; if(p&&await sha(a.salt+p)===a.hash) return 'ok';
  await env.KV.put(fk,String(fails+1),{expirationTtl:172800}); return 'bad'; }
const AUTHMSG={setup:['Set a passcode in Settings first',401],bad:['Wrong passcode',401],locked:['Too many wrong passcodes today. Try again tomorrow.',429]};
async function key(env){ return (env.XAI_API_KEY||'').startsWith('xai-')?env.XAI_API_KEY:await env.KV.get('xai_key'); }
async function xai(env,path,init={}){ const r=await fetch(X+path,{...init,headers:{'authorization':'Bearer '+await key(env),'content-type':'application/json'}}); let j; try{ j=await r.json(); }catch(e){ j={}; } return {ok:r.ok,status:r.status,j}; }
const errText=j=>(j&&(j.error?.message||j.error||j.message||j.detail))||'';
const SYS=`You are a film director and storyboard artist adapting a single comic book page into a short animated sequence.
Find every panel on the page in reading order (left-to-right, top-to-bottom; right-to-left if the page is manga). For each panel return:
- box: [x,y,w,h] as fractions (0..1) of the full page image, tightly around the panel border (include the whole panel art, exclude gutters).
- what: one short sentence on what happens in the panel.
- prompt: a vivid image-to-video prompt (40-90 words) that animates THIS panel's art cinematically: subject motion, environment motion (wind, debris, light), facial acting, keep the comic art style and colors, no new characters, no on-screen text. Speech balloons and captions should stay still or fade.
- camera: the camera move (e.g. slow push-in, whip pan left, low-angle tilt up, static lock-off with rack focus).
- sound: music and sound design for the panel (instrumentation, dynamics, key sound effects).
- pacing: beat and timing note (e.g. "hold, then a sudden hit at 3s").
- seconds: integer clip length 5-8, longer for dramatic or dialogue-heavy beats.
Also return mood (overall tone of the page) and score (one sentence: how the music should build across the panels).`;
const SCHEMA={type:'object',additionalProperties:false,required:['mood','score','panels'],properties:{mood:{type:'string'},score:{type:'string'},panels:{type:'array',items:{type:'object',additionalProperties:false,required:['box','what','prompt','camera','sound','pacing','seconds'],properties:{box:{type:'array',items:{type:'number'}},what:{type:'string'},prompt:{type:'string'},camera:{type:'string'},sound:{type:'string'},pacing:{type:'string'},seconds:{type:'integer'}}}}}};
export default { async fetch(req,env){
  if(req.method==='OPTIONS') return new Response(null,{headers:H});
  const u=new URL(req.url), p=u.pathname;
  try{
    if(p==='/'||p==='/status'){ const a=await env.KV.get('auth'); return J({ok:true,configured:!!a,spent:+(await spent(env)).toFixed(2),cap:CAP,price:PRICE,model:VIDEO_MODEL}); }
    if(p==='/setup'&&req.method==='POST'){ const b=await req.json(); const pass=String(b.pass||''); if(pass.length<6) return J({error:'Use at least 6 characters'},400);
      const a=await env.KV.get('auth',{type:'json'}); if(a){ const old=String(b.old||''); if(!old||await sha(a.salt+old)!==a.hash) return J({error:'A passcode is already set. Enter the current one to change it.'},409); }
      const salt=hex(crypto.getRandomValues(new Uint8Array(16))); await env.KV.put('auth',JSON.stringify({salt,hash:await sha(salt+pass),at:Date.now()})); return J({ok:true}); }
    if(p==='/installkey'&&req.method==='POST'&&env.INSTALL_TOKEN){ const b=await req.json(); if(b.token!==env.INSTALL_TOKEN||!String(b.key||'').startsWith('xai-')) return J({error:'no'},403); await env.KV.put('xai_key',b.key); return J({ok:true}); }
    const st=await auth(req,env); if(st!=='ok'){ const [m,s]=AUTHMSG[st]; return J({error:m,auth:st},s); }
    if(p==='/check') return J({ok:true,spent:+(await spent(env)).toFixed(2),cap:CAP});
    if(p==='/plan'&&req.method==='POST'){ const b=await req.json(); if(!/^data:image\/(jpeg|png);base64,/.test(b.image||'')) return J({error:'Missing page image'},400);
      if(await spent(env)+PRICE.plan>CAP) return J({error:`Today's $${CAP} limit is used up. It resets at midnight.`,cap:true},402);
      const r=await xai(env,'/chat/completions',{method:'POST',body:JSON.stringify({model:PLAN_MODEL,temperature:0.6,messages:[{role:'system',content:SYS},{role:'user',content:[{type:'image_url',image_url:{url:b.image,detail:'high'}},{type:'text',text:`Comic: ${String(b.title||'').slice(0,120)}${b.rtl?' (manga, read right-to-left)':''}. Return the JSON plan.`}]}],response_format:{type:'json_schema',json_schema:{name:'page_plan',strict:true,schema:SCHEMA}}})});
      const ticks=r.j?.usage?.cost_in_usd_ticks; const cost=ticks?ticks/1e10:PRICE.plan; await addSpend(env,cost);
      if(!r.ok) return J({error:'Grok could not read this page: '+errText(r.j)},502);
      let plan; try{ plan=JSON.parse(r.j.choices[0].message.content); }catch(e){ return J({error:'Grok returned an unreadable plan'},502); }
      plan.panels=(plan.panels||[]).filter(q=>Array.isArray(q.box)&&q.box.length===4).slice(0,12).map(q=>{ let [x,y,w,h]=q.box.map(Number); x=Math.min(Math.max(x,0),1); y=Math.min(Math.max(y,0),1); w=Math.min(Math.max(w,.05),1-x); h=Math.min(Math.max(h,.05),1-y); return {...q,box:[x,y,w,h],seconds:Math.min(8,Math.max(5,Math.round(q.seconds||6)))}; });
      return J({plan,planCost:+cost.toFixed(4),spent:+(await spent(env)).toFixed(2),cap:CAP}); }
    if(p==='/clip'&&req.method==='POST'){ const b=await req.json(); if(!/^data:image\/(jpeg|png);base64,/.test(b.image||'')) return J({error:'Missing panel image'},400);
      const secs=Math.min(8,Math.max(1,Math.round(+b.seconds||5))), est=secs*PRICE.sec+PRICE.img;
      if(await spent(env)+est>CAP) return J({error:`Today's $${CAP} limit would be passed. It resets at midnight.`,cap:true},402);
      await addSpend(env,est);
      const r=await xai(env,'/videos/generations',{method:'POST',body:JSON.stringify({model:VIDEO_MODEL,prompt:String(b.prompt||'').slice(0,2000),image:{url:b.image},duration:secs,resolution:'720p'})});
      const id=r.j?.request_id; if(!r.ok||!id){ await addSpend(env,-est); return J({error:errText(r.j)||('HTTP '+r.status),refused:r.status===400||r.status===422},r.ok?502:r.status); }
      await env.KV.put('res:'+id,String(est),{expirationTtl:86400*2}); return J({id,cost:est}); }
    let m=p.match(/^\/clip\/([\w-]+)$/); if(m){ const r=await xai(env,'/videos/'+m[1]); const s=r.j?.status||(r.ok?'pending':'failed');
      if(s==='failed'||s==='expired'||!r.ok&&r.status!==404){ const k='res:'+m[1], v=await env.KV.get(k); if(v){ await env.KV.delete(k); await addSpend(env,-(+v)); } }
      return J({status:s,url:r.j?.video?.url||null,moderated:r.j?.video?.respect_moderation===false,error:errText(r.j)||null,raw_status:r.status}); }
    if(p==='/video'){ const t=u.searchParams.get('u')||''; let h; try{ h=new URL(t); }catch(e){ return J({error:'bad url'},400); }
      if(h.protocol!=='https:'||!/(^|\.)x\.ai$|(^|\.)xai\.|imgen\.x\.ai$/.test(h.hostname)) return J({error:'host not allowed: '+h.hostname},400);
      const r=await fetch(t); return new Response(r.body,{status:r.status,headers:{...H,'content-type':r.headers.get('content-type')||'video/mp4'}}); }
    return J({error:'not found'},404);
  }catch(e){ return J({error:String(e&&e.message||e)},500); } } };
