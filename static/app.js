const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const eur = v => (v ?? 0).toLocaleString(I18N.locale(), {style:'currency', currency:'EUR'});
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let S = {}, PRINTERS = [], MATS = [], PRODUCTS = [], STATUSES = [], lastCalc = null, curOrder = null, orderFilter = '';
const COLORS = ['#3fae6a','#f0a35e','#e8572a','#d9a400','#1f6f5c','#4a9c86','#3b6fb6','#8a63c9','#b44f8c','#7a7a72'];
const LABELS = {material:'Material',merma:'Merma',electricidad:'Electricidad',amortizacion:'Amortización',mantenimiento:'Mantenimiento',preparacion:'Preparación',postprocesado:'Postprocesado',extras:'Otros gastos',riesgo_fallo:'Riesgo fallo'};

function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('on');setTimeout(()=>t.classList.remove('on'),1800)}
async function api(path, opts={}){
  const r = await fetch('/api'+path, {headers:{'Content-Type':'application/json'}, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined});
  if (r.status === 401 && path !== '/login'){ showLogin(); throw new Error('auth'); }
  const j = await r.json().catch(()=>({}));
  if (!r.ok){ toast(j.error || 'Error'); throw new Error(j.error); }
  return j;
}
const opts = (arr, sel, map=x=>[x,x]) => arr.map(x=>{const [v,l]=map(x);return `<option value="${esc(v)}" ${String(v)===String(sel)?'selected':''}>${esc(l)}</option>`}).join('');

// ---------- auth
function showLogin(){ $('#app').classList.add('hidden'); $('#login').classList.remove('hidden'); }
async function doLogin(e){ e.preventDefault();
  try{ await api('/login',{method:'POST',body:{username:$('#lu').value,password:$('#lp').value}}); boot(); }
  catch(err){ $('#lerr').textContent = err.message || 'Usuario o contraseña incorrectos'; } }
async function doLogout(){ await api('/logout',{method:'POST'}); showLogin(); }

let BRAND = {}, ME = {};
async function loadBrand(){
  BRAND = await fetch('/api/brand').then(r=>r.json()).catch(()=>({}));
  const name = BRAND.shop_name || 'MiTallercito';
  document.title = name; $$('.b-name').forEach(e=>e.textContent=name); $$('.b-tag').forEach(e=>e.textContent=BRAND.shop_tagline||'');
  $$('.b-logo').forEach(e=>{ e.classList.toggle('hidden', !BRAND.logo_url); if(BRAND.logo_url) e.src = BRAND.logo_url; });
  $('#fav').href = (BRAND.favicon_url || '/favicon.ico') + '?v=' + Date.now();
  if (BRAND.accent_color) document.documentElement.style.setProperty('--acc', BRAND.accent_color);
  I18N.setLang(BRAND.language || 'es');
}
// ---------- primer arranque
const MAT_PRESETS = [{name:'PLA',kind:'PLA',price:18,qty:1000,unit:'g',on:true},{name:'PETG',kind:'PETG',price:20,qty:1000,unit:'g',on:true},
  {name:'ABS/ASA',kind:'ABS',price:22,qty:1000,unit:'g',on:false},{name:'TPU',kind:'TPU',price:30,qty:1000,unit:'g',on:false},
  {name:'Resina estándar',kind:'Resina',price:30,qty:1000,unit:'ml',on:false}];
function suPrinter(){ const d=document.createElement('div'); d.className='row su-p'; d.style.marginBottom='8px';
  d.innerHTML=`<div style="flex:3"><label>Nombre</label><input class="sp-n" placeholder="p.ej. Prusa MK4"></div><div><label>W medios</label><input class="sp-w" type="number" value="150"></div><div><label>Precio €</label><input class="sp-c" type="number" placeholder="600"></div><button class="btn sec sm" style="align-self:end" onclick="this.parentNode.remove()">✕</button>`;
  $('#su-printers').append(d); }
function suMat(m){ const d=document.createElement('div'); d.className='row su-m'; d.style.marginBottom='6px';
  d.innerHTML=`<label class="switch" style="flex:0 0 auto;margin:0"><input type="checkbox" class="sm-on" ${m.on?'checked':''}></label><div style="flex:2"><input class="sm-n" value="${esc(t(m.name))}" placeholder="Nombre"></div>
    <div><input class="sm-k" value="${esc(t(m.kind))}" placeholder="Tipo"></div><div><input class="sm-p" type="number" step="0.01" value="${m.price}" placeholder="€ envase"></div>
    <div><input class="sm-q" type="number" value="${m.qty}"></div><div style="flex:0 0 70px"><select class="sm-u">${opts(['g','ml'],m.unit)}</select></div>`;
  $('#su-mats').append(d); }
async function showSetup(){
  $('#login').classList.add('hidden'); $('#app').classList.add('hidden'); $('#setup').classList.remove('hidden');
  const tk = (location.hash.match(/setup=([\w-]+)/)||[])[1]; if (tk) $('#su-token').value = tk;
  if (!/^(es|ca|gl|eu)/.test(navigator.language||'es')) I18N.setLang('en');   // navegador en otro idioma → inglés por defecto
  $('#su-lang').value = I18N.lang;
  if (!$('#su-printers').children.length){ suPrinter(); MAT_PRESETS.forEach(suMat); }
  $('#su-mats').oninput = () => $('#su-mats').dataset.touched = '1';
}
async function doSetup(){
  $('#su-err').textContent='';
  if ($('#su-pw').value !== $('#su-pw2').value) return $('#su-err').textContent='Las contraseñas no coinciden';
  const vat = +$('#su-vat').value;
  const body = {token:$('#su-token').value.trim(), admin:{username:$('#su-user').value, password:$('#su-pw').value},
    shop_name:$('#su-shop').value, people:$('#su-people').value.split(',').map(x=>x.trim()).filter(Boolean),
    kwh_price:$('#su-kwh').value, margin_pct:$('#su-margin').value, prep_rate:$('#su-rate').value, post_rate:$('#su-rate').value,
    apply_vat: vat>0, vat_pct: vat||21, language: $('#su-lang').value,
    printers: $$('#su-printers .su-p').map(r=>({name:r.querySelector('.sp-n').value, watts:r.querySelector('.sp-w').value, cost:r.querySelector('.sp-c').value})),
    materials: $$('#su-mats .su-m').filter(r=>r.querySelector('.sm-on').checked).map(r=>({name:r.querySelector('.sm-n').value, kind:r.querySelector('.sm-k').value,
      price:r.querySelector('.sm-p').value, qty:r.querySelector('.sm-q').value, unit:r.querySelector('.sm-u').value}))};
  const r = await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}), j = await r.json().catch(()=>({}));
  if (!r.ok) return $('#su-err').textContent = j.error || 'Error';
  history.replaceState(null,'',location.pathname); $('#setup').classList.add('hidden'); toast('¡Tienda creada!'); boot();
}

async function boot(){
  await loadBrand();
  const su = await fetch('/api/setup').then(r=>r.json()).catch(()=>({}));
  if (su.needed) return showSetup();
  const me = await api('/me'); if(!me.user) return showLogin();
  ME = me; document.body.classList.toggle('is-admin', me.role==='admin');
  $('#who').textContent = me.user + (me.role==='admin' ? ' (admin)' : ''); $('#login').classList.add('hidden'); $('#app').classList.remove('hidden');
  [S, PRINTERS, MATS, PRODUCTS] = await Promise.all([api('/settings'), api('/printers'), api('/materials'), api('/products')]);
  STATUSES = (await api('/meta')).statuses;
  api('/version').then(v=>{ $('#ver').textContent='v'+v.version; $('#ver2').textContent='v'+v.version; }).catch(()=>{});
  const v = location.hash.slice(1); initCalc(); refreshLowStock(); loadSpools(); loadClientList();
  const om = v.match(/^order=(\d+)$/), sm = v.match(/^spool=(\d+)$/), lm = v.match(/^loc=(\d+)$/);   // avisos de Telegram, etiquetas QR
  if (lm){ STK_TAB = 'loc'; show('stk'); openLoc(+lm[1]); return; }
  document.body.classList.toggle('has-mf', !!S.manyfold_url);
  show(sm ? 'stk' : /^[a-z]+$/.test(v) ? v : 'home'); if (om) openOrder(+om[1]); if (sm) openSpoolQuick(+sm[1]);
}
function drawer(on){ document.body.classList.toggle('drawer', !!on); }
function show(v){
  $$('#nav [data-v],#tabbar [data-v]').forEach(b=>b.classList.toggle('on', b.dataset.v===v));
  const inTab = !!$(`#tabbar [data-v="${v}"]`); $('#tabbar [data-more]')?.classList.toggle('on', !inTab);
  drawer(false); window.scrollTo(0,0);
  $$('main>section').forEach(s=>s.classList.toggle('hidden', s.id!=='v-'+v));
  $('#pos-bar').classList.remove('on');
  location.hash = v;
  clearInterval(prnTimer);
  ({home:loadHome, pos:loadPos, cli:loadClients, stk:()=>{ loadStock(); loadForecast(); loadShopping(); ensureLocs(); stkTab(STK_TAB); }, orders:loadOrders, acc:()=>{ loadAcc(); loadRecurring(); }, rep:loadRep, prn:loadPrinters, cat:loadCat, cfg:loadCfg, mnt:()=>{ loadUpdate().then(u=>{ if (u.repo && !u.docker) checkRelease(); else $('#u-rel').innerHTML = u.docker ? '' : '<span class="mut">Sin repositorio configurado: sube el paquete a mano.</span>'; }).catch(()=>{}); }})[v]?.();
}
document.addEventListener('click', e => { const b = e.target.closest('#nav [data-v],#tabbar [data-v]'); if (b) show(b.dataset.v); });

// ---------- calculadora
function initCalc(){
  $('#c-printer').innerHTML = opts(PRINTERS.filter(p=>p.active), '', p=>[p.id,p.name]);
  $('#c-margin').value = S.margin_pct; $('#c-sale').value = S.sale_type; $('#c-comm').value = S.commission_pct;
  $('#c-commf').value = S.commission_fixed; $('#c-round').value = S.rounding; $('#c-min').value = S.min_price; $('#c-vat').value = S.apply_vat?1:0;
  if (!$('#c-mats').children.length) addMatRow();
  setMatMode(matMode, false);
  $('#v-calc').oninput = $('#v-calc').onchange = e => { if (!e.target.closest('#c-name,#sl-file,#c-mine')) markStale(); };
  $('#v-calc').onkeydown = e => { if (e.key==='Enter' && e.target.matches('input') && !e.target.closest('#c-name,#c-mine')){ e.preventDefault(); runCalc(); } };
  markStale();
}
let matMode = (()=>{try{return localStorage.getItem('matMode')||'grams'}catch(e){return 'grams'}})();
function setMatMode(m, recalc=true){
  matMode = m; try{localStorage.setItem('matMode', m)}catch(e){}
  $('#mm-grams').classList.toggle('sec', m!=='grams'); $('#mm-direct').classList.toggle('sec', m!=='direct');
  $('#mm-direct-box').classList.toggle('hidden', m!=='direct');
  if (recalc) markStale();
}
function matOpts(sel){ return opts(MATS.filter(m=>m.active), sel, m=>[m.id, `${m.name}${m.color?' · '+m.color:''} (${m.unit})${m.stock_level!=null?' · quedan '+qfmt(m.stock_level,m.unit):''}`]); }
let SPOOLS = [];
async function loadSpools(){ try { SPOOLS = await api('/spools'); } catch(e){ SPOOLS = []; } }
const spoolLabel = sp => `${sp.brand?sp.brand+' ':''}${sp.color_name||'sin color'} · ${qfmt(sp.remaining, sp.unit)}${sp.location?' · '+sp.location:''}`;
function spoolOpts(mid, sel){
  const sps = SPOOLS.filter(s=>s.material_id==mid);
  return `<option value="">${sps.length?'bobina: automática':'sin bobinas en el almacén'}</option>` + sps.map(sp=>`<option value="${sp.id}" ${sp.id==sel?'selected':''}>● ${esc(spoolLabel(sp))}</option>`).join('');
}
function addMatRow(mid='', amt='', swatch='', spool=''){
  const d = document.createElement('div'); d.className='row'; d.style.marginBottom='8px'; d.style.flexWrap='wrap';
  d.innerHTML = `${swatch?`<span title="${esc(swatch)}" style="flex:0 0 18px;min-width:0;height:18px;border-radius:50%;border:1px solid var(--line);background:${esc(swatch)};align-self:center"></span>`:''}<div style="flex:3"><select class="cm-id">${matOpts(mid)}</select></div><div><input class="cm-amt" type="number" min="0" placeholder="g / ml" value="${amt}"></div><button class="btn sec sm" onclick="this.parentNode.remove();markStale()">✕</button>
    <div style="flex:1 1 100%"><select class="cm-sp" style="font-size:13px;padding:5px 8px">${spoolOpts(mid || d.querySelector?.('.cm-id')?.value, spool)}</select></div>`;
  $('#c-mats').append(d);
  const sel = d.querySelector('.cm-id'), sp = d.querySelector('.cm-sp');
  if (!mid) sp.innerHTML = spoolOpts(sel.value, spool);
  sel.addEventListener('change', ()=>{ sp.innerHTML = spoolOpts(sel.value, ''); });
}
function addExtraRow(c='', a=''){
  const d = document.createElement('div'); d.className='row'; d.style.marginBottom='8px';
  d.innerHTML = `<div style="flex:3"><input class="ce-c" placeholder="Concepto" value="${esc(c)}"></div><div><input class="ce-a" type="number" step="0.01" placeholder="€" value="${a}"></div><button class="btn sec sm" onclick="this.parentNode.remove();markStale()">✕</button>`;
  $('#c-extras').append(d);
}
function calcInput(){
  return {
    printer_id: $('#c-printer').value, hours: $('#c-hours').value, minutes: $('#c-minutes').value, units: $('#c-units').value,
    material_mode: matMode, material_cost: $('#c-matcost').value,
    materials: $$('#c-mats .row').map(r=>({material_id:r.querySelector('.cm-id').value, amount:r.querySelector('.cm-amt').value, spool_id:r.querySelector('.cm-sp')?.value||''})),
    prep_min: $('#c-prep').value, post_min: $('#c-post').value,
    extras: $$('#c-extras .row').map(r=>({concept:r.querySelector('.ce-c').value, amount:r.querySelector('.ce-a').value})),
    margin_pct: $('#c-margin').value, sale_type: $('#c-sale').value, commission_pct: $('#c-comm').value,
    commission_fixed: $('#c-commf').value, rounding: $('#c-round').value, min_price: $('#c-min').value, apply_vat: $('#c-vat').value==='1'
  };
}
function loadCalcInput(d){
  $('#c-printer').value = d.printer_id; $('#c-hours').value = d.hours; $('#c-minutes').value = d.minutes; $('#c-units').value = d.units;
  $('#c-mats').innerHTML=''; (d.materials||[]).forEach(m=>addMatRow(m.material_id, m.amount, '', m.spool_id||'')); if(!(d.materials||[]).length) addMatRow();
  $('#c-extras').innerHTML=''; (d.extras||[]).forEach(e=>addExtraRow(e.concept, e.amount));
  $('#c-prep').value = d.prep_min; $('#c-post').value = d.post_min;
  $('#c-matcost').value = d.material_cost ?? ''; setMatMode(d.material_mode || 'grams', false);
  ['margin_pct:c-margin','sale_type:c-sale','commission_pct:c-comm','commission_fixed:c-commf','rounding:c-round','min_price:c-min'].forEach(p=>{const [k,id]=p.split(':'); if(d[k]!==undefined) $('#'+id).value=d[k];});
  if (d.apply_vat!==undefined) $('#c-vat').value = d.apply_vat?1:0;
  runCalc();
}
let calcStale = false;
function markStale(){
  calcStale = true;
  $('#r-stale').classList.toggle('hidden', !lastCalc);
  $('#c-calc').textContent = lastCalc ? 'Recalcular' : 'Calcular';
  $('#r-price').style.opacity = $('#r-price-ex').style.opacity = $('#r-table').style.opacity = lastCalc ? .4 : 1;
}
function resetCalc(){
  ['#c-hours','#c-minutes','#c-prep','#c-post','#c-matcost','#c-name','#c-mine'].forEach(x=>$(x).value=''); $('#c-units').value=1;
  $('#c-mats').innerHTML=''; addMatRow(); $('#c-extras').innerHTML=''; $('#sl-result').classList.add('hidden'); $('#sl-file').value=''; IMPORTED = null;
  initCalc(); lastCalc = null; calcStale = true; $('#r-mine').classList.add('hidden');
  $('#r-price').textContent='–'; $('#r-price-ex').textContent='–'; $('#r-title').textContent='Precio total'; $('#r-adj').classList.add('hidden'); $('#r-sub').textContent='Rellena los datos y pulsa Calcular.';
  ['#r-cost','#r-profit','#r-batch'].forEach(x=>$(x).textContent='–'); ['#r-bar','#r-legend','#r-table'].forEach(x=>$(x).innerHTML='');
  markStale();
}
async function runCalc(){
  const ci = calcInput(), hasTime = (+ci.hours||0)+(+ci.minutes||0) > 0, hasMat = ci.materials.some(m=>+m.amount>0) || (ci.material_mode==='direct' && +ci.material_cost>0);
  if (!hasTime && !hasMat) return toast('Mete al menos el tiempo de impresión o el material');
  const r = lastCalc = await api('/calc',{method:'POST',body:ci});
  calcStale = false; $('#r-stale').classList.add('hidden'); $('#c-calc').textContent = 'Recalcular';
  $('#r-price').style.opacity = $('#r-price-ex').style.opacity = $('#r-table').style.opacity = 1;
  const u = r.unit, n = r.units;
  const pieceEx = u.price_ex_vat, pieceInc = r.sale_type==='B2C' ? u.price : u.price_inc_vat;
  const totEx = pieceEx*n, totInc = pieceInc*n;
  $('#r-title').textContent = n>1 ? `Precio total (${n} piezas)` : 'Precio total';
  $('#r-price-ex').textContent = eur(totEx); $('#r-price').textContent = eur(totInc);
  $('#r-sub').innerHTML = (n>1 ? `Por pieza: <b>${eur(pieceEx)}</b> sin IVA · <b>${eur(pieceInc)}</b> con IVA` : '') +
     (r.vat_pct ? '' : `${n>1?' · ':''}sin IVA aplicado`);
  const adj = [];
  if (u.min_applied) adj.push(`Se aplica el <b>precio mínimo</b> de ${eur(u.min_price)}: con tu margen saldría a <b>${eur(u.raw)}</b>. Por eso cambiar el margen no mueve el precio hasta que lo supere. Puedes bajarlo en «Precio mínimo €».`);
  else if (Math.abs(u.price - u.raw) > 0.005) adj.push(`Redondeado desde <b>${eur(u.raw)}</b> (redondeo «${$('#c-round').selectedOptions[0].text}»). Cambios pequeños de margen pueden dar el mismo precio.`);
  $('#r-adj').innerHTML = adj.join('<br>'); $('#r-adj').classList.toggle('hidden', !adj.length);
  $('#r-cost').textContent = eur(r.cost_unit*n);
  $('#r-profit').textContent = eur(r.profit_unit*n); $('#r-profit').className = 'v ' + (r.profit_unit>=0?'pos':'neg');
  $('#r-batch').textContent = eur(totInc - totEx);
  const b = r.breakdown, tot = Object.values(b).reduce((a,c)=>a+c,0) || 1, keys = Object.keys(b).filter(k=>b[k]>0);
  $('#r-bar').innerHTML = keys.map((k,i)=>`<i style="width:${b[k]/tot*100}%;background:${COLORS[i%9]}"></i>`).join('');
  $('#r-legend').innerHTML = keys.map((k,i)=>`<span><b style="background:${COLORS[i%9]}"></b>${LABELS[k]}</span>`).join('');
  $('#r-table').innerHTML = keys.map(k=>`<tr><td>${LABELS[k]}</td><td class="n">${eur(b[k])}</td><td class="n mut">${(b[k]/tot*100).toFixed(0)}%</td></tr>`).join('')
    + `<tr><th>Coste total (${r.units} pz · ${r.hours} h)</th><th class="n">${eur(r.cost)}</th><th></th></tr>`
    + `<tr><td>Margen</td><td class="n">${eur(r.margin)}</td><td></td></tr>`
    + (r.commission ? `<tr><td>Comisión plataforma</td><td class="n">${eur(r.commission)}</td><td></td></tr>` : '');
  $('#r-mine').classList.remove('hidden'); mineCalc();
}
// Precio propio: qué te queda si cobras otra cosa
function minePrice(){ const v = num($('#c-mine').value); return v>0 ? v : null; }
function mineCalc(){
  const r = lastCalc, out = $('#r-mine-out'); if (!r) return;
  const b2c = r.sale_type==='B2C', vat = (r.vat_pct||0)/100, n = r.units, cp = (r.commission_pct||0)/100, cf = r.commission_fixed||0;
  $('#c-mine-l').textContent = b2c && vat ? '¿Prefieres otro precio? Tu precio por pieza (con IVA)' : '¿Prefieres otro precio? Tu precio por pieza' + (vat ? ' (sin IVA)' : '');
  const v = minePrice(); $('#c-mine-x').classList.toggle('hidden', v==null);
  const costU = r.cost / n, sugg = b2c ? r.unit.price : r.unit.price_ex_vat;
  const toShown = ex => b2c ? ex*(1+vat) : ex;
  const even = toShown((costU + cf/n) / (1 - cp));
  if (v==null){ out.innerHTML = `<div class="mut" style="font-size:12.5px;margin-top:6px">Para no perder dinero, como mínimo <b>${eur(even)}</b> por pieza.</div>`; return; }
  const ex = b2c ? v/(1+vat) : v, inc = b2c ? v : v*(1+vat), comm = ex*cp + cf/n, prof = ex - comm - costU, pct = costU ? prof/costU*100 : 0;
  const diff = (v - sugg) * n, cls = prof>=0 ? 'pos' : 'neg';
  out.innerHTML = `<div class="grid g3 mine-k">
      <div class="kpi"><div class="v ${cls}">${eur(prof*n)}</div><div class="l">${prof>=0?'ganas':'pierdes'} (total)</div></div>
      <div class="kpi"><div class="v ${cls}">${eur(prof)}</div><div class="l">por pieza</div></div>
      <div class="kpi"><div class="v ${cls}">${pct.toFixed(0)} %</div><div class="l">sobre el coste</div></div></div>
    <table class="nocards" style="font-size:13.5px">
      ${n>1?`<tr><td>Cobras en total</td><td class="n"><b>${eur(inc*n)}</b>${vat?` <span class="mut">(${eur(ex*n)} sin IVA)</span>`:''}</td></tr>`:''}
      ${vat?`<tr><td>IVA a ingresar</td><td class="n">${eur((inc-ex)*n)}</td></tr>`:''}
      ${comm?`<tr><td>Comisión plataforma</td><td class="n">${eur(comm*n)}</td></tr>`:''}
      <tr><td>Te cuesta</td><td class="n">${eur(r.cost)}</td></tr>
      <tr><td>Frente al calculado (${eur(sugg)})</td><td class="n ${diff>=0?'pos':'neg'}">${diff>=0?'+':'−'}${eur(Math.abs(diff))}</td></tr>
      <tr><td>Mínimo para no perder</td><td class="n">${eur(even)} / pieza</td></tr></table>
    ${prof<0?'<div class="warn" style="font-size:13px;margin-top:6px">Con este precio pierdes dinero.</div>':''}
    <div class="mut" style="font-size:12px;margin-top:6px">Al guardar en el catálogo o añadir al pedido se usa tu precio.</div>`;
}
// precio unitario a usar (el propio si lo hay), en la misma base que unit.price
function calcUnitPrice(){ return minePrice() ?? lastCalc.unit.price; }
function debounce(f, ms){ let t; return (...a)=>{clearTimeout(t); t=setTimeout(()=>f(...a), ms)} }
async function saveProduct(){
  if (!lastCalc || calcStale) return toast('Pulsa Calcular primero');
  const name = $('#c-name').value.trim(); if(!name) return toast('Ponle nombre');
  const pr = await api('/products',{method:'POST',body:{name, calc_json:calcInput(), unit_price:calcUnitPrice(), unit_cost:lastCalc.cost_unit, print_info:currentPrintInfo()}});
  if (IMPORTED?.file) await uploadModel(IMPORTED.file, {product_id: pr.id});
  PRODUCTS = await api('/products'); toast('Guardado en catálogo' + (IMPORTED?.file ? ' con su archivo' : ''));
}
function toOrder(){
  if (!lastCalc || calcStale) return toast('Pulsa Calcular primero');
  const name = $('#c-name').value.trim() || 'Pieza impresa';
  openOrder(null, [{description:name, qty:lastCalc.units, unit_price:calcUnitPrice(), unit_cost:lastCalc.cost_unit, calc_json:calcInput(), calc_result:lastCalc, print_info:currentPrintInfo()}],
            IMPORTED?.file ? [IMPORTED.file] : []);
}

// ---------- importar del laminador (todo en el navegador)
const HEAD = 768*1024, TAIL = 768*1024;
async function headTailText(blob){
  const dec = new TextDecoder('utf-8', {fatal:false});
  if (blob.size <= HEAD+TAIL) return dec.decode(await blob.arrayBuffer());
  return dec.decode(await blob.slice(0,HEAD).arrayBuffer()) + '\n' + dec.decode(await blob.slice(blob.size-TAIL).arrayBuffer());
}
// Lector ZIP mínimo (3MF = zip), con ZIP64
async function zipIndex(file){
  const tailLen = Math.min(file.size, 70000), tail = new DataView(await file.slice(file.size-tailLen).arrayBuffer());
  let e = -1; for (let i=tailLen-22;i>=0;i--) if (tail.getUint32(i,true)===0x06054b50){ e=i; break; }
  if (e<0) throw new Error('no es un ZIP/3MF válido');
  let cdSize = tail.getUint32(e+12,true), cdOff = tail.getUint32(e+16,true);
  if (cdOff===0xFFFFFFFF && e>=20 && tail.getUint32(e-20,true)===0x07064b50){
    const z64 = Number(tail.getBigUint64(e-20+8,true)), rec = new DataView(await file.slice(z64, z64+56).arrayBuffer());
    cdSize = Number(rec.getBigUint64(40,true)); cdOff = Number(rec.getBigUint64(48,true));
  }
  const cd = new DataView(await file.slice(cdOff, cdOff+cdSize).arrayBuffer()), td = new TextDecoder(), out = {};
  for (let p=0; p+46<=cd.byteLength && cd.getUint32(p,true)===0x02014b50;){
    const method=cd.getUint16(p+10,true), nl=cd.getUint16(p+28,true), xl=cd.getUint16(p+30,true), cl=cd.getUint16(p+32,true);
    let csize=cd.getUint32(p+20,true), usize=cd.getUint32(p+24,true), loff=cd.getUint32(p+42,true);
    const name = td.decode(new Uint8Array(cd.buffer, p+46, nl));
    for (let x=p+46+nl; x<p+46+nl+xl;){ const id=cd.getUint16(x,true), sz=cd.getUint16(x+2,true);
      if (id===1){ let q=x+4; if(usize===0xFFFFFFFF){usize=Number(cd.getBigUint64(q,true));q+=8} if(csize===0xFFFFFFFF){csize=Number(cd.getBigUint64(q,true));q+=8} if(loff===0xFFFFFFFF){loff=Number(cd.getBigUint64(q,true))} }
      x+=4+sz; }
    out[name] = {method, csize, usize, loff}; p += 46+nl+xl+cl;
  }
  return out;
}
async function zipEntryBlob(file, ent){
  const lh = new DataView(await file.slice(ent.loff, ent.loff+30).arrayBuffer());
  const start = ent.loff + 30 + lh.getUint16(26,true) + lh.getUint16(28,true), raw = file.slice(start, start+ent.csize);
  if (ent.method===0) return raw;
  if (ent.method!==8) throw new Error('compresión no soportada');
  return raw.stream().pipeThrough(new DecompressionStream('deflate-raw'));
}
async function streamHeadTail(stream){   // para G-code dentro del 3MF: sin cargarlo entero
  const r = stream.getReader(), head=[], tail=[]; let hn=0, tn=0;
  for(;;){ const {done, value} = await r.read(); if (done) break;
    if (hn < HEAD){ head.push(value); hn += value.length; continue; }
    tail.push(value); tn += value.length; while (tail.length>1 && tn - tail[0].length >= TAIL){ tn -= tail[0].length; tail.shift(); } }
  const dec = new TextDecoder(); return head.map(c=>dec.decode(c,{stream:true})).join('') + '\n' + tail.map(c=>dec.decode(c,{stream:true})).join('');
}
function parseDuration(t){
  let s = 0; const m = t.match(/(?:(\d+)d)?\s*(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?/);
  if (m) s = (+m[1]||0)*86400 + (+m[2]||0)*3600 + (+m[3]||0)*60 + (+m[4]||0);
  return s;
}
function parseGcodeText(txt){
  const kv = {}; for (const m of txt.matchAll(/^;\s*([^=:\n]+?)\s*[=:]\s*(.*)$/gm)) { const k=m[1].trim().toLowerCase(); if(!(k in kv)) kv[k]=m[2].trim(); }
  const list = v => (v||'').split(/[;,]/).map(x=>x.trim().replace(/^"|"$/g,''));
  let secs = 0;
  const tot = txt.match(/total estimated time:\s*([0-9dhms ]+)/i);
  if (tot) secs = parseDuration(tot[1]);
  else if (kv['estimated printing time (normal mode)']) secs = parseDuration(kv['estimated printing time (normal mode)']);
  else if (kv['time']) secs = +kv['time'];                                    // Cura ;TIME:
  const grams = list(kv['filament used [g]']).map(Number), costs = list(kv['filament cost']).map(Number);
  const types = list(kv['filament_type']), colors = list(kv['filament_colour'] || kv['filament_color'] || kv['extruder_colour']);
  const names = list(kv['filament_settings_id']);
  let fil = grams.map((g,i)=>({slot:i+1, grams:g||0, cost:costs[i]||0, type:types[i]||'', color:colors[i]||'', name:names[i]||''}));
  if (!fil.length && kv['filament used']){                                    // Cura: metros → gramos (1.75 mm, 1.24 g/cm³)
    fil = list(kv['filament used']).map((v,i)=>({slot:i+1, grams:(parseFloat(v)||0)*2.98, cost:0, type:'', color:'', name:''}));
  }
  const totCost = +kv['total filament cost'] || fil.reduce((a,f)=>a+f.cost,0);
  const first = v => list(v)[0] || '';
  const settings = cleanSettings({
    layer_height: kv['layer_height'] || kv['layer height'], first_layer: kv['initial_layer_print_height'] || kv['first_layer_height'],
    infill: kv['sparse_infill_density'] || kv['fill_density'], infill_pattern: kv['sparse_infill_pattern'] || kv['fill_pattern'],
    walls: kv['wall_loops'] || kv['perimeters'], top_bottom: [kv['top_shell_layers']||kv['top_solid_layers'], kv['bottom_shell_layers']||kv['bottom_solid_layers']].filter(Boolean).join(' / '),
    nozzle: first(kv['nozzle_diameter']), supports: kv['enable_support'] ?? kv['support_material'], profile: kv['print_settings_id'],
    filaments: names.filter(Boolean).join(' + ')});
  return {secs, filaments: fil.filter(f=>f.grams>0.01), cost: totCost, printer: kv['printer_model'] || kv['printer_settings_id'] || '', settings};
}
function cleanSettings(o){
  const out = {}; for (const [k,v] of Object.entries(o)){ let x = Array.isArray(v) ? v[0] : v; if (x==null) continue; x = String(x).replace(/^"|"$/g,'').trim(); if (x!=='') out[k]=x; }
  if (out.supports!=null) out.supports = ['1','true'].includes(String(out.supports).toLowerCase()) ? 'sí' : ['0','false'].includes(String(out.supports).toLowerCase()) ? 'no' : out.supports;
  if (out.infill && !String(out.infill).includes('%') && +out.infill<=1) out.infill = Math.round(+out.infill*100)+'%';
  return out;
}
function settingsFromProject(js){
  return cleanSettings({layer_height: js.layer_height, first_layer: js.initial_layer_print_height, infill: js.sparse_infill_density,
    infill_pattern: js.sparse_infill_pattern, walls: js.wall_loops, top_bottom: [js.top_shell_layers, js.bottom_shell_layers].filter(x=>x!=null).join(' / '),
    nozzle: js.nozzle_diameter, supports: js.enable_support, profile: js.print_settings_id,
    filaments: (Array.isArray(js.filament_settings_id) ? js.filament_settings_id : [js.filament_settings_id]).filter(Boolean).join(' + ')});
}
function parseSliceInfo(xml){
  const doc = new DOMParser().parseFromString(xml, 'application/xml'), plates = [];
  for (const pl of doc.querySelectorAll('plate')){
    const md = k => pl.querySelector(`metadata[key="${k}"]`)?.getAttribute('value');
    const fil = [...pl.querySelectorAll('filament')].map(f=>({slot:+f.getAttribute('id'), grams:+f.getAttribute('used_g')||0, cost:0,
      type:f.getAttribute('type')||'', color:f.getAttribute('color')||'', name:''})).filter(f=>f.grams>0.01);
    plates.push({index:+md('index')||plates.length+1, secs:+md('prediction')||0, filaments:fil, cost:0, printer:''});
  }
  return plates;
}
async function readSlicerFile(file){
  const name = file.name.toLowerCase();
  if (name.endsWith('.3mf')){
    const z = await zipIndex(file), keys = Object.keys(z);
    const gcodes = keys.filter(k=>/^Metadata\/plate_\d+\.gcode$/i.test(k)).sort();
    let plates = [];
    if (z['Metadata/slice_info.config']){
      const xml = await new Response(await zipEntryBlob(file, z['Metadata/slice_info.config'])).text();
      plates = parseSliceInfo(xml);
    }
    let proj = {};
    if (z['Metadata/project_settings.config']){
      try { proj = settingsFromProject(JSON.parse(await new Response(await zipEntryBlob(file, z['Metadata/project_settings.config'])).text())); } catch(e){}
    }
    plates.forEach(p=>p.settings = {...proj});
    // Si hay G-code dentro, de ahí sacamos además coste y tipos por color
    for (const g of gcodes){
      const idx = +g.match(/plate_(\d+)/)[1], blob = await zipEntryBlob(file, z[g]);
      const txt = blob instanceof Blob ? await headTailText(blob) : await streamHeadTail(blob);
      const r = parseGcodeText(txt); r.index = idx;
      const i = plates.findIndex(p=>p.index===idx);
      r.settings = {...proj, ...r.settings};
      if (i<0) plates.push(r); else plates[i] = {...plates[i], ...r, secs: r.secs || plates[i].secs, filaments: r.filaments.length ? r.filaments : plates[i].filaments};
    }
    plates = plates.filter(p=>p.secs || p.filaments.length);
    if (!plates.length) throw new Error('este 3MF no está laminado: lamínalo y exporta el G-code o el «3MF laminado»');
    return plates.sort((a,b)=>a.index-b.index);
  }
  if (/\.(gcode|gco|g)$/.test(name)){
    const r = parseGcodeText(await headTailText(file)); r.index = 1;
    if (!r.secs && !r.filaments.length) throw new Error('no encuentro tiempo ni filamento en el G-code');
    return [r];
  }
  throw new Error('formato no soportado (usa .gcode o .3mf laminado)');
}
let SLICE = [], IMPORTED = null;   // IMPORTED = {file, settings} del último archivo importado
const FICHA = [['printer','Impresora'],['layer_height','Altura de capa'],['first_layer','Primera capa'],['infill','Relleno'],['infill_pattern','Patrón'],
  ['walls','Perímetros'],['top_bottom','Capas sup./inf.'],['nozzle','Boquilla'],['supports','Soportes'],['profile','Perfil'],['filaments','Filamentos'],['notes','Notas']];
function currentPrintInfo(){
  const pr = PRINTERS.find(x=>x.id==$('#c-printer').value);
  const mats = $$('#c-mats .row').map(r=>{ const m = MATS.find(x=>x.id==r.querySelector('.cm-id').value), a = r.querySelector('.cm-amt').value; return m && a ? `${m.name}${m.color?' '+m.color:''} ${a} ${m.unit}` : ''; }).filter(Boolean).join(' + ');
  return {printer: pr?.name || '', ...(IMPORTED?.settings || {}), materials: mats, source_file: IMPORTED?.file?.name || ''};
}
function applyPlate(i){
  const p = SLICE[i];
  $('#c-hours').value = Math.floor(p.secs/3600); $('#c-minutes').value = Math.round(p.secs%3600/60);
  if (p.printer){ const pr = PRINTERS.find(x=>x.active && (p.printer.toLowerCase().includes(x.name.toLowerCase()) || x.name.toLowerCase().includes(p.printer.toLowerCase()) ||
      x.name.toLowerCase().split(/\s+/).filter(w=>w.length>2).some(w=>p.printer.toLowerCase().includes(w) && !['anycubic','snapmaker','printer'].includes(w)))); if (pr) $('#c-printer').value = pr.id; }
  $('#c-mats').innerHTML = '';
  const act = MATS.filter(m=>m.active);
  for (const f of p.filaments){
    const t = f.type.toLowerCase();
    const m = act.find(m=>t && m.kind.toLowerCase()===t && m.color && f.color && m.color.toLowerCase()===f.color.toLowerCase())
          || act.find(m=>t && (m.kind.toLowerCase()===t || m.name.toLowerCase().includes(t))) || act.find(m=>m.unit==='g') || act[0];
    addMatRow(m?.id||'', +f.grams.toFixed(2), f.color);
  }
  if (!p.filaments.length) addMatRow();
  // ¿lo tengo en el almacén? → elige la bobina que mejor encaja con cada color
  if (p.filaments.length && SPOOLS.length) api('/spools/match',{method:'POST',body:{needs:p.filaments.map(f=>({kind:f.type, color_hex:f.color, grams:f.grams}))}}).then(r=>{
    const rowsEl = $$('#c-mats .row');
    r.results.forEach((x,i)=>{ const c = x.candidates[0], row = rowsEl[i]; if (!row || !c || !x.close) return;
      const sp = SPOOLS.find(s=>s.id===c.spool_id); if (!sp) return;
      row.querySelector('.cm-id').value = sp.material_id; row.querySelector('.cm-sp').innerHTML = spoolOpts(sp.material_id, sp.id); });
    $('#sl-have').innerHTML = (r.all_ok ? '<span class="pos">✓ Tienes todos los colores en el almacén.</span>' : '<span class="neg">Te falta algún color o cantidad:</span>') + ' ' +
      r.results.map(x=>`<span style="white-space:nowrap"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${esc(x.need.color_hex||'#999')};border:1px solid var(--line)"></span> ${x.ok?'✓':x.close?'≈':'✗'} ${x.candidates[0]&&x.close?esc(spoolLabel(SPOOLS.find(s=>s.id===x.candidates[0].spool_id)||{remaining:0,unit:'g'})):'no lo tienes'}</span>`).join(' · ');
    markStale();
  }).catch(()=>{});
  if (p.cost > 0){ $('#c-matcost').value = p.cost.toFixed(2); setMatMode('direct', false); }
  if (IMPORTED) IMPORTED.settings = p.settings || {};
  $('#sl-result').innerHTML = `<b>${esc(SLICE.length>1?'Placa '+p.index+': ':'')}${Math.floor(p.secs/3600)} h ${Math.round(p.secs%3600/60)} min</b> · `+
    p.filaments.map(f=>`<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${esc(f.color||'#999')};border:1px solid var(--line)"></span> ${esc(f.type||'filamento '+f.slot)} ${f.grams.toFixed(1)} g`).join(' · ') +
    (p.cost>0?` · coste laminador <b>${eur(p.cost)}</b>`:'') + (p.printer?` · <span class="mut">${esc(p.printer)}</span>`:'') +
    (SLICE.length>1 ? `<div class="chips" style="margin-top:8px">${SLICE.map((x,j)=>`<button class="btn sm ${j===i?'':'sec'}" onclick="applyPlate(${j})">Placa ${x.index}</button>`).join('')}</div>` : '') +
    (p.settings && Object.keys(p.settings).length ? `<div class="mut" style="margin-top:6px">Ficha: ${FICHA.filter(([k])=>p.settings[k]).map(([k,l])=>`${l} <b>${esc(p.settings[k])}</b>`).join(' · ')}</div>` : '') +
    `<div id="sl-have" style="margin-top:6px"></div><div class="mut" style="margin-top:6px">Revisa que cada color apunta al material correcto${p.cost>0?'':' (el archivo no trae coste: se calcula por gramos)'}.</div>`;
  $('#sl-result').classList.remove('hidden');
  markStale(); toast('Datos importados: revisa los materiales y pulsa Calcular');
}
async function importSlicer(file){
  try{
    $('#sl-result').classList.remove('hidden'); $('#sl-result').textContent = 'Leyendo ' + file.name + '…';
    SLICE = await readSlicerFile(file); IMPORTED = {file, settings:{}};
    if (!$('#c-name').value) $('#c-name').value = file.name.replace(/\.(gcode|gco|g|3mf)$/i,'').replace(/\.gcode$/i,'').replace(/[_-]+/g,' ').trim();
    applyPlate(0);
  }catch(e){ $('#sl-result').innerHTML = `<span class="neg">${esc(e.message)}</span>`; }
}
$('#sl-file').onchange = e => e.target.files[0] && importSlicer(e.target.files[0]);
['dragover','drop'].forEach(ev=>$('#drop').addEventListener(ev, e=>{ e.preventDefault(); if(ev==='drop' && e.dataTransfer.files[0]) importSlicer(e.dataTransfer.files[0]); }));

// ---------- pedidos
async function loadOrders(){
  $('#o-filter').innerHTML = ['', ...STATUSES].map(s=>`<button class="btn sm ${s===orderFilter?'':'sec'}" onclick="orderFilter='${s}';loadOrders()">${s||'todos'}</button>`).join('');
  const os = await api('/orders' + (orderFilter?`?status=${orderFilter}`:''));
  $('#o-table').innerHTML = `<tr><th>#</th><th>Cliente</th><th>Qué</th><th>Estado</th><th>Entrega</th><th>Lo lleva</th><th class="n">Total</th><th class="n">Benef.</th><th>Cobro</th></tr>` +
    (os.map(o=>`<tr style="cursor:pointer" onclick="openOrder(${o.id})"><td class="mut">${o.id}</td><td><b>${esc(o.client)}</b><br><span class="mut" style="font-size:12px">${esc(o.channel)}</span></td>
      <td style="font-size:13px">${o.items.map(i=>`${i.qty}× ${esc(i.description)}`).join('<br>')}</td>
      <td><span class="tag st-${o.status}">${o.status}</span>${stuck(o)}</td><td>${o.due_date||''}</td><td>${esc(o.assigned)}</td>
      <td class="n">${eur(o.total)}</td><td class="n ${o.profit>=0?'pos':'neg'}">${eur(o.profit)}</td>
      <td>${o.paid?`<span class="pos">✓ ${esc(o.paid_to)}</span>`:'<span class="mut">pendiente</span>'}</td></tr>`).join('') || '<tr><td colspan="9" class="mut">Sin pedidos</td></tr>');
}
const dlg = $('#dlg');
let QUEUED = [];   // archivos pendientes de subir al guardar
async function uploadModel(file, target){
  const fd = new FormData(); fd.append('file', file); for (const [k,v] of Object.entries(target)) fd.append(k, v);
  const r = await fetch('/api/files', {method:'POST', body:fd}), j = await r.json().catch(()=>({}));
  if (!r.ok){ toast(`${file.name}: ${j.error||'error al subir'}`); throw new Error(j.error); } return j;
}
const fsize = b => b > 1048576 ? (b/1048576).toFixed(1)+' MB' : Math.ceil(b/1024)+' KB';
function renderFiles(){
  const saved = (curOrder.files||[]).map(f=>`<div class="row" style="margin-bottom:4px;align-items:center"><div style="flex:3">📎 <a href="/api/files/${f.id}">${esc(f.name)}</a> <span class="mut" style="font-size:12px">${fsize(f.size)} · ${esc(f.uploaded_by||'')} ${f.uploaded?.slice(0,10)||''}${f.note?' · '+esc(f.note):''}</span></div>${/\.(gcode|gco|g|bgcode)$/i.test(f.name)?`<button class="btn sec sm" onclick="sendToPrinter(${f.id})">Enviar a impresora</button>`:''}<button class="btn sec sm" onclick="delOrderFile(${f.id})">✕</button></div>`);
  const q = QUEUED.map((f,i)=>`<div class="row" style="margin-bottom:4px;align-items:center"><div style="flex:3">⏳ ${esc(f.name)} <span class="mut" style="font-size:12px">${fsize(f.size)} · se sube al guardar</span></div><button class="btn sec sm" onclick="QUEUED.splice(${i},1);renderFiles()">✕</button></div>`);
  $('#d-files').innerHTML = ([...saved, ...q].join('') || '<p class="mut" style="margin:0;font-size:13px">Sin archivos todavía.</p>') + '<div id="d-jobs"></div>';
  if (curOrder.id) api(`/orders/${curOrder.id}/jobs`).then(js=>{ if(!js.length) return;
    const est = curOrder.items.reduce((a,i)=>{ try{ const c = typeof i.calc_result==='string'?JSON.parse(i.calc_result||'null'):i.calc_result; return a + (c? c.hours*3600*(i.qty/(c.units||1)) : 0); }catch(e){ return a; } },0);
    const real = js.reduce((a,j)=>a+(j.print_duration||0),0), g = js.reduce((a,j)=>a+(j.filament_g||0),0);
    $('#d-jobs').innerHTML = `<div style="margin-top:8px;font-size:13px"><b>Impresiones reales:</b> ${js.map(j=>`${esc(j.printer||'')} · ${esc(j.filename)} · ${hm(j.print_duration)}${j.filament_g?' · '+j.filament_g.toFixed(1)+' g':''}`).join('<br>')}
      <br><span class="mut">Total real ${hm(real)}${g?' · '+g.toFixed(1)+' g':''} · estimado ${hm(est)}</span></div>`; }).catch(()=>{});
}
$('#d-file').onchange = e => { QUEUED.push(...e.target.files); e.target.value=''; renderFiles(); };
async function delOrderFile(fid){ if (!await sure('¿Quitar este archivo del pedido?', {ok:'Quitar', danger:1})) return; await api('/files/'+fid,{method:'DELETE'}); curOrder.files = curOrder.files.filter(f=>f.id!==fid); renderFiles(); }
async function repeatOrder(){
  if (!await sure('Se creará un pedido nuevo (recibido) con las mismas piezas, fichas de impresión y archivos.', {title:'Repetir pedido', ok:'Repetir'})) return;
  const n = await api(`/orders/${curOrder.id}/repeat`,{method:'POST'}); toast(`Creado el pedido #${n.id}`); openOrder(n.id); loadOrders();
}
function editFicha(i){
  readItems(); const it = curOrder.items[i];
  let pi = {}; try { pi = typeof it.print_info==='string' ? JSON.parse(it.print_info||'{}') : (it.print_info||{}); } catch(e){}
  const tr = $(`#d-items tr[data-i="${i}"]`), open = tr.nextElementSibling?.classList.contains('ficha');
  $$('#d-items tr.ficha').forEach(x=>x.remove()); if (open) return;
  const row = document.createElement('tr'); row.className='ficha';
  row.innerHTML = `<td colspan="5" style="background:var(--bg)"><div class="grid g4">${FICHA.map(([k,l])=>`<div><label>${l}</label><input data-pi="${k}" value="${esc(pi[k]||'')}"></div>`).join('')}
    ${pi.materials?`<div style="grid-column:span 2"><label>Materiales</label><div style="font-size:13px">${esc(pi.materials)}</div></div>`:''}
    ${pi.source_file?`<div style="grid-column:span 2"><label>Archivo de origen</label><div style="font-size:13px">${esc(pi.source_file)}</div></div>`:''}</div>
    <button class="btn sm" style="margin-top:8px" onclick="saveFicha(${i})">Listo</button></td>`;
  tr.after(row);
}
function saveFicha(i){
  const it = curOrder.items[i]; let pi = {}; try { pi = typeof it.print_info==='string' ? JSON.parse(it.print_info||'{}') : (it.print_info||{}); } catch(e){}
  $$('#d-items tr.ficha [data-pi]').forEach(el=>{ if (el.value) pi[el.dataset.pi] = el.value; else delete pi[el.dataset.pi]; });
  it.print_info = pi; renderItems();
}
const hasFicha = it => { try { const p = typeof it.print_info==='string' ? JSON.parse(it.print_info||'{}') : (it.print_info||{}); return Object.keys(p).length>0; } catch(e){ return false; } };
async function openOrder(id=null, presetItems=null, presetFiles=[]){
  QUEUED = [...presetFiles];
  curOrder = id ? await api('/orders/'+id) : {client:'',contact:'',email:'',address:'',source:'interno',channel:S.channels[0]||'',status:'recibido',due_date:'',assigned:'',notes:'',shipping:0,discount:0,paid:0,paid_to:'',paid_date:'',items:[]};
  if (presetItems) curOrder.items = [...curOrder.items, ...presetItems];
  $('#d-title').textContent = id ? `Pedido #${id}` : 'Nuevo pedido';
  $('#d-client').value=curOrder.client; $('#d-contact').value=curOrder.contact;
  $('#d-email').value=curOrder.email||''; $('#d-address').value=curOrder.address||''; $('#d-source').value=curOrder.source||'interno';
  $('#d-channel').innerHTML = opts(S.channels, curOrder.channel); $('#d-status').innerHTML = opts(STATUSES, curOrder.status);
  $('#d-due').value=curOrder.due_date; $('#d-assigned').innerHTML = opts(['',...S.people], curOrder.assigned);
  $('#d-ship').value=curOrder.shipping; $('#d-disc').value=curOrder.discount; $('#d-notes').value=curOrder.notes;
  $('#d-paid').value=curOrder.paid?1:0; $('#d-paidto').innerHTML=opts(['',...S.people], curOrder.paid_to); $('#d-paiddate').value=curOrder.paid_date;
  $('#d-prod').innerHTML = '<option value="">+ desde catálogo…</option>' + opts(PRODUCTS, '', p=>[p.id, `${p.kind==='conjunto'?'📦 ':''}${p.name} — ${eur(p.unit_price)}`]);
  $('#d-del').classList.toggle('hidden', !id); $('#d-repeat').classList.toggle('hidden', !id);
  renderItems(); renderFiles(); renderOrderExtra(); dlg.showModal();
}
$('#d-client').onchange = e => { const c = CLIENTS.find(x=>x.name.toLowerCase()===e.target.value.trim().toLowerCase()); if (!c) return;
  if (!$('#d-contact').value) $('#d-contact').value = c.phone||''; if (!$('#d-email').value) $('#d-email').value = c.email||'';
  if (!$('#d-address').value) $('#d-address').value = c.address||''; };
$('#d-prod').onchange = async e => { const p = PRODUCTS.find(x=>x.id==e.target.value); e.target.value=''; if(!p) return; readItems();
  if (p.kind==='conjunto'){ const b = await api(`/products/${p.id}/bundle`);
    curOrder.items.push({description:p.name, qty:1, unit_price:p.unit_price, unit_cost:b.kit.cost, calc_result:b.calc_result, product_id:p.id,
      print_info:{notes: b.kit.items.map(i=>`${i.qty}× ${i.name}`).join(', ')}});
  } else { const pv = await pickVariant(p, false, false); if (!pv) return; const v = pv.variant;
    let cj = p.calc_json; if (v && v.material_id){ try { const o = JSON.parse(cj||'{}'); if (o.materials?.length){ o.materials[0].material_id = v.material_id; delete o.materials[0].spool_id; } cj = JSON.stringify(o); } catch(e){} }
    curOrder.items.push({description:p.name + (v?` (${v.name})`:''), qty:1, unit_price:vPrice(p, v, false), unit_cost:p.unit_cost, calc_json:cj, product_id:p.id, variant_id:v?.id||null, print_info:p.print_info||''}); }
  renderItems(); };
function renderItems(){
  $('#prod-list').innerHTML = (PRODUCTS||[]).map(p=>`<option value="${esc(p.name)}">`).join('');
  $('#d-items').innerHTML = `<tr><th>Producto</th><th style="width:80px">Uds</th><th style="width:110px">Precio ud</th><th style="width:110px">Coste ud</th><th style="width:120px"></th></tr>` +
    curOrder.items.map((it,i)=>`<tr data-i="${i}"><td><input class="it-d" list="prod-list" value="${esc(it.description)}" placeholder="Producto (del catálogo o lo que quieras)" onchange="itProduct(this)">
      <textarea class="it-x" rows="${Math.min(6, Math.max(1, String(it.details||'').split('\n').length))}" placeholder="Descripción libre: sale en el presupuesto y el albarán (opcional)" oninput="itRows(this)">${esc(it.details||'')}</textarea></td><td><input class="it-q" type="number" min="1" value="${it.qty}"></td>
      <td><input class="it-p" type="number" step="0.01" value="${it.unit_price}"></td><td><input class="it-c" type="number" step="0.01" value="${it.unit_cost}"></td>
      <td style="white-space:nowrap"><button class="btn sm ${hasFicha(it)?'sec':''}" title="Ficha de impresión" onclick="editFicha(${i})">${hasFicha(it)?'Ficha ✓':'Ficha'}</button>${curOrder.id&&it.calc_result?` <button class="btn sec sm" title="La impresión falló: apunta lo que se ha perdido" onclick="addFailure(${i})">Fallo</button>`:''} <button class="btn sec sm" onclick="readItems();curOrder.items.splice(${i},1);renderItems()">✕</button></td></tr>`).join('');
  $('#d-items').oninput = dlgTotals; dlgTotals();
}
function renderOrderExtra(){
  const fl = curOrder.failures||[], log = curOrder.status_log||[];
  $('#d-extra').innerHTML =
    (fl.length ? `<h3 style="font-size:14px;margin:16px 0 6px">Fallos de impresión</h3>` + fl.map(f=>{
      const g = JSON.parse(f.grams_json||'[]').map(x=>`${x.amount} ${x.unit||'g'} ${esc(x.name)}`).join(', ');
      return `<div class="row" style="margin-bottom:4px;align-items:center;font-size:13px"><div style="flex:4">❌ ${esc(f.description)} al <b>${f.pct}%</b> · ${g} · ${f.hours} h · <b class="neg">${eur(f.cost)}</b>${f.cause?` · ${esc(f.cause)}`:''} <span class="mut">${f.created.slice(0,10)}</span></div><button class="btn sec sm" onclick="delFailure(${f.id})">✕</button></div>`;
    }).join('') + `<div class="mut" style="font-size:12px">Perdido en fallos: ${eur(curOrder.failure_cost)} (ya restado del beneficio)</div>` : '') +
    (log.length ? `<details style="margin-top:12px"><summary class="mut" style="cursor:pointer;font-size:13px">Historial de estados</summary>
      <div style="font-size:13px;margin-top:6px">${log.map(l=>`${l.at.replace('T',' ').slice(0,16)} → <span class="tag st-${l.status}">${l.status}</span> <span class="mut">${esc(l.user||'')}</span>`).join('<br>')}</div></details>` : '');
}
async function addFailure(i){
  readItems();
  let pct = '';
  try { const ps = (await api('/printers/status')).filter(p=>p.online && ['printing','paused','cancelled','error'].includes(p.state));
        if (ps.length===1) pct = String(Math.round(ps[0].progress)); } catch(e){}
  const f = await form('Apuntar fallo', [
    {k:'pct', label:'¿A qué porcentaje iba cuando falló? (1-100)', type:'number', value:pct, req:1},
    {k:'cause', label:'¿Qué pasó? (opcional)', placeholder:'despegue, espagueti, atasco, corte de luz…'}], {msg:curOrder.items[i].description, ok:'Apuntar fallo'});
  if (!f) return;
  await api(`/orders/${curOrder.id}/failures`,{method:'POST',body:{item_index:i, pct:f.pct, cause:f.cause}});
  curOrder = await api('/orders/'+curOrder.id); renderItems(); renderOrderExtra(); refreshLowStock();
  toast('Fallo apuntado: material descontado del stock');
}
async function delFailure(id){ if (!await sure('¿Borrar este fallo? El material vuelve al stock.', {ok:'Borrar', danger:1})) return; await api('/failures/'+id,{method:'DELETE'});
  curOrder = await api('/orders/'+curOrder.id); renderOrderExtra(); }
// Al escribir o elegir un producto del catálogo en una línea nueva, coge su precio y su coste
function itRows(t){ t.rows = Math.min(8, Math.max(1, t.value.split('\n').length)); }
function itProduct(inp){
  const i = +inp.closest('tr').dataset.i, it = curOrder.items[i], p = (PRODUCTS||[]).find(x=>x.name.toLowerCase()===inp.value.trim().toLowerCase());
  if (!p || it.product_id===p.id) return;
  readItems(); Object.assign(curOrder.items[i], {description:p.name, product_id:p.id, unit_price:p.unit_price||0, unit_cost:p.unit_cost||0}); renderItems();
}
function readItems(){ curOrder.items = $$('#d-items tr[data-i]').map(r=>({...curOrder.items[r.dataset.i], description:r.querySelector('.it-d').value, details:r.querySelector('.it-x').value, qty:+r.querySelector('.it-q').value||1, unit_price:+r.querySelector('.it-p').value||0, unit_cost:+r.querySelector('.it-c').value||0})); }
function addItemRow(){ readItems(); curOrder.items.push({description:'',qty:1,unit_price:0,unit_cost:0}); renderItems(); }
function dlgTotals(){ readItems();
  const sub = curOrder.items.reduce((a,i)=>a+i.qty*i.unit_price,0), cost = curOrder.items.reduce((a,i)=>a+i.qty*i.unit_cost,0);
  const tot = sub + (+$('#d-ship').value||0) - (+$('#d-disc').value||0);
  $('#d-total').textContent = eur(tot); $('#d-profit').textContent = eur(tot - (+$('#d-ship').value||0) - cost); }
async function saveOrder(){
  readItems();
  const body = {client:$('#d-client').value, contact:$('#d-contact').value, email:$('#d-email').value, address:$('#d-address').value, source:$('#d-source').value, channel:$('#d-channel').value, status:$('#d-status').value,
    due_date:$('#d-due').value, assigned:$('#d-assigned').value, notes:$('#d-notes').value, shipping:$('#d-ship').value, discount:$('#d-disc').value,
    paid:$('#d-paid').value==='1', paid_to:$('#d-paidto').value, paid_date:$('#d-paiddate').value, items:curOrder.items};
  const printing = ['imprimiendo','listo','entregado'].includes(body.status);
  if (printing && !(curOrder.files||[]).length && !QUEUED.length &&
      !await sure('Este pedido no tiene STL ni 3MF adjunto. Si algún día quieres repetirlo igual, te hará falta.', {title:'¿Guardar sin archivo?', ok:'Guardar sin archivo'})) return;
  const saved = curOrder.id ? await api('/orders/'+curOrder.id,{method:'PUT',body}) : await api('/orders',{method:'POST',body});
  for (const f of QUEUED) { try { await uploadModel(f, {order_id: saved.id}); } catch(e){} }
  QUEUED = []; dlg.close(); toast('Pedido guardado'); loadClientList(); show($('#v-home').classList.contains('hidden') ? 'orders' : 'home'); refreshLowStock();
}
function printOrder(kind){
  readItems(); const o = {...curOrder, client:$('#d-client').value, email:$('#d-email').value, address:$('#d-address').value,
    shipping:+$('#d-ship').value||0, discount:+$('#d-disc').value||0};
  const sub = o.items.reduce((a,i)=>a+i.qty*i.unit_price,0), total = sub + o.shipping - o.discount;
  const vatRate = S.apply_vat ? S.vat_pct/100 : 0, b2c = S.sale_type==='B2C';
  const base = b2c ? total/(1+vatRate) : total, vat = b2c ? total-base : total*vatRate, grand = b2c ? total : total+vat;
  const today = new Date(), fmt = d => d.toLocaleDateString(I18N.locale());
  const valid = new Date(today.getTime() + (S.quote_validity_days||15)*864e5);
  const title = t(kind==='presupuesto' ? 'Presupuesto' : 'Albarán');
  const num = o.id ? `${kind==='presupuesto'?'P':'A'}-${today.getFullYear()}-${String(o.id).padStart(4,'0')}` : t('borrador');
  const biz = [S.business_name, S.business_nif && 'NIF '+S.business_nif, S.business_address, S.business_email, S.business_phone, S.business_web].filter(Boolean).map(esc).join('<br>');
  const acc = BRAND.accent_color || '#3fae6a';
  const html = `<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>${title} ${num}</title><style>
    body{font:13px/1.5 system-ui,sans-serif;color:#222;margin:40px}h1{margin:0;font-size:26px;color:${acc}}
    .top{display:flex;justify-content:space-between;gap:20px;border-bottom:3px solid ${acc};padding-bottom:14px}
    .top img{max-height:70px;max-width:200px}.meta{text-align:right}table{width:100%;border-collapse:collapse;margin-top:24px}
    th{background:${acc};color:#fff;text-align:left;padding:8px}td{padding:8px;border-bottom:1px solid #ddd;vertical-align:top}.n{text-align:right}
    .det{white-space:pre-line;color:#555;font-size:12px;margin-top:3px}
    .tot{margin-left:auto;width:280px;margin-top:14px}.tot td{border:0;padding:4px 8px}.tot tr:last-child td{font-weight:700;font-size:16px;border-top:2px solid #222}
    .foot{margin-top:40px;color:#777;font-size:12px;border-top:1px solid #ddd;padding-top:10px}@media print{body{margin:0}}</style></head><body>
    <div class="top"><div>${BRAND.logo_url?`<img src="${BRAND.logo_url}"><br>`:''}<b>${esc(BRAND.shop_name||'')}</b><br><span style="color:#777">${biz}</span></div>
    <div class="meta"><h1>${title}</h1><b>${num}</b><br>${t('Fecha')}: ${fmt(today)}${kind==='presupuesto'?`<br>${t('Válido hasta')}: ${fmt(valid)}`:''}
    <br><br><b>${t('Cliente')}</b><br>${esc(o.client)}${o.email?'<br>'+esc(o.email):''}${o.contact?'<br>'+esc(o.contact):''}${o.address?'<br>'+esc(o.address):''}</div></div>
    <table><tr><th>${t('Descripción')}</th><th class="n">${t('Uds')}</th><th class="n">${t('Precio')}</th><th class="n">${t('Importe')}</th></tr>
    ${o.items.map(i=>`<tr><td>${i.details?`<b>${esc(i.description)}</b><div class="det">${esc(i.details)}</div>`:esc(i.description)}</td><td class="n">${i.qty}</td><td class="n">${eur(i.unit_price)}</td><td class="n">${eur(i.qty*i.unit_price)}</td></tr>`).join('')}
    ${o.shipping?`<tr><td>${t('Envío')}</td><td class="n">1</td><td class="n">${eur(o.shipping)}</td><td class="n">${eur(o.shipping)}</td></tr>`:''}
    ${o.discount?`<tr><td>${t('Descuento')}</td><td></td><td></td><td class="n">−${eur(o.discount)}</td></tr>`:''}</table>
    <table class="tot">${vatRate?`<tr><td>${t('Base imponible')}</td><td class="n">${eur(base)}</td></tr><tr><td>${t('IVA')} ${S.vat_pct}%</td><td class="n">${eur(vat)}</td></tr>`:''}
    <tr><td>${t('Total')}</td><td class="n">${eur(grand)}</td></tr></table>
    ${o.notes&&kind==='presupuesto'?`<p style="margin-top:24px"><b>${t('Observaciones')}:</b> ${esc(o.notes)}</p>`:''}
    <div class="foot">${esc(S.doc_footer||'')}</div><script>onload=()=>setTimeout(()=>print(),300)<\/script></body></html>`;
  const w = window.open('', '_blank'); if(!w) return toast('Permite ventanas emergentes'); w.document.write(html); w.document.close();
}
async function delOrder(){ if (!await sure('¿Borrar pedido?', {ok:'Borrar', danger:1})) return; await api('/orders/'+curOrder.id,{method:'DELETE'}); dlg.close(); loadOrders(); }

// ---------- contabilidad
async function loadAcc(){
  const ys = $('#a-year'); if(!ys.options.length){ const y=new Date().getFullYear(); ys.innerHTML = opts([y,y-1,y-2], y); }
  $('#m-date').value ||= new Date().toISOString().slice(0,10);
  $('#m-cat').innerHTML = opts([...S.expense_categories,'Ventas'], $('#m-cat').value||S.expense_categories[0]);
  $('#m-person').innerHTML = opts(S.people, $('#m-person').value);
  const year = ys.value, [sm, mv] = await Promise.all([api('/summary?year='+year), api('/movements?year='+year)]);
  $('#k-in').textContent = eur(sm.ingresos); $('#k-out').textContent = eur(sm.gastos);
  $('#k-ben').textContent = eur(sm.beneficio); $('#k-ben').className = 'v '+(sm.beneficio>=0?'pos':'neg');
  $('#k-pend').textContent = eur(sm.pendiente_cobro); $('#k-open').textContent = sm.pedidos_abiertos;
  const max = Math.max(1, ...sm.months.flatMap(m=>[m.ingresos,m.gastos]));
  const mm = Object.fromEntries(sm.months.map(m=>[m.month.slice(5),m]));
  $('#a-chart').innerHTML = ['01','02','03','04','05','06','07','08','09','10','11','12'].map(k=>{const m=mm[k]||{ingresos:0,gastos:0};
    return `<div title="ing ${eur(m.ingresos)} · gas ${eur(m.gastos)}"><div style="display:flex;gap:2px;align-items:end;height:110px;width:100%;justify-content:center"><span style="height:${m.ingresos/max*100}%;background:var(--acc2)"></span><span style="height:${m.gastos/max*100}%;background:var(--acc)"></span></div>${k}</div>`}).join('');
  $('#a-people').innerHTML = `<tr><th>Persona</th><th class="n">Ha cobrado</th><th class="n">Ha pagado</th><th class="n">Neto en mano</th></tr>` +
    sm.people.map(p=>`<tr><td>${esc(p.person||'(sin asignar)')}</td><td class="n">${eur(p.cobrado)}</td><td class="n">${eur(p.pagado)}</td><td class="n">${eur(p.cobrado-p.pagado)}</td></tr>`).join('');
  const named = sm.people.filter(p=>p.person);
  if (named.length===2){ const [a,b]=named, na=a.cobrado-a.pagado, nb=b.cobrado-b.pagado, diff=(na-nb)/2;
    $('#a-settle').textContent = Math.abs(diff)<0.01 ? 'Estáis en paz.' : `Para repartir a medias: ${diff>0?a.person:b.person} debe pasar ${eur(Math.abs(diff))} a ${diff>0?b.person:a.person}.`;
  } else $('#a-settle').textContent='';
  $('#a-table').innerHTML = `<tr><th>Fecha</th><th>Tipo</th><th>Categoría</th><th>Concepto</th><th>Quién</th><th class="n">Importe</th><th></th></tr>` +
    mv.map(m=>`<tr><td>${m.date}</td><td>${m.kind}</td><td>${esc(m.category)}</td><td>${esc(m.concept)}${m.order_id?` <a href="#" onclick="event.preventDefault();openOrder(${m.order_id})">#${m.order_id}</a>`:''}</td><td>${esc(m.person)}</td>
      <td class="n ${m.kind==='ingreso'?'pos':'neg'}">${m.kind==='gasto'?'−':''}${eur(m.amount)}</td>
      <td>${m.order_id?'':`<button class="btn sec sm" onclick="delMov(${m.id})">✕</button>`}</td></tr>`).join('');
}
async function addMovement(){
  await api('/movements',{method:'POST',body:{date:$('#m-date').value, kind:$('#m-kind').value, category:$('#m-cat').value, concept:$('#m-concept').value, amount:$('#m-amount').value, person:$('#m-person').value}});
  $('#m-concept').value=''; $('#m-amount').value=''; toast('Apuntado'); loadAcc();
}
async function delMov(id){ if (await sure('¿Borrar movimiento?', {ok:'Borrar', danger:1})){ await api('/movements/'+id,{method:'DELETE'}); loadAcc(); } }

// ---------- inicio
const MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
function delta(now, before){
  if (!before) return '';
  const d = (now-before)/Math.abs(before)*100, up = d>=0;
  return `<span class="${up?'pos':'neg'}" style="font-size:13px;font-weight:600">${up?'▲':'▼'} ${Math.abs(d).toFixed(0)}%</span> <span class="mut" style="font-size:12px">vs mes pasado</span>`;
}
function stuck(o){
  const lim = (S.status_limits_h||{})[o.status], h = o.hours_in_status;
  return lim && h != null && h > lim ? `<br><span class="neg" style="font-size:11px" title="lleva demasiado en este estado">⏰ ${h>=48?(h/24).toFixed(1)+' d':Math.round(h)+' h'} en ${o.status}</span>` : '';
}
async function loadHome(){
  homeOrg();
  const d = await api('/dashboard'), h = new Date().getHours();
  $('#h-hello').textContent = `${h<14?'Buenos días':h<21?'Buenas tardes':'Buenas noches'}, ${ME.user}`;
  $('#h-sub').textContent = `${MESES[+d.month.slice(5)-1]} ${d.month.slice(0,4)} · ${d.new_this_week} pedido(s) nuevo(s) esta semana`;
  const open = ['recibido','programado','imprimiendo','postprocesado','listo'].reduce((a,s)=>a+(d.by_status[s]||0),0);
  $('#h-kpis').innerHTML = [
    [eur(d.this_month.ingresos), 'cobrado este mes', delta(d.this_month.ingresos, d.last_month.ingresos)],
    [eur(d.this_month.beneficio), 'beneficio este mes', `<span class="mut" style="font-size:12px">gastos ${eur(d.this_month.gastos)}</span>`, d.this_month.beneficio>=0?'pos':'neg'],
    [open, 'pedidos en marcha', d.overdue?`<span class="neg" style="font-size:13px;font-weight:600">${d.overdue} con la entrega pasada</span>`:`<span class="mut" style="font-size:12px">${d.orders_month} este mes</span>`],
    [eur(d.unpaid_total), 'pendiente de cobro', `<span class="mut" style="font-size:12px">${d.unpaid.length} pedido(s) entregados o listos</span>`, d.unpaid_total>0?'neg':''],
  ].map(([v,l,x,c])=>`<div class="card kpi"><div class="v ${c||''}">${v}</div><div class="l">${l}</div><div style="margin-top:6px">${x||''}</div></div>`).join('');
  $('#h-status').innerHTML = STATUSES.filter(s=>d.by_status[s]).map(s=>`<button class="tag st-${s}" style="cursor:pointer;font:inherit;font-size:12px" onclick="orderFilter='${s}';show('orders')">${s} · <b>${d.by_status[s]}</b></button>`).join('');
  const when = o => !o.due_date ? '<span class="mut">sin fecha</span>' : o.overdue ? `<span class="neg"><b>hace ${-o.days_left} d</b></span>` :
    o.days_left===0 ? '<b style="color:var(--acc)">hoy</b>' : o.days_left===1 ? '<b>mañana</b>' : `en ${o.days_left} d`;
  $('#h-upcoming').innerHTML = d.upcoming.length ? `<tr><th>Entrega</th><th>Cliente</th><th>Qué</th><th>Estado</th><th class="n">Total</th></tr>` +
    d.upcoming.map(o=>`<tr style="cursor:pointer${o.overdue?';background:color-mix(in srgb,var(--bad) 7%,transparent)':''}" onclick="openOrder(${o.id})">
      <td style="white-space:nowrap">${when(o)}${stuck(o)}</td><td><b>${esc(o.client)}</b>${o.assigned?`<br><span class="mut" style="font-size:12px">lo lleva ${esc(o.assigned)}</span>`:''}</td>
      <td style="font-size:13px">${esc(o.what)}</td><td><span class="tag st-${o.status}">${o.status}</span></td><td class="n">${eur(o.total)}</td></tr>`).join('')
    : '<tr><td class="mut">Nada pendiente. 🎉</td></tr>';
  $('#h-unpaid').innerHTML = d.unpaid.length ? d.unpaid.map(o=>`<div class="row" style="margin-bottom:6px;cursor:pointer" onclick="openOrder(${o.id})"><div>#${o.id} <b>${esc(o.client)}</b> <span class="tag st-${o.status}">${o.status}</span></div><div class="n" style="text-align:right;flex:0 0 auto"><b>${eur(o.total)}</b></div></div>`).join('') : '<p class="mut" style="margin:0">Todo cobrado.</p>';
  $('#h-stock-card').classList.toggle('hidden', !d.low_stock.length);
  $('#h-stock').innerHTML = d.low_stock.map(m=>`<div>⚠️ ${esc(m.name)} ${esc(m.color||'')} — quedan <b>${qfmt(m.level,m.unit)}</b></div>`).join('') + '<a href="#stk" onclick="show(\'stk\')" style="font-size:13px">ir al almacén</a>';
  $('#h-top').innerHTML = d.top_products.length ? `<tr><th>Producto</th><th class="n">Uds</th><th class="n">Facturado</th></tr>` + d.top_products.map(t=>`<tr><td>${esc(t.name)}</td><td class="n">${t.qty}</td><td class="n">${eur(t.total)}</td></tr>`).join('') : '<tr><td class="mut">Aún no hay ventas este mes.</td></tr>';
  $('#h-moves').innerHTML = d.recent_movements.map(m=>`<tr><td class="mut" style="white-space:nowrap">${m.date.slice(8,10)}/${m.date.slice(5,7)}</td><td>${esc(m.concept||m.category)}<br><span class="mut" style="font-size:12px">${esc(m.category)}${m.person?' · '+esc(m.person):''}</span></td><td class="n ${m.kind==='ingreso'?'pos':'neg'}">${m.kind==='gasto'?'−':''}${eur(m.amount)}</td></tr>`).join('') || '<tr><td class="mut">Sin movimientos.</td></tr>';
  $('#h-fc-card').classList.toggle('hidden', !(d.forecast||[]).length);
  $('#h-fc').innerHTML = (d.forecast||[]).map(m=>`<div class="row" style="margin-bottom:6px;align-items:center;cursor:pointer" onclick="show('stk')"><div>${m.status==='falta'?'🧵':'🛒'} <b>${esc(m.name)}</b>: <span>${m.status==='falta'?`faltan ${qfmt(-m.left, m.unit)} para los pedidos`:`se acaba hacia el ${m.runs_out}`}</span></div><span class="tag ${m.status==='falta'?'due':'soon'}" style="flex:0 0 auto">comprar ${m.buy_units}</span></div>`).join('');
  $('#h-maint-card').classList.toggle('hidden', !d.maintenance.length);
  $('#h-maint').innerHTML = d.maintenance.map(m=>`<div class="row" style="margin-bottom:6px;align-items:center;cursor:pointer" onclick="show('prn')"><div>${m.state==='toca'?'🔧':'🕐'} <b>${esc(m.printer)}</b>: <span>${esc(m.task)}</span></div><span class="tag ${m.state==='toca'?'due':'soon'}" style="flex:0 0 auto">${m.state==='toca'?'toca':'pronto'}</span></div>`).join('');
  $('#h-events-card').classList.toggle('hidden', !d.open_events.length);
  $('#h-events').innerHTML = d.open_events.map(e=>`<div style="margin-bottom:6px;cursor:pointer" onclick="POS.ev=${e.id};show('pos')">🏪 <b>${esc(e.name)}</b> <span class="mut">${esc(e.date||'')}</span></div>`).join('');
  api('/printers/status').then(ps=>{
    $('#h-printers-card').classList.toggle('hidden', !ps.length);
    $('#h-printers').innerHTML = ps.map(p=>{ const [lbl,cls] = p.online ? (ST[p.state]||[p.state,'']) : ['sin conexión','st-cancelado'];
      return `<div class="row" style="margin-bottom:8px;align-items:center;cursor:pointer" onclick="show('prn')"><div><b>${esc(p.name)}</b>${p.online&&p.state==='printing'?`<div class="bar" style="margin-top:4px"><i style="width:${p.progress}%;background:var(--acc)"></i></div><span class="mut" style="font-size:12px">${p.progress}% · fin ${p.eta?p.eta.slice(11,16):'?'}</span>`:''}</div><span class="tag ${cls}" style="flex:0 0 auto">${esc(lbl)}</span></div>`; }).join('');
  }).catch(()=>$('#h-printers-card').classList.add('hidden'));
}

// ---------- extracto mensual
const MES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
const REPCOLS = [['pedidos','Pedidos','n'],['piezas','Piezas','n'],['facturado','Facturado','e'],['iva','IVA repercutido','e'],
  ['horas_maquina','Horas máquina','h'],['kwh','kWh','k'],['luz','Luz','e'],['material','Material','e'],['merma','Merma','e'],
  ['amortizacion','Amortización','e'],['mantenimiento','Mantenimiento','e'],['horas_mano_obra','Horas mano obra','h'],['mano_obra','Mano de obra','e'],
  ['extras','Otros gastos','e'],['riesgo_fallo','Riesgo fallo','e'],['comisiones','Comisiones','e'],['coste_total','Coste total','e'],['beneficio','Beneficio','e']];
const fmtv = (v,t) => t==='e' ? eur(v) : t==='h' ? (v||0).toLocaleString(I18N.locale(),{maximumFractionDigits:1})+' h' : t==='k' ? (v||0).toLocaleString(I18N.locale(),{maximumFractionDigits:1}) : (v||0);
let REP = [];
async function loadRep(){
  const ys = $('#r-year'); if(!ys.options.length){ const y=new Date().getFullYear(); ys.innerHTML = opts([y,y-1,y-2], y); }
  REP = await api('/report/monthly?year='+ys.value); $('#r-csv').href = '/api/export/monthly.csv?year='+ys.value;
  const sum = k => REP.reduce((a,m)=>a+(m[k]||0),0);
  $('#r-kpis').innerHTML = [['facturado','Facturado','e'],['luz','Luz estimada','e'],['kwh','kWh','k'],['beneficio','Beneficio','e']]
    .map(([k,l,t])=>`<div class="card kpi"><div class="v">${fmtv(sum(k),t)}</div><div class="l">${l} · ${ys.value}</div></div>`).join('');
  if (!REP.length){ $('#rp-table').innerHTML='<tr><td class="mut">Sin pedidos este año</td></tr>'; $('#r-detail').innerHTML=''; return; }
  $('#rp-table').innerHTML = `<thead><tr><th></th>${REP.map((m,i)=>`<th class="n"><a href="#" onclick="event.preventDefault();repDetail(${i})">${MES[+m.month.slice(5)-1]}</a></th>`).join('')}<th class="n">Total</th></tr></thead><tbody>` +
    REPCOLS.map(([k,l,t])=>`<tr><td>${l}</td>${REP.map(m=>`<td class="n ${k==='beneficio'?(m[k]>=0?'pos':'neg'):''}">${fmtv(m[k],t)}</td>`).join('')}<td class="n"><b>${fmtv(sum(k),t)}</b></td></tr>`).join('') +
    `<tr class="sub"><td>Luz ya apuntada en contabilidad</td>${REP.map(m=>`<td class="n">${eur(m.luz_apuntada)}</td>`).join('')}<td></td></tr>
     <tr class="sub"><td>Líneas sin desglose</td>${REP.map(m=>`<td class="n">${m.lineas_sin_desglose||''}</td>`).join('')}<td></td></tr></tbody>`;
  repDetail(REP.length-1);
}
function repDetail(i){
  const m = REP[i], mes = MES[+m.month.slice(5)-1] + ' ' + m.month.slice(0,4);
  const tbl = (head, obj, f) => Object.keys(obj).length ? `<table><tr>${head.map(h=>`<th class="${h[1]||''}">${h[0]}</th>`).join('')}</tr>${Object.entries(obj).map(f).join('')}</table>` : '<p class="mut">—</p>';
  $('#r-detail').innerHTML = `<h2>Detalle de ${mes}</h2>
    <div class="row" style="margin-bottom:14px"><div><b>Luz estimada: ${eur(m.luz)}</b> <span class="mut">(${fmtv(m.kwh,'k')} kWh · ${fmtv(m.horas_maquina,'h')} de máquina)</span>
      ${m.luz_apuntada?`<br><span class="mut">Ya apuntado en contabilidad: ${eur(m.luz_apuntada)}</span>`:''}</div>
      <select id="r-person" style="flex:0 0 160px">${opts(S.people,'')}</select>
      <button class="btn" onclick="bookLight('${m.month}')">${m.luz_apuntada?'Actualizar':'Apuntar'} luz como gasto</button></div>
    <div class="grid g3">
      <div><h3 style="font-size:13px" class="mut">Por impresora</h3>${tbl([['Impresora'],['Horas','n'],['kWh','n'],['Luz','n']], m.por_impresora, ([k,v])=>`<tr><td>${esc(k)}</td><td class="n">${fmtv(v.horas,'h')}</td><td class="n">${fmtv(v.kwh,'k')}</td><td class="n">${eur(v.luz)}</td></tr>`)}</div>
      <div><h3 style="font-size:13px" class="mut">Material consumido</h3>${tbl([['Material'],['Cantidad','n'],['Coste','n']], m.por_material, ([k,v])=>`<tr><td>${esc(k)}</td><td class="n">${v.unidad==='€'?'—':fmtv(v.cantidad,'k')+' '+esc(v.unidad)}</td><td class="n">${eur(v.coste)}</td></tr>`)}</div>
      <div><h3 style="font-size:13px" class="mut">Por canal</h3>${tbl([['Canal'],['Pedidos','n'],['Facturado','n']], m.por_canal, ([k,v])=>`<tr><td>${esc(k)}</td><td class="n">${v.pedidos}</td><td class="n">${eur(v.facturado)}</td></tr>`)}</div>
    </div>
    ${m.lineas_sin_desglose?`<p class="mut" style="font-size:12px">${m.lineas_sin_desglose} línea(s) se metieron a mano sin calculadora: cuentan en facturado y coste, pero no en luz, material ni horas.</p>`:''}`;
}
async function bookLight(month){
  const r = await api('/report/electricity',{method:'POST',body:{month, person:$('#r-person').value}});
  toast(`Apuntado: ${eur(r.amount)} de luz`); loadRep();
}

// ---------- catálogo
// ---------- stock
const qfmt = (v,u) => v==null ? '—' : `${(+v).toLocaleString(I18N.locale(),{maximumFractionDigits:0})} ${u}`;
async function refreshLowStock(){
  MATS = await api('/materials');
  const low = MATS.filter(m=>m.active && m.stock_low);
  $('#lowstock').classList.toggle('hidden', !low.length);
  $('#lowstock').innerHTML = low.length ? `⚠️ <b>Stock bajo:</b> ${low.map(m=>`${esc(m.name)}${m.color?' '+esc(m.color):''} (${qfmt(m.stock_level,m.unit)})`).join(' · ')} <a href="#stk" onclick="show('stk')">ver almacén</a>` : '';
}
let SPDLG_ID = null;
async function loadStock(){
  await refreshLowStock();
  const all = $('#sk-showempty').checked;
  SPOOLS = await api('/spools' + (all ? '?all=1' : ''));
  const tares = await api('/spool-tares');
  // paleta de colores agrupada por material
  const groups = {};
  SPOOLS.forEach(sp=>{ (groups[sp.kind||sp.material||'—'] ||= []).push(sp); });
  $('#sk-palette').innerHTML = Object.keys(groups).length ? Object.entries(groups).map(([k, sps])=>`<div style="margin-bottom:10px"><b style="font-size:13px">${esc(k)}</b>
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:6px">${sps.map(sp=>`<div title="${esc(spoolLabel(sp))}" style="width:46px;text-align:center;font-size:10px;line-height:1.2;opacity:${sp.status==='gastada'?.35:1}">
      <div style="width:38px;height:38px;margin:0 auto 3px;border-radius:50%;border:2px solid var(--line);background:conic-gradient(${esc(sp.color_hex||'#888')} ${sp.pct}%, var(--bg) 0)"></div>${esc(sp.color_name||'?')}</div>`).join('')}</div></div>`).join('')
    : '<p class="mut" style="margin:0">Aún no hay bobinas. Añádelas abajo.</p>';
  $('#sk-table').innerHTML = SPOOLS.length ? `<tr><th><input type="checkbox" title="Marcar todas" onchange="$$('#sk-table .sk-ck').forEach(x=>x.checked=this.checked)"></th><th></th><th>Material</th><th>Marca</th><th>Color</th><th class="n">Queda</th><th>Ubicación</th><th>Estado</th><th></th></tr>` + SPOOLS.map(sp=>`<tr style="${sp.status==='gastada'?'opacity:.5':''}">
      <td><input type="checkbox" class="sk-ck" data-id="${sp.id}"></td><td><span style="display:inline-block;width:18px;height:18px;border-radius:50%;background:${esc(sp.color_hex||'#888')};border:1px solid var(--line)"></span></td>
      <td>${esc(sp.material)}</td><td>${esc(sp.brand)}</td><td>${esc(sp.color_name)}</td>
      <td class="n" style="min-width:120px">${qfmt(sp.remaining, sp.unit)}<div class="bar" style="height:5px;margin-top:3px"><i style="width:${sp.pct}%;background:${sp.pct<20?'var(--bad)':'var(--acc2)'}"></i></div></td>
      <td>${esc(sp.location)}</td><td><span class="tag ${sp.status==='abierta'?'st-imprimiendo':sp.status==='gastada'?'st-cancelado':'st-listo'}">${sp.status}</span></td>
      <td style="text-align:right;white-space:nowrap">${sp.status!=='gastada'?`<button class="btn sec sm" onclick="weighSpool(${sp.id})">Pesar</button> <button class="btn sec sm" onclick="editSpool(${sp.id})">Editar</button> <button class="btn sec sm" onclick="askFinish(${sp.id})">Gastada / borrar</button> <a class="btn sec sm" title="Etiqueta con QR" href="/labels/spools?ids=${sp.id}" target="_blank">QR</a>`:''}</td></tr>`).join('')
    : '<tr><td class="mut">Sin bobinas.</td></tr>';
  $('#tr-table').innerHTML = tares.length ? `<tr><th>Marca</th><th>Material</th><th class="n">Bobina vacía</th><th class="n">Pesadas</th></tr>` +
    tares.map(t=>`<tr><td>${esc(t.brand)}</td><td>${esc(t.kind)}</td><td class="n">${t.tare_g} g</td><td class="n">${t.samples}</td></tr>`).join('') : '<tr><td class="mut">Ninguna todavía.</td></tr>';
  { const cur = $('#sa-mat').value; $('#sa-mat').innerHTML = matOpts(cur) + '<option value="new">＋ Nuevo material…</option>';
    if (!MATS.some(m=>m.active) || cur==='new') $('#sa-mat').value = 'new'; else if (!cur && $('#sa-mat').value==='new') $('#sa-mat').selectedIndex = 0;
    $('#sa-kind').innerHTML = opts(SPOOL_KINDS, $('#sa-kind').value || 'PLA'); saMatChange(true); }
  $('#sa-person').innerHTML = opts(['',...S.people], $('#sa-person').value);
  $('#sa-brands').innerHTML = [...new Set([...SPOOLS.map(s=>s.brand), ...tares.map(t=>t.brand)].filter(Boolean))].map(b=>`<option value="${esc(b)}">`).join('');
  if (!$('#mk-needs').children.length) mkNeed();
  $('#st-table').innerHTML = `<tr><th>Material</th><th class="n">Queda</th><th class="n">Envases aprox.</th><th>Estado</th><th></th></tr>` +
    MATS.filter(m=>m.active).map(m=>`<tr><td><b>${esc(m.name)}</b> <span class="mut">${esc(m.kind)} ${esc(m.color)}</span></td>
      <td class="n">${qfmt(m.stock_level, m.unit)}</td><td class="n">${m.stock_level==null?'':(m.stock_level/m.qty).toFixed(1)}</td>
      <td>${m.stock_level==null?'<span class="mut">sin controlar</span>':m.stock_low?'<span class="tag" style="border-color:#d9a400">bajo</span>':'<span class="tag st-listo">ok</span>'}</td>
      <td style="text-align:right;white-space:nowrap">${m.spools?`<span class="mut" style="font-size:12px">${m.spools} bobina(s)</span>`:`<button class="btn sec sm" onclick="stockAdjust(${m.id})">Ajuste</button>`} <button class="btn sec sm" onclick="stockMoves(${m.id})">Movimientos</button> <button class="btn sec sm" onclick="priceHistory(${m.id})">Precios</button></td></tr>`).join('');
}
const COLOR_HEX = {negro:'#222222', blanco:'#f2f2f2', rojo:'#c62828', azul:'#1e5bb8', verde:'#3fae6a', amarillo:'#f2c200', naranja:'#ef7d22', gris:'#8a8a8a', rosa:'#e88fb3', morado:'#7b4bb8', lila:'#a585d6', violeta:'#7b4bb8', marron:'#7a4e2d', 'marrón':'#7a4e2d', beige:'#d8c3a0', dorado:'#c9a227', oro:'#c9a227', plata:'#c0c0c0', plateado:'#c0c0c0', cobre:'#b06a3b', bronce:'#9c6b30', turquesa:'#20b2aa', celeste:'#7ec8e3', cian:'#00a6c8', granate:'#7a1f2b', transparente:'#e8eef0', natural:'#efe7d6', piel:'#e8c4a8', caqui:'#8f8a5a', oliva:'#6b7a2f',
  black:'#222222', white:'#f2f2f2', red:'#c62828', blue:'#1e5bb8', green:'#3fae6a', yellow:'#f2c200', orange:'#ef7d22', grey:'#8a8a8a', gray:'#8a8a8a', pink:'#e88fb3', purple:'#7b4bb8', brown:'#7a4e2d', gold:'#c9a227', silver:'#c0c0c0'};
function colorHex(name){ const w = String(name||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').split(/[\s,/-]+/);
  for (const x of w) if (COLOR_HEX[x]) return COLOR_HEX[x]; return null; }
// ---------- pegar de Amazon / tienda
let SA_READ = null;
function saFindMat(kind, color){
  const k = (kind||'').toLowerCase(), c = (color||'').toLowerCase(), act = MATS.filter(m=>m.active && (m.kind||'').toLowerCase()===k);
  return act.find(m=>c && ((m.color||'').toLowerCase()===c || m.name.toLowerCase().split(/\s+/).includes(c) || m.name.toLowerCase().endsWith(' '+c)))
      || (!c ? act.find(m=>m.name.toLowerCase()===k) : null) || null;
}
async function saPaste(){
  const text = $('#sa-paste').value.trim(); if (!text) return;
  const box = $('#sa-pres'); box.className = 'sa-pres'; box.innerHTML = '<span class="mut">Leyendo…</span>';
  let r; try { r = await api('/spools/parse',{method:'POST',body:{text}}); } catch(e){ box.className = 'hidden'; return; }
  SA_READ = r;
  if (r.kind && !SPOOL_KINDS.includes(r.kind)) SPOOL_KINDS.push(r.kind);
  const m = r.kind ? saFindMat(r.kind, r.color_name) : null;
  if (m){ $('#sa-mat').value = m.id; saMatChange(true); }
  else if (r.kind){ $('#sa-mat').value = 'new'; $('#sa-kind').innerHTML = opts(SPOOL_KINDS, r.kind); delete $('#sa-mname').dataset.touched; }
  if (r.brand) $('#sa-brand').value = r.brand;
  if (r.color_name) $('#sa-cname').value = r.color_name;
  delete $('#sa-chex').dataset.touched;
  if (r.net_g) $('#sa-net').value = r.net_g;
  $('#sa-count').value = r.count || 1;
  if (r.price) $('#sa-paid').value = r.price;
  if (r.supplier) $('#sa-sup').value = r.supplier;
  saMatChange(true); saNewName(); saTare();
  const got = [r.brand, r.kind, r.colors?.join(', '), r.net_g ? qfmt(r.net_g, r.unit||'g') + (r.count>1 ? ` × ${r.count}` : '') : '', r.price!=null ? eur(r.price) : ''].filter(Boolean);
  const miss = [['kind','tipo'],['color_name','color'],['net_g','peso']].filter(([k])=>!r[k]).map(([,l])=>l);
  const multi = (r.colors||[]).length > 1;
  box.innerHTML = (got.length ? `<div>✓ <b>${esc(got.join(' · '))}</b></div>` : '<div>No he reconocido nada: rellénalo a mano.</div>')
    + (r.title && !/^https?:/.test(r.title) ? `<div class="mut" style="font-size:12px;margin-top:2px">${esc(r.title.slice(0,140))}</div>` : '')
    + (miss.length && got.length ? `<div class="mut" style="font-size:12.5px;margin-top:4px">Revisa: no he encontrado ${miss.join(', ')}.</div>` : '')
    + (r.note ? `<div class="mut" style="font-size:12.5px;margin-top:4px">${esc(r.note)}</div>` : '')
    + (multi ? `<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:center"><span style="font-size:13px">Son ${r.colors.length} colores:</span>
        <button class="btn sm" onclick="saAddEach()">Añadir una bobina de cada color</button><span class="mut" style="font-size:12px">o revisa el formulario para añadirlas iguales</span></div>` : '')
    + (multi ? '' : '<div class="mut" style="font-size:12.5px;margin-top:4px">Revisa el formulario y pulsa «Añadir al almacén».</div>');
}
async function saAddEach(){
  const r = SA_READ; if (!r || !(r.colors||[]).length) return;
  const n = r.colors.length, paid = num($('#sa-paid').value), kind = $('#sa-mat').value==='new' ? $('#sa-kind').value : (MATS.find(m=>m.id==$('#sa-mat').value)||{}).kind || r.kind || 'PLA';
  if (!await sure(`Se añadirán ${n} bobinas de ${$('#sa-brand').value||kind}: ${r.colors.join(', ')}.` + (paid ? ` Lo pagado (${eur(paid)}) se reparte entre ellas.` : ''), {title:'Una de cada color', ok:`Añadir ${n}`})) return;
  const ids = [];
  for (const c of r.colors){
    const m = saFindMat(kind, c);
    const body = {material_id: m ? m.id : 'new', new_material: m ? null : {name:`${kind} ${c.toLowerCase()}`, kind}, brand:$('#sa-brand').value, color_name:c,
      color_hex: colorHex(c) || '#888888', net_g:$('#sa-net').value, tare_g:$('#sa-tare').value, count:1, location:$('#sa-loc').value,
      paid_total: paid ? (paid/n).toFixed(2) : '', person:$('#sa-person').value, supplier:$('#sa-sup').value.trim(), update_price:$('#sa-upd').checked};
    const res = await api('/spools',{method:'POST',body}); ids.push(...res.map(x=>x.id));
    if (!m) MATS = await api('/materials');
  }
  $('#sa-paste').value = ''; $('#sa-pres').className = 'hidden'; SA_READ = null; ['#sa-cname','#sa-paid'].forEach(x=>$(x).value=''); $('#sa-count').value = 1;
  toast(`${ids.length} bobina(s) añadida(s)`); loadStock(); loadForecast();
  if (ids.length && await sure('¿Imprimir las etiquetas con QR de estas bobinas?', {ok:'Imprimir etiquetas'})) window.open('/labels/spools?ids=' + ids.join(','), '_blank');
}
const SPOOL_KINDS = ['PLA','PLA+','PLA Silk','PLA Mate','PLA-CF','PETG','PETG-CF','ABS','ASA','TPU','Nylon','PC','Resina'];
function saMatChange(quiet){
  const isNew = $('#sa-mat').value==='new';
  $$('.sa-new').forEach(e=>e.classList.toggle('hidden', !isNew));
  if (isNew){ saNewName(); if (!quiet) $('#sa-kind').focus(); }
  if (!quiet || !isNew) saTare();
}
function saAutoHex(){ const h = colorHex($('#sa-cname').value); if (h && !$('#sa-chex').dataset.touched) $('#sa-chex').value = h; }
function saNewName(){ saAutoHex();
  const n = $('#sa-mname'); if ($('#sa-mat').value!=='new' || n.dataset.touched) return;
  const k = $('#sa-kind').value, c = $('#sa-cname').value.trim().toLowerCase();
  n.value = k==='Resina' ? `Resina${c?' '+c:''}` : `${k}${c?' '+c:''}`;
}
async function saTare(){
  const m = MATS.find(x=>x.id==$('#sa-mat').value), b = $('#sa-brand').value.trim().toLowerCase();
  if (m) $('#sa-net').value = m.qty || 1000;
  const t = b && m ? (await api('/spool-tares')).find(x=>x.brand===b && x.kind===(m.kind||'').toLowerCase()) || (await api('/spool-tares')).find(x=>x.brand===b) : null;
  $('#sa-tarehelp').textContent = t ? `Bobina vacía de ${t.brand} (${t.kind}): ${t.tare_g} g, la sabemos de ${t.samples} pesada(s).` : (b ? 'Aún no sabemos lo que pesa vacía una bobina de esta marca: pésala cuando se acabe.' : '');
  if (t && !$('#sa-tare').value) $('#sa-tare').placeholder = t.tare_g + ' g';
}
async function addSpools(){
  const isNew = $('#sa-mat').value==='new';
  if (isNew && !$('#sa-mname').value.trim()) return toast('Ponle nombre al material nuevo');
  const locTxt = $('#sa-loc').value.trim(), locHit = LOCS.find(l=>l.path.toLowerCase()===locTxt.toLowerCase() || l.name.toLowerCase()===locTxt.toLowerCase());
  const r = await api('/spools',{method:'POST',body:{material_id:$('#sa-mat').value, brand:$('#sa-brand').value, location_id: locHit ? locHit.id : null,
    new_material: isNew ? {name:$('#sa-mname').value.trim(), kind:$('#sa-kind').value} : null, color_name:$('#sa-cname').value,
    color_hex:$('#sa-chex').value, net_g:$('#sa-net').value, tare_g:$('#sa-tare').value, count:$('#sa-count').value, location:$('#sa-loc').value,
    paid_total:$('#sa-paid').value, person:$('#sa-person').value, supplier:$('#sa-sup').value.trim(), update_price:$('#sa-upd').checked, shopping_id:SHOP.buying||null}});
  ['#sa-cname','#sa-tare','#sa-paid'].forEach(x=>$(x).value=''); $('#sa-count').value=1; delete $('#sa-chex').dataset.touched; $('#sa-paste').value=''; $('#sa-pres').className='hidden'; SA_READ=null;
  if (SHOP.buying){ SHOP.buying = null; $('#sa-shop').classList.add('hidden'); loadShopping(); }
  if (isNew){ const nm = $('#sa-mname').value.trim(); delete $('#sa-mname').dataset.touched; $('#sa-mname').value = '';
    MATS = await api('/materials'); const m = MATS.find(x=>x.name.toLowerCase()===nm.toLowerCase()); if (m) $('#sa-mat').innerHTML = matOpts(m.id), $('#sa-mat').value = m.id;
  }
  toast(`${r.length} bobina(s) añadida(s)`); loadStock(); loadForecast();
  if (r.length && await sure('¿Imprimir las etiquetas con QR de estas bobinas?', {ok:'Imprimir etiquetas'})) window.open('/labels/spools?ids=' + r.map(x=>x.id).join(','), '_blank');
}
async function weighSpool(id){
  const sp = SPOOLS.find(x=>x.id===id);
  const fl = [{k:'g', label:'¿Cuánto pesa ahora la bobina entera? (g)', type:'number', req:1}];
  if (!sp.suggested_tare) fl.push({k:'tare', label:`Peso de la bobina vacía de ${sp.brand||'esta marca'} (g)`, type:'number', req:1, hint:'Suele ser 150-250 g. Lo recordaré para esa marca.'});
  const f = await form('Pesar bobina', fl, {msg:spoolLabel(sp), ok:'Guardar peso'}); if (!f) return;
  const r = await api(`/spools/${id}/weigh`,{method:'POST',body:{gross:f.g, tare_g:String(f.tare||sp.suggested_tare)}});
  toast(`Quedan ${qfmt(r.remaining, r.unit)}`); loadStock();
}
async function editSpool(id){
  const sp = SPOOLS.find(x=>x.id===id);
  await ensureLocs();
  const f = await form('Editar bobina', [
    {k:'color_name', label:'Nombre del color', value:sp.color_name||''},
    LOCS.length ? {k:'location_id', label:'Ubicación', type:'select', value:sp.location_id||'', options:locFormOpts()}
                : {k:'location', label:'Ubicación', value:sp.location||'', placeholder:'estantería, caja seca…', hint:'Crea ubicaciones con QR en Almacén → Ubicaciones.'},
    {k:'supplier', label:'Proveedor', value:sp.supplier||'', list:'sup-list'}], {msg:spoolLabel(sp), ok:'Guardar'}); if (!f) return;
  if ('location_id' in f){ await api(`/spools/${id}/location`,{method:'PUT',body:{location_id:f.location_id||null}}); delete f.location_id; }
  await api('/spools/'+id,{method:'PUT',body:f}); loadStock();
}
function askFinish(id){
  const sp = SPOOLS.find(x=>x.id===id); SPDLG_ID = id;
  $('#sp-title').textContent = spoolLabel(sp); $('#sp-brand').textContent = `${sp.brand||'esta marca'} · ${sp.kind||sp.material}`;
  $('#sp-empty').value = ''; $('#spdlg').showModal();
}
async function finishSpool(del){
  if (del && !await sure('¿Borrar la bobina del almacén? Si solo se ha gastado, mejor «Marcar como gastada» para conservar el historial.', {ok:'Borrar', danger:1})) return;
  const r = await api(`/spools/${SPDLG_ID}/finish`,{method:'POST',body:{empty_g:$('#sp-empty').value.replace(',','.'), delete:del}});
  $('#spdlg').close(); toast(r.learned ? 'Guardado el peso de la bobina vacía para esa marca' : del ? 'Bobina borrada' : 'Bobina gastada'); loadStock();
}
async function saveTare(){
  await api('/spool-tares',{method:'PUT',body:{brand:$('#tr-brand').value, kind:$('#tr-kind').value, tare_g:$('#tr-g').value}});
  ['#tr-brand','#tr-kind','#tr-g'].forEach(x=>$(x).value=''); loadStock();
}
// ¿Lo puedo imprimir?
function mkNeed(kind='PLA', hex='#222222', grams=''){
  const d = document.createElement('div'); d.className='row'; d.style.marginBottom='6px';
  d.innerHTML = `<div><input class="mk-k" value="${esc(kind)}" placeholder="Material"></div><div style="flex:0 0 60px"><input class="mk-c" type="color" value="${esc(hex)}" style="height:38px;padding:3px"></div><div><input class="mk-g" type="number" value="${grams}" placeholder="g"></div><button class="btn sec sm" onclick="this.parentNode.remove()">✕</button>`;
  $('#mk-needs').append(d);
}
function mkFromSlicer(){
  const p = SLICE[0]; if (!p) return toast('Primero suelta el 3MF o G-code en la calculadora');
  $('#mk-needs').innerHTML=''; p.filaments.forEach(f=>mkNeed(f.type||'PLA', /^#[0-9a-f]{6}$/i.test(f.color)?f.color:'#888888', f.grams.toFixed(1))); mkCheck();
}
async function mkCheck(){
  const needs = $$('#mk-needs .row').map(r=>({kind:r.querySelector('.mk-k').value, color_hex:r.querySelector('.mk-c').value, grams:r.querySelector('.mk-g').value}));
  const r = await api('/spools/match',{method:'POST',body:{needs}});
  $('#mk-result').innerHTML = `<p style="margin:0 0 8px"><b class="${r.all_ok?'pos':'neg'}">${r.all_ok?'✓ Lo puedes imprimir con lo que tienes':'✗ Te falta algo'}</b></p>` + r.results.map(x=>`
    <div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:8px;font-size:13px"><span style="flex:0 0 22px;height:22px;border-radius:50%;background:${esc(x.need.color_hex)};border:1px solid var(--line)"></span>
    <div><b>${esc(x.need.kind)} ${x.need.grams?x.need.grams+' g':''}</b> — ${x.ok?'<span class="pos">lo tienes</span>':x.close?'<span style="color:#b58900">algo parecido</span>':'<span class="neg">no lo tienes</span>'}
    ${x.candidates.slice(0,3).map(c=>`<br><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${esc(c.color_hex||'#888')};border:1px solid var(--line)"></span> ${esc(c.brand)} ${esc(c.material)} ${esc(c.color_name)} · ${qfmt(c.remaining,'g')}${c.location?' · '+esc(c.location):''} <span class="mut">${c.distance<=45?'mismo color':c.distance<=90?'parecido':'distinto'}${c.same_kind?'':' · otro material'}${c.enough?'':' · no llega'}</span>`).join('')}</div></div>`).join('');
}
async function stockBuy(id){
  const m = MATS.find(x=>x.id===id);
  const f = await form('Entrada de material', [
    {k:'packs', label:`¿Cuántos envases de ${m.qty} ${m.unit}?`, type:'number', value:'1', req:1},
    {k:'paid', label:'Pagado en total (€)', type:'number', value:(+m.price||0).toFixed(2), hint:'Vacío = no apuntar el gasto en contabilidad.'},
    {k:'person', label:'¿Quién lo pagó?', type:'select', value:S.people[0]||'', options:[['','—'], ...S.people.map(x=>[x,x])]},
    {k:'supplier', label:'Proveedor', list:'sup-list'}], {msg:m.name, ok:'Registrar entrada'}); if (!f) return;
  await api(`/materials/${id}/stock`,{method:'POST',body:{mode:'compra', ...f}});
  toast('Entrada registrada' + (f.paid ? ' y gasto apuntado' : '')); loadStock(); loadForecast();
}
async function stockAdjust(id){
  const m = MATS.find(x=>x.id===id);
  const v = await ask(`¿Cuánto queda de verdad? (${m.unit})`, m.stock_level ?? '', {title:'Ajustar stock: '+m.name, type:'number', hint:'Pesa las bobinas sin el carrete.', ok:'Ajustar'}); if(v===null||v==='') return;
  await api(`/materials/${id}/stock`,{method:'POST',body:{mode:'ajuste', amount:v.replace(',','.')}}); toast('Stock ajustado'); loadStock();
}
async function stockMoves(id){
  const m = MATS.find(x=>x.id===id), mv = await api(`/materials/${id}/moves`);
  await tell('', {title:m.name+' · últimos movimientos', html: mv.length ? `<div class="scroll"><table><tr><th>Fecha</th><th class="n">Cantidad</th><th>Nota</th></tr>${mv.map(x=>`<tr><td>${esc(x.date)}</td><td class="n ${x.delta>0?'pos':'neg'}">${x.delta>0?'+':''}${x.delta} ${esc(m.unit)}</td><td>${esc(x.note)}</td></tr>`).join('')}</table></div>` : '<p class="mut">Ninguno</p>'});
}

// ---------- impresoras conectadas
let prnTimer = null, PSTAT = [];
const ST = {printing:['Imprimiendo','st-imprimiendo'], paused:['En pausa','st-recibido'], complete:['Terminada','st-listo'], standby:['Libre','st-listo'],
  cancelled:['Cancelada','st-cancelado'], error:['Error','st-cancelado']};
const hm = s => s==null ? '–' : `${Math.floor(s/3600)} h ${String(Math.round(s%3600/60)).padStart(2,'0')} min`;
async function loadPrinters(){
  loadMaint();
  await refreshPrinters(); clearInterval(prnTimer); prnTimer = setInterval(refreshPrinters, 10000);
}
async function refreshPrinters(){
  if ($('#v-prn').classList.contains('hidden')) return clearInterval(prnTimer);
  PSTAT = await api('/printers/status');
  $('#pr-help').innerHTML = PSTAT.length ? 'Se actualiza cada 10 s.' : `No hay impresoras conectadas. ${ME.role==='admin'?'Configúralas en <a href="#cfg" onclick="show(\'cfg\')">Ajustes → Impresoras</a> (Conexión: Moonraker, OctoPrint o PrusaLink + IP).':'Pide a un administrador que las configure.'}`;
  $('#pr-cards').innerHTML = PSTAT.map(p=>{
    if (!p.online) return `<div class="card"><h2>${esc(p.name)}</h2><p class="neg" style="margin:0">Sin conexión: ${esc(p.error)}</p><p class="mut" style="font-size:12px">${esc(p.host)}${p.via==='bridge'?' · vía puente':''}</p></div>`;
    const [lbl, cls] = ST[p.state] || [p.state, ''];
    const t = (o) => o && o.temperature!=null ? `${Math.round(o.temperature)}°${o.target?' / '+Math.round(o.target)+'°':''}` : '–';
    return `<div class="card"><div class="row" style="align-items:center"><h2 style="margin:0">${esc(p.name)}</h2><div></div><span class="tag ${cls}" style="flex:0 0 auto">${esc(lbl)}</span></div>
      ${p.state==='printing'||p.state==='paused' ? `<div style="margin:12px 0 4px;font-size:13px">${esc(p.filename)}</div>
        <div class="bar"><i style="width:${p.progress}%;background:var(--acc)"></i></div>
        <div class="row" style="font-size:13px;margin-top:6px"><div><b>${p.progress}%</b></div><div class="n" style="text-align:right">${p.remaining!=null?`quedan ${hm(p.remaining)} · fin ${p.eta.slice(11,16)}`:''}</div></div>` :
        `<p class="mut" style="font-size:13px">${p.filename?'Último: '+esc(p.filename):'Sin trabajo'}</p>`}
      <div class="mut" style="font-size:12px;margin-top:8px">Boquilla ${t(p.extruder)} · Cama ${t(p.bed)} · ${esc(p.host)}${p.via==='bridge'?' · vía puente':''}</div>
      <button class="btn sec sm" style="margin-top:10px" onclick="printerHistory(${p.id})">Historial e impresiones reales</button>
      ${['printing','paused','cancelled','error'].includes(p.state)?`<button class="btn sec sm" style="margin-top:10px" onclick="printerFailure(${p.id})">Ha fallado</button>`:''}</div>`;
  }).join('');
}
async function printerFailure(pid){
  const p = PSTAT.find(x=>x.id===pid), os = (await api('/orders?status=imprimiendo'));
  if (!os.length) return toast('No hay pedidos en «imprimiendo»');
  const lines = []; os.forEach(o=>o.items.forEach((it,i)=>{ if (it.calc_result) lines.push({o, i, it}); }));
  if (!lines.length) return toast('No hay pedidos en «imprimiendo»');
  const f = await form('Ha fallado: '+p.name, [
    {k:'n', label:'¿Qué pieza era?', type:'select', options:lines.map((l,k)=>[k, `#${l.o.id} ${l.o.client} · ${l.it.description}`])},
    {k:'pct', label:'Porcentaje al que se paró', type:'number', value:String(Math.round(p.progress)), req:1},
    {k:'cause', label:'¿Qué pasó? (opcional)', placeholder:'despegue, espagueti, atasco…'}], {ok:'Apuntar fallo'}); if (!f) return;
  const l = lines[+f.n];
  await api(`/orders/${l.o.id}/failures`,{method:'POST',body:{item_index:l.i, pct:f.pct, cause:f.cause}}); toast('Fallo apuntado');
}
async function testPrinter(id, btn){
  btn.textContent='…'; const r = await api(`/printers/${id}/test`,{method:'POST'});
  btn.textContent='Probar'; toast(r.ok ? `Conectada ✓ ${r.hostname||''} · Klipper ${r.klippy_state||''}` : 'No conecta: '+r.error);
}
async function printerHistory(id){
  const p = PSTAT.find(x=>x.id===id), [jobs, orders] = await Promise.all([api(`/printers/${id}/history`), api('/orders')]);
  const oo = orders.filter(o=>o.status!=='cancelado');
  $('#pr-hist').classList.remove('hidden');
  $('#pr-hist').innerHTML = `<h2>Historial de ${esc(p.name)}</h2><p class="mut" style="font-size:12px;margin-top:0">Asigna cada impresión a su pedido para guardar el tiempo y el filamento <b>reales</b> junto a lo estimado.</p>
    <div class="scroll"><table><tr><th>Fin</th><th>Archivo</th><th>Estado</th><th class="n">Real</th><th class="n">Estimado</th><th class="n">Filamento</th><th>Pedido</th></tr>` +
    jobs.map(j=>`<tr><td>${j.end_time?new Date(j.end_time*1000).toLocaleString(I18N.locale(),{dateStyle:'short',timeStyle:'short'}):'–'}</td><td style="font-size:13px">${esc(j.filename)}</td>
      <td>${esc(j.status)}</td><td class="n">${hm(j.print_duration)}</td><td class="n mut">${hm(j.estimated_time)}</td>
      <td class="n">${j.filament_g?j.filament_g.toFixed(1)+' g':((j.filament_mm||0)/1000).toFixed(2)+' m'}</td>
      <td><select onchange="assignJob(${id},'${esc(j.job_id)}',this.value)"><option value="">—</option>${oo.map(o=>`<option value="${o.id}" ${o.id===j.order_id?'selected':''}>#${o.id} ${esc(o.client)}</option>`).join('')}</select></td></tr>`).join('') +
    `</table></div>`;
  $('#pr-hist').scrollIntoView({behavior:'smooth'});
}
async function assignJob(pid, job, oid){ await api(`/printers/${pid}/history/${encodeURIComponent(job)}/assign`,{method:'POST',body:{order_id:oid?+oid:null}}); toast(oid?`Asignada al pedido #${oid}`:'Desasignada'); }
async function sendToPrinter(fid){
  const ps = await api('/printers/status'), on = ps.filter(p=>p.online);
  if (!on.length) return toast('No hay impresoras conectadas');
  const pid = await choose('¿A qué impresora?', on.map(p=>({value:p.id, label:p.name, sub:(ST[p.state]||[p.state])[0]}))); if (pid==null) return;
  const p = on.find(x=>x.id===pid);
  const f = await form('Enviar a '+p.name, [{k:'start', type:'checkbox', label:'Empezar a imprimir ya', value:false, hint:'Sin marcar: solo se sube y lo arrancas tú desde la impresora.'}], {ok:'Enviar'}); if (!f) return;
  const start = f.start;
  if (start && !await sure(`${p.name} empezará a imprimir ahora. Comprueba que la cama está libre y el filamento cargado.`, {title:'¿Seguro?', ok:'Imprimir ya', danger:1})) return;
  toast('Enviando…');
  const r = await api(`/printers/${p.id}/send`,{method:'POST',body:{file_id:fid, start, order_id:curOrder?.id}});
  toast(r.queued ? r.message : r.started ? `${p.name} imprimiendo ${r.filename}` : `Subido a ${p.name}: ${r.filename}`);
  if (r.started && curOrder?.id){ dlg.close(); loadOrders(); refreshLowStock(); }
}

// ---------- usuarios
async function loadUsers(){
  const us = await api('/users');
  $('#us-table').innerHTML = `<tr><th>Usuario</th><th>Rol</th><th></th></tr>` + us.map(u=>`<tr><td><b>${esc(u.username)}</b>${u.username===ME.user?' <span class="mut">(tú)</span>':''}</td>
    <td><select onchange="setRole('${esc(u.username)}',this.value)">${opts([['user','Usuario'],['admin','Administrador']],u.role,x=>x)}</select></td>
    <td style="text-align:right;white-space:nowrap"><button class="btn sec sm" onclick="resetPw('${esc(u.username)}')">Cambiar contraseña</button>
    ${u.username===ME.user?'':`<button class="btn sec sm" onclick="delUser('${esc(u.username)}')">✕</button>`}</td></tr>`).join('');
}
async function addUser(){
  await api('/users',{method:'POST',body:{username:$('#nu-name').value, password:$('#nu-pw').value, role:$('#nu-role').value}});
  $('#nu-name').value=''; $('#nu-pw').value=''; toast('Usuario creado'); loadUsers();
}
async function setRole(u, role){ try{ await api('/users/'+encodeURIComponent(u),{method:'PUT',body:{role}}); toast('Rol cambiado'); }catch(e){} loadUsers(); }
async function resetPw(u){ const pw = await ask('Nueva contraseña (mín. 8)', '', {title:'Contraseña de '+u, type:'password', ok:'Cambiar'}); if(!pw) return;
  await api('/users/'+encodeURIComponent(u),{method:'PUT',body:{password:pw}}); toast('Contraseña cambiada'); }
async function delUser(u){ if (!await sure(`¿Borrar el usuario ${u}?`, {ok:'Borrar', danger:1})) return; await api('/users/'+encodeURIComponent(u),{method:'DELETE'}); loadUsers(); }
async function changeMyPw(){
  if ($('#me-new').value !== $('#me-new2').value) return toast('Las contraseñas nuevas no coinciden');
  await api('/me/password',{method:'POST',body:{current:$('#me-cur').value, new:$('#me-new').value}});
  ['#me-cur','#me-new','#me-new2'].forEach(x=>$(x).value=''); toast('Contraseña cambiada');
}

async function loadCat(){
  PRODUCTS = await api('/products'); loadOffers();
  const nKit = {}; for (const p of PRODUCTS.filter(p=>p.kind==='conjunto')) nKit[p.id] = '';
  $('#p-table').innerHTML = `<tr><th></th><th>Producto</th><th>Categoría</th><th class="n">Precio</th><th class="n">Coste</th><th>Stock</th><th>Tienda</th><th></th></tr>` +
    (PRODUCTS.map(p=>`<tr><td>${p.image?`<img class="thumb" src="/media/${esc(p.image)}">`:''}</td><td>${p.kind==='conjunto'?'<span class="tag st-programado" style="font-size:11px">conjunto</span> ':''}<b>${esc(p.name)}</b>${p.sku?`<br><span class="mut" style="font-size:12px">${esc(p.sku)}</span>`:''}</td>
      <td>${esc(p.category)}</td><td class="n">${eur(p.unit_price)}${p.public_price!=null?`<br><span class="mut" style="font-size:12px">web ${eur(p.public_price)}</span>`:''}</td><td class="n">${eur(p.unit_cost)}</td>
      <td>${p.stock==null?'<span class="mut">bajo pedido</span>':p.stock}${(p.variants||[]).length?`<br><span class="mut" style="font-size:12px">${p.variants.map(v=>`${esc(v.name)}${v.stock!=null?' '+v.stock:''}`).join(' · ')}</span>`:''}</td><td>${p.public?'<span class="tag st-listo">pública</span>':''}</td>
      <td style="text-align:right;white-space:nowrap"><button class="btn sec sm" onclick="editProd(${p.id})">Ficha</button> ${p.kind==='conjunto'?'':`<button class="btn sec sm" onclick="loadProd(${p.id})">Calculadora</button> `}<button class="btn sec sm" onclick="updProd(${p.id})">Actualizar precio</button> <button class="btn sec sm" onclick="delProd(${p.id})">✕</button></td></tr>`).join('') || '<tr><td colspan="8" class="mut">Guarda productos desde la calculadora</td></tr>');
}
function loadProd(id){ const p=PRODUCTS.find(x=>x.id===id); show('calc'); $('#c-name').value=p.name; loadCalcInput(JSON.parse(p.calc_json)); }
async function updProd(id){ const p=PRODUCTS.find(x=>x.id===id);
  if (p.kind==='conjunto'){ const k = await api(`/products/${id}/kit`); await api('/products/'+id,{method:'PUT',body:{unit_price:k.suggested_price, unit_cost:k.cost}}); toast(`${p.name}: ${eur(k.suggested_price)}`); return loadCat(); }
  const r=await api('/calc',{method:'POST',body:JSON.parse(p.calc_json)});
  await api('/products/'+id,{method:'PUT',body:{unit_price:r.unit.price, unit_cost:r.cost_unit}}); toast(`${p.name}: ${eur(r.unit.price)}`); loadCat(); }
const pdlg = $('#pdlg'); let curProd = null;
function editProd(id){
  curProd = PRODUCTS.find(x=>x.id===id);
  $('#p-name').value=curProd.name; $('#p-sku').value=curProd.sku||''; $('#p-cat').value=curProd.category||'';
  $('#p-cats').innerHTML = [...new Set(PRODUCTS.map(p=>p.category).filter(Boolean))].map(c=>`<option value="${esc(c)}">`).join('');
  $('#p-price').value=curProd.unit_price; $('#p-cost').value=curProd.unit_cost; $('#p-pprice').value=curProd.public_price??'';
  $('#p-stock').value=curProd.stock??''; $('#p-lead').value=curProd.lead_days??3; $('#p-desc').value=curProd.description||'';
  $('#p-notes').value=curProd.notes||''; $('#p-public').checked=!!curProd.public; $('#p-file').value='';
  $('#p-img').classList.toggle('hidden', !curProd.image); if(curProd.image) $('#p-img').src='/media/'+curProd.image;
  let pi = {}; try { pi = JSON.parse(curProd.print_info||'{}'); } catch(e){}
  $('#p-ficha').innerHTML = Object.keys(pi).length ? 'Ficha: ' + [...FICHA, ['materials','Materiales']].filter(([k])=>pi[k]).map(([k,l])=>`${l} <b>${esc(pi[k])}</b>`).join(' · ') : '';
  $('#p-mfile').value=''; loadProdFiles();
  $('#p-zip').href = `/api/products/${curProd.id}/download.zip`;
  $('#p-instr').value = curProd.instructions||'';
  $('#p-kit').classList.toggle('hidden', curProd.kind!=='conjunto'); $('#pk-sugg').classList.toggle('hidden', curProd.kind!=='conjunto');
  $('#p-var').classList.toggle('hidden', curProd.kind==='conjunto'); PV = (curProd.variants||[]).map(v=>({...v})); pvRender(); mfLink();
  $('#p-min').value = curProd.min_stock || '';
  KIT = {items:[], parts:[]}; pkRender();
  ensureLocs().then(()=>{ $('#p-loc').innerHTML = locOpts(curProd.location_id); });
  loadKit();
  pdlg.showModal();
}
let KIT = {items:[], parts:[]};
async function loadKit(){
  const [k] = await Promise.all([api(`/products/${curProd.id}/kit`), ensureComps()]); KIT = k;
  $('#pk-add').innerHTML = '<option value="">+ añadir pieza del catálogo…</option>' + PRODUCTS.filter(p=>p.kind!=='conjunto').map(p=>`<option value="${p.id}">${esc(p.name)} — ${eur(p.unit_price)}</option>`).join('');
  $('#pk-add').onchange = e => { const p = PRODUCTS.find(x=>x.id==e.target.value); e.target.value=''; if(!p) return; pkRead(); KIT.items.push({product_id:p.id, name:p.name, qty:1, notes:'', unit_price:p.unit_price, unit_cost:p.unit_cost, files:0}); pkRender(); };
  pkRender();
}
function pkRender(){
  $('#pk-items').innerHTML = KIT.items.length ? `<tr><th>Pieza</th><th style="width:70px">Uds</th><th>Notas</th><th class="n">Precio</th><th></th></tr>` + KIT.items.map((it,i)=>`<tr data-k="${i}"><td>${esc(it.name)}${it.files?` <span class="mut" style="font-size:12px">📎${it.files}</span>`:''}</td>
    <td><input class="pk-q" type="number" min="1" value="${it.qty}"></td><td><input class="pk-n" value="${esc(it.notes||'')}" placeholder="color, relleno…"></td><td class="n">${eur(it.unit_price*it.qty)}</td>
    <td><button class="btn sec sm" onclick="pkRead();KIT.items.splice(${i},1);pkRender()">✕</button></td></tr>`).join('') : '<tr><td class="mut">Añade las piezas que lo forman.</td></tr>';
  $('#pk-parts').innerHTML = KIT.parts.length ? `<tr><th>Componente</th><th style="width:92px">Por ud.</th><th style="width:96px">€/ud</th><th>Notas</th><th></th></tr>` + KIT.parts.map((pt,i)=>{
      const c = pkComp(pt.name);
      return `<tr data-p="${i}"><td><input class="pp-name" list="comp-list" value="${esc(pt.name)}" placeholder="Elige de tus componentes o escribe" oninput="pkLive(this)">
        <div class="pp-info mut">${c ? `✓ del almacén · hay ${+c.stock.toFixed(3)} ${esc(c.unit)}${c.location?' · 📍 '+esc(c.location):''}` : pt.name ? 'no está en el almacén: no se descuenta' : ''}</div></td>
      <td><input class="pp-q" type="number" step="any" min="0" value="${pt.qty}"></td><td><input class="pp-c" type="number" step="0.01" value="${c ? c.unit_cost : pt.unit_cost}" ${c?'readonly title="Lo marca el componente"':''}></td><td><input class="pp-n" value="${esc(pt.notes||'')}"></td>
      <td><button class="btn sec sm" onclick="pkRead();KIT.parts.splice(${i},1);pkRender()">✕</button></td></tr>`; }).join('') : '';
  const kit = curProd?.kind==='conjunto';
  const pp = KIT.items.reduce((a,i)=>a+i.unit_price*i.qty,0), pc = KIT.items.reduce((a,i)=>a+i.unit_cost*i.qty,0), xc = KIT.parts.reduce((a,p)=>a+(+p.unit_cost||0)*(+p.qty||0),0);
  KIT.suggested_price = +(pp + xc*(1+(S.margin_pct||0)/100)).toFixed(2);
  $('#pk-sum').innerHTML = kit ? `Piezas ${eur(pp)} · componentes ${eur(xc)} · coste total <b>${eur(pc+xc)}</b> · precio sugerido <b>${eur(KIT.suggested_price)}</b>`
    : xc ? `Componentes: <b>${eur(xc)}</b> por unidad (se suman al coste al guardar; el precio, con «Recalcular todos los precios»)` : '';
}
function pkComp(name){ const n = String(name||'').trim().toLowerCase(); return n ? COMPS.find(c=>c.name.toLowerCase()===n) : null; }
function pkLive(inp){ const c = pkComp(inp.value), tr = inp.closest('tr');
  tr.querySelector('.pp-info').textContent = c ? `✓ del almacén · hay ${+c.stock.toFixed(3)} ${c.unit}${c.location?' · 📍 '+c.location:''}` : inp.value ? 'no está en el almacén: no se descuenta' : '';
  const cc = tr.querySelector('.pp-c'); if (c){ cc.value = c.unit_cost; cc.readOnly = true; } else cc.readOnly = false; }
function pkRead(){
  KIT.items = $$('#pk-items tr[data-k]').map(r=>({...KIT.items[r.dataset.k], qty:+r.querySelector('.pk-q').value||1, notes:r.querySelector('.pk-n').value}));
  KIT.parts = $$('#pk-parts tr[data-p]').map(r=>{ const name = r.querySelector('.pp-name').value, c = pkComp(name);
    return {name, component_id:c?c.id:null, qty:+r.querySelector('.pp-q').value||0, unit_cost:+r.querySelector('.pp-c').value||0, notes:r.querySelector('.pp-n').value}; });
}
function pkPart(){ pkRead(); KIT.parts.push({name:'', qty:1, unit_cost:0, notes:''}); pkRender(); }
function pkUseSuggested(){ pkRead(); pkRender(); $('#p-price').value = KIT.suggested_price; }
async function makeStock(){
  const pv = await pickVariant(curProd, false, false); if (!pv) return;
  const lbl = curProd.name + (pv.variant ? ` (${pv.variant.name})` : '');
  const n = await ask('¿Cuántas unidades quieres fabricar para tener en stock?', '5', {title:lbl, type:'number', ok:'Crear pedido'}); if (!n) return;
  const o = await api(`/products/${curProd.id}/make`,{method:'POST',body:{qty:+n, variant_id:pv.variant?.id}});
  pdlg.close(); toast(`Pedido #${o.id} creado: al pasar a «listo» se suman ${n} al stock`); openOrder(o.id);
}
async function newKit(){
  const name = await ask('Nombre del conjunto', '', {title:'Nuevo conjunto', placeholder:'p. ej. Granada de airsoft M67', ok:'Crear'}); if (!name) return;
  const p = await api('/products',{method:'POST',body:{name, calc_json:{}, kind:'conjunto'}});
  PRODUCTS = await api('/products'); editProd(p.id);
}
async function upload(kind, file){
  const fd = new FormData(); fd.append('file', file);
  const r = await fetch('/api/upload/'+kind, {method:'POST', body:fd}); const j = await r.json();
  if(!r.ok){ toast(j.error||'Error al subir'); throw new Error(j.error); } return j;
}
async function loadProdFiles(){
  const fs = await api(`/products/${curProd.id}/files`);
  const isImg = n => /\.(jpe?g|png|webp)$/i.test(n);
  $('#p-files').innerHTML = (fs.some(f=>isImg(f.name)) ? `<div class="p-photos">${fs.filter(f=>isImg(f.name)).map(f=>`<a href="/api/files/${f.id}?inline=1" target="_blank"><img src="/api/files/${f.id}?inline=1" alt="${esc(f.name)}" loading="lazy"></a>`).join('')}</div>` : '')
    + fs.map(f=>`<div class="row" style="margin-bottom:4px;align-items:center"><div style="flex:3">📎 <a href="/api/files/${f.id}">${esc(f.name)}</a> <span class="mut" style="font-size:12px">${fsize(f.size)}</span></div><button class="btn sec sm" onclick="delProdFile(${f.id})">✕</button></div>`).join('') || '<p class="mut" style="margin:0;font-size:13px">Sin archivos. Al añadir este producto a un pedido, el pedido hereda sus archivos.</p>';
}
async function delProdFile(fid){ if (!await sure('¿Quitar archivo?', {ok:'Quitar', danger:1})) return; await api('/files/'+fid,{method:'DELETE'}); loadProdFiles(); }
async function saveProd(){
  for (const f of $('#p-mfile').files) await uploadModel(f, {product_id: curProd.id});
  const nz = v => v==='' ? null : +v;
  await api('/products/'+curProd.id,{method:'PUT',body:{name:$('#p-name').value, sku:$('#p-sku').value, category:$('#p-cat').value,
    unit_price:+$('#p-price').value||0, unit_cost:+$('#p-cost').value||0, public_price:nz($('#p-pprice').value), stock:nz($('#p-stock').value),
    lead_days:+$('#p-lead').value||0, description:$('#p-desc').value, notes:$('#p-notes').value, public:$('#p-public').checked?1:0,
    min_stock:Math.max(0, Math.round(+$('#p-min').value||0)), location_id:$('#p-loc').value||null,
    instructions:$('#p-instr').value, ...(PV.length ? {} : {stock:nz($('#p-stock').value)})}});
  if (curProd.kind!=='conjunto'){ pvRead(); if (PV.some(v=>!v.name.trim())) { toast('Pon nombre a todas las variantes'); return; }
    if (PV.length || (curProd.variants||[]).length) await api(`/products/${curProd.id}/variants`,{method:'PUT',body:{variants:PV}}); }
  pkRead();
  if (curProd.kind==='conjunto'){ const k = await api(`/products/${curProd.id}/kit`,{method:'PUT',body:{items:KIT.items, parts:KIT.parts}});
    if (!(+$('#p-price').value)) await api('/products/'+curProd.id,{method:'PUT',body:{unit_price:k.suggested_price}}); }
  else await api(`/products/${curProd.id}/kit`,{method:'PUT',body:{parts:KIT.parts}});
  const f = $('#p-file').files[0]; if (f) await upload('product-'+curProd.id, f);
  pdlg.close(); toast('Producto guardado'); loadCat();
}
async function recalcAll(){
  if (!await sure('Recalcula precio y coste de todos los productos con los ajustes actuales (margen, luz, materiales…).', {title:'Recalcular precios', ok:'Recalcular'})) return;
  const r = await api('/products/recalculate',{method:'POST'});
  const ch = r.filter(x=>x.old_price!==x.new_price);
  toast(ch.length ? `${ch.length} precio(s) cambiado(s)` : 'Ningún precio ha cambiado');
  if (ch.length) await tell('', {title:'Precios cambiados', html:`<table>${ch.map(x=>`<tr><td>${esc(x.name)}</td><td class="n mut">${eur(x.old_price)}</td><td class="n"><b>${eur(x.new_price)}</b></td></tr>`).join('')}</table>`});
  loadCat();
}
async function delProd(id){ if (await sure('¿Borrar producto?', {ok:'Borrar', danger:1})){ await api('/products/'+id,{method:'DELETE'}); loadCat(); } }

// ---------- ajustes
const SFIELDS = [['kwh_price','Precio luz €/kWh'],['prep_rate','Preparación €/h'],['post_rate','Postprocesado €/h'],['waste_pct','Merma material %'],
  ['fail_pct','Riesgo de fallo %'],['margin_pct','Margen %'],['vat_pct','IVA %'],['min_price','Precio mínimo € (por pieza)'],['commission_pct','Comisión %'],['commission_fixed','Comisión fija €']];
let updTimer = null;
async function loadUpdate(){
  const u = await api('/update/status');
  $('#u-ver').textContent = u.version + (u.commit ? ` (main@${u.commit.slice(0,7)})` : ''); $('#ver').textContent = 'v'+u.version;
  $('#u-prev').textContent = u.previous ? `(anterior guardada: ${u.previous})` : '';
  $('#u-rb').classList.toggle('hidden', !u.previous);
  const st = u.status||{}, col = {ok:'pos', error:'neg', running:''}[st.state] ?? 'mut';
  $('#u-state').innerHTML = u.docker ? 'Instalación con Docker: actualiza con <code>docker compose pull && docker compose up -d</code>.' : !u.updater ? '<span class="neg">El aplicador no está instalado: actualiza una vez desde el host con <code>bash mitallercito-lxc.sh update &lt;CTID&gt;</code>.</span>'
    : u.pending ? 'Petición enviada, esperando al aplicador…'
    : st.state ? `<span class="${col}">${esc(st.message)}</span> <span class="mut">· ${esc(st.time||'')}</span>` : 'Sin actualizaciones todavía.';
  $('#u-hist').textContent = u.history.join('\n') || '—';
  $('#u-sign').innerHTML = u.signed_only ? '🔒 Solo se aceptan paquetes <b>firmados</b> por el proyecto.' : u.updater ? '⚠️ Esta instalación no tiene clave pública: acepta paquetes sin firmar.' : '';
  return u;
}
const CHAN_HELP = {releases:'Instala las versiones que se publican en GitHub (Releases). Es lo recomendado.',
  main:'Instala el último cambio subido a la rama main, sin esperar a una versión. Sin firma: solo para quien sigue el desarrollo.'};
async function setChannel(ch){ await api('/update/channel',{method:'PUT',body:{channel:ch}}); $('#u-chan-help').textContent = CHAN_HELP[ch]; checkRelease(true); }
async function checkRelease(force){
  $('#u-rel').innerHTML = '<span class="mut">Consultando GitHub…</span>';
  const r = await api('/update/check' + (force?'?force=1':''));
  $('#u-channel').value = r.channel || 'releases'; $('#u-chan-help').textContent = CHAN_HELP[r.channel||'releases'];
  if (!r.ok) return $('#u-rel').innerHTML = `<span class="mut">${esc(r.error)}${r.channel==='releases'&&/no hay versiones|no encontrado/.test(r.error)?' · Puedes usar el canal «Rama main».':''}</span>`;
  if (r.channel==='main'){
    const d = r.date ? new Date(r.date).toLocaleString(I18N.locale(),{dateStyle:'short',timeStyle:'short'}) : '';
    return $('#u-rel').innerHTML = r.blocked ? `<span class="neg">Esta instalación solo acepta versiones firmadas: el canal main no se puede instalar aquí.</span>`
      : r.newer ? `<div style="border:1px solid var(--acc);border-radius:8px;padding:10px 12px"><b>Hay cambios nuevos en main:</b> <code>${esc(r.short)}</code> · versión ${esc(r.version)} · ${d}
          <span class="mut">(tienes ${esc(r.current)}${r.current_commit?' @'+esc(r.current_commit):''})</span> · <a href="${esc(r.url)}" target="_blank" rel="noopener">ver commit</a>
          <pre style="white-space:pre-wrap;font-size:12px;max-height:120px;overflow:auto">${esc(r.notes)}</pre>
          <div class="row"><div><input type="password" id="u-pw2" placeholder="Tu contraseña" autocomplete="current-password"></div><button class="btn" onclick="installLatest()">Instalar main@${esc(r.short)}</button><div></div></div></div>`
      : `<span class="pos">Estás al día con main (${esc(r.short)}).</span> <a href="#" onclick="event.preventDefault();checkRelease(true)">comprobar de nuevo</a>`;
  }
  $('#u-rel').innerHTML = r.newer
    ? `<div style="border:1px solid var(--acc);border-radius:8px;padding:10px 12px"><b>Hay una versión nueva: ${esc(r.version)}</b> <span class="mut">(tienes ${esc(r.current)})</span> · <a href="${esc(r.url)}" target="_blank" rel="noopener">novedades</a>
       ${r.notes?`<pre style="white-space:pre-wrap;font-size:12px;max-height:160px;overflow:auto">${esc(r.notes)}</pre>`:''}
       <div class="row" style="margin-top:8px"><div><input type="password" id="u-pw2" placeholder="Tu contraseña" autocomplete="current-password"></div><button class="btn" onclick="installLatest()">Instalar ${esc(r.version)}</button><div></div></div></div>`
    : `<span class="pos">Estás en la última versión (${esc(r.current)}).</span> <a href="#" onclick="event.preventDefault();checkRelease(true)">comprobar de nuevo</a>`;
}
async function installLatest(){
  if(!$('#u-pw2').value) return toast('Pon tu contraseña');
  const r = await api('/update/install-latest',{method:'POST',body:{password:$('#u-pw2').value}}); toast(`Instalando ${r.version}…`); watchUpdate();
}
function watchUpdate(fromVersion){
  clearInterval(updTimer); let n = 0;
  updTimer = setInterval(async ()=>{
    n++; let u; try{ u = await loadUpdate(); }catch(e){ return; }   // durante el reinicio la API no responde
    if (!u.pending && u.status?.state && u.status.state!=='running'){
      clearInterval(updTimer);
      if (u.status.state==='ok'){ toast('Actualizado a '+u.version+', recargando…'); setTimeout(()=>location.reload(), 1500); }
    }
    if (n > 90) clearInterval(updTimer);
  }, 2000);
}
async function doUpdate(){
  const f = $('#u-file').files[0]; if(!f) return toast('Elige el paquete');
  if(!$('#u-pw').value) return toast('Pon tu contraseña');
  const fd = new FormData(); fd.append('file', f); fd.append('password', $('#u-pw').value);
  const r = await fetch('/api/update',{method:'POST',body:fd}), j = await r.json().catch(()=>({}));
  $('#u-pw').value='';
  if(!r.ok) return toast(j.error||'Error');
  toast(`Instalando ${j.version}…`); $('#u-file').value=''; watchUpdate();
}
async function doRollback(){
  const pw = await ask('Tu contraseña', '', {title:'Volver a la versión anterior', type:'password', ok:'Volver atrás', danger:1}); if(!pw) return;
  await api('/update/rollback',{method:'POST',body:{password:pw}}); toast('Volviendo a la anterior…'); watchUpdate();
}
function loadTelegram(){
  $('#tg-on').checked = !!S.telegram_enabled; $('#tg-token').value = S.telegram_token||''; $('#tg-chat').value = S.telegram_chat_id||'';
  $('#tg-url').value = S.public_url || location.origin; $('#tg-remind').value = S.remind_hours ?? 24;
  $('#tg-new').checked = S.notify_new!==false; $('#tg-due').checked = S.notify_due!==false; $('#tg-low').checked = S.notify_low_stock!==false; $('#tg-maint').checked = S.notify_maint!==false;
  const lim = S.status_limits_h||{};
  $('#tg-limits').innerHTML = ['presupuesto','recibido','programado','imprimiendo','postprocesado','listo'].map(s=>`<div><label><span class="tag st-${s}">${s}</span></label><input data-lim="${s}" type="number" min="0" value="${lim[s]??''}" placeholder="sin límite"></div>`).join('');
  const lr = S.notify_last_run, ago = lr ? (Date.now() - new Date(lr)) / 60000 : null;
  $('#tg-run').innerHTML = !S.telegram_enabled ? '' : lr == null ? '<span class="warn">⚠ Aún no se ha revisado ninguna vez. Si en 15 minutos sigue así, actualiza desde el host de Proxmox (crea el temporizador de avisos).</span>'
    : ago > 30 ? `<span class="warn">⚠ La última revisión fue hace ${Math.round(ago)} min: el temporizador de avisos no está funcionando.</span>`
    : `Última revisión: hace ${Math.max(0, Math.round(ago))} min.`;
}
async function saveTelegram(){
  const lim = {}; $$('#tg-limits [data-lim]').forEach(e=>{ if (e.value!=='') lim[e.dataset.lim] = +e.value; });
  S = await api('/settings',{method:'PUT',body:{telegram_enabled:$('#tg-on').checked, telegram_token:$('#tg-token').value, telegram_chat_id:$('#tg-chat').value.trim(),
    public_url:$('#tg-url').value.trim(), remind_hours:+$('#tg-remind').value||24, notify_new:$('#tg-new').checked, notify_due:$('#tg-due').checked,
    notify_low_stock:$('#tg-low').checked, notify_maint:$('#tg-maint').checked, status_limits_h:lim}});
  loadTelegram(); toast('Avisos guardados');
}
async function tgTest(){ await saveTelegram(); const r = await api('/telegram/test',{method:'POST'}); toast(r.ok ? 'Mensaje enviado: mira Telegram' : 'No se pudo: ' + r.error); }
async function tgChats(){
  await saveTelegram();
  const cs = await api('/telegram/chats');
  if (!cs.length) return toast('El bot no ha recibido mensajes: escríbele /start y vuelve a pulsar');
  if (cs.length===1){ $('#tg-chat').value = cs[0].id; toast(`Chat: ${cs[0].name}`); return saveTelegram(); }
  const cid = await choose('¿Qué chat?', cs.map(c=>({value:c.id, label:c.name}))); if (cid!=null){ $('#tg-chat').value = cid; saveTelegram(); }
}
function loadCfg(){
  if (ME.role!=='admin') return;
  loadTelegram(); loadManyfoldCfg();
  loadUsers();
  $('#b-name').value=S.shop_name||''; $('#b-tag').value=S.shop_tagline||''; $('#b-color').value=S.accent_color||'#3fae6a';
  $$('[data-b]').forEach(el=>el.value = S[el.dataset.b] ?? ''); $('#b-store').checked = !!S.store_enabled;
  [['logo','#b-logo-prev'],['favicon','#b-fav-prev']].forEach(([k,sel])=>{ $(sel).classList.toggle('hidden',!S[k]); if(S[k]) $(sel).src='/media/'+S[k]; });
  $('#s-form').innerHTML = SFIELDS.map(([k,l])=>`<div><label>${l}</label><input data-k="${k}" type="number" step="0.01" value="${S[k]}"></div>`).join('') +
    `<div><label>Tipo de venta</label><select data-k="sale_type">${opts(['B2C','B2B'],S.sale_type)}</select></div>` +
    `<div><label>Redondeo</label><select data-k="rounding">${opts(['none','0.99','0.50','1.00'],S.rounding)}</select></div>` +
    `<div><label>IVA</label><select data-k="apply_vat">${opts([[1,'Aplicar'],[0,'Sin IVA']],S.apply_vat?1:0,x=>x)}</select></div>`;
  $('#s-people').value=S.people.join(', '); $('#s-channels').value=S.channels.join(', '); $('#s-cats').value=S.expense_categories.join(', ');
  renderCrud('printers', '#pr-table', [['name','Nombre'],['watts','W medios'],['cost','Precio €'],['hours_day','Horas/día'],['amort_months','Amortizar (meses)'],['maint_month','Mant. €/mes'],['active','Activa'],['conn','Conexión'],['bridge_id','Puente'],['host','IP / nombre'],['api_key','API key']]);
  loadBridges();
  renderCrud('materials', '#mt-table', [['name','Nombre'],['kind','Tipo'],['color','Color'],['price','Precio envase €'],['qty','Cantidad'],['unit','Unidad'],['low_stock','Aviso'],['active','Activo']]);
}
async function saveBrand(){
  const d = {shop_name:$('#b-name').value.trim()||'MiTallercito', shop_tagline:$('#b-tag').value, accent_color:$('#b-color').value, store_enabled:$('#b-store').checked};
  $$('[data-b]').forEach(el=>d[el.dataset.b] = el.type==='number' ? +el.value : el.value);
  S = await api('/settings',{method:'PUT',body:d});
  for (const [k,sel] of [['logo','#b-logo-file'],['favicon','#b-fav-file']]){ const f=$(sel).files[0]; if(f){ await upload(k,f); $(sel).value=''; } }
  S = await api('/settings'); await loadBrand(); loadCfg(); toast('Marca guardada');
}
async function delUpload(k){ await api('/upload/'+k,{method:'DELETE'}); S = await api('/settings'); await loadBrand(); loadCfg(); }
async function saveSettings(){
  const d = {}; $$('#s-form [data-k]').forEach(el=>{ const k=el.dataset.k; d[k] = ['sale_type','rounding'].includes(k) ? el.value : k==='apply_vat' ? el.value==='1' : +el.value; });
  const split = s => s.split(',').map(x=>x.trim()).filter(Boolean);
  d.people = split($('#s-people').value); d.channels = split($('#s-channels').value); d.expense_categories = split($('#s-cats').value);
  S = await api('/settings',{method:'PUT',body:d}); initCalc(); toast('Ajustes guardados. Recalcula los precios del catálogo si hace falta.');
}
let BRIDGES = [];
async function loadBridges(){
  BRIDGES = await api('/bridges');
  $('#br-table').innerHTML = BRIDGES.length ? `<tr><th>Puente</th><th>Estado</th><th>Impresoras</th><th>Versión</th><th></th></tr>` + BRIDGES.map(b=>`<tr>
    <td><b>${esc(b.name)}</b></td><td>${b.online?'<span class="tag st-listo">conectado</span>':`<span class="tag st-cancelado">${b.last_seen?'desconectado':'sin estrenar'}</span>`}
      ${b.last_seen?`<div class="mut" style="font-size:11px">${new Date(b.last_seen*1000).toLocaleString(I18N.locale())} · ${esc(b.last_ip)}</div>`:''}</td>
    <td style="font-size:13px">${b.printers.map(esc).join(', ')||'<span class="mut">ninguna</span>'}</td><td class="mut">${esc(b.version||'')}</td>
    <td style="text-align:right"><button class="btn sec sm" onclick="delBridge(${b.id})">✕</button></td></tr>`).join('') : '<tr><td class="mut">Sin puentes.</td></tr>';
}
async function addBridge(){
  const b = await api('/bridges',{method:'POST',body:{name:$('#br-name').value}}); $('#br-name').value='';
  const repo = (await api('/update/status')).repo || 'Oda615/MiTallercito';
  const cmd = `curl -fsSL https://raw.githubusercontent.com/${repo}/main/bridge/install-bridge.sh | sudo bash -s -- --url ${location.origin} --token ${b.token}`;
  $('#br-new').innerHTML = `<div style="border:1px solid var(--acc);border-radius:8px;padding:12px"><b>Puente «${esc(b.name)}» creado.</b> Copia ahora el token: no se vuelve a mostrar.
    <p style="margin:8px 0 4px">En el equipo de la red de las impresoras (Debian/Ubuntu/Raspberry Pi OS):</p>
    <pre style="white-space:pre-wrap;word-break:break-all;background:var(--bg);padding:8px;border-radius:6px;font-size:12px">${esc(cmd)}</pre>
    <button class="btn sec sm" onclick="navigator.clipboard.writeText(${esc(JSON.stringify(cmd))}).then(()=>toast('Copiado'))">Copiar comando</button>
    <p class="mut" style="font-size:12px;margin:8px 0 0">${location.protocol==='http:'?'⚠️ Estás entrando por http: el puente necesita llegar a esta URL; lo ideal es tu subdominio con https. ':''}Luego asigna impresoras a este puente en la tabla de Impresoras.</p></div>`;
  $('#br-new').classList.remove('hidden'); loadBridges(); loadCfg();
}
async function delBridge(id){ if (!await sure('¿Borrar el puente? Sus impresoras se quedarán sin conexión.', {ok:'Borrar', danger:1})) return; await api('/bridges/'+id,{method:'DELETE'}); loadBridges(); loadCfg(); }
async function renderCrud(table, sel, cols){
  if (table==='printers') BRIDGES = await api('/bridges').catch(()=>[]);
  const data = await api('/'+table);
  if (table==='printers') PRINTERS=data; else MATS=data;
  const cell = (c,v) => c==='conn' ? `<select data-c="conn">${opts([['','Ninguna'],['moonraker','Moonraker / Klipper'],['octoprint','OctoPrint'],['prusalink','PrusaLink'],['bridge','Puente (Moonraker)']],v,x=>x)}</select>`
    : c==='bridge_id' ? `<select data-c="bridge_id">${opts([['','—'], ...BRIDGES.map(b=>[b.id,b.name])],v??'',x=>x)}</select>`
    : c==='host' ? `<input data-c="host" value="${esc(v)}" placeholder="192.168.1.40" style="min-width:130px">`
    : c==='api_key' ? `<input data-c="api_key" type="password" autocomplete="off" value="${esc(v)}" placeholder="(opcional)" title="API key. En PrusaLink también vale usuario:contraseña (maker:…)" style="min-width:90px">`
    : c==='active' ? `<select data-c="${c}">${opts([[1,'Sí'],[0,'No']],v,x=>x)}</select>` : c==='unit' ? `<select data-c="${c}">${opts(['g','ml'],v)}</select>` : `<input data-c="${c}" value="${esc(v)}" ${['name','kind','color'].includes(c)?'':'type="number" step="0.01"'}>`;
  const blank = {active:1, unit:'g'};
  $(sel).innerHTML = `<tr>${cols.map(c=>`<th>${c[1]}</th>`).join('')}<th></th></tr>` +
    [...data, blank].map(r=>`<tr data-id="${r.id||''}">${cols.map(([c])=>`<td>${cell(c, r[c]??'')}</td>`).join('')}
      <td style="white-space:nowrap"><button class="btn sm ${r.id?'sec':''}" onclick="saveCrud('${table}',this)">${r.id?'Guardar':'Añadir'}</button>${table==='printers'&&r.id&&r.conn?` <button class="btn sec sm" onclick="testPrinter(${r.id},this)">Probar</button>`:''}${r.id?` <button class="btn sec sm" onclick="delCrud('${table}',${r.id})">✕</button>`:''}</td></tr>`).join('');
}
async function saveCrud(table, btn){
  const tr = btn.closest('tr'), d = {};
  tr.querySelectorAll('[data-c]').forEach(el=>d[el.dataset.c] = el.type==='number' || el.dataset.c==='active' ? +el.value : el.value);
  if (table==='printers' && d.conn && !d.host) return toast('Pon la IP o el nombre de la impresora');
  if (table==='printers' && d.conn==='bridge' && !d.bridge_id) return toast('Elige el puente de esa impresora');
  if (tr.dataset.id) await api(`/${table}/${tr.dataset.id}`,{method:'PUT',body:d}); else await api('/'+table,{method:'POST',body:d});
  toast('Guardado'); loadCfg(); setTimeout(initCalc, 300);
}
async function delCrud(table, id){ if (await sure('¿Borrar?', {ok:'Borrar', danger:1})){ await api(`/${table}/${id}`,{method:'DELETE'}); loadCfg(); } }

boot().catch(()=>{});


// ---------- mantenimiento de impresoras
let MAINT = [], MPROF = [], curTask = null;
const every = t => [t.every_h?`${t.every_h} h`:'', t.every_prints?`${t.every_prints} impresiones`:'', t.every_days?`${t.every_days} días`:''].filter(Boolean).join(' · ');
async function loadMaint(sync=true){
  [MAINT, MPROF] = await Promise.all([api('/maintenance' + (sync?'':'?sync=0')), MPROF.length ? MPROF : api('/maint-profiles')]);
  const adm = ME.role==='admin';
  $('#mt-wrap').innerHTML = MAINT.map(m=>{
    const prof = MPROF.find(p=>p.key===m.model);
    const src = m.mode==='moonraker' ? 'horas de Moonraker' : 'horas de pedidos y fallos';
    return `<div class="card"><div class="row" style="align-items:center"><h2 style="margin:0">${esc(m.name)}</h2><div></div>
      <span class="mut" style="font-size:13px;flex:0 0 auto"><b>${(m.hours_total||0).toLocaleString(I18N.locale(),{maximumFractionDigits:1})} h</b> · ${m.prints_total} impresiones</span></div>
      <div class="mut" style="font-size:12px;margin:2px 0 8px">${prof?esc(prof.name)+' · ':''}${src}</div>
      ${m.tasks.length ? m.tasks.map(t=>{
        const since = [t.every_h?`${(t.hours_since||0).toLocaleString(I18N.locale(),{maximumFractionDigits:1})} h`:'', t.every_prints?`${t.prints_since} impresiones`:'', t.every_days&&t.days_since!=null?`${t.days_since} d`:''].filter(Boolean).join(' · ');
        return `<div class="mt-row"><div><b>${esc(t.name)}</b><div class="mut" style="font-size:12px"><span>cada ${every(t)}</span>${t.notes?` — <span>${esc(t.notes)}</span>`:''}</div></div>
          <div style="font-size:12px"><span class="${t.state==='toca'?'neg':''}">${since}</span><div class="bar"><i class="mt-${t.state}" style="width:${Math.min(100,t.pct)}%"></i></div></div>
          <div style="white-space:nowrap"><button class="btn ${t.state==='ok'?'sec':''} sm" onclick="taskDone(${t.id})">Hecho</button>${adm?` <button class="btn sec sm" onclick="editTask(${m.id},${t.id})">✎</button>`:''}</div></div>`;
      }).join('') : '<p class="mut" style="font-size:13px">Sin tareas. Elige el modelo de la impresora para cargar las recomendadas por el fabricante.</p>'}
      ${adm?`<div class="row" style="margin-top:12px;align-items:end;gap:8px">
        <div style="flex:2"><label>Modelo (perfil)</label><select id="mp-${m.id}">${opts([['','—'], ...MPROF.map(p=>[p.key,p.name])], m.model, x=>x)}</select></div>
        <button class="btn sec sm" style="flex:0 0 auto" onclick="applyProfile(${m.id})">Cargar tareas</button></div>
      <div class="row" style="margin-top:8px;gap:8px;flex-wrap:wrap">
        <button class="btn sec sm" onclick="editTask(${m.id})">+ Tarea</button>
        <button class="btn sec sm" onclick="adjustHours(${m.id})">Sumar horas</button>
        <button class="btn sec sm" onclick="maintLog(${m.id})">Historial</button>
        ${['moonraker','bridge'].includes(m.conn)?`<select style="max-width:230px" onchange="setHoursSource(${m.id},this.value)">${opts([['auto','Horas: Moonraker'],['app','Horas: pedidos y fallos']], m.hours_source, x=>x)}</select>`:''}</div>`:''}
    </div>`;
  }).join('') || '<p class="mut">Añade tus impresoras en Ajustes.</p>';
}
async function taskDone(tid){
  const note = await ask('¿Alguna nota? (opcional)', '', {title:'Tarea hecha', placeholder:'qué has cambiado, qué grasa…', ok:'Marcar hecha'}); if (note===null) return;
  await api(`/maint/tasks/${tid}/done`,{method:'POST',body:{note}}); toast('Apuntado'); loadMaint(false);
}
async function applyProfile(pid){
  const key = $('#mp-'+pid).value; if (!key) return toast('Elige el modelo');
  const m = MAINT.find(x=>x.id===pid);
  const fl = [{k:'when', type:'date', label:'¿Cuándo le hiciste mantenimiento por última vez?', hint:'Vacío = hoy.'}];
  if (m.tasks.length) fl.push({k:'replace', type:'checkbox', label:'Sustituir las tareas que ya tiene', hint:'Sin marcar: solo se añaden las que falten.'});
  const f = await form('Cargar tareas de mantenimiento', fl, {ok:'Cargar'}); if (!f) return;
  await api(`/printers/${pid}/maint`,{method:'PUT',body:{profile:key, replace:!!f.replace, last_done: f.when ? f.when+'T00:00:00' : ''}});
  toast('Tareas cargadas'); loadMaint(false);
}
async function setHoursSource(pid, v){ await api(`/printers/${pid}/maint`,{method:'PUT',body:{hours_source:v}}); loadMaint(false); }
async function adjustHours(pid){
  const f = await form('Sumar horas', [
    {k:'hours', label:'Horas a sumar', type:'number', req:1, hint:'Lo que ya llevaba la impresora antes de usar MiTallercito, o impresiones sin pedido. Negativo para restar.'},
    {k:'note', label:'Nota (opcional)'}], {ok:'Sumar'}); if (!f) return;
  await api(`/printers/${pid}/maint/adjust`,{method:'POST',body:f}); loadMaint(false);
}
async function maintLog(pid){
  const m = MAINT.find(x=>x.id===pid), log = await api(`/printers/${pid}/maint/log`);
  $('#pr-hist').classList.remove('hidden');
  $('#pr-hist').innerHTML = `<h2>Mantenimiento de ${esc(m.name)}</h2>` + (log.length ? `<table><tr><th>Fecha</th><th>Qué</th><th class="n">Horas</th><th>Quién</th></tr>` +
    log.map(l=>`<tr><td>${l.at.slice(0,10)}</td><td>${l.kind==='ajuste'?'<span class="mut">Horas sumadas a mano</span>':esc(l.task_name)}${l.note?`<br><span class="mut" style="font-size:12px">${esc(l.note)}</span>`:''}</td>
      <td class="n">${l.kind==='ajuste'?'+':''}${(l.hours||0).toLocaleString(I18N.locale(),{maximumFractionDigits:1})} h</td><td>${esc(l.user||'')}</td></tr>`).join('') + '</table>' : '<p class="mut">Nada apuntado todavía.</p>');
  $('#pr-hist').scrollIntoView({behavior:'smooth'});
}
const mdlg = $('#mdlg');
function editTask(pid, tid=null){
  const m = MAINT.find(x=>x.id===pid); curTask = {pid, ...(tid ? m.tasks.find(t=>t.id===tid) : {})};
  $('#mt-title').textContent = tid ? 'Tarea de mantenimiento' : `Nueva tarea · ${m.name}`;
  $('#mt-name').value = curTask.name||''; $('#mt-h').value = curTask.every_h||''; $('#mt-n').value = curTask.every_prints||''; $('#mt-d').value = curTask.every_days||'';
  $('#mt-last').value = (curTask.last_done||new Date().toISOString()).slice(0,10); $('#mt-notes').value = curTask.notes||'';
  $('#mt-del').classList.toggle('hidden', !tid); mdlg.showModal();
}
async function saveTask(){
  const body = {name:$('#mt-name').value, every_h:$('#mt-h').value, every_prints:$('#mt-n').value, every_days:$('#mt-d').value,
    notes:$('#mt-notes').value, last_done:$('#mt-last').value ? $('#mt-last').value+'T00:00:00' : undefined};
  if (curTask.id) await api(`/maint/tasks/${curTask.id}`,{method:'PUT',body}); else await api(`/printers/${curTask.pid}/maint/tasks`,{method:'POST',body});
  mdlg.close(); loadMaint(false);
}
async function delTask(){ if (!await sure('¿Borrar esta tarea?', {ok:'Borrar', danger:1})) return; await api(`/maint/tasks/${curTask.id}`,{method:'DELETE'}); mdlg.close(); loadMaint(false); }

// ---------- clientes
let CLIENTS = [], curClient = null;
async function loadClientList(){ CLIENTS = await api('/clients').catch(()=>[]); $('#cl-list').innerHTML = CLIENTS.map(c=>`<option value="${esc(c.name)}">`).join(''); return CLIENTS; }
async function loadClients(){ await loadClientList(); renderClients(); }
function renderClients(){
  const q = ($('#cl-q').value||'').toLowerCase(), cs = CLIENTS.filter(c=>!q || [c.name,c.phone,c.email].join(' ').toLowerCase().includes(q));
  $('#cl-table').innerHTML = cs.length ? `<tr><th>Cliente</th><th>Contacto</th><th class="n">Pedidos</th><th class="n">Gastado</th><th class="n">Debe</th><th>Último</th></tr>` +
    cs.map(c=>`<tr style="cursor:pointer" onclick="openClient(${c.id})"><td><b>${esc(c.name)}</b></td><td style="font-size:13px">${esc([c.phone,c.email].filter(Boolean).join(' · '))}</td>
      <td class="n">${c.orders}</td><td class="n">${eur(c.spent)}</td><td class="n ${c.owed>0?'neg':''}">${c.owed>0?eur(c.owed):'–'}</td><td class="mut">${esc(c.last||'')}</td></tr>`).join('')
    : `<tr><td class="mut">${CLIENTS.length?'Nadie coincide con la búsqueda.':'Aún no hay clientes.'}</td></tr>`;
}
const cdlg = $('#cdlg');
async function openClient(id=null){
  curClient = id ? await api('/clients/'+id) : {name:'', phone:'', email:'', address:'', notes:'', history:[]};
  $('#cl-title').textContent = id ? curClient.name : 'Nuevo cliente';
  ['name','phone','email','address','notes'].forEach(k=>$('#cl-'+k).value = curClient[k]||'');
  $('#cl-stats').innerHTML = id ? [[curClient.orders,'pedidos'],[eur(curClient.spent),'gastado'],[eur(curClient.owed),'pendiente de cobro', curClient.owed>0?'neg':''],[curClient.last||'–','último pedido']]
    .map(([v,l,cl])=>`<div class="kpi"><div class="v ${cl||''}" style="font-size:20px">${v}</div><div class="l">${l}</div></div>`).join('') : '';
  $('#cl-hist').innerHTML = curClient.history.length ? `<tr><th>#</th><th>Fecha</th><th>Qué</th><th>Estado</th><th class="n">Total</th></tr>` + curClient.history.map(o=>`<tr style="cursor:pointer" onclick="cdlg.close();openOrder(${o.id})">
    <td>${o.id}</td><td class="mut">${o.created.slice(0,10)}</td><td style="font-size:13px">${esc(o.items.map(i=>`${i.qty}× ${i.description}`).join(', '))}</td>
    <td><span class="tag st-${o.status}">${o.status}</span>${o.paid?'':' <span class="neg" style="font-size:12px">sin cobrar</span>'}</td><td class="n">${eur(o.total)}</td></tr>`).join('') : '<tr><td class="mut">Sin pedidos.</td></tr>';
  $('#cl-del').classList.toggle('hidden', !id); $('#cl-new').classList.toggle('hidden', !id); $('#cl-rep').classList.toggle('hidden', !curClient.last_order_id);
  cdlg.showModal();
}
async function saveClient(){
  const body = {}; ['name','phone','email','address','notes'].forEach(k=>body[k] = $('#cl-'+k).value);
  if (!body.name.trim()) return toast('Falta el nombre');
  curClient.id ? await api('/clients/'+curClient.id,{method:'PUT',body}) : await api('/clients',{method:'POST',body});
  cdlg.close(); toast('Guardado'); loadClients();
}
async function delClient(){ if (!await sure('¿Borrar la ficha? Los pedidos se quedan, pero sin enlazar.', {ok:'Borrar', danger:1})) return; await api('/clients/'+curClient.id,{method:'DELETE'}); cdlg.close(); loadClients(); }
async function clientNewOrder(){ const c = curClient; cdlg.close(); await openOrder();
  $('#d-client').value = c.name; $('#d-contact').value = c.phone||''; $('#d-email').value = c.email||''; $('#d-address').value = c.address||''; }
async function clientRepeat(){ cdlg.close(); curOrder = {id: curClient.last_order_id}; await repeatOrder(); }

// ---------- venta en puestos
const POS = {ev: null, cart: [], pay: 'efectivo', events: []};
const PAYS = [['efectivo','Efectivo'],['tarjeta','Tarjeta'],['bizum','Bizum'],['transferencia','Transferencia'],['otro','Otro']];
const sprice = p => p.public_price!=null && p.public_price!=='' ? +p.public_price : +p.unit_price;
async function loadPos(){
  [POS.events, PRODUCTS] = await Promise.all([api('/events'), api('/products')]);
  const open = POS.events.filter(e=>e.status==='abierto');
  if (POS.ev && !POS.events.find(e=>e.id===POS.ev)) POS.ev = null;
  if (POS.ev==null && open.length) POS.ev = open[0].id;
  $('#pos-ev').innerHTML = `<option value="">Sin puesto (venta suelta en mano)</option>` + POS.events.map(e=>`<option value="${e.id}" ${e.id===POS.ev?'selected':''}>${e.status==='cerrado'?'🔒 ':'🏪 '}${esc(e.name)} · ${esc(e.date||'')}</option>`).join('');
  $('#pos-who').innerHTML = opts(S.people, S.people.includes(ME.user) ? ME.user : S.people[0]);
  $('#pos-pay').innerHTML = PAYS.map(([k,l])=>`<button data-k="${k}" class="${k===POS.pay?'on':''}" onclick="POS.pay='${k}';$$('#pos-pay button').forEach(b=>b.classList.toggle('on',b.dataset.k==='${k}'))">${l}</button>`).join('');
  posProducts(); posCart(); posEvent(true);
}
async function posEvent(keep){
  if (!keep) POS.ev = +$('#pos-ev').value || null;
  $('#pos-edit').classList.toggle('hidden', !POS.ev);
  if (!POS.ev){ $('#pos-sum').innerHTML = '<h2>Venta suelta</h2><p class="mut" style="font-size:13px">Crea un puesto (mercadillo, feria, quedada…) para ver la caja, lo vendido y lo que te ha costado.</p>'; $('#pos-take').innerHTML = '<p class="mut" style="font-size:13px">Elige un puesto.</p>';
    const all = await api('/orders?source=puesto').catch(()=>[]); return posSalesTable(all.filter(o=>!o.event_id).slice(0,30).map(o=>({id:o.id, created:o.created, client:o.client, pay_method:o.pay_method, total:o.total, what:o.items.map(i=>`${i.qty}× ${i.description}`).join(', ')}))); }
  const e = await api('/events/'+POS.ev); POS.cur = e;
  const diff = e.cash_end!=null ? e.cash_end - e.cash_expected : null;
  $('#pos-sum').innerHTML = `<div class="row" style="align-items:center"><h2 style="margin:0">${esc(e.name)}</h2><div></div><span class="tag ${e.status==='abierto'?'st-listo':'st-entregado'}" style="flex:0 0 auto">${e.status}</span></div>
    <div class="mut" style="font-size:13px;margin:4px 0 10px">${esc(e.date||'')}${e.place?' · '+esc(e.place):''}</div>
    <div class="grid g3" style="gap:10px">${[[eur(e.total),`${e.count} venta(s)`],[eur(e.profit),'beneficio', e.profit>=0?'pos':'neg'],[eur(e.cash_expected),'debería haber en caja']]
      .map(([v,l,c])=>`<div class="kpi"><div class="v ${c||''}" style="font-size:20px">${v}</div><div class="l">${l}</div></div>`).join('')}</div>
    <div style="font-size:13px;margin-top:10px">${Object.entries(e.by_method).map(([k,v])=>`${(PAYS.find(p=>p[0]===k)||[k,k])[1]} <b>${eur(v)}</b>`).join(' · ')||'<span class="mut">Sin ventas todavía.</span>'}</div>
    <div class="mut" style="font-size:12px;margin-top:4px">Coste de lo vendido ${eur(e.goods_cost)} · puesto ${eur(e.stand_cost)} · cambio inicial ${eur(e.cash_start)}</div>
    ${diff!=null?`<div style="margin-top:8px;font-size:13px">Caja contada: <b>${eur(e.cash_end)}</b> ${Math.abs(diff)<0.005?'✓ cuadra':`<span class="neg">(${diff>0?'sobran':'faltan'} ${eur(Math.abs(diff))})</span>`}</div>`:''}
    <div style="margin-top:10px">${e.status==='abierto'?`<button class="btn sec sm" onclick="closeEvent()">Cerrar puesto y contar caja</button>`:`<button class="btn sec sm" onclick="reopenEvent()">Reabrir</button>`}</div>`;
  $('#pos-take').innerHTML = `<table><tr><th>Producto</th><th style="width:90px">Llevas</th><th class="n">Vendidas</th><th class="n">Vuelven</th></tr>` +
    PRODUCTS.map(p=>{ const t = e.taken.find(x=>x.product_id===p.id) || {qty:'', sold:(e.items_sold.find(x=>x.product_id===p.id)||{}).qty||0, left:''};
      return `<tr><td>${esc(p.name)}${p.stock!=null?` <span class="mut" style="font-size:12px">(stock ${p.stock})</span>`:''}</td><td><input class="tk" data-p="${p.id}" type="number" min="0" value="${t.qty}"></td><td class="n">${t.sold||'–'}</td><td class="n">${t.left!==''?`<b>${t.left}</b>`:'–'}</td></tr>`; }).join('') + '</table>';
  posSalesTable(e.sales); posProducts();
}
function posSalesTable(sales){
  $('#pos-sales').innerHTML = sales.length ? `<tr><th>Hora</th><th>Qué</th><th>Pago</th><th>Cliente</th><th class="n">Total</th><th></th></tr>` + sales.map(s=>`<tr><td class="mut">${s.created.slice(11,16)}</td><td style="font-size:13px">${esc(s.what)}</td>
    <td>${esc((PAYS.find(p=>p[0]===s.pay_method)||['',s.pay_method||''])[1])}</td><td style="font-size:13px">${esc(s.client)}</td><td class="n"><b>${eur(s.total)}</b></td><td><button class="btn sec sm" onclick="undoSale(${s.id})">Deshacer</button></td></tr>`).join('')
    : '<tr><td class="mut">Sin ventas.</td></tr>';
}
function posLeft(p){
  if ((p.variants||[]).length){ const t = p.variants.filter(v=>v.stock!=null); return t.length ? t.reduce((a,v)=>a+posVLeft(p, v),0) : null; }
  const inCart = POS.cart.filter(c=>c.product_id===p.id).reduce((a,c)=>a+c.qty,0);
  return p.stock==null ? null : p.stock - inCart;
}
function posVLeft(p, v){ const inCart = POS.cart.filter(c=>c.product_id===p.id && c.variant_id===v.id).reduce((a,c)=>a+c.qty,0); return v.stock==null ? null : v.stock - inCart; }
function posProducts(){
  const q = ($('#pos-q').value||'').toLowerCase();
  $('#pos-prods').innerHTML = PRODUCTS.filter(p=>!q || p.name.toLowerCase().includes(q) || (p.category||'').toLowerCase().includes(q)).map(p=>{ const left = posLeft(p);
    return `<button onclick="posAdd(${p.id})" ${left!=null&&left<=0?'disabled':''}>${p.image?`<img src="/media/${esc(p.image)}" alt="">`:''}<span>${esc(p.name)}</span><span class="pr">${eur(sprice(p))}</span><span class="st">${(p.variants||[]).length?`${p.variants.length} variantes · `:''}${left==null?'bajo pedido':`quedan ${left}`}</span></button>`; }).join('')
    || '<p class="mut" style="font-size:13px">No hay productos en el catálogo. Guárdalos desde la calculadora.</p>';
}
async function posAdd(pid){
  const p = PRODUCTS.find(x=>x.id===pid), pv = await pickVariant(p, true, true); if (!pv) return; const v = pv.variant;
  const c = POS.cart.find(x=>x.product_id===pid && (x.variant_id||null)===(v?.id||null));
  if (c) c.qty++; else POS.cart.push({product_id:pid, variant_id:v?.id||null, description:p.name + (v?` (${v.name})`:''), qty:1, unit_price:vPrice(p, v, true)});
  posCart(); posProducts();
}
async function posFree(){
  const f = await form('Venta libre', [{k:'d', label:'¿Qué es?', value:'Varios', req:1}, {k:'pr', label:'Precio (€)', type:'number', req:1}, {k:'q', label:'Cantidad', type:'number', value:'1'}], {ok:'Añadir'}); if (!f) return;
  POS.cart.push({description:f.d, qty:Math.max(1, Math.round(+f.q||1)), unit_price:+f.pr||0}); posCart();
}
function posQty(i, dq){ POS.cart[i].qty += dq; if (POS.cart[i].qty<=0) POS.cart.splice(i,1); posCart(); posProducts(); }
let posOfferTimer = null;
function posCart(){
  const tot = POS.cart.reduce((a,c)=>a+c.qty*c.unit_price,0) - (POS.disc||[]).reduce((a,d)=>a+d.amount,0);
  $('#pos-cart').innerHTML = POS.cart.length ? POS.cart.map((c,i)=>`<tr><td>${esc(c.description)}</td><td class="n" style="white-space:nowrap"><span class="q"><button class="btn sec sm" onclick="posQty(${i},-1)">−</button><b>${c.qty}</b><button class="btn sec sm" onclick="posQty(${i},1)">+</button></span></td>
    <td class="n" style="white-space:nowrap;font-size:12px" class="mut"><input type="number" step="0.01" value="${c.unit_price}" title="Precio por unidad" style="width:64px;padding:6px" onchange="POS.cart[${i}].unit_price=+this.value||0;posCart()"><span class="pu"> €/ud</span></td><td class="n"><b>${eur(c.qty*c.unit_price)}</b></td></tr>`).join('')
    : '<tr><td class="mut">Toca los productos para añadirlos.</td></tr>';
  if (POS.cart.length) $('#pos-cart').innerHTML += (POS.disc||[]).map(d=>`<tr class="offer"><td colspan="3">🏷 <span>${esc(d.name)}</span></td><td class="n"><b>−${eur(d.amount)}</b></td></tr>`).join('');
  clearTimeout(posOfferTimer);
  posOfferTimer = setTimeout(async ()=>{ const key = JSON.stringify(POS.cart.map(c=>[c.product_id,c.qty,c.unit_price]));
    if (key===POS.discKey) return; POS.discKey = key;
    const r = POS.cart.length ? await api('/offers/preview',{method:'POST',body:{items:POS.cart, where:'puesto'}}).catch(()=>({discounts:[]})) : {discounts:[]};
    POS.disc = r.discounts; posCart(); }, 250);
  $('#pos-go').textContent = tot ? `Cobrar ${eur(tot)}` : 'Cobrar'; $('#pos-go').disabled = !POS.cart.length;
  const n = POS.cart.reduce((a,c)=>a+c.qty,0);
  $('#pos-bar').classList.toggle('on', !!POS.cart.length && !$('#v-pos').classList.contains('hidden'));
  $('#pos-bar').innerHTML = `<span>🛒 ${n}</span><span>Cobrar ${eur(tot)} ↓</span>`;
}
async function posCharge(){
  if (!POS.cart.length) return;
  const name = $('#pos-client').value.trim(), c = CLIENTS.find(x=>x.name.toLowerCase()===name.toLowerCase());
  const s = await api('/sales',{method:'POST',body:{event_id:POS.ev, items:POS.cart, pay_method:POS.pay, paid_to:$('#pos-who').value, client:name, client_id:c?c.id:null}});
  toast(`Vendido: ${eur(s.total)}`); POS.cart = []; POS.disc = []; POS.discKey = ''; $('#pos-client').value=''; PRODUCTS = await api('/products'); posCart(); posProducts(); posEvent(true); if (name) loadClientList();
}
async function undoSale(id){ if (!await sure('¿Deshacer esta venta? Lo vendido vuelve al stock.', {ok:'Deshacer', danger:1})) return; await api('/orders/'+id,{method:'DELETE'}); PRODUCTS = await api('/products'); posEvent(true); posProducts(); }
async function newEvent(){
  const f = await form('Nuevo puesto', [
    {k:'name', label:'Nombre', placeholder:'p. ej. Mercadillo medieval de Toledo', req:1},
    {k:'place', label:'Lugar (opcional)'},
    {k:'stand_cost', label:'Coste del puesto (€)', type:'number', value:'0', half:1},
    {k:'cash_start', label:'Cambio inicial en caja (€)', type:'number', value:'0', half:1}], {ok:'Abrir puesto'}); if (!f) return;
  const e = await api('/events',{method:'POST',body:f});
  POS.ev = e.id; loadPos();
}
async function editEvent(){
  const e = POS.cur;
  const f = await form('Editar puesto', [
    {k:'name', label:'Nombre', value:e.name, req:1}, {k:'place', label:'Lugar', value:e.place||''},
    {k:'date', label:'Fecha', type:'date', value:e.date||''},
    {k:'stand_cost', label:'Coste del puesto (€)', type:'number', value:e.stand_cost, half:1},
    {k:'cash_start', label:'Cambio inicial (€)', type:'number', value:e.cash_start, half:1}], {ok:'Guardar'}); if (!f) return;
  await api('/events/'+e.id,{method:'PUT',body:f}); loadPos();
}
async function closeEvent(){
  const e = POS.cur, n = await ask('¿Cuánto efectivo hay? (€)', String(e.cash_expected), {title:'Cerrar puesto', type:'number', hint:`Cuenta la caja. Debería haber ${eur(e.cash_expected)}.`, ok:'Cerrar puesto'}); if (n===null) return;
  await api('/events/'+e.id,{method:'PUT',body:{status:'cerrado', cash_end:n.replace(',','.')}}); toast('Puesto cerrado'); loadPos();
}
async function reopenEvent(){ await api('/events/'+POS.cur.id,{method:'PUT',body:{status:'abierto'}}); loadPos(); }
async function saveTake(){
  if (!POS.ev) return toast('Elige un puesto');
  await api(`/events/${POS.ev}/stock`,{method:'PUT',body:{items:$$('#pos-take .tk').map(i=>({product_id:+i.dataset.p, qty:+i.value||0}))}}); toast('Guardado'); posEvent(true);
}


// ---------- elegir una opción (variantes…)
const chdlg = $('#chdlg');
// ---------- diálogos propios (sustituyen a prompt/confirm/alert)
// fields: [{k,label,type:text|number|date|month|select|textarea|color|checkbox|password,value,placeholder,options:[[v,l]],hint,step,min,max,req}]
function form(title, fields=[], o={}){
  return new Promise(res=>{
    const d = $('#uidlg'), f = $('#ui-form');
    $('#ui-title').textContent = title || '';
    $('#ui-msg').innerHTML = o.html || (o.msg ? esc(o.msg).replace(/\n/g,'<br>') : '');
    $('#ui-msg').classList.toggle('hidden', !(o.html||o.msg));
    $('#ui-fields').innerHTML = fields.map((x,i)=>{
      const id = 'uif'+i, v = x.value==null ? '' : x.value, ph = x.placeholder ? ` placeholder="${esc(x.placeholder)}"` : '';
      const at = `id="${id}" data-k="${esc(x.k)}"${x.req?' required':''}${x.list?` list="${x.list}"`:''}${x.step?` step="${x.step}"`:''}${x.min!=null?` min="${x.min}"`:''}${x.max!=null?` max="${x.max}"`:''}${ph}`;
      let inp;
      if (x.type==='select') inp = `<select ${at}>${(x.options||[]).map(([ov,ol])=>`<option value="${esc(ov)}"${String(ov)===String(v)?' selected':''}>${esc(ol)}</option>`).join('')}</select>`;
      else if (x.type==='textarea') inp = `<textarea ${at}>${esc(v)}</textarea>`;
      else if (x.type==='checkbox') return `<label class="switch ui-chk"><input type="checkbox" ${at}${v?' checked':''}> ${esc(x.label)}</label>${x.hint?`<div class="hint">${esc(x.hint)}</div>`:''}`;
      else inp = `<input type="${x.type==='number'?'text" inputmode="decimal':x.type||'text'}" ${at} value="${esc(v)}">`;
      return `<div class="ui-f${x.half?' half':''}"><label for="${id}">${esc(x.label||'')}</label>${inp}${x.hint?`<div class="hint">${esc(x.hint)}</div>`:''}</div>`;
    }).join('');
    $('#ui-fields').classList.toggle('hidden', !fields.length);
    const ok = $('#ui-ok'); ok.textContent = o.ok || 'Aceptar'; ok.classList.toggle('bad', !!o.danger);
    const cancel = $('#ui-cancel'); cancel.textContent = o.cancel || 'Cancelar'; cancel.classList.toggle('hidden', !!o.noCancel);
    const ex = $('#ui-extra'); ex.textContent = o.extra || ''; ex.classList.toggle('hidden', !o.extra);
    let done = false;
    const finish = val => { if (done) return; done = true; d.close(); res(val); };
    cancel.onclick = () => finish(null);
    ex.onclick = () => finish({__extra:true});
    f.onsubmit = e => { e.preventDefault();
      const out = {};
      $$('#ui-fields [data-k]').forEach(el=>{ out[el.dataset.k] = el.type==='checkbox' ? el.checked : el.value.trim(); });
      fields.forEach(x=>{ if (x.type==='number' && out[x.k]!=='') out[x.k] = out[x.k].replace(',','.'); });
      finish(out); };
    d.onclose = () => finish(null);
    d.showModal();
    const first = $('#ui-fields input:not([type=checkbox]),#ui-fields select,#ui-fields textarea');
    if (first && !o.danger) { first.focus(); first.select?.(); } else ok.focus();
  });
}
async function ask(msg, def='', o={}){ const r = await form(o.title||'', [{k:'v', label:msg, value:def, type:o.type, placeholder:o.placeholder, hint:o.hint}], o); return r ? r.v : null; }
async function sure(msg, o={}){ return !!(await form(o.title||'', [], {msg, ok:o.ok||'Sí', danger:o.danger, html:o.html})); }
async function tell(msg, o={}){ await form(o.title||'', [], {msg, html:o.html, ok:'Vale', noCancel:true}); }
const num = v => v==null || v==='' ? null : +String(v).replace(',','.');

function choose(title, options){
  return new Promise(res=>{
    $('#ch-title').textContent = title;
    $('#ch-opts').innerHTML = options.map((o,i)=>`<button data-i="${i}" ${o.disabled?'disabled':''}><span>${o.hex?`<i class="sw" style="background:${esc(o.hex)}"></i>`:''}${esc(o.label)}</span><span class="mut" style="font-size:13px">${esc(o.sub||'')}</span></button>`).join('');
    let done = false;
    $('#ch-opts').onclick = e => { const b = e.target.closest('button'); if (!b) return; done = true; chdlg.close(); res(options[+b.dataset.i].value); };
    chdlg.onclose = () => { if (!done) res(null); };
    chdlg.showModal();
  });
}
const vPrice = (p, v, pub) => v && v.price!=null ? +v.price : (pub ? sprice(p) : +p.unit_price);
async function pickVariant(p, pub, needStock){
  if (!(p.variants||[]).length) return {variant:null};
  const left = v => needStock ? posVLeft(p, v) : v.stock;
  const v = await choose(p.name, p.variants.map(v=>({value:v, label:v.name, hex:v.color_hex,
    sub:`${eur(vPrice(p, v, pub))}${left(v)==null?'':' · quedan '+left(v)}`, disabled: needStock && left(v)!=null && left(v)<=0})));
  return v ? {variant:v} : null;
}

// ---------- variantes en la ficha del producto
let PV = [];
function pvRender(){
  const mopt = sel => '<option value="">— el del producto —</option>' + MATS.filter(m=>m.active).map(m=>`<option value="${m.id}" ${m.id==sel?'selected':''}>${esc(m.name)}</option>`).join('');
  $('#pv-table').innerHTML = PV.length ? `<tr><th>Variante</th><th style="width:50px">Color</th><th style="width:90px">Precio €</th><th style="width:80px">Stock</th><th>Material</th><th></th></tr>` +
    PV.map((v,i)=>`<tr data-v="${i}"><td><input class="pv-n" value="${esc(v.name)}" placeholder="Rojo, M, 10 cm…"></td><td><input class="pv-c" type="color" value="${esc(v.color_hex||'#888888')}"></td>
      <td><input class="pv-p" type="number" step="0.01" value="${v.price??''}" placeholder="${sprice(curProd)}"></td><td><input class="pv-s" type="number" min="0" value="${v.stock??''}" placeholder="bajo pedido"></td>
      <td><select class="pv-m">${mopt(v.material_id)}</select></td><td><button class="btn sec sm" onclick="pvRead();PV.splice(${i},1);pvRender()">✕</button></td></tr>`).join('') : '';
  $('#p-stock').disabled = PV.length>0; $('#p-stock').title = PV.length ? 'Es la suma del stock de las variantes' : '';
}
function pvRead(){ PV = $$('#pv-table tr[data-v]').map(r=>({...PV[r.dataset.v], name:r.querySelector('.pv-n').value, color_hex:r.querySelector('.pv-c').value,
  price:r.querySelector('.pv-p').value, stock:r.querySelector('.pv-s').value, material_id:r.querySelector('.pv-m').value||null})); }
function pvAdd(){ pvRead(); PV.push({name:'', color_hex:'#888888', price:'', stock:'', material_id:null}); pvRender(); }
async function pvBulk(){
  const t = await ask('Variantes separadas por comas', '', {title:'Añadir varias variantes', placeholder:'Negro, Blanco, Rojo', ok:'Añadir'}); if (!t) return;
  pvRead(); const hexes = COLOR_HEX;
  t.split(',').map(x=>x.trim()).filter(Boolean).forEach(n=>PV.push({name:n, color_hex:hexes[n.toLowerCase()]||'#888888', price:'', stock:'', material_id:(MATS.find(m=>m.name.toLowerCase().includes(n.toLowerCase()))||{}).id||null}));
  pvRender();
}

// ---------- ofertas
let OFFERS = [], curOffer = null;
const odlg = $('#odlg');
async function loadOffers(){
  OFFERS = await api('/offers');
  const where = {todo:'puestos y pedidos', puesto:'solo puestos', pedidos:'solo pedidos'};
  $('#of-table').innerHTML = OFFERS.length ? `<tr><th>Oferta</th><th>Qué</th><th>Para</th><th>Dónde</th><th></th></tr>` + OFFERS.map(o=>`<tr style="${o.active?'':'opacity:.5'}">
    <td><b>${esc(o.name)}</b></td><td>${esc(o.text)}</td><td>${o.product?esc(o.product):o.category?'categoría '+esc(o.category):'todo'}</td><td>${where[o.applies]}</td>
    <td style="text-align:right;white-space:nowrap"><button class="btn sec sm" onclick="toggleOffer(${o.id})">${o.active?'Pausar':'Activar'}</button> <button class="btn sec sm" onclick="editOffer(${o.id})">Editar</button></td></tr>`).join('')
    : '<tr><td class="mut">Sin ofertas. Ejemplos: «3 llaveros por 10 €», «la 2ª maceta a mitad de precio».</td></tr>';
}
function ofKind(){
  const k = $('#of-kind').value, sc = $('#of-scope').value;
  $('#of-pw').classList.toggle('hidden', k!=='pack'); $('#of-qw').classList.toggle('hidden', k==='pct'); $('#of-cw').classList.toggle('hidden', k==='pack');
  $('#of-ql').textContent = k==='nth' ? 'A partir de la unidad nº' : 'Unidades del pack'; $('#of-cl').textContent = k==='nth' ? 'Descuento en esa unidad % (100 = gratis)' : 'Descuento %';
  $('#of-catw').classList.toggle('hidden', sc!=='cat'); $('#of-prodw').classList.toggle('hidden', sc!=='prod');
  const q = $('#of-qty').value||'N', pr = $('#of-price').value||'X', pc = $('#of-pct').value||'P';
  $('#of-eg').textContent = k==='pack' ? `Ejemplo: ${q} unidades por ${pr} €. Se juntan de la más cara a la más barata.` : k==='nth' ? `Ejemplo: de cada ${q}, la más barata con un ${pc} % de descuento.` : `Ejemplo: un ${pc} % menos en todo lo que entre.`;
}
function editOffer(id){
  curOffer = id ? OFFERS.find(o=>o.id===id) : {name:'', kind:'pack', qty:3, price:'', pct:'', product_id:null, category:'', applies:'todo', active:1};
  $('#of-name').value = curOffer.name; $('#of-kind').value = curOffer.kind; $('#of-qty').value = curOffer.qty; $('#of-price').value = curOffer.price??''; $('#of-pct').value = curOffer.pct??'';
  $('#of-scope').value = curOffer.product_id ? 'prod' : curOffer.category ? 'cat' : 'all'; $('#of-cat').value = curOffer.category||'';
  $('#p-cats2').innerHTML = [...new Set(PRODUCTS.map(p=>p.category).filter(Boolean))].map(c=>`<option value="${esc(c)}">`).join('');
  $('#of-prod').innerHTML = opts(PRODUCTS, curOffer.product_id, p=>[p.id, p.name]); $('#of-where').value = curOffer.applies; $('#of-on').checked = !!curOffer.active;
  $('#of-del').classList.toggle('hidden', !id); ofKind(); ['#of-qty','#of-price','#of-pct'].forEach(x=>$(x).oninput = ofKind); odlg.showModal();
}
async function saveOffer(){
  const sc = $('#of-scope').value;
  const body = {name:$('#of-name').value, kind:$('#of-kind').value, qty:$('#of-qty').value, price:$('#of-price').value, pct:$('#of-pct').value,
    category: sc==='cat' ? $('#of-cat').value : '', product_id: sc==='prod' ? +$('#of-prod').value : null, applies:$('#of-where').value, active:$('#of-on').checked};
  curOffer.id ? await api('/offers/'+curOffer.id,{method:'PUT',body}) : await api('/offers',{method:'POST',body});
  odlg.close(); toast('Oferta guardada'); loadOffers();
}
async function toggleOffer(id){ const o = OFFERS.find(x=>x.id===id); await api('/offers/'+id,{method:'PUT',body:{active:!o.active}}); loadOffers(); }
async function delOffer(){ if (!await sure('¿Borrar esta oferta?', {ok:'Borrar', danger:1})) return; await api('/offers/'+curOffer.id,{method:'DELETE'}); odlg.close(); loadOffers(); }
async function applyOrderOffers(){
  readItems(); const items = curOrder.items.filter(i=>!i.offer_id);
  const r = await api('/offers/preview',{method:'POST',body:{items, where:'pedidos'}});
  curOrder.items = [...items, ...r.discounts.map(d=>({description:`Oferta: ${d.name}`, qty:1, unit_price:-d.amount, unit_cost:0, offer_id:d.offer_id}))];
  renderItems(); toast(r.discounts.length ? `Ofertas aplicadas: −${eur(r.subtotal - r.total)}` : 'Ninguna oferta encaja con este pedido');
}

// ---------- etiquetas QR y bobina rápida
let SQ = null;
const sqdlg = $('#sqdlg');
function printLabels(onlyChecked){
  const ids = onlyChecked ? $$('#sk-table .sk-ck:checked').map(x=>x.dataset.id) : SPOOLS.filter(s=>s.status!=='gastada').map(s=>s.id);
  if (!ids.length) return toast(onlyChecked ? 'Marca alguna bobina' : 'No hay bobinas');
  window.open('/labels/spools?ids=' + ids.join(','), '_blank');
}
async function openSpoolQuick(id){
  const all = await api('/spools?all=1'); SPOOLS = all; SQ = all.find(s=>s.id===id);
  if (!SQ) return toast('Esa bobina ya no existe');
  $('#sq-title').innerHTML = `<i class="sw" style="display:inline-block;width:18px;height:18px;border-radius:50%;vertical-align:-3px;margin-right:8px;background:${esc(SQ.color_hex||'#888')}"></i>#${SQ.id} · ${esc(SQ.color_name||SQ.material||'')}`;
  $('#sq-body').innerHTML = `<div class="kpi"><div class="v" style="font-size:28px">${qfmt(SQ.remaining, SQ.unit)}</div><div class="l">quedan de ${qfmt(SQ.net_g, SQ.unit)}</div></div>
    <div class="bar" style="margin:10px 0"><i style="width:${SQ.pct}%;background:${SQ.pct<20?'var(--bad)':'var(--acc2)'}"></i></div>
    <div style="font-size:14px">${esc(SQ.material||'')} · ${esc(SQ.brand||'')}${SQ.location?' · '+esc(SQ.location):''} · <span class="tag">${SQ.status}</span></div>`;
  sqdlg.showModal();
}

// ---------- previsión de filamento
async function loadForecast(){
  const f = await api('/forecast');
  $('#fc-help').textContent = `ritmo de los últimos ${f.window_days} días · compra en ${f.lead_days} días`;
  $('#fc-lead').value = f.lead_days; $('#fc-win').value = f.window_days; $('#fc-quotes').checked = !!S.forecast_quotes;
  const st = {falta:'<span class="fc-falta">no llega</span>', comprar:'<span class="fc-comprar">comprar</span>', ok:'<span class="tag st-listo">ok</span>', sin_stock:'<span class="mut">sin controlar</span>'};
  $('#fc-table').innerHTML = f.materials.length ? `<tr><th>Material</th><th class="n">Queda</th><th class="n">Pendiente</th><th class="n">Tras los pedidos</th><th class="n">Gasto/día</th><th>Se acaba</th><th class="n">Comprar</th><th></th></tr>` +
    f.materials.map(m=>`<tr><td>${m.color?`<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${esc(m.color)};border:1px solid var(--line);margin-right:6px"></span>`:''}<b>${esc(m.name)}</b></td>
      <td class="n">${qfmt(m.stock, m.unit)}</td><td class="n">${m.pending?qfmt(m.pending, m.unit):'–'}${m.pending_orders.length?`<br><span class="mut" style="font-size:11px">${m.pending_orders.map(o=>`<a href="#" onclick="openOrder(${o});return false">#${o}</a>`).join(' ')}</span>`:''}</td>
      <td class="n ${m.left<0?'neg':''}">${m.left==null?'':qfmt(m.left, m.unit)}</td><td class="n">${m.rate_day?qfmt(m.rate_day, m.unit):'–'}</td>
      <td>${m.status==='falta'?'<span class="neg">ya no llega</span>':m.runs_out?`${m.runs_out} <span class="mut">(${m.days_left} d)</span>`:'<span class="mut">–</span>'}</td>
      <td class="n">${m.buy_units?`<b>${m.buy_units}</b> × ${qfmt(m.pack, m.unit)}`:'–'}</td><td>${st[m.status]}</td></tr>`).join('')
    : '<tr><td class="mut">Activa el control de stock en tus materiales o añade bobinas para ver la previsión.</td></tr>';
}
async function saveForecastCfg(){
  S = await api('/settings',{method:'PUT',body:{forecast_lead_days:+$('#fc-lead').value||0, forecast_window_days:+$('#fc-win').value||60, forecast_quotes:$('#fc-quotes').checked}});
  toast('Guardado'); loadForecast();
}

// ---------- Manyfold
let MF = {target:null, model:null};
const mfdlg = $('#mfdlg');
function openManyfold(target){
  if (!S.manyfold_url) return toast('Configura Manyfold en Ajustes');
  MF = {target, model:null}; $('#mf-go').classList.add('hidden'); $('#mf-list').innerHTML = ''; mfdlg.showModal(); $('#mf-q').focus();
  if (target.product_id && !$('#mf-q').value) $('#mf-q').value = (PRODUCTS.find(p=>p.id===target.product_id)||{}).name||'';
  mfSearch();
}
async function mfSearch(){
  $('#mf-list').innerHTML = '<p class="mut">Buscando…</p>'; $('#mf-go').classList.add('hidden');
  try { const r = await api('/manyfold/search?q=' + encodeURIComponent($('#mf-q').value.trim()));
    $('#mf-list').innerHTML = r.models.length ? r.models.map((m,i)=>`<div class="mf-model" onclick="mfOpen(${i})"><b>${esc(m.name)}</b> <span class="mut" style="font-size:12px">${esc(m.id)}</span></div>`).join('')
      + (r.total > r.models.length ? `<p class="mut" style="font-size:12px">${r.total} en total: afina la búsqueda.</p>` : '') : '<p class="mut">Nada con ese nombre.</p>';
    MF.list = r.models;
  } catch(e){ $('#mf-list').innerHTML = `<p class="neg">${esc(e.message)}</p>`; }
}
async function mfOpen(i){
  const m = await api('/manyfold/model?id=' + encodeURIComponent(MF.list[i].id)); MF.model = m;
  $('#mf-list').innerHTML = `<div class="row" style="align-items:center"><b>${esc(m.name)}</b><div></div><button class="btn sec sm" style="flex:0 0 auto" onclick="mfSearch()">← volver</button></div>` +
    (m.files.length ? m.files.map((f,k)=>`<label class="switch" style="display:flex;margin:8px 0"><input type="checkbox" class="mf-f" data-k="${k}" ${/stl|3mf|gcode|obj|step/i.test(f.name+f.format)?'checked':''}> ${esc(f.name)} <span class="mut" style="font-size:12px">${esc(f.format)}</span></label>`).join('') : '<p class="mut">Este modelo no tiene archivos.</p>');
  $('#mf-go').classList.toggle('hidden', !m.files.length);
}
async function mfImport(){
  const ids = $$('#mf-list .mf-f:checked').map(x=>MF.model.files[x.dataset.k].id); if (!ids.length) return toast('Marca algún archivo');
  $('#mf-go').disabled = true; $('#mf-go').textContent = 'Trayendo…';
  try { const r = await api('/manyfold/import',{method:'POST',body:{...MF.target, model_id:MF.model.id, file_ids:ids}});
    toast(`${r.imported.length} archivo(s) traído(s) de Manyfold`); mfdlg.close();
    if (MF.target.order_id){ const o = await api('/orders/'+MF.target.order_id); curOrder.files = o.files; renderFiles(); }
    if (MF.target.product_id){ loadProdFiles(); curProd.manyfold_id = MF.model.id; mfLink(); }
  } catch(e){ toast(e.message); } finally { $('#mf-go').disabled = false; $('#mf-go').textContent = 'Traer los marcados'; }
}
function mfLink(){ const on = !!(S.manyfold_url && curProd.manyfold_id); $('#p-mflink').classList.toggle('hidden', !on);
  if (on) $('#p-mflink').href = S.manyfold_url.replace(/\/$/,'') + curProd.manyfold_id; }
function loadManyfoldCfg(){ $('#mf-url').value = S.manyfold_url||''; $('#mf-id').value = S.manyfold_client_id||''; $('#mf-secret').value = S.manyfold_client_secret||''; $('#mf-res').textContent=''; }
async function saveManyfold(){
  S = await api('/settings',{method:'PUT',body:{manyfold_url:$('#mf-url').value.trim(), manyfold_client_id:$('#mf-id').value.trim(), manyfold_client_secret:$('#mf-secret').value}});
  document.body.classList.toggle('has-mf', !!S.manyfold_url); loadManyfoldCfg(); toast('Guardado');
}
async function testManyfold(){
  await saveManyfold(); const r = await api('/manyfold/test');
  $('#mf-res').innerHTML = r.ok ? `<span class="pos">✓ Conectado: ${r.models} modelo(s) ${r.auth?'(con credenciales)':'(solo públicos)'}</span>` : `<span class="neg">${esc(r.error)}</span>`;
}

// ---------- tablas → tarjetas en móvil (etiqueta cada celda con su cabecera)
function cardify(t){
  if (t.closest('.rep,.nocards,dialog') || t.id==='pos-cart') return;
  const rows = [...t.rows], h = rows.find(r=>r.cells.length>1 && [...r.cells].every(c=>c.tagName==='TH'));
  if (!h || rows.length<2) return t.classList.remove('mc');
  const dr = rows.find(r=>r!==h);
  if (!t.classList.contains('cardok') && dr && dr.querySelectorAll('input:not([type=checkbox]),select,textarea').length>2) return t.classList.remove('mc');
  h.classList.add('mc-h');
  const labels = [...h.cells].flatMap(c=>Array(c.colSpan||1).fill(c.textContent.trim()));
  rows.forEach(r=>{ if (r===h) return; let i = 0;
    [...r.cells].forEach((c,k)=>{ const l = labels[i]; i += c.colSpan||1;
      if (k>0 && l && (c.colSpan||1)===1){ if (c.dataset.l!==l) c.dataset.l = l; } else if (c.dataset.l!=null) delete c.dataset.l; }); });
  t.classList.add('mc');
}
let cardTimer = null;
new MutationObserver(()=>{ clearTimeout(cardTimer); cardTimer = setTimeout(()=>$$('main table').forEach(cardify), 80); })
  .observe(document.querySelector('main'), {childList:true, subtree:true});

// ---------- buscador global (Ctrl+K o /)
const K = {sel:0, items:[], timer:null, seq:0};
const K_ACTIONS = [
  ['Nuevo pedido', 'pedido presupuesto encargo', ()=>{ show('orders'); openOrder(); }],
  ['Venta en el puesto', 'vender cobrar caja mercadillo', ()=>show('pos')],
  ['Nuevo cliente', 'ficha cliente', ()=>{ show('cli'); openClient(); }],
  ['Apuntar gasto o ingreso', 'movimiento contabilidad', ()=>{ show('acc'); setTimeout(()=>$('#m-concept')?.focus(), 50); }],
  ['Añadir bobinas', 'filamento rollo almacén entrada', ()=>{ show('stk'); setTimeout(()=>$('#sa-mat')?.scrollIntoView({behavior:'smooth', block:'center'}), 50); }],
  ['Lista de la compra', 'comprar previsión proveedor', ()=>{ show('stk'); setTimeout(()=>$('#shop-card')?.scrollIntoView({behavior:'smooth'}), 120); }],
  ['Nuevo gasto fijo', 'recurrente cuota autónomo alquiler dominio', ()=>{ show('acc'); editRecurring(); }],
  ['Nuevo componente', 'muelle tornillo imán inserto ferretería', async ()=>{ show('stk'); await stkTab('comp'); compEdit(); }],
  ['Nueva ubicación', 'caja cajón estantería sitio', async ()=>{ show('stk'); await stkTab('loc'); locEdit(); }],
  ['¿Qué me falta para fabricar…?', 'receta fabricar necesito materiales', async ()=>{ const pid = await choose('¿Qué artículo?', PRODUCTS.map(p=>({value:p.id, label:p.name, sub:p.stock!=null?`hay ${p.stock}`:''}))); if (pid!=null) openNeeds(pid); }],
  ['Recontar componentes', 'inventario recuento contar', async ()=>{ show('stk'); await stkTab('comp'); $('#cp-count').checked = true; cpRender(); }],
  ['Calculadora de precio', 'calcular coste', ()=>show('calc')],
  ['Ajustes', 'configuración', ()=>show('cfg')],
];
const K_ICON = {order:'orders', client:'cli', product:'cat', spool:'stk', material:'stk', component:'stk', location:'stk', printer:'prn', event:'pos', action:'search'};
const K_GROUP = {action:'Acciones', order:'Pedidos', client:'Clientes', product:'Productos', component:'Componentes', location:'Ubicaciones', spool:'Bobinas', material:'Materiales', printer:'Impresoras', event:'Puestos'};
function openSearch(){ drawer(false); $('#k-q').value = ''; kRender([]); $('#kdlg').showModal(); $('#k-q').focus(); }
function kIcon(t){ const b = $(`#nav [data-v="${K_ICON[t]}"] svg`); return b ? b.outerHTML : ''; }
function kRender(res){
  const q = $('#k-q').value.trim().toLowerCase();
  const acts = K_ACTIONS.filter(([l,kw])=>!q || (l+' '+kw).toLowerCase().includes(q)).slice(0, q?4:9).map(([l,,fn])=>({type:'action', title:l, fn}));
  K.items = [...acts, ...res]; K.sel = Math.min(K.sel, Math.max(0, K.items.length-1));
  let last = '';
  $('#k-res').innerHTML = K.items.map((x,i)=>{ const g = x.type!==last ? `<div class="k-g">${K_GROUP[x.type]||x.type}</div>` : ''; last = x.type;
    return g + `<button data-i="${i}" class="${i===K.sel?'on':''}">${kIcon(x.type)}<span class="k-t">${esc(x.title)}</span><span class="k-s">${esc(x.sub||'')}</span></button>`; }).join('')
    || `<p class="mut" style="padding:14px">Nada con «${esc(q)}».</p>`;
}
function kGo(i){
  const x = K.items[i]; if (!x) return; $('#kdlg').close();
  if (x.type==='action') return x.fn();
  ({order:()=>{ show('orders'); openOrder(x.id); }, client:()=>{ show('cli'); openClient(x.id); }, product:()=>{ show('cat'); setTimeout(()=>editProd(x.id), 150); },
    spool:()=>{ show('stk'); openSpoolQuick(x.id); }, material:()=>{ show('stk'); priceHistory(x.id); }, printer:()=>show('prn'),
    component:()=>openComp(x.id), location:()=>openLoc(x.id),
    event:()=>{ POS.ev = x.id; show('pos'); }})[x.type]?.();
}
$('#k-q').addEventListener('input', ()=>{ K.sel = 0; kRender(K.items.filter(x=>x.type!=='action'));
  clearTimeout(K.timer); const q = $('#k-q').value.trim(); if (!q) return kRender([]);
  K.timer = setTimeout(async ()=>{ const seq = ++K.seq; const r = await api('/search?q='+encodeURIComponent(q)).catch(()=>({results:[]}));
    if (seq===K.seq) kRender(r.results); }, 160); });
$('#k-q').addEventListener('keydown', e=>{
  if (e.key==='ArrowDown' || e.key==='ArrowUp'){ e.preventDefault(); K.sel = (K.sel + (e.key==='ArrowDown'?1:-1) + K.items.length) % Math.max(1,K.items.length);
    $$('#k-res button').forEach((b,i)=>b.classList.toggle('on', i===K.sel)); $('#k-res button.on')?.scrollIntoView({block:'nearest'}); }
  else if (e.key==='Enter'){ e.preventDefault(); kGo(K.sel); } });
$('#k-res').addEventListener('click', e=>{ const b = e.target.closest('button[data-i]'); if (b) kGo(+b.dataset.i); });
document.addEventListener('keydown', e=>{
  if ($('#app').classList.contains('hidden')) return;
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
  if ((e.key==='k' || e.key==='K') && (e.ctrlKey || e.metaKey)){ e.preventDefault(); $('#kdlg').open ? $('#kdlg').close() : openSearch(); }
  else if (e.key==='/' && !typing && !document.querySelector('dialog[open]')){ e.preventDefault(); openSearch(); }
});

// ---------- lista de la compra y precios
let SHOP = {items:[], buying:null};
async function loadSuppliers(){ const l = await api('/suppliers').catch(()=>[]); $('#sup-list').innerHTML = l.map(x=>`<option value="${esc(x)}">`).join(''); }
async function loadShopping(){
  const r = await api('/shopping'); SHOP.items = r.items; loadSuppliers();
  $('#buy-n').textContent = r.items.length ? r.items.length : '';
  const pk = x => x.material_id ? `${x.units} × ${qfmt(x.pack, x.unit)}` : `${x.units}`;
  $('#shop-sugg').innerHTML = r.suggestions.length ? `<div class="sugg"><div class="mut" style="font-size:12px;margin-bottom:6px">La previsión sugiere:</div>${r.suggestions.map((x,i)=>
    `<div class="sugg-i"><span><b>${esc(x.material)}</b> · ${x.units} × ${qfmt(x.pack, x.unit)} <span class="mut">(${esc(x.reason)}${x.supplier?' · '+esc(x.supplier):''}${x.est_price!=null?' · ~'+eur(x.est_price)+'/ud':''})</span></span>
     <button class="btn sec sm" onclick="shopAddSugg(${i})">Añadir</button></div>`).join('')}</div>` : '';
  SHOP.sugg = r.suggestions;
  $('#shop-table').innerHTML = r.items.length ? `<tr><th>Qué</th><th class="n">Cuánto</th><th>Proveedor</th><th class="n">Precio/ud</th><th class="n">Total</th><th></th></tr>` +
    r.items.map(x=>`<tr><td><b>${x.url?`<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.material)}</a>`:esc(x.material||x.text)}</b>${x.component_id?' <span class="tag">componente</span>':''}${x.note?`<br><span class="mut" style="font-size:12px">${esc(x.note)}</span>`:''}</td><td class="n">${pk(x)}</td>
      <td>${esc(x.supplier)||'<span class="mut">–</span>'}</td><td class="n">${x.est_price!=null?eur(x.est_price):'–'}</td><td class="n">${x.total!=null?eur(x.total):'–'}</td>
      <td style="text-align:right;white-space:nowrap"><button class="btn sm" onclick="shopBought(${x.id})">Comprado</button> <button class="btn sec sm" onclick="shopEdit(${x.id})">Editar</button></td></tr>`).join('')
    : '<tr><td class="mut">No hay nada apuntado. Añade lo que haga falta o usa lo que sugiere la previsión.</td></tr>';
  $('#shop-total').innerHTML = r.items.length ? `Total estimado: <b>${eur(r.total)}</b>` : '';
  $('#shop-done').innerHTML = r.done.length ? `<tr><th>Fecha</th><th>Qué</th><th class="n">Cuánto</th><th>Proveedor</th></tr>` + r.done.map(x=>`<tr><td>${esc(x.bought_at)}</td><td>${esc(x.material||x.text)}</td><td class="n">${pk(x)}</td><td>${esc(x.supplier)}</td></tr>`).join('') : '<tr><td class="mut">Nada todavía.</td></tr>';
}
async function shopAddSugg(i){ const x = SHOP.sugg[i]; await api('/shopping',{method:'POST',body:{material_id:x.material_id||null, component_id:x.component_id||null, units:x.units, supplier:x.supplier, est_price:x.est_price}}); loadShopping(); }
async function shopEdit(id){
  const x = id ? SHOP.items.find(i=>i.id===id) : {};
  const f = await form(id ? 'Editar compra' : 'Añadir a la lista', [
    {k:'material_id', label:'Material', type:'select', value:x.material_id||'', options:[['','— otra cosa —'], ...MATS.filter(m=>m.active).map(m=>[m.id, m.name])]},
    {k:'text', label:'Si no es un material: ¿qué es?', value:x.text||'', placeholder:'boquillas 0.4, PEI, IPA…'},
    {k:'units', label:'Envases / unidades', type:'number', value:x.units||1, half:1},
    {k:'est_price', label:'Precio por unidad (€)', type:'number', value:x.est_price??'', half:1, hint:'Vacío = el de la última compra.'},
    {k:'supplier', label:'Proveedor', value:x.supplier||'', list:'sup-list'},
    {k:'note', label:'Nota', value:x.note||'', placeholder:'enlace, oferta, código…'}],
    {ok:'Guardar', extra: id ? 'Quitar de la lista' : ''});
  if (!f) return; if (f.__extra) return shopDel(id);
  if (id && f.material_id==='' && !f.text) return toast('¿Qué hay que comprar?');
  if (id) await api('/shopping/'+id,{method:'PUT',body:f}); else await api('/shopping',{method:'POST',body:{...f, material_id:f.material_id||null}});
  loadShopping();
}
async function shopDel(id){ await api('/shopping/'+id,{method:'DELETE'}); loadShopping(); }
async function shopBought(id){
  const x = SHOP.items.find(i=>i.id===id); if (!x) return;
  const how = await choose('¿Cómo lo apuntas?', [
    ...(x.material_id ? [{value:'spools', label:'Dar de alta las bobinas', sub:'rellena «Añadir bobinas»'}] : []),
    ...(x.component_id ? [{value:'comp', label:'Sumarlo al almacén', sub:`${x.units} × ${+x.pack} ${x.unit}`}] : []),
    {value:'mark', label:'Solo marcar como comprado', sub:'sin tocar el almacén'},
    {value:'del', label:'Quitar de la lista', sub:'ya no hace falta'}]);
  if (!how) return;
  if (how==='del') return shopDel(id);
  if (how==='mark'){ await api('/shopping/'+id,{method:'PUT',body:{status:'comprado'}}); return loadShopping(); }
  if (how==='comp'){
    const f = await form('Comprado: '+x.material, [
      {k:'packs', label:'Packs que han llegado', type:'number', value:x.units, half:1},
      {k:'paid', label:'Pagado en total (€)', type:'number', value:x.total??'', half:1, hint:'Vacío = no apuntar el gasto.'},
      {k:'person', label:'¿Quién lo pagó?', type:'select', value:S.people[0]||'', options:[['','—'], ...S.people.map(p=>[p,p])]}], {ok:'Sumar al almacén'});
    if (!f) return;
    await api(`/components/${x.component_id}/stock`,{method:'POST',body:{mode:'compra', ...f, supplier:x.supplier, shopping_id:id}});
    toast('Sumado al almacén'); return loadShopping();
  }
  SHOP.buying = id;
  $('#sa-mat').value = x.material_id; saTare?.(); $('#sa-count').value = x.units; $('#sa-sup').value = x.supplier||'';
  $('#sa-paid').value = x.total!=null ? x.total : ''; $('#sa-net').value = x.pack || $('#sa-net').value;
  $('#sa-shop').innerHTML = `Dando de alta la compra de <b>${esc(x.material)}</b>: revisa marca y color y pulsa «Añadir al almacén». <a href="#" onclick="SHOP.buying=null;$('#sa-shop').classList.add('hidden');return false">Cancelar</a>`;
  $('#sa-shop').classList.remove('hidden'); $('#sa-brand').scrollIntoView({behavior:'smooth', block:'center'}); $('#sa-brand').focus();
}
async function shopCopy(){
  const by = {}; SHOP.items.forEach(x=>(by[x.supplier||'Sin proveedor'] ||= []).push(x));
  const txt = Object.entries(by).map(([s,l])=>`${s}:\n` + l.map(x=>`- ${x.material||x.text}: ${x.units}${x.material_id?' × '+qfmt(x.pack, x.unit):''}${x.est_price!=null?' (~'+eur(x.est_price)+'/ud)':''}`).join('\n')).join('\n\n');
  if (!txt) return toast('La lista está vacía');
  try { await navigator.clipboard.writeText(txt); toast('Lista copiada'); } catch(e){ await tell('', {title:'Lista de la compra', html:`<textarea style="min-height:200px" readonly>${esc(txt)}</textarea>`}); }
}
async function priceHistory(mid){
  const m = MATS.find(x=>x.id===mid) || {name:''}, r = await api(`/materials/${mid}/prices`);
  const h = r.history;
  await tell('', {title:'Precios: '+m.name, html: h.length ? `
    <div class="grid g3" style="margin-bottom:12px"><div class="kpi"><div class="l">Más barato</div><div class="v">${eur(r.min)}<span class="mut" style="font-size:13px">/kg</span></div></div>
      <div class="kpi"><div class="l">Media</div><div class="v">${eur(r.avg)}<span class="mut" style="font-size:13px">/kg</span></div></div>
      <div class="kpi"><div class="l">Más caro</div><div class="v">${eur(r.max)}<span class="mut" style="font-size:13px">/kg</span></div></div></div>
    ${r.suppliers.length?`<p style="font-size:13px;margin:0 0 10px">Mejor precio por proveedor: ${r.suppliers.map(s=>`<b>${esc(s.supplier)}</b> ${eur(s.best_per_kg)}/kg`).join(' · ')}</p>`:''}
    <div class="scroll"><table><tr><th>Fecha</th><th>Proveedor</th><th>Marca</th><th class="n">Cuánto</th><th class="n">Pagado</th><th class="n">€/kg</th></tr>
    ${h.map(x=>`<tr><td>${esc(x.date)}</td><td>${esc(x.supplier)||'–'}</td><td>${esc(x.brand)||'–'}</td><td class="n">${x.units} × ${qfmt(x.unit_qty, m.unit||'g')}</td><td class="n">${eur(x.total)}</td><td class="n"><b>${x.per_kg!=null?eur(x.per_kg):'–'}</b></td></tr>`).join('')}</table></div>`
    : '<p class="mut">Todavía no hay compras con precio. Se apuntan solas al añadir bobinas o registrar una entrada con lo pagado.</p>'});
}

// ---------- gastos fijos
const RC_EVERY = [['mensual','Cada mes'],['trimestral','Cada 3 meses'],['semestral','Cada 6 meses'],['anual','Cada año']];
let RC = [];
async function loadRecurring(){
  const r = await api('/recurring'); RC = r.items;
  $('#rc-total').innerHTML = RC.length ? `≈ <b>${eur(r.per_month)}</b> al mes` : '';
  $('#rc-table').innerHTML = RC.length ? `<tr><th>Concepto</th><th class="n">Importe</th><th>Cada</th><th>Próximo</th><th class="n">Apuntado</th><th></th></tr>` +
    RC.map(x=>`<tr class="${x.active?'':'rc-off'}"><td><b>${esc(x.concept)}</b><br><span class="mut" style="font-size:12px">${esc(x.category)}${x.person?' · '+esc(x.person):''}</span></td>
      <td class="n">${eur(x.amount)}</td><td>${esc((RC_EVERY.find(e=>e[0]===x.every)||[,x.every])[1])} <span class="mut">(día ${x.day})</span></td>
      <td>${x.active ? (x.next ? esc(x.next) : '<span class="mut">terminado</span>') : '<span class="mut">en pausa</span>'}</td>
      <td class="n">${x.booked.n} · ${eur(x.booked.s)}</td>
      <td style="text-align:right;white-space:nowrap"><button class="btn sec sm" onclick="toggleRecurring(${x.id})">${x.active?'Pausar':'Reanudar'}</button> <button class="btn sec sm" onclick="editRecurring(${x.id})">Editar</button></td></tr>`).join('')
    : '<tr><td class="mut">No hay gastos fijos. Añade la cuota de autónomo, el dominio, el alquiler…</td></tr>';
}
async function editRecurring(id){
  const x = id ? RC.find(r=>r.id===id) : {every:'mensual', day:1, start:new Date().toISOString().slice(0,7), category:(S.expense_categories||[]).find(c=>/fij|cuota|otro|general/i.test(c))||(S.expense_categories||[])[0]||''};
  const f = await form(id ? 'Editar gasto fijo' : 'Nuevo gasto fijo', [
    {k:'concept', label:'Concepto', value:x.concept||'', placeholder:'Cuota de autónomo, dominio, alquiler…', req:1},
    {k:'amount', label:'Importe (€)', type:'number', value:x.amount??'', half:1, req:1},
    {k:'every', label:'Cada cuánto', type:'select', value:x.every, options:RC_EVERY, half:1},
    {k:'day', label:'Día del mes', type:'number', value:x.day, half:1, hint:'Del 1 al 28.'},
    {k:'category', label:'Categoría', type:'select', value:x.category, options:(S.expense_categories||[]).map(c=>[c,c]), half:1},
    {k:'start', label:'Desde (mes)', type:'month', value:x.start||'', half:1, placeholder:'AAAA-MM'},
    {k:'until', label:'Hasta (opcional)', type:'month', value:x.until||'', half:1, placeholder:'AAAA-MM'},
    {k:'person', label:'¿Quién lo paga?', type:'select', value:x.person||'', options:[['','—'], ...S.people.map(p=>[p,p])]}],
    {ok:'Guardar', extra: id ? 'Borrar' : '', html: id ? '' : '<span class="mut" style="font-size:13px">Si el inicio es un mes pasado, se apuntan también los meses que faltan hasta hoy.</span>'});
  if (!f) return; if (f.__extra) return delRecurring(id);
  const r = id ? await api('/recurring/'+id,{method:'PUT',body:f}) : await api('/recurring',{method:'POST',body:f});
  toast(r.booked ? `Guardado · ${r.booked} gasto(s) apuntado(s)` : 'Guardado');
  loadRecurring(); loadAcc();
}
async function toggleRecurring(id){ const x = RC.find(r=>r.id===id); await api('/recurring/'+id,{method:'PUT',body:{active:!x.active}}); loadRecurring(); loadAcc(); }
async function delRecurring(id){
  const how = await choose('¿Borrar este gasto fijo?', [
    {value:'keep', label:'Borrar y conservar lo ya apuntado', sub:'los movimientos se quedan en contabilidad'},
    {value:'all', label:'Borrar también lo apuntado', sub:'quita sus movimientos'}]);
  if (!how) return;
  await api(`/recurring/${id}${how==='all'?'?movements=1':''}`,{method:'DELETE'}); toast('Borrado'); loadRecurring(); loadAcc();
}

// ---------- Almacén en pestañas
let STK_TAB = (()=>{ try { return localStorage.getItem('stkTab') || 'fil'; } catch(e){ return 'fil'; } })();
function stkTab(p){
  STK_TAB = p; try { localStorage.setItem('stkTab', p); } catch(e){}
  $$('#stk-tabs button').forEach(b=>b.classList.toggle('on', b.dataset.p===p));
  $$('.stk-pane').forEach(x=>x.classList.toggle('hidden', x.dataset.p!==p));
  return ({comp:loadComps, fin:loadFinished, loc:loadLocs, buy:loadShopping})[p]?.();
}
$('#stk-tabs').onclick = e => { const b = e.target.closest('button[data-p]'); if (b) stkTab(b.dataset.p); };

// ---------- ubicaciones
let LOCS = [], LOC = null;
const LOC_KINDS = [['estantería','Estantería'],['cajonera','Cajonera'],['cajón','Cajón'],['caja','Caja'],['armario','Armario'],['balda','Balda'],['otro','Otro']];
async function ensureLocs(force){ if (force || !LOCS.length) LOCS = await api('/locations').catch(()=>[]); $('#loc-list').innerHTML = LOCS.map(l=>`<option value="${esc(l.path)}">`).join(''); return LOCS; }
const locOpts = (sel, none='— sin ubicación —') => `<option value="">${none}</option>` + LOCS.map(l=>`<option value="${l.id}" ${String(l.id)===String(sel)?'selected':''}>${esc(l.path)}</option>`).join('');
const locFormOpts = () => [['', '— sin ubicación —'], ...LOCS.map(l=>[l.id, l.path])];
async function loadLocs(){
  await ensureLocs(true);
  const kids = {}; LOCS.forEach(l=>(kids[l.parent_id||0] ||= []).push(l));
  const node = l => { const n = l.n_components + l.n_spools + l.n_products;
    return `<li><div class="lc-row"><label class="lc-ck"><input type="checkbox" class="lc-sel" value="${l.id}"></label>
      <a href="#" onclick="openLoc(${l.id});return false"><b>${esc(l.name)}</b></a> <span class="mut" style="font-size:12px">${esc((LOC_KINDS.find(k=>k[0]===l.kind)||[,l.kind])[1])}${n?` · ${[l.n_components?l.n_components+' comp.':'', l.n_spools?l.n_spools+' bob.':'', l.n_products?l.n_products+' art.':''].filter(Boolean).join(', ')}`:''}</span>
      <span style="margin-left:auto;display:flex;gap:6px"><button class="btn sec sm" onclick="locEdit(null, ${l.id})" title="Añadir dentro">+ dentro</button><button class="btn sec sm" onclick="locEdit(${l.id})">Editar</button></span></div>
      ${(kids[l.id]||[]).length ? `<ul>${kids[l.id].map(node).join('')}</ul>` : ''}</li>`; };
  $('#lc-tree').innerHTML = LOCS.length ? `<ul class="lc-tree">${(kids[0]||[]).map(node).join('')}</ul>` :
    '<p class="mut">Aún no hay ubicaciones. Empieza por lo grande (la estantería) y mete dentro cajas y cajones.</p>';
}
async function locEdit(id, parent){
  await ensureLocs();
  const l = id ? LOCS.find(x=>x.id===id) : {kind:'caja', parent_id:parent||''};
  const f = await form(id ? 'Editar ubicación' : 'Nueva ubicación', [
    {k:'name', label:'Nombre', value:l.name||'', req:1, placeholder:'Estantería del taller, Caja tornillería, Cajón 3…'},
    {k:'kind', label:'Tipo', type:'select', value:l.kind, options:LOC_KINDS, half:1},
    {k:'parent_id', label:'Está dentro de', type:'select', value:l.parent_id||'', half:1, options:[['', '— nada (es lo más grande) —'], ...LOCS.filter(x=>x.id!==id).map(x=>[x.id, x.path])]},
    {k:'notes', label:'Notas', value:l.notes||''}], {ok:'Guardar', extra: id ? 'Borrar' : ''});
  if (!f) return;
  if (f.__extra){ if (!await sure('Lo que haya dentro pasa al sitio que la contiene.', {title:`¿Borrar «${l.name}»?`, ok:'Borrar', danger:1})) return;
    await api('/locations/'+id,{method:'DELETE'}); if ($('#ldlg').open) ldlg.close(); toast('Borrada'); return loadLocs(); }
  const r = id ? await api('/locations/'+id,{method:'PUT',body:f}) : await api('/locations',{method:'POST',body:f});
  toast('Guardado'); await loadLocs(); if ($('#ldlg').open && LOC) openLoc(LOC.id);
  return r;
}
function locLabels(){
  const ids = $$('.lc-sel:checked').map(x=>x.value);
  window.open('/labels/locations?ids=' + (ids.length ? ids : LOCS.map(l=>l.id)).join(','), '_blank');
}
async function openLoc(id){
  LOC = await api('/locations/'+id); await ensureLocs();
  $('#ld-title').textContent = LOC.name; $('#ld-path').textContent = LOC.parent_id ? LOC.path : '';
  $('#ld-qr').href = '/labels/locations?ids=' + id;
  const cs = LOC.components, sp = LOC.spools, pr = LOC.products;
  $('#ld-body').innerHTML =
    (LOC.children.length ? `<div class="chips">${LOC.children.map(c=>`<button class="btn sec sm" onclick="openLoc(${c.id})">📦 ${esc(c.name)}</button>`).join('')}</div>` : '')
    + (cs.length ? `<h3 class="rh">Componentes</h3><table class="nocards cnt-t">${cs.map(c=>`<tr class="${c.low?'low':''}"><td><b>${esc(c.name)}</b>${c.low?' <span class="tag due">falta</span>':''}</td>
        <td class="n" style="white-space:nowrap"><button class="btn sec sm" onclick="compQuick(${c.id},-1)">−</button>
        <input class="cnt-in" inputmode="decimal" value="${c.stock}" onchange="compCount(${c.id}, this.value, true)"> <span class="mut">${esc(c.unit)}</span>
        <button class="btn sec sm" onclick="compQuick(${c.id},1)">+</button></td></tr>`).join('')}</table>` : '')
    + (sp.length ? `<h3 class="rh">Bobinas</h3>${sp.map(s=>`<div class="ld-sp"><i class="sw" style="background:${esc(s.color_hex||'#888')}"></i> <a href="#" onclick="ldlg.close();openSpoolQuick(${s.id});return false">#${s.id} ${esc(s.material||'')} ${esc(s.color_name||'')}</a> <span class="mut">${esc(s.brand||'')} · ${qfmt(s.remaining, s.unit)}</span></div>`).join('')}` : '')
    + (pr.length ? `<h3 class="rh">Producto terminado</h3><table class="nocards cnt-t">${pr.map(p=>`<tr><td><b>${esc(p.name)}</b></td>
        <td class="n"><input class="cnt-in" inputmode="numeric" value="${p.stock??''}" placeholder="—" onchange="finSet(${p.id},'stock',this.value,true)"> <span class="mut">uds</span></td></tr>`).join('')}</table>` : '')
    + (!LOC.children.length && !cs.length && !sp.length && !pr.length ? '<p class="mut">Vacía. Asigna aquí componentes, bobinas o artículos desde su ficha.</p>' : '');
  if (!$('#ldlg').open) ldlg.showModal();
}

// ---------- componentes
let COMPS = [];
const COMP_UNITS = [['ud','unidades'],['par','pares'],['m','metros'],['cm','centímetros'],['ml','mililitros'],['g','gramos']];
async function ensureComps(force){
  if (force || !COMPS.length) COMPS = await api('/components').catch(()=>[]);
  $('#comp-list').innerHTML = COMPS.filter(c=>c.active).map(c=>`<option value="${esc(c.name)}">`).join('');
  $('#comp-cats').innerHTML = [...new Set(COMPS.map(c=>c.category).filter(Boolean))].map(c=>`<option value="${esc(c)}">`).join('');
  return COMPS;
}
async function loadComps(){
  await Promise.all([ensureComps(true), ensureLocs(), loadSuppliers()]);
  const cats = [...new Set(COMPS.map(c=>c.category).filter(Boolean))].sort();
  $('#cp-cat').innerHTML = `<option value="">Todas las categorías</option>` + opts(cats, $('#cp-cat').value);
  cpRender();
}
function cpRender(){
  const q = $('#cp-q').value.trim().toLowerCase(), cat = $('#cp-cat').value, low = $('#cp-low').checked, count = $('#cp-count').checked;
  const list = COMPS.filter(c=>(!q || (c.name+' '+c.category+' '+c.location+' '+c.supplier).toLowerCase().includes(q)) && (!cat || c.category===cat) && (!low || c.low));
  $('#cp-table').innerHTML = list.length ? `<tr><th>Componente</th><th class="n">Hay</th><th class="n">Mínimo</th><th class="n">€/ud</th><th>Dónde</th><th>Va en</th><th></th></tr>` +
    list.map(c=>`<tr class="${c.active?'':'rc-off'}"><td><b>${esc(c.name)}</b>${c.low?' <span class="tag due">falta</span>':''}<br><span class="mut" style="font-size:12px">${esc(c.category)}${c.url?` · <a href="${esc(c.url)}" target="_blank" rel="noopener">comprar</a>`:c.supplier?' · '+esc(c.supplier):''}</span></td>
      <td class="n" style="white-space:nowrap">${count ? `<input class="cnt-in" inputmode="decimal" value="${c.stock}" onchange="compCount(${c.id}, this.value)"> ${esc(c.unit)}` : `<b class="${c.low?'neg':''}">${+c.stock.toFixed(3)}</b> ${esc(c.unit)}`}</td>
      <td class="n">${c.min_stock?+c.min_stock:'–'}</td><td class="n">${c.unit_cost?eur(c.unit_cost):'–'}</td>
      <td style="font-size:13px">${c.location_id?`<a href="#" onclick="openLoc(${c.location_id});return false">${esc(c.location)}</a>`:'<span class="mut">–</span>'}</td>
      <td style="font-size:13px">${c.used_in.length?c.used_in.slice(0,3).map(p=>`<a href="#" onclick="show('cat');setTimeout(()=>editProd(${p.id}),150);return false">${esc(p.name)}</a>`).join(', ')+(c.used_in.length>3?` +${c.used_in.length-3}`:''):'<span class="mut">–</span>'}</td>
      <td style="text-align:right;white-space:nowrap"><button class="btn sm" onclick="compBuy(${c.id})">+ Entrada</button> <button class="btn sec sm" onclick="compEdit(${c.id})">Editar</button></td></tr>`).join('')
    : `<tr><td class="mut">${COMPS.length ? 'Nada con ese filtro.' : 'Aún no hay componentes. Añade los muelles, tornillos, imanes… que uses.'}</td></tr>`;
}
async function compEdit(id){
  await Promise.all([ensureComps(), ensureLocs(), loadSuppliers()]);
  const c = id ? COMPS.find(x=>x.id===id) : {unit:'ud', pack_qty:1};
  const f = await form(id ? 'Editar componente' : 'Nuevo componente', [
    ...(id ? [] : [{k:'paste', label:'Pegar de Amazon o de la tienda (opcional)', placeholder:'Enlace o título: rellena nombre, precio y unidades del pack'}]),
    {k:'name', label:'Nombre', value:c.name||'', placeholder:'Tornillo M3×10 DIN912, Muelle 0,8×6×20, Imán 6×2…'},
    {k:'category', label:'Categoría', value:c.category||'', list:'comp-cats', placeholder:'Tornillería, Muelles, Imanes…', half:1},
    {k:'unit', label:'Se cuenta en', type:'select', value:c.unit, options:COMP_UNITS, half:1},
    {k:'pack_qty', label:'Cuántos trae el pack', type:'number', value:c.pack_qty??1, half:1},
    {k:'pack_price', label:'Precio del pack (€)', type:'number', value:c.pack_price??'', half:1, hint: id && c.unit_cost ? `Ahora: ${eur(c.unit_cost)} por unidad` : 'El coste por unidad sale solo.'},
    ...(id ? [] : [{k:'stock', label:'Cuántos tienes ahora', type:'number', value:'', half:1}]),
    {k:'min_stock', label:'Avisar cuando queden', type:'number', value:c.min_stock||'', half:1, placeholder:'0 = sin aviso'},
    {k:'location_id', label:'Dónde está', type:'select', value:c.location_id||'', options:locFormOpts()},
    {k:'supplier', label:'Proveedor', value:c.supplier||'', list:'sup-list', half:1},
    {k:'url', label:'Enlace de compra', value:c.url||'', placeholder:'https://…', half:1},
    {k:'notes', label:'Notas', value:c.notes||''},
    ...(id ? [{k:'active', type:'checkbox', label:'En uso (desmárcalo para ocultarlo sin perder el historial)', value:!!c.active}] : [])],
    {ok:'Guardar', extra: id ? 'Borrar' : ''});
  if (!f) return;
  if (f.__extra){ if (!await sure(`Las recetas que lo usan conservan el nombre y el coste, pero dejará de descontarse.`, {title:`¿Borrar «${c.name}»?`, ok:'Borrar', danger:1})) return;
    await api('/components/'+id,{method:'DELETE'}); toast('Borrado'); return loadComps(); }
  if (f.paste){
    const r = await api('/components/parse',{method:'POST',body:{text:f.paste}}).catch(()=>null);
    if (r){ if (!f.name) f.name = r.name||''; if (!f.pack_price && r.price) f.pack_price = r.price; if ((!f.pack_qty || f.pack_qty==='1') && r.pieces) f.pack_qty = r.pieces;
      if (!f.supplier && r.supplier) f.supplier = r.supplier; if (!f.url && /^https?:/.test(f.paste.trim())) f.url = f.paste.trim().split(/\s/)[0]; }
    delete f.paste;
    if (!f.name) return toast('No he sacado el nombre: escríbelo a mano');
  }
  if (!f.name) return toast('Ponle nombre al componente');
  f.location_id = f.location_id || null;
  if (id) await api('/components/'+id,{method:'PUT',body:f}); else await api('/components',{method:'POST',body:f});
  toast('Guardado'); loadComps();
}
async function compBuy(id){
  const c = COMPS.find(x=>x.id===id);
  const f = await form('Entrada: '+c.name, [
    {k:'packs', label:`¿Cuántos packs de ${+c.pack_qty} ${c.unit}?`, type:'number', value:'1', half:1},
    {k:'qty', label:`o unidades sueltas`, type:'number', value:'', half:1, placeholder:'—'},
    {k:'paid', label:'Pagado en total (€)', type:'number', value:c.pack_price??'', hint:'Vacío = no apuntar el gasto.', half:1},
    {k:'person', label:'¿Quién lo pagó?', type:'select', value:S.people[0]||'', options:[['','—'], ...S.people.map(x=>[x,x])], half:1},
    {k:'supplier', label:'Proveedor', value:c.supplier||'', list:'sup-list'}], {ok:'Registrar entrada'});
  if (!f) return;
  await api(`/components/${id}/stock`,{method:'POST',body:{mode:'compra', ...f}}); toast('Entrada registrada'); loadComps();
}
async function compCount(id, v, inLoc){
  const n = num(v); if (n==null || n<0) return toast('Pon un número');
  await api(`/components/${id}/stock`,{method:'POST',body:{mode:'ajuste', qty:n}}); toast('Recontado');
  await ensureComps(true); if (inLoc && LOC) openLoc(LOC.id); else cpRender();
}
async function compQuick(id, d){
  const c = (LOC?.components||[]).find(x=>x.id===id) || COMPS.find(x=>x.id===id); if (!c) return;
  await compCount(id, Math.max(0, c.stock + d), true);
}
async function openComp(id){ show('stk'); await stkTab('comp'); compEdit(id); }

// ---------- producto terminado y reposición
async function loadFinished(){
  const [rs] = await Promise.all([api('/restock'), ensureLocs(), api('/products').then(p=>PRODUCTS=p)]);
  $('#rs-list').innerHTML = rs.length ? rs.map(p=>`<div class="rs-i"><div><b>${esc(p.name)}</b><br><span class="mut" style="font-size:12.5px">hay ${p.stock||0}, mínimo ${p.min_stock}${p.making?`, ${p.making} en marcha`:''}</span></div>
      <span style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end"><button class="btn sec sm" onclick="openNeeds(${p.id}, ${p.make})">¿Qué me falta?</button><button class="btn sm" onclick="makeFor(${p.id}, ${p.make})">Fabricar ${p.make}</button></span></div>`).join('')
    : '<p class="mut" style="margin:0">Todo en orden: nada por debajo del mínimo.</p>';
  const list = PRODUCTS.slice().sort((a,b)=>a.name.localeCompare(b.name));
  $('#fp-table').innerHTML = list.length ? `<tr><th>Artículo</th><th class="n">Hay</th><th class="n">Mínimo</th><th>Dónde</th><th></th></tr>` + list.map(p=>{
      const hasV = (p.variants||[]).length;
      return `<tr><td><b>${esc(p.name)}</b>${p.kind==='conjunto'?' <span class="tag">conjunto</span>':''}${hasV?`<br><span class="mut" style="font-size:12px">${p.variants.map(v=>`${esc(v.name)} ${v.stock??'–'}`).join(' · ')}</span>`:''}</td>
      <td class="n">${hasV ? `<b>${p.stock??'–'}</b>` : `<input class="cnt-in" inputmode="numeric" value="${p.stock??''}" placeholder="—" title="Vacío = bajo pedido" onchange="finSet(${p.id},'stock',this.value)">`}</td>
      <td class="n"><input class="cnt-in" inputmode="numeric" value="${p.min_stock||''}" placeholder="0" onchange="finSet(${p.id},'min_stock',this.value)"></td>
      <td><select class="fp-loc" onchange="finSet(${p.id},'location_id',this.value)">${locOpts(p.location_id, '—')}</select></td>
      <td style="text-align:right;white-space:nowrap"><button class="btn sec sm" onclick="openNeeds(${p.id})">¿Qué me falta?</button></td></tr>`; }).join('')
    : '<tr><td class="mut">Aún no hay artículos en el catálogo.</td></tr>';
}
async function finSet(pid, k, v, inLoc){
  const val = k==='location_id' ? (v||null) : (v==='' ? (k==='stock' ? null : 0) : Math.max(0, Math.round(num(v)||0)));
  await api('/products/'+pid,{method:'PUT',body:{[k]:val}}); toast('Guardado');
  PRODUCTS = await api('/products');
  if (inLoc && LOC) openLoc(LOC.id); else if (STK_TAB==='fin' && !$('#v-stk').classList.contains('hidden')) loadFinished();
}
async function makeFor(pid, n){
  const p = PRODUCTS.find(x=>x.id===pid);
  const pv = await pickVariant(p, false, false); if (!pv) return;
  const o = await api(`/products/${pid}/make`,{method:'POST',body:{qty:n, variant_id:pv.variant?.id}});
  toast(`Pedido #${o.id} creado: al pasar a «listo» se suman ${n} al stock`); if (STK_TAB==='fin') loadFinished();
}

// ---------- ¿qué me falta para hacer N?
let NEED = {pid:null};
async function openNeeds(pid, qty){
  const p = PRODUCTS.find(x=>x.id===pid) || (await api('/products')).find(x=>x.id===pid);
  NEED = {pid, p};
  $('#nd-title').textContent = '¿Qué me falta? · ' + p.name;
  $('#nd-qty').value = qty || 1;
  const vs = p.variants||[]; $('#nd-var-w').classList.toggle('hidden', !vs.length);
  $('#nd-var').innerHTML = '<option value="">—</option>' + vs.map(v=>`<option value="${v.id}">${esc(v.name)}</option>`).join('');
  if (!$('#ndlg').open) ndlg.showModal();
  needsLoad();
}
async function needsLoad(){
  const q = Math.max(1, Math.round(num($('#nd-qty').value)||1)), v = $('#nd-var').value;
  const r = await api(`/products/${NEED.pid}/needs?qty=${q}${v?'&variant_id='+v:''}`); NEED.r = r;
  const fmt = (x, u) => u==='g'||u==='ml' ? qfmt(x, u) : `${+(+x).toFixed(3)} ${u}`;
  const row = x => `<tr class="${x.missing>0?'low':''}"><td><b>${esc(x.name)}</b>${x.location?`<br><span class="mut" style="font-size:12px">📍 ${esc(x.location)}</span>`:''}</td>
    <td class="n mut">${fmt(x.per_unit, x.unit)}</td><td class="n">${fmt(x.need, x.unit)}</td>
    <td class="n">${x.have==null?'<span class="mut">sin controlar</span>':fmt(x.have, x.unit)}</td>
    <td class="n">${x.missing==null?'–':x.missing>0?`<b class="neg">${fmt(x.missing, x.unit)}</b>`:'<span class="pos">✓</span>'}</td></tr>`;
  const mats = r.lines.filter(x=>x.type==='material'), comps = r.lines.filter(x=>x.type==='component');
  const head = '<tr><th></th><th class="n">Por unidad</th><th class="n">Hace falta</th><th class="n">Tienes</th><th class="n">Falta</th></tr>';
  $('#nd-body').innerHTML = `<div class="nd-sum ${r.ok?'ok':'ko'}">${r.ok ? `✓ Tienes todo lo controlado para hacer ${q}.` : `Te falta algo para hacer ${q}.`}${r.product.stock?` <span class="mut">(ya tienes ${r.product.stock} hechos)</span>`:''}</div>`
    + (r.pieces.length ? `<h3 class="rh">Piezas a imprimir</h3><div style="font-size:14px">${r.pieces.map(x=>`${x.need} × ${esc(x.name)}`).join(' · ')}</div>` : '')
    + (mats.length ? `<h3 class="rh">Filamento / resina</h3><table class="nocards">${head}${mats.map(row).join('')}</table>` : '')
    + (comps.length ? `<h3 class="rh">Componentes</h3><table class="nocards">${head}${comps.map(row).join('')}</table>` : '')
    + (r.untracked.length ? `<p class="mut" style="font-size:13px">Sin controlar en el almacén: ${r.untracked.map(x=>`${+x.need.toFixed(2)} × ${esc(x.name)}`).join(', ')}. Enlázalos a un componente en la receta para que se cuenten.</p>` : '')
    + (!mats.length && !comps.length && !r.pieces.length ? '<p class="mut">Este artículo no tiene receta: añade su cálculo (material) y sus componentes en el catálogo.</p>' : '');
  $('#nd-shop').disabled = r.ok;
}
async function needsShop(){
  const r = await api(`/products/${NEED.pid}/needs/shop`,{method:'POST',body:{qty:+$('#nd-qty').value||1, variant_id:$('#nd-var').value||null}});
  toast(r.added.length ? `A la compra: ${r.added.join(', ')}` : 'No falta nada'); loadShopping();
}
async function needsMake(){
  const q = Math.max(1, Math.round(num($('#nd-qty').value)||1)), v = $('#nd-var').value || null;
  if (!NEED.r?.ok && !await sure('Falta algo de lo que pide la receta. ¿Crear igualmente el pedido de fabricación?', {ok:'Fabricar igual'})) return;
  const o = await api(`/products/${NEED.pid}/make`,{method:'POST',body:{qty:q, variant_id:v}});
  ndlg.close(); toast(`Pedido #${o.id} creado: al pasar a «listo» se suman ${q} al stock`);
  if (!$('#v-stk').classList.contains('hidden') && STK_TAB==='fin') loadFinished();
}

async function homeOrg(){
  const [rs, cs] = await Promise.all([api('/restock').catch(()=>[]), api('/components').catch(()=>[])]);
  const low = cs.filter(c=>c.active && c.low);
  $('#h-org-card').classList.toggle('hidden', !rs.length && !low.length);
  $('#h-org').innerHTML = (rs.length ? `<div class="mut" style="font-size:12px;margin-bottom:4px">Para reponer</div>` + rs.slice(0,5).map(p=>`<div class="h-li"><span>🧩 <b>${esc(p.name)}</b> <span class="mut">hay ${p.stock||0} de ${p.min_stock}</span></span><button class="btn sec sm" onclick="openNeeds(${p.id}, ${p.make})">Fabricar ${p.make}</button></div>`).join('') : '')
    + (low.length ? `<div class="mut" style="font-size:12px;margin:8px 0 4px">Componentes que faltan</div>` + low.slice(0,6).map(c=>`<div class="h-li"><span>🔩 <b>${esc(c.name)}</b> <span class="mut">quedan ${+c.stock.toFixed(3)} ${esc(c.unit)}</span></span><a href="#" onclick="show('stk');stkTab('buy');return false">a la compra</a></div>`).join('') : '');
}
