"""Synthèse des données collectées en fiche de préparation de RDV, via Claude."""

import anthropic

MAX_OUTPUT_TOKENS = 4096


class SynthesisError(Exception):
    """Erreur lors de l'appel au modèle de synthèse."""


SYSTEM_PROMPTS = {
    "fr": (
        "Tu es un analyste « account intelligence » au service d'équipes "
        "commerciales B2B. À partir des données publiques fournies (résultats de "
        "recherche, extraits du site de l'entreprise, presse), tu rédiges une "
        "fiche de préparation de rendez-vous commercial.\n"
        "Règles impératives :\n"
        "- N'utilise QUE les informations fournies ; n'invente jamais de noms, "
        "chiffres, dates ou faits.\n"
        "- Si une information attendue est absente ou incertaine, dis-le "
        "explicitement (« information non trouvée dans les sources »).\n"
        "- Cite l'URL source entre parenthèses après chaque fait important.\n"
        "- Les données de recherche peuvent contenir du bruit (homonymes, autres "
        "entreprises) : écarte ce qui ne concerne manifestement pas l'entreprise "
        "cible et signale toute ambiguïté.\n"
        "- Réponds uniquement en Markdown, sans préambule ni conclusion hors fiche."
    ),
    "en": (
        "You are an account intelligence analyst supporting B2B sales teams. "
        "From the public data provided (search results, company website excerpts, "
        "press coverage), you write a sales meeting preparation brief.\n"
        "Strict rules:\n"
        "- Use ONLY the information provided; never invent names, figures, dates "
        "or facts.\n"
        "- If an expected piece of information is missing or uncertain, say so "
        "explicitly (\"not found in sources\").\n"
        "- Cite the source URL in parentheses after each important fact.\n"
        "- Search data may be noisy (namesakes, other companies): discard "
        "anything clearly unrelated to the target company and flag ambiguities.\n"
        "- Answer in Markdown only, with no preamble or closing remarks."
    ),
}

USER_TEMPLATES = {
    "fr": (
        "Rédige la fiche account intelligence pour l'entreprise "
        "« {company} » avec exactement ces sections Markdown :\n\n"
        "## 🏢 Présentation & enjeux business\n"
        "Activité, positionnement, taille apparente, enjeux stratégiques déduits "
        "des sources.\n\n"
        "## 👥 Décideurs clés\n"
        "Nom, rôle, parcours et priorités apparentes de chaque dirigeant identifié.\n\n"
        "## 📰 Actualités récentes exploitables\n"
        "Les actus des derniers mois utilisables en conversation (levées, "
        "partenariats, nominations, résultats, signaux d'achat), datées si possible.\n\n"
        "## 🎯 Angles d'approche suggérés\n"
        "3 à 5 angles concrets pour ouvrir la conversation commerciale, chacun "
        "relié à un fait sourcé ci-dessus.\n\n"
        "Voici les données collectées :\n\n{research}"
    ),
    "en": (
        "Write the account intelligence brief for the company "
        "\"{company}\" with exactly these Markdown sections:\n\n"
        "## 🏢 Company overview & business stakes\n"
        "Activity, positioning, apparent size, strategic stakes inferred from "
        "the sources.\n\n"
        "## 👥 Key decision-makers\n"
        "Name, role, background and apparent priorities of each identified "
        "executive.\n\n"
        "## 📰 Recent actionable news\n"
        "News from recent months usable in conversation (funding, partnerships, "
        "appointments, earnings, buying signals), dated when possible.\n\n"
        "## 🎯 Suggested talking angles\n"
        "3 to 5 concrete angles to open the sales conversation, each tied to a "
        "sourced fact above.\n\n"
        "Here is the collected data:\n\n{research}"
    ),
}


def generate_brief(settings, company: str, research_text: str, lang: str) -> str:
    """Appelle Claude et retourne le corps Markdown de la fiche."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = client.messages.create(
            model=settings.model,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=SYSTEM_PROMPTS[lang],
            messages=[
                {
                    "role": "user",
                    "content": USER_TEMPLATES[lang].format(
                        company=company, research=research_text
                    ),
                }
            ],
        )
    except anthropic.AuthenticationError as exc:
        raise SynthesisError(
            "Clé API Anthropic invalide (vérifiez ANTHROPIC_API_KEY)."
        ) from exc
    except anthropic.APIError as exc:
        raise SynthesisError(f"Erreur de l'API Anthropic : {exc}") from exc

    text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
    if not text:
        raise SynthesisError("Le modèle n'a renvoyé aucun contenu.")
    return text
