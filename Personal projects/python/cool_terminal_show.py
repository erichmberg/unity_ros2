#!/usr/bin/env python3
import math
import random
import shutil
import sys
import time
from datetime import datetime

# Tiny "cool" terminal animation: starfield + live clock + CPU-ish pulse bars (no deps)


def clear():
    sys.stdout.write("\x1b[2J\x1b[H")


def hide_cursor():
    sys.stdout.write("\x1b[?25l")


def show_cursor():
    sys.stdout.write("\x1b[?25h")


def color(text, code):
    return f"\x1b[{code}m{text}\x1b[0m"


def main(seconds=12):
    w, h = shutil.get_terminal_size((100, 30))
    stars = [[random.randint(0, w - 1), random.randint(1, h - 4), random.choice([".", "+", "*"])] for _ in range(max(30, w // 3))]
    start = time.time()

    hide_cursor()
    try:
        while time.time() - start < seconds:
            t = time.time() - start
            canvas = [[" " for _ in range(w)] for _ in range(h)]

            # Move stars
            for s in stars:
                s[0] -= 1
                if s[0] < 0:
                    s[0] = w - 1
                    s[1] = random.randint(1, h - 4)
                    s[2] = random.choice([".", "+", "*"])
                x, y, ch = s
                if 0 <= y < h and 0 <= x < w:
                    canvas[y][x] = ch

            # Pulsing bars at bottom
            bars = 3
            for i in range(bars):
                val = (math.sin(t * 2 + i * 1.5) + 1) / 2
                bar_len = int(val * (w // 4))
                y = h - (bars - i)
                label = f"core{i+1}: "
                for j, c in enumerate(label):
                    if j < w:
                        canvas[y][j] = c
                for j in range(bar_len):
                    x = len(label) + j
                    if x < w:
                        canvas[y][x] = "█"

            # Center clock
            now = datetime.now().strftime("%H:%M:%S")
            title = "JARVIS TERMINAL SHOW"
            cx = max(0, (w - len(title)) // 2)
            cy = max(0, h // 2 - 1)
            for i, c in enumerate(title):
                if cx + i < w:
                    canvas[cy][cx + i] = c
            cx2 = max(0, (w - len(now)) // 2)
            for i, c in enumerate(now):
                if cx2 + i < w:
                    canvas[cy + 1][cx2 + i] = c

            clear()
            for row in canvas:
                line = "".join(row)
                # subtle coloring
                line = line.replace("*", color("*", "96"))
                line = line.replace("+", color("+", "94"))
                line = line.replace("█", color("█", "92"))
                sys.stdout.write(line + "\n")
            sys.stdout.flush()
            time.sleep(0.07)

    finally:
        show_cursor()
        print("\nDone. Run again with: python3 'Personal projects/python/cool_terminal_show.py'")


if __name__ == "__main__":
    main()
