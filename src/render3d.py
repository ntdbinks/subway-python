"""Rendu en perspective, ambiance de jour colorée (façon métro en plein air).

La logique du jeu (world.py) reste en 2D vue de dessus : chaque objet a une voie
et une position `y`. Ce module convertit cette position en profondeur puis la
projette à l'écran, avec ciel dégradé, brume claire, décor coloré et ombrage.
"""
import math
import random

import pygame
from pygame import gfxdraw

from . import config as C
from .entities import HIGH, HOVERBOARD, JETPACK, LOW, MAGNET, MULTIPLIER, SHIELD, SNEAKERS, TRAIN

W, H = C.WIDTH, C.HEIGHT
HORIZON = 196
CAM_BACK = 150
FOCAL = 195
GROUND = 255
Z_NEAR = 28
Z_FOG_START, Z_FOG_END = 320, 1150
CX = W / 2

# palette de jour, vive
FOG = (208, 234, 250)
SKY_TOP = (58, 150, 240)
SKY_MID = (128, 196, 246)
SKY_LOW = (216, 240, 252)
BALLAST = (150, 120, 96)
EARTH = (176, 150, 120)
GRASS = (108, 178, 92)
RAIL = (214, 220, 228)
SLEEPER = (120, 92, 66)

TRAIN_W, TRAIN_H = 112, 152
WALL_OFFSET = 150
POST_EVERY = 340
PANEL_EVERY = 200
SLEEPER_EVERY = 38

# couleurs vives des trains (corps clair, bande foncée)
TRAIN_SKINS = [
    ((240, 196, 70), (210, 150, 20)),    # jaune
    ((230, 84, 84), (180, 40, 46)),      # rouge
    ((88, 170, 230), (40, 110, 180)),    # bleu
    ((110, 200, 130), (50, 150, 86)),    # vert
    ((240, 150, 80), (200, 100, 40)),    # orange
    ((190, 150, 230), (140, 96, 200)),   # violet
]
BUILDING_COLORS = [
    (236, 206, 150), (210, 170, 150), (170, 200, 220),
    (200, 180, 210), (230, 190, 160), (180, 210, 190),
]

POWERUP_GLOW = {
    MAGNET: (255, 90, 90), SHIELD: (90, 170, 255), JETPACK: (255, 150, 40),
    MULTIPLIER: (170, 110, 240), SNEAKERS: (60, 210, 140), HOVERBOARD: (120, 180, 255),
}


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))


def shade(color, k):
    return tuple(max(0, min(255, int(v * k))) for v in color[:3])


def fog_t(z):
    t = (z - Z_FOG_START) / (Z_FOG_END - Z_FOG_START)
    return max(0.0, min(1.0, t)) ** 1.3


class Camera:
    def __init__(self):
        self.x = CX
        self.shake = (0, 0)

    def follow(self, player_x, dt):
        target = CX + (player_x - CX) * 0.55
        self.x += (target - self.x) * min(1.0, dt * 8)

    def project(self, xw, z, h=0.0):
        s = FOCAL / z
        return (CX + (xw - self.x) * s + self.shake[0],
                HORIZON + (GROUND - h) * s + self.shake[1])


def depth_of(y_world):
    return (C.PLAYER_Y - y_world) + CAM_BACK


class Renderer:
    def __init__(self, assets):
        self.assets = assets
        self.character = C.CHARACTERS[0]
        self.cam = Camera()
        self.sky = self._make_sky()
        self.vignette = self._make_vignette()
        self.time = 0.0
        rng = random.Random(4)
        self.building_h = [rng.randint(60, 150) for _ in range(64)]
        self.building_c = [rng.choice(BUILDING_COLORS) for _ in range(64)]
        # nuages : (x, y, rayon de base) répartis sur la largeur
        self.clouds = [[i * (W / 4) + rng.uniform(0, 80), rng.uniform(24, 80), rng.uniform(26, 40)]
                       for i in range(4)]

    # --- ciel -------------------------------------------------------------
    def _make_sky(self):
        sky = pygame.Surface((W, HORIZON + 40))
        for y in range(HORIZON + 40):
            t = y / HORIZON
            c = mix(SKY_TOP, SKY_MID, min(1, t * 1.3)) if t < 0.6 else mix(SKY_MID, SKY_LOW, min(1, (t - 0.6) / 0.4))
            pygame.draw.line(sky, c, (0, y), (W, y))
        # soleil
        glow = pygame.Surface((300, 300), pygame.SRCALPHA)
        for r in range(150, 0, -4):
            a = int(70 * (1 - r / 150) ** 2)
            pygame.draw.circle(glow, (255, 244, 200, a), (150, 150), r)
        pygame.draw.circle(glow, (255, 250, 224, 255), (150, 150), 34)
        sky.blit(glow, (W * 0.74 - 150, 20 - 150 + 60))
        return sky

    def _make_vignette(self):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(40):
            a = int(46 * (i / 40) ** 2.5)
            pygame.draw.rect(v, (30, 30, 40, a // 8), (40 - i, 40 - i, W - 2 * (40 - i), H - 2 * (40 - i)), 2)
        return v

    # --- primitives -------------------------------------------------------
    def _poly(self, surf, color, pts):
        if len(pts) >= 3:
            ipts = [(int(x), int(y)) for x, y in pts]
            pygame.draw.polygon(surf, color, ipts)
            gfxdraw.aapolygon(surf, ipts, color)

    def _fogged(self, color, z):
        return mix(color, FOG, fog_t(z))

    # --- scène ------------------------------------------------------------
    def draw(self, surf, world, dt, particles=()):
        self.time += dt
        self.cam.follow(world.player.x, dt)
        surf.blit(self.sky, (self.cam.shake[0] * 0.3, 0))
        self._draw_clouds(surf, dt)
        self._draw_skyline(surf, world)
        self._draw_ground(surf, world)
        self._draw_track(surf, world)
        self._draw_scenery(surf, world)
        self._draw_objects(surf, world)
        self._draw_player(surf, world)
        for x, y, _, _, life, color in particles:
            pygame.draw.circle(surf, color, (int(x), int(y)), max(1, int(life * 7)))
        surf.blit(self.vignette, (0, 0))

    def _draw_clouds(self, surf, dt):
        for c in self.clouds:
            c[0] = (c[0] - dt * 14) % (W + 260) - 130
            x, y, r = c
            w, h = int(r * 4.4), int(r * 2.2)
            cl = pygame.Surface((w, h), pygame.SRCALPHA)
            for dx, dy, k in ((0.30, 0.62, 0.62), (0.52, 0.42, 0.75), (0.72, 0.60, 0.66), (0.90, 0.66, 0.5)):
                pygame.draw.circle(cl, (255, 255, 255, 235), (int(w * dx), int(h * dy)), int(r * k))
            pygame.draw.ellipse(cl, (255, 255, 255, 235), (int(w * 0.16), int(h * 0.6), int(w * 0.7), int(h * 0.34)))
            surf.blit(cl, (x, y))

    def _draw_skyline(self, surf, world):
        base = HORIZON + 4
        off = int(world.distance * 0.4)
        for k in range(-1, 26):
            idx = (k + off // 70) % 64
            bx = (k * 70 - off % 70)
            bh = self.building_h[idx]
            col = self.building_c[idx]
            pygame.draw.rect(surf, mix(col, FOG, 0.35), (bx, base - bh, 60, bh + 40))
            for wy in range(base - bh + 8, base, 16):
                for wx in range(bx + 6, bx + 54, 12):
                    pygame.draw.rect(surf, (255, 250, 210), (wx, wy, 5, 8))

    def _draw_ground(self, surf, world):
        # herbe claire au premier plan, brume au fond
        for y in range(HORIZON, H, 3):
            z = FOCAL * GROUND / max(1, (y - HORIZON + 1))
            pygame.draw.line(surf, self._fogged(GRASS, z), (0, y), (W, y), 3)
        # plateforme de ballast sous les voies
        left = C.TRACK_LEFT - 40
        right = C.TRACK_LEFT + C.LANE_WIDTH * C.LANE_COUNT + 40
        p = self.cam.project
        self._poly(surf, self._fogged(EARTH, 500),
                   [p(left - 26, Z_NEAR), p(right + 26, Z_NEAR), p(right + 26, 2600), p(left - 26, 2600)])
        self._poly(surf, self._fogged(BALLAST, 460),
                   [p(left, Z_NEAR), p(right, Z_NEAR), p(right, 2600), p(left, 2600)])

    def _draw_track(self, surf, world):
        offset = world.distance % SLEEPER_EVERY
        p = self.cam.project
        d = 1300 - offset
        while d > -CAM_BACK + Z_NEAR:
            z = d + CAM_BACK
            if z > Z_NEAR:
                color = self._fogged(SLEEPER, z)
                for lx in C.LANES_X:
                    self._poly(surf, color, [p(lx - 48, z), p(lx + 48, z), p(lx + 48, z + 12), p(lx - 48, z + 12)])
            d -= SLEEPER_EVERY
        for lx in C.LANES_X:
            for rx in (lx - 30, lx + 30):
                a, b = p(rx, Z_NEAR), p(rx, 2600)
                pygame.draw.line(surf, (120, 120, 128), a, b, 7)
                pygame.draw.line(surf, RAIL, (a[0], a[1] - 2), b, 3)

    def _draw_scenery(self, surf, world):
        p = self.cam.project
        left_x = C.TRACK_LEFT - WALL_OFFSET
        right_x = C.TRACK_LEFT + C.LANE_WIDTH * C.LANE_COUNT + WALL_OFFSET
        items = []
        post_first = int(world.distance // POST_EVERY)
        for k in range(post_first + 5, post_first - 1, -1):
            z = k * POST_EVERY - world.distance + CAM_BACK
            if z > Z_NEAR + 4:
                items.append((z, k))
        for z, k in sorted(items, key=lambda it: -it[0]):
            s = FOCAL / z
            # clôtures grillagées basses de chaque côté
            for wx, side in ((left_x, 1.0), (right_x, 0.9)):
                col = self._fogged(shade((150, 158, 168), side), z)
                pygame.draw.line(surf, col, p(wx, z), p(wx, z, 70), max(1, int(6 * s)))
            # portique de caténaire coloré + fils
            postcol = self._fogged((90, 100, 120), z)
            for px in (C.TRACK_LEFT - 60, C.TRACK_LEFT + C.LANE_WIDTH * C.LANE_COUNT + 60):
                pygame.draw.line(surf, postcol, p(px, z), p(px, z, 300), max(1, int(8 * s)))
            pygame.draw.line(surf, postcol, p(C.TRACK_LEFT - 60, z, 292),
                             p(C.TRACK_LEFT + C.LANE_WIDTH * C.LANE_COUNT + 60, z, 292), max(1, int(5 * s)))
            # lampadaire avec halo chaud
            lamp = p(right_x, z, 120)
            pygame.draw.circle(surf, self._fogged((255, 236, 150), z), (int(lamp[0]), int(lamp[1])), max(2, int(6 * s)))

    # --- objets -----------------------------------------------------------
    def _draw_objects(self, surf, world):
        items = []
        for o in world.obstacles:
            zn, zf = depth_of(o.y + o.length), depth_of(o.y)
            if zf > Z_NEAR:
                items.append((zn, "obs", o, zn, zf))
        for c in world.coins:
            z = depth_of(c.y)
            if z > Z_NEAR + 10:
                items.append((z, "coin", c, z, z))
        for pu in world.powerups:
            z = depth_of(pu.y)
            if z > Z_NEAR + 10:
                items.append((z, "pu", pu, z, z))
        for _, kind, obj, zn, zf in sorted(items, key=lambda it: -it[0]):
            if kind == "obs":
                if obj.kind == TRAIN:
                    self._draw_train(surf, C.LANES_X[obj.lane], zn, zf, obj.variant)
                else:
                    self._draw_barrier(surf, C.LANES_X[obj.lane], zn, obj.kind == LOW)
            elif kind == "coin":
                self._draw_coin(surf, obj.cx, zn, hash((obj.lane, round(obj.y))) % 10)
            else:
                self._draw_powerup(surf, C.LANES_X[obj.lane], zn, obj.kind)

    def _draw_train(self, surf, lx, z_near, z_far, variant):
        p = self.cam.project
        body, stripe = TRAIN_SKINS[variant % len(TRAIN_SKINS)]
        x0, x1 = lx - TRAIN_W / 2, lx + TRAIN_W / 2
        zn = max(Z_NEAR + 20, z_near)
        zm = (zn + z_far) / 2
        # ombre au sol
        self._poly(surf, self._fogged((70, 60, 52), zm),
                   [p(x0 - 8, zn), p(x1 + 8, zn), p(x1 + 8, z_far), p(x0 - 8, z_far)])
        # flanc visible
        side_x = x1 if self.cam.x > lx + 10 else (x0 if self.cam.x < lx - 10 else None)
        if side_x is not None:
            self._poly(surf, self._fogged(shade(body, 0.78), zm),
                       [p(side_x, zn), p(side_x, z_far), p(side_x, z_far, TRAIN_H), p(side_x, zn, TRAIN_H)])
            self._poly(surf, self._fogged(shade(stripe, 0.85), zm),
                       [p(side_x, zn, 46), p(side_x, z_far, 46), p(side_x, z_far, 60), p(side_x, zn, 60)])
            n = int((z_far - zn) // 46)
            for i in range(n):
                a = zn + 12 + i * 46
                if a + 30 < z_far:
                    self._poly(surf, self._fogged((150, 205, 232), a),
                               [p(side_x, a, 82), p(side_x, a + 30, 82), p(side_x, a + 30, 128), p(side_x, a, 128)])
        # toit
        self._poly(surf, self._fogged(shade(body, 1.05), zm),
                   [p(x0, zn, TRAIN_H), p(x1, zn, TRAIN_H), p(x1, z_far, TRAIN_H), p(x0, z_far, TRAIN_H)])
        if z_near < Z_NEAR + 20:
            return
        # face avant
        z = z_near
        s = FOCAL / z
        f = lambda c: self._fogged(c, z)  # noqa: E731
        tl, br = p(x0, z, TRAIN_H), p(x1, z, 0)
        rect = pygame.Rect(int(tl[0]), int(tl[1]), int(br[0] - tl[0]), int(br[1] - tl[1]))
        pygame.draw.rect(surf, f(body), rect, border_radius=max(2, int(14 * s)))
        pygame.draw.rect(surf, f(shade(body, 0.7)), rect, max(1, int(3 * s)), border_radius=max(2, int(14 * s)))
        ws = pygame.Rect(0, 0, int(rect.w * 0.78), int(rect.h * 0.32))
        ws.midtop = (rect.centerx, rect.top + int(rect.h * 0.13))
        pygame.draw.rect(surf, f((150, 205, 232)), ws, border_radius=max(1, int(6 * s)))
        pygame.draw.polygon(surf, f((210, 236, 250)), [(ws.left + ws.w * 0.1, ws.bottom),
                            (ws.left + ws.w * 0.4, ws.top), (ws.left + ws.w * 0.52, ws.top), (ws.left + ws.w * 0.22, ws.bottom)])
        band = pygame.Rect(rect.left, rect.top + int(rect.h * 0.62), rect.w, max(2, int(rect.h * 0.09)))
        pygame.draw.rect(surf, f(stripe), band)
        for hx in (rect.left + rect.w * 0.2, rect.right - rect.w * 0.2):
            pygame.draw.circle(surf, f((255, 248, 214)), (int(hx), int(rect.top + rect.h * 0.82)), max(2, int(8 * s)))
        pygame.draw.rect(surf, f((60, 60, 66)), (rect.left + rect.w * 0.1, rect.bottom - max(2, int(9 * s)),
                         rect.w * 0.8, max(2, int(9 * s))))

    def _draw_barrier(self, surf, lx, z, low):
        if z <= Z_NEAR:
            return
        p = self.cam.project
        s = FOCAL / z
        f = lambda c: self._fogged(c, z)  # noqa: E731
        x0, x1 = lx - 58, lx + 58
        if low:
            for px in (x0 + 10, x1 - 10):
                pygame.draw.line(surf, f((80, 82, 88)), p(px, z), p(px, z, 26), max(1, int(6 * s)))
            tl, br = p(x0, z, 46), p(x1, z, 22)
            rect = pygame.Rect(int(tl[0]), int(tl[1]), max(1, int(br[0] - tl[0])), max(1, int(br[1] - tl[1])))
            stripe = max(2, rect.w // 8)
            for i, xx in enumerate(range(rect.left, rect.right, stripe)):
                pygame.draw.rect(surf, f((250, 200, 30) if i % 2 == 0 else (40, 40, 44)),
                                 (xx, rect.top, min(stripe, rect.right - xx), rect.h))
            pygame.draw.line(surf, f((255, 245, 200)), rect.topleft, rect.topright, max(1, int(2 * s)))
        else:
            for px in (x0, x1):
                pygame.draw.line(surf, f((120, 124, 132)), p(px, z), p(px, z, 120), max(2, int(8 * s)))
            tl, br = p(x0, z, 120), p(x1, z, 72)
            rect = pygame.Rect(int(tl[0]), int(tl[1]), max(1, int(br[0] - tl[0])), max(1, int(br[1] - tl[1])))
            stripe = max(2, rect.w // 7)
            for i, xx in enumerate(range(rect.left, rect.right, stripe)):
                pygame.draw.rect(surf, f((235, 70, 80) if i % 2 == 0 else (245, 245, 245)),
                                 (xx, rect.top, min(stripe, rect.right - xx), rect.h))
            if int(self.time * 3) % 2 == 0:
                c = p(lx, z, 130)
                pygame.draw.circle(surf, f((255, 90, 70)), (int(c[0]), int(c[1])), max(2, int(6 * s)))

    def _draw_coin(self, surf, xw, z, phase):
        p = self.cam.project
        s = FOCAL / z
        cx, cy = p(xw, z, 46 + 5 * math.sin(self.time * 4 + phase))
        r = max(2, int(17 * s))
        spin = abs(math.cos(self.time * 5 + phase))
        w = max(2, int(r * 2 * (0.25 + 0.75 * spin)))
        rect = pygame.Rect(0, 0, w, r * 2)
        rect.center = (int(cx), int(cy))
        pygame.draw.ellipse(surf, self._fogged((214, 150, 8), z), rect)
        pygame.draw.ellipse(surf, self._fogged((255, 210, 56), z), rect.inflate(-max(1, w // 5), -max(1, r // 3)))
        if spin > 0.5:
            pygame.draw.ellipse(surf, self._fogged((255, 248, 206), z),
                                (rect.centerx - w // 6, rect.top + r // 3, max(1, w // 5), max(1, r // 2)))

    def _draw_powerup(self, surf, lx, z, kind):
        p = self.cam.project
        s = FOCAL / z
        cx, cy = p(lx, z, 56 + 8 * math.sin(self.time * 3))
        size = max(4, int(46 * s))
        col = POWERUP_GLOW.get(kind, (90, 170, 255))
        hr = int(size * 1.15)
        halo = pygame.Surface((hr * 2, hr * 2))
        strength = 0.5 * (1 - fog_t(z))
        for rr in range(hr, 2, -max(1, hr // 8)):
            k = strength * (1 - rr / hr) ** 1.6
            pygame.draw.circle(halo, (int(col[0] * k), int(col[1] * k), int(col[2] * k)), (hr, hr), rr)
        surf.blit(halo, (cx - hr, cy - hr), special_flags=pygame.BLEND_RGB_ADD)
        icon = pygame.transform.smoothscale(self.assets.powerups[kind], (size, size))
        surf.blit(icon, icon.get_rect(center=(int(cx), int(cy))))

    # --- coureur vu de dos ------------------------------------------------
    def _draw_hair(self, surf, P, k, char):
        col, style, top_dark = char["hair_col"], char["hair"], char["top_dark"]
        if style == "cap":
            pygame.draw.ellipse(surf, top_dark, (*P(-15, 116), 30 * k, 12 * k))
            pygame.draw.rect(surf, col, (*P(-13, 118), 26 * k, 8 * k), border_radius=int(4 * k))
        elif style == "beanie":
            pygame.draw.circle(surf, col, P(0, 112), int(13 * k))
            pygame.draw.rect(surf, shade(col, 0.8), (*P(-13, 100), 26 * k, 7 * k), border_radius=int(3 * k))
        elif style == "ponytail":
            pygame.draw.ellipse(surf, col, (*P(-14, 118), 28 * k, 16 * k))          # cheveux
            pygame.draw.circle(surf, col, P(0, 96), int(7 * k))                     # attache
            self._poly(surf, col, [P(-3, 96), P(3, 96), P(6, 74), P(-2, 72)])       # queue de cheval
        elif style == "bun":
            pygame.draw.circle(surf, col, P(0, 124), int(8 * k))                    # chignon
            pygame.draw.ellipse(surf, col, (*P(-14, 114), 28 * k, 14 * k))

    def draw_runner(self, surf, cx, foot_y, k, char, *, run=0.0, airborne=False,
                    sliding=False, flying=False, shield=False, hoverboard=False):
        """Dessine un coureur (vu de dos) paramétré par un personnage.

        Réutilisé par le jeu et par l'écran de sélection."""
        def P(dx, dy):
            return (cx + dx * k, foot_y - dy * k)

        if hoverboard and not flying:
            board = pygame.Rect(0, 0, int(48 * k), int(9 * k)); board.center = P(0, -2)
            glow = pygame.Surface((board.w + int(20 * k), int(14 * k)), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (120, 190, 255, 120), glow.get_rect())
            surf.blit(glow, glow.get_rect(center=P(0, -6)))
            pygame.draw.rect(surf, (60, 70, 92), board, border_radius=int(4 * k))
            pygame.draw.rect(surf, (150, 210, 255), board, max(1, int(2 * k)), border_radius=int(4 * k))

        skin, top, top_dark = char["skin"], char["top"], char["top_dark"]
        legs, shoe, shoe2, bag = char["legs"], char["shoe"], char["shoe2"], char["bag"]
        if sliding:
            pygame.draw.line(surf, legs, P(-10, 8), P(-18, 2), int(11 * k))
            pygame.draw.line(surf, legs, P(10, 8), P(18, 2), int(11 * k))
            self._poly(surf, top, [P(-22, 8), P(22, 8), P(18, 44), P(-18, 44)])
            pygame.draw.circle(surf, skin, P(0, 54), int(12 * k))
            self._draw_hair(surf, lambda dx, dy: P(dx, dy - 44), k, char)
            pygame.draw.rect(surf, bag, (*P(-14, 42), 28 * k, 22 * k), border_radius=int(5 * k))
            return
        lift = 0 if airborne else run
        for side, ph in ((-1, lift), (1, -lift)):
            knee = P(side * 9, 30 + 6 * max(0, ph))
            foot = P(side * 10, 2 + 16 * max(0, ph) + (10 if airborne else 0))
            pygame.draw.line(surf, legs, P(side * 8, 50), knee, int(12 * k))
            pygame.draw.line(surf, legs, knee, foot, int(11 * k))
            sole = pygame.Rect(0, 0, int(14 * k), int(8 * k)); sole.center = foot
            pygame.draw.ellipse(surf, shoe, sole)
            pygame.draw.ellipse(surf, shoe2, sole.inflate(-int(6 * k), -int(4 * k)))
        for side, ph in ((-1, -run), (1, run)):
            arm_top = P(side * 20, 88)
            hand = P(side * (26 + (8 if airborne else 0)), 60 + 12 * ph + (20 if airborne else 0))
            pygame.draw.line(surf, top_dark, arm_top, hand, int(10 * k))
            pygame.draw.circle(surf, skin, hand, int(5 * k))
        if flying:
            for side in (-1, 1):
                cyl = pygame.Rect(0, 0, int(11 * k), int(34 * k)); cyl.center = P(side * 15, 74)
                pygame.draw.rect(surf, (170, 176, 188), cyl, border_radius=int(4 * k))
                pygame.draw.rect(surf, (110, 116, 130), cyl, max(1, int(2 * k)), border_radius=int(4 * k))
                flame = 1 + 0.4 * math.sin(self.time * 40 + side)
                fx, fy = P(side * 15, 4)
                self._poly(surf, (255, 170, 50), [(fx - 7 * k, fy), (fx + 7 * k, fy), (fx, fy + 30 * k * flame)])
                self._poly(surf, (255, 240, 160), [(fx - 3 * k, fy), (fx + 3 * k, fy), (fx, fy + 18 * k * flame)])
        self._poly(surf, top, [P(-20, 50), P(20, 50), P(22, 92), P(-22, 92)])
        self._poly(surf, top_dark, [P(8, 50), P(20, 50), P(22, 92), P(12, 92)])
        pack = pygame.Rect(0, 0, int(26 * k), int(30 * k)); pack.midtop = P(0, 88)
        pygame.draw.rect(surf, bag, pack, border_radius=int(6 * k))
        pygame.draw.rect(surf, shade(bag, 1.25), pack.inflate(-int(8 * k), -int(18 * k)).move(0, int(8 * k)),
                         border_radius=int(3 * k))
        pygame.draw.circle(surf, skin, P(0, 104), int(12 * k))
        self._draw_hair(surf, P, k, char)
        if shield:
            r = int(78 * k)
            bubble = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(bubble, (90, 180, 255, 55), (r + 2, r + 2), r)
            pygame.draw.circle(bubble, (150, 210, 255, 190), (r + 2, r + 2), r, 3)
            surf.blit(bubble, bubble.get_rect(center=P(0, 62)))

    def _draw_player(self, surf, world):
        pl = world.player
        z = CAM_BACK
        s = FOCAL / z
        p = self.cam.project
        gx, gy = p(pl.x, z)
        sh_w = max(10, int((58 - pl.height * 0.15) * s))
        shadow = pygame.Surface((sh_w, max(4, sh_w // 4)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
        surf.blit(shadow, shadow.get_rect(center=(int(gx), int(gy))))
        if world.invuln_timer > 0 and int(world.invuln_timer * 12) % 2 == 0:
            return
        board_lift = 10 if (world.hoverboard_timer > 0 and pl.height < 1 and not pl.flying) else 0
        foot_y = gy - (pl.height + board_lift) * s
        self.draw_runner(surf, gx, foot_y, s * 0.95, self.character,
                         run=math.sin(pl.anim_time * 14), airborne=pl.height > 1,
                         sliding=pl.sliding, flying=pl.flying, shield=world.shield,
                         hoverboard=world.hoverboard_timer > 0)
