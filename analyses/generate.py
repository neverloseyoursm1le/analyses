#!/usr/bin/env python3
# generate.py — генерирует страницы в analyses/pages/ по analyses/data.csv
import csv, os, html, argparse

parser = argparse.ArgumentParser()
parser.add_argument('--csv', default='analyses/data.csv')
parser.add_argument('--out', default='analyses')
parser.add_argument('--host', default='')
args = parser.parse_args()

CSV = args.csv
OUT_DIR = args.out
PAGES_DIR = os.path.join(OUT_DIR, 'pages')
os.makedirs(PAGES_DIR, exist_ok=True)

def safe_slug(s):
    return ''.join(c if c.isalnum() else '-' for c in (s or '').lower()).strip('-')

with open("data.csv", encoding="utf-8") as f:
    reader = csv.reader(f, delimiter="|")

    # detect delimiter automatically
    sample = f.read(4096)
    f.seek(0)
    dialect = csv.Sniffer().sniff(sample, delimiters=',|;')
    reader = csv.DictReader(f, dialect=dialect)
    rows = list(reader)

for row in rows:
    title = row.get('title') or row.get('name') or row.get('название') or ''
    summary = row.get('summary') or row.get('desc') or row.get('description') or ''
    tags = row.get('tags') or row.get('keywords') or ''
    slug = (row.get('slug') or row.get('id') or safe_slug(title)) or 'item'
    url = row.get('url') or f'pages/{slug}.html'
    # optional fields:
    norm_low = row.get('norm_low','')
    norm_high = row.get('norm_high','')
    unit = row.get('unit','')
    below = row.get('below_text','Ниже нормы — см. врача.')
    normal = row.get('normal_text','В пределах нормы.')
    above = row.get('above_text','Выше нормы — см. врача.')

    page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{html.escape(title)} — Справочник анализов</title>
<meta name="description" content="{html.escape(summary)}"/>
<link rel="stylesheet" href="../style.css"/>
</head>
<body>
  <header class="site-header"><div class="container"><h1>{html.escape(title)}</h1><p class="lead">{html.escape(summary)}</p></div></header>
  <main class="container">
    <article class="card">
      <h2>Кратко</h2>
      <p>{html.escape(summary)}</p>

      <h2>Норма</h2>
      <p>{html.escape(norm_low)} {html.escape(unit)} — {html.escape(norm_high)} {html.escape(unit)}</p>

      <h2>Таблица</h2>
      <table class="ranges-table">
        <thead><tr><th>Диапазон</th><th>Категория</th><th>Описание</th></tr></thead>
        <tbody>
          <tr><td>ниже нормы</td><td>Ниже</td><td>{html.escape(below)}</td></tr>
          <tr><td>в норме</td><td>Норма</td><td>{html.escape(normal)}</td></tr>
          <tr><td>выше нормы</td><td>Выше</td><td>{html.escape(above)}</td></tr>
        </tbody>
      </table>

      <h2>Проверить результат</h2>
      <label>Ввести значение: <input id="val" type="number" step="any" /></label>
      <button onclick="check()">Проверить</button>
      <div id="out" class="calc-result"></div>

      <p class="muted">Теги: {html.escape(tags)}</p>
    </article>

    <nav class="card"><a href="../index.html">← Вернуться</a></nav>
  </main>

  <script>
  function check(){
    var v = parseFloat(document.getElementById('val').value);
    var out = document.getElementById('out');
    if(isNaN(v)){ out.innerHTML = '<p class="muted">Введите корректное число</p>'; return; }
    var low = {nl}, high = {nh};
    // fallback: if no numeric norms provided, just say checked
    if(!isFinite(low) || !isFinite(high)){ out.innerHTML = '<p><strong>Значение зарегистрировано: '+v+'</strong></p>'; return; }
    if(v < low) out.innerHTML = '<p><strong>Ниже нормы.</strong></p><p>{b}</p>';
    else if(v > high) out.innerHTML = '<p><strong>Выше нормы.</strong></p><p>{a}</p>';
    else out.innerHTML = '<p><strong>В пределах нормы.</strong></p><p>{n}</p>';
  }
  </script>

</body>
</html>""".replace('{nl}', str(norm_low or 'NaN')).replace('{nh}', str(norm_high or 'NaN')).replace('{b}', html.escape(below)).replace('{n}', html.escape(normal)).replace('{a}', html.escape(above))

    out_path = os.path.join(PAGES_DIR, f"{slug}.html")
    with open(out_path, 'w', encoding='utf-8') as of:
        of.write(page)
    print('Wrote', out_path)

print('Generation finished.')
