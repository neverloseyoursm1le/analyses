// script.js — search + checker
document.addEventListener('DOMContentLoaded', () => {
  try {
    if (document.getElementById('search')) initSearch();
    if (document.getElementById('checker')) initChecker();
  } catch (e) {
    console.error(e);
  }
});

/* ================== SEARCH (index) ================== */
async function initSearch(){
  let list = [];
  try {
    const r = await fetch('analyses.json', {cache:'no-store'});
    if (!r.ok) throw new Error('analyses.json not found');
    list = await r.json();
  } catch (e) {
    console.error('Failed to load analyses.json', e);
    document.getElementById('results').innerHTML = '<p class="muted">Список недоступен</p>';
    return;
  }

  const input = document.getElementById('search');
  const clear = document.getElementById('clear');
  const tagsRoot = document.getElementById('tags');
  const resultsRoot = document.getElementById('results');

  function renderCards(arr){
    resultsRoot.innerHTML = '';
    if (arr.length === 0) {
      resultsRoot.innerHTML = '<p class="muted">Ничего не найдено</p>';
      return;
    }
    arr.forEach(a => {
      const el = document.createElement('a');
      el.className = 'card';
      el.href = a.url;
      el.innerHTML = `<h3>${escapeHtml(a.title)}</h3><p class="muted">${escapeHtml(a.summary)}</p><p class="meta">${(a.tags||[]).slice(0,6).join(', ')}</p>`;
      resultsRoot.appendChild(el);
    });
  }

  function renderTags(){
    const map = {};
    list.forEach(a => (a.tags||[]).forEach(t => map[t] = (map[t]||0)+1));
    const sorted = Object.keys(map).sort((x,y)=>map[y]-map[x]).slice(0,24);
    tagsRoot.innerHTML = '';
    sorted.forEach(t=>{
      const b = document.createElement('button'); b.className='tag'; b.textContent=t;
      b.addEventListener('click', ()=>{ input.value = t; doSearch(); });
      tagsRoot.appendChild(b);
    });
  }

  function doSearch(){
    const q = input.value.trim().toLowerCase();
    if (q.length < 2){ renderCards(list); return; }
    const filtered = list.filter(a => ( (a.title||'') + ' ' + (a.summary||'') + ' ' + (a.tags||[]).join(' ') ).toLowerCase().includes(q));
    renderCards(filtered);
  }

  input.addEventListener('input', debounce(doSearch, 150));
  clear.addEventListener('click', ()=>{ input.value=''; doSearch(); });
  renderTags();
  renderCards(list);
}

/* ================== CHECKER (per-page) ================== */
function initChecker(){
  const root = document.getElementById('checker');
  if(!root) return;
  const btn = document.getElementById('btn-check');
  const input = document.getElementById('val');
  const out = document.getElementById('out');

  // read dataset
  const midMin = tryParseFloat(root.dataset.midMin);
  const midMax = tryParseFloat(root.dataset.midMax);
  const lowVal = tryParseFloat(root.dataset.low);
  const highVal = tryParseFloat(root.dataset.high);
  const normLow = root.dataset.normLow || '';
  const normMid = root.dataset.normMid || '';
  const normHigh = root.dataset.normHigh || '';
  const textBelow = root.dataset.below || '';
  const textNormal = root.dataset.normal || '';
  const textAbove = root.dataset.above || '';

  btn.addEventListener('click', ()=> doCheck(input.value));
  input.addEventListener('keydown', (e)=>{ if(e.key === 'Enter') doCheck(input.value); });

  function doCheck(raw){
    const vTrim = String(raw || '').trim();
    if(vTrim === ''){
      out.innerHTML = '<p class="muted">Введите значение</p>';
      out.className = 'checker-out muted';
      return;
    }
    // try numeric
    const num = parseFloat(vTrim.replace(',', '.'));
    if(!isNaN(num)){
      const res = evaluateNumeric(num, midMin, midMax, lowVal, highVal, normLow, normMid, normHigh);
      showResultNumeric(res, num);
    } else {
      // categorical/textual
      const res = evaluateTextual(vTrim.toLowerCase(), textBelow, textNormal, textAbove, normLow, normMid, normHigh);
      showResultTextual(res, vTrim);
    }
  }

  function evaluateNumeric(num, midMin, midMax, lowVal, highVal, normLowRaw, normMidRaw, normHighRaw){
    // priority: if mid range available -> use it
    if(isFinite(midMin) && isFinite(midMax)){
      if(num < midMin) return {cat:'below', text: textBelow};
      if(num > midMax) return {cat:'above', text: textAbove};
      return {cat:'normal', text: textNormal};
    }

    // if both low and high numeric thresholds available
    if(isFinite(lowVal) && isFinite(highVal)){
      if(num < lowVal) return {cat:'below', text: textBelow};
      if(num > highVal) return {cat:'above', text: textAbove};
      return {cat:'normal', text: textNormal};
    }

    // if low bound only (<x) was provided
    if(isFinite(lowVal)){
      if(normLowRaw && normLowRaw.trim().startsWith('<')){
        if(num < lowVal) return {cat:'below', text: textBelow};
        return {cat:'normal', text: textNormal || 'Вне диапазонов — обратитесь к врачу для уточнения.'};
      }
    }

    // if high bound only (>x)
    if(isFinite(highVal)){
      if(normHighRaw && normHighRaw.trim().startsWith('>')){
        if(num > highVal) return {cat:'above', text: textAbove};
        return {cat:'normal', text: textNormal || 'Вне диапазонов — обратитесь к врачу для уточнения.'};
      }
    }

    // fallback: cannot classify
    return {cat:'unknown', text: 'Не удалось автоматически классифицировать значение. Уточните у врача.'};
  }

  function evaluateTextual(inputLower, textBelow, textNormal, textAbove, normLowRaw, normMidRaw, normHighRaw){
    // common words detection
    if(inputLower.includes('полож')) {
      // positive
      // if normal contains отриц -> positive means abnormal
      if(textNormal.toLowerCase().includes('отриц')) return {cat:'above', text:textAbove || 'Положительный результат — обратитесь к врачу.'};
      return {cat:'above', text: textAbove || 'Положительный результат — возможное отклонение.'};
    }
    if(inputLower.includes('отриц') || inputLower.includes('нет') || inputLower.includes('-негат')) {
      return {cat:'normal', text: textNormal || 'Результат в пределах нормы.'};
    }
    // exact match against provided normal/below/above words
    if(textNormal && inputLower.includes(textNormal.toLowerCase())) return {cat:'normal', text: textNormal};
    if(textBelow && inputLower.includes(textBelow.toLowerCase())) return {cat:'below', text: textBelow};
    if(textAbove && inputLower.includes(textAbove.toLowerCase())) return {cat:'above', text: textAbove};

    return {cat:'unknown', text: 'Не удалось автоматически классифицировать текстовый результат. Уточните у врача.'};
  }

  function showResultNumeric(res, num){
    if(res.cat === 'below'){
      out.innerHTML = `<div class="status status-low">Ниже нормы (введено: ${num})</div><p>${escapeHtml(res.text)}</p>`;
      out.className = 'checker-out status-low';
    } else if(res.cat === 'above'){
      out.innerHTML = `<div class="status status-high">Выше нормы (введено: ${num})</div><p>${escapeHtml(res.text)}</p>`;
      out.className = 'checker-out status-high';
    } else if(res.cat === 'normal'){
      out.innerHTML = `<div class="status status-normal">В пределах нормы (введено: ${num})</div><p>${escapeHtml(res.text)}</p>`;
      out.className = 'checker-out status-normal';
    } else {
      out.innerHTML = `<div class="status status-unknown">Невозможно определить</div><p>${escapeHtml(res.text)}</p>`;
      out.className = 'checker-out status-unknown';
    }
  }

  function showResultTextual(res, raw){
    if(res.cat === 'below'){
      out.innerHTML = `<div class="status status-low">Интерпретация: возможное отклонение</div><p>Введено: ${escapeHtml(raw)} — ${escapeHtml(res.text)}</p>`;
      out.className = 'checker-out status-low';
    } else if(res.cat === 'above'){
      out.innerHTML = `<div class="status status-high">Интерпретация: возможное отклонение</div><p>Введено: ${escapeHtml(raw)} — ${escapeHtml(res.text)}</p>`;
      out.className = 'checker-out status-high';
    } else if(res.cat === 'normal'){
      out.innerHTML = `<div class="status status-normal">В пределах нормы</div><p>Введено: ${escapeHtml(raw)} — ${escapeHtml(res.text)}</p>`;
      out.className = 'checker-out status-normal';
    } else {
      out.innerHTML = `<div class="status status-unknown">Невозможно автоматически классифицировать</div><p>Введено: ${escapeHtml(raw)} — ${escapeHtml(res.text)}</p>`;
      out.className = 'checker-out status-unknown';
    }
  }

  function tryParseFloat(v){
    const n = parseFloat(String(v || '').replace(',', '.'));
    return isNaN(n) ? NaN : n;
  }

  function isFinite(v){ return typeof v === 'number' && !Number.isNaN(v) && Number.isFinite(v); }

  function escapeHtml(s){
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function debounce(f, t){ let to=null; return (...a)=>{ clearTimeout(to); to=setTimeout(()=>f(...a), t); }; }
}
