#!/usr/bin/env python3
"""Sunstone Lash — neon grappling-swing arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "SUNSTONE LASH"
HANDLE = "x.com/ElbowOS"

INK = (18, 8, 28)
DUSK = (42, 16, 48)
AMBER = (255, 168, 48)
GOLD = (255, 214, 96)
CREAM = (255, 244, 220)
MAG = (255, 72, 148)
VIOLET = (160, 80, 220)
LIME = (180, 255, 90)
ROSE = (255, 120, 90)


class Node:
    def __init__(self, x: float, y: float):
        self.x, self.y = x, y
        self.phase = random.uniform(0, 6.28)
        self.amp = random.uniform(18, 46)
        self.ox = x
        self.used = False
        self.nid = id(self)


class Thorn:
    def __init__(self, x: float, y: float):
        self.x, self.y = x, y
        self.r = random.randint(16, 28)


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 84)
        self.font_md = pygame.font.Font(None, 52)
        self.font_sm = pygame.font.Font(None, 38)
        self.px, self.py = W * 0.5, 400.0
        self.vx, self.vy = 180.0, -40.0
        self.hooked = False
        self.anchor: Node | None = None
        self.ax = self.ay = 0.0
        self.length = 220.0
        self.theta = 0.6
        self.omega = 1.4
        self.nodes: list[Node] = []
        self.thorns: list[Thorn] = []
        self.sparks: list[list[float]] = []
        self.judges: list[tuple[str, float]] = []
        self.score = 0
        self.combo = 0
        self.best = 0
        self.t = 0.0
        self.cam = 0.0
        self.highest = 400.0
        self.spawn_y = -80.0
        self.shake = 0.0
        self.cool = 0.0
        self.running = True
        self.screen = None
        self.seed_world()
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)

    def seed_world(self):
        y = 200.0
        while y > -2400:
            self.nodes.append(Node(random.uniform(160, W - 160), y))
            if random.random() < 0.45:
                self.thorns.append(Thorn(random.uniform(120, W - 120), y + random.uniform(40, 160)))
            y -= random.uniform(170, 260)
        self.spawn_y = y
        n = min(self.nodes, key=lambda z: abs(z.y - self.py) + abs(z.x - self.px) * 0.3)
        self.attach(n, first=True)

    def attach(self, n: Node, first: bool = False):
        self.hooked = True
        self.anchor = n
        self.ax, self.ay = n.x, n.y
        dx, dy = self.px - n.x, self.py - n.y
        self.length = max(90.0, min(340.0, math.hypot(dx, dy)))
        self.theta = math.atan2(dx, dy)
        tx, ty = math.cos(self.theta), -math.sin(self.theta)
        tang = self.vx * tx + self.vy * ty
        self.omega = tang / max(80.0, self.length)
        self.cool = 0.32
        if not first and not n.used:
            n.used = True
            self.combo += 1
            self.best = max(self.best, self.combo)
            pts = 120 + self.combo * 18
            self.score += pts
            tag = "LASH" if self.combo < 4 else "CHAIN"
            self.cool = 0.28
            self.judges.append((tag, 0.7))
            for _ in range(12):
                a = random.uniform(0, 6.28)
                self.sparks.append(
                    [n.x, n.y, math.cos(a) * 260, math.sin(a) * 260, 0.4, *GOLD]
                )

    def release(self):
        if not self.hooked:
            return
        self.hooked = False
        self.anchor = None
        self.vx = self.omega * self.length * math.cos(self.theta)
        self.vy = -self.omega * self.length * math.sin(self.theta)
        self.vy -= 80

    def fire(self):
        best, best_s = None, 1e9
        for n in self.nodes:
            if self.anchor is not None and n is self.anchor:
                continue
            dx, dy = n.x - self.px, n.y - self.py
            dist = math.hypot(dx, dy)
            if dist < 70 or dist > 720:
                continue
            if n.y > self.py + 20:
                continue
            score = dy * 3.0 + abs(dx) * 0.2 + dist * 0.15
            if score < best_s:
                best, best_s = n, score
        if best is not None:
            if self.hooked:
                self.release()
            self.attach(best)
        else:
            self.judges.append(("MISS", 0.4))

    def grow_world(self):
        while self.spawn_y > self.py - 2200:
            self.nodes.append(Node(random.uniform(150, W - 150), self.spawn_y))
            if random.random() < 0.5:
                self.thorns.append(
                    Thorn(random.uniform(110, W - 110), self.spawn_y + random.uniform(30, 140))
                )
            self.spawn_y -= random.uniform(160, 250)
        self.nodes = [n for n in self.nodes if n.y < self.py + 900]
        self.thorns = [th for th in self.thorns if th.y < self.py + 900]

    def autoplay(self):
        if self.cool > 0:
            return
        if self.hooked:
            if abs(self.theta) > 0.62:
                self.fire()
        else:
            self.fire()

    def update(self, dt: float):
        self.t += dt
        self.cool = max(0.0, self.cool - dt)
        if self.record:
            self.autoplay()
        if self.hooked:
            self.omega += -math.sin(self.theta) * 980.0 / max(90.0, self.length) * dt
            self.omega *= 0.997
            self.theta += self.omega * dt
            self.px = self.ax + self.length * math.sin(self.theta)
            self.py = self.ay + self.length * math.cos(self.theta)
            if self.px < 70:
                self.px, self.theta, self.omega = 70, self.theta * 0.4, abs(self.omega) * 0.6
            if self.px > W - 70:
                self.px, self.theta, self.omega = W - 70, self.theta * 0.4, -abs(self.omega) * 0.6
        else:
            self.vy += 980 * dt
            self.vx *= 0.995
            self.px += self.vx * dt
            self.py += self.vy * dt
            if self.px < 60:
                self.px, self.vx = 60, abs(self.vx) * 0.7
            if self.px > W - 60:
                self.px, self.vx = W - 60, -abs(self.vx) * 0.7
        for n in self.nodes:
            n.x = n.ox + math.sin(self.t * 1.2 + n.phase) * n.amp
            if self.anchor is n:
                self.ax, self.ay = n.x, n.y
        self.grow_world()
        if self.py < self.highest:
            self.highest = self.py
            self.score += 1
        for th in self.thorns:
            if math.hypot(th.x - self.px, th.y - self.py) < th.r + 18:
                self.combo = 0
                self.shake = 0.28
                self.vy = min(self.vy, -220)
                self.judges.append(("BURN", 0.5))
                if self.hooked:
                    self.release()
        target = self.py - 980
        self.cam += (target - self.cam) * min(1.0, dt * 4)
        nxt = []
        for sp in self.sparks:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[4] -= dt
            if sp[4] > 0:
                nxt.append(sp)
        self.sparks = nxt
        self.judges = [(s, life - dt) for s, life in self.judges if life - dt > 0]
        self.shake = max(0.0, self.shake - dt)

    def sy(self, y: float) -> int:
        return int(y - self.cam)

    def draw(self, s: pygame.Surface):
        ox = int(math.sin(self.t * 38) * 12 * self.shake)
        s.fill(INK)
        pygame.draw.rect(s, DUSK, (0, 0, 70, H))
        pygame.draw.rect(s, DUSK, (W - 70, 0, 70, H))
        pygame.draw.rect(s, AMBER, (64, 0, 8, H))
        pygame.draw.rect(s, GOLD, (W - 72, 0, 8, H))
        rng = random.Random(7)
        for i in range(40):
            mx = rng.randint(90, W - 90)
            my = (rng.randint(0, H) + int(self.t * (20 + i % 18) - self.cam * 0.15)) % H
            pygame.draw.circle(s, (70, 30, 80), (mx, my), 2 + i % 3)
        for i in range(16):
            y = (i * 140 + int(-self.cam * 0.4)) % (H + 140) - 70
            pygame.draw.line(s, (50, 18, 58), (78, y), (W - 78, y), 2)
        for n in self.nodes:
            yy = self.sy(n.y)
            if -40 < yy < H + 40:
                pygame.draw.circle(s, (80, 40, 20), (int(n.x), yy), 22)
                pygame.draw.circle(s, GOLD if n.used else AMBER, (int(n.x), yy), 16)
                pygame.draw.circle(s, CREAM, (int(n.x), yy), 6)
        for th in self.thorns:
            yy = self.sy(th.y)
            if -40 < yy < H + 40:
                pts = []
                for k in range(6):
                    a = k / 6 * 6.283 + self.t * 1.4
                    r = th.r if k % 2 == 0 else th.r * 0.45
                    pts.append((int(th.x + math.cos(a) * r), int(yy + math.sin(a) * r)))
                pygame.draw.polygon(s, MAG, pts)
        py = self.sy(self.py)
        if self.hooked:
            pygame.draw.line(s, GOLD, (int(self.ax) + ox, self.sy(self.ay)), (int(self.px) + ox, py), 6)
            pygame.draw.line(s, CREAM, (int(self.ax) + ox, self.sy(self.ay)), (int(self.px) + ox, py), 2)
        pygame.draw.circle(s, ROSE, (int(self.px) + ox, py), 22)
        pygame.draw.circle(s, AMBER, (int(self.px) + ox, py), 14)
        pygame.draw.circle(s, CREAM, (int(self.px) + ox - 4, py - 4), 5)
        for sp in self.sparks:
            pygame.draw.circle(s, (int(sp[5]), int(sp[6]), int(sp[7])), (int(sp[0]) + ox, self.sy(sp[1])), 6)
        title = self.font_lg.render(TITLE, True, AMBER)
        s.blit(title, title.get_rect(center=(W // 2 + ox, 70)))
        handle = self.font_sm.render(HANDLE, True, GOLD)
        s.blit(handle, handle.get_rect(center=(W // 2, 124)))
        sc = self.font_md.render(f"SCORE  {self.score}", True, CREAM)
        s.blit(sc, (88, 164))
        cb = self.font_md.render(f"CHAIN  {self.combo}   BEST {self.best}", True, VIOLET)
        s.blit(cb, (88, 210))
        climb = int(max(0, 400 - self.highest) / 10)
        ht = self.font_sm.render(f"ASCENT  {climb}m", True, LIME)
        s.blit(ht, (88, 258))
        for tag, life in self.judges:
            col = GOLD if tag in ("LASH", "CHAIN") else MAG
            img = self.font_md.render(tag, True, col)
            s.blit(img, img.get_rect(center=(int(self.px), py - 70 - int((0.7 - life) * 40))))
        hint = self.font_sm.render("SPACE / W  —  lash the next sunstone", True, (210, 160, 120))
        s.blit(hint, hint.get_rect(center=(W // 2, H - 46)))

    def handle(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                self.fire()
            elif ev.key == pygame.K_r:
                rec = self.record
                self.__init__(rec)

    def play(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str):
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main():
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    if record:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record)
    if record:
        g.record_mp4("/home/workdir/artifacts/sunstone_lash_ElbowOS.mp4")
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
