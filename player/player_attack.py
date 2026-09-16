"""
player/player_attack.py
Responsável pelo ataque de Kael: criação da área de colisão (hitbox),
duração do golpe e cooldown entre ataques. Propositalmente simples,
sem combos ou múltiplas armas (fora do escopo mínimo).
"""

import pygame
from config import settings


class PlayerAttack:
    def __init__(self):
        self.active = False
        self.timer = 0
        self.cooldown_timer = 0
        self.hit_enemies_this_swing = set()

    def try_start(self, cooldown=None):
        """cooldown: se informado (vindo de PlayerStats.attack_cooldown,
        que diminui com a melhoria de velocidade de ataque), substitui o
        valor padrão de config/settings.py."""
        if self.cooldown_timer <= 0 and not self.active:
            self.active = True
            self.timer = settings.PLAYER_ATTACK_DURATION
            self.cooldown_timer = cooldown if cooldown is not None else settings.PLAYER_ATTACK_COOLDOWN
            self.hit_enemies_this_swing = set()
            return True
        return False

    def update(self):
        if self.active:
            self.timer -= 1
            if self.timer <= 0:
                self.active = False
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1

    def get_hitbox(self, player_rect, facing_right):
        """Retorna o retângulo de colisão do ataque, ou None se não estiver ativo."""
        if not self.active:
            return None
        width = settings.PLAYER_ATTACK_RANGE
        height = settings.PLAYER_ATTACK_HEIGHT
        y = player_rect.centery - height // 2
        if facing_right:
            x = player_rect.right
        else:
            x = player_rect.left - width
        return pygame.Rect(x, y, width, height)

    def has_hit(self, enemy_id):
        return enemy_id in self.hit_enemies_this_swing

    def register_hit(self, enemy_id):
        self.hit_enemies_this_swing.add(enemy_id)
