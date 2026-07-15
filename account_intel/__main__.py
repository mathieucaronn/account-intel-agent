"""Point d'entrée CLI : python -m account_intel [entreprises ad hoc...]

Régénère le dashboard HTML (presse + LinkedIn) pour les clients suivis dans
clients.json, plus d'éventuelles entreprises ponctuelles passées en argument.
"""

import argparse
import sys

from . import clients as clients_module
from . import config, dashboard, search


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m account_intel",
        description=(
            "Régénère le dashboard HTML de revue de presse et de posts "
            "LinkedIn pour les équipes sales, à partir de données publiques."
        ),
    )
    parser.add_argument(
        "company",
        nargs="*",
        help=(
            "entreprise(s) ponctuelle(s) à inclure dans ce dashboard en plus "
            "des clients suivis (clients.json), sans les y enregistrer"
        ),
    )
    parser.add_argument(
        "--add",
        action="append",
        default=[],
        metavar="ENTREPRISE",
        help="ajoute durablement cette entreprise à clients.json (répétable)",
    )
    parser.add_argument(
        "--lang",
        choices=config.SUPPORTED_LANGS,
        help="langue du dashboard (défaut : DEFAULT_LANG du .env, sinon fr)",
    )
    parser.add_argument(
        "--out",
        default="output/dashboard.html",
        help="chemin du fichier HTML généré (défaut : output/dashboard.html)",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        settings = config.load_settings()
    except config.ConfigError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2

    lang = args.lang or settings.default_lang

    try:
        tracked = clients_module.load_clients(settings.clients_path)
    except clients_module.ClientsConfigError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2

    for name in args.add:
        clients_module.add_client(name, settings.clients_path)
        print(f"➕ « {name} » ajouté à {settings.clients_path}")
        tracked = clients_module.load_clients(settings.clients_path)

    ad_hoc = [clients_module.Client(name=c.strip(), executives=[]) for c in args.company if c.strip()]
    all_clients = tracked + ad_hoc

    if not all_clients:
        print(
            "⚠️  Aucun client suivi et aucune entreprise passée en argument. "
            "Copiez clients.example.json vers clients.json, ou lancez avec des "
            "noms d'entreprise en argument.",
            file=sys.stderr,
        )

    linkedin_enabled = bool(settings.linkedin_mcp_command)
    if linkedin_enabled and any(c.executives for c in all_clients):
        print(
            "⚠️  Extension LinkedIn activée : NON CONFORME AUX CGU LINKEDIN "
            "(scraping via credentials personnels, risque de bannissement de "
            "compte). Voir LINKEDIN_MCP.md. Poursuite à vos risques.",
            file=sys.stderr,
        )

    tavily_client = search.TavilyClient(settings.tavily_api_key)
    clients_data = []
    for c in all_clients:
        print(f"🔎 Collecte pour « {c.name} »...")
        data = dashboard.collect_client(
            tavily_client, settings.linkedin_mcp_command, c.name, c.executives, lang
        )
        if data.press_error:
            print(f"⚠️  {c.name} : {data.press_error}", file=sys.stderr)
        for entry in data.linkedin:
            if entry["status"] == "error":
                print(f"⚠️  {c.name} / {entry['person']} : {entry['error']}", file=sys.stderr)
        clients_data.append(data)

    html_content = dashboard.render_html(clients_data, lang, linkedin_enabled)
    out_path = dashboard.write_dashboard(html_content, args.out)
    print(f"✅ Dashboard généré : {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
