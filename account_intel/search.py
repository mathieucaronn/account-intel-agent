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


# Tavily ne fournit jamais de published_date structurée en mode de recherche
# générale (communiqués officiels, réseaux sociaux) : on tente d'en extraire
# une du texte lui-même (souvent présente, ex. "13 février 2026", "27 Sep
# 2019"), en best-effort — absente si le texte ne contient pas de date
# reconnaissable.
_MONTHS = {
    "janvier": 1, "janv": 1, "jan": 1,
    "fevrier": 2, "fev": 2, "fevr": 2, "feb": 2, "february": 2,
    "mars": 3, "mar": 3, "march": 3,
    "avril": 4, "avr": 4, "apr": 4, "april": 4,
    "mai": 5, "may": 5,
    "juin": 6, "jun": 6, "june": 6,
    "juillet": 7, "juil": 7, "jul": 7, "july": 7,
    "aout": 8, "aug": 8, "august": 8,
    "septembre": 9, "sept": 9, "sep": 9, "september": 9,
    "octobre": 10, "oct": 10, "october": 10,
    "novembre": 11, "nov": 11, "november": 11,
    "decembre": 12, "dec": 12, "december": 12,
}
_DATE_DMY_RE = re.compile(r"\b(\d{1,2})(?:er)?\s+([A-Za-zéûôîàè]{3,10})\.?\s+(\d{4})\b")
_DATE_MDY_RE = re.compile(r"\b([A-Za-zéûôîàè]{3,10})\.?\s+(\d{1,2}),?\s+(\d{4})\b")
_DATE_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _extract_date(text: str) -> str:
    iso = _DATE_ISO_RE.search(text)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
    for pattern, order in ((_DATE_DMY_RE, "dmy"), (_DATE_MDY_RE, "mdy")):
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groups()
        day, month_raw, year = groups if order == "dmy" else (groups[1], groups[0], groups[2])
        month = _MONTHS.get(_normalize(month_raw).strip())
        if month and 1 <= int(day) <= 31 and 2000 <= int(year) <= 2100:
            return f"{int(year):04d}-{month:02d}-{int(day):02d}"
    return ""


def _with_extracted_dates(results: list) -> list:
    for r in results:
        if not r.get("published_date"):
            r["published_date"] = _extract_date(r.get("title", "") + " " + r.get("content", ""))
    return results


def collect_press(
    client: TavilyClient,
    company: str,
    lang: str,
    french_max_results: int = 10,
    international_max_results: int = 12,
) -> dict:
    """Retourne les articles de presse récents sur `company`, restreints aux
    grands médias, avec un résumé du jour généré par Tavily.

    En français (`lang="fr"`) : presse française en priorité, complétée par
    les grands médias États-Unis/Royaume-Uni/tech (couverture mondiale déjà
    demandée). En anglais (`lang="en"`) : uniquement les médias
    internationaux, pour un dashboard entièrement en anglais.

    Retourne {"results": [...], "answer": str | None}.
    """
    query = NEWS_QUERY[lang].format(company=company)
    words = _name_words(company)

    # international_max_results volontairement large : avec une valeur trop
    # basse, Reuters/WSJ (les mieux classés sur ces mots-clés) monopolisent
    # les résultats et écrasent la diversité (Bloomberg, CNN, Forbes, BBC,
    # Guardian, presse tech...).
    intl_data = client.search(
        query,
        topic="news",
        max_results=international_max_results,
        include_domains=INTERNATIONAL_NEWS_DOMAINS,
        include_answer=True,
    )
    intl_results = _filter_results(intl_data.get("results", []), words)

    if lang != "fr":
        return {"results": intl_results, "answer": intl_data.get("answer") or None}

    # Le mode "news" de Tavily a un index très pauvre sur les seuls domaines
    # français (déjà constaté : dérive systématique vers du hors-sujet, quel
    # que soit le texte de la requête) ; le mode général y est nettement
    # plus fiable, au prix de l'absence de date de publication structurée
    # (compensée par extraction de date depuis le texte, voir plus bas).
    french_data = client.search(
        query,
        topic="general",
        max_results=french_max_results,
        include_domains=FRENCH_NEWS_DOMAINS,
        include_answer=True,
    )
    french_results = _with_extracted_dates(
        _filter_results(french_data.get("results", []), words, drop_hub_pages=True)
    )
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
    results = _filter_results(data.get("results", []), words, drop_hub_pages=True)
    return _with_extracted_dates(results)


def collect_social(client: TavilyClient, company: str, lang: str, max_results: int = 10) -> list:
    """Retourne des publications publiques (LinkedIn, X, YouTube, Instagram,
    Facebook) mentionnant l'entreprise, telles qu'indexées par Tavily —
    aucune connexion ni automatisation de ces plateformes."""
    query = SOCIAL_QUERY[lang].format(company=company)
    data = client.search(
        query, topic="general", max_results=max_results, include_domains=SOCIAL_DOMAINS
    )
    words = _name_words(company)
    results = _filter_results(data.get("results", []), words)
    return _with_extracted_dates(results)
