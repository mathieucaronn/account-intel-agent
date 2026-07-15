"""Collecte de presse publique via l'API Tavily."""

import unicodedata

import requests

SEARCH_URL = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 30
NEWS_LOOKBACK_DAYS = 180


class SearchError(Exception):
    """Erreur d'accès à l'API de recherche (réseau, quota, clé invalide...)."""


NEWS_QUERY = {
    "fr": "{company} actualité levée de fonds partenariat nomination résultats",
    "en": "{company} news funding partnership appointment earnings",
}


class TavilyClient:
    def __init__(self, api_key: str):
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}"})

    def search(self, query: str, *, topic: str = "general", max_results: int = 8) -> dict:
        payload = {
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "include_answer": False,
        }
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
    return text.lower()


def collect_press(client: TavilyClient, company: str, lang: str, max_results: int = 8) -> list:
    """Retourne les articles de presse récents (6 derniers mois) sur `company`.

    Quand la couverture presse d'une entreprise est faible, l'API Tavily peut
    dériver vers des résultats thématiquement proches mais sans rapport
    (observé sur des entreprises peu couvertes en presse anglophone) : on
    filtre donc pour ne garder que les résultats qui mentionnent réellement
    l'entreprise, quitte à renvoyer une liste vide plutôt que du bruit."""
    query = NEWS_QUERY[lang].format(company=company)
    data = client.search(query, topic="news", max_results=max_results)
    results = data.get("results", [])
    needle = _normalize(company)
    return [
        r
        for r in results
        if needle in _normalize(r.get("title", "") + " " + r.get("content", ""))
    ]
