"""
screens/pause.py
Menu de pausa completo, substituindo o overlay simples anterior.
Oferece três opções: continuar a partida, reiniciar a tentativa atual
(volta ao último Núcleo/checkpoint sem contar como morte) e sair para
o menu principal.
"""

import pygame
from config import settings


class PauseMenu:
    OPTIONS = ["Continuar", "Reiniciar tentativa", "Sair para o menu"]

    def __init__(self):
        self.selected_index = 0
        self.big_font = pygame.font.Font(None, 42)
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 20)

    def reset_selection(self):
        self.selected_index = 0

    def move_selection(self, delta):
        self.selected_index = (self.selected_index + delta) % len(PauseMenu.OPTIONS)

    def selected_option(self):
        return PauseMenu.OPTIONS[self.selected_index]

    def draw(self, surface):
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 8, 15, 190))
        surface.blit(overlay, (0, 0))

        title = self.big_font.render("PAUSADO", True, settings.COLOR_TEXT)
        surface.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 - 90)))

        panel_w, panel_h = 340, len(PauseMenu.OPTIONS) * 46 + 30
        px = settings.SCREEN_WIDTH // 2 - panel_w // 2
        py = settings.SCREEN_HEIGHT // 2 - 40
        pygame.draw.rect(surface, settings.COLOR_UI_PANEL, (px, py, panel_w, panel_h), border_radius=10)
        pygame.draw.rect(surface, settings.COLOR_UI_BORDER, (px, py, panel_w, panel_h), width=2, border_radius=10)

        y = py + 20
        for i, option in enumerate(PauseMenu.OPTIONS):
            selected = i == self.selected_index
            if selected:
                pygame.draw.rect(surface, (60, 50, 80), (px + 16, y - 6, panel_w - 32, 36), border_radius=6)
            prefix = "> " if selected else "  "
            color = settings.COLOR_TEXT if selected else (180, 175, 190)
            rendered = self.font.render(prefix + option, True, color)
            surface.blit(rendered, (px + 28, y))
            y += 46

        hint = self.small_font.render("W/S: navegar   ENTER/E: confirmar   ESC/P: continuar", True, (170, 165, 180))
        surface.blit(hint, hint.get_rect(center=(settings.SCREEN_WIDTH // 2, py + panel_h + 26)))
