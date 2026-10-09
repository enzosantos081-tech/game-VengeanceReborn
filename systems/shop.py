"""
systems/shop.py
Responsável pela compra de melhorias. A loja é uma área específica da
Região 1 (área inicial) - quando Kael entra na zona e pressiona
"interagir", o estado do jogo muda para STATE_SHOP (ver core/states.py)
e a screens/shop-like overlay é desenhada pelo HUD/menu correspondente.
"""

import pygame
from config import settings
from systems import progression


class ShopZone:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def player_in_range(self, player):
        return self.rect.colliderect(player.rect)


class Shop:
    OPTIONS = ["health", "damage", "jump", "attack_speed", "double_jump", "magnet", "dash_charge", "heal"]

    def __init__(self):
        self.selected_index = 0

    def move_selection(self, delta):
        self.selected_index = (self.selected_index + delta) % len(Shop.OPTIONS)

    def selected_option(self):
        return Shop.OPTIONS[self.selected_index]

    def purchase_selected(self, player):
        kind = self.selected_option()
        stats = player.stats
        success = False
        if kind == "health":
            success = stats.upgrade_health()
            if success:
                progression.apply_full_heal_on_upgrade(player)
        elif kind == "damage":
            success = stats.upgrade_damage()
        elif kind == "jump":
            success = stats.upgrade_jump()
        elif kind == "attack_speed":
            success = stats.upgrade_attack_speed()
        elif kind == "double_jump":
            success = stats.upgrade_double_jump()
        elif kind == "magnet":
            success = stats.upgrade_magnet()
        elif kind == "dash_charge":
            success = stats.upgrade_dash_charge()
        elif kind == "heal":
            if player.health < stats.max_health and stats.spend_coins(settings.SHOP_HEAL_COST):
                player.health = min(stats.max_health, player.health + settings.SHOP_HEAL_AMOUNT)
                success = True
        return success

    def can_afford(self, player, kind):
        stats = player.stats
        if kind == "health":
            return stats.can_upgrade_health()
        if kind == "damage":
            return stats.can_upgrade_damage()
        if kind == "jump":
            return stats.can_upgrade_jump()
        if kind == "attack_speed":
            return stats.can_upgrade_attack_speed()
        if kind == "double_jump":
            return stats.can_upgrade_double_jump()
        if kind == "magnet":
            return stats.can_upgrade_magnet()
        if kind == "dash_charge":
            return stats.can_upgrade_dash_charge()
        if kind == "heal":
            return player.health < stats.max_health and stats.coins >= settings.SHOP_HEAL_COST
        return False
