import csv, json, os, sys

def main():
    outdir = sys.argv[sys.argv.index("--out")+1] if "--out" in sys.argv else "analyses"
    host = sys.argv[sys.argv.index("--host")+1] if "--host" in sys.argv else ""

    os.makedirs(outdir, exist_ok=True)

    analyses = []
    with open("analyses/data.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug = row["slug"].strip()
            title = row["title"].strip()
            summary = row.get("summary","").strip()
            tags = [t.strip() for t in row.get("tags","").split(",") if t.strip()]
            nl = row.get("norm_low","").strip()
            nh = row.get("norm_high","").strip()
            below = row.get("below","").strip()
            above = row.get("above","").strip()
            normal = row.get("normal","").strip()

            url = f"{host}/{outdir}/{slug}.html" if host else f"{outdir}/{slug}.html"

            analyses.append({
                "slug": slug,
                "title": title,
                "summary": summary,
                "tags": tags,
                "url": url
            })

            # генерируем HTML-страницу
            html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>{title} – Анализы</title>
  <link rel="stylesheet" href="../style.css">
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <p>{summary}</p>

    <div class="card">
      <h3>Проверка значения</h3>
      <label for="val">Введите число:</label>
      <input id="val" type="number" placeholder="Введите значение">
      <button id="btn-check">Проверить</button>
      <div id="out" class="result-box"></div>
    </div>

    <div class="card">
      <h3>Нормальные значения</h3>
      <table>
        <tr><th>Ниже нормы (&lt;{nl})</th><td>{below}</td></tr>
        <tr><th>Норма ({nl}–{nh})</th><td>{normal}</td></tr>
        <tr><th>Выше нормы (&gt;{nh})</th><td>{above}</td></tr>
      </table>
    </div>
  </div>

  <script>
    function check(){{
        var v = parseFloat(document.getElementById('val').value);
        var out = document.getElementById('out');
        if(isNaN(v)){{ out.innerHTML = '<p class="muted">Введите корректное число</p>'; return; }}
        var low = {nl or 'NaN'}, high = {nh or 'NaN'};
        if(!isFinite(low) || !isFinite(high)){{ out.innerHTML = '<p><strong>Значение: '+v+'</strong></p>'; return; }}
        if(v < low) out.innerHTML = '<p><strong>Ниже нормы.</strong></p><p>{below}</p>';
        else if(v > high) out.innerHTML = '<p><strong>Выше нормы.</strong></p><p>{above}</p>';
        else out.innerHTML = '<p><strong>В пределах нормы.</strong></p><p>{normal}</p>';
    }}
    document.addEventListener('DOMContentLoaded', function(){{
        document.getElementById('btn-check').addEventListener('click', check);
    }});
  </script>
</body>
</html>
"""
            with open(os.path.join(outdir, f"{slug}.html"), "w", encoding="utf-8") as f2:
                f2.write(html)

    # сохраняем JSON для главной страницы
    with open(os.path.join(outdir, "analyses.json"), "w", encoding="utf-8") as f:
        json.dump(analyses, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
