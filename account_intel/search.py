"""Collecte de données publiques via l'API Tavily (recherche web, presse,
extraction du contenu des pages du site officiel)."""

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests

SEARCH_URL = "https://api.tavily.com/search"
EXTRACT_URL = "https://api.tavily.com/extract"
TIMEOUT_SECONDS = 30
NEWS_LOOKBACK_DAYS = 180
MAX_PAGE_CHARS = 5000  # contenu max conservé par page extraite

# Domaines de référence/presse/réseaux fréquemment renvoyés en tête de
# recherche mais qui ne sont jamais le site officiel de l'entreprise.
NON_OFFICIAL_DOMAINS = (
    "wikipedia.org",
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "instagram.com",
    "crunchbase.com",
    "bloomberg.com",
    "reuters.com",
    "forbes.com",
    "glassdoor.com",
    "indeed.com",
    "prnewswire.com",
    "businesswire.com",
    "marketscreener.com",
    "biospace.com",
    "pitchbook.com",
    "societe.com",
    "infogreffe.fr",
    "pappers.fr",
    "data.gouv.fr",
    "google.com",
)

_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_ANCHOR_LINK_RE = re.compile(r"\[([^\]]*)\]\(#[^)]*\)")
_MD_RELATIVE_LINK_RE = re.compile(r"\[([^\]]*)\]\((?!https?://)[^)]*\)")


def _is_official_domain(domain: str) -> bool:
    domain = domain.lower()
    return not any(
        domain == d or domain.endswith(f".{d}") for d in NON_OFFICIAL_DOMAINS
    )


def _sanitize_extracted_markdown(text: str) -> str:
    """Retire le bruit typique des pages extraites (images, ancres internes
    et liens relatifs cassés) qui peut polluer le prompt LLM et faire
    planter la conversion PDF en mode --no-llm."""
    text = _MD_IMAGE_RE.sub("", text)
    text = _MD_ANCHOR_LINK_RE.sub(r"\1", text)
    text = _MD_RELATIVE_LINK_RE.sub(r"\1", text)
    return text


class SearchError(Exception):
    """Erreur d'accès à l'API de recherche (réseau, quota, clé invalide...)."""


class CompanyNotFoundError(Exception):
    """Aucune information publique trouvée pour cette entreprise."""


# Requêtes par thème et par langue.
QUERIES = {
    "profile": {
        "fr": "{company} entreprise société activité produits services site officiel",
        "en": "{company} company products services official website",
    },
    "news": {
        "fr": "{company} actualité levée de fonds partenariat nomination résultats",
        "en": "{company} news funding partnership appointment earnings",
    },
    "leadership": {
        "fr": "{company} dirigeants CEO fondateur équipe de direction interview",
        "en": "{company} executives CEO founder leadership team interview",
    },
}


@dataclass
class ResearchBundle:
    """Données brutes collectées, prêtes à être synthétisées."""

    company: str
    profile: dict = field(default_factory=dict)
    news: dict = field(default_factory=dict)
    leadership: dict = field(default_factory=dict)
    pages: list = field(default_factory=list)  # [{"url", "content"}]
    linkedin: list = field(default_factory=list)  # [{"person", "tool", "content"}]
    warnings: list = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (
            self.profile.get("results")
            or self.news.get("results")
            or self.leadership.get("results")
            or self.pages
        )

    def to_prompt_text(self) -> str:
        """Met en forme les données collectées pour le prompt de synthèse."""
        blocks = [f"ENTREPRISE RECHERCHÉE : {self.company}"]

        for title, payload in (
            ("PROFIL / RECHERCHE GÉNÉRALE", self.profile),
            ("PRESSE RÉCENTE (6 derniers mois)", self.news),
            ("DIRIGEANTS", self.leadership),
        ):
            lines = [f"=== {title} ==="]
            if payload.get("answer"):
                lines.append(f"Résumé du moteur de recherche : {payload['answer']}")
            for result in payload.get("results", []):
                date = result.get("published_date")
                date_str = f" ({date})" if date else ""
                lines.append(
                    f"- {result.get('title', 'Sans titre')}{date_str}\n"
                    f"  Source : {result.get('url', '?')}\n"
                    f"  Extrait : {result.get('content', '').strip()}"
                )
            if len(lines) == 1:
                lines.append("(aucun résultat)")
            blocks.append("\n".join(lines))

        page_lines = ["=== CONTENU DU SITE OFFICIEL ==="]
        for page in self.pages:
            page_lines.append(f"--- Page : {page['url']} ---\n{page['content']}")
        if len(page_lines) == 1:
            page_lines.append("(aucune page extraite)")
        blocks.append("\n".join(page_lines))

        if self.linkedin:
            li_lines = [
                "=== LINKEDIN (source tierce non officielle, hors CGU LinkedIn — "
                "à mentionner comme telle, ne pas citer d'URL LinkedIn précise) ==="
            ]
            for entry in self.linkedin:
                li_lines.append(f"--- {entry['person']} ---\n{entry['content']}")
            blocks.append("\n".join(li_lines))

        return "\n\n".join(blocks)


class TavilyClient:
    def __init__(self, api_key: str):
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _post(self, url: str, payload: dict) -> dict:
        try:
            response = self._session.post(url, json=payload, timeout=TIMEOUT_SECONDS)
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

    def search(self, query: str, *, topic: str = "general", max_results: int = 5) -> dict:
        payload = {
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "include_answer": True,
        }
        if topic == "news":
            payload["days"] = NEWS_LOOKBACK_DAYS
        return self._post(SEARCH_URL, payload)

    def extract(self, urls: list) -> list:
        """Retourne le contenu textuel propre des URLs demandées."""
        data = self._post(EXTRACT_URL, {"urls": urls})
        return [
            {
                "url": item.get("url", "?"),
                "content": _sanitize_extracted_markdown(item["raw_content"])[
                    :MAX_PAGE_CHARS
                ],
            }
            for item in data.get("results", [])
            if item.get("raw_content")
        ]


def _official_site_urls(profile: dict, max_urls: int = 3) -> list:
    """Heuristique : le 1er résultat de la recherche profil dont le domaine
    n'est pas une référence/presse/réseau connue (Wikipédia, LinkedIn...) est
    présumé être le site officiel ; on retient les résultats partageant ce
    même domaine."""
    results = profile.get("results", [])
    domain = next(
        (
            urlparse(r["url"]).netloc
            for r in results
            if r.get("url") and _is_official_domain(urlparse(r["url"]).netloc)
        ),
        None,
    )
    if not domain:
        return []
    urls = [
        r["url"]
        for r in results
        if r.get("url") and urlparse(r["url"]).netloc == domain
    ]
    return urls[:max_urls]


def collect(client: TavilyClient, company: str, lang: str) -> ResearchBundle:
    """Lance les recherches thématiques et l'extraction du site officiel.

    Une recherche thématique qui échoue est signalée en warning ; on n'échoue
    globalement que si aucune donnée n'a pu être collectée.
    """
    bundle = ResearchBundle(company=company)

    searches = (
        ("profile", "general"),
        ("news", "news"),
        ("leadership", "general"),
    )
    for theme, topic in searches:
        query = QUERIES[theme][lang].format(company=company)
        try:
            setattr(bundle, theme, client.search(query, topic=topic))
        except SearchError as exc:
            bundle.warnings.append(f"Recherche « {theme} » échouée : {exc}")

    site_urls = _official_site_urls(bundle.profile)
    if site_urls:
        try:
            bundle.pages = client.extract(site_urls)
        except SearchError as exc:
            bundle.warnings.append(f"Extraction du site officiel échouée : {exc}")

    if bundle.is_empty():
        raise CompanyNotFoundError(
            f"Aucune information publique trouvée pour « {company} ». "
            "Vérifiez l'orthographe ou essayez avec le nom légal complet."
        )
    return bundle
