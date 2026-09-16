"""
enemies/wall_sentinel.py
Sentinela de Parede: inimigo novo, exclusivo da Fenda Vertical (a área
de wall jump nas Ruínas). Fica embutida na pedra de uma das paredes do
poço - não sofre gravidade nem se move - e dispara um projétil
horizontal sempre que o jogador cruza sua faixa de altura durante a
escalada. Obriga o jogador a não ficar "grudado" tempo demais na mesma
parede bem na altura de uma sentinela.
"""

import pygame
from config import settings
from enemies.enemy import Enemy


class WallSentinel(Enemy):
    def __init__(self, x, y, facing_dir):
        """facing_dir: 1 -> atira para a direita (sentinela na parede
        esquerda do poço); -1 -> atira para a esquerda (parede direita)."""
        super().__init__(
            x, y,
            settings.WALL_SENTINEL_WIDTH, settings.WALL_SENTINEL_HEIGHT,
            settings.WALL_SENTINEL_HEALTH, settings.WALL_SENTINEL_DAMAGE,
            settings.COLOR_WALL_SENTINEL,
            coin_value=settings.ENEMY_COIN_DROP_SENTINEL,
        )
        self.facing_dir = facing_dir
        self.facing_right = facing_dir > 0
        # Começa com meio cooldown, pra não atirar assim que a tela carrega.
        self.cooldown = settings.WALL_SENTINEL_COOLDOWN // 2
        self.projectiles = []

    def update(self, level, player):
        super().update(level, player)

        if self.alive:
            if self.cooldown > 0:
                self.cooldown -= 1

            in_band = abs(player.rect.centery - self.rect.centery) <= settings.WALL_SENTINEL_VERTICAL_RANGE
            if in_band and self.cooldown <= 0 and player.alive:
                self._fire()
                self.cooldown = settings.WALL_SENTINEL_COOLDOWN

        self._update_projectiles(level, player)

    def _fire(self):
        proj = pygame.Rect(
            self.rect.centerx, self.rect.centery - settings.PROJECTILE_SIZE // 2,
            settings.PROJECTILE_SIZE, settings.PROJECTILE_SIZE,
        )
        self.projectiles.append({"rect": proj, "dir": self.facing_dir})

    def _update_projectiles(self, level, player):
        alive_projectiles = []
        for p in self.projectiles:
            p["rect"].x += settings.PROJECTILE_SPEED * p["dir"]
            if level.rect_hits_solid(p["rect"]):
                continue
            if p["rect"].colliderect(player.rect) and player.alive:
                direction = 1 if p["dir"] > 0 else -1
                player.take_damage(self.damage, knockback_dir=direction)
                continue
            if 0 <= p["rect"].x <= level.width:
                alive_projectiles.append(p)
        self.projectiles = alive_projectiles

    def respawn(self):
        super().respawn()
        self.cooldown = settings.WALL_SENTINEL_COOLDOWN // 2
        self.projectiles = []

    def draw(self, surface, camera_x):
        super().draw(surface, camera_x)
        for p in self.projectiles:
            r = p["rect"].move(-camera_x, 0)
            pygame.draw.ellipse(surface, settings.COLOR_WALL_SENTINEL, r)
