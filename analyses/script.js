const data = [
  // Здесь будут данные, сгенерированные из CSV через generate.py
  // пример для отладки:
  {
    slug: "glucose",
    title: "Глюкоза (натощак)",
    summary: "Ключевой тест для диагностики диабета.",
    description: "Глюкоза натощак: норма и отклонения.",
    norm_low: "<3.9",
    norm_mid: "3.9–6.1",
    norm_high: ">7.0",
    below: "Гипогликемия: слабость, потливость, головокружение.",
    normal: "В пределах нормы.",
    above: "Высокий уровень — риск преддиабета/диабета, нужна консультация врача.",
    prep: "Натощак 8–12 ч; избегать сладкого и алкоголя перед сдачей.",
    tags: ["глюкоза","диабет","nat"]
  }
];

const params = new URLSearchParams(window.location.search);
const slug = params.get("a");
const container = document.getElementById("cards-container");

if (slug) {
  // Страница конкретного анализа
  const analysis = data.find(d => d.slug === slug);
  if (analysis) {
    document.body.innerHTML = `
      <div class="analysis-container">
        <h2>${analysis.title}</h2>
        <p>${analysis.description}</p>
        <h3>Нормы:</h3>
        <ul>
          <li>Низкий уровень: ${analysis.norm_low}</li>
          <li>Норма: ${analysis.norm_mid}</li>
          <li>Высокий уровень: ${analysis.norm_high}</li>
        </ul>
        <div class="value-check">
          <input type="number" id="value-input" placeholder="Введите значение">
          <button onclick="checkValue()">Проверить</button>
        </div>
        <div id="result"></div>
        <h3>Подготовка:</h3>
        <p>${analysis.prep}</p>
        <p><a href="index.html">← Назад к списку</a></p>
      </div>
    `;

    window.checkValue = () => {
      const val = parseFloat(document.getElementById("value-input").value);
      const res = document.getElementById("result");
      if (isNaN(val)) {
        res.textContent = "Введите корректное число.";
        res.className = "result";
        return;
      }
      if (val < parseFloat(analysis.norm_low.replace("<",""))) {
        res.textContent = analysis.below;
        res.className = "result low";
      } else if (val > parseFloat(analysis.norm_high.replace(">",""))) {
        res.textContent = analysis.above;
        res.className = "result high";
      } else {
        res.textContent = analysis.normal;
        res.className = "result normal";
      }
    };
  }
} else {
  // Главная страница со списком анализов
  function renderCards(items) {
    container.innerHTML = "";
    items.forEach(d => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `<h2>${d.title}</h2><p>${d.summary}</p>`;
      card.onclick = () => { window.location.href = `?a=${d.slug}`; };
      container.appendChild(card);
    });
  }

  renderCards(data);

  document.getElementById("search-input").addEventListener("input", e => {
    const q = e.target.value.toLowerCase();
    const filtered = data.filter(d =>
      d.title.toLowerCase().includes(q) ||
      d.tags.some(tag => tag.toLowerCase().includes(q))
    );
    renderCards(filtered);
  });
}
