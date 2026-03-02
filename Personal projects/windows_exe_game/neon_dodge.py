#!/usr/bin/env python3
"""
Neon Dodge - simple arcade game (Tkinter, no external deps)
Move with A/D or Left/Right, avoid falling blocks, survive as long as possible.
"""

import random
import time
import tkinter as tk

WIDTH, HEIGHT = 800, 500
PLAYER_W, PLAYER_H = 70, 18
ENEMY_MIN_W, ENEMY_MAX_W = 30, 110

BG = "#0b1020"
PLAYER_COLOR = "#00e5ff"
ENEMY_COLOR = "#ff5c8a"
TEXT = "#e6f1ff"
ACCENT = "#8eff80"


class Game:
    def __init__(self, root):
        self.root = root
        self.root.title("Neon Dodge")
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG, highlightthickness=0)
        self.canvas.pack()

        self.running = False
        self.game_over = False
        self.speed = 5.0
        self.spawn_every = 600  # ms
        self.last_spawn = 0

        self.player_x = WIDTH // 2 - PLAYER_W // 2
        self.player = self.canvas.create_rectangle(
            self.player_x, HEIGHT - 40,
            self.player_x + PLAYER_W, HEIGHT - 40 + PLAYER_H,
            fill=PLAYER_COLOR, outline=""
        )

        self.enemies = []
        self.score = 0
        self.start_time = time.time()

        self.left_pressed = False
        self.right_pressed = False

        self.title_text = self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 80,
            text="NEON DODGE", fill=TEXT,
            font=("Segoe UI", 36, "bold")
        )
        self.help_text = self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 15,
            text="Move: A/D or ←/→   |   Restart: R",
            fill=ACCENT, font=("Segoe UI", 14)
        )
        self.start_text = self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 + 30,
            text="Press SPACE to start",
            fill=TEXT, font=("Segoe UI", 16)
        )

        self.hud = self.canvas.create_text(10, 10, anchor="nw", text="", fill=TEXT, font=("Consolas", 14))

        root.bind("<KeyPress>", self.on_key_down)
        root.bind("<KeyRelease>", self.on_key_up)

        self.tick()

    def reset(self):
        for e in self.enemies:
            self.canvas.delete(e)
        self.enemies.clear()

        self.player_x = WIDTH // 2 - PLAYER_W // 2
        self.canvas.coords(self.player, self.player_x, HEIGHT - 40, self.player_x + PLAYER_W, HEIGHT - 40 + PLAYER_H)

        self.score = 0
        self.speed = 5.0
        self.spawn_every = 600
        self.start_time = time.time()
        self.last_spawn = 0
        self.game_over = False
        self.running = True

        self.canvas.itemconfig(self.title_text, state="hidden")
        self.canvas.itemconfig(self.help_text, state="hidden")
        self.canvas.itemconfig(self.start_text, state="hidden")

    def show_start(self, game_over=False):
        self.running = False
        self.game_over = game_over

        self.canvas.itemconfig(self.title_text, state="normal")
        self.canvas.itemconfig(self.help_text, state="normal")
        self.canvas.itemconfig(self.start_text, state="normal")

        if game_over:
            self.canvas.itemconfig(self.title_text, text="GAME OVER")
            self.canvas.itemconfig(self.start_text, text=f"Score: {self.score}  |  Press R to restart")
        else:
            self.canvas.itemconfig(self.title_text, text="NEON DODGE")
            self.canvas.itemconfig(self.start_text, text="Press SPACE to start")

    def spawn_enemy(self):
        w = random.randint(ENEMY_MIN_W, ENEMY_MAX_W)
        x = random.randint(0, WIDTH - w)
        enemy = self.canvas.create_rectangle(x, -20, x + w, 0, fill=ENEMY_COLOR, outline="")
        self.enemies.append(enemy)

    def on_key_down(self, event):
        k = event.keysym.lower()
        if k in ("a", "left"):
            self.left_pressed = True
        if k in ("d", "right"):
            self.right_pressed = True
        if k == "space" and not self.running and not self.game_over:
            self.reset()
        if k == "r" and self.game_over:
            self.reset()

    def on_key_up(self, event):
        k = event.keysym.lower()
        if k in ("a", "left"):
            self.left_pressed = False
        if k in ("d", "right"):
            self.right_pressed = False

    def intersects(self, a, b):
        ax1, ay1, ax2, ay2 = self.canvas.coords(a)
        bx1, by1, bx2, by2 = self.canvas.coords(b)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def tick(self):
        if self.running:
            # player movement
            dx = 0
            if self.left_pressed:
                dx -= 8
            if self.right_pressed:
                dx += 8
            self.player_x = max(0, min(WIDTH - PLAYER_W, self.player_x + dx))
            self.canvas.coords(self.player, self.player_x, HEIGHT - 40, self.player_x + PLAYER_W, HEIGHT - 40 + PLAYER_H)

            # enemy spawning
            now_ms = int((time.time() - self.start_time) * 1000)
            if now_ms - self.last_spawn >= self.spawn_every:
                self.spawn_enemy()
                self.last_spawn = now_ms

            # difficulty ramp
            t = time.time() - self.start_time
            self.speed = 5 + min(8, t / 10)
            self.spawn_every = max(180, int(600 - t * 12))

            # enemy update + collision
            for e in list(self.enemies):
                self.canvas.move(e, 0, self.speed)
                _, y1, _, y2 = self.canvas.coords(e)
                if y1 > HEIGHT:
                    self.canvas.delete(e)
                    self.enemies.remove(e)
                    self.score += 1
                    continue
                if self.intersects(self.player, e):
                    self.show_start(game_over=True)
                    break

            self.canvas.itemconfig(self.hud, text=f"Score: {self.score}    Speed: {self.speed:.1f}")
        else:
            if not self.game_over:
                self.canvas.itemconfig(self.hud, text="")

        self.root.after(16, self.tick)


def main():
    root = tk.Tk()
    root.resizable(False, False)
    game = Game(root)
    game.show_start(game_over=False)
    root.mainloop()


if __name__ == "__main__":
    main()
