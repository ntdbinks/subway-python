"""Sauvegarde du meilleur score et des statistiques (JSON)."""
import json
from pathlib import Path

from . import config as C

DEFAULT = {"best_score": 0, "total_coins": 0, "games_played": 0}


def load(path: Path = C.SAVE_FILE) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {**DEFAULT, **{k: int(v) for k, v in data.items() if k in DEFAULT}}
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT)


def save(data: dict, path: Path = C.SAVE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)  # écriture atomique : pas de fichier corrompu en cas de crash


def record_game(data: dict, score: int, coins: int) -> bool:
    """Met à jour les stats ; renvoie True si nouveau record."""
    data["games_played"] += 1
    data["total_coins"] += coins
    if score > data["best_score"]:
        data["best_score"] = score
        return True
    return False
