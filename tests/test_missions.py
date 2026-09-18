"""Tests du système de missions (logique pure)."""
import random

from src import missions as M


def test_generate_set_three_distinct():
    s = M.generate_set(0, random.Random(1))
    assert len(s) == 3
    assert len({m["key"] for m in s}) == 3
    assert all(not m["done"] for m in s)
    assert all(str(m["target"]) in m["text"] for m in s)


def test_targets_grow_with_level():
    assert M._target("coins", 0) < M._target("coins", 3)


def test_update_marks_done_and_reports():
    save = {"missions": [
        {"key": "coins", "target": 10, "text": "c", "done": False},
        {"key": "jumps", "target": 5, "text": "j", "done": False},
        {"key": "score", "target": 999, "text": "s", "done": False},
    ], "mission_level": 0}
    res = M.update_after_run(save, {"coins": 12, "jumps": 6, "score": 100})
    assert set(res["completed"]) == {"c", "j"}
    assert not res["leveled_up"]
    assert save["missions"][0]["done"] and not save["missions"][2]["done"]


def test_all_done_levels_up_and_regenerates():
    save = {"missions": [
        {"key": "coins", "target": 1, "text": "c", "done": False},
        {"key": "jumps", "target": 1, "text": "j", "done": False},
        {"key": "score", "target": 1, "text": "s", "done": False},
    ], "mission_level": 0}
    res = M.update_after_run(save, {"coins": 5, "jumps": 5, "score": 5})
    assert res["leveled_up"] and save["mission_level"] == 1
    assert len(save["missions"]) == 3 and all(not m["done"] for m in save["missions"])


def test_progress_caps_at_target():
    m = {"key": "coins", "target": 10}
    assert M.progress(m, {"coins": 4}) == (4, 10)
    assert M.progress(m, {"coins": 99}) == (10, 10)


def test_run_stats_feed_missions():
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from src.world import World
    w = World(seed=1)
    w.update(1 / 60)
    st = w.run_stats()
    assert set(st) >= {"coins", "meters", "jumps", "powerups", "jetpacks", "score"}
