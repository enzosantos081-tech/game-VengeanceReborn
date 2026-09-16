"""
screens/hud.py
Informações exibidas durante o jogo: vida, moedas, prompts de interação
(Núcleo do Retorno / Loja) e a interface da loja em si (já que é uma
tela simples que sobrepõe o jogo, conforme a seção 14 do documento).
"""

import pygame
from config import settings
from systems import progression
from systems.shop import Shop


class HUD:
    def __init__(self):
        self.font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 20)
        self.big_font = pygame.font.Font(None, 34)

    def draw(self, surface, player):
        self._draw_health_bar(surface, player)
        self._draw_coins(surface, player)
        self._draw_dash(surface, player)

    def _draw_health_bar(self, surface, player):
        """Barra de vida (0-100 de base, pode passar disso com melhorias
        de vida compradas na loja) - substitui os corações antigos."""
        x, y = 20, 20
        w, h = 220, 24
        ratio = 0 if player.stats.max_health <= 0 else max(0, min(1, player.health / player.stats.max_health))

        pygame.draw.rect(surface, settings.COLOR_HP_BG, (x, y, w, h), border_radius=8)

        if ratio > 0:
            # Verde com vida alta, passando por amarelo, até vermelho com vida baixa.
            if ratio > 0.5:
                t = (ratio - 0.5) * 2
                color = (int(230 - t * 140), 200, 70)
            else:
                t = ratio * 2
                color = (230, int(60 + t * 140), 70)
            fill_w = max(1, int(w * ratio))
            pygame.draw.rect(surface, color, (x, y, fill_w, h), border_radius=8)

        pygame.draw.rect(surface, settings.COLOR_UI_BORDER, (x, y, w, h), width=2, border_radius=8)

        label = self.small_font.render(f"{int(player.health)}/{int(player.stats.max_health)}", True, settings.COLOR_TEXT)
        surface.blit(label, label.get_rect(center=(x + w // 2, y + h // 2)))

    def _draw_coins(self, surface, player):
        text = self.font.render(f"Moedas: {player.stats.coins}", True, settings.COLOR_TEXT)
        pygame.draw.rect(surface, settings.COLOR_UI_PANEL, (16, 50, text.get_width() + 20, 30), border_radius=6)
        surface.blit(text, (26, 55))

    def _draw_dash(self, surface, player):
        """Indicador do dash (Q): um "pip" (bolinha) para cada carga
        disponível, mais uma barrinha mostrando o progresso até
        recarregar a próxima carga. Com a melhoria de carga extra
        comprada na loja, aparecem 2 pips em vez de 1."""
        x, y = 20, 92
        pip_size = 16
        pip_gap = 6
        max_charges = max(1, player.max_dash_charges)
        for i in range(max_charges):
            px = x + i * (pip_size + pip_gap)
            filled = i < player.dash_charges
            color = settings.COLOR_DASH_TRAIL if filled else (70, 65, 80)
            pygame.draw.circle(surface, color, (px + pip_size // 2, y + pip_size // 2), pip_size // 2)
            pygame.draw.circle(surface, settings.COLOR_UI_BORDER, (px + pip_size // 2, y + pip_size // 2), pip_size // 2, width=2)

        bar_x = x + max_charges * (pip_size + pip_gap)
        bar_w, bar_h = 70, pip_size
        pygame.draw.rect(surface, settings.COLOR_UI_PANEL, (bar_x, y, bar_w, bar_h), border_radius=6)
        if player.dash_charges < player.max_dash_charges:
            ratio = player.dash_recharge_timer / settings.DASH_COOLDOWN_FRAMES
            fill_w = max(2, int(bar_w * ratio))
            pygame.draw.rect(surface, (150, 220, 255), (bar_x, y, fill_w, bar_h), border_radius=6)
        pygame.draw.rect(surface, settings.COLOR_UI_BORDER, (bar_x, y, bar_w, bar_h), width=2, border_radius=6)
        label = self.small_font.render("Q - Dash", True, settings.COLOR_TEXT)
        surface.blit(label, (bar_x + bar_w + 10, y - 1))

    def draw_prompt(self, surface, text):
        rendered = self.small_font.render(text, True, settings.COLOR_TEXT)
        bg = pygame.Surface((rendered.get_width() + 20, rendered.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(bg, (20, 16, 30, 200), bg.get_rect(), border_radius=6)
        bg.blit(rendered, (10, 6))
        surface.blit(bg, (settings.SCREEN_WIDTH // 2 - bg.get_width() // 2, settings.SCREEN_HEIGHT - 70))

    def draw_shop(self, surface, player, shop: Shop):
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 8, 15, 210))
        surface.blit(overlay, (0, 0))

        # Duas colunas (8 opções agora) pra caber confortavelmente na tela.
        panel_w, panel_h = 820, 320
        px = settings.SCREEN_WIDTH // 2 - panel_w // 2
        py = settings.SCREEN_HEIGHT // 2 - panel_h // 2
        pygame.draw.rect(surface, settings.COLOR_UI_PANEL, (px, py, panel_w, panel_h), border_radius=10)
        pygame.draw.rect(surface, settings.COLOR_UI_BORDER, (px, py, panel_w, panel_h), width=2, border_radius=10)

        title = self.big_font.render("Melhorias", True, settings.COLOR_TEXT)
        surface.blit(title, (px + 24, py + 18))

        coins_text = self.font.render(f"Moedas: {player.stats.coins}", True, settings.COLOR_COIN)
        surface.blit(coins_text, (px + 24, py + 54))

        options = [
            ("health", progression.upgrade_description("health"), player.stats.health_level, settings.MAX_UPGRADE_LEVEL),
            ("damage", progression.upgrade_description("damage"), player.stats.damage_level, settings.MAX_UPGRADE_LEVEL),
            ("jump", progression.upgrade_description("jump"), player.stats.jump_level, settings.MAX_UPGRADE_LEVEL),
            ("attack_speed", progression.upgrade_description("attack_speed"), player.stats.attack_speed_level, settings.MAX_UPGRADE_LEVEL),
            ("double_jump", progression.upgrade_description("double_jump"), player.stats.double_jump_level, 1),
            ("magnet", progression.upgrade_description("magnet"), player.stats.magnet_level, 1),
            ("dash_charge", progression.upgrade_description("dash_charge"), player.stats.dash_charge_level, 1),
            ("heal", progression.upgrade_description("heal"), None, None),
        ]

        col_w = panel_w // 2
        row_h = 42
        start_y = py + 100
        for i, (kind, desc, level, max_level) in enumerate(options):
            col = i // 4
            row = i % 4
            col_x = px + 24 + col * col_w
            y = start_y + row * row_h
            selected = i == shop.selected_index
            can_afford = shop.can_afford(player, kind)
            color = settings.COLOR_TEXT if can_afford else (120, 115, 125)
            prefix = "> " if selected else "  "
            level_text = "" if level is None else f"  (Nv {level}/{max_level})"
            line = f"{prefix}{desc}{level_text}"
            rendered = self.font.render(line, True, color)
            if selected:
                pygame.draw.rect(surface, (60, 50, 80), (col_x - 8, y - 4, col_w - 24, 32), border_radius=4)
            surface.blit(rendered, (col_x, y))

        hint = self.small_font.render(
            "W/S: navegar   ENTER/E: comprar   ESC: sair", True, (190, 185, 195)
        )
        surface.blit(hint, (px + 24, py + panel_h - 34))
