"""Icônes de bonus et sons générés par code : le jeu tourne sans fichier externe.

Le décor, les trains et le coureur sont dessinés en perspective par render3d.py.
"""
import math
import struct

import pygame


def _disc(s, ring):
    pygame.draw.circle(s, (255, 255, 255), (19, 19), 18)
    pygame.draw.circle(s, ring, (19, 19), 18, 2)


def _powerup(kind: str) -> pygame.Surface:
    s = pygame.Surface((38, 38), pygame.SRCALPHA)
    if kind == "magnet":
        _disc(s, (200, 40, 50))
        # aimant en fer à cheval (U), pointes grises en haut
        pygame.draw.arc(s, (220, 40, 50), (8, 9, 22, 22), math.pi, math.tau, 6)
        pygame.draw.rect(s, (220, 40, 50), (8, 10, 6, 10))
        pygame.draw.rect(s, (220, 40, 50), (24, 10, 6, 10))
        pygame.draw.rect(s, (170, 170, 185), (8, 6, 6, 5))
        pygame.draw.rect(s, (170, 170, 185), (24, 6, 6, 5))
    elif kind == "shield":
        pygame.draw.circle(s, (255, 255, 255), (19, 19), 18)
        pts = [(19, 6), (30, 10), (28, 22), (19, 32), (10, 22), (8, 10)]
        pygame.draw.polygon(s, (40, 140, 255), pts)
        pygame.draw.polygon(s, (20, 90, 200), pts, 2)
    elif kind == "jetpack":
        _disc(s, (240, 130, 40))
        pygame.draw.rect(s, (90, 96, 110), (13, 9, 12, 16), border_radius=4)   # réservoir
        pygame.draw.rect(s, (60, 66, 80), (13, 9, 12, 16), 1, border_radius=4)
        for fx in (11, 27):                                                     # flammes
            pygame.draw.polygon(s, (255, 170, 40), [(fx - 3, 25), (fx + 3, 25), (fx, 34)])
            pygame.draw.polygon(s, (255, 230, 120), [(fx - 1, 25), (fx + 1, 25), (fx, 30)])
    elif kind == "multiplier":
        _disc(s, (150, 90, 210))
        f = pygame.font.SysFont("arial", 20, bold=True)
        t = f.render("x2", True, (150, 60, 210))
        s.blit(t, t.get_rect(center=(19, 20)))
    elif kind == "sneakers":
        _disc(s, (30, 170, 110))
        pygame.draw.polygon(s, (40, 200, 130), [(8, 24), (24, 24), (30, 20), (30, 26), (8, 27)])
        pygame.draw.rect(s, (255, 255, 255), (9, 26, 22, 3))                    # semelle
        pygame.draw.line(s, (255, 255, 255), (14, 18), (20, 22), 2)             # lacet
    else:
        _disc(s, (120, 120, 130))
    return s


def _tone(freq_start, freq_end, duration=0.15, volume=0.35):
    """Génère un son (balayage de fréquence) sans dépendance externe."""
    try:
        rate, fmt, channels = pygame.mixer.get_init()
    except TypeError:
        return None
    n = int(rate * duration)
    frames = bytearray()
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = freq_start + (freq_end - freq_start) * t
        phase += math.tau * freq / rate
        env = (1 - t) ** 2
        sample = int(32767 * volume * env * math.sin(phase))
        frames += struct.pack("<h", sample) * channels
    return pygame.mixer.Sound(buffer=bytes(frames))


class Assets:
    def __init__(self):
        self.powerups = {k: _powerup(k) for k in ("magnet", "shield", "jetpack", "multiplier", "sneakers")}
        self.sounds = {}
        if pygame.mixer.get_init():
            self.sounds = {
                "jump": _tone(300, 700),
                "coin": _tone(900, 1400, 0.08, 0.25),
                "crash": _tone(220, 40, 0.45, 0.5),
                "powerup": _tone(500, 1200, 0.25, 0.3),
                "shield": _tone(700, 200, 0.3, 0.4),
                "jetpack": _tone(200, 900, 0.5, 0.35),
            }
        self.muted = False

    def play(self, name: str):
        snd = self.sounds.get(name)
        if snd and not self.muted:
            snd.play()
