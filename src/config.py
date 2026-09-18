"""Paramètres centralisés du jeu."""
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if getattr(sys, "frozen", False):
    # version .exe : sauvegarde dans le profil utilisateur (toujours accessible en écriture)
    DATA_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / "SubwayPython"
else:
    DATA_DIR = ROOT_DIR / "data"
SAVE_FILE = DATA_DIR / "save.json"

# Fenêtre
WIDTH, HEIGHT = 800, 600
FPS = 60
TITLE = "Subway Python"

# Voies (3 couloirs)
LANE_COUNT = 3
LANE_WIDTH = 130
TRACK_LEFT = (WIDTH - LANE_COUNT * LANE_WIDTH) // 2
LANES_X = [TRACK_LEFT + LANE_WIDTH * i + LANE_WIDTH // 2 for i in range(LANE_COUNT)]

# Joueur
PLAYER_Y = 500
PLAYER_SIZE = (54, 54)
LANE_SWITCH_TIME = 0.12      # secondes pour changer de voie
JUMP_VELOCITY = 620          # px/s (hauteur « virtuelle »)
GRAVITY = 1900               # px/s²
SLIDE_TIME = 0.6             # secondes
JUMP_CLEARANCE = 38          # hauteur mini pour franchir une barrière basse

# Défilement / difficulté
START_SPEED = 250            # px/s
MAX_SPEED = 680
SPEED_GAIN = 6               # px/s gagnés par seconde de jeu
ROW_GAP_START = 360          # distance entre deux rangées d'obstacles
ROW_GAP_MIN = 230

# Bonus
POWERUP_CHANCE = 0.16        # probabilité d'un bonus par rangée
MAGNET_TIME = 20.0            # secondes
MAGNET_RANGE = 260           # px au-dessus du joueur
MAGNET_PULL = 1100           # px/s
INVULN_TIME = 1.2            # invincibilité après la perte du bouclier
JETPACK_TIME = 20.0           # secondes de vol (invincible, traînée de pièces)
JETPACK_HEIGHT = 210         # hauteur de vol
JETPACK_COIN_GAP = 0.10      # une pièce de traînée toutes les N secondes de vol
MULTIPLIER_TIME = 20.0       # secondes de score ×2
MULTIPLIER_FACTOR = 2
SNEAKERS_TIME = 20.0         # secondes de super-baskets
SNEAKERS_BOOST = 1.5         # saut plus haut pendant les super-baskets
HOVERBOARD_TIME = 20.0       # secondes de hoverboard (immunité aux chocs)

# Score
COIN_VALUE = 10
DISTANCE_DIVISOR = 25        # 1 point tous les N pixels parcourus

# Couleurs
COL_WHITE = (240, 240, 245)
COL_ACCENT = (255, 196, 0)
COL_DANGER = (230, 60, 70)

# Personnages jouables (couleurs + style). hair: cap | beanie | ponytail | bun
CHARACTERS = [
    {"name": "Max", "gender": "Garçon", "skin": (224, 176, 138), "top": (60, 150, 235),
     "top_dark": (36, 108, 190), "legs": (54, 66, 104), "shoe": (245, 245, 250),
     "shoe2": (70, 200, 140), "bag": (238, 96, 80), "hair": "cap", "hair_col": (240, 200, 40)},
    {"name": "Léa", "gender": "Fille", "skin": (238, 196, 164), "top": (232, 96, 150),
     "top_dark": (196, 60, 118), "legs": (60, 56, 92), "shoe": (255, 255, 255),
     "shoe2": (255, 150, 190), "bag": (150, 110, 220), "hair": "ponytail", "hair_col": (120, 74, 40)},
    {"name": "Neo", "gender": "Garçon", "skin": (150, 108, 80), "top": (40, 190, 150),
     "top_dark": (24, 140, 110), "legs": (44, 48, 58), "shoe": (250, 250, 250),
     "shoe2": (255, 200, 40), "bag": (40, 44, 54), "hair": "beanie", "hair_col": (220, 70, 70)},
    {"name": "Zoé", "gender": "Fille", "skin": (245, 214, 180), "top": (250, 160, 60),
     "top_dark": (210, 120, 30), "legs": (70, 60, 96), "shoe": (255, 255, 255),
     "shoe2": (120, 200, 255), "bag": (90, 200, 210), "hair": "bun", "hair_col": (30, 26, 24)},
]
