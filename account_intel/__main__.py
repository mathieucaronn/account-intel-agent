"""Point d'entrée CLI : python -m account_intel "Nom de l'entreprise" """

import argparse
import sys

from . import config, report, search, synthesis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m account_intel",
        description=(
            "Génère une fiche de préparation de RDV commercial pour une "
            "entreprise, à partir de données publiques (site officiel, presse)."
        ),
    )
    parser.add_argument("company", help="nom de l'entreprise à analyser")
    parser.add_argument(
        "--lang",
        choices=config.SUPPORTED_LANGS,
        help="langue de la fiche (défaut : DEFAULT_LANG du .env, sinon fr)",
    )
    parser.add_argument(
        "--out", default="output", help="dossier de sortie (défaut : output/)"
    )
    parser.add_argument(
        "--no-pdf", action="store_true", help="ne générer que le Markdown"
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
    company = args.company.strip()
    if not company:
        print("❌ Le nom de l'entreprise ne peut pas être vide.", file=sys.stderr)
        return 2

    print(f"🔎 Collecte d'informations publiques sur « {company} »...")
    client = search.TavilyClient(settings.tavily_api_key)
    try:
        bundle = search.collect(client, company, lang)
    except search.CompanyNotFoundError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    except search.SearchError as exc:
        print(f"❌ Recherche impossible : {exc}", file=sys.stderr)
        return 1

    for warning in bundle.warnings:
        print(f"⚠️  {warning}", file=sys.stderr)
    n_news = len(bundle.news.get("results", []))
    print(f"   → {n_news} article(s) de presse, {len(bundle.pages)} page(s) du site officiel.")

    print(f"🧠 Synthèse de la fiche ({lang}) avec {settings.model}...")
    try:
        body = synthesis.generate_brief(settings, company, bundle.to_prompt_text(), lang)
    except synthesis.SynthesisError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    result = report.write_report(company, body, args.out, lang, make_pdf=not args.no_pdf)
    print(f"✅ Fiche Markdown : {result['md']}")
    if result["pdf"]:
        print(f"✅ Fiche PDF      : {result['pdf']}")
    elif result["pdf_error"]:
        print(f"⚠️  PDF non généré ({result['pdf_error']}), la fiche .md reste disponible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
