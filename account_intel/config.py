"""Chargement de la configuration depuis les variables d'environnement / .env."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

DEFAULT_MODEL = "claude-sonnet-5"
SUPPORTED_LANGS = ("fr", "en")


class ConfigError(Exception):
    """Configuration invalide ou clé API manquante."""


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    tavily_api_key: str
    model: str
    default_lang: str
    linkedin_mcp_command: Optional[str]


def load_settings() -> Settings:
    load_dotenv()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()

    missing = [
        name
        for name, value in (
            ("ANTHROPIC_API_KEY", anthropic_key),
            ("TAVILY_API_KEY", tavily_key),
        )
        if not value
    ]
    if missing:
        raise ConfigError(
            f"Clé(s) API manquante(s) : {', '.join(missing)}. "
            "Copiez .env.example vers .env et renseignez vos clés."
        )

    default_lang = os.getenv("DEFAULT_LANG", "fr").strip().lower()
    if default_lang not in SUPPORTED_LANGS:
        raise ConfigError(
            f"DEFAULT_LANG={default_lang!r} non supporté (valeurs possibles : "
            f"{', '.join(SUPPORTED_LANGS)})."
        )

    return Settings(
        anthropic_api_key=anthropic_key,
        tavily_api_key=tavily_key,
        model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        default_lang=default_lang,
        # Extension optionnelle et NON conforme aux CGU LinkedIn — voir LINKEDIN_MCP.md.
        # Commande pour lancer un serveur MCP tiers déjà installé/configuré à part
        # (ex. "node /chemin/vers/linkedin-mcpserver/build/index.js").
        linkedin_mcp_command=os.getenv("LINKEDIN_MCP_COMMAND", "").strip() or None,
    )
