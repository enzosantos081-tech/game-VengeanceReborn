"""
systems/particles.py
Sistema de partículas simples para dar feedback visual a eventos do
jogo (acerto em inimigo, moeda coletada, poeira ao pousar, morte do
jogador). Não depende de nenhum asset de imagem - cada partícula é
apenas um pequeno círculo/quadrado colorido que se move e desaparece
com o tempo (fade out).
"""

import random
import pygame


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color", "gravity")

    def __init__(self, x, y, vx, vy, life, size, color, gravity=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.gravity = gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1
        return self.life > 0

    def draw(self, surface, camera_x):
        ratio = max(0.0, self.life / self.max_life)
        size = max(1, int(self.size * ratio))
        pos = (int(self.x - camera_x), int(self.y))
        if -20 < pos[0] < 2000:
            pygame.draw.circle(surface, self.color, pos, size)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def update(self):
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, surface, camera_x):
        for p in self.particles:
            p.draw(surface, camera_x)

    # ---------- Emissores de eventos específicos ----------
    def emit_hit(self, x, y, color=(255, 255, 255), count=8):
        for _ in range(count):
            angle = random.uniform(0, 6.283)
            speed = random.uniform(1.5, 4.0)
            vx = speed * random.uniform(-1, 1)
            vy = speed * random.uniform(-1, 1)
            self.particles.append(Particle(x, y, vx, vy, life=random.randint(14, 26), size=4, color=color, gravity=0.15))

    def emit_coin(self, x, y):
        for _ in range(6):
            vx = random.uniform(-1.2, 1.2)
            vy = random.uniform(-3.5, -1.5)
            self.particles.append(
                Particle(x, y, vx, vy, life=random.randint(18, 30), size=3, color=(255, 215, 90), gravity=0.18)
            )

    def emit_dust(self, x, y, count=5):
        for _ in range(count):
            vx = random.uniform(-1.5, 1.5)
            vy = random.uniform(-1.0, -0.2)
            self.particles.append(
                Particle(x, y, vx, vy, life=random.randint(10, 18), size=3, color=(150, 140, 160), gravity=0.05)
            )

    def emit_death(self, x, y):
        for _ in range(24):
            vx = random.uniform(-3, 3)
            vy = random.uniform(-4, 1)
            self.particles.append(
                Particle(x, y, vx, vy, life=random.randint(24, 40), size=5, color=(230, 200, 90), gravity=0.2)
            )

    def emit_checkpoint(self, x, y):
        for _ in range(14):
            angle = random.uniform(0, 6.283)
            speed = random.uniform(0.8, 2.2)
            vx = speed * random.uniform(-1, 1)
            vy = -abs(speed) - 0.5
            self.particles.append(
                Particle(x, y, vx, vy, life=random.randint(20, 34), size=4, color=(90, 230, 160), gravity=0.05)
            )

    def emit_dash_trail(self, x, y):
        """Um leve rastro atrás do Kael enquanto ele executa o dash (Q)."""
        vx = random.uniform(-0.4, 0.4)
        vy = random.uniform(-0.4, 0.4)
        self.particles.append(
            Particle(x, y, vx, vy, life=random.randint(8, 14), size=5, color=(210, 225, 255), gravity=0.0)
        )
