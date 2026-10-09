"""
enemies/basic_enemy.py
Implementação do inimigo comum (P1 - obrigatório): patrulha uma região
determinada, anda de um lado para o outro, causa dano por contato e
pode ser derrotado pelo ataque de Kael.

Também implementa o inimigo opcional (P2) à distância, que persegue
o jogador dentro de um alcance e atira projéteis - conforme a seção 8
do documento de escopo ("inimigo que ataca à distância").
"""

import pygame
from config import settings
from enemies.enemy import Enemy


class BasicEnemy(Enemy):
    """Patrulha da esquerda para a direita dentro de PATROL_RANGE a partir
    do ponto de spawn, invertendo direção ao atingir os limites ou uma borda."""

    def __init__(self, x, y):
        super().__init__(
            x, y,
            settings.BASIC_ENEMY_WIDTH, settings.BASIC_ENEMY_HEIGHT,
            settings.BASIC_ENEMY_HEALTH, settings.BASIC_ENEMY_DAMAGE,
            settings.COLOR_ENEMY,
            coin_value=settings.ENEMY_COIN_DROP_BASIC,
        )
        self.left_bound = x - settings.BASIC_ENEMY_PATROL_RANGE
        self.right_bound = x + settings.BASIC_ENEMY_PATROL_RANGE
        self.direction = 1

    def respawn(self):
        super().respawn()
        self.direction = 1

    def update(self, level, player):
        super().update(level, player)
        if not self.alive:
            return

        self.vel_x = settings.BASIC_ENEMY_SPEED * self.direction
        self.vel_y += settings.GRAVITY
        if self.vel_y > settings.MAX_FALL_SPEED:
            self.vel_y = settings.MAX_FALL_SPEED

        level.move_and_collide_enemy(self, self.vel_x, self.vel_y)

        if self.rect.x <= self.left_bound:
            self.direction = 1
        elif self.rect.x >= self.right_bound:
            self.direction = -1

        # Evita andar para fora de uma plataforma (não cair em buracos)
        if not level.has_ground_ahead(self.rect, self.direction):
            self.direction *= -1

        self.facing_right = self.direction > 0
        self.check_contact_damage(player)


class RangedEnemy(Enemy):
    """Inimigo opcional (P2): fica parado, detecta o jogador dentro de um
    alcance e atira projéteis periodicamente. Não persegue corpo a corpo."""

    def __init__(self, x, y):
        super().__init__(
            x, y,
            settings.RANGED_ENEMY_WIDTH, settings.RANGED_ENEMY_HEIGHT,
            settings.RANGED_ENEMY_HEALTH, settings.RANGED_ENEMY_DAMAGE,
            settings.COLOR_ENEMY_RANGED,
            coin_value=settings.ENEMY_COIN_DROP_RANGED,
        )
        self.cooldown = 0
        self.projectiles = []

    def respawn(self):
        super().respawn()
        self.cooldown = 0
        self.projectiles = []

    def update(self, level, player):
        super().update(level, player)
        if not self.alive:
            return

        self.vel_y += settings.GRAVITY
        if self.vel_y > settings.MAX_FALL_SPEED:
            self.vel_y = settings.MAX_FALL_SPEED
        level.move_and_collide_enemy(self, 0, self.vel_y)

        distance = player.rect.centerx - self.rect.centerx
        self.facing_right = distance > 0

        if self.cooldown > 0:
            self.cooldown -= 1

        if abs(distance) <= settings.RANGED_ENEMY_RANGE and self.cooldown <= 0 and player.alive:
            self._fire(distance)
            self.cooldown = settings.RANGED_ENEMY_COOLDOWN

        self._update_projectiles(level, player)

    def _fire(self, distance):
        direction = 1 if distance > 0 else -1
        proj = pygame.Rect(
            self.rect.centerx, self.rect.centery,
            settings.PROJECTILE_SIZE, settings.PROJECTILE_SIZE,
        )
        self.projectiles.append({"rect": proj, "dir": direction})

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

    def draw(self, surface, camera_x):
        super().draw(surface, camera_x)
        for p in self.projectiles:
            r = p["rect"].move(-camera_x, 0)
            pygame.draw.ellipse(surface, settings.COLOR_ENEMY_RANGED, r)
