"""Connecteur OPTIONNEL vers un serveur MCP tiers (ex. felipfr/linkedin-mcpserver)
pour récupérer des informations de profils LinkedIn de dirigeants.

⚠️  NON CONFORME AUX CGU DE LINKEDIN — désactivé par défaut, non installé par
défaut, non recommandé pour un usage en équipe ou en production.

Les serveurs MCP « LinkedIn » de ce type n'utilisent en général PAS l'API
officielle LinkedIn pour la recherche/récupération de profils ou l'envoi de
messages (ces usages sont réservés à des partenariats LinkedIn encadrés).
Ils s'appuient typiquement sur les identifiants d'un compte personnel (cookie
de session) pour automatiser la navigation, ce qui contrevient à l'article
8.2 du LinkedIn User Agreement (interdiction du scraping et de
l'automatisation) et expose ce compte à un bannissement.

Ce module ne fait AUCUNE hypothèse figée sur le nom exact des tools exposés
par le serveur tiers (non documenté publiquement) : il les découvre à chaque
connexion via `list_tools()` et choisit heuristiquement celui qui ressemble
le plus à une recherche/récupération de profil. Voir LINKEDIN_MCP.md pour
l'installation du serveur tiers, qui reste un projet externe avec ses propres
identifiants (jamais stockés dans ce dépôt).
"""

import asyncio
import shlex

PROFILE_TOOL_HINTS = ("profile", "person")
EXCLUDED_HINTS = ("message", "job")
QUERY_ARG_CANDIDATES = ("query", "name", "keywords", "search", "q", "url")


class LinkedInMCPError(Exception):
    """Erreur de connexion ou d'appel au serveur MCP LinkedIn tiers."""


def fetch_profile(command: str, person_query: str) -> dict:
    """Interroge le serveur MCP tiers pour un dirigeant donné.

    `command` est une commande shell complète (ex. "node build/index.js"),
    lancée en sous-processus via le protocole MCP (stdio). Lève
    LinkedInMCPError en cas d'échec ; ne lève jamais d'autre exception.
    """
    try:
        return asyncio.run(_fetch_async(command, person_query))
    except LinkedInMCPError:
        raise
    except Exception as exc:  # protocole/sous-processus tiers non garanti
        raise LinkedInMCPError(f"Erreur MCP LinkedIn : {exc}") from exc


async def _fetch_async(command: str, person_query: str) -> dict:
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
                    "Aucun tool de type recherche/récupération de profil "
                    f"trouvé parmi les tools exposés : {available}"
                )
            arg_name = _guess_query_arg(tool)
            result = await session.call_tool(tool.name, {arg_name: person_query})
            return {"tool": tool.name, "content": _stringify(result)}


def _pick_profile_tool(tools):
    for tool in tools:
        name = tool.name.lower()
        if any(h in name for h in PROFILE_TOOL_HINTS) and not any(
            h in name for h in EXCLUDED_HINTS
        ):
            return tool
    return None


def _guess_query_arg(tool) -> str:
    schema = getattr(tool, "inputSchema", None) or {}
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    for candidate in QUERY_ARG_CANDIDATES:
        if candidate in props:
            return candidate
    return next(iter(props), "query")


def _stringify(result) -> str:
    chunks = [
        item.text
        for item in getattr(result, "content", []) or []
        if getattr(item, "text", None)
    ]
    return "\n".join(chunks) if chunks else str(result)
