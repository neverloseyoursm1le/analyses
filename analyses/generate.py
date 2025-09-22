import csv
import argparse
from pathlib import Path
import json
import shutil


def render_page(row) -> str:
    """Генерация HTML-страницы для одного анализа"""
    slug = row["slug"].strip()
    title = row["title"].strip()
    summary = row["summary"].strip()
    description = row["description"].strip()
    norm_low = row["norm_low"].strip()
    norm_mid = row["norm_mid"].strip()
    norm_high = row["norm_high"].strip()
    below = row["below"].strip()
    normal = row["normal"].strip()
    above = row["above"].strip()
    prep = row["prep"].strip()
    tags = row["tags"].strip()

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Справочник анализов</title>
  <meta name="description" content="{summary}">
  <link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>{title}</h1>
  <p class="muted">{summary}</p>
  <nav><a href="index.html">← Назад к списку</a></nav>
</header>

<main>
  <section class="card">
    <h2>Описание</h2>
    <p>{description}</p>
  </section>

  <section class="card">
    <h2>Нормы и отклонения</h2>
    <table>
      <thead>
        <tr><th>Значение</th><th>Интерпретация</th></tr>
      </thead>
      <tbody>
        <tr><td>{norm_low}</td><td>{below}</td></tr>
        <tr><td>{norm_mid}</td><td>{normal}</td></tr>
        <tr><td>{norm_high}</td><td>{above}</td></tr>
      </tbody>
    </table>
  </section>

  <section class="card">
    <h2>Подготовка</h2>
    <p>{prep}</p>
  </section>
</main>

<footer>
  <p>Теги: {tags}</p>
  <p><a href="index.html">Вернуться к списку анализов</a></p>
</footer>
</body>
</html>
"""


def render_index(items):
    """Генерация списка всех анализов"""
    cards = "\n".join(
        f"""<a class="card" href="{item['slug']}.html">
            <h3>{item['title']}</h3>
            <p>{item['summary']}</p>
            <div class="meta">{", ".join(item['tags'])}</div>
        </a>"""
        for item in items
    )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Справочник анализов</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">
  <h1>Справочник анализов</h1>
  <p class="lead">Выберите нужный анализ, чтобы узнать подробности</p>
</header>

<main class="container">
  <div class="results-grid">
    {cards}
  </div>
</main>

<footer class="site-footer">
  <p>© 2025 — Все права защищены</p>
</footer>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="analyses", help="Выходная директория")
    args = parser.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    data_file = script_dir / "data.csv"
    style_file = script_dir / "style.css"

    items = []
    with data_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            slug = row["slug"].strip()
            title = row["title"].strip()
            summary = row["summary"].strip()
            tags = [t.strip() for t in row["tags"].split(",")]

            items.append({
                "slug": slug,
                "title": title,
                "summary": summary,
                "tags": tags
            })

            # создаём отдельную страницу
            page_html = render_page(row)
            (outdir / f"{slug}.html").write_text(page_html, encoding="utf-8")

    # создаём index.html
    index_html = render_index(items)
    (outdir / "index.html").write_text(index_html, encoding="utf-8")

    # копируем style.css (если он есть)
    if style_file.exists() and style_file.resolve() != (outdir / "style.css").resolve():
        shutil.copy(style_file, outdir / "style.css")


if __name__ == "__main__":
    main()
