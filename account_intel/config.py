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
    linkedin_mcp_command: Optional[str]
    clients_path: str


def load_settings() -> Settings:
    load_dotenv()

    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not tavily_key:
        raise ConfigError(
            "Clé API manquante : TAVILY_API_KEY. "
            "Copiez .env.example vers .env et renseignez vos clés."
        )

    default_lang = os.getenv("DEFAULT_LANG", "fr").strip().lower()
    if default_lang not in SUPPORTED_LANGS:
        raise ConfigError(
            f"DEFAULT_LANG={default_lang!r} non supporté (valeurs possibles : "
            f"{', '.join(SUPPORTED_LANGS)})."
        )

    return Settings(
        tavily_api_key=tavily_key,
        default_lang=default_lang,
        # Extension optionnelle et NON conforme aux CGU LinkedIn — voir LINKEDIN_MCP.md.
        # Commande pour lancer un serveur MCP tiers déjà installé/configuré à part
        # (ex. "node /chemin/vers/linkedin-mcpserver/build/index.js").
        linkedin_mcp_command=os.getenv("LINKEDIN_MCP_COMMAND", "").strip() or None,
        clients_path=os.getenv("CLIENTS_PATH", "").strip() or DEFAULT_CLIENTS_PATH,
    )
