"""
screens/menu.py
Tela inicial do jogo. Exibe o título, uma breve premissa da história e
as instruções de controle. Aguarda o jogador pressionar ENTER/ESPAÇO
para iniciar (ver core/input.py -> confirm_pressed).
"""

import pygame
from config import settings


class MenuScreen:
    def __init__(self):
        self.title_font = pygame.font.Font(None, 72)
        self.subtitle_font = pygame.font.Font(None, 28)
        self.body_font = pygame.font.Font(None, 24)
        self.pulse = 0.0

    def update(self):
        self.pulse += 0.05

    def draw(self, surface):
        surface.fill(settings.COLOR_BG_SKY)

        title = self.title_font.render(settings.GAME_TITLE, True, settings.COLOR_TEXT)
        shadow = self.title_font.render(settings.GAME_TITLE, True, settings.COLOR_TEXT_SHADOW)
        cx = settings.SCREEN_WIDTH // 2
        surface.blit(shadow, shadow.get_rect(center=(cx + 3, 143)))
        surface.blit(title, title.get_rect(center=(cx, 140)))

        subtitle = self.subtitle_font.render(
            "Kael busca vinganca contra Vharok, o Rei do Abismo",
            True, (200, 190, 210),
        )
        surface.blit(subtitle, subtitle.get_rect(center=(cx, 195)))

        import math
        alpha = int(150 + 105 * math.sin(self.pulse))
        prompt_surf = self.body_font.render("Pressione ENTER ou ESPACO para comecar", True, settings.COLOR_TEXT)
        prompt_surf.set_alpha(alpha)
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(cx, 340)))

        controls = [
            "Controles:",
            "A / D ou setas  -  Mover",
            "ESPACO / W  -  Pular (aperte de novo p/ pulo duplo, se comprado)",
            "Segure na parede no ar  -  Deslizar / Wall Jump",
            "Clique esquerdo  -  Atacar (mira na direcao do mouse)",
            "Q  -  Dash",
            "E / ENTER  -  Interagir (Nucleo / Loja)",
            "ESC / P  -  Pausar",
        ]
        y = 372
        for line in controls:
            c = self.body_font.render(line, True, (180, 175, 190))
            surface.blit(c, c.get_rect(center=(cx, y)))
            y += 24
