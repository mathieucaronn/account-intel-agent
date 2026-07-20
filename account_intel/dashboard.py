"""Collecte la presse par client suivi et génère un dashboard HTML statique,
régénéré automatiquement (voir .github/workflows/refresh-dashboard.yml)."""

import html
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import search

LABELS = {
    "fr": {
        "title": "Account Intelligence",
        "subtitle": "Revue de presse par compte, sources grand public uniquement",
        "generated": "Actualisé automatiquement le {date}.",
        "no_press": "Aucun article trouvé dans les grands médias suivis pour cette entreprise.",
        "press_error": "Recherche presse indisponible : {error}",
        "no_clients": "Aucun client suivi. Ajoutez-en dans clients.json ou lancez avec des noms d'entreprise en argument.",
        "source": "Lire l'article",
        "search_placeholder": "Rechercher une entreprise...",
        "search_button": "Rechercher",
        "search_loading": "Recherche en cours...",
        "search_unavailable": "Recherche indisponible sur cette page statique : lancez `python -m account_intel --serve` en local pour l'activer.",
    },
    "en": {
        "title": "Account Intelligence",
        "subtitle": "Per-account press review, major outlets only",
        "generated": "Automatically refreshed on {date}.",
        "no_press": "No articles found in tracked major outlets for this company.",
        "press_error": "Press search unavailable: {error}",
        "no_clients": "No tracked clients. Add some in clients.json or run with company names as arguments.",
        "source": "Read article",
        "search_placeholder": "Search for a company...",
        "search_button": "Search",
        "search_loading": "Searching...",
        "search_unavailable": "Search unavailable on this static page: run `python -m account_intel --serve` locally to enable it.",
    },
}


@dataclass
class ClientData:
    name: str
    press: list = field(default_factory=list)
    press_error: str = None


def collect_client(tavily_client: search.TavilyClient, client_name: str, lang: str) -> ClientData:
    data = ClientData(name=client_name)
    try:
        data.press = search.collect_press(tavily_client, client_name, lang)
    except search.SearchError as exc:
        data.press_error = str(exc)
    return data


def render_html(clients_data: list, lang: str) -> str:
    labels = LABELS[lang]
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not clients_data:
        panels_html = f'<p class="empty">{html.escape(labels["no_clients"])}</p>'
        tabs_html = ""
    else:
        tabs_html = "\n".join(
            f'<button class="tab{" active" if i == 0 else ""}" '
            f'onclick="showClient({i})">{html.escape(c.name)}</button>'
            for i, c in enumerate(clients_data)
        )
        panels_html = "\n".join(
            _render_panel(c, i, labels) for i, c in enumerate(clients_data)
        )

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(labels['title'])}</title>
<style>{_CSS}</style>
</head>
<body
  data-search-loading="{html.escape(labels['search_loading'])}"
  data-search-unavailable="{html.escape(labels['search_unavailable'])}"
>
<header>
  <div class="header-inner">
    <div class="brand">
      <span class="brand-mark"></span>
      <div>
        <h1>{html.escape(labels['title'])}</h1>
        <p class="subtitle">{html.escape(labels['subtitle'])}</p>
      </div>
    </div>
    <div class="search-bar">
      <input type="text" id="search-input" placeholder="{html.escape(labels['search_placeholder'])}">
      <button onclick="searchCompany()">{html.escape(labels['search_button'])}</button>
    </div>
  </div>
  <p id="search-status"></p>
  <nav class="tabs">{tabs_html}</nav>
</header>
<main>{panels_html}</main>
<footer><p class="meta">{html.escape(labels['generated'].format(date=generated_at))}</p></footer>
<script>{_JS}</script>
</body>
</html>
"""


def _render_panel(client: ClientData, index: int, labels: dict) -> str:
    press_html = render_press(client, labels)
    display = "block" if index == 0 else "none"
    return f"""<section class="panel" id="panel-{index}" style="display:{display}">
  <h2>{html.escape(client.name)}</h2>
  <div class="card-grid">{press_html}</div>
</section>"""


def render_press(client: ClientData, labels: dict) -> str:
    if client.press_error:
        return f'<p class="empty error">{html.escape(labels["press_error"].format(error=client.press_error))}</p>'
    if not client.press:
        return f'<p class="empty">{html.escape(labels["no_press"])}</p>'
    cards = []
    for r in client.press:
        title = html.escape(r.get("title", "Sans titre"))
        url = html.escape(r.get("url", ""))
        source_name = html.escape(_source_name(r.get("url", "")))
        date = r.get("published_date", "")
        date_html = f'<span class="date">{html.escape(date)}</span>' if date else ""
        content = html.escape(r.get("content", "").strip()[:280])
        cards.append(
            f'<article class="card">'
            f'<div class="card-top"><span class="outlet">{source_name}</span>{date_html}</div>'
            f'<a class="card-title" href="{url}" target="_blank" rel="noopener">{title}</a>'
            f'<p>{content}</p>'
            f'<a class="card-source" href="{url}" target="_blank" rel="noopener">{html.escape(labels["source"])} →</a>'
            f"</article>"
        )
    return "\n".join(cards)


def _source_name(url: str) -> str:
    from urllib.parse import urlparse

    domain = urlparse(url).netloc.replace("www.", "")
    return domain.split(".")[0].upper() if domain else ""


_CSS = """
:root {
  color-scheme: light;
  --cisco-blue: #049fd9;
  --cisco-blue-dark: #005073;
  --ink: #0d1a26;
  --muted: #5b6b79;
  --bg: #f5f8fa;
  --card: #ffffff;
  --border: #e1e8ed;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
  margin: 0; background: var(--bg); color: var(--ink);
}
header {
  background: linear-gradient(135deg, var(--cisco-blue-dark) 0%, var(--cisco-blue) 100%);
  color: white; padding: 24px 32px 0;
}
.header-inner {
  display: flex; justify-content: space-between; align-items: flex-start;
  flex-wrap: wrap; gap: 16px; padding-bottom: 20px;
}
.brand { display: flex; align-items: center; gap: 14px; }
.brand-mark {
  width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0;
  background: white;
  background-image: radial-gradient(circle at 30% 30%, rgba(4,159,217,0.9), rgba(0,80,115,0.9));
}
header h1 { margin: 0; font-size: 21px; font-weight: 700; letter-spacing: -0.01em; }
.subtitle { margin: 2px 0 0; font-size: 13px; color: rgba(255,255,255,0.85); }
.search-bar { display: flex; gap: 8px; }
.search-bar input {
  width: 240px; padding: 9px 12px; border-radius: 8px; border: 1px solid transparent;
  font-size: 14px; outline: none;
}
.search-bar input:focus { box-shadow: 0 0 0 3px rgba(255,255,255,0.5); }
.search-bar button {
  border: none; background: rgba(255,255,255,0.18); color: white; padding: 9px 18px;
  border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600;
  transition: background 0.15s ease;
}
.search-bar button:hover { background: rgba(255,255,255,0.32); }
#search-status {
  color: white; font-size: 13px; margin: 0; min-height: 18px; opacity: 0.9;
  padding: 0 32px;
}
.tabs {
  display: flex; flex-wrap: wrap; gap: 6px; padding: 14px 32px 0; margin: 0;
  border-top: 1px solid rgba(255,255,255,0.15);
}
.tab {
  border: none; background: transparent; color: rgba(255,255,255,0.75);
  padding: 10px 16px; border-radius: 8px 8px 0 0; cursor: pointer; font-size: 14px;
  font-weight: 500; transition: background 0.15s ease, color 0.15s ease;
}
.tab:hover { background: rgba(255,255,255,0.12); color: white; }
.tab.active { background: var(--bg); color: var(--cisco-blue-dark); font-weight: 700; }
main { padding: 28px 32px 8px; max-width: 1280px; margin: 0 auto; }
.panel { animation: fade-in 0.25s ease; }
@keyframes fade-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
.panel h2 { margin: 0 0 18px; font-size: 20px; color: var(--ink); }
.card-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;
}
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 16px 18px; display: flex; flex-direction: column; gap: 8px;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(13,26,38,0.08); }
.card-top { display: flex; justify-content: space-between; align-items: center; }
.outlet {
  font-size: 11px; font-weight: 700; letter-spacing: 0.04em; color: var(--cisco-blue-dark);
  background: rgba(4,159,217,0.1); padding: 3px 8px; border-radius: 999px;
}
.date { font-size: 12px; color: var(--muted); }
.card-title { font-weight: 600; text-decoration: none; color: var(--ink); line-height: 1.35; }
.card-title:hover { color: var(--cisco-blue-dark); }
.card p { font-size: 13.5px; line-height: 1.55; margin: 0; color: var(--muted); flex-grow: 1; }
.card-source {
  font-size: 12.5px; font-weight: 600; color: var(--cisco-blue); text-decoration: none; margin-top: 4px;
}
.card-source:hover { text-decoration: underline; }
.empty { color: var(--muted); font-style: italic; grid-column: 1 / -1; }
.error { color: #b91c1c; }
footer { padding: 24px 32px 32px; max-width: 1280px; margin: 0 auto; }
.meta { margin: 0; font-size: 12.5px; color: var(--muted); }
@media (max-width: 640px) {
  .header-inner { flex-direction: column; }
  .search-bar input { width: 100%; }
  .search-bar { width: 100%; }
}
"""

_JS = """
function showClient(index) {
  document.querySelectorAll('.panel').forEach((p, i) => { p.style.display = (i === index) ? 'block' : 'none'; });
  document.querySelectorAll('.tab').forEach((t, i) => { t.classList.toggle('active', i === index); });
}

async function searchCompany() {
  const body = document.body;
  const input = document.getElementById('search-input');
  const status = document.getElementById('search-status');
  const company = input.value.trim();
  if (!company) return;
  status.textContent = body.dataset.searchLoading;
  try {
    const res = await fetch('/search?company=' + encodeURIComponent(company));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    addDynamicPanel(data);
    status.textContent = '';
    input.value = '';
  } catch (err) {
    status.textContent = body.dataset.searchUnavailable;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('search-input');
  if (input) {
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') searchCompany(); });
  }
});

function addDynamicPanel(data) {
  const emptyMsg = document.querySelector('main > p.empty');
  if (emptyMsg) emptyMsg.remove();

  const index = document.querySelectorAll('.panel').length;
  const panel = document.createElement('section');
  panel.className = 'panel';
  panel.id = 'panel-' + index;
  panel.innerHTML = '<h2></h2><div class="card-grid"></div>';
  panel.querySelector('h2').textContent = data.name;
  panel.querySelector('.card-grid').innerHTML = data.press_html;
  document.querySelector('main').appendChild(panel);

  const tab = document.createElement('button');
  tab.className = 'tab';
  tab.textContent = data.name;
  tab.onclick = () => showClient(index);
  document.querySelector('.tabs').appendChild(tab);

  showClient(index);
}
"""


def write_dashboard(html_content: str, out_path: str) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path
