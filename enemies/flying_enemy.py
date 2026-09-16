"""
enemies/flying_enemy.py
Corvo Sombrio: inimigo voador novo. Patrulha um trecho no ar batendo
asas em zigue-zague (senoide vertical + vaivém horizontal), sem sofrer
gravidade e sem colidir com plataformas - simplesmente sobrevoa o
cenário. Obriga o jogador a reagir num timing diferente dos inimigos
terrestres, já que pode atacar em qualquer altura dentro do seu
alcance de patrulha, inclusive no meio de um pulo.
"""

import math
import pygame
from config import settings
from enemies.enemy import Enemy


class FlyingEnemy(Enemy):
    def __init__(self, x, y, patrol_range=None, bob_amplitude=None):
        super().__init__(
            x, y,
            settings.FLYING_ENEMY_WIDTH, settings.FLYING_ENEMY_HEIGHT,
            settings.FLYING_ENEMY_HEALTH, settings.FLYING_ENEMY_DAMAGE,
            settings.COLOR_FLYING_ENEMY,
            coin_value=settings.ENEMY_COIN_DROP_FLYING,
        )
        self.home_x = x
        self.home_y = y
        self.patrol_range = patrol_range if patrol_range is not None else settings.FLYING_ENEMY_PATROL_RANGE
        self.bob_amplitude = bob_amplitude if bob_amplitude is not None else settings.FLYING_ENEMY_BOB_AMPLITUDE
        self.direction = 1
        self.facing_right = True
        self._t = 0.0

    def update(self, level, player):
        super().update(level, player)
        if not self.alive:
            return

        self._t += settings.FLYING_ENEMY_BOB_SPEED
        self.rect.x += round(settings.FLYING_ENEMY_SPEED * self.direction)
        if self.rect.x >= self.home_x + self.patrol_range:
            self.direction = -1
            self.facing_right = False
        elif self.rect.x <= self.home_x - self.patrol_range:
            self.direction = 1
            self.facing_right = True
        self.rect.y = round(self.home_y + math.sin(self._t) * self.bob_amplitude)

        self.check_contact_damage(player)

    def respawn(self):
        super().respawn()
        self.rect.x = self.home_x
        self.rect.y = self.home_y
        self.direction = 1
        self._t = 0.0

    def draw(self, surface, camera_x):
        if not self.alive:
            return
        r = self.rect.move(-camera_x, 0)
        color = (255, 255, 255) if self.hit_flash_timer > 0 else self.color
        pygame.draw.ellipse(surface, color, r)
        # asas simples, batendo conforme o seno do voo
        wing_lift = int(abs(math.sin(self._t * 2.2)) * 9) + 2
        left_wing = [(r.left + 4, r.centery), (r.left - 10, r.centery - wing_lift), (r.left + 6, r.centery + 4)]
        right_wing = [(r.right - 4, r.centery), (r.right + 10, r.centery - wing_lift), (r.right - 6, r.centery + 4)]
        pygame.draw.polygon(surface, color, left_wing)
        pygame.draw.polygon(surface, color, right_wing)
        eye_x = r.right - 8 if self.facing_right else r.left + 4
        pygame.draw.circle(surface, (230, 60, 60), (eye_x, r.top + 7), 2)
