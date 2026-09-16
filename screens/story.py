"""
screens/story.py
Pequenos textos de história exibidos brevemente quando Kael entra em
uma nova região do cenário, conforme sugerido na seção 21 do documento
("história apresentada durante o jogo"). Fica sobreposto à HUD, sem
pausar o jogo.
"""

import pygame
from config import settings


class StoryPopup:
    DISPLAY_FRAMES = 210  # ~3.5s a 60 FPS
    FADE_FRAMES = 30

    def __init__(self):
        self.text = None
        self.timer = 0
        self.font = pygame.font.Font(None, 26)

    def show(self, text):
        self.text = text
        self.timer = StoryPopup.DISPLAY_FRAMES

    def update(self):
        if self.timer > 0:
            self.timer -= 1

    def draw(self, surface):
        if not self.text or self.timer <= 0:
            return
        if self.timer > StoryPopup.DISPLAY_FRAMES - StoryPopup.FADE_FRAMES:
            alpha = int(255 * (StoryPopup.DISPLAY_FRAMES - self.timer) / StoryPopup.FADE_FRAMES)
        elif self.timer < StoryPopup.FADE_FRAMES:
            alpha = int(255 * self.timer / StoryPopup.FADE_FRAMES)
        else:
            alpha = 255

        rendered = self.font.render(self.text, True, settings.COLOR_TEXT)
        box = pygame.Surface((rendered.get_width() + 40, rendered.get_height() + 24), pygame.SRCALPHA)
        pygame.draw.rect(box, (20, 16, 30, min(215, alpha)), box.get_rect(), border_radius=8)
        pygame.draw.rect(box, (120, 100, 140, alpha), box.get_rect(), width=2, border_radius=8)
        text_surf = rendered.copy()
        text_surf.set_alpha(alpha)
        box.blit(text_surf, (20, 12))

        x = settings.SCREEN_WIDTH // 2 - box.get_width() // 2
        surface.blit(box, (x, 90))
