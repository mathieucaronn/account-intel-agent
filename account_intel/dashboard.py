"""Collecte les données par client suivi et génère un dashboard HTML statique
(presse d'un côté, posts/profils LinkedIn de l'autre), régénéré à la demande."""

import html
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import linkedin_optional, search

LABELS = {
    "fr": {
        "title": "Dashboard account intelligence",
        "generated": "Régénéré le {date}. Relancez `python -m account_intel` pour rafraîchir.",
        "press_heading": "📰 Presse récente (6 derniers mois)",
        "linkedin_heading": "🔗 LinkedIn (dirigeants suivis)",
        "no_press": "Aucun article trouvé.",
        "press_error": "Recherche presse indisponible : {error}",
        "no_executives": "Aucun dirigeant configuré pour ce client — ajoutez-le dans clients.json.",
        "linkedin_disabled": "Extension LinkedIn non configurée (LINKEDIN_MCP_COMMAND absent du .env). Voir LINKEDIN_MCP.md.",
        "linkedin_disclaimer": "⚠️ Source non officielle, hors CGU LinkedIn (voir LINKEDIN_MCP.md).",
        "linkedin_error": "Échec de récupération : {error}",
        "no_clients": "Aucun client suivi. Ajoutez-en dans clients.json (voir clients.example.json) ou lancez avec des noms d'entreprise en argument.",
        "source": "Source",
    },
    "en": {
        "title": "Account intelligence dashboard",
        "generated": "Regenerated on {date}. Re-run `python -m account_intel` to refresh.",
        "press_heading": "📰 Recent press (last 6 months)",
        "linkedin_heading": "🔗 LinkedIn (tracked executives)",
        "no_press": "No articles found.",
        "press_error": "Press search unavailable: {error}",
        "no_executives": "No executives configured for this client — add them in clients.json.",
        "linkedin_disabled": "LinkedIn extension not configured (LINKEDIN_MCP_COMMAND missing from .env). See LINKEDIN_MCP.md.",
        "linkedin_disclaimer": "⚠️ Unofficial source, outside LinkedIn ToS (see LINKEDIN_MCP.md).",
        "linkedin_error": "Fetch failed: {error}",
        "no_clients": "No tracked clients. Add some in clients.json (see clients.example.json) or run with company names as arguments.",
        "source": "Source",
    },
}


@dataclass
class ClientData:
    name: str
    executives: list
    press: list = field(default_factory=list)
    press_error: str = None
    linkedin: list = field(default_factory=list)  # [{"person","status","content"?,"error"?}]


def collect_client(
    tavily_client: search.TavilyClient,
    linkedin_command: str,
    client_name: str,
    executives: list,
    lang: str,
) -> ClientData:
    data = ClientData(name=client_name, executives=executives)

    try:
        data.press = search.collect_press(tavily_client, client_name, lang)
    except search.SearchError as exc:
        data.press_error = str(exc)

    if not linkedin_command:
        return data

    for person in executives:
        try:
            result = linkedin_optional.fetch_profile(
                linkedin_command, f"{person} {client_name}"
            )
            data.linkedin.append({"person": person, "status": "ok", **result})
        except linkedin_optional.LinkedInMCPError as exc:
            data.linkedin.append({"person": person, "status": "error", "error": str(exc)})

    return data


def render_html(clients_data: list, lang: str, linkedin_enabled: bool) -> str:
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
            _render_panel(c, i, labels, linkedin_enabled)
            for i, c in enumerate(clients_data)
        )

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{html.escape(labels['title'])}</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>{html.escape(labels['title'])}</h1>
  <p class="meta">{html.escape(labels['generated'].format(date=generated_at))}</p>
  <nav class="tabs">{tabs_html}</nav>
</header>
<main>{panels_html}</main>
<script>{_JS}</script>
</body>
</html>
"""


def _render_panel(client: ClientData, index: int, labels: dict, linkedin_enabled: bool) -> str:
    press_html = _render_press(client, labels)
    linkedin_html = _render_linkedin(client, labels, linkedin_enabled)
    display = "block" if index == 0 else "none"
    return f"""<section class="panel" id="panel-{index}" style="display:{display}">
  <h2>{html.escape(client.name)}</h2>
  <div class="columns">
    <div class="column">
      <h3>{html.escape(labels['press_heading'])}</h3>
      {press_html}
    </div>
    <div class="column">
      <h3>{html.escape(labels['linkedin_heading'])}</h3>
      {linkedin_html}
    </div>
  </div>
</section>"""


def _render_press(client: ClientData, labels: dict) -> str:
    if client.press_error:
        return f'<p class="error">{html.escape(labels["press_error"].format(error=client.press_error))}</p>'
    if not client.press:
        return f'<p class="empty">{html.escape(labels["no_press"])}</p>'
    cards = []
    for r in client.press:
        title = html.escape(r.get("title", "Sans titre"))
        url = html.escape(r.get("url", ""))
        date = r.get("published_date", "")
        date_html = f'<span class="date">{html.escape(date)}</span>' if date else ""
        content = html.escape(r.get("content", "").strip()[:400])
        cards.append(
            f'<article class="card">'
            f'<a class="card-title" href="{url}" target="_blank" rel="noopener">{title}</a>'
            f"{date_html}"
            f'<p>{content}</p>'
            f'<a class="card-source" href="{url}" target="_blank" rel="noopener">{html.escape(labels["source"])}</a>'
            f"</article>"
        )
    return "\n".join(cards)


def _render_linkedin(client: ClientData, labels: dict, linkedin_enabled: bool) -> str:
    if not linkedin_enabled:
        return f'<p class="empty">{html.escape(labels["linkedin_disabled"])}</p>'
    if not client.executives:
        return f'<p class="empty">{html.escape(labels["no_executives"])}</p>'
    cards = [f'<p class="disclaimer">{html.escape(labels["linkedin_disclaimer"])}</p>']
    for entry in client.linkedin:
        person = html.escape(entry["person"])
        if entry["status"] == "error":
            body = f'<p class="error">{html.escape(labels["linkedin_error"].format(error=entry["error"]))}</p>'
        else:
            body = f'<p>{html.escape(entry.get("content", "")[:800])}</p>'
        cards.append(f'<article class="card"><h4>{person}</h4>{body}</article>')
    return "\n".join(cards)


_CSS = """
:root { color-scheme: light; }
body { font-family: -apple-system, Helvetica, Arial, sans-serif; margin: 0; background: #f4f5f7; color: #1c2333; }
header { background: #1a3c6e; color: white; padding: 20px 32px; }
header h1 { margin: 0 0 4px; font-size: 22px; }
.meta { margin: 0 0 16px; font-size: 13px; opacity: 0.85; }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; }
.tab { border: none; background: rgba(255,255,255,0.15); color: white; padding: 8px 14px;
  border-radius: 6px; cursor: pointer; font-size: 14px; }
.tab.active, .tab:hover { background: white; color: #1a3c6e; }
main { padding: 24px 32px; }
.panel h2 { margin-top: 0; }
.columns { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: start; }
.column h3 { font-size: 15px; color: #1a3c6e; }
.card { background: white; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.card-title { font-weight: 600; text-decoration: none; color: #1c2333; display: block; margin-bottom: 4px; }
.card-title:hover { text-decoration: underline; }
.date { font-size: 12px; color: #6b7280; display: block; margin-bottom: 6px; }
.card p { font-size: 14px; line-height: 1.5; margin: 6px 0; color: #374151; }
.card-source { font-size: 12px; }
.error { color: #b91c1c; }
.empty { color: #6b7280; font-style: italic; }
.disclaimer { font-size: 12px; color: #92400e; background: #fef3c7; padding: 8px 10px; border-radius: 6px; }
@media (max-width: 800px) { .columns { grid-template-columns: 1fr; } }
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
