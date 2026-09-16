"""
screens/game_over.py
Tela apresentada após a morte de Kael. Conforme a seção 10 do
documento, a morte NAO e um Game Over definitivo: e apenas uma nova
tentativa. Esta tela aparece brevemente, mostrando o que foi coletado
na tentativa, e então o jogador retorna ao Núcleo do Retorno.
"""

import pygame
from config import settings


class GameOverScreen:
    def __init__(self):
        self.title_font = pygame.font.Font(None, 64)
        self.body_font = pygame.font.Font(None, 26)
        self.timer = 0
        self.MIN_DISPLAY_FRAMES = 90

    def reset(self):
        self.timer = 0

    def update(self):
        self.timer += 1

    def ready_to_continue(self):
        return self.timer >= self.MIN_DISPLAY_FRAMES

    def draw(self, surface, player):
        surface.fill((15, 8, 12))
        cx = settings.SCREEN_WIDTH // 2

        title = self.title_font.render("Kael caiu...", True, (220, 60, 70))
        surface.blit(title, title.get_rect(center=(cx, 200)))

        msg = self.body_font.render(
            "O Nucleo do Retorno reconstroi seu corpo no ultimo ponto conhecido.",
            True, settings.COLOR_TEXT,
        )
        surface.blit(msg, msg.get_rect(center=(cx, 260)))

        coins_msg = self.body_font.render(
            f"Moedas mantidas: {player.stats.coins}", True, settings.COLOR_COIN,
        )
        surface.blit(coins_msg, coins_msg.get_rect(center=(cx, 300)))

        if self.ready_to_continue():
            hint = self.body_font.render(
                "Pressione ENTER ou ESPACO para retornar", True, (200, 195, 205),
            )
            surface.blit(hint, hint.get_rect(center=(cx, 380)))
