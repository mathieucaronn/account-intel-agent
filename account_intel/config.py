"""Chargement de la configuration depuis les variables d'environnement / .env."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

SUPPORTED_LANGS = ("fr", "en")
DEFAULT_CLIENTS_PATH = "clients.json"


class ConfigError(Exception):
    """Configuration invalide ou clé API manquante."""


@dataclass(frozen=True)
class Settings:
    tavily_api_key: str
    default_lang: str
    clients_path: str
    anthropic_api_key: Optional[str]


def load_settings() -> Settings:
    load_dotenv()

    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not tavily_key:
        raise ConfigError(
            "Clé API manquante : TAVILY_API_KEY. "
            "Copiez .env.example vers .env et renseignez vos clés."
        )

    default_lang = os.getenv("DEFAULT_LANG", "").strip().lower() or "fr"
    if default_lang not in SUPPORTED_LANGS:
        raise ConfigError(
            f"DEFAULT_LANG={default_lang!r} non supporté (valeurs possibles : "
            f"{', '.join(SUPPORTED_LANGS)})."
        )

    return Settings(
        tavily_api_key=tavily_key,
        default_lang=default_lang,
        clients_path=os.getenv("CLIENTS_PATH", "").strip() or DEFAULT_CLIENTS_PATH,
        # Optionnel : résumé du jour croisant presse/communiqués/réseaux
        # sociaux via Claude (voir account_intel/summary.py). Sans clé, repli
        # automatique sur le résumé Tavily existant.
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip() or None,
    )
