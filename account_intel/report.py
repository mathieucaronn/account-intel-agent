"""Écriture de la fiche : fichier Markdown + conversion PDF."""

import re
import unicodedata
from datetime import date
from pathlib import Path

PDF_CSS = """
body { font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; }
h1 { font-size: 18pt; border-bottom: 2px solid #1a3c6e; padding-bottom: 6px; }
h2 { font-size: 14pt; color: #1a3c6e; margin-top: 18px; }
a { color: #1a5fb4; }
li { margin-bottom: 4px; }
"""

HEADERS = {
    "fr": "# Fiche account intelligence — {company}\n\n*Générée le {date} à partir de données publiques.*\n\n",
    "en": "# Account intelligence brief — {company}\n\n*Generated on {date} from public data.*\n\n",
}


def slugify(name: str) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or "entreprise"


def write_report(
    company: str, body_markdown: str, out_dir: str, lang: str, make_pdf: bool = True
) -> dict:
    """Écrit la fiche .md (et .pdf si demandé). Retourne
    {"md": Path, "pdf": Path | None, "pdf_error": str | None}."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    full_markdown = (
        HEADERS[lang].format(company=company, date=today) + body_markdown + "\n"
    )

    base = out_path / f"{slugify(company)}-{today}"
    md_path = base.with_suffix(".md")
    md_path.write_text(full_markdown, encoding="utf-8")

    pdf_path, pdf_error = None, None
    if make_pdf:
        try:
            pdf_path = _write_pdf(full_markdown, base.with_suffix(".pdf"))
        except Exception as exc:  # le PDF ne doit jamais faire échouer la fiche
            pdf_error = str(exc)

    return {"md": md_path, "pdf": pdf_path, "pdf_error": pdf_error}


def _write_pdf(markdown_text: str, pdf_path: Path) -> Path:
    from markdown_pdf import MarkdownPdf, Section

    pdf = MarkdownPdf(toc_level=0)
    pdf.add_section(Section(markdown_text), user_css=PDF_CSS)
    pdf.save(str(pdf_path))
    return pdf_path
