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
from systems.swords import SWORDS, next_upgrade_cost, sword_damage
from screens.menu import (
    get_font, draw_panel, draw_divider, draw_coin_icon, draw_key_chip,
    COL_TEXT, COL_MOON, COL_MOON_DIM, COL_EMBER, COL_GOLD, COL_BORDER,
)

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
        self.shop_title_font = get_font(35, serif=True, bold=True)
        self.shop_tab_font = get_font(18, bold=True)
        self.shop_button_font = get_font(17, bold=True)
        self.shop_damage_font = get_font(22, serif=True, bold=True)

        self._ghost = 1.0  # "rastro" da barra de vida
        self._shop_tab_rects = {}
        self._shop_card_rects = {}
        self._shop_action_rects = {}

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
            ratio = min(1.0, player.dash_recharge_timer_ms / settings.DASH_COOLDOWN_MS)
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
    # Loja — painel por categorias, com navegação por teclado e mouse
    # ------------------------------------------------------------------
    def draw_shop(self, surface, player, shop: Shop):
        w, h = surface.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((4, 5, 13, 218))
        surface.blit(overlay, (0, 0))

        margin = max(14, int(min(w, h) * 0.035))
        panel = pygame.Rect(margin, margin, w - margin * 2, h - margin * 2)
        draw_panel(surface, panel, alpha=247, radius=16)
        self._shop_tab_rects = {}
        self._shop_card_rects = {}
        self._shop_action_rects = {}

        # Cabeçalho
        title = self.shop_title_font.render("ARSENAL DO NÚCLEO", True, COL_TEXT)
        surface.blit(title, (panel.x + 25, panel.y + 13))
        subtitle = self.desc_font.render("Aço, sobrevivência e poder", True, COL_MOON_DIM)
        surface.blit(subtitle, (panel.x + 28, panel.y + 51))

        coins_text = self.font.render(str(player.stats.coins), True, COL_GOLD)
        coin_box = pygame.Rect(panel.right - 150, panel.y + 18, 122, 42)
        draw_panel(surface, coin_box, alpha=220, border=(126, 99, 49), radius=10)
        draw_coin_icon(surface, (coin_box.x + 21, coin_box.centery), 9)
        surface.blit(coins_text, coins_text.get_rect(midleft=(coin_box.x + 39, coin_box.centery)))
        draw_divider(surface, panel.centerx, panel.y + 87, half_width=max(100, panel.width // 2 - 35))

        # Abas clicáveis
        tab_y = panel.y + 98
        tab_gap = 10
        tab_w = min(220, (panel.width - 60 - tab_gap * 2) // 3)
        tabs_total = tab_w * 3 + tab_gap * 2
        tab_x = panel.centerx - tabs_total // 2
        for i, tab in enumerate(Shop.TABS):
            rect = pygame.Rect(tab_x + i * (tab_w + tab_gap), tab_y, tab_w, 32)
            self._shop_tab_rects[tab] = rect
            active = i == shop.tab_index
            bg = (77, 31, 39) if active else (20, 23, 37)
            pygame.draw.rect(surface, bg, rect, border_radius=7)
            border = COL_EMBER if active else (65, 70, 91)
            pygame.draw.rect(surface, border, rect, width=2 if active else 1, border_radius=7)
            label = Shop.TAB_LABELS[tab]
            txt = self.shop_tab_font.render(label, True, COL_TEXT if active else COL_MOON_DIM)
            surface.blit(txt, txt.get_rect(center=rect.center))

        content = pygame.Rect(panel.x + 22, tab_y + 43, panel.width - 44, panel.bottom - (tab_y + 43) - 62)
        items = Shop.ITEMS[shop.active_tab]
        gap = 12
        if shop.active_tab == "swords":
            cols = 2
        elif shop.active_tab == "upgrades":
            cols = 2
        else:
            cols = 1
        rows = (len(items) + cols - 1) // cols
        card_w = (content.width - gap * (cols - 1)) // cols
        card_h = min(150, (content.height - gap * (rows - 1)) // max(1, rows))
        card_h = max(110, card_h)
        grid_height = rows * card_h + (rows - 1) * gap
        start_y = content.y + max(0, (content.height - grid_height) // 2)

        for i, item_id in enumerate(items):
            row, col = divmod(i, cols)
            rect = pygame.Rect(content.x + col * (card_w + gap), start_y + row * (card_h + gap), card_w, card_h)
            self._shop_card_rects[(shop.active_tab, i)] = rect
            selected = i == shop.selected_index
            if shop.active_tab == "swords":
                self._draw_sword_card(surface, rect, item_id, player, selected)
            elif shop.active_tab == "upgrades":
                self._draw_upgrade_card(surface, rect, item_id, player, selected)
            else:
                self._draw_heal_card(surface, rect, player, selected)

        hint_text = "A/D ou ←/→: categoria   W/S ou ↑/↓: item   ENTER: comprar/equipar   F: aprimorar   ESC: sair"
        hint = self.key_font.render(hint_text, True, COL_MOON_DIM)
        if hint.get_width() > panel.width - 36:
            hint = pygame.transform.smoothscale(hint, (panel.width - 36, hint.get_height()))
        surface.blit(hint, hint.get_rect(center=(panel.centerx, panel.bottom - 24)))

        if shop.feedback_active():
            color = (137, 219, 157) if shop.feedback_success else (244, 126, 132)
            msg = self.small_font.render(shop.feedback_text, True, color)
            feedback_rect = pygame.Rect(0, 0, min(panel.width - 48, msg.get_width() + 34), 30)
            feedback_rect.center = (panel.centerx, panel.bottom - 57)
            pygame.draw.rect(surface, (13, 16, 25), feedback_rect, border_radius=7)
            pygame.draw.rect(surface, color, feedback_rect, width=1, border_radius=7)
            surface.blit(msg, msg.get_rect(center=feedback_rect.center))

    def _draw_shop_card_base(self, surface, rect, selected, accent):
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.004)
        bg = (33, 27, 38) if selected else (16, 19, 30)
        pygame.draw.rect(surface, bg, rect, border_radius=10)
        border = tuple(int(c * (0.78 + 0.22 * pulse)) for c in accent) if selected else (58, 62, 78)
        pygame.draw.rect(surface, border, rect, width=2 if selected else 1, border_radius=10)
        inner = rect.inflate(-8, -8)
        pygame.draw.rect(surface, (40, 42, 53), inner, width=1, border_radius=7)

    def _draw_sword_icon(self, surface, center, color, scale=1.0):
        cx, cy = center
        blade = [(cx, cy - int(24 * scale)), (cx + int(5 * scale), cy + int(2 * scale)),
                 (cx, cy + int(9 * scale)), (cx - int(5 * scale), cy + int(2 * scale))]
        pygame.draw.polygon(surface, color, blade)
        pygame.draw.line(surface, (235, 224, 207), (cx, cy - int(18 * scale)), (cx, cy + int(2 * scale)), max(1, int(2 * scale)))
        pygame.draw.line(surface, (118, 77, 54), (cx - int(10 * scale), cy + int(7 * scale)),
                         (cx + int(10 * scale), cy + int(7 * scale)), max(2, int(4 * scale)))
        pygame.draw.line(surface, (170, 130, 88), (cx, cy + int(7 * scale)),
                         (cx, cy + int(19 * scale)), max(2, int(4 * scale)))
        pygame.draw.circle(surface, color, (cx, cy + int(21 * scale)), max(2, int(3 * scale)))

    def _draw_action_button(self, surface, rect, label, enabled=True, accent=COL_EMBER):
        if rect is None:
            return
        bg = (77, 34, 39) if enabled else (28, 30, 39)
        border = accent if enabled else (63, 66, 79)
        pygame.draw.rect(surface, bg, rect, border_radius=6)
        pygame.draw.rect(surface, border, rect, width=1, border_radius=6)
        txt_color = COL_TEXT if enabled else (111, 115, 131)
        txt = self.shop_button_font.render(label, True, txt_color)
        surface.blit(txt, txt.get_rect(center=rect.center))

    def _draw_sword_card(self, surface, rect, sword_id, player, selected):
        data = SWORDS[sword_id]
        stats = player.stats
        owned = stats.owns_sword(sword_id)
        equipped = stats.equipped_sword_id == sword_id
        level = stats.sword_levels.get(sword_id, 0)
        damage = sword_damage(sword_id, level) if owned else data["damage"]
        next_damage = sword_damage(sword_id, level + 1) if owned and next_upgrade_cost(sword_id, level) is not None else None
        self._draw_shop_card_base(surface, rect, selected, data["color"])
        self._draw_sword_icon(surface, (rect.x + 29, rect.y + 38), data["color"], 0.78)

        name = self.name_font.render(data["name"], True, COL_TEXT)
        surface.blit(name, (rect.x + 57, rect.y + 10))
        subtitle = self.desc_font.render(data["subtitle"], True, COL_MOON_DIM)
        surface.blit(subtitle, (rect.x + 57, rect.y + 37))
        damage_text = f"DANO  {damage} → {next_damage}" if next_damage is not None else f"DANO  {damage}"
        dmg_label = self.shop_damage_font.render(damage_text, True, data["color"])
        surface.blit(dmg_label, (rect.x + 57, rect.y + 63))
        if owned:
            level_txt = self.small_font.render(f"NÍVEL {level}/{data['max_level']}", True, COL_MOON_DIM)
            surface.blit(level_txt, (rect.x + 57, rect.y + 88))
        else:
            price = self.small_font.render(f"Preço: {data['price']} moedas", True, COL_GOLD)
            surface.blit(price, (rect.x + 57, rect.y + 89))

        button_y = rect.bottom - 34
        if not owned:
            buy_rect = pygame.Rect(rect.right - 148, button_y, 130, 25)
            self._shop_action_rects[("swords", sword_id, "buy")] = buy_rect
            self._draw_action_button(surface, buy_rect, "COMPRAR", stats.coins >= data["price"], data["color"])
        else:
            equip_rect = pygame.Rect(rect.right - 268, button_y, 116, 25)
            upgrade_rect = pygame.Rect(rect.right - 143, button_y, 125, 25)
            self._shop_action_rects[("swords", sword_id, "equip")] = equip_rect
            if equipped:
                self._draw_action_button(surface, equip_rect, "EQUIPADA", False, data["color"])
            else:
                self._draw_action_button(surface, equip_rect, "EQUIPAR", True, data["color"])
            cost = next_upgrade_cost(sword_id, level)
            if cost is None:
                self._draw_action_button(surface, upgrade_rect, "NÍVEL MÁXIMO", False, data["color"])
            else:
                self._shop_action_rects[("swords", sword_id, "upgrade")] = upgrade_rect
                can_upgrade = stats.coins >= cost
                self._draw_action_button(surface, upgrade_rect, f"APRIM. {cost}", can_upgrade, data["color"])

    def _draw_upgrade_card(self, surface, rect, kind, player, selected):
        stats = player.stats
        accents = {"health": (192, 67, 81), "double_jump": (105, 171, 219), "magnet": (222, 174, 76)}
        accent = accents[kind]
        self._draw_shop_card_base(surface, rect, selected, accent)
        icon_center = (rect.x + 30, rect.y + 34)
        pygame.draw.circle(surface, (22, 24, 34), icon_center, 19)
        pygame.draw.circle(surface, accent, icon_center, 19, width=2)
        symbols = {"health": "+", "double_jump": "↟", "magnet": "✦"}
        symbol = self.shop_title_font.render(symbols[kind], True, accent)
        surface.blit(symbol, symbol.get_rect(center=icon_center))

        if kind == "health":
            title, desc = "Vida máxima", f"Atual: {stats.max_health}  →  Próxima: {stats.max_health + settings.UPGRADE_HEALTH_AMOUNT}"
            cost = settings.UPGRADE_HEALTH_COST
            maxed = stats.health_level >= settings.MAX_UPGRADE_LEVEL
            status = f"NÍVEL {stats.health_level}/{settings.MAX_UPGRADE_LEVEL}"
        elif kind == "double_jump":
            title = "Pulo duplo"
            desc = "Mais um salto no ar" if not stats.double_jump_level else "Habilidade permanente desbloqueada"
            cost = settings.UPGRADE_DOUBLE_JUMP_COST
            maxed = bool(stats.double_jump_level)
            status = "DESBLOQUEADO" if maxed else "BLOQUEADO"
        else:
            title = "Ímã de moedas"
            desc = f"Atrai moedas em até {settings.COIN_MAGNET_RADIUS}px" if stats.magnet_level else f"Desbloqueia atração: {settings.COIN_MAGNET_RADIUS}px"
            cost = settings.UPGRADE_MAGNET_COST
            maxed = bool(stats.magnet_level)
            status = "DESBLOQUEADO" if maxed else "BLOQUEADO"

        surface.blit(self.name_font.render(title, True, COL_TEXT), (rect.x + 57, rect.y + 10))
        desc_surf = self.desc_font.render(desc, True, COL_MOON_DIM)
        surface.blit(desc_surf, (rect.x + 57, rect.y + 39))
        status_surf = self.small_font.render(status, True, accent if maxed else COL_MOON_DIM)
        surface.blit(status_surf, (rect.x + 57, rect.y + 68))
        button_rect = pygame.Rect(rect.right - 151, rect.bottom - 34, 133, 25)
        self._shop_action_rects[("upgrades", kind, "buy")] = button_rect
        if maxed:
            label, enabled = ("MÁXIMO" if kind == "health" else "ADQUIRIDO"), False
        else:
            label = f"COMPRAR {cost}"
            enabled = stats.coins >= cost
        self._draw_action_button(surface, button_rect, label, enabled, accent)

    def _draw_heal_card(self, surface, rect, player, selected):
        stats = player.stats
        accent = (102, 190, 133)
        self._draw_shop_card_base(surface, rect, selected, accent)
        icon_center = (rect.x + 34, rect.y + 37)
        pygame.draw.circle(surface, (22, 30, 28), icon_center, 21)
        pygame.draw.circle(surface, accent, icon_center, 21, width=2)
        pygame.draw.line(surface, accent, (icon_center[0] - 9, icon_center[1]), (icon_center[0] + 9, icon_center[1]), 4)
        pygame.draw.line(surface, accent, (icon_center[0], icon_center[1] - 9), (icon_center[0], icon_center[1] + 9), 4)
        surface.blit(self.name_font.render("Poção de cura", True, COL_TEXT), (rect.x + 68, rect.y + 12))
        surface.blit(self.desc_font.render(f"Recupera até {settings.SHOP_HEAL_AMOUNT} de vida", True, COL_MOON_DIM), (rect.x + 68, rect.y + 42))
        surface.blit(self.small_font.render(f"Vida atual: {int(player.health)}/{stats.max_health}", True, accent), (rect.x + 68, rect.y + 72))
        button_rect = pygame.Rect(rect.right - 174, rect.bottom - 37, 156, 27)
        self._shop_action_rects[("consumables", "heal", "buy")] = button_rect
        enabled = player.health < stats.max_health and stats.coins >= settings.SHOP_HEAL_COST
        label = f"USAR · {settings.SHOP_HEAL_COST}" if player.health < stats.max_health else "VIDA CHEIA"
        self._draw_action_button(surface, button_rect, label, enabled, accent)

    def handle_shop_click(self, pos, player, shop: Shop):
        """Retorna True/False se um botão de ação foi clicado, None nos demais casos."""
        for tab, rect in self._shop_tab_rects.items():
            if rect.collidepoint(pos):
                shop.tab_index = Shop.TABS.index(tab)
                return None

        for (tab, item_id, action), rect in self._shop_action_rects.items():
            if not rect.collidepoint(pos):
                continue
            shop.tab_index = Shop.TABS.index(tab)
            shop.select_index(Shop.ITEMS[tab].index(item_id))
            if action == "upgrade":
                return shop.upgrade_selected(player)
            if tab == "swords" and action == "equip":
                if player.stats.equipped_sword_id == item_id:
                    shop.set_feedback("Esta espada já está equipada.")
                    return False
                success = player.stats.equip_sword(item_id)
                shop.set_feedback("Espada equipada." if success else "Compre esta espada primeiro.", success)
                return success
            return shop.purchase_selected(player)

        for (tab, index), rect in self._shop_card_rects.items():
            if rect.collidepoint(pos):
                shop.tab_index = Shop.TABS.index(tab)
                shop.select_index(index)
                return None
        return None
