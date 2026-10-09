"""
screens/pause.py
Menu de pausa com três opções: continuar, reiniciar a tentativa atual
(volta ao último Núcleo/checkpoint sem contar como morte) e sair para o
menu principal. As strings de OPTIONS são usadas por core/game.py para
decidir o que fazer - se mudar o texto, mude lá também.
"""

import math

import pygame
from config import settings
from screens.menu import (
    get_font, draw_text_glow, draw_panel, draw_divider, make_vignette,
    COL_TEXT, COL_MOON_DIM, COL_EMBER,
)


class PauseMenu:
    OPTIONS = ["Continuar", "Reiniciar tentativa", "Sair para o menu"]
    ROW_H = 58

    def __init__(self):
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        self.selected_index = 0
        self.title_font = get_font(60, serif=True, bold=True)
        self.font = get_font(34)
        self.small_font = get_font(22)

        # Escurece o jogo parado ao fundo (montado uma vez só)
        self.overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        self.overlay.fill((5, 7, 20, 175))
        self.overlay.blit(make_vignette(w, h, strength=200), (0, 0))

    def reset_selection(self):
        self.selected_index = 0

    def move_selection(self, delta):
        self.selected_index = (self.selected_index + delta) % len(PauseMenu.OPTIONS)

    def selected_option(self):
        return PauseMenu.OPTIONS[self.selected_index]

    def draw(self, surface):
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        cx = w // 2
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.006)

        surface.blit(self.overlay, (0, 0))

        draw_text_glow(surface, self.title_font, "PAUSADO", COL_TEXT, (cx, 140), glow=COL_EMBER)
        draw_divider(surface, cx, 184, half_width=120)

        panel = pygame.Rect(cx - 200, 214, 400, len(PauseMenu.OPTIONS) * self.ROW_H + 28)
        draw_panel(surface, panel, alpha=215)

        y = panel.y + 14
        for i, option in enumerate(PauseMenu.OPTIONS):
            row = pygame.Rect(panel.x + 16, y, panel.width - 32, self.ROW_H - 8)
            selected = i == self.selected_index
            if selected:
                glow = pygame.Surface(row.size, pygame.SRCALPHA)
                pygame.draw.rect(glow, (255, 150, 70, int(40 + 30 * pulse)), glow.get_rect(),
                                 border_radius=8)
                surface.blit(glow, row.topleft)
                pygame.draw.rect(surface, COL_EMBER, row, width=2, border_radius=8)
                # losango marcador
                mx, my = row.x + 20, row.centery
                pygame.draw.polygon(surface, COL_EMBER,
                                    [(mx, my - 6), (mx + 6, my), (mx, my + 6), (mx - 6, my)])
            color = COL_TEXT if selected else COL_MOON_DIM
            text = self.font.render(option, True, color)
            surface.blit(text, text.get_rect(center=row.center))
            y += self.ROW_H

        hint = self.small_font.render("W/S navegar   ·   ENTER/E confirmar   ·   ESC/P continuar",
                                      True, COL_MOON_DIM)
        surface.blit(hint, hint.get_rect(center=(cx, panel.bottom + 32)))
