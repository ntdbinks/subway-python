"""Tests de la logique de jeu (sans fenêtre) : python -m pytest"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src import config as C, storage
from src.entities import HIGH, LOW, TRAIN, Obstacle, Player
from src.world import World


def _obstacle_on_player(kind, lane=1):
    o = Obstacle(kind, lane, 0)
    o.y = C.PLAYER_Y - o.length // 2
    return o


def test_train_always_hits():
    p = Player()
    p.height = 200
    assert _obstacle_on_player(TRAIN).hits(p)


def test_low_barrier_is_jumpable():
    p = Player()
    assert _obstacle_on_player(LOW).hits(p)
    p.height = C.JUMP_CLEARANCE + 1
    assert not _obstacle_on_player(LOW).hits(p)


def test_high_barrier_requires_slide():
    p = Player()
    assert _obstacle_on_player(HIGH).hits(p)
    p.slide()
    assert not _obstacle_on_player(HIGH).hits(p)


def test_other_lane_is_safe():
    assert not _obstacle_on_player(TRAIN, lane=0).hits(Player())


def test_lane_bounds():
    p = Player()
    assert p.move(-1) and not p.move(-1)
    assert p.lane == 0


def test_jump_lands():
    p = Player()
    assert p.jump() and not p.jump()
    for _ in range(200):
        p.update(1 / 60)
    assert p.on_ground and p.height == 0


def test_every_row_leaves_a_free_lane():
    w = World(seed=42)
    for _ in range(500):
        w.obstacles.clear()
        w._spawn_row()
        blocked = {o.lane for o in w.obstacles}
        assert len(blocked) < C.LANE_COUNT


def test_speed_is_capped_and_score_grows():
    w = World(seed=1)
    w.player.height = 10_000  # immortel pour le test : ne touche que trains → on vide
    for _ in range(60 * 120):
        w.obstacles.clear()
        w.update(1 / 60)
    assert w.speed == C.MAX_SPEED
    assert w.score > 0


def test_storage_roundtrip(tmp_path):
    path = tmp_path / "save.json"
    data = storage.load(path)
    assert storage.record_game(data, 120, 7)
    storage.save(data, path)
    again = storage.load(path)
    assert again["best_score"] == 120 and again["total_coins"] == 7
    assert not storage.record_game(again, 50, 1)


def test_corrupted_save_falls_back(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{pas du json")
    data = storage.load(path)
    assert {k: data[k] for k in storage.DEFAULT} == storage.DEFAULT
    assert len(data["missions"]) == 3 and data["mission_level"] == 0


# --- bonus -----------------------------------------------------------------
from src.entities import JETPACK, MAGNET, MULTIPLIER, SHIELD, SNEAKERS, Coin, PowerUp


def _world_with(*items):
    w = World(seed=3)
    w._until_next_row = 10**9  # pas de génération aléatoire pendant le test
    for item in items:
        (w.powerups if isinstance(item, PowerUp) else w.obstacles).append(item)
    return w


def test_shield_absorbs_one_hit_then_invulnerable():
    w = _world_with(PowerUp(SHIELD, 1, C.PLAYER_Y))
    w.update(1 / 60)
    assert w.shield
    w.obstacles.append(_obstacle_on_player(TRAIN))
    w.update(1 / 60)
    assert w.alive and not w.shield and w.invuln_timer > 0
    assert not w.obstacles  # l'obstacle touché est détruit
    w.obstacles.append(_obstacle_on_player(TRAIN))
    w.update(1 / 60)
    assert w.alive  # encore invincible
    w.invuln_timer = 0
    w.update(1 / 60)
    assert not w.alive  # plus de bouclier : game over


def test_magnet_pulls_coins_from_other_lanes():
    w = _world_with(PowerUp(MAGNET, 1, C.PLAYER_Y))
    w.update(1 / 60)
    assert w.magnet_timer > 0
    w.coins.append(Coin(0, C.PLAYER_Y - 150))
    for _ in range(60):
        w.update(1 / 60)
    assert w.coin_count == 1


def test_magnet_expires():
    w = _world_with(PowerUp(MAGNET, 1, C.PLAYER_Y))
    for _ in range(int(60 * (C.MAGNET_TIME + 0.5))):
        w.update(1 / 60)
    assert w.magnet_timer == 0


def test_powerups_never_spawn_in_blocked_lane():
    w = World(seed=7)
    for _ in range(2000):
        w.obstacles.clear(); w.powerups.clear(); w.coins.clear()
        w._spawn_row()
        blocked = {o.lane for o in w.obstacles}
        assert all(p.lane not in blocked for p in w.powerups)


def test_jetpack_flies_over_trains_and_expires():
    w = _world_with(PowerUp(JETPACK, 1, C.PLAYER_Y))
    w.update(1 / 60)
    assert w.player.flying and w.jetpack_timer > 0
    # un train sous le joueur ne le tue pas pendant le vol
    w.obstacles.append(_obstacle_on_player(TRAIN))
    for _ in range(30):
        w.update(1 / 60)
    assert w.alive
    # une traînée de pièces est générée
    assert w.coins
    # à l'expiration, il ne vole plus
    for _ in range(int(60 * (C.JETPACK_TIME + 0.5))):
        w.update(1 / 60)
    assert not w.player.flying and w.jetpack_timer == 0


def test_multiplier_doubles_coin_score():
    plain = _world_with()
    plain.update(1 / 60)
    plain.coins.append(Coin(1, C.PLAYER_Y))
    plain.update(1 / 60)
    base = plain.score

    w = _world_with(PowerUp(MULTIPLIER, 1, C.PLAYER_Y))
    w.update(1 / 60)
    assert w.multiplier == 2
    w.coins.append(Coin(1, C.PLAYER_Y))
    w.update(1 / 60)
    assert w.coin_count == 1 and w.score >= base + C.COIN_VALUE  # pièce comptée ×2


def test_sneakers_boost_higher_jump():
    normal = _world_with()
    normal.update(1 / 60)
    normal.player.jump()
    for _ in range(20):
        normal.update(1 / 60)
    peak_normal = max(normal.player.height, 1)

    w = _world_with(PowerUp(SNEAKERS, 1, C.PLAYER_Y))
    w.update(1 / 60)
    assert w.sneakers_timer > 0 and w.player.jump_boost > 1
    w.player.jump()
    peak = 0
    for _ in range(30):
        w.update(1 / 60)
        peak = max(peak, w.player.height)
    assert peak > peak_normal
