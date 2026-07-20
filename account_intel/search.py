"""Collecte de presse publique via l'API Tavily."""

import re
import unicodedata

import requests

SEARCH_URL = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 30
NEWS_LOOKBACK_DAYS = 180
DEFAULT_MAX_RESULTS = 15


class SearchError(Exception):
    """Erreur d'accès à l'API de recherche (réseau, quota, clé invalide...)."""


NEWS_QUERY = {
    "fr": "{company} actualité",
    "en": "{company} news",
}

# Recherche "news" chez Tavily a un index pauvre sur les seuls domaines
# français (résultats hors sujet observés en test) ; la recherche générale a
# une bien meilleure couverture sur ces mêmes domaines. Le mix international
# (Reuters, WSJ...) fonctionne bien en "news" avec de vraies dates.
SEARCH_TOPIC = {"fr": "general", "en": "news"}

# Grands médias reconnus uniquement : on exclut délibérément la presse
# spécialisée/blogs/communiqués pour ne garder que des sources grand public
# de référence.
MAJOR_NEWS_DOMAINS = {
    "fr": (
        "lemonde.fr",
        "lefigaro.fr",
        "liberation.fr",
        "tf1info.fr",
        "francetvinfo.fr",
        "franceinfo.fr",
        "bfmtv.com",
        "lesechos.fr",
        "latribune.fr",
        "challenges.fr",
        "capital.fr",
        "la-croix.com",
        "ouest-france.fr",
        "leparisien.fr",
        "lepoint.fr",
        "lexpress.fr",
        "usinenouvelle.com",
        "boursorama.com",
    ),
    "en": (
        "bbc.com",
        "bbc.co.uk",
        "cnn.com",
        "reuters.com",
        "apnews.com",
        "nytimes.com",
        "washingtonpost.com",
        "theguardian.com",
        "wsj.com",
        "bloomberg.com",
        "economist.com",
        "time.com",
        "forbes.com",
        "ft.com",
    ),
}

# Titres de pages "hub" (flux/agrégateur d'une valeur boursière ou d'une
# entreprise) plutôt que de vrais articles datés — motifs observés en test
# sur la presse économique française.
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


def _looks_like_hub_page(title: str, company_normalized: str) -> bool:
    title_n = _normalize(title)
    if title_n.strip() == company_normalized:
        return True
    if title_n.startswith("actions ") or title_n.startswith("action "):
        return True
    if "actualit" in title_n and any(m in title_n for m in _HUB_TITLE_MARKERS):
        return True
    return False


def collect_press(
    client: TavilyClient, company: str, lang: str, max_results: int = DEFAULT_MAX_RESULTS
) -> dict:
    """Retourne les articles de presse récents sur `company`, restreints aux
    grands médias, avec un résumé du jour généré par Tavily.

    Quand la couverture presse d'une entreprise est faible, l'API Tavily peut
    dériver vers des résultats thématiquement proches mais sans rapport : on
    filtre donc pour ne garder que les résultats qui mentionnent réellement
    l'entreprise, quitte à renvoyer une liste vide plutôt que du bruit. On
    écarte aussi les pages "hub" (flux d'actualités d'une valeur boursière)
    au profit de vrais titres d'articles.

    Retourne {"results": [...], "answer": str | None}.
    """
    query = NEWS_QUERY[lang].format(company=company)
    data = client.search(
        query,
        topic=SEARCH_TOPIC[lang],
        max_results=max_results,
        include_domains=MAJOR_NEWS_DOMAINS[lang],
        include_answer=True,
    )
    results = data.get("results", [])
    needle = _normalize(company)
    filtered = [
        r
        for r in results
        if needle in _normalize(r.get("title", "") + " " + r.get("content", ""))
        and not _looks_like_hub_page(r.get("title", ""), needle)
    ]
    return {"results": filtered, "answer": data.get("answer") or None}
