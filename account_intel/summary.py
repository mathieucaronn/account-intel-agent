"""Résumé du jour croisant presse, communiqués et réseaux sociaux, via Claude.

Optionnel : n'est utilisé que si ANTHROPIC_API_KEY est configuré. Sans clé,
le dashboard retombe sur le résumé plus sommaire déjà fourni par Tavily
(voir search.collect_press). Dépendance optionnelle, voir requirements-ai.txt.
"""

MODEL = "claude-haiku-4-5-20251001"
MAX_OUTPUT_TOKENS = 500
MAX_ITEMS_PER_CATEGORY = 8
MAX_CONTENT_CHARS = 220

SYSTEM_PROMPT = {
    "fr": (
        "Tu es un analyste qui prépare une synthèse quotidienne pour une équipe "
        "commerciale, à partir de presse, communiqués et réseaux sociaux déjà "
        "collectés sur une entreprise. Rédige un résumé détaillé (6 à 10 phrases) "
        "qui croise ces sources — ne te contente pas de reformuler un seul "
        "article, relie les informations entre elles quand c'est pertinent "
        "(ex. un communiqué confirmé par la presse, un post social qui annonce "
        "ce que la presse développe). N'utilise QUE les informations fournies : "
        "n'invente jamais de fait, chiffre ou date. Termine par une ligne "
        "« Sources : » citant les médias/plateformes utilisés, séparés par des "
        "virgules. Réponds uniquement avec le résumé, sans préambule."
    ),
    "en": (
        "You are an analyst preparing a daily briefing for a sales team, from "
        "press, official announcements and social media already collected "
        "about a company. Write a detailed summary (6 to 10 sentences) that "
        "cross-references these sources — don't just restate a single "
        "article, connect information across them when relevant (e.g. an "
        "announcement confirmed by press coverage, a social post previewing "
        "what the press later covers). Use ONLY the information provided: "
        "never invent a fact, figure, or date. End with a line \"Sources:\" "
        "listing the outlets/platforms used, comma-separated. Reply with the "
        "summary only, no preamble."
    ),
}


class SummaryError(Exception):
    """Erreur lors de l'appel au modèle de résumé."""


def _format_items(label: str, items: list) -> str:
    if not items:
        return ""
    lines = [f"=== {label} ==="]
    for item in items[:MAX_ITEMS_PER_CATEGORY]:
        title = item.get("title", "").strip()
        content = item.get("content", "").strip()[:MAX_CONTENT_CHARS]
        source = item.get("url", "").split("/")[2] if item.get("url") else ""
        lines.append(f"- [{source}] {title} : {content}")
    return "\n".join(lines)


def generate_cross_summary(
    anthropic_api_key: str,
    company: str,
    press: list,
    official_press: list,
    social: list,
    lang: str,
) -> str:
    """Retourne un résumé du jour croisant les trois catégories de données.
    Lève SummaryError en cas d'échec (l'appelant doit prévoir un repli)."""
    try:
        import anthropic
    except ImportError as exc:
        raise SummaryError(
            "Le paquet 'anthropic' n'est pas installé (pip install -r requirements-ai.txt)."
        ) from exc

    blocks = [
        b
        for b in (
            _format_items("PRESSE" if lang == "fr" else "PRESS", press),
            _format_items(
                "ANNONCES & COMMUNIQUÉS" if lang == "fr" else "ANNOUNCEMENTS", official_press
            ),
            _format_items("RÉSEAUX SOCIAUX" if lang == "fr" else "SOCIAL MEDIA", social),
        )
        if b
    ]
    if not blocks:
        return ""

    user_prompt = (
        f"Entreprise : {company}\n\n" if lang == "fr" else f"Company: {company}\n\n"
    ) + "\n\n".join(blocks)

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=SYSTEM_PROMPT[lang],
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.AuthenticationError as exc:
        raise SummaryError("Clé API Anthropic invalide (vérifiez ANTHROPIC_API_KEY).") from exc
    except anthropic.APIError as exc:
        raise SummaryError(f"Erreur de l'API Anthropic : {exc}") from exc

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise SummaryError("Le modèle n'a renvoyé aucun contenu.")
    return text
