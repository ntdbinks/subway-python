"""Rendu en perspective : caméra placée derrière et au-dessus du coureur.

La logique du jeu (world.py) reste en 2D vue de dessus : chaque objet a une voie
et une position `y`. Ce module convertit cette position en profondeur
(distance devant le joueur) puis la projette à l'écran, avec brouillard,
éclairage par face et décor qui défile.
"""
import math
import random

import pygame
from pygame import gfxdraw

from . import config as C
from .entities import HIGH, JETPACK, LOW, MAGNET, MULTIPLIER, SHIELD, SNEAKERS, TRAIN

POWERUP_GLOW = {
    MAGNET: (255, 90, 90), SHIELD: (90, 170, 255), JETPACK: (255, 150, 40),
    MULTIPLIER: (170, 110, 240), SNEAKERS: (60, 210, 140),
}

W, H = C.WIDTH, C.HEIGHT
HORIZON = 190            # ligne d'horizon à l'écran
CAM_BACK = 150           # distance caméra → joueur (unités du monde)
FOCAL = 195              # focale : échelle = FOCAL / profondeur
GROUND = 255             # hauteur de la caméra au-dessus du sol (unités × FOCAL / FOCAL)
Z_NEAR = 28              # plan de coupe proche
Z_FOG_START, Z_FOG_END = 260, 900
CX = W / 2

FOG = (182, 170, 172)            # couleur du brouillard, accordée au ciel à l'horizon
SKY_TOP = (38, 54, 92)
SKY_MID = (122, 118, 150)
SKY_LOW = (236, 176, 128)
BALLAST = (92, 86, 80)
EARTH = (70, 72, 62)

TRAIN_W, TRAIN_H = 112, 150
WALL_OFFSET = 150        # murs latéraux à 150 unités du bord des voies
WALL_H = 230
POST_EVERY = 360         # espacement des poteaux de caténaire
PANEL_EVERY = 180        # espacement des panneaux de mur
SLEEPER_EVERY = 38


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

    def scale(self, z):
        return FOCAL / z

    def project(self, xw, z, h=0.0):
        """(x monde, profondeur, hauteur) → (x écran, y écran)."""
        s = FOCAL / z
        return (CX + (xw - self.x) * s + self.shake[0],
                HORIZON + (GROUND - h) * s + self.shake[1])


def depth_of(y_world):
    """Position `y` de la logique 2D → profondeur devant la caméra."""
    return (C.PLAYER_Y - y_world) + CAM_BACK


class Renderer:
    def __init__(self, assets):
        self.assets = assets
        self.cam = Camera()
        self.sky = self._make_sky()
        self.vignette = self._make_vignette()
        self.time = 0.0
        rng = random.Random(4)
        # variations des panneaux de mur (graffitis / affiches), indexées par numéro de panneau
        self.panel_colors = [rng.choice([(96, 92, 88), (84, 86, 90), (104, 96, 86), (78, 80, 84)])
                             for _ in range(64)]
        self.panel_tags = [rng.random() < 0.35 for _ in range(64)]
        self.tag_colors = [rng.choice([(170, 70, 64), (64, 110, 160), (190, 150, 70), (80, 140, 100)])
                           for _ in range(64)]

    # --- éléments précalculés ---------------------------------------------
    def _make_sky(self):
        sky = pygame.Surface((W, HORIZON + 40))
        for y in range(HORIZON + 40):
            t = y / HORIZON
            color = mix(SKY_TOP, SKY_MID, min(1, t * 1.4)) if t < 0.7 else mix(SKY_MID, SKY_LOW, min(1, (t - 0.7) / 0.3))
            pygame.draw.line(sky, color, (0, y), (W, y))
        # soleil voilé
        glow = pygame.Surface((360, 360), pygame.SRCALPHA)
        for r in range(180, 0, -6):
            a = int(90 * (1 - r / 180) ** 2)
            pygame.draw.circle(glow, (255, 214, 160, a), (180, 180), r)
        pygame.draw.circle(glow, (255, 236, 200, 230), (180, 180), 22)
        sky.blit(glow, (W * 0.68 - 180, HORIZON - 40 - 180))
        # silhouette de la ville, deux plans
        rng = random.Random(11)
        for layer, (base, height, color) in enumerate(((HORIZON + 2, 70, (150, 136, 150)),
                                                       (HORIZON + 6, 46, (112, 104, 124)))):
            x = -20
            while x < W + 20:
                w = rng.randint(24, 70)
                h = rng.randint(int(height * 0.35), height)
                pygame.draw.rect(sky, color, (x, base - h, w, h + 40))
                if layer == 1:
                    for wy in range(base - h + 6, base - 4, 9):
                        for wx in range(x + 4, x + w - 4, 8):
                            if rng.random() < 0.18:
                                sky.fill((255, 214, 150), (wx, wy, 2, 3))
                x += w + rng.randint(-6, 6)
        return sky

    def _make_vignette(self):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(60):
            a = int(110 * (i / 60) ** 2.2)
            pygame.draw.rect(v, (10, 8, 14, a // 6), (60 - i, 60 - i, W - 2 * (60 - i), H - 2 * (60 - i)), 2)
        v2 = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, 90):
            pygame.draw.line(v2, (0, 0, 0, int(70 * (1 - y / 90))), (0, H - y), (W, H - y))
        v.blit(v2, (0, 0))
        return v

    # --- primitives ---------------------------------------------------------
    def _poly(self, surf, color, pts):
        if len(pts) >= 3:
            pygame.draw.polygon(surf, color, pts)
            gfxdraw.aapolygon(surf, [(int(x), int(y)) for x, y in pts], color)

    def _fogged(self, color, z):
        return mix(color, FOG, fog_t(z))

    def _quad_ground(self, surf, x0, x1, d0, d1, h, color):
        """Rectangle horizontal au sol (ou à la hauteur h) entre deux profondeurs."""
        z0, z1 = max(Z_NEAR, d0), max(Z_NEAR, d1)
        if z1 <= Z_NEAR:
            return
        p = self.cam.project
        self._poly(surf, color, [p(x0, z0, h), p(x1, z0, h), p(x1, z1, h), p(x0, z1, h)])

    # --- scène ------------------------------------------------------------
    def draw(self, surf, world, dt, particles=()):
        self.time += dt
        self.cam.follow(world.player.x, dt)
        surf.blit(self.sky, (self.cam.shake[0] * 0.3, 0))
        self._draw_ground(surf, world)
        self._draw_track(surf, world)
        self._draw_scenery(surf, world)
        self._draw_objects(surf, world)
        self._draw_player(surf, world)
        for x, y, _, _, life, color in particles:
            pygame.draw.circle(surf, color, (int(x), int(y)), max(1, int(life * 7)))
        surf.blit(self.vignette, (0, 0))

    def _draw_ground(self, surf, world):
        # dégradé du sol : le brouillard dépend seulement de la profondeur
        for y in range(HORIZON + 1, H, 3):
            z = FOCAL * GROUND / max(1, (y - HORIZON))
            pygame.draw.line(surf, self._fogged(EARTH, z), (0, y), (W, y), 3)
        # plateforme de ballast sous les trois voies
        left = C.TRACK_LEFT - 30
        right = C.TRACK_LEFT + C.LANE_WIDTH * C.LANE_COUNT + 30
        p = self.cam.project
        far, near = 2400, Z_NEAR
        self._poly(surf, self._fogged(BALLAST, 380), [p(left, near), p(right, near), p(right, far), p(left, far)])

    def _draw_track(self, surf, world):
        offset = world.distance % SLEEPER_EVERY
        p = self.cam.project
        # traverses, du fond vers l'avant
        d = 1100 - offset
        while d > -CAM_BACK + Z_NEAR:
            z = d + CAM_BACK
            if z > Z_NEAR:
                color = self._fogged((74, 58, 46), z)
                for lx in C.LANES_X:
                    self._poly(surf, color, [p(lx - 48, z), p(lx + 48, z), p(lx + 48, z + 12), p(lx - 48, z + 12)])
            d -= SLEEPER_EVERY
        # rails : lignes droites convergentes, avec reflet métallique
        for lx in C.LANES_X:
            for rx in (lx - 30, lx + 30):
                a, b = p(rx, Z_NEAR), p(rx, 2400)
                pygame.draw.line(surf, (70, 70, 76), a, b, 7)
                pygame.draw.line(surf, (200, 204, 212), (a[0], a[1] - 2), b, 3)

    def _draw_scenery(self, surf, world):
        p = self.cam.project
        left_x = C.TRACK_LEFT - WALL_OFFSET
        right_x = C.TRACK_LEFT + C.LANE_WIDTH * C.LANE_COUNT + WALL_OFFSET
        # murs latéraux par panneaux, du fond vers l'avant
        first = int(world.distance // PANEL_EVERY)
        items = []
        for k in range(first + 8, first - 2, -1):
            d0 = k * PANEL_EVERY - world.distance
            z0, z1 = d0 + CAM_BACK, d0 + PANEL_EVERY + CAM_BACK
            if z1 <= Z_NEAR:
                continue
            items.append((max(z0, z1), "panel", k, z0, z1))
        post_first = int(world.distance // POST_EVERY)
        for k in range(post_first + 4, post_first - 1, -1):
            z = k * POST_EVERY - world.distance + CAM_BACK
            if z > Z_NEAR + 4:
                items.append((z, "post", k, z, z))
        items.sort(key=lambda it: -it[0])
        for _, kind, k, z0, z1 in items:
            if kind == "panel":
                base = self.panel_colors[k % 64]
                zn, zf = max(Z_NEAR, z0), z1
                for wx, side in ((left_x, 1.0), (right_x, 0.82)):
                    color = self._fogged(shade(base, side), (zn + zf) / 2)
                    self._poly(surf, color, [p(wx, zn), p(wx, zf), p(wx, zf, WALL_H), p(wx, zn, WALL_H)])
                    for jh in (70, 150):
                        pygame.draw.line(surf, self._fogged(shade(base, 0.85), zf), p(wx, zn, jh), p(wx, zf, jh), 1)
                    # joint entre panneaux
                    pygame.draw.line(surf, self._fogged(shade(base, 0.6), zf), p(wx, zf), p(wx, zf, WALL_H), 2)
                    if self.panel_tags[k % 64] and zf - zn > 60:
                        # affiche / graffiti : rectangle coloré sur le mur
                        zm = (zn + zf) / 2
                        a, b = zn + (zf - zn) * 0.25, zn + (zf - zn) * 0.7
                        self._poly(surf, self._fogged((226, 222, 212), zm),
                                   [p(wx, a - 4, 56), p(wx, b + 4, 56), p(wx, b + 4, 144), p(wx, a - 4, 144)])
                        self._poly(surf, self._fogged(self.tag_colors[k % 64], zm),
                                   [p(wx, a, 62), p(wx, b, 62), p(wx, b, 138), p(wx, a, 138)])
                        self._poly(surf, self._fogged(shade(self.tag_colors[k % 64], 1.35), zm),
                                   [p(wx, a, 110), p(wx, b, 110), p(wx, b, 130), p(wx, a, 130)])
                # corniche
                for wx in (left_x, right_x):
                    pygame.draw.line(surf, self._fogged((150, 146, 140), zf), p(wx, zn, WALL_H), p(wx, zf, WALL_H), 3)
            else:
                # poteau de caténaire + traverse au-dessus des voies
                color = self._fogged((58, 62, 70), z0)
                s = FOCAL / z0
                for px in (C.TRACK_LEFT - 60, C.TRACK_LEFT + C.LANE_WIDTH * C.LANE_COUNT + 60):
                    pygame.draw.line(surf, color, p(px, z0), p(px, z0, 300), max(1, int(9 * s)))
                pygame.draw.line(surf, color, p(C.TRACK_LEFT - 60, z0, 292),
                                 p(C.TRACK_LEFT + C.LANE_WIDTH * C.LANE_COUNT + 60, z0, 292), max(1, int(6 * s)))
                for lx in C.LANES_X:
                    pygame.draw.line(surf, color, p(lx, z0, 292), p(lx, z0, 262), max(1, int(3 * s)))
        # fils de contact au-dessus de chaque voie
        for lx in C.LANES_X:
            pygame.draw.line(surf, (40, 42, 48), p(lx, Z_NEAR + 2, 262), p(lx, 2400, 262), 1)

    # --- objets -------------------------------------------------------------
    def _draw_objects(self, surf, world):
        items = []
        for o in world.obstacles:
            z_near = depth_of(o.y + o.length)
            z_far = depth_of(o.y)
            if z_far > Z_NEAR:
                items.append((z_near, "obs", o, z_near, z_far))
        for c in world.coins:
            z = depth_of(c.y)
            if z > Z_NEAR + 10:
                items.append((z, "coin", c, z, z))
        for pu in world.powerups:
            z = depth_of(pu.y)
            if z > Z_NEAR + 10:
                items.append((z, "pu", pu, z, z))
        items.sort(key=lambda it: -it[0])
        for _, kind, obj, zn, zf in items:
            if kind == "obs":
                if obj.kind == TRAIN:
                    self._draw_train(surf, C.LANES_X[obj.lane], zn, zf)
                else:
                    self._draw_barrier(surf, C.LANES_X[obj.lane], zn, obj.kind == LOW)
            elif kind == "coin":
                self._draw_coin(surf, obj.cx, zn, hash((obj.lane, round(obj.y))) % 10)
            else:
                self._draw_powerup(surf, C.LANES_X[obj.lane], zn, obj.kind)

    def _draw_train(self, surf, lx, z_near, z_far):
        p = self.cam.project
        x0, x1 = lx - TRAIN_W / 2, lx + TRAIN_W / 2
        zn = max(Z_NEAR + 20, z_near)  # un train qui dépasse le joueur sort proprement du champ
        body = (196, 200, 206)
        stripe = (200, 40, 48)
        # ombre portée au sol (ancre le train sur les rails)
        self._poly(surf, self._fogged((40, 38, 36), (zn + z_far) / 2),
                   [p(x0 - 8, zn), p(x1 + 8, zn), p(x1 + 8, z_far), p(x0 - 8, z_far)])
        # côté visible (celui tourné vers la caméra)
        side_x = x1 if self.cam.x > lx + 10 else (x0 if self.cam.x < lx - 10 else None)
        if side_x is not None:
            zm = (zn + z_far) / 2
            self._poly(surf, self._fogged(shade(body, 0.72), zm),
                       [p(side_x, zn), p(side_x, z_far), p(side_x, z_far, TRAIN_H), p(side_x, zn, TRAIN_H)])
            self._poly(surf, self._fogged(shade(stripe, 0.8), zm),
                       [p(side_x, zn, 52), p(side_x, z_far, 52), p(side_x, z_far, 64), p(side_x, zn, 64)])
            # bogies (roues) sous le flanc
            for a in (zn + 20, z_far - 60):
                if a > Z_NEAR and a + 40 < z_far + 1:
                    self._poly(surf, self._fogged((34, 34, 38), a),
                               [p(side_x, a), p(side_x, a + 40), p(side_x, a + 40, 18), p(side_x, a, 18)])
            # fenêtres le long du flanc
            n = int((z_far - zn) // 46)
            for i in range(n):
                a = zn + 12 + i * 46
                b = a + 30
                if b < z_far:
                    self._poly(surf, self._fogged((40, 52, 70), a), [p(side_x, a, 80), p(side_x, b, 80),
                                                                    p(side_x, b, 128), p(side_x, a, 128)])
        # toit : gris plus sombre, gouttières et blocs de climatisation
        zm = (zn + z_far) / 2
        self._poly(surf, self._fogged((150, 154, 160), zm),
                   [p(x0, zn, TRAIN_H), p(x1, zn, TRAIN_H), p(x1, z_far, TRAIN_H), p(x0, z_far, TRAIN_H)])
        for gx in (x0 + 14, x1 - 14):
            pygame.draw.line(surf, self._fogged((110, 114, 120), zm), p(gx, zn, TRAIN_H), p(gx, z_far, TRAIN_H), 2)
        for a in (z_far - 70, zn + 40):
            if a > zn and a + 36 < z_far:
                self._poly(surf, self._fogged((120, 124, 130), a),
                           [p(lx - 30, a, TRAIN_H + 1), p(lx + 30, a, TRAIN_H + 1),
                            p(lx + 30, a + 36, TRAIN_H + 1), p(lx - 30, a + 36, TRAIN_H + 1)])
        if z_near < Z_NEAR + 20:
            return  # la face avant est derrière la caméra
        # face avant
        z = z_near
        s = FOCAL / z
        f = lambda c: self._fogged(c, z)  # noqa: E731
        tl, br = p(x0, z, TRAIN_H), p(x1, z, 0)
        rect = pygame.Rect(int(tl[0]), int(tl[1]), int(br[0] - tl[0]), int(br[1] - tl[1]))
        pygame.draw.rect(surf, f(body), rect, border_radius=max(2, int(12 * s)))
        pygame.draw.rect(surf, f(shade(body, 0.7)), rect, max(1, int(3 * s)), border_radius=max(2, int(12 * s)))
        # pare-brise avec reflet
        ws = pygame.Rect(0, 0, int(rect.w * 0.8), int(rect.h * 0.3))
        ws.midtop = (rect.centerx, rect.top + int(rect.h * 0.14))
        pygame.draw.rect(surf, f((34, 46, 64)), ws, border_radius=max(1, int(6 * s)))
        pygame.draw.polygon(surf, f((90, 110, 140)), [(ws.left + ws.w * 0.1, ws.bottom), (ws.left + ws.w * 0.35, ws.top),
                                                        (ws.left + ws.w * 0.47, ws.top), (ws.left + ws.w * 0.22, ws.bottom)])
        # girouette (destination)
        sign = pygame.Rect(0, 0, int(rect.w * 0.5), max(2, int(rect.h * 0.07)))
        sign.midbottom = (rect.centerx, ws.top - max(1, int(3 * s)))
        pygame.draw.rect(surf, f((20, 20, 20)), sign)
        pygame.draw.rect(surf, f((255, 170, 40)), sign.inflate(-sign.w * 0.3, -max(0, sign.h * 0.5)))
        # bande rouge et phares allumés
        band = pygame.Rect(rect.left, rect.top + int(rect.h * 0.6), rect.w, max(2, int(rect.h * 0.08)))
        pygame.draw.rect(surf, f(stripe), band)
        for hx in (rect.left + rect.w * 0.18, rect.right - rect.w * 0.18):
            hy = rect.top + rect.h * 0.8
            r = max(2, int(9 * s))
            glow = 1 - fog_t(z)
            if glow > 0.05:
                gr = r * 3
                g = pygame.Surface((gr * 2, gr * 2))
                for rr in range(gr, 0, -max(1, gr // 6)):
                    k = glow * 70 * (1 - rr / gr) ** 1.5
                    pygame.draw.circle(g, (int(k), int(k * 0.92), int(k * 0.7)), (gr, gr), rr)
                surf.blit(g, (hx - gr, hy - gr), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(surf, f((255, 246, 214)), (int(hx), int(hy)), r)
        # attelage / chasse-pierres
        pygame.draw.rect(surf, f((50, 50, 56)), (rect.left + rect.w * 0.1, rect.bottom - max(2, int(10 * s)),
                                                 rect.w * 0.8, max(2, int(10 * s))))

    def _draw_barrier(self, surf, lx, z, low):
        if z <= Z_NEAR:
            return
        p = self.cam.project
        s = FOCAL / z
        f = lambda c: self._fogged(c, z)  # noqa: E731
        x0, x1 = lx - 58, lx + 58
        if low:
            # barrière basse rayée jaune et noir sur deux pieds
            for px in (x0 + 10, x1 - 10):
                pygame.draw.line(surf, f((70, 70, 74)), p(px, z), p(px, z, 26), max(1, int(6 * s)))
            tl, br = p(x0, z, 44), p(x1, z, 22)
            rect = pygame.Rect(int(tl[0]), int(tl[1]), max(1, int(br[0] - tl[0])), max(1, int(br[1] - tl[1])))
            stripe = max(2, rect.w // 8)
            for i, xx in enumerate(range(rect.left, rect.right, stripe)):
                pygame.draw.rect(surf, f((245, 190, 20) if i % 2 == 0 else (30, 30, 30)),
                                 (xx, rect.top, min(stripe, rect.right - xx), rect.h))
            pygame.draw.rect(surf, f((40, 40, 40)), rect, max(1, int(2 * s)))
            pygame.draw.line(surf, f((255, 240, 180)), rect.topleft, rect.topright, max(1, int(2 * s)))
        else:
            # portique haut : on passe dessous en glissant
            for px in (x0, x1):
                pygame.draw.line(surf, f((110, 112, 120)), p(px, z), p(px, z, 118), max(2, int(8 * s)))
            tl, br = p(x0, z, 118), p(x1, z, 70)
            rect = pygame.Rect(int(tl[0]), int(tl[1]), max(1, int(br[0] - tl[0])), max(1, int(br[1] - tl[1])))
            stripe = max(2, rect.w // 7)
            for i, xx in enumerate(range(rect.left, rect.right, stripe)):
                pygame.draw.rect(surf, f((215, 40, 50) if i % 2 == 0 else (240, 240, 240)),
                                 (xx, rect.top, min(stripe, rect.right - xx), rect.h))
            pygame.draw.rect(surf, f((60, 60, 60)), rect, max(1, int(2 * s)))
            # feu clignotant
            if int(self.time * 3) % 2 == 0:
                c = p(lx, z, 128)
                pygame.draw.circle(surf, f((255, 80, 60)), (int(c[0]), int(c[1])), max(2, int(6 * s)))

    def _draw_coin(self, surf, xw, z, phase):
        p = self.cam.project
        s = FOCAL / z
        cx, cy = p(xw, z, 46 + 5 * math.sin(self.time * 4 + phase))
        r = max(2, int(17 * s))
        spin = abs(math.cos(self.time * 5 + phase))
        w = max(2, int(r * 2 * (0.25 + 0.75 * spin)))
        rect = pygame.Rect(0, 0, w, r * 2)
        rect.center = (int(cx), int(cy))
        pygame.draw.ellipse(surf, self._fogged((196, 140, 10), z), rect)
        pygame.draw.ellipse(surf, self._fogged((255, 206, 50), z), rect.inflate(-max(1, w // 5), -max(1, r // 3)))
        if spin > 0.5:
            pygame.draw.ellipse(surf, self._fogged((255, 246, 200), z),
                                (rect.centerx - w // 6, rect.top + r // 3, max(1, w // 5), max(1, r // 2)))
        # ombre au sol
        gx, gy = p(xw, z)
        pygame.draw.ellipse(surf, self._fogged((60, 56, 52), z), (gx - r * 0.8, gy - r * 0.2, r * 1.6, r * 0.4))

    def _draw_powerup(self, surf, lx, z, kind):
        p = self.cam.project
        s = FOCAL / z
        cx, cy = p(lx, z, 56 + 8 * math.sin(self.time * 3))
        size = max(4, int(46 * s))
        col = POWERUP_GLOW.get(kind, (90, 170, 255))
        hr = int(size * 1.1)
        halo = pygame.Surface((hr * 2, hr * 2))
        strength = 0.45 * (1 - fog_t(z))
        for rr in range(hr, 2, -max(1, hr // 8)):
            k = strength * (1 - rr / hr) ** 1.6
            pygame.draw.circle(halo, (int(col[0] * k), int(col[1] * k), int(col[2] * k)), (hr, hr), rr)
        surf.blit(halo, (cx - hr, cy - hr), special_flags=pygame.BLEND_RGB_ADD)
        icon = pygame.transform.smoothscale(self.assets.powerups[kind], (size, size))
        surf.blit(icon, icon.get_rect(center=(int(cx), int(cy))))

    # --- coureur vu de dos --------------------------------------------------
    def _draw_player(self, surf, world):
        pl = world.player
        z = CAM_BACK
        s = FOCAL / z
        p = self.cam.project
        gx, gy = p(pl.x, z)
        # ombre : rétrécit quand il saute
        sh_w = max(10, int((58 - pl.height * 0.15) * s))
        shadow = pygame.Surface((sh_w, max(4, sh_w // 4)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 120), shadow.get_rect())
        surf.blit(shadow, shadow.get_rect(center=(int(gx), int(gy))))

        if world.invuln_timer > 0 and int(world.invuln_timer * 12) % 2 == 0:
            return
        foot_y = gy - pl.height * s
        run = math.sin(pl.anim_time * 14)
        airborne = pl.height > 1
        sliding = pl.sliding
        k = s * 0.9  # taille du personnage

        def P(dx, dy):
            return (gx + dx * k, foot_y - dy * k)

        skin, hoodie, jeans, shoe = (214, 164, 124), (38, 110, 200), (44, 58, 92), (235, 235, 235)
        hood_dark, bag = (28, 84, 160), (60, 60, 64)
        if sliding:
            # glissade : corps bas et penché, jambes vers l'avant
            pygame.draw.line(surf, jeans, P(-10, 8), P(-18, 2), int(11 * k))
            pygame.draw.line(surf, jeans, P(10, 8), P(18, 2), int(11 * k))
            self._poly(surf, hoodie, [P(-22, 8), P(22, 8), P(18, 44), P(-18, 44)])
            pygame.draw.circle(surf, (30, 24, 22), P(0, 54), int(12 * k))
            pygame.draw.rect(surf, bag, (*P(-14, 42), 28 * k, 22 * k), border_radius=int(5 * k))
            return
        lift = 0 if airborne else run
        # jambes (vue de dos : alternance haut/bas)
        for side, ph in ((-1, lift), (1, -lift)):
            knee = P(side * 9, 30 + 6 * max(0, ph))
            foot = P(side * 10, 2 + 16 * max(0, ph) + (10 if airborne else 0))
            pygame.draw.line(surf, jeans, P(side * 8, 50), knee, int(12 * k))
            pygame.draw.line(surf, jeans, knee, foot, int(11 * k))
            sole = pygame.Rect(0, 0, int(14 * k), int(8 * k))
            sole.center = foot
            pygame.draw.ellipse(surf, shoe, sole)
            pygame.draw.ellipse(surf, (190, 60, 60), sole.inflate(-int(6 * k), -int(4 * k)))
        # bras qui balancent
        for side, ph in ((-1, -run), (1, run)):
            arm_top = P(side * 20, 88)
            hand = P(side * (26 + (8 if airborne else 0)), 60 + 12 * ph + (20 if airborne else 0))
            pygame.draw.line(surf, hood_dark, arm_top, hand, int(10 * k))
            pygame.draw.circle(surf, skin, hand, int(5 * k))
        # torse (sweat à capuche) + ombrage
        self._poly(surf, hoodie, [P(-20, 50), P(20, 50), P(22, 92), P(-22, 92)])
        self._poly(surf, hood_dark, [P(8, 50), P(20, 50), P(22, 92), P(12, 92)])
        # sac à dos (ou jetpack pendant le vol)
        pack = pygame.Rect(0, 0, int(26 * k), int(30 * k))
        pack.midtop = P(0, 88)
        if pl.flying:
            for side in (-1, 1):
                cyl = pygame.Rect(0, 0, int(11 * k), int(34 * k))
                cyl.center = P(side * 15, 74)
                pygame.draw.rect(surf, (150, 156, 168), cyl, border_radius=int(4 * k))
                pygame.draw.rect(surf, (90, 96, 110), cyl, max(1, int(2 * k)), border_radius=int(4 * k))
                # flamme animée sous chaque réacteur
                flame = 1 + 0.4 * math.sin(self.time * 40 + side)
                fx, fy = P(side * 15, 4)
                pts = [(fx - 7 * k, fy), (fx + 7 * k, fy), (fx, fy + 30 * k * flame)]
                self._poly(surf, (255, 160, 40), pts)
                pts2 = [(fx - 3 * k, fy), (fx + 3 * k, fy), (fx, fy + 18 * k * flame)]
                self._poly(surf, (255, 236, 150), pts2)
        pygame.draw.rect(surf, bag, pack, border_radius=int(6 * k))
        pygame.draw.rect(surf, (80, 80, 86), pack.inflate(-int(8 * k), -int(18 * k)).move(0, int(8 * k)),
                         border_radius=int(3 * k))
        # tête : cheveux + capuche baissée
        pygame.draw.ellipse(surf, hood_dark, (*P(-15, 96), 30 * k, 12 * k))
        pygame.draw.circle(surf, skin, P(0, 104), int(12 * k))
        pygame.draw.circle(surf, (30, 24, 22), P(0, 106), int(12 * k))
        pygame.draw.rect(surf, (215, 40, 50), (*P(-13, 118), 26 * k, 8 * k), border_radius=int(4 * k))  # casquette
        if world.shield:
            r = int(78 * k)
            bubble = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(bubble, (90, 170, 255, 45), (r + 2, r + 2), r)
            pygame.draw.circle(bubble, (140, 200, 255, 170), (r + 2, r + 2), r, 3)
            surf.blit(bubble, bubble.get_rect(center=P(0, 62)))
