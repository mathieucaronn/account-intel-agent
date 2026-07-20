"""Collecte la presse par client suivi et génère un dashboard HTML statique,
régénéré automatiquement (voir .github/workflows/refresh-dashboard.yml)."""

import html
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from . import search

LABELS = {
    "fr": {
        "title": "Account Intelligence",
        "subtitle": "Revue de presse par compte, sources grand public uniquement",
        "generated": "Actualisé automatiquement le {date}.",
        "summary_heading": "Résumé du jour",
        "headlines_heading": "Grands titres",
        "no_press": "Aucun article trouvé dans les grands médias suivis pour cette entreprise.",
        "press_error": "Recherche presse indisponible : {error}",
        "no_clients": "Aucun client suivi. Ajoutez-en dans clients.json.",
        "source": "Lire l'article",
    },
    "en": {
        "title": "Account Intelligence",
        "subtitle": "Per-account press review, major outlets only",
        "generated": "Automatically refreshed on {date}.",
        "summary_heading": "Today's summary",
        "headlines_heading": "Top headlines",
        "no_press": "No articles found in tracked major outlets for this company.",
        "press_error": "Press search unavailable: {error}",
        "no_clients": "No tracked clients. Add some in clients.json.",
        "source": "Read article",
    },
}


@dataclass
class ClientData:
    name: str
    press: list = field(default_factory=list)
    answer: str = None
    press_error: str = None


def collect_client(tavily_client: search.TavilyClient, client_name: str, lang: str) -> ClientData:
    data = ClientData(name=client_name)
    try:
        result = search.collect_press(tavily_client, client_name, lang)
        data.press = result["results"]
        data.answer = result["answer"]
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
<body>
<header>
  <div class="header-inner">
    <div class="brand">
      <span class="brand-mark"></span>
      <div>
        <h1>{html.escape(labels['title'])}</h1>
        <p class="subtitle">{html.escape(labels['subtitle'])}</p>
      </div>
    </div>
  </div>
  <nav class="tabs">{tabs_html}</nav>
</header>
<main>{panels_html}</main>
<footer><p class="meta">{html.escape(labels['generated'].format(date=generated_at))}</p></footer>
<script>{_JS}</script>
</body>
</html>
"""


def _render_panel(client: ClientData, index: int, labels: dict) -> str:
    display = "block" if index == 0 else "none"
    summary_html = ""
    if client.answer:
        summary_html = (
            f'<div class="summary">'
            f'<span class="summary-label">{html.escape(labels["summary_heading"])}</span>'
            f'<p>{html.escape(client.answer)}</p>'
            f'</div>'
        )
    press_html = render_press(client, labels)
    headline_heading = "" if not client.press else (
        f'<h3 class="section-heading">{html.escape(labels["headlines_heading"])}</h3>'
    )
    return f"""<section class="panel" id="panel-{index}" style="display:{display}">
  <h2>{html.escape(client.name)}</h2>
  {summary_html}
  {headline_heading}
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
.header-inner { padding-bottom: 20px; }
.brand { display: flex; align-items: center; gap: 14px; }
.brand-mark {
  width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0;
  background: white;
  background-image: radial-gradient(circle at 30% 30%, rgba(4,159,217,0.9), rgba(0,80,115,0.9));
}
header h1 { margin: 0; font-size: 21px; font-weight: 700; letter-spacing: -0.01em; }
.subtitle { margin: 2px 0 0; font-size: 13px; color: rgba(255,255,255,0.85); }
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
.panel h2 { margin: 0 0 16px; font-size: 20px; color: var(--ink); }
.summary {
  background: linear-gradient(135deg, rgba(4,159,217,0.08), rgba(0,80,115,0.05));
  border: 1px solid rgba(4,159,217,0.25); border-radius: 12px;
  padding: 16px 20px; margin-bottom: 20px;
}
.summary-label {
  font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--cisco-blue-dark);
}
.summary p { margin: 6px 0 0; font-size: 14.5px; line-height: 1.6; color: var(--ink); }
.section-heading {
  font-size: 13px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--muted); margin: 0 0 12px;
}
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
"""

_JS = """
function showClient(index) {
  document.querySelectorAll('.panel').forEach((p, i) => { p.style.display = (i === index) ? 'block' : 'none'; });
  document.querySelectorAll('.tab').forEach((t, i) => { t.classList.toggle('active', i === index); });
}
"""


def write_dashboard(html_content: str, out_path: str) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path
