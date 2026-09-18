"""Machine à états (menu / jeu / pause / game over) et rendu."""
import random

import pygame

from . import config as C
from . import storage
from .assets import Assets
from .render3d import CAM_BACK, Renderer
from .world import World

MENU, PLAYING, PAUSED, GAME_OVER = "menu", "playing", "paused", "game_over"

KEYS_LEFT = {pygame.K_LEFT, pygame.K_a, pygame.K_q}
KEYS_RIGHT = {pygame.K_RIGHT, pygame.K_d}
KEYS_JUMP = {pygame.K_UP, pygame.K_SPACE, pygame.K_w, pygame.K_z}
KEYS_SLIDE = {pygame.K_DOWN, pygame.K_s}


class Game:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.assets = Assets()
        self.font = pygame.font.SysFont("arial", 24, bold=True)
        self.font_big = pygame.font.SysFont("arial", 56, bold=True)
        self.font_small = pygame.font.SysFont("arial", 18)
        self.save = storage.load()
        self.world = World()
        self.state = MENU
        self.flash = 0.0
        self.new_record = False
        self.running = True
        self.particles = []  # [x, y, vx, vy, vie, couleur]
        self.renderer = Renderer(self.assets)
        self.last_dt = 1 / 60

    # --- entrées ----------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.WINDOWFOCUSLOST and self.state == PLAYING:
            self.state = PAUSED  # pause auto si on change de fenêtre
            return
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key == pygame.K_m:
            self.assets.muted = not self.assets.muted
        if key == pygame.K_F11:
            pygame.display.toggle_fullscreen()

        if self.state == MENU:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start()
            elif key == pygame.K_ESCAPE:
                self.running = False
        elif self.state == PLAYING:
            p = self.world.player
            if key in KEYS_LEFT:
                p.move(-1)
            elif key in KEYS_RIGHT:
                p.move(1)
            elif key in KEYS_JUMP:
                if p.jump():
                    self.assets.play("jump")
            elif key in KEYS_SLIDE:
                p.slide()
            elif key in (pygame.K_p, pygame.K_ESCAPE):
                self.state = PAUSED
        elif self.state == PAUSED:
            if key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN):
                self.state = PLAYING
            elif key == pygame.K_q:
                self.state = MENU
        elif self.state == GAME_OVER:
            if key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                self.start()
            elif key == pygame.K_ESCAPE:
                self.state = MENU

    def start(self):
        self.world = World()
        self.state = PLAYING
        self.new_record = False
        self.particles.clear()

    # --- logique ----------------------------------------------------------
    def update(self, dt: float):
        dt = min(dt, 1 / 20)  # évite les « sauts » si la fenêtre a été bloquée
        self.last_dt = dt
        self.flash = max(0.0, self.flash - dt)
        self._update_particles(dt)
        if self.state != PLAYING:
            return
        self.world.update(dt)
        p = self.world.player
        sx, sy = self.renderer.cam.project(p.x, CAM_BACK, 70 + p.height)
        for event in self.world.events:
            self.assets.play(event)
            if event == "coin":
                self._burst(sx, sy, C.COL_ACCENT, 6)
            elif event == "jetpack":
                self._burst(sx, sy, (255, 150, 40), 22)
            elif event in ("powerup", "shield"):
                self._burst(sx, sy, (90, 170, 255), 14)
        if not self.world.alive:
            self.flash = 0.35
            self.new_record = storage.record_game(self.save, self.world.score, self.world.coin_count)
            storage.save(self.save)
            self.state = GAME_OVER

    def _burst(self, x, y, color, n):
        for _ in range(n):
            self.particles.append([x, y, random.uniform(-160, 160), random.uniform(-260, -60),
                                   random.uniform(0.3, 0.6), color])

    def _update_particles(self, dt):
        for part in self.particles:
            part[0] += part[2] * dt
            part[1] += part[3] * dt
            part[3] += 600 * dt
            part[4] -= dt
        self.particles = [part for part in self.particles if part[4] > 0]

    # --- rendu ------------------------------------------------------------
    def draw(self):
        if self.flash > 0:  # secousse de caméra au moment du choc
            amp = 10 * self.flash / 0.35
            self.renderer.cam.shake = (random.uniform(-amp, amp), random.uniform(-amp, amp))
        else:
            self.renderer.cam.shake = (0, 0)
        dt = self.last_dt if self.state == PLAYING else 0.0
        self.renderer.draw(self.screen, self.world, dt, self.particles)
        if self.state == PLAYING:
            self._draw_hud()
        elif self.state == MENU:
            self._draw_menu()
        elif self.state == PAUSED:
            self._draw_hud()
            self._overlay("PAUSE", ["P / Entrée : reprendre", "Q : menu principal"])
        elif self.state == GAME_OVER:
            self._draw_game_over()
        if self.flash > 0:
            s = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
            s.fill((255, 0, 0, int(160 * self.flash / 0.35)))
            self.screen.blit(s, (0, 0))

    def _text(self, text, font, color, center):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=center))

    def _draw_hud(self):
        w = self.world
        panel = pygame.Surface((220, 92), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 140))
        self.screen.blit(panel, (10, 10))
        score_col = (170, 110, 240) if w.multiplier > 1 else C.COL_WHITE
        score_txt = f"Score  {w.score}" + ("  ×2" if w.multiplier > 1 else "")
        self.screen.blit(self.font.render(score_txt, True, score_col), (22, 18))
        self.screen.blit(self.font.render(f"Pièces {w.coin_count}", True, C.COL_ACCENT), (22, 46))
        self.screen.blit(self.font_small.render(f"Record {self.save['best_score']}", True, (180, 180, 190)), (22, 76))
        # bonus actifs : icône + jauge de temps restant
        gauges = [
            ("jetpack", w.jetpack_timer, C.JETPACK_TIME, (255, 150, 40)),
            ("magnet", w.magnet_timer, C.MAGNET_TIME, (230, 60, 70)),
            ("multiplier", w.multiplier_timer, C.MULTIPLIER_TIME, (170, 110, 240)),
            ("sneakers", w.sneakers_timer, C.SNEAKERS_TIME, (60, 210, 140)),
        ]
        y = 112
        for kind, t, full, col in gauges:
            if t <= 0:
                continue
            self.screen.blit(pygame.transform.smoothscale(self.assets.powerups[kind], (26, 26)), (14, y))
            pygame.draw.rect(self.screen, (60, 60, 70), (48, y + 9, 120, 8), border_radius=4)
            pygame.draw.rect(self.screen, col, (48, y + 9, int(120 * t / full), 8), border_radius=4)
            y += 32
        if w.shield:
            self.screen.blit(pygame.transform.smoothscale(self.assets.powerups["shield"], (26, 26)), (14, y))
            self.screen.blit(self.font_small.render("bouclier", True, (150, 200, 255)), (48, y + 3))
        speed = f"{w.speed / C.START_SPEED:.1f}x"
        self._text(speed, self.font_small, (180, 180, 190), (C.WIDTH - 50, 24))
        if self.assets.muted:
            self._text("muet", self.font_small, (180, 180, 190), (C.WIDTH - 50, 48))

    def _overlay(self, title, lines, title_color=C.COL_WHITE):
        s = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 170))
        self.screen.blit(s, (0, 0))
        self._text(title, self.font_big, title_color, (C.WIDTH // 2, 200))
        for i, line in enumerate(lines):
            self._text(line, self.font, C.COL_WHITE, (C.WIDTH // 2, 290 + i * 38))

    def _draw_menu(self):
        self._overlay("SUBWAY PYTHON", [
            "Entrée / Espace : jouer",
            "← → : changer de voie   ↑ : sauter   ↓ : glisser",
            "P : pause   M : son   F11 : plein écran   Échap : quitter",
            "Bonus : aimant · bouclier · jetpack · score ×2 · super-baskets",
            f"Record : {self.save['best_score']}   ·   Parties : {self.save['games_played']}",
        ], C.COL_ACCENT)

    def _draw_game_over(self):
        w = self.world
        lines = [f"Score : {w.score}   (pièces : {w.coin_count})"]
        lines.append("NOUVEAU RECORD !" if self.new_record else f"Record : {self.save['best_score']}")
        lines.append("R / Entrée : rejouer   Échap : menu")
        self._overlay("GAME OVER", lines, C.COL_DANGER)
