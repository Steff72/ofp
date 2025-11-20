from typing import Callable, Tuple, List, Generator
import time

# Typ-Alias-Definitionen
Grid = Tuple[Tuple[bool, ...], ...]
CellCheck = Callable[[int, int], bool]
Rule = Callable[[CellCheck, int, int], bool]
StepFunction = Callable[[Grid], Grid]

# Regel-Funktionen

def conway_rule(cell_check: CellCheck, x: int, y: int) -> bool:
    """
    Berechnet den nächsten Zustand einer Zelle gemäß Conways Regel.
    Lebt eine Zelle weiter, wenn sie aktuell lebt und genau 2 oder 3 lebende Nachbarn hat,
    oder wenn sie aktuell tot ist und genau 3 lebende Nachbarn hat.
    """
    alive_neighbors = sum(  # True/False als 1/0 gezählt
        cell_check(x + dx, y + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if dx or dy  # schließt (0,0) aus
    )
    alive = cell_check(x, y)
    return (alive and alive_neighbors in (2, 3)) or (not alive and alive_neighbors == 3)

def highlife_rule(cell_check: CellCheck, x: int, y: int) -> bool:
    """
    Alternative Regel (HighLife):
    Eine leblose Zelle wird lebendig, wenn sie genau 3 oder 6 lebende Nachbarn hat,
    ansonsten gilt wie bei Conway.
    """
    alive_neighbors = sum(  # True/False als 1/0 gezählt
        cell_check(x + dx, y + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if dx or dy  # schließt (0,0) aus
    )
    alive = cell_check(x, y)
    return (alive and alive_neighbors in (2, 3)) or (not alive and alive_neighbors in (3, 6))

# Step-Funktion: Erzeugt aus einem Grid das Grid der nächsten Generation.
def step_func(rule: Rule) -> StepFunction:
    """
    Erzeugt eine Step-Funktion für ein Grid mit festen Rändern.
    Außerhalb des Grids wird stets angenommen, dass die Zellen tot sind.
    """
    def step(grid: Grid) -> Grid:
        n_rows = len(grid)
        n_cols = len(grid[0]) if n_rows > 0 else 0

        # Lebt die Zelle an der Stelle (x, y)?, Closure, das sich grid, n_rows, n_cols merkt
        def cell_check(x: int, y: int) -> bool: 
            if 0 <= y < n_rows and 0 <= x < n_cols: # Grenzprüfung
                return grid[y][x]
            return False

        return tuple(
            tuple(rule(cell_check, x, y) for x in range(n_cols))
            for y in range(n_rows)
        )
    return step

# Alternative Weltenvariante: Toroidale Welt (wrap-around)
def step_func_torus(rule: Rule) -> StepFunction:
    """
    Erzeugt eine Step-Funktion für ein toroidales Grid.
    Dabei werden Zellen am rechten Rand mit denen am linken Rand (und oben/unten) verbunden.
    """
    def step(grid: Grid) -> Grid:
        n_rows = len(grid)
        n_cols = len(grid[0]) if n_rows > 0 else 0

        def cell_check(x: int, y: int) -> bool:
            return grid[y % n_rows][x % n_cols]     # Modulo macht wrap-around

        return tuple(
            tuple(rule(cell_check, x, y) for x in range(n_cols))
            for y in range(n_rows)
        )
    return step

# Generator, der aufeinanderfolgende Generationen produziert.
def generations(start_grid: Grid, step: StepFunction) -> Generator[Grid, None, None]:
    """
    Erzeugt eine Folge von Generationen,
    ausgehend von start_grid und unter Anwendung der step-Funktion.
    """
    grid = start_grid
    while True:
        yield grid
        grid = step(grid)

# Anzeige-Funktion und Hilfsfunktion zum Erzeugen eines Grids aus Strings.
def display_grid(grid: Grid) -> None:
    """
    Gibt das Grid in der Konsole aus. Für lebende Zellen wird '#' verwendet, für tote Zellen '.'.
    """
    for row in grid:
        print(''.join('#' if cell else '.' for cell in row))
    print()  # Leere Zeile zur Trennung

def grid_from_strings(lines: List[str]) -> Grid:
    """
    Wandelt eine Liste von Strings in ein Grid um.
    Das Zeichen '#' repräsentiert eine lebende Zelle, alle anderen Zeichen werden als tot gewertet.
    """
    return tuple(tuple(c == '#' for c in line) for line in lines)

# Test
def main():
    # Beispiel-Startkonfiguration
    start = [
        "..........",
        "....#.....",
        "...##.....",
        "...#......",
        "..........",
    ]
    grid = grid_from_strings(start)
    
    # Auswahl der Regel und der Step-Funktion:
    rule = conway_rule
    # rule = highlife_rule 

    step = step_func(rule)
    # step = step_func_torus(rule)
    
    gen = generations(grid, step)
    
    # Simuliere 10 Generationen
    for i in range(10):
        print(f"Generation {i}:")
        current = next(gen)
        display_grid(current)
        time.sleep(0.5)

if __name__ == "__main__":
    main()