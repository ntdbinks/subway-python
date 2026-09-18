"""Entités du jeu : logique pure (aucun rendu), donc testable sans fenêtre."""
from dataclasses import dataclass

import pygame

from . import config as C

TRAIN, LOW, HIGH = "train", "low", "high"
MAGNET, SHIELD, JETPACK, MULTIPLIER, SNEAKERS = "magnet", "shield", "jetpack", "multiplier", "sneakers"
POWERUP_KINDS = (MAGNET, SHIELD, JETPACK, MULTIPLIER, SNEAKERS)
OBSTACLE_LENGTH = {TRAIN: 220, LOW: 34, HIGH: 26}


class Player:
    def __init__(self):
        self.lane = 1
        self.x = float(C.LANES_X[self.lane])
        self._from_x = self.x
        self._switch_t = 1.0
        self.height = 0.0          # hauteur de saut (0 = au sol)
        self.vz = 0.0
        self.slide_timer = 0.0
        self.anim_time = 0.0
        self.flying = False        # jetpack : le joueur reste en l'air
        self.jump_boost = 1.0      # super-baskets : saut plus haut

    # --- actions ---------------------------------------------------------
    def move(self, direction: int) -> bool:
        target = self.lane + direction
        if 0 <= target < C.LANE_COUNT:
            self._from_x = self.x
            self.lane = target
            self._switch_t = 0.0
            return True
        return False

    def jump(self) -> bool:
        if self.flying:
            return False
        if self.on_ground:
            self.vz = C.JUMP_VELOCITY * self.jump_boost
            self.slide_timer = 0.0
            return True
        return False

    def slide(self):
        if self.flying:
            return
        if self.on_ground:
            self.slide_timer = C.SLIDE_TIME
        else:
            self.vz = min(self.vz, -C.JUMP_VELOCITY)   # retombée rapide

    # --- état ------------------------------------------------------------
    @property
    def on_ground(self) -> bool:
        return not self.flying and self.height <= 0 and self.vz <= 0

    @property
    def sliding(self) -> bool:
        return self.slide_timer > 0

    @property
    def hitbox(self) -> pygame.Rect:
        w = C.PLAYER_SIZE[0] - 18
        r = pygame.Rect(0, 0, w, 30)
        r.center = (round(self.x), C.PLAYER_Y)
        return r

    def update(self, dt: float):
        self.anim_time += dt
        # glissement horizontal fluide entre deux voies
        self._switch_t = min(1.0, self._switch_t + dt / C.LANE_SWITCH_TIME)
        t = 1 - (1 - self._switch_t) ** 3  # ease-out
        self.x = self._from_x + (C.LANES_X[self.lane] - self._from_x) * t
        if self.flying:
            # jetpack : montée en douceur vers la hauteur de vol, sans gravité
            self.height += (C.JETPACK_HEIGHT - self.height) * min(1.0, dt * 5)
            self.vz = 0.0
            self.slide_timer = 0.0
            return
        # saut
        if self.height > 0 or self.vz > 0:
            self.vz -= C.GRAVITY * dt
            self.height += self.vz * dt
            if self.height <= 0:
                self.height, self.vz = 0.0, 0.0
        if self.slide_timer > 0:
            self.slide_timer = max(0.0, self.slide_timer - dt)


@dataclass
class Obstacle:
    kind: str
    lane: int
    y: float  # bord haut, coordonnées écran

    @property
    def length(self) -> int:
        return OBSTACLE_LENGTH[self.kind]

    @property
    def rect(self) -> pygame.Rect:
        w = C.LANE_WIDTH - 20
        return pygame.Rect(C.LANES_X[self.lane] - w // 2, int(self.y), w, self.length)

    def hits(self, player: Player) -> bool:
        if not self.rect.colliderect(player.hitbox):
            return False
        if self.kind == LOW:
            return player.height < C.JUMP_CLEARANCE
        if self.kind == HIGH:
            return not player.sliding
        return True  # un train ne se franchit pas


@dataclass
class Coin:
    lane: int
    y: float
    collected: bool = False
    x: float | None = None  # position libre quand l'aimant attire la pièce

    @property
    def cx(self) -> float:
        return C.LANES_X[self.lane] if self.x is None else self.x

    @property
    def rect(self) -> pygame.Rect:
        r = pygame.Rect(0, 0, 30, 30)
        r.center = (int(self.cx), int(self.y))
        return r


@dataclass
class PowerUp:
    kind: str  # MAGNET ou SHIELD
    lane: int
    y: float
    taken: bool = False

    @property
    def rect(self) -> pygame.Rect:
        r = pygame.Rect(0, 0, 38, 38)
        r.center = (C.LANES_X[self.lane], int(self.y))
        return r
