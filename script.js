// script.js — загрузка data.csv, парсинг, поиск, рендер
(async function(){
  const infoEl = id('info');
  const debugEl = id('debug');
  const resultsEl = id('results');
  const tagsEl = id('tags');
  const searchInput = id('search');
  const clearBtn = id('clear');

  // helper
  function id(n){ return document.getElementById(n); }

  // build absolute URL to data.csv relative to current index.html
  const dataUrl = new URL('data.csv', location.href).href;

  infoEl.textContent = 'Подгружаю список анализов…';

  // robust CSV parser: supports quoted fields with delimiter detection
  function parseCSV(text){
    // detect delimiter by first non-empty line
    const linesRaw = text.split(/\r\n|\n/);
    let i = 0;
    while(i < linesRaw.length && linesRaw[i].trim()==='') i++;
    if(i >= linesRaw.length) return [];
    const headerLine = linesRaw[i];
    let delim = ',';
    const pipeCount = (headerLine.match(/\|/g)||[]).length;
    const commaCount = (headerLine.match(/,/g)||[]).length;
    const semicolonCount = (headerLine.match(/;/g)||[]).length;
    if(pipeCount > commaCount && pipeCount >= semicolonCount) delim='|';
    else if(semicolonCount > commaCount && semicolonCount > pipeCount) delim=';';
    else delim = ',';

    // state machine parse to handle quotes
    const rows = [];
    let cur = '', row = [];
    let inQuotes = false;
    for(let idx = i; idx < linesRaw.length; idx++){
      const line = linesRaw[idx];
      // if not inQuotes we can try to parse by characters including adding newline at end
      let j = 0;
      while(j < line.length){
        const ch = line[j];
        if(inQuotes){
          if(ch === '"'){
            if(line[j+1] === '"'){ cur += '"'; j += 2; continue; }
            else { inQuotes = false; j++; continue; }
          } else {
            cur += ch; j++; continue;
          }
        } else {
          if(ch === '"'){ inQuotes = true; j++; continue; }
          if(ch === delim){
            row.push(cur); cur = ''; j++; continue;
          }
          cur += ch; j++; continue;
        }
      }
      // line ended
      if(inQuotes){
        // keep a newline inside quoted field
        cur += '\n';
        // continue to next physical line
      } else {
        // end of row
        row.push(cur);
        rows.push(row.map(s=>s.trim()));
        row = []; cur = '';
      }
    }
    // if something left
    if((cur !== '') || (row.length>0)){
      row.push(cur);
      rows.push(row.map(s=>s.trim()));
    }
    return { rows, delim };
  }

  // load file
  async function loadData(){
    try {
      const r = await fetch(dataUrl, { cache: 'no-store' });
      if(!r.ok){
        throw new Error(`HTTP ${r.status} ${r.statusText} — ${dataUrl}`);
      }
      const text = await r.text();
      const parsed = parseCSV(text);
      if(!parsed || !parsed.rows || parsed.rows.length===0) return { error: 'CSV пуст или некорректен' };
      const rows = parsed.rows;
      const header = rows.shift().map(h=>h.toString().trim().toLowerCase());
      const items = rows.map(cols=>{
        const obj = {};
        for(let i=0;i<header.length;i++){
          obj[header[i]] = (cols[i]!==undefined) ? cols[i] : '';
        }
        // normalize fields: title, summary, tags, slug, url
        const title = obj.title || obj.name || obj['название'] || obj['title_ru'] || '';
        const summary = obj.summary || obj.desc || obj.description || obj['кратко'] || '';
        const tagsRaw = obj.tags || obj.keywords || obj.tags_list || '';
        const tags = tagsRaw ? tagsRaw.split(/[,|;]/).map(s=>s.trim()).filter(Boolean) : [];
        const slug = (obj.slug || obj.id || title).toString().trim().toLowerCase().replace(/\s+/g,'-').replace(/[^a-z0-9\-а-яё]/ig,'');
        const url = (obj.url && obj.url.trim()!=='') ? obj.url.trim() : `pages/${encodeURIComponent(slug)}.html`;
        return { title: title || slug, summary, tags, slug, url, raw: obj };
      });
      return { items, header };
    } catch (e) {
      return { error: String(e) };
    }
  }

  // render helpers
  function createCard(a){
    const aEl = document.createElement('a');
    aEl.className = 'card';
    aEl.href = a.url;
    aEl.innerHTML = `<h3>${escapeHtml(a.title)}</h3>
      <p class="muted">${escapeHtml(a.summary || '')}</p>
      <div class="meta muted">Теги: ${(a.tags||[]).slice(0,6).map(escapeHtml).join(', ')}</div>`;
    return aEl;
  }
  function escapeHtml(s){ return (s+'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  // debounce helper
  function debounce(fn, ms=200){
    let t;
    return (...args)=>{ clearTimeout(t); t = setTimeout(()=>fn(...args), ms); };
  }

  // main flow
  const loaded = await loadData();
  if(loaded.error){
    infoEl.textContent = 'Ошибка загрузки: ' + loaded.error;
    debugEl.style.display = 'block';
    debugEl.setAttribute('aria-hidden','false');
    debugEl.innerText = `DEBUG: tried to fetch: ${dataUrl}\nError: ${loaded.error}\nУбедитесь, что файл data.csv находится в той же папке, что и index.html (analyses/data.csv).`;
    return;
  }

  const list = loaded.items || [];
  infoEl.textContent = `Загружено ${list.length} анализов.`;
  debugEl.style.display = 'none';
  renderTags(list);
  renderAll(list);

  // search
  function doSearch(q){
    const ql = (q||'').trim().toLowerCase();
    if(ql.length < 2){
      renderAll(list); infoEl.textContent = `Загружено ${list.length} анализов.`; return;
    }
    const filtered = list.filter(a => ((a.title+' '+a.summary+' '+(a.tags||[]).join(' ')).toLowerCase().indexOf(ql) !== -1));
    resultsEl.innerHTML = '';
    if(filtered.length === 0){
      resultsEl.innerHTML = '<p class="muted">Ничего не найдено</p>';
    } else {
      filtered.forEach(it => resultsEl.appendChild(createCard(it)));
    }
    infoEl.textContent = `Найдено ${filtered.length} результатов по «${q}»`;
  }
  const debounced = debounce(e => doSearch(e.target.value), 180);
  searchInput.addEventListener('input', debounced);
  clearBtn && clearBtn.addEventListener('click', ()=>{ searchInput.value = ''; searchInput.dispatchEvent(new Event('input')); });

  // render helpers
  function renderAll(arr){
    resultsEl.innerHTML = '';
    arr.forEach(a => resultsEl.appendChild(createCard(a)));
  }

  function renderTags(arr){
    const counts = {};
    arr.forEach(it => (it.tags||[]).forEach(t => counts[t] = (counts[t]||0)+1));
    const tags = Object.keys(counts).sort((a,b)=>counts[b]-counts[a]).slice(0,30);
    tagsEl.innerHTML = '';
    tags.forEach(t=>{
      const btn = document.createElement('button');
      btn.className = 'tag';
      btn.textContent = `${t} (${counts[t]})`;
      btn.addEventListener('click', ()=>{ searchInput.value = t; searchInput.dispatchEvent(new Event('input')); });
      tagsEl.appendChild(btn);
    });
  }
})();
