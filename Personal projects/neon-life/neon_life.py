#!/usr/bin/env python3
"""
Neon Life: a colorful terminal simulation of Conway's Game of Life.
Run: python3 neon_life.py
"""

import os
import random
import shutil
import sys
import time

ALIVE = "█"
DEAD = " "

# ANSI 256-color neon palette
PALETTE = [39, 45, 51, 87, 93, 99, 129, 165, 201, 207, 213, 219]


def clear():
    sys.stdout.write("\x1b[2J\x1b[H")


def colorize(char: str, age: int) -> str:
    color = PALETTE[min(age, len(PALETTE) - 1)]
    return f"\x1b[38;5;{color}m{char}\x1b[0m"


def make_grid(w, h, density=0.18):
    return [[1 if random.random() < density else 0 for _ in range(w)] for _ in range(h)]


def neighbors(grid, x, y):
    h = len(grid)
    w = len(grid[0])
    total = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            total += grid[(y + dy) % h][(x + dx) % w]
    return total


def step(grid, ages):
    h = len(grid)
    w = len(grid[0])
    new = [[0] * w for _ in range(h)]
    new_ages = [[0] * w for _ in range(h)]

    for y in range(h):
        for x in range(w):
            n = neighbors(grid, x, y)
            alive = grid[y][x] == 1
            if alive and n in (2, 3):
                new[y][x] = 1
                new_ages[y][x] = ages[y][x] + 1
            elif not alive and n == 3:
                new[y][x] = 1
                new_ages[y][x] = 0
            else:
                new[y][x] = 0
                new_ages[y][x] = 0
    return new, new_ages


def render(grid, ages, gen, fps):
    lines = []
    for y, row in enumerate(grid):
        line = []
        for x, cell in enumerate(row):
            if cell:
                line.append(colorize(ALIVE, ages[y][x]))
            else:
                line.append(DEAD)
        lines.append("".join(line))

    banner = (
        f"Neon Life | gen={gen} | fps={fps} | Ctrl+C to quit | r to reseed\n"
    )
    sys.stdout.write("\x1b[H" + banner + "\n".join(lines))
    sys.stdout.flush()


def key_pressed_r():
    # Lightweight non-blocking check for 'r' on Unix terminals.
    try:
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            return ch.lower() == "r"
    except Exception:
        pass
    return False


def main():
    os.system("stty -echo -icanon time 0 min 0")
    try:
        cols, rows = shutil.get_terminal_size((100, 36))
        h = max(10, rows - 3)
        w = max(20, cols)
        fps = 18

        grid = make_grid(w, h)
        ages = [[0] * w for _ in range(h)]

        clear()
        gen = 0
        while True:
            if key_pressed_r():
                grid = make_grid(w, h)
                ages = [[0] * w for _ in range(h)]
                gen = 0
                clear()
            render(grid, ages, gen, fps)
            grid, ages = step(grid, ages)
            gen += 1
            time.sleep(1 / fps)
    except KeyboardInterrupt:
        pass
    finally:
        os.system("stty sane")
        print("\nExited Neon Life.")


if __name__ == "__main__":
    main()
