"""Serveur HTTP local minimal (bibliothèque standard uniquement) pour la
recherche ponctuelle d'entreprise depuis le dashboard. La clé Tavily reste
côté serveur : elle n'est jamais envoyée au navigateur."""

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import dashboard


def _make_handler(tavily_client, linkedin_command: str, lang: str, serve_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # les logs par défaut du serveur stdlib sont trop bruyants ici

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/search":
                self._handle_search(parse_qs(parsed.query))
            else:
                self._serve_static(parsed.path)

        def _handle_search(self, query: dict) -> None:
            company = query.get("company", [""])[0].strip()
            if not company:
                self._json({"error": "missing company"}, status=400)
                return
            data = dashboard.collect_client(
                tavily_client, linkedin_command, company, [], lang
            )
            labels = dashboard.LABELS[lang]
            self._json(
                {
                    "name": data.name,
                    "press_html": dashboard.render_press(data, labels),
                    "linkedin_html": dashboard.render_linkedin(
                        data, labels, bool(linkedin_command)
                    ),
                }
            )

        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_static(self, path: str) -> None:
            if path == "/":
                path = "/dashboard.html"
            file_path = (serve_dir / path.lstrip("/")).resolve()
            if not file_path.is_relative_to(serve_dir.resolve()) or not file_path.is_file():
                self.send_error(404)
                return
            content_type = (
                "text/html; charset=utf-8" if file_path.suffix == ".html" else "application/octet-stream"
            )
            body = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def run(tavily_client, linkedin_command: str, lang: str, serve_dir: str, port: int = 8000) -> None:
    handler = _make_handler(tavily_client, linkedin_command, lang, Path(serve_dir))
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as exc:
        raise RuntimeError(
            f"Impossible de démarrer le serveur sur le port {port} ({exc}). "
            "Essayez --port avec un autre numéro."
        ) from exc

    url = f"http://127.0.0.1:{port}/dashboard.html"
    print(f"🌐 Dashboard servi sur {url} (Ctrl+C pour arrêter)")
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Serveur arrêté.")
    finally:
        httpd.server_close()
