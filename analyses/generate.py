#!/usr/bin/env python3
# generate.py
# Usage:
#   python3 generate.py --csv analyses/data.csv --out analyses/site --base /USERNAME/REPO/analyses
import csv, os, re, json, argparse, html

parser = argparse.ArgumentParser()
parser.add_argument('--csv', default='analyses/data.csv', help='CSV input (delimiter |)')
parser.add_argument('--out', default='analyses/site', help='Output site directory')
parser.add_argument('--base', default='', help='Optional base path for URLs (e.g. /repo/analyses)')
args = parser.parse_args()

CSV = args.csv
OUT = args.out.rstrip('/')
BASE = args.base.rstrip('/')

os.makedirs(OUT, exist_ok=True)
PAGES_DIR = os.path.join(OUT, 'pages')
os.makedirs(PAGES_DIR, exist_ok=True)

# Safe slug
def slugify(s):
    s = (s or '').strip().lower()
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9\-а-яё]', '', s, flags=re.IGNORECASE)
    s = re.sub(r'-+', '-', s).strip('-')
    return s or 'item'

# Try to extract numeric min/max from normal_range (like "3.9–6.1" or "3.9-6.1")
num_re_range = re.compile(r'(\d+(?:[.,]\d+)?)\s*[–\-]\s*(\d+(?:[.,]\d+)?)')
num_re_first = re.compile(r'(\d+(?:[.,]\d+)?)')

def parse_bounds(normal_field):
    if not normal_field:
        return None, None
    s = str(normal_field)
    m = num_re_range.search(s)
    if m:
        a = float(m.group(1).replace(',', '.'))
        b = float(m.group(2).replace(',', '.'))
        return a, b
    # try first two numbers
    nums = num_re_first.findall(s)
    if len(nums) >= 2:
        return float(nums[0].replace(',', '.')), float(nums[1].replace(',', '.'))
    # if single number, treat as exact (low==high)
    if nums:
        v = float(nums[0].replace(',', '.'))
        return v, v
    return None, None

# Read CSV with delimiter '|'
rows = []
with open(CSV, encoding='utf-8') as f:
    # support pipes and detect if file uses pipes; user CSV uses '|'
    reader = csv.DictReader(f, delimiter='|')
    for r in reader:
        rows.append(r)

# Build analyses JSON entries and per-page HTML
analyses_json = []

# Basic templates for index/css/js are created below
for r in rows:
    # Expected CSV columns (as per your file):
    # slug|title|summary|meta?|below_range|normal_range|above_range|below_text|normal_text|above_text|preparation|tags
    slug = slugify(r.get('slug') or r.get('id') or r.get('glucose') or r.get('title') or r.get('0'))
    title = r.get('title') or r.get('0') or slug
    summary = r.get('summary') or r.get('description') or ''
    below_range = r.get('below_range') or r.get('4') or ''
    normal_range = r.get('normal_range') or r.get('5') or ''
    above_range = r.get('above_range') or r.get('6') or ''
    below_text = r.get('below_text') or r.get('7') or ''
    normal_text = r.get('normal_text') or r.get('8') or ''
    above_text = r.get('above_text') or r.get('9') or ''
    preparation = r.get('preparation') or r.get('10') or ''
    tags = r.get('tags') or r.get('11') or ''
    tags_list = [t.strip() for t in re.split('[,|;]', tags) if t.strip()]

    nl, nh = parse_bounds(normal_range)
    nl_js = 'null' if nl is None else repr(nl)
    nh_js = 'null' if nh is None else repr(nh)

    # page url
    page_rel = f'pages/{slug}.html'
    page_url = (BASE + '/' + page_rel).lstrip('/') if BASE else page_rel

    analyses_json.append({
        'slug': slug,
        'title': title,
        'summary': summary,
        'tags': tags_list,
        'url': page_rel
    })

    # create per-page HTML
    # escape texts for HTML body
    esc = lambda s: html.escape(s or '')
    page_html = f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{esc(title)} — Справочник анализов</title>
<meta name="description" content="{esc(summary)}"/>
<link rel="stylesheet" href="../style.css"/>
</head>
<body>
<header class="page-header">
  <div class="container">
    <a class="back" href="../index.html">← Вернуться</a>
    <h1>{esc(title)}</h1>
    <p class="lead">{esc(summary)}</p>
  </div>
</header>

<main class="container">
  <article class="card">
    <h2>Краткая информация</h2>
    <p>{esc(summary)}</p>

    <h3>Нормы</h3>
    <table class="ranges-table">
      <thead><tr><th>Диапазон</th><th>Описание</th></tr></thead>
      <tbody>
        <tr><td><strong>Ниже</strong><div class="small">{esc(below_range)}</div></td><td>{esc(below_text)}</td></tr>
        <tr><td><strong>Норма</strong><div class="small">{esc(normal_range)}</div></td><td>{esc(normal_text)}</td></tr>
        <tr><td><strong>Выше</strong><div class="small">{esc(above_range)}</div></td><td>{esc(above_text)}</td></tr>
      </tbody>
    </table>

    <h3>Проверка результата</h3>
    <div id="calculator" class="calc">
      <label>Ввести значение: <input id="val" type="number" step="any" placeholder="Например, 5.2"></label>
      <button id="btn-check">Проверить</button>
      <div id="out" class="calc-result"></div>
    </div>

    <h3>Подготовка к сдаче</h3>
    <p>{esc(preparation)}</p>

    <p class="muted">Теги: {esc(tags)}</p>
  </article>
</main>

<script>
(function(){
  var btn = document.getElementById('btn-check');
  var out = document.getElementById('out');
  var nl = {nl_js};
  var nh = {nh_js};
  var txtBelow = {json_below};
  var txtNorm = {json_norm};
  var txtAbove = {json_above};

  btn.addEventListener('click', function(){
    var v = parseFloat(document.getElementById('val').value);
    if(isNaN(v)){ out.innerHTML = '<p class="muted">Введите корректное числовое значение</p>'; return; }
    if(nl === null || nh === null){ out.innerHTML = '<p><strong>Значение зарегистрировано: '+v+'</strong></p>'; return; }
    if(v < nl) out.innerHTML = '<p><strong>Ниже нормы.</strong></p><p>'+txtBelow+'</p>';
    else if(v > nh) out.innerHTML = '<p><strong>Выше нормы.</strong></p><p>'+txtAbove+'</p>';
    else out.innerHTML = '<p><strong>В пределах нормы.</strong></p><p>'+txtNorm+'</p>';
  });
})();
</script>

</body>
</html>'''.format(
        # The .format is only for safety of braces, but we already used f-strings; ensure JSON strings inserted below
    )

    # We must insert JSON-escaped texts (we'll write the file using safe replacement)
    # Build JSON-escaped strings:
    j_below = json.dumps(below_text or '')
    j_norm = json.dumps(normal_text or '')
    j_above = json.dumps(above_text or '')

    # Now replace placeholders {json_below} etc manually
    page_html = page_html.replace('var txtBelow = {json_below};', f'var txtBelow = {j_below};')
    page_html = page_html.replace('var txtNorm = {json_norm};', f'var txtNorm = {j_norm};')
    page_html = page_html.replace('var txtAbove = {json_above};', f'var txtAbove = {j_above};')

    # ensure nl_js/nh_js are inserted
    page_html = page_html.replace('{nl_js}', nl_js)
    page_html = page_html.replace('{nh_js}', nh_js)

    # write file
    with open(os.path.join(PAGES_DIR, slug + '.html'), 'w', encoding='utf-8') as fo:
        fo.write(page_html)

# write analyses.json
with open(os.path.join(OUT, 'analyses.json'), 'w', encoding='utf-8') as fo:
    json.dump(analyses_json, fo, ensure_ascii=False, indent=2)

# write index.html, style.css, script.js into OUT
index_html = '''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Справочник анализов</title>
<meta name="description" content="Справочник по лабораторным анализам: нормы, подготовка, интерактивная проверка."/>
<link rel="stylesheet" href="style.css"/>
</head>
<body>
<header class="site-header">
  <div class="container">
    <h1>Справочник анализов</h1>
    <p class="lead">Нормы, расшифровка и быстрые проверки — удобно и понятно.</p>
  </div>
</header>

<main class="container">
  <section class="search-panel">
    <div class="search-wrap">
      <input id="search" type="search" placeholder="Например: глюкоза, гемоглобин, холестерин" aria-label="Поиск по анализам"/>
      <button id="clear">Очистить</button>
    </div>
    <div id="info" class="info-row">Загрузка списка анализов…</div>
  </section>

  <section id="tags" class="tags-row"></section>
  <section id="results" class="results-grid" aria-live="polite"></section>

  <section id="debug" class="debug" style="display:none"></section>
</main>

<footer class="site-footer"><div class="container"><small>© Справочник анализов — информация справочная.</small></div></footer>

<script src="script.js"></script>
</body>
</html>
'''

style_css = '''
:root{--maxw:1100px;--accent:#1e6ef3;--muted:#6b7280;--bg:#f6f8fb;--card:#ffffff;--radius:12px;--border:#e6eef8}
*{box-sizing:border-box}
body{font-family:Inter,system-ui,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:#0f1724;margin:0;line-height:1.45}
.container{max-width:var(--maxw);margin:20px auto;padding:0 16px}
.site-header{background:linear-gradient(90deg,var(--accent),#0b57d0);color:#fff;padding:28px;border-radius:12px;margin:8px 0}
.site-header h1{margin:0;font-size:26px}
.site-header .lead{opacity:.95;margin-top:8px}
.search-panel{margin-top:18px}
.search-wrap{display:flex;gap:8px;align-items:center;background:var(--card);border:2px solid var(--border);padding:10px;border-radius:12px}
#search{flex:1;padding:12px;border:1px solid #e9f0ff;border-radius:8px;font-size:16px;outline:none}
#clear{background:transparent;border:1px solid var(--border);padding:8px 12px;border-radius:8px;cursor:pointer}
.info-row{margin-top:10px;color:var(--muted);font-size:14px}
.tags-row{margin:18px 0;display:flex;flex-wrap:wrap;gap:8px}
.tag{background:#eef6ff;color:var(--accent);padding:8px 12px;border-radius:999px;font-size:13px;border:1px solid #d6e8ff;cursor:pointer}
.results-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-top:10px}
.card{background:var(--card);padding:16px;border-radius:12px;border:1px solid var(--border);text-decoration:none;color:inherit;display:block;box-shadow:0 6px 18px rgba(2,6,23,0.04);transition:transform .14s,box-shadow .14s}
.card:hover{transform:translateY(-6px);box-shadow:0 14px 40px rgba(2,6,23,0.08)}
.card h3{margin:0 0 6px 0;color:var(--accent);font-size:18px}
.card p{margin:6px 0;color:#344054;font-size:14px}
.muted{color:var(--muted)}
.debug{margin-top:14px;padding:10px;background:#fff;border-radius:10px;border:1px dashed #e8eefc;color:#0b1220;font-size:13px}
.site-footer{margin-top:26px;padding:20px 0;text-align:center;color:var(--muted);font-size:13px}
.ranges-table{width:100%;border-collapse:collapse;margin-top:12px}
.ranges-table th,.ranges-table td{padding:10px;border:1px solid #eef2f7;text-align:left}
.ranges-table thead{background:#f1f5ff;color:var(--accent)}
.calc{margin-top:12px}
.calc input{padding:8px;border:1px solid #e6eef8;border-radius:8px;width:200px}
.calc-result{margin-top:10px;padding:8px;border-radius:8px;background:#f8fafc;border:1px solid #eef2f7}
.small{font-size:13px;color:var(--muted);margin-top:6px}
@media(max-width:720px){.site-header h1{font-size:20px}}
'''

# script.js loads analyses.json and renders search/tags/cards
script_js = '''
// script.js — loads analyses.json, renders list, search and tags
(async function(){
  const infoEl = document.getElementById('info');
  const debugEl = document.getElementById('debug');
  const resultsEl = document.getElementById('results');
  const tagsEl = document.getElementById('tags');
  const searchInput = document.getElementById('search');
  const clearBtn = document.getElementById('clear');

  function id(n){ return document.getElementById(n); }
  function escapeHtml(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  async function load(){
    try{
      const r = await fetch('analyses.json', {cache:'no-store'});
      if(!r.ok) throw new Error('analyses.json not found: '+r.status);
      const data = await r.json();
      return data;
    }catch(e){
      debugEl.style.display = 'block';
      debugEl.setAttribute('aria-hidden','false');
      debugEl.textContent = 'Error loading analyses.json: ' + e;
      return [];
    }
  }

  const list = await load();
  if(!list || list.length===0){
    infoEl.textContent = 'Список недоступен';
    resultsEl.innerHTML = '<p class="muted">Список недоступен</p>';
    return;
  }

  infoEl.textContent = 'Загружено ' + list.length + ' анализов';

  function createCard(a){
    const el = document.createElement('a');
    el.className = 'card';
    el.href = a.url;
    el.innerHTML = '<h3>' + escapeHtml(a.title) + '</h3><p class="muted">' + escapeHtml(a.summary) + '</p><div class="muted small">Теги: ' + (a.tags||[]).slice(0,6).map(escapeHtml).join(', ') + '</div>';
    return el;
  }

  function renderAll(){
    resultsEl.innerHTML = '';
    list.forEach(a => resultsEl.appendChild(createCard(a)));
  }

  function renderTags(){
    const map = {};
    list.forEach(a => (a.tags||[]).forEach(t => map[t] = (map[t]||0) + 1));
    const tags = Object.keys(map).sort((x,y)=>map[y]-map[x]).slice(0,30);
    tagsEl.innerHTML = '';
    tags.forEach(t => {
      const btn = document.createElement('button');
      btn.className = 'tag';
      btn.textContent = t + ' (' + map[t] + ')';
      btn.addEventListener('click', () => {
        searchInput.value = t;
        searchInput.dispatchEvent(new Event('input'));
      });
      tagsEl.appendChild(btn);
    });
  }

  function doSearch(q){
    const ql = (q||'').trim().toLowerCase();
    if(ql.length < 2){
      renderAll(); infoEl.textContent = 'Загружено ' + list.length + ' анализов'; return;
    }
    const filtered = list.filter(a => (a.title +' '+ a.summary +' '+ (a.tags||[]).join(' ')).toLowerCase().indexOf(ql) !== -1);
    resultsEl.innerHTML = '';
    if(filtered.length === 0) resultsEl.innerHTML = '<p class="muted">Ничего не найдено</p>';
    else filtered.forEach(it => resultsEl.appendChild(createCard(it)));
    infoEl.textContent = 'Найдено ' + filtered.length + ' результатов по «' + q + '»';
  }

  const deb = (fn,ms=180)=>{ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; };
  searchInput.addEventListener('input', deb(e=>doSearch(e.target.value), 180));
  clearBtn && clearBtn.addEventListener('click', ()=>{ searchInput.value=''; searchInput.dispatchEvent(new Event('input')); });

  renderTags();
  renderAll();
})();
'''

# write core files
with open(os.path.join(OUT,'index.html'), 'w', encoding='utf-8') as f:
    f.write(index_html)
with open(os.path.join(OUT,'style.css'), 'w', encoding='utf-8') as f:
    f.write(style_css)
with open(os.path.join(OUT,'script.js'), 'w', encoding='utf-8') as f:
    f.write(script_js)

print('Site generation complete. Output folder:', OUT)
print('Pages written:', len(rows))
