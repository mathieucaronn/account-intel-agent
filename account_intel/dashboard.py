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
        "title": "Cisco Manufacturing — Account News",
        "subtitle": "Revue de presse par compte, sources grand public uniquement",
        "generated": "Actualisé automatiquement le {date}.",
        "summary_heading": "Résumé du jour",
        "sources_label": "Sources",
        "headlines_heading": "Grands titres",
        "official_heading": "Annonces & communiqués",
        "social_heading": "Réseaux sociaux",
        "no_press": "Aucun article trouvé dans les grands médias suivis pour cette entreprise.",
        "press_error": "Recherche presse indisponible : {error}",
        "no_clients": "Aucun client suivi. Ajoutez-en dans clients.json.",
        "source": "Lire l'article",
        "no_date": "Date inconnue",
    },
    "en": {
        "title": "Cisco Manufacturing — Account News",
        "subtitle": "Per-account press review, major outlets only",
        "generated": "Automatically refreshed on {date}.",
        "summary_heading": "Today's summary",
        "sources_label": "Sources",
        "headlines_heading": "Top headlines",
        "official_heading": "Announcements & press coverage",
        "social_heading": "Social media",
        "no_press": "No articles found in tracked major outlets for this company.",
        "press_error": "Press search unavailable: {error}",
        "no_clients": "No tracked clients. Add some in clients.json.",
        "source": "Read article",
        "no_date": "Date unknown",
    },
}


@dataclass
class ClientData:
    name: str
    press: list = field(default_factory=list)
    official_press: list = field(default_factory=list)
    social: list = field(default_factory=list)
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
    try:
        data.official_press = search.collect_official_press(tavily_client, client_name, lang)
    except search.SearchError:
        pass  # les communiqués officiels sont un bonus, pas critique
    try:
        data.social = search.collect_social(tavily_client, client_name, lang)
    except search.SearchError:
        pass  # idem pour les réseaux sociaux
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
      <span class="soundwave" aria-hidden="true">
        <span></span><span></span><span></span><span></span><span></span><span></span><span></span>
      </span>
      <div>
        <h1>{html.escape(labels['title'])}</h1>
        <p class="subtitle">{html.escape(labels['subtitle'])}</p>
      </div>
    </div>
  </div>
  <nav class="tabs">{tabs_html}</nav>
</header>
<main>{panels_html}</main>
<footer><p class="meta"><span class="live-dot"></span>{html.escape(labels['generated'].format(date=generated_at))}</p></footer>
<script>{_JS}</script>
</body>
</html>
"""


def _render_panel(client: ClientData, index: int, labels: dict) -> str:
    display = "block" if index == 0 else "none"
    summary_html = _render_summary(client, labels)
    press_html = render_press(client, labels)
    headline_heading = "" if not client.press else (
        f'<h3 class="section-heading">{html.escape(labels["headlines_heading"])}</h3>'
    )
    official_html = ""
    if client.official_press:
        official_cards = _render_cards(client.official_press, labels, badge="official")
        official_html = (
            f'<h3 class="section-heading">{html.escape(labels["official_heading"])}</h3>'
            f'<div class="card-grid">{official_cards}</div>'
        )
    social_html = ""
    if client.social:
        social_cards = _render_cards(client.social, labels, badge="social")
        social_html = (
            f'<h3 class="section-heading">{html.escape(labels["social_heading"])}</h3>'
            f'<div class="card-grid">{social_cards}</div>'
        )
    return f"""<section class="panel" id="panel-{index}" style="display:{display}">
  <h2>{html.escape(client.name)}</h2>
  {summary_html}
  {headline_heading}
  <div class="card-grid">{press_html}</div>
  {official_html}
  {social_html}
</section>"""


def _render_summary(client: ClientData, labels: dict) -> str:
    if not client.answer:
        return ""
    seen, links = set(), []
    for r in client.press:
        name = _source_name(r.get("url", ""))
        if name and name not in seen and r.get("url"):
            seen.add(name)
            links.append(
                f'<a href="{html.escape(r["url"])}" target="_blank" rel="noopener">{html.escape(name)}</a>'
            )
    sources_html = ""
    if links:
        sources_html = (
            f'<p class="summary-sources">'
            f'<span>{html.escape(labels["sources_label"])} :</span> {" · ".join(links)}'
            f'</p>'
        )
    return (
        f'<div class="summary">'
        f'<span class="summary-label">{html.escape(labels["summary_heading"])}</span>'
        f'<p>{html.escape(client.answer)}</p>'
        f'{sources_html}'
        f'</div>'
    )


def render_press(client: ClientData, labels: dict) -> str:
    if client.press_error:
        return f'<p class="empty error">{html.escape(labels["press_error"].format(error=client.press_error))}</p>'
    if not client.press:
        return f'<p class="empty">{html.escape(labels["no_press"])}</p>'
    return _render_cards(client.press, labels)


_PLATFORM_LABELS = {
    "linkedin.com": "LinkedIn",
    "x.com": "X",
    "twitter.com": "X",
    "youtube.com": "YouTube",
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
}


def _render_cards(results: list, labels: dict, badge: str = "press") -> str:
    cards = []
    for i, r in enumerate(results):
        title = html.escape(r.get("title", "Sans titre"))
        url = html.escape(r.get("url", ""))
        domain = urlparse(r.get("url", "")).netloc.replace("www.", "")
        if badge == "social":
            badge_text = next(
                (v for k, v in _PLATFORM_LABELS.items() if domain.endswith(k)), domain.upper()
            )
            badge_class = f"outlet social social-{badge_text.lower()}"
        else:
            badge_text = _source_name(r.get("url", ""))
            badge_class = "outlet official" if badge == "official" else "outlet"
        date = r.get("published_date", "")
        date_text = date if date else labels["no_date"]
        date_class = "date" if date else "date date-unknown"
        date_html = f'<span class="{date_class}">{html.escape(date_text)}</span>'
        content = html.escape(r.get("content", "").strip()[:280])
        cards.append(
            f'<article class="card" style="animation-delay:{i * 40}ms">'
            f'<div class="card-top"><span class="{badge_class}">{html.escape(badge_text)}</span>{date_html}</div>'
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
  color: white; padding: 24px 32px 0; position: relative; overflow: hidden;
}
.header-inner { padding-bottom: 20px; }
.brand { display: flex; align-items: center; gap: 16px; }
.soundwave { display: flex; align-items: center; gap: 3px; height: 32px; flex-shrink: 0; }
.soundwave span {
  display: block; width: 4px; border-radius: 3px; background: white;
  animation: wave 1.6s ease-in-out infinite;
}
.soundwave span:nth-child(1) { height: 40%; animation-delay: 0s; }
.soundwave span:nth-child(2) { height: 70%; animation-delay: 0.1s; }
.soundwave span:nth-child(3) { height: 100%; animation-delay: 0.2s; }
.soundwave span:nth-child(4) { height: 55%; animation-delay: 0.3s; }
.soundwave span:nth-child(5) { height: 90%; animation-delay: 0.4s; }
.soundwave span:nth-child(6) { height: 65%; animation-delay: 0.5s; }
.soundwave span:nth-child(7) { height: 35%; animation-delay: 0.6s; }
@keyframes wave { 0%, 100% { transform: scaleY(0.6); opacity: 0.7; } 50% { transform: scaleY(1); opacity: 1; } }
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
.panel { animation: fade-in 0.3s ease; }
@keyframes fade-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
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
.summary-sources { font-size: 12px !important; color: var(--muted) !important; margin-top: 10px !important; }
.summary-sources span { font-weight: 700; color: var(--cisco-blue-dark); }
.summary-sources a { color: var(--cisco-blue-dark); font-weight: 600; text-decoration: none; }
.summary-sources a:hover { text-decoration: underline; }
.section-heading {
  font-size: 13px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--muted); margin: 24px 0 12px;
}
.card-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;
}
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 16px 18px; display: flex; flex-direction: column; gap: 8px;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  animation: card-in 0.35s ease backwards;
}
@keyframes card-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.card:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(13,26,38,0.1); }
.card-top { display: flex; justify-content: space-between; align-items: center; }
.outlet {
  font-size: 11px; font-weight: 700; letter-spacing: 0.04em; color: var(--cisco-blue-dark);
  background: rgba(4,159,217,0.1); padding: 3px 8px; border-radius: 999px;
}
.outlet.official { color: #0d7a3f; background: rgba(13,122,63,0.1); }
.outlet.social { color: #6d28d9; background: rgba(109,40,217,0.1); }
.outlet.social-linkedin { color: #0a66c2; background: rgba(10,102,194,0.1); }
.outlet.social-x { color: #0d1a26; background: rgba(13,26,38,0.08); }
.outlet.social-youtube { color: #cc0000; background: rgba(204,0,0,0.1); }
.outlet.social-instagram { color: #c1287a; background: rgba(193,40,122,0.1); }
.outlet.social-facebook { color: #1877f2; background: rgba(24,119,242,0.1); }
.date { font-size: 12px; color: var(--muted); }
.date-unknown { font-style: italic; opacity: 0.6; }
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
.meta { margin: 0; font-size: 12.5px; color: var(--muted); display: flex; align-items: center; gap: 7px; }
.live-dot {
  width: 7px; height: 7px; border-radius: 50%; background: #17b06b; flex-shrink: 0;
  box-shadow: 0 0 0 rgba(23,176,107,0.5); animation: pulse 2s infinite;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(23,176,107,0.5); }
  70% { box-shadow: 0 0 0 6px rgba(23,176,107,0); }
  100% { box-shadow: 0 0 0 0 rgba(23,176,107,0); }
}
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
