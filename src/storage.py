"""Sauvegarde du meilleur score, des statistiques et des missions (JSON)."""
import json
from pathlib import Path

from . import config as C
from . import missions as M

DEFAULT = {"best_score": 0, "total_coins": 0, "games_played": 0}


def load(path: Path = C.SAVE_FILE) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        out = {**DEFAULT, **{k: int(v) for k, v in data.items() if k in DEFAULT}}
        out["mission_level"] = int(data.get("mission_level", 0))
        out["character"] = int(data.get("character", 0))
        ms = data.get("missions")
        out["missions"] = ms if isinstance(ms, list) and ms else M.generate_set(out["mission_level"])
    except (OSError, ValueError, TypeError):
        out = dict(DEFAULT)
        out["mission_level"] = 0
        out["missions"] = M.generate_set(0)
        out["character"] = 0
    return out


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
