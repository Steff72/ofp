from game_of_life import (
    conway_rule,
    highlife_rule,
    step_func,
    generations,
    alive_from_strings,
)


def test_alive_from_strings_returns_alive_set():
    alive = alive_from_strings(["#.", ".#"])
    assert alive == frozenset({(0, 0), (1, 1)})


def test_conway_block_stays_stable():
    start = alive_from_strings(["##", "##"])
    step = step_func(conway_rule)
    assert step(start) == start


def test_blinker_oscillates_between_states():
    horizontal = alive_from_strings(["...", "###", "..."])
    vertical = alive_from_strings([".#.", ".#.", ".#."])
    step = step_func(conway_rule)
    assert step(horizontal) == vertical
    assert step(vertical) == horizontal


def test_highlife_spawns_on_six_neighbors_only_for_highlife():
    crowded = alive_from_strings(["###", "#.#", ".#."])
    conway_next = step_func(conway_rule)(crowded)
    highlife_next = step_func(highlife_rule)(crowded)
    assert (1, 1) not in conway_next
    assert (1, 1) in highlife_next


def test_generations_yields_successive_states():
    start = alive_from_strings([".#.", ".#.", ".#."])
    step = step_func(conway_rule)
    gen = generations(start, step)
    first = next(gen)
    second = next(gen)
    assert first == start
    assert second == step(start)
