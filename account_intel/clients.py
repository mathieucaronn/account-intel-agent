"""Chargement / mise à jour de la liste des clients suivis (clients.json)."""

import json
from dataclasses import dataclass
from pathlib import Path


class ClientsConfigError(Exception):
    """Fichier de clients invalide (JSON malformé)."""


@dataclass
class Client:
    name: str
    executives: list


def load_clients(path: str) -> list:
    """Retourne les clients suivis. Fichier absent → liste vide (pas une erreur :
    l'utilisateur peut n'avoir configuré aucun client suivi et n'utiliser que
    la recherche ponctuelle en argument de la CLI)."""
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ClientsConfigError(f"{path} n'est pas un JSON valide : {exc}") from exc
    return [
        Client(name=entry["name"], executives=list(entry.get("executives", [])))
        for entry in raw
    ]


def add_client(name: str, path: str) -> None:
    """Ajoute un client (sans dirigeants) au fichier de config, sauf s'il y
    est déjà. Crée le fichier s'il n'existe pas."""
    clients = load_clients(path)
    if any(c.name.lower() == name.lower() for c in clients):
        return
    clients.append(Client(name=name, executives=[]))
    save_clients(clients, path)


def save_clients(clients: list, path: str) -> None:
    payload = [{"name": c.name, "executives": c.executives} for c in clients]
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
