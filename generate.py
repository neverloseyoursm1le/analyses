#!/usr/bin/env python3
# generate.py — генератор статического справочника анализов
# - Читает CSV с разделителем '|' (по умолчанию file next to script: data.csv)
# - Генерирует для каждой строки slug.html и slug/index.html
# - Генерирует index.html и analyses.json
# - Копирует style.css и script.js при наличии
# Usage:
#   python3 generate.py --csv analyses/data.csv --out analyses
#   python3 generate.py --out .            # положит файлы в текущую папку

import csv
import argparse
from pathlib import Path
import json
import shutil
import html
import sys

# ---------- Настройки / утилиты ----------
def slugify(s: str) -> str:
    if not s:
        return "item"
    s = str(s).strip().lower()
    # простая очистка: оставить a-z0-9-_.
    out = []
    for ch in s:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch.isspace():
            out.append("-")
        # остальные отбрасываем
    res = "".join(out).strip("-")
    return res or "item"

def safe(v):
    return "" if v is None else str(v)

# ---------- Шаблоны ----------
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

    <p class="muted">Теги: {tags}</p>
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
  <section class="results-grid">
{cards}
  </section>
</main>
<footer class="site-footer"><div class="container"><small>© Справочник анализов</small></div></footer>
<script src="script.js"></script>
</body>
</html>
"""

# ---------- Основная логика ----------
def main():
    parser = argparse.ArgumentParser(description="Генератор статического справочника анализов (CSV -> HTML)")
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

    # читаем CSV
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="|")
        # проверка заголовков
        headers = reader.fieldnames or []
        required = {"slug","title","summary","description","norm_low","norm_mid","norm_high","below","normal","above","prep","tags"}
        missing = required - set([h.strip() for h in headers])
        if missing:
            print("WARNING: CSV header doesn't contain all expected fields. Missing:", missing)
            # но всё равно попробуем: будем брать доступные поля

        for i, row in enumerate(reader, start=1):
            if not row:
                continue
            slug_raw = safe(row.get("slug")) or safe(row.get("id")) or safe(row.get("name"))
            slug = slugify(slug_raw)
            if not slug:
                print(f"Skip row #{i}: empty slug/name", file=sys.stderr)
                continue

            title = safe(row.get("title")) or slug
            summary = safe(row.get("summary")) or ""
            description = safe(row.get("description")) or summary
            norm_low = safe(row.get("norm_low")) or ""
            norm_mid = safe(row.get("norm_mid")) or ""
            norm_high = safe(row.get("norm_high")) or ""
            below = safe(row.get("below")) or ""
            normal = safe(row.get("normal")) or ""
            above = safe(row.get("above")) or ""
            prep = safe(row.get("prep")) or ""
            tags_raw = safe(row.get("tags")) or ""
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

            # подготовка данных (escape для безопасности HTML)
            ctx = {
                "title": html.escape(title),
                "summary": html.escape(summary),
                "description": html.escape(description).replace("\n","<br>"),
                "norm_low": html.escape(norm_low),
                "norm_mid": html.escape(norm_mid),
                "norm_high": html.escape(norm_high),
                "below": html.escape(below),
                "normal": html.escape(normal),
                "above": html.escape(above),
                "prep": html.escape(prep),
                "tags": html.escape(tags_raw)
            }

            # формируем HTML
            root_html = PAGE_ROOT_TEMPLATE.format(**ctx)
            folder_html = PAGE_FOLDER_TEMPLATE.format(**ctx)

            # записываем root slug.html (например analyses/glucose.html)
            out_root_file = outdir / f"{slug}.html"
            out_root_file.write_text(root_html, encoding="utf-8")
            # записываем folder index (например analyses/glucose/index.html)
            page_dir = outdir / slug
            page_dir.mkdir(parents=True, exist_ok=True)
            (page_dir / "index.html").write_text(folder_html, encoding="utf-8")

            items.append({
                "slug": slug,
                "title": title,
                "summary": summary,
                "url": f"{slug}/",
                "tags": tags_list
            })
            generated += 1
            print(f"[{i}] generated: {out_root_file}  and {page_dir/'index.html'}")

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

        # copy static assets (style/script)
        if style_src.exists():
            dst = (outdir / "style.css").resolve()
            src = style_src.resolve()
            if src != dst:
                shutil.copy(src, dst)
                print("Copied style.css ->", dst)
            else:
                print("style.css already in output folder; skipped copy")
        else:
            print("style.css not found next to script; pages may look unstyled.")

        if script_src.exists():
            dst = (outdir / "script.js").resolve()
            src = script_src.resolve()
            if src != dst:
                shutil.copy(src, dst)
                print("Copied script.js ->", dst)
            else:
                print("script.js already in output folder; skipped copy")
        else:
            # создаём пустой script.js чтобы не ждать 404 в консоли
            (outdir / "script.js").write_text("// optional site script\n", encoding="utf-8")
            print("Created placeholder script.js in output.")

        print(f"Generation complete: {generated} pages -> {outdir.resolve()}")

if __name__ == "__main__":
    main()
