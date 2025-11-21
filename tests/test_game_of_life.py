from game_of_life import (
    conway_rule,
    highlife_rule,
    step_func,
    step_func_torus,
    generations,
    grid_from_strings,
)


def test_grid_from_strings_returns_bool_grid():
    grid = grid_from_strings(["#.", ".#"])
    assert grid == ((True, False), (False, True))


def test_conway_block_stays_stable():
    start = grid_from_strings(["##", "##"])
    step = step_func(conway_rule)
    assert step(start) == start


def test_blinker_oscillates_between_states():
    horizontal = grid_from_strings(["...", "###", "..."])
    vertical = grid_from_strings([".#.", ".#.", ".#."])
    step = step_func(conway_rule)
    assert step(horizontal) == vertical
    assert step(vertical) == horizontal


def test_highlife_spawns_on_six_neighbors_only_for_highlife():
    crowded = grid_from_strings(["###", "#.#", ".#."])
    conway_next = step_func(conway_rule)(crowded)
    highlife_next = step_func(highlife_rule)(crowded)
    assert conway_next[1][1] is False
    assert highlife_next[1][1] is True


def test_generations_yields_successive_states():
    start = grid_from_strings([".#.", ".#.", ".#."])
    step = step_func(conway_rule)
    gen = generations(start, step)
    first = next(gen)
    second = next(gen)
    assert first == start
    assert second == step(start)


def test_torus_wraps_edges():
    start = grid_from_strings(["###", "...", "..."])
    normal_step = step_func(conway_rule)
    torus_step = step_func_torus(conway_rule)
    normal = normal_step(start)
    torus = torus_step(start)
    assert normal[2][1] is False
    assert torus[2][1] is True
