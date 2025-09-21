import csv
import argparse
from pathlib import Path
import json
import shutil


def render_page(row, host: str) -> str:
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

  <section class="card">
    <h2>Проверка своего результата</h2>
    <input id="val" type="number" step="any" placeholder="Введите значение">
    <button id="btn-check">Проверить</button>
    <div id="out" class="muted"></div>
  </section>
</main>

<footer>
  <p>Теги: {tags}</p>
  <p><a href="index.html">Вернуться к списку анализов</a></p>
</footer>

<script>
document.getElementById('btn-check').addEventListener('click', function(){{
    var v = parseFloat(document.getElementById('val').value);
    var out = document.getElementById('out');
    if(isNaN(v)) {{
        out.innerHTML = '<p class="muted">Введите корректное число</p>';
        return;
    }}
    var low = parseFloat("{norm_low}".replace(/[^0-9.,-]/g, '').replace(',', '.'));
    var high = parseFloat("{norm_high}".replace(/[^0-9.,-]/g, '').replace(',', '.'));
    if(!isFinite(low) || !isFinite(high)) {{
        out.innerHTML = '<p><strong>Значение зарегистрировано: ' + v + '</strong></p>';
        return;
    }}
    if(v < low) out.innerHTML = '<p><strong>Ниже нормы.</strong> {below}</p>';
    else if(v > high) out.innerHTML = '<p><strong>Выше нормы.</strong> {above}</p>';
    else out.innerHTML = '<p><strong>В пределах нормы.</strong> {normal}</p>';
}});
</script>

</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="analyses",
        help="Выходная директория"
    )
    parser.add_argument(
        "--host",
        default="",
        help="Хост для ссылок (например, yourname.github.io/analyses)"
    )
    args = parser.parse_args()

    # директория для вывода
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # путь к data.csv относительно этого скрипта
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
            description = row["description"].strip()
            tags = [t.strip() for t in row["tags"].split(",")]

            url = f"https://{args.host}/{slug}.html" if args.host else f"{slug}.html"

            items.append({
                "slug": slug,
                "title": title,
                "summary": summary,
                "description": description,
                "tags": tags,
                "url": url
            })

            # генерируем HTML-страницу
            page_html = render_page(row, args.host)
            (outdir / f"{slug}.html").write_text(page_html, encoding="utf-8")

    # сохраняем JSON для поиска
    (outdir / "analyses.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # копируем style.css, только если он реально в другом месте
    if style_file.exists():
        dst_style = outdir / "style.css"
        if style_file.resolve() != dst_style.resolve():
            shutil.copy(style_file, dst_style)
            
    # генерируем index.html со списком анализов
    index_html = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Справочник анализов</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <h1>Справочник анализов</h1>
  <ul>
"""
    for item in items:
        index_html += f'    <li><a href="{item["slug"]}.html">{item["title"]}</a> — {item["summary"]}</li>\n'

    index_html += """  </ul>
</body>
</html>"""

    (outdir / "index.html").write_text(index_html, encoding="utf-8")


if __name__ == "__main__":
    main()

