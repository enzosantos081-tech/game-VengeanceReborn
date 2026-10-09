"""
enemies/enemy.py
Classe base para inimigos. Define a interface comum (posição, vida,
dano, colisão com o jogador) que os tipos específicos (basic_enemy,
enemy à distância, boss) reaproveitam por herança.
"""

import itertools
import pygame
from config import settings

_id_counter = itertools.count()


class Enemy:
    def __init__(self, x, y, width, height, health, damage, color, coin_value=0):
        self.id = next(_id_counter)
        self.rect = pygame.Rect(x, y, width, height)
        self.spawn_x = x
        self.spawn_y = y
        self.health = health
        self.max_health = health
        self.damage = damage
        self.color = color
        self.alive = True
        self.facing_right = False
        self.vel_x = 0
        self.vel_y = 0
        self.hit_flash_timer = 0

        # Moedas dadas ao jogador quando este inimigo é derrotado (ver
        # systems/combat.py -> resolve_player_attack).
        self.coin_value = coin_value

        # Respawn automático: inimigos comuns voltam ao ponto de spawn
        # depois de settings.ENEMY_RESPAWN_FRAMES (padrão: 1 minuto).
        # O Boss desativa isso (ver enemies/boss.py).
        self.can_respawn = True
        self.respawn_timer = 0

    def take_damage(self, amount):
        if not self.alive:
            return
        self.health -= amount
        self.hit_flash_timer = 8
        if self.health <= 0:
            self.health = 0
            self.alive = False
            if self.can_respawn:
                self.respawn_timer = settings.ENEMY_RESPAWN_FRAMES

    def respawn(self):
        """Reaparece no ponto de spawn original, com a vida cheia. Chamado
        automaticamente por update() quando respawn_timer chega a zero.
        Subclasses com estado próprio (direção de patrulha, projéteis
        etc.) devem sobrescrever e chamar super().respawn()."""
        self.rect.x = self.spawn_x
        self.rect.y = self.spawn_y
        self.health = self.max_health
        self.alive = True
        self.hit_flash_timer = 0
        self.vel_x = 0
        self.vel_y = 0

    def update(self, level, player):
        """Deve ser sobrescrito pelas subclasses (que chamam super().update() primeiro)."""
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
        if not self.alive and self.can_respawn:
            if self.respawn_timer > 0:
                self.respawn_timer -= 1
            else:
                self.respawn()

    def check_contact_damage(self, player):
        """Dano por contato direto (comportamento padrão de inimigo comum)."""
        if self.alive and player.alive and self.rect.colliderect(player.rect):
            direction = 1 if player.rect.centerx > self.rect.centerx else -1
            player.take_damage(self.damage, knockback_dir=direction)

    def draw(self, surface, camera_x):
        if not self.alive:
            return
        r = self.rect.move(-camera_x, 0)
        color = (255, 255, 255) if self.hit_flash_timer > 0 else self.color
        pygame.draw.rect(surface, color, r, border_radius=4)

    def draw_health_bar(self, surface, camera_x):
        if not self.alive or self.health >= self.max_health:
            return
        r = self.rect.move(-camera_x, 0)
        bar_w = r.width
        bar_h = 4
        bx = r.left
        by = r.top - 8
        pygame.draw.rect(surface, (40, 10, 10), (bx, by, bar_w, bar_h))
        ratio = max(0, self.health / self.max_health)
        pygame.draw.rect(surface, (200, 40, 40), (bx, by, int(bar_w * ratio), bar_h))
