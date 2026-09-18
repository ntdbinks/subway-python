"""Monde de jeu : défilement, génération procédurale, collisions, score."""
import random

from . import config as C
from .entities import (
    HIGH, HOVERBOARD, JETPACK, LOW, MAGNET, MULTIPLIER, POWERUP_KINDS, SHIELD, SNEAKERS, TRAIN,
    Coin, Obstacle, Player, PowerUp,
)

# poids de tirage des bonus (le bouclier et l'aimant restent les plus fréquents)
POWERUP_WEIGHTS = {MAGNET: 5, SHIELD: 5, MULTIPLIER: 4, SNEAKERS: 3, JETPACK: 2, HOVERBOARD: 3}


class World:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.player = Player()
        self.obstacles: list[Obstacle] = []
        self.coins: list[Coin] = []
        self.powerups: list[PowerUp] = []
        self.magnet_timer = 0.0
        self.shield = False
        self.invuln_timer = 0.0
        self.jetpack_timer = 0.0
        self.multiplier_timer = 0.0
        self.sneakers_timer = 0.0
        self.hoverboard_timer = 0.0
        self._jet_coin_timer = 0.0
        self.powerups_run = 0            # bonus ramassés (missions)
        self.jetpacks_run = 0            # jetpacks ramassés (missions)
        self.speed = float(C.START_SPEED)
        self.distance = 0.0
        self.coin_count = 0
        self.score_val = 0.0             # score cumulé (tient compte du ×2)
        self.elapsed = 0.0
        self.alive = True
        self.events: list[str] = []      # sons : coin, powerup, shield, jetpack, crash
        self._until_next_row = 400.0     # premier obstacle après un court répit

    # --- score -----------------------------------------------------------
    @property
    def score(self) -> int:
        return int(self.score_val)

    @property
    def multiplier(self) -> int:
        return C.MULTIPLIER_FACTOR if self.multiplier_timer > 0 else 1

    @property
    def row_gap(self) -> float:
        # l'écart se resserre avec la vitesse, sans descendre sous le minimum
        progress = (self.speed - C.START_SPEED) / (C.MAX_SPEED - C.START_SPEED)
        return C.ROW_GAP_START - (C.ROW_GAP_START - C.ROW_GAP_MIN) * progress

    # --- génération --------------------------------------------------------
    def _spawn_row(self):
        """Crée une rangée en garantissant toujours au moins un passage possible."""
        lanes = list(range(C.LANE_COUNT))
        self.rng.shuffle(lanes)
        blocked = lanes[: self.rng.choice([1, 2, 2])]
        free = [lane for lane in lanes if lane not in blocked]

        longest = 0
        for lane in blocked:
            kind = self.rng.choices([TRAIN, LOW, HIGH], weights=[5, 3, 2])[0]
            obstacle = Obstacle(kind, lane, 0, variant=self.rng.randrange(6))
            obstacle.y = -obstacle.length
            self.obstacles.append(obstacle)
            longest = max(longest, obstacle.length)

        # une traînée de pièces dans une voie libre
        coin_lane = None
        if free and self.rng.random() < 0.85:
            coin_lane = self.rng.choice(free)
            for i in range(10):
                self.coins.append(Coin(coin_lane, -20 - i * 40))
            longest = max(longest, 10 * 40)

        # un bonus de temps en temps, dans une voie libre (pas sur les pièces)
        spots = [lane for lane in free if lane != coin_lane]
        if spots and self.rng.random() < C.POWERUP_CHANCE:
            kind = self.rng.choices(POWERUP_KINDS, weights=[POWERUP_WEIGHTS[k] for k in POWERUP_KINDS])[0]
            self.powerups.append(PowerUp(kind, self.rng.choice(spots), -30))
            longest = max(longest, 60)

        self._until_next_row = longest + self.row_gap

    # --- boucle ------------------------------------------------------------
    def update(self, dt: float):
        if not self.alive:
            return
        self.events.clear()
        self.elapsed += dt
        self.speed = min(C.MAX_SPEED, self.speed + C.SPEED_GAIN * dt)
        step = self.speed * dt
        self.distance += step

        # bonus temporisés
        self.magnet_timer = max(0.0, self.magnet_timer - dt)
        self.invuln_timer = max(0.0, self.invuln_timer - dt)
        self.multiplier_timer = max(0.0, self.multiplier_timer - dt)
        self.sneakers_timer = max(0.0, self.sneakers_timer - dt)
        self.hoverboard_timer = max(0.0, self.hoverboard_timer - dt)
        self.player.jump_boost = C.SNEAKERS_BOOST if self.sneakers_timer > 0 else 1.0
        if self.jetpack_timer > 0:
            self.jetpack_timer = max(0.0, self.jetpack_timer - dt)
            if self.jetpack_timer == 0:
                self.player.flying = False

        self.player.update(dt)

        # score : distance parcourue, doublée pendant le ×2
        self.score_val += (step / C.DISTANCE_DIVISOR) * self.multiplier

        self._until_next_row -= step
        if self._until_next_row <= 0:
            self._spawn_row()
        self._emit_jetpack_trail(dt)

        for obstacle in self.obstacles:
            obstacle.y += step
        for coin in self.coins:
            coin.y += step
        for p in self.powerups:
            p.y += step

        if self.magnet_timer > 0:
            self._attract_coins(dt)

        hitbox = self.player.hitbox
        for coin in self.coins:
            reachable = self.player.flying or self.player.height < 60 or self.magnet_timer > 0
            if not coin.collected and reachable and coin.rect.colliderect(hitbox):
                coin.collected = True
                self.coin_count += 1
                self.score_val += C.COIN_VALUE * self.multiplier
                self.events.append("coin")

        for p in self.powerups:
            if not p.taken and p.rect.colliderect(hitbox):
                p.taken = True
                self._activate(p.kind)

        if self.invuln_timer <= 0 and not self.player.flying:
            hit = [o for o in self.obstacles if o.hits(self.player)]
            if hit and self.hoverboard_timer > 0:
                # hoverboard : on fend les obstacles touchés sans mourir
                self.obstacles = [o for o in self.obstacles if all(o is not h for h in hit)]
            elif hit and self.shield:
                # le bouclier absorbe le choc et détruit l'obstacle touché
                self.shield = False
                self.invuln_timer = C.INVULN_TIME
                self.obstacles = [o for o in self.obstacles if all(o is not h for h in hit)]
                self.events.append("shield")
            elif hit:
                self.alive = False
                self.events.append("crash")

        # nettoyage (listes reconstruites : pas de suppression pendant l'itération)
        self.obstacles = [o for o in self.obstacles if o.y < C.HEIGHT]
        self.coins = [c for c in self.coins if c.y < C.HEIGHT + 20 and not c.collected]
        self.powerups = [p for p in self.powerups if p.y < C.HEIGHT + 20 and not p.taken]

    def _activate(self, kind: str):
        self.powerups_run += 1
        if kind == MAGNET:
            self.magnet_timer = C.MAGNET_TIME
        elif kind == SHIELD:
            self.shield = True
        elif kind == MULTIPLIER:
            self.multiplier_timer = C.MULTIPLIER_TIME
        elif kind == SNEAKERS:
            self.sneakers_timer = C.SNEAKERS_TIME
            self.player.jump_boost = C.SNEAKERS_BOOST  # effet immédiat, dès la même image
        elif kind == HOVERBOARD:
            self.hoverboard_timer = C.HOVERBOARD_TIME
        elif kind == JETPACK:
            self.jetpacks_run += 1
            self.jetpack_timer = C.JETPACK_TIME
            self.player.flying = True
            self.events.append("jetpack")
            return
        self.events.append("powerup")

    def run_stats(self) -> dict:
        """Statistiques de la partie, pour les missions."""
        return {
            "coins": self.coin_count,
            "meters": int(self.distance / 40),
            "jumps": self.player.jumps,
            "powerups": self.powerups_run,
            "jetpacks": self.jetpacks_run,
            "score": self.score,
        }

    def _emit_jetpack_trail(self, dt: float):
        """Pendant le vol, une traînée de pièces apparaît devant le joueur."""
        if self.jetpack_timer <= 0:
            return
        self._jet_coin_timer -= dt
        if self._jet_coin_timer <= 0:
            self._jet_coin_timer = C.JETPACK_COIN_GAP
            self.coins.append(Coin(self.player.lane, -20))

    def _attract_coins(self, dt: float):
        px = self.player.x
        for coin in self.coins:
            if C.PLAYER_Y - C.MAGNET_RANGE < coin.y < C.PLAYER_Y + 30:
                x = coin.cx
                move = C.MAGNET_PULL * dt
                coin.x = px if abs(px - x) <= move else x + move * (1 if px > x else -1)
