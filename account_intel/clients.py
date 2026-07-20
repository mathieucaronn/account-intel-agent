"""Chargement / mise à jour de la liste des clients suivis (clients.json)."""

import json
from pathlib import Path


class ClientsConfigError(Exception):
    """Fichier de clients invalide (JSON malformé)."""


def load_clients(path: str) -> list:
    """Retourne les noms des clients suivis. Fichier absent → liste vide (pas
    une erreur : l'utilisateur peut n'utiliser que la recherche ponctuelle en
    argument de la CLI)."""
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ClientsConfigError(f"{path} n'est pas un JSON valide : {exc}") from exc
    return [entry.strip() for entry in raw if isinstance(entry, str) and entry.strip()]


def add_client(name: str, path: str) -> None:
    """Ajoute un client au fichier de config, sauf s'il y est déjà. Crée le
    fichier s'il n'existe pas."""
    clients = load_clients(path)
    if any(c.lower() == name.lower() for c in clients):
        return
    clients.append(name)
    save_clients(clients, path)


def save_clients(clients: list, path: str) -> None:
    Path(path).write_text(
        json.dumps(clients, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
