"""
screens/story.py
Pequenos textos de história exibidos brevemente quando Kael cruza um
ponto do cenário. Ficam sobrepostos à HUD, sem pausar o jogo.

Visual: caixa translúcida com um losango âmbar, texto quebrado em linhas
(se for longo), entrada deslizando de cima e uma fina barra que mostra
quanto tempo falta para a mensagem sumir.
"""

import pygame
from config import settings
from screens.menu import (
    get_font, draw_panel,
    COL_TEXT, COL_EMBER,
)


class StoryPopup:
    DISPLAY_FRAMES = 210  # ~3.5s a 60 FPS
    FADE_FRAMES = 30
    MAX_TEXT_W = 640
    TOP_Y = 84

    def __init__(self):
        self.text = None
        self.timer = 0
        self.font = get_font(27)
        self._lines = []

    def show(self, text):
        self.text = text
        self.timer = StoryPopup.DISPLAY_FRAMES
        self._lines = self._wrap(text)

    def update(self):
        if self.timer > 0:
            self.timer -= 1

    def _wrap(self, text):
        lines, current = [], ""
        for word in text.split():
            candidate = (current + " " + word).strip()
            if not current or self.font.size(candidate)[0] <= StoryPopup.MAX_TEXT_W:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def draw(self, surface):
        if not self.text or self.timer <= 0:
            return

        elapsed = StoryPopup.DISPLAY_FRAMES - self.timer
        if elapsed < StoryPopup.FADE_FRAMES:
            k = elapsed / StoryPopup.FADE_FRAMES
        elif self.timer < StoryPopup.FADE_FRAMES:
            k = self.timer / StoryPopup.FADE_FRAMES
        else:
            k = 1.0
        slide = int((1.0 - k) * -16)  # desliza um pouquinho de cima

        rendered = [self.font.render(line, True, COL_TEXT) for line in self._lines]
        line_h = self.font.get_linesize()
        text_w = max(r.get_width() for r in rendered)
        box_w = text_w + 36 + 44
        box_h = line_h * len(rendered) + 28

        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        draw_panel(box, box.get_rect(), alpha=215, radius=10)

        # losango âmbar à esquerda
        dx, dy = 28, box_h // 2
        pygame.draw.polygon(box, COL_EMBER, [(dx, dy - 8), (dx + 8, dy), (dx, dy + 8), (dx - 8, dy)])
        pygame.draw.polygon(box, (255, 230, 190), [(dx, dy - 3), (dx + 3, dy), (dx, dy + 3), (dx - 3, dy)])

        y = 14
        for r in rendered:
            box.blit(r, (56, y))
            y += line_h

        # barrinha de tempo restante
        ratio = self.timer / StoryPopup.DISPLAY_FRAMES
        bar_w = int((box_w - 40) * ratio)
        if bar_w > 0:
            pygame.draw.rect(box, (255, 150, 70, 160), (20, box_h - 8, bar_w, 2))

        box.set_alpha(int(255 * k))
        x = settings.SCREEN_WIDTH // 2 - box_w // 2
        surface.blit(box, (x, StoryPopup.TOP_Y + slide))
