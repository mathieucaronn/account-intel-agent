"""Connecteur OPTIONNEL vers un serveur MCP tiers pour récupérer les posts
LinkedIn récents d'un dirigeant (par défaut : stickerdaniel/linkedin-mcp-server).

⚠️  NON CONFORME AUX CGU DE LINKEDIN — désactivé par défaut, non installé par
défaut, non recommandé pour un usage en équipe ou en production.

Ce serveur n'utilise PAS l'API officielle LinkedIn : il pilote un navigateur
Chromium automatisé (Patchright, conçu pour échapper à la détection anti-bot)
avec la session LinkedIn personnelle de l'utilisateur (connexion réelle ou
cookies importés d'un navigateur déjà connecté). Cela contrevient à
l'article 8.2 du LinkedIn User Agreement (interdiction du scraping et de
l'automatisation) et expose le compte utilisé à une restriction/bannissement.
Voir LINKEDIN_MCP.md.

Le tool ciblé est `get_person_profile` (paramètre `linkedin_username`,
`sections="posts"`), avec repli générique (découverte via `list_tools()`) si
le nom ou le schéma du tool diffère selon la version du serveur installé.
"""

import asyncio
import shlex

PREFERRED_TOOL_NAME = "get_person_profile"
PREFERRED_ARG_NAME = "linkedin_username"
POSTS_SECTIONS = "posts"

PROFILE_TOOL_HINTS = ("profile", "person")
EXCLUDED_HINTS = ("message", "job")
QUERY_ARG_CANDIDATES = ("linkedin_username", "query", "username", "name", "url")


class LinkedInMCPError(Exception):
    """Erreur de connexion ou d'appel au serveur MCP LinkedIn tiers."""


def fetch_profile(command: str, linkedin_username: str) -> dict:
    """Interroge le serveur MCP tiers pour un dirigeant donné (identifié par
    son nom d'utilisateur LinkedIn, ex. "williamhgates").

    `command` est une commande shell complète (ex. "uvx mcp-server-linkedin@latest"),
    lancée en sous-processus via le protocole MCP (stdio). Lève
    LinkedInMCPError en cas d'échec ; ne lève jamais d'autre exception.
    """
    try:
        return asyncio.run(_fetch_async(command, linkedin_username))
    except LinkedInMCPError:
        raise
    except Exception as exc:  # protocole/sous-processus tiers non garanti
        raise LinkedInMCPError(f"Erreur MCP LinkedIn : {exc}") from exc


async def _fetch_async(command: str, linkedin_username: str) -> dict:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as exc:
        raise LinkedInMCPError(
            "Le paquet 'mcp' n'est pas installé. Installez la dépendance "
            "optionnelle : pip install -r requirements-linkedin.txt"
        ) from exc

    parts = shlex.split(command)
    if not parts:
        raise LinkedInMCPError("LINKEDIN_MCP_COMMAND est vide.")

    params = StdioServerParameters(command=parts[0], args=parts[1:])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            tool = _pick_profile_tool(tools)
            if tool is None:
                available = ", ".join(t.name for t in tools) or "(aucun)"
                raise LinkedInMCPError(
                    "Aucun tool de type récupération de profil trouvé parmi "
                    f"les tools exposés : {available}"
                )

            arg_name = _pick_arg_name(tool)
            call_args = {arg_name: linkedin_username}
            if tool.name == PREFERRED_TOOL_NAME:
                call_args["sections"] = POSTS_SECTIONS

            result = await session.call_tool(tool.name, call_args)
            return {"tool": tool.name, "content": _stringify(result)}


def _pick_profile_tool(tools):
    by_name = {t.name: t for t in tools}
    if PREFERRED_TOOL_NAME in by_name:
        return by_name[PREFERRED_TOOL_NAME]
    for tool in tools:
        name = tool.name.lower()
        if any(h in name for h in PROFILE_TOOL_HINTS) and not any(
            h in name for h in EXCLUDED_HINTS
        ):
            return tool
    return None


def _pick_arg_name(tool) -> str:
    schema = getattr(tool, "inputSchema", None) or {}
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    for candidate in QUERY_ARG_CANDIDATES:
        if candidate in props:
            return candidate
    return next(iter(props), PREFERRED_ARG_NAME)


def _stringify(result) -> str:
    chunks = [
        item.text
        for item in getattr(result, "content", []) or []
        if getattr(item, "text", None)
    ]
    return "\n".join(chunks) if chunks else str(result)
