#!/usr/bin/env python3
# generate.py — генерирует статический сайт из analyses/data.csv
# Требует: data.csv (разделитель |) рядом с этим скриптом; style.css и script.js опционально.
import csv
import argparse
from pathlib import Path
import json
import shutil
import re
import html
from typing import Optional

# ---------- Утилиты ----------
def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    # заменить пробелы на тире, удалить неподходящие символы
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9\-]', '', s, flags=re.IGNORECASE)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s or 'item'

def first_field(row, candidates, default=''):
    for c in candidates:
        if c in row and row[c] is not None and str(row[c]).strip() != '':
            return str(row[c]).strip()
    return default

# Попытка извлечь числовные границы из строки вида "3.9–6.1", "3.9-6.1", "<3.9" и т.п.
def parse_bounds(s: str) -> (Optional[float], Optional[float]):
    if not s:
        return None, None
    s = str(s)
    # сначала ищем диапазон "a-b" или "a–b"
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*[–\-]\s*(\d+(?:[.,]\d+)?)', s)
    if m:
        a = float(m.group(1).replace(',', '.'))
        b = float(m.group(2).replace(',', '.'))
        return a, b
    # если есть два числа в тексте, возьмём первые два
    nums = re.findall(r'(\d+(?:[.,]\d+)?)', s)
    if len(nums) >= 2:
        return float(nums[0].replace(',', '.')), float(nums[1].replace(',', '.'))
    # если одно число — применим как обе границы (точное значение)
    if len(nums) == 1:
        v = float(nums[0].replace(',', '.'))
        return v, v
    return None, None

# ---------- Шаблоны ----------
INDEX_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Справочник анализов</title>
  <meta name="description" content="Справочник лабораторных анализов — нормы, расшифровки, быстрые проверки.">
  <link rel="stylesheet" href="style.css">
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
      <div class="info-row">Список анализов:</div>
    </section>
    <section class="results-grid">
{items}
    </section>
  </main>
  <footer class="site-footer"><div class="container"><small>© Справочник анализов</small></div></footer>
  <script src="script.js" defer></script>
</body>
</html>
"""

PAGE_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} — Справочник анализов</title>
  <meta name="description" content="{summary}">
  <link rel="stylesheet" href="../style.css">
</head>
<body>
  <header>
    <div class="container">
      <a href="../index.html">← Вернуться к списку</a>
      <h1>{title}</h1>
      <p class="muted">{summary}</p>
    </div>
  </header>

  <main class="container">
    <article class="card">
      <h2>Описание</h2>
      <p>{description}</p>

      <h3>Нормы</h3>
      <table class="ranges-table">
        <thead><tr><th>Диапазон</th><th>Интерпретация</th></tr></thead>
        <tbody>
          <tr><td>Ниже: <div class="small">{norm_low}</div></td><td>{below}</td></tr>
          <tr><td>Норма: <div class="small">{norm_mid}</div></td><td>{normal}</td></tr>
          <tr><td>Выше: <div class="small">{norm_high}</div></td><td>{above}</td></tr>
        </tbody>
      </table>

      <h3>Проверка результата</h3>
      <div id="calculator" class="calc">
        <label>Ввести значение: <input id="val" type="number" step="any" placeholder="Например, 5.2"></label>
        <button id="btn-check">Проверить</button>
        <div id="out" class="calc-result"></div>
      </div>

      <h3>Подготовка</h3>
      <p>{prep}</p>

      <p class="muted">Теги: {tags}</p>
    </article>
  </main>

<script>
(function(){{
  var nl = {nl_js};
  var nh = {nh_js};
  var txtBelow = {j_below};
  var txtNorm = {j_norm};
  var txtAbove = {j_above};

  document.getElementById('btn-check').addEventListener('click', function(){{
    var v = parseFloat(document.getElementById('val').value);
    var out = document.getElementById('out');
    if(isNaN(v)){{ out.innerHTML = '<p class="muted">Введите корректное число</p>'; return; }}
    if(nl === null || nh === null){{ out.innerHTML = '<p><strong>Значение зарегистрировано: ' + v + '</strong></p>'; return; }}
    if(v < nl) out.innerHTML = '<p><strong>Ниже нормы.</strong></p><p>' + txtBelow + '</p>';
    else if(v > nh) out.innerHTML = '<p><strong>Выше нормы.</strong></p><p>' + txtAbove + '</p>';
    else out.innerHTML = '<p><strong>В пределах нормы.</strong></p><p>' + txtNorm + '</p>';
  }});
}})();
</script>
</body>
</html>
"""

REDIRECT_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={folder}/">
  <link rel="canonical" href="{folder}/">
  <title>Перенаправление</title>
</head>
<body>
  <p>Перенаправление на <a href="{folder}/">{folder}/</a></p>
</body>
</html>
"""

# ---------- Главная логика ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=None, help="CSV файл (по умолчанию: data.csv рядом со скриптом)")
    parser.add_argument("--out", default="site", help="Выходная директория для сайта")
    parser.add_argument("--host", default="", help="Хост (опционально) — не обязательно для работы")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    csv_path = Path(args.csv) if args.csv else (script_dir / "data.csv")
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    style_file = script_dir / "style.css"
    script_file = script_dir / "script.js"

    if not csv_path.exists():
        print(f"ERROR: CSV-файл не найден: {csv_path}")
        return

    items = []
    used_slugs = set()

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter='|')
        for i, row in enumerate(reader):
            # безопасно получить поля с разными возможными названиями
            title = first_field(row, ['title','name','название'], default=f'item-{i}')
            summary = first_field(row, ['summary','brief','description','кратко'], default='')
            description = first_field(row, ['description','desc','details'], default=summary)
            # поля с нормами - разрешаем несколько возможных имён
            norm_low = first_field(row, ['norm_low','normal_low','below_range','below'], default=first_field(row, ['4','below_range'], ''))
            norm_mid = first_field(row, ['norm_mid','normal_range','normal','normal_mid'], default=first_field(row, ['5','normal_range'], ''))
            norm_high = first_field(row, ['norm_high','normal_high','above_range','above'], default=first_field(row, ['6','above_range'], ''))
            below = first_field(row, ['below_text','below','desc_below'], default=first_field(row, ['7'], ''))
            normal = first_field(row, ['normal_text','normal','desc_normal'], default=first_field(row, ['8'], ''))
            above = first_field(row, ['above_text','above','desc_above'], default=first_field(row, ['9'], ''))
            prep = first_field(row, ['preparation','prep','подготовка'], default=first_field(row, ['10'], ''))
            tags_raw = first_field(row, ['tags','keywords'], default=first_field(row, ['11'], ''))
            tags_list = [t.strip() for t in re.split('[,|;]', tags_raw) if t.strip()]

            # slug
            raw_slug = first_field(row, ['slug','id'], default='') or slugify(title)
            slug = slugify(raw_slug)
            # ensure unique
            if slug in used_slugs:
                suffix = 2
                while f"{slug}-{suffix}" in used_slugs:
                    suffix += 1
                slug = f"{slug}-{suffix}"
            used_slugs.add(slug)

            # numeric bounds for JS
            nl, nh = parse_bounds(norm_mid or norm_low or norm_high)
            nl_js = 'null' if nl is None else repr(nl)
            nh_js = 'null' if nh is None else repr(nh)

            # safe JSON strings for insertion into JS
            j_below = json.dumps(below or '', ensure_ascii=False)
            j_norm = json.dumps(normal or '', ensure_ascii=False)
            j_above = json.dumps(above or '', ensure_ascii=False)

            # prepare page HTML (page will sit in outdir/slug/index.html)
            page_html = PAGE_TEMPLATE.format(
                title=html.escape(title),
                summary=html.escape(summary),
                description=html.escape(description),
                norm_low=html.escape(norm_low),
                norm_mid=html.escape(norm_mid),
                norm_high=html.escape(norm_high),
                below=html.escape(below),
                normal=html.escape(normal),
                above=html.escape(above),
                prep=html.escape(prep),
                tags=html.escape(tags_raw),
                nl_js=nl_js,
                nh_js=nh_js,
                j_below=j_below,
                j_norm=j_norm,
                j_above=j_above
            )

            # write folder + index.html
            page_dir = outdir / slug
            page_dir.mkdir(parents=True, exist_ok=True)
            (page_dir / "index.html").write_text(page_html, encoding="utf-8")

            # write redirect slug.html that points to slug/
            redirect_html = REDIRECT_TEMPLATE.format(folder=slug)
            (outdir / f"{slug}.html").write_text(redirect_html, encoding="utf-8")

            # add to items list (url relative)
            items.append({
                "slug": slug,
                "title": title,
                "summary": summary,
                "url": f"{slug}/",
                "tags": tags_list
            })

            print(f"Generated: {slug}/index.html")

    # generate index.html list
    items_html = ""
    for it in items:
        # item card in index
        items_html += f'      <a class="card" href="{it["url"]}"><h3>{html.escape(it["title"])}</h3><p class="muted">{html.escape(it["summary"])}</p></a>\n'

    index_content = INDEX_TEMPLATE.format(items=items_html)
    (outdir / "index.html").write_text(index_content, encoding="utf-8")
    print("Generated: index.html")

    # write analyses.json
    (outdir / "analyses.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Generated: analyses.json")

    # copy static assets: style.css, script.js — но не копировать сам в себя
    if style_file.exists():
        dst_style = (outdir / "style.css").resolve()
        src_style = style_file.resolve()
        if src_style != dst_style:
            shutil.copy(src_style, dst_style)
            print("Copied style.css")
        else:
            print("style.css already in output; skip copying")

    if script_file.exists():
        dst_script = (outdir / "script.js").resolve()
        src_script = script_file.resolve()
        if src_script != dst_script:
            shutil.copy(src_script, dst_script)
            print("Copied script.js")
        else:
            print("script.js already in output; skip copying")

    print("Site generation complete. Output folder:", outdir.resolve())


if __name__ == "__main__":
    main()
