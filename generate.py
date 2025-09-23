#!/usr/bin/env python3
import csv
import argparse
from pathlib import Path
import json
import shutil
import html
import re
import sys

def slugify(s: str) -> str:
    if not s:
        return "item"
    s = str(s).strip().lower()
    out = []
    for ch in s:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch.isspace():
            out.append("-")
    res = "".join(out).strip("-")
    return res or "item"

def parse_number(s: str):
    if not s:
        return None
    m = re.search(r'(-?\d+[.,]?\d*)', s)
    if not m:
        return None
    try:
        return float(m.group(1).replace(',', '.'))
    except:
        return None

def parse_range(s: str):
    if not s:
        return (None, None)
    m = re.search(r'(-?\d+[.,]?\d*)\s*[–\-]\s*(-?\d+[.,]?\d*)', s)
    if m:
        try:
            a = float(m.group(1).replace(',', '.'))
            b = float(m.group(2).replace(',', '.'))
            return (min(a,b), max(a,b))
        except:
            return (None, None)
    return (None, None)

PAGE_ROOT_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Справочник анализов</title>
<meta name="description" content="{summary}">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header"><div class="container"><h1>{title}</h1><p class="muted">{summary}</p></div></header>
<main class="container">
  <article class="card">
    <h2>Описание</h2>
    <p>{description}</p>

    <h3>Нормы и интерпретация</h3>
    <table>
      <thead><tr><th>Диапазон</th><th>Интерпретация</th></tr></thead>
      <tbody>
        <tr><td>{norm_low}</td><td>{below}</td></tr>
        <tr><td>{norm_mid}</td><td>{normal}</td></tr>
        <tr><td>{norm_high}</td><td>{above}</td></tr>
      </tbody>
    </table>

    <h3>Подготовка</h3>
    <p>{prep}</p>

    <div id="checker" class="checker"
      data-mid-min="{mid_min}"
      data-mid-max="{mid_max}"
      data-low="{low_val}"
      data-high="{high_val}"
      data-norm-low="{norm_low_attr}"
      data-norm-mid="{norm_mid_attr}"
      data-norm-high="{norm_high_attr}"
      data-below="{below_attr}"
      data-normal="{normal_attr}"
      data-above="{above_attr}"
      >
      <label for="val">Проверить своё значение</label>
      <div class="checker-input">
        <input id="val" type="text" placeholder="Введите число (без единиц) или текст (положительный/отрицательный)">
        <button id="btn-check">Проверить</button>
      </div>
      <div id="out" class="checker-out muted"></div>
    </div>

    <p class="muted">Теги: {tags}</p>
    <p><a href="index.html">← Назад к списку</a></p>
  </article>
</main>
<script src="script.js"></script>
</body>
</html>
"""

PAGE_FOLDER_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Справочник анализов</title>
<meta name="description" content="{summary}">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header class="site-header"><div class="container"><a href="../index.html">← Назад к списку</a><h1>{title}</h1><p class="muted">{summary}</p></div></header>
<main class="container">
  <article class="card">
    <h2>Описание</h2>
    <p>{description}</p>

    <h3>Нормы и интерпретация</h3>
    <table>
      <thead><tr><th>Диапазон</th><th>Интерпретация</th></tr></thead>
      <tbody>
        <tr><td>{norm_low}</td><td>{below}</td></tr>
        <tr><td>{norm_mid}</td><td>{normal}</td></tr>
        <tr><td>{norm_high}</td><td>{above}</td></tr>
      </tbody>
    </table>

    <h3>Подготовка</h3>
    <p>{prep}</p>

    <div id="checker" class="checker"
      data-mid-min="{mid_min}"
      data-mid-max="{mid_max}"
      data-low="{low_val}"
      data-high="{high_val}"
      data-norm-low="{norm_low_attr}"
      data-norm-mid="{norm_mid_attr}"
      data-norm-high="{norm_high_attr}"
      data-below="{below_attr}"
      data-normal="{normal_attr}"
      data-above="{above_attr}"
      >
      <label for="val">Проверить своё значение</label>
      <div class="checker-input">
        <input id="val" type="text" placeholder="Введите число (без единиц) или текст (положительный/отрицательный)">
        <button id="btn-check">Проверить</button>
      </div>
      <div id="out" class="checker-out muted"></div>
    </div>

  </article>
</main>
<script src="../script.js"></script>
</body>
</html>
"""

INDEX_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Справочник анализов</title>
<meta name="description" content="Справочник лабораторных анализов — нормы, что значит 'ниже/выше нормы', подготовка.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header"><div class="container"><h1>Справочник анализов</h1><p class="lead">Найдите анализ и проверьте результат</p></div></header>
<main class="container">
  <div class="search-panel">
    <div class="search-wrap">
      <input id="search" placeholder="Поиск: название, тег или симптом">
      <button id="clear">Очистить</button>
    </div>
    <div id="tags" class="tags-row"></div>
  </div>

  <section id="results" class="results-grid">
    <!-- cards will be rendered by script.js -->
  </section>
</main>
<footer class="site-footer"><div class="container"><small>© Справочник анализов</small></div></footer>
<script src="script.js"></script>
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(description="Генератор справочника (CSV -> HTML)")
    parser.add_argument("--csv", default=None, help="Путь к CSV (по умолчанию: data.csv рядом со скриптом)")
    parser.add_argument("--out", default="analyses", help="Папка вывода")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    csv_path = Path(args.csv) if args.csv else (script_dir / "data.csv")
    outdir = Path(args.out)

    print("Script dir:", script_dir)
    print("CSV path:", csv_path)
    print("Output dir:", outdir)

    if not csv_path.exists():
        print("ERROR: CSV not found:", csv_path, file=sys.stderr)
        sys.exit(2)

    outdir.mkdir(parents=True, exist_ok=True)

    style_src = script_dir / "style.css"
    script_src = script_dir / "script.js"

    items = []
    generated = 0

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="|")
        headers = reader.fieldnames or []
        for i, row in enumerate(reader, start=1):
            if not row:
                continue
            slug_raw = (row.get("slug") or row.get("id") or row.get("name") or "").strip()
            slug = slugify(slug_raw)
            if not slug:
                print(f"Skip row #{i}: empty slug", file=sys.stderr)
                continue

            title = (row.get("title") or "").strip()
            summary = (row.get("summary") or "").strip()
            description = (row.get("description") or "").strip()
            norm_low = (row.get("norm_low") or "").strip()
            norm_mid = (row.get("norm_mid") or "").strip()
            norm_high = (row.get("norm_high") or "").strip()
            below = (row.get("below") or "").strip()
            normal = (row.get("normal") or "").strip()
            above = (row.get("above") or "").strip()
            prep = (row.get("prep") or "").strip()
            tags_raw = (row.get("tags") or "").strip()
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

            # parse numeric thresholds when possible
            mid_min, mid_max = parse_range(norm_mid)
            low_val = parse_number(norm_low)
            high_val = parse_number(norm_high)

            ctx = {
                "title": html.escape(title),
                "summary": html.escape(summary),
                "description": html.escape(description).replace("\n", "<br>"),
                "norm_low": html.escape(norm_low),
                "norm_mid": html.escape(norm_mid),
                "norm_high": html.escape(norm_high),
                "below": html.escape(below),
                "normal": html.escape(normal),
                "above": html.escape(above),
                "prep": html.escape(prep),
                "tags": html.escape(tags_raw),
                "mid_min": str(mid_min) if mid_min is not None else "",
                "mid_max": str(mid_max) if mid_max is not None else "",
                "low_val": str(low_val) if low_val is not None else "",
                "high_val": str(high_val) if high_val is not None else "",
                "norm_low_attr": html.escape(norm_low, quote=True),
                "norm_mid_attr": html.escape(norm_mid, quote=True),
                "norm_high_attr": html.escape(norm_high, quote=True),
                "below_attr": html.escape(below, quote=True),
                "normal_attr": html.escape(normal, quote=True),
                "above_attr": html.escape(above, quote=True)
            }

            # write slug.html and slug/index.html
            root_html = PAGE_ROOT_TEMPLATE.format(**ctx)
            (outdir / f"{slug}.html").write_text(root_html, encoding="utf-8")

            page_dir = outdir / slug
            page_dir.mkdir(parents=True, exist_ok=True)
            folder_html = PAGE_FOLDER_TEMPLATE.format(**ctx)
            (page_dir / "index.html").write_text(folder_html, encoding="utf-8")

            items.append({
                "slug": slug,
                "title": title,
                "summary": summary,
                "url": f"{slug}/",
                "tags": tags_list
            })
            generated += 1
            print(f"[{i}] generated: {outdir / (slug + '.html')} and {page_dir / 'index.html'}")

    if generated == 0:
        print("WARNING: No rows processed from CSV. Aborting (no pages generated).", file=sys.stderr)
    else:
        # index
        cards_html = ""
        for it in items:
            title_esc = html.escape(it["title"])
            summ_esc = html.escape(it["summary"])
            tags_str = ", ".join(it["tags"])
            cards_html += f'<a class="card" href="{it["url"]}"><h3>{title_esc}</h3><p class="muted">{summ_esc}</p><p class="meta">{html.escape(tags_str)}</p></a>\n'

        index_html = INDEX_TEMPLATE.format(cards=cards_html)
        (outdir / "index.html").write_text(index_html, encoding="utf-8")
        (outdir / "analyses.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

        # copy static assets
        if style_src.exists():
            dst = (outdir / "style.css").resolve()
            src = style_src.resolve()
            if src != dst:
                shutil.copy(src, dst)
                print("Copied style.css ->", dst)
        else:
            print("style.css not found next to script; pages may look unstyled.")

        if script_src.exists():
            dst = (outdir / "script.js").resolve()
            src = script_src.resolve()
            if src != dst:
                shutil.copy(src, dst)
                print("Copied script.js ->", dst)
        else:
            (outdir / "script.js").write_text("// placeholder\n", encoding="utf-8")
            print("Created placeholder script.js in output.")

        print(f"Generation complete: {generated} pages -> {outdir.resolve()}")

if __name__ == "__main__":
    main()
