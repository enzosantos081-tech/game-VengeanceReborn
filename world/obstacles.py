"""
world/obstacles.py
Responsável por obstáculos que causam dano ao jogador por contato,
como espinhos. Buracos não precisam de uma classe própria: são apenas
a ausência de plataforma, tratados pela verificação de queda em
player.py (rect.top > level.height).
"""

import pygame
from config import settings


class Spike:
    def __init__(self, x, y, width=32, height=16, facing="up"):
        # Espinhos de chão ("up") ficam grudados no topo do chão.
        # Espinhos de parede ("left"/"right") ficam grudados numa parede
        # vertical, usados na Fenda Vertical (ver world/level.py).
        self.rect = pygame.Rect(x, y, width, height)
        self.facing = facing

    def check_damage(self, player):
        if player.alive and self.rect.colliderect(player.rect):
            direction = 1 if player.rect.centerx > self.rect.centerx else -1
            player.take_damage(settings.SPIKE_DAMAGE, knockback_dir=direction)

    def draw(self, surface, camera_x):
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        if self.facing == "up":
            # Desenha como uma fileira de triângulos apontando para cima
            n = max(1, r.width // 16)
            seg_w = r.width / n
            for i in range(n):
                x0 = r.x + i * seg_w
                points = [(x0, r.bottom), (x0 + seg_w / 2, r.top), (x0 + seg_w, r.bottom)]
                pygame.draw.polygon(surface, settings.COLOR_SPIKE, points)
        else:
            # Fileira de triângulos apontando para o lado (grudados numa parede)
            n = max(1, r.height // 16)
            seg_h = r.height / n
            for i in range(n):
                y0 = r.y + i * seg_h
                if self.facing == "right":
                    # parede fica à esquerda do vão; espinhos apontam p/ direita
                    points = [(r.left, y0), (r.right, y0 + seg_h / 2), (r.left, y0 + seg_h)]
                else:  # "left": parede fica à direita do vão; espinhos apontam p/ esquerda
                    points = [(r.right, y0), (r.left, y0 + seg_h / 2), (r.right, y0 + seg_h)]
                pygame.draw.polygon(surface, settings.COLOR_SPIKE, points)


class ObstacleGroup:
    def __init__(self):
        self.spikes = []

    def add_spike(self, x, y, width=32, height=16):
        s = Spike(x, y, width, height, facing="up")
        self.spikes.append(s)
        return s

    def add_wall_spike(self, x, y, width, height, facing):
        """Espinhos grudados numa parede vertical. facing='right' se a
        parede fica à ESQUERDA do vão (espinhos apontam p/ direita);
        facing='left' se a parede fica à DIREITA do vão."""
        s = Spike(x, y, width, height, facing=facing)
        self.spikes.append(s)
        return s

    def update(self, player):
        for s in self.spikes:
            s.check_damage(player)

    def draw(self, surface, camera_x):
        for s in self.spikes:
            s.draw(surface, camera_x)
