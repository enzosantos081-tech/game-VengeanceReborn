"""
screens/victory.py
Tela apresentada após derrotar Vharok, conforme a seção 18 do
documento: "Vharok foi derrotado" seguido de "Kael finalmente
conseguiu sua vinganca", encerrando o MVP.
"""

import pygame
from config import settings


class VictoryScreen:
    def __init__(self):
        self.title_font = pygame.font.Font(None, 60)
        self.body_font = pygame.font.Font(None, 26)
        self.small_font = pygame.font.Font(None, 22)

    def draw(self, surface, player):
        surface.fill((12, 10, 22))
        cx = settings.SCREEN_WIDTH // 2

        title = self.title_font.render("Vharok foi derrotado.", True, settings.COLOR_CORE)
        surface.blit(title, title.get_rect(center=(cx, 200)))

        subtitle = self.body_font.render(
            "Kael finalmente conseguiu sua vinganca.", True, settings.COLOR_TEXT,
        )
        surface.blit(subtitle, subtitle.get_rect(center=(cx, 250)))

        stats_text = self.small_font.render(
            f"Moedas totais coletadas: {player.stats.total_coins_collected}",
            True, (190, 185, 200),
        )
        surface.blit(stats_text, stats_text.get_rect(center=(cx, 320)))

        hint = self.small_font.render(
            "Pressione ENTER para voltar ao menu", True, (170, 165, 180),
        )
        surface.blit(hint, hint.get_rect(center=(cx, 420)))
