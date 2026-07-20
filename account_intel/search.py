"""Collecte de presse publique via l'API Tavily."""

import re
import unicodedata

import requests

SEARCH_URL = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 30
NEWS_LOOKBACK_DAYS = 180

_STOPWORDS = {"and", "et", "de", "des", "du", "la", "le", "les", "of", "the"}


class SearchError(Exception):
    """Erreur d'accès à l'API de recherche (réseau, quota, clé invalide...)."""


# Orienté technologie / IA / réseaux / acquisitions / dirigeants plutôt que
# pure actualité financière (marchés, cours de bourse).
NEWS_QUERY = {
    "fr": "{company} technologie intelligence artificielle réseaux acquisition dirigeant innovation",
    "en": "{company} technology AI artificial intelligence networking acquisition leadership innovation",
}

OFFICIAL_PRESS_QUERY = {
    "fr": "{company} communiqué de presse officiel annonce",
    "en": "{company} official press release announcement newsroom",
}

SOCIAL_QUERY = {
    "fr": "{company} innovation actualité annonce",
    "en": "{company} innovation announcement update",
}

# Réseaux sociaux : pas de scraping ni de connexion à un compte — uniquement
# ce que l'index de recherche de Tavily a déjà indexé publiquement (comme un
# moteur de recherche classique), donc pas de risque vis-à-vis des CGU de
# ces plateformes.
SOCIAL_DOMAINS = (
    "linkedin.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "instagram.com",
    "facebook.com",
)

# Grands médias reconnus uniquement : on exclut délibérément la presse
# spécialisée/blogs pour ne garder que des sources grand public de
# référence. Séparé en deux groupes (plutôt qu'une seule liste) car dans un
# appel unique, les grands médias internationaux (Reuters, WSJ...) noient
# systématiquement la presse française dans les résultats — deux appels
# distincts garantissent une vraie place à la presse française, demandée en
# priorité.
FRENCH_NEWS_DOMAINS = (
    "lemonde.fr",
    "lefigaro.fr",
    "lesechos.fr",
    "latribune.fr",
    "challenges.fr",
    "capital.fr",
    "bfmtv.com",
    "tf1info.fr",
    "usinenouvelle.com",
    "boursorama.com",
    "lemagit.fr",
    "channelnews.fr",
)
INTERNATIONAL_NEWS_DOMAINS = (
    # États-Unis
    "nytimes.com",
    "wsj.com",
    "bloomberg.com",
    "cnn.com",
    "reuters.com",
    "apnews.com",
    "washingtonpost.com",
    "forbes.com",
    "fortune.com",
    "businessinsider.com",
    # Royaume-Uni
    "bbc.com",
    "bbc.co.uk",
    "theguardian.com",
    "ft.com",
    "sky.com",
    "telegraph.co.uk",
    # Presse tech de référence
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "arstechnica.com",
)


class TavilyClient:
    def __init__(self, api_key: str):
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}"})

    def search(
        self,
        query: str,
        *,
        topic: str = "general",
        max_results: int = 8,
        include_domains: tuple = (),
        include_answer: bool = False,
    ) -> dict:
        payload = {
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "include_answer": include_answer,
        }
        if include_domains:
            payload["include_domains"] = list(include_domains)
        if topic == "news":
            payload["days"] = NEWS_LOOKBACK_DAYS
        try:
            response = self._session.post(SEARCH_URL, json=payload, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                raise SearchError(
                    "Clé API Tavily invalide ou non autorisée (vérifiez TAVILY_API_KEY)."
                ) from exc
            if status == 429:
                raise SearchError("Quota Tavily dépassé, réessayez plus tard.") from exc
            raise SearchError(f"Erreur Tavily HTTP {status}.") from exc
        except requests.RequestException as exc:
            raise SearchError(f"Impossible de joindre l'API Tavily : {exc}") from exc


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"['’\-]", " ", text.lower())


def _name_words(company: str) -> tuple:
    words = [w for w in _normalize(company).split() if w not in _STOPWORDS and len(w) > 2]
    return tuple(words) if words else (_normalize(company),)


def _matches_company(text: str, words: tuple) -> bool:
    """Le mot principal (ex. « airbus ») doit apparaître, et au moins un des
    mots secondaires si le nom en comporte (ex. « defence »/« space » pour
    « Airbus Defence and Space ») — la presse écrit rarement les noms de
    filiales composés mot pour mot, donc exiger la phrase exacte ne renvoie
    presque jamais rien."""
    text_n = _normalize(text)
    primary, rest = words[0], words[1:]
    return primary in text_n and (not rest or any(w in text_n for w in rest))


# Titres de pages "hub" (flux/agrégateur d'une valeur boursière ou d'une
# entreprise) plutôt que de vrais articles datés — n'apparaissent qu'en mode
# de recherche générale (le mode "news" n'en produit pas).
_HUB_TITLE_MARKERS = (
    "direct",
    "infos",
    "information",
    "derniere",
    "chiffre",
    "conseil",
    "enquete",
    "groupe",
    "video",
)


def _looks_like_hub_page(title: str, company_normalized: str) -> bool:
    title_n = _normalize(title)
    if title_n.strip() == company_normalized:
        return True
    if title_n.startswith("actions ") or title_n.startswith("action "):
        return True
    if "actualit" in title_n and any(m in title_n for m in _HUB_TITLE_MARKERS):
        return True
    return False


def _filter_results(results: list, words: tuple, drop_hub_pages: bool = False) -> list:
    kept = []
    for r in results:
        text = r.get("title", "") + " " + r.get("content", "")
        if not _matches_company(text, words):
            continue
        if drop_hub_pages and _looks_like_hub_page(r.get("title", ""), words[0]):
            continue
        kept.append(r)
    return kept


def collect_press(
    client: TavilyClient,
    company: str,
    lang: str,
    french_max_results: int = 10,
    international_max_results: int = 6,
) -> dict:
    """Retourne les articles de presse récents sur `company`, restreints aux
    grands médias (presse française en priorité, complétée par les grands
    médias États-Unis/Royaume-Uni/tech), avec un résumé du jour généré par
    Tavily.

    Retourne {"results": [...], "answer": str | None}.
    """
    query = NEWS_QUERY[lang].format(company=company)
    words = _name_words(company)

    # Le mode "news" de Tavily a un index très pauvre sur les seuls domaines
    # français (déjà constaté : dérive systématique vers du hors-sujet, quel
    # que soit le texte de la requête) ; le mode général y est nettement
    # plus fiable, au prix de l'absence de date de publication.
    french_data = client.search(
        query,
        topic="general",
        max_results=french_max_results,
        include_domains=FRENCH_NEWS_DOMAINS,
        include_answer=True,
    )
    intl_data = client.search(
        query,
        topic="news",
        max_results=international_max_results,
        include_domains=INTERNATIONAL_NEWS_DOMAINS,
        include_answer=True,
    )

    french_results = _filter_results(french_data.get("results", []), words, drop_hub_pages=True)
    intl_results = _filter_results(intl_data.get("results", []), words)
    answer = french_data.get("answer") or intl_data.get("answer") or None
    return {"results": french_results + intl_results, "answer": answer}


def collect_official_press(
    client: TavilyClient, company: str, lang: str, max_results: int = 6
) -> list:
    """Retourne des communiqués/annonces publiés par l'entreprise elle-même
    (site officiel, newsroom), sans restriction de domaine."""
    query = OFFICIAL_PRESS_QUERY[lang].format(company=company)
    data = client.search(query, topic="general", max_results=max_results)
    words = _name_words(company)
    return _filter_results(data.get("results", []), words, drop_hub_pages=True)


def collect_social(client: TavilyClient, company: str, lang: str, max_results: int = 10) -> list:
    """Retourne des publications publiques (LinkedIn, X, YouTube, Instagram,
    Facebook) mentionnant l'entreprise, telles qu'indexées par Tavily —
    aucune connexion ni automatisation de ces plateformes."""
    query = SOCIAL_QUERY[lang].format(company=company)
    data = client.search(
        query, topic="general", max_results=max_results, include_domains=SOCIAL_DOMAINS
    )
    words = _name_words(company)
    return _filter_results(data.get("results", []), words)
