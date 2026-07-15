"""Chargement de la configuration depuis les variables d'environnement / .env."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
SUPPORTED_LANGS = ("fr", "en")
SUPPORTED_BACKENDS = ("anthropic", "ollama")


class ConfigError(Exception):
    """Configuration invalide ou clé API manquante."""


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: Optional[str]
    tavily_api_key: str
    model: str
    default_lang: str
    linkedin_mcp_command: Optional[str]
    llm_backend: str
    ollama_model: str
    ollama_base_url: str


def load_settings() -> Settings:
    """Charge la configuration. Seule TAVILY_API_KEY est toujours requise :
    la recherche publique est nécessaire dans tous les modes. La
    disponibilité d'ANTHROPIC_API_KEY (requise uniquement pour le backend
    "anthropic") est validée par l'appelant selon le mode choisi
    (--no-llm, --backend ollama...)."""
    load_dotenv()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
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

    llm_backend = os.getenv("LLM_BACKEND", "anthropic").strip().lower()
    if llm_backend not in SUPPORTED_BACKENDS:
        raise ConfigError(
            f"LLM_BACKEND={llm_backend!r} non supporté (valeurs possibles : "
            f"{', '.join(SUPPORTED_BACKENDS)})."
        )

    return Settings(
        anthropic_api_key=anthropic_key or None,
        tavily_api_key=tavily_key,
        model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        default_lang=default_lang,
        # Extension optionnelle et NON conforme aux CGU LinkedIn — voir LINKEDIN_MCP.md.
        # Commande pour lancer un serveur MCP tiers déjà installé/configuré à part
        # (ex. "node /chemin/vers/linkedin-mcpserver/build/index.js").
        linkedin_mcp_command=os.getenv("LINKEDIN_MCP_COMMAND", "").strip() or None,
        llm_backend=llm_backend,
        ollama_model=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
        or DEFAULT_OLLAMA_MODEL,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).strip()
        or DEFAULT_OLLAMA_BASE_URL,
    )
