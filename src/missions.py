"""Missions : 3 objectifs à accomplir en une partie. Logique pure, testable.

Chaque mission porte sur une statistique de la partie (pièces, distance, sauts,
bonus, jetpacks, score). Quand les 3 sont accomplies, un nouveau lot un cran
plus difficile est généré (niveau +1). L'état est sérialisable en JSON.
"""
import random

# clé -> (modèle de texte, paliers par niveau)
METRICS = {
    "coins": ("Ramasse {t} pièces en une partie", [15, 25, 40, 60, 90]),
    "meters": ("Cours {t} m en une partie", [400, 700, 1100, 1600, 2200]),
    "jumps": ("Fais {t} sauts en une partie", [8, 12, 18, 25, 35]),
    "powerups": ("Ramasse {t} bonus en une partie", [2, 3, 4, 5, 6]),
    "jetpacks": ("Prends {t} jetpack(s) en une partie", [1, 1, 2, 2, 3]),
    "score": ("Atteins {t} points en une partie", [300, 600, 1000, 1600, 2400]),
}
_ORDER = list(METRICS)


def _target(key: str, level: int) -> int:
    tiers = METRICS[key][1]
    return tiers[min(level, len(tiers) - 1)]


def generate_set(level: int, rng: random.Random | None = None) -> list[dict]:
    """Trois missions distinctes pour ce niveau."""
    rng = rng or random.Random(level)
    keys = rng.sample(_ORDER, 3)
    out = []
    for key in keys:
        t = _target(key, level)
        out.append({"key": key, "target": t, "text": METRICS[key][0].format(t=t), "done": False})
    return out


def progress(mission: dict, stats: dict) -> tuple[int, int]:
    """(valeur actuelle plafonnée, cible) pour l'affichage d'une jauge."""
    cur = min(int(stats.get(mission["key"], 0)), mission["target"])
    return cur, mission["target"]


def update_after_run(save: dict, stats: dict) -> dict:
    """Met à jour les missions avec les stats de la partie.

    Renvoie {"completed": [textes accomplis cette partie], "leveled_up": bool}.
    Modifie `save` en place (clés "missions" et "mission_level").
    """
    missions = save.get("missions") or generate_set(0)
    level = int(save.get("mission_level", 0))
    completed = []
    for m in missions:
        if not m["done"] and int(stats.get(m["key"], 0)) >= m["target"]:
            m["done"] = True
            completed.append(m["text"])
    leveled_up = bool(missions) and all(m["done"] for m in missions)
    if leveled_up:
        level += 1
        missions = generate_set(level)
    save["missions"] = missions
    save["mission_level"] = level
    return {"completed": completed, "leveled_up": leveled_up}
