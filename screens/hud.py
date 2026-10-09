"""
screens/hud.py
Informações exibidas durante o jogo: barra de vida, moedas, indicador de
dash, prompts de interação e a interface da loja (uma tela simples que
sobrepõe o jogo).

Visual: barra de vida com "rastro" claro quando você toma dano, moedas
com ícone, dash com pips de carga e a loja em cartões (nome, descrição,
custo e nível).
"""

import math

import pygame
from config import settings
from systems.shop import Shop
from screens.menu import (
    get_font, draw_panel, draw_divider, draw_coin_icon, draw_key_chip,
    COL_TEXT, COL_MOON, COL_MOON_DIM, COL_EMBER, COL_GOLD, COL_BORDER,
)

# Loja: tipo -> (nome, descrição, custo, atributo do nível em PlayerStats, nível máximo)
SHOP_INFO = {
    "health": ("Vida máxima", f"+{settings.UPGRADE_HEALTH_AMOUNT} de vida e cura total",
               settings.UPGRADE_HEALTH_COST, "health_level", settings.MAX_UPGRADE_LEVEL),
    "damage": ("Dano", f"+{settings.UPGRADE_DAMAGE_AMOUNT} de dano por golpe",
               settings.UPGRADE_DAMAGE_COST, "damage_level", settings.MAX_UPGRADE_LEVEL),
    "jump": ("Força do pulo", "Pulos mais altos",
             settings.UPGRADE_JUMP_COST, "jump_level", settings.MAX_UPGRADE_LEVEL),
    "attack_speed": ("Velocidade de ataque", "Golpes mais rápidos",
                     settings.UPGRADE_ATTACK_SPEED_COST, "attack_speed_level", settings.MAX_UPGRADE_LEVEL),
    "double_jump": ("Pulo duplo", "Pule mais uma vez no ar",
                    settings.UPGRADE_DOUBLE_JUMP_COST, "double_jump_level", 1),
    "magnet": ("Ímã de moedas", "Atrai moedas por perto",
               settings.UPGRADE_MAGNET_COST, "magnet_level", 1),
    "dash_charge": ("Carga extra de dash", "Uma carga de dash a mais",
                    settings.UPGRADE_DASH_CHARGE_COST, "dash_charge_level", 1),
    "heal": ("Poção de cura", f"Recupera {settings.SHOP_HEAL_AMOUNT} de vida",
             settings.SHOP_HEAL_COST, None, None),
}


def _hp_color(ratio):
    """Verde com vida alta, passando por amarelo, até vermelho."""
    if ratio > 0.5:
        t = (ratio - 0.5) * 2
        return (int(230 - t * 140), 200, 70)
    t = ratio * 2
    return (230, int(60 + t * 140), 70)


class HUD:
    def __init__(self):
        self.font = get_font(30)
        self.small_font = get_font(21)
        self.big_font = get_font(44, serif=True, bold=True)
        self.name_font = get_font(27)
        self.desc_font = get_font(20)
        self.key_font = get_font(19)

        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        self._ghost = 1.0  # "rastro" da barra de vida
        self._shop_overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        self._shop_overlay.fill((5, 7, 20, 205))

    # ------------------------------------------------------------------
    # HUD principal
    # ------------------------------------------------------------------
    def draw(self, surface, player):
        self._draw_health_bar(surface, player)
        self._draw_coins(surface, player)
        self._draw_dash(surface, player)

    def _draw_health_bar(self, surface, player):
        x, y, w, h = 20, 18, 270, 28
        max_hp = player.stats.max_health
        ratio = 0 if max_hp <= 0 else max(0.0, min(1.0, player.health / max_hp))

        # O rastro claro fica para trás e vai "alcançando" a vida atual
        if ratio >= self._ghost:
            self._ghost = ratio
        else:
            self._ghost = max(ratio, self._ghost - 0.005)

        bar = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, (34, 12, 20), bar, border_radius=9)
        if self._ghost > ratio:
            pygame.draw.rect(surface, (240, 225, 225), (x, y, int(w * self._ghost), h), border_radius=9)
        if ratio > 0:
            fill_w = max(6, int(w * ratio))
            color = _hp_color(ratio)
            pygame.draw.rect(surface, color, (x, y, fill_w, h), border_radius=9)
            if fill_w > 14:
                light = tuple(min(255, c + 55) for c in color)
                pygame.draw.rect(surface, light, (x + 5, y + 4, fill_w - 10, 5), border_radius=3)
        pygame.draw.rect(surface, COL_BORDER, bar, width=2, border_radius=9)

        label = self.small_font.render(f"{int(player.health)} / {int(max_hp)}", True, COL_TEXT)
        shadow = self.small_font.render(f"{int(player.health)} / {int(max_hp)}", True, (0, 0, 0))
        center = bar.center
        surface.blit(shadow, shadow.get_rect(center=(center[0] + 1, center[1] + 1)))
        surface.blit(label, label.get_rect(center=center))

    def _draw_coins(self, surface, player):
        text = self.font.render(str(player.stats.coins), True, (255, 238, 175))
        rect = pygame.Rect(20, 54, 38 + text.get_width() + 16, 30)
        draw_panel(surface, rect, alpha=170, radius=9)
        draw_coin_icon(surface, (rect.x + 20, rect.centery), 8)
        surface.blit(text, text.get_rect(midleft=(rect.x + 36, rect.centery)))

    def _draw_dash(self, surface, player):
        """Tecla Q + um pip por carga de dash + barrinha de recarga."""
        max_charges = max(1, player.max_dash_charges)
        bar_w = 56
        width = 8 + 24 + 10 + max_charges * 20 + 6 + bar_w + 10
        rect = pygame.Rect(20, 92, width, 30)
        draw_panel(surface, rect, alpha=170, radius=9)

        chip = draw_key_chip(surface, rect.x + 8, rect.y + 2, "Q", self.key_font)

        px = chip.right + 14
        for i in range(max_charges):
            center = (px + i * 20, rect.centery)
            if i < player.dash_charges:
                pygame.draw.circle(surface, (190, 225, 255), center, 7)
                pygame.draw.circle(surface, (235, 245, 255), center, 3)
            else:
                pygame.draw.circle(surface, (46, 52, 82), center, 7)
            pygame.draw.circle(surface, COL_BORDER, center, 7, width=2)

        bar = pygame.Rect(px + max_charges * 20 - 4, rect.centery - 4, bar_w, 8)
        pygame.draw.rect(surface, (22, 26, 48), bar, border_radius=4)
        if player.dash_charges < player.max_dash_charges:
            ratio = min(1.0, player.dash_recharge_timer / settings.DASH_COOLDOWN_FRAMES)
            fill = max(3, int(bar.width * ratio))
            pygame.draw.rect(surface, (150, 220, 255), (bar.x, bar.y, fill, bar.height), border_radius=4)
        else:
            pygame.draw.rect(surface, (150, 220, 255), bar, border_radius=4)
        pygame.draw.rect(surface, COL_BORDER, bar, width=1, border_radius=4)

    def draw_prompt(self, surface, text):
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.006)
        rendered = self.small_font.render(text, True, COL_TEXT)
        rect = pygame.Rect(0, 0, rendered.get_width() + 56, rendered.get_height() + 18)
        rect.center = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT - 62)
        border = tuple(int(c * (0.65 + 0.35 * pulse)) for c in COL_EMBER)
        draw_panel(surface, rect, alpha=205, border=border, radius=10)
        surface.blit(rendered, rendered.get_rect(center=(rect.centerx + 8, rect.centery)))
        dx, dy = rect.x + 22, rect.centery
        pygame.draw.polygon(surface, COL_EMBER, [(dx, dy - 6), (dx + 6, dy), (dx, dy + 6), (dx - 6, dy)])

    # ------------------------------------------------------------------
    # Loja
    # ------------------------------------------------------------------
    def draw_shop(self, surface, player, shop: Shop):
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        surface.blit(self._shop_overlay, (0, 0))

        panel = pygame.Rect((w - 880) // 2, (h - 440) // 2, 880, 440)
        draw_panel(surface, panel, alpha=235, radius=14)

        title = self.big_font.render("MELHORIAS", True, COL_TEXT)
        surface.blit(title, (panel.x + 32, panel.y + 20))

        coins = self.font.render(str(player.stats.coins), True, COL_GOLD)
        crect = coins.get_rect(midright=(panel.right - 34, panel.y + 40))
        surface.blit(coins, crect)
        draw_coin_icon(surface, (crect.left - 18, crect.centery), 10)

        draw_divider(surface, panel.centerx, panel.y + 80, half_width=380)

        card_w, card_h, gap = 400, 64, 10
        start_y = panel.y + 100
        for i, kind in enumerate(Shop.OPTIONS):
            col, row = divmod(i, 4)
            card = pygame.Rect(panel.x + 32 + col * (card_w + 16),
                               start_y + row * (card_h + gap), card_w, card_h)
            self._draw_shop_card(surface, card, kind, player, shop, i == shop.selected_index)

        hint = self.small_font.render("W/S navegar   ·   ENTER/E comprar   ·   ESC sair",
                                      True, COL_MOON_DIM)
        surface.blit(hint, hint.get_rect(center=(panel.centerx, panel.bottom - 28)))

    def _draw_shop_card(self, surface, card, kind, player, shop, selected):
        name, desc, cost, level_attr, max_level = SHOP_INFO[kind]
        level = getattr(player.stats, level_attr) if level_attr else None
        maxed = level is not None and level >= max_level
        can_buy = shop.can_afford(player, kind)

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.006)
        bg = (48, 42, 74) if selected else (20, 25, 50)
        pygame.draw.rect(surface, bg, card, border_radius=9)
        if selected:
            border = tuple(int(c * (0.7 + 0.3 * pulse)) for c in COL_EMBER)
            pygame.draw.rect(surface, border, card, width=2, border_radius=9)
        else:
            pygame.draw.rect(surface, (58, 68, 110), card, width=1, border_radius=9)

        usable = can_buy or maxed
        name_col = COL_TEXT if (can_buy or selected) else COL_MOON_DIM
        if not usable and not selected:
            name_col = (115, 122, 150)
        surface.blit(self.name_font.render(name, True, name_col), (card.x + 16, card.y + 10))
        surface.blit(self.desc_font.render(desc, True, (125, 135, 170)), (card.x + 16, card.y + 38))

        # Lado direito: custo (ou "MÁXIMO"/"COMPRADO") e pips de nível
        if maxed:
            label = "COMPRADO" if max_level == 1 else "MÁXIMO"
            txt = self.small_font.render(label, True, COL_MOON)
            surface.blit(txt, txt.get_rect(midright=(card.right - 16, card.y + 20)))
        else:
            cost_col = COL_GOLD if can_buy else (190, 95, 100)
            txt = self.font.render(str(cost), True, cost_col)
            trect = txt.get_rect(midright=(card.right - 16, card.y + 20))
            surface.blit(txt, trect)
            draw_coin_icon(surface, (trect.left - 14, trect.centery), 7)

        if max_level is not None and max_level > 1:
            for n in range(max_level):
                cx = card.right - 16 - 6 - (max_level - 1 - n) * 14
                cy = card.y + 46
                if n < level:
                    pygame.draw.circle(surface, COL_EMBER, (cx, cy), 5)
                else:
                    pygame.draw.circle(surface, (46, 52, 82), (cx, cy), 5)
                pygame.draw.circle(surface, COL_BORDER, (cx, cy), 5, width=1)
