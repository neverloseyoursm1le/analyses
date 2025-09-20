// script.js — фронтенд: загрузка data.csv, поиск, теги
async function loadAnalyses() {
  try {
    const r = await fetch('data.csv', { cache: 'no-store' });
    if (!r.ok) throw new Error('data.csv not found');
    const text = await r.text();

    // Парсим CSV -> массив объектов
    const lines = text.trim().split('\n');
    const headers = lines.shift().split(',');
    return lines.map(line => {
      const cols = line.split(',');
      const obj = {};
      headers.forEach((h, i) => obj[h.trim()] = (cols[i] || '').trim());
      return {
        title: obj.title,
        summary: obj.summary,
        tags: obj.tags ? obj.tags.split('|').map(t => t.trim()) : [],
        url: obj.url,
        slug: obj.slug || obj.title.toLowerCase().replace(/\s+/g, '-')
      };
    });
  } catch (e) {
    console.error(e);
    return [];
  }
}

function createCard(a) {
  const el = document.createElement('a');
  el.className = 'card';
  el.href = a.url;
  el.innerHTML = `
    <h3>${a.title}</h3>
    <p class="muted">${a.summary}</p>
    <p style="margin-top:8px" class="muted">
      Теги: ${(a.tags || []).slice(0, 6).join(', ')}
    </p>`;
  return el;
}

function renderTags(list) {
  const map = {};
  list.forEach(a => (a.tags || []).forEach(t => map[t] = (map[t] || 0) + 1));
  const sorted = Object.keys(map).sort((x, y) => map[y] - map[x]).slice(0, 24);
  const root = document.getElementById('tags');
  root.innerHTML = '';
  sorted.forEach(t => {
    const b = document.createElement('button');
    b.className = 'tag';
    b.textContent = t;
    b.addEventListener('click', () => {
      document.getElementById('search').value = t;
      document.getElementById('search').dispatchEvent(new Event('input'));
    });
    root.appendChild(b);
  });
}

function renderAll(list) {
  const root = document.getElementById('results');
  root.innerHTML = '';
  list.forEach(a => root.appendChild(createCard(a)));
}

function searchAndRender(list, q) {
  const ql = q.trim().toLowerCase();
  if (ql.length < 2) { renderAll(list); return; }
  const filtered = list.filter(a =>
    (a.title + ' ' + a.summary + ' ' + (a.tags || []).join(' '))
      .toLowerCase()
      .includes(ql)
  );
  const root = document.getElementById('results');
  root.innerHTML = '';
  if (filtered.length === 0) {
    root.innerHTML = '<p class="muted">Ничего не найдено</p>';
    return;
  }
  filtered.forEach(a => root.appendChild(createCard(a)));
}

document.addEventListener('DOMContentLoaded', async () => {
  const list = await loadAnalyses();
  if (!list || list.length === 0) {
    document.getElementById('results').innerHTML = '<p class="muted">Список недоступен</p>';
    return;
  }
  renderTags(list);
  renderAll(list);
  const input = document.getElementById('search');
  input.addEventListener('input', () => searchAndRender(list, input.value));
});
