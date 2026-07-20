"""Collecte de presse publique via l'API Tavily."""

import re
import unicodedata

import requests

SEARCH_URL = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 30
NEWS_LOOKBACK_DAYS = 180
DEFAULT_MAX_RESULTS = 15

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

# Grands médias reconnus uniquement (France, États-Unis, Royaume-Uni,
# presse tech de référence) : on exclut délibérément la presse
# spécialisée/blogs pour ne garder que des sources grand public de référence.
MAJOR_NEWS_DOMAINS = (
    # France
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


def collect_press(
    client: TavilyClient, company: str, lang: str, max_results: int = DEFAULT_MAX_RESULTS
) -> dict:
    """Retourne les articles de presse récents sur `company`, restreints aux
    grands médias mondiaux (France, États-Unis, Royaume-Uni, presse tech),
    avec un résumé du jour généré par Tavily.

    Retourne {"results": [...], "answer": str | None}.
    """
    query = NEWS_QUERY[lang].format(company=company)
    data = client.search(
        query,
        topic="news",
        max_results=max_results,
        include_domains=MAJOR_NEWS_DOMAINS,
        include_answer=True,
    )
    results = data.get("results", [])
    words = _name_words(company)
    filtered = [
        r
        for r in results
        if _matches_company(r.get("title", "") + " " + r.get("content", ""), words)
    ]
    return {"results": filtered, "answer": data.get("answer") or None}


def collect_official_press(
    client: TavilyClient, company: str, lang: str, max_results: int = 6
) -> list:
    """Retourne des communiqués/annonces publiés par l'entreprise elle-même
    (site officiel, newsroom), sans restriction de domaine."""
    query = OFFICIAL_PRESS_QUERY[lang].format(company=company)
    data = client.search(query, topic="general", max_results=max_results)
    results = data.get("results", [])
    words = _name_words(company)
    return [
        r
        for r in results
        if _matches_company(r.get("title", "") + " " + r.get("content", ""), words)
    ]
