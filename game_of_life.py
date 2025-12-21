from __future__ import annotations
from typing import Callable, FrozenSet, Iterable, Iterator, Tuple, List
import time

# Typen (unendliches Grid als Menge lebender Zellen)
Cell = Tuple[int, int]
Alive = FrozenSet[Cell]                 # immutable (funktional)
Rule = Callable[[bool, int], bool]      # (is_alive_now, alive_neighbor_count) -> is_alive_next

NEIGH: Tuple[Cell, ...] = tuple(
    (dx, dy)
    for dx in (-1, 0, 1)
    for dy in (-1, 0, 1)
    if (dx, dy) != (0, 0)
)

# Regeln (pure functions)
def conway_rule(is_alive: bool, n: int) -> bool:
    return (n == 3) or (is_alive and n == 2)

def highlife_rule(is_alive: bool, n: int) -> bool:
    return (n in (3, 6)) or (is_alive and n == 2)

# Kernlogik: unendlicher Step über Alive-Set
def neighbors(c: Cell) -> Iterable[Cell]:
    x, y = c
    return ((x + dx, y + dy) for dx, dy in NEIGH)

def step_func(rule: Rule) -> Callable[[Alive], Alive]:
    """
    Factory: gibt eine Step-Funktion zurück, parametrisiert mit 'rule'.
    Welt ist unendlich, gespeichert werden nur lebende Zellen (Alive-Set).
    """
    def step(alive: Alive) -> Alive:
        candidates = frozenset(alive | frozenset(n for c in alive for n in neighbors(c)))

        def n_alive(c: Cell) -> int:
            return sum((n in alive) for n in neighbors(c))

        return frozenset(
            c for c in candidates
            if rule((c in alive), n_alive(c))
        )
    return step

# Generator, unendliche Generationen
def generations(start: Alive, step: Callable[[Alive], Alive]) -> Iterator[Alive]:
    alive = start
    while True:
        yield alive
        alive = step(alive)

# Parsing & Anzeige (Ausschnitt automatisch via Bounding Box)
def alive_from_strings(lines: List[str], origin: Cell = (0, 0), live_char: str = "#") -> Alive:
    ox, oy = origin
    return frozenset(
        (ox + x, oy + y)
        for y, row in enumerate(lines)
        for x, ch in enumerate(row)
        if ch == live_char
    )

def bbox(alive: Alive, pad: int = 1) -> Tuple[int, int, int, int]:
    xs = [x for x, _ in alive]
    ys = [y for _, y in alive]
    return (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)

def display(alive: Alive, pad: int = 2, live: str = "#", dead: str = ".") -> None:
    if not alive:
        print("(empty)\n")
        return
    minx, maxx, miny, maxy = bbox(alive, pad=pad)
    print("\n".join(
        "".join(live if (x, y) in alive else dead for x in range(minx, maxx + 1))
        for y in range(miny, maxy + 1)
    ))
    print()

# Demo
def main() -> None:
    # Startkonfig
    start = [
        "..........",
        "....###...",
        "...###....",
        "..###.....",
        "..........",
    ]
    alive0 = alive_from_strings(start)

    rule = conway_rule          # oder: highlife_rule
    step = step_func(rule)
    gen = generations(alive0, step)

    for i in range(50):
        print(f"Generation {i}:")
        display(next(gen), pad=2)
        time.sleep(0.5)

if __name__ == "__main__":
    main()