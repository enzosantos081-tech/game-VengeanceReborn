"""Lógica da loja: espadas equipáveis, melhorias permanentes e poção."""

import pygame
from config import settings
from systems import progression
from systems.swords import SWORDS, next_upgrade_cost, sword_damage


class ShopZone:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def player_in_range(self, player):
        return self.rect.colliderect(player.rect)


class Shop:
    TABS = ("swords", "upgrades", "consumables")
    TAB_LABELS = {"swords": "ESPADAS", "upgrades": "MELHORIAS", "consumables": "CONSUMÍVEIS"}
    ITEMS = {
        "swords": tuple(SWORDS.keys()),
        "upgrades": ("health", "double_jump", "magnet"),
        "consumables": ("heal",),
    }

    def __init__(self):
        self.tab_index = 0
        self.selected_by_tab = {tab: 0 for tab in self.TABS}
        self.feedback_text = ""
        self.feedback_success = True
        self.feedback_until = 0

    @property
    def active_tab(self):
        return self.TABS[self.tab_index]

    @property
    def selected_index(self):
        return self.selected_by_tab[self.active_tab]

    def selected_option(self):
        items = self.ITEMS[self.active_tab]
        return items[self.selected_index]

    def move_selection(self, delta):
        items = self.ITEMS[self.active_tab]
        self.selected_by_tab[self.active_tab] = (self.selected_index + delta) % len(items)

    def select_index(self, index):
        items = self.ITEMS[self.active_tab]
        if 0 <= index < len(items):
            self.selected_by_tab[self.active_tab] = index

    def switch_tab(self, delta):
        self.tab_index = (self.tab_index + delta) % len(self.TABS)
        self.selected_by_tab[self.active_tab] = min(
            self.selected_by_tab[self.active_tab], len(self.ITEMS[self.active_tab]) - 1
        )

    def set_feedback(self, text, success=False):
        self.feedback_text = text
        self.feedback_success = success
        self.feedback_until = pygame.time.get_ticks() + 2200

    def feedback_active(self):
        return bool(self.feedback_text) and pygame.time.get_ticks() < self.feedback_until

    def purchase_selected(self, player):
        """Compra uma espada, equipa uma já comprada ou compra melhoria/poção."""
        kind = self.selected_option()
        stats = player.stats

        if self.active_tab == "swords":
            sword = SWORDS[kind]
            if not stats.owns_sword(kind):
                if stats.coins < sword["price"]:
                    self.set_feedback("Moedas insuficientes para esta espada.")
                    return False
                if stats.buy_sword(kind):
                    self.set_feedback(f'{sword["name"]} adquirida e equipada!', True)
                    return True
            elif stats.equipped_sword_id != kind:
                stats.equip_sword(kind)
                self.set_feedback(f'{sword["name"]} equipada.', True)
                return True
            else:
                self.set_feedback("Esta espada já está equipada. Use APRIMORAR para evoluí-la.")
            return False

        if kind == "health":
            if stats.health_level >= settings.MAX_UPGRADE_LEVEL:
                self.set_feedback("Vida máxima já está no nível máximo.")
                return False
            if stats.coins < settings.UPGRADE_HEALTH_COST:
                self.set_feedback("Moedas insuficientes para melhorar a vida.")
                return False
            success = stats.upgrade_health()
            if success:
                progression.apply_full_heal_on_upgrade(player)
                self.set_feedback("Vida máxima aprimorada e vida restaurada!", True)
                return True

        elif kind == "double_jump":
            if stats.double_jump_level:
                self.set_feedback("Pulo duplo já desbloqueado.")
                return False
            if stats.coins < settings.UPGRADE_DOUBLE_JUMP_COST:
                self.set_feedback("Moedas insuficientes para desbloquear o pulo duplo.")
                return False
            if stats.upgrade_double_jump():
                self.set_feedback("Pulo duplo desbloqueado!", True)
                return True

        elif kind == "magnet":
            if stats.magnet_level:
                self.set_feedback("Ímã de moedas já desbloqueado.")
                return False
            if stats.coins < settings.UPGRADE_MAGNET_COST:
                self.set_feedback("Moedas insuficientes para comprar o ímã.")
                return False
            if stats.upgrade_magnet():
                self.set_feedback("Ímã de moedas desbloqueado!", True)
                return True

        elif kind == "heal":
            if player.health >= stats.max_health:
                self.set_feedback("Você já está com a vida cheia.")
                return False
            if stats.coins < settings.SHOP_HEAL_COST:
                self.set_feedback("Moedas insuficientes para a poção.")
                return False
            if stats.spend_coins(settings.SHOP_HEAL_COST):
                player.health = min(stats.max_health, player.health + settings.SHOP_HEAL_AMOUNT)
                self.set_feedback(f"Poção utilizada: +{settings.SHOP_HEAL_AMOUNT} de vida.", True)
                return True

        self.set_feedback("Não foi possível concluir a compra.")
        return False

    def upgrade_selected(self, player):
        if self.active_tab != "swords":
            self.set_feedback("Os aprimoramentos de dano ficam na categoria ESPADAS.")
            return False
        sword_id = self.selected_option()
        data = SWORDS[sword_id]
        stats = player.stats
        if not stats.owns_sword(sword_id):
            self.set_feedback("Compre esta espada antes de aprimorá-la.")
            return False
        level = stats.sword_levels.get(sword_id, 0)
        cost = next_upgrade_cost(sword_id, level)
        if cost is None:
            self.set_feedback("Esta espada já atingiu o nível máximo.")
            return False
        if stats.coins < cost:
            self.set_feedback("Moedas insuficientes para o aprimoramento.")
            return False
        old_damage = sword_damage(sword_id, level)
        if stats.upgrade_sword(sword_id):
            new_damage = sword_damage(sword_id, stats.sword_levels[sword_id])
            self.set_feedback(f"Dano de {data['name']}: {old_damage} → {new_damage}.", True)
            return True
        self.set_feedback("Não foi possível aprimorar esta espada.")
        return False

    def can_afford(self, player, kind=None):
        """Compatibilidade e estado de disponibilidade usado pela interface."""
        kind = kind or self.selected_option()
        stats = player.stats
        if kind in SWORDS:
            if not stats.owns_sword(kind):
                return stats.coins >= SWORDS[kind]["price"]
            if stats.equipped_sword_id != kind:
                return True
            cost = next_upgrade_cost(kind, stats.sword_levels.get(kind, 0))
            return cost is not None and stats.coins >= cost
        if kind == "health":
            return stats.can_upgrade_health()
        if kind == "double_jump":
            return stats.can_upgrade_double_jump()
        if kind == "magnet":
            return stats.can_upgrade_magnet()
        if kind == "heal":
            return player.health < stats.max_health and stats.coins >= settings.SHOP_HEAL_COST
        return False
