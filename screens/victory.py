"""
screens/victory.py
Tela apresentada após derrotar Vharok: "Vharok foi derrotado" seguido de
"Kael finalmente conseguiu sua vingança", encerrando a história.

Visual: o mesmo panorama noturno do menu, com partículas douradas
subindo e o conteúdo surgindo em fade. Esta tela só tem draw() (o jogo
não chama update), então a animação usa um contador interno que reinicia
sozinho quando a tela volta a aparecer.
"""

import math
import random

import pygame
from config import settings
from screens.menu import (
    get_font, draw_text_glow, draw_panel, draw_divider, draw_coin_icon,
    vertical_gradient, make_vignette, load_backdrop,
    COL_TEXT, COL_MOON, COL_MOON_DIM, COL_GOLD,
)


class VictoryScreen:
    FADE_FRAMES = 60

    def __init__(self):
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        self.title_font = get_font(66, serif=True, bold=True)
        self.sub_font = get_font(36)
        self.label_font = get_font(24)
        self.number_font = get_font(52)
        self.hint_font = get_font(28)

        self.backdrop = load_backdrop()
        self.shade = vertical_gradient(w, h, (3, 6, 18, 110), (3, 6, 18, 175))
        self.vignette = make_vignette(w, h, strength=185)
        self._layer = pygame.Surface((w, h), pygame.SRCALPHA)

        self._t = 0
        self._last_draw = -10000

        # Partículas douradas: (x, y inicial, velocidade, fase, tamanho)
        rng = random.Random(5)
        self.motes = [
            (rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.3, 1.0),
             rng.uniform(0, 6.28), rng.choice((1, 2, 2, 3)))
            for _ in range(55)
        ]

    def draw(self, surface, player):
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        cx = w // 2

        # Reinicia a animação se a tela ficou um tempo sem ser desenhada
        now = pygame.time.get_ticks()
        if now - self._last_draw > 300:
            self._t = 0
        self._last_draw = now
        self._t += 1
        t = self._t

        # Fundo: lua centralizada no panorama
        offset = max(0, (self.backdrop.get_width() - w) // 2)
        surface.blit(self.backdrop, (-offset, 0))
        surface.blit(self.shade, (0, 0))

        for x, y0, speed, phase, size in self.motes:
            y = (y0 - t * speed) % (h + 20) - 10
            px = x + math.sin(phase + t * 0.02) * 12
            b = 0.35 + 0.65 * abs(math.sin(phase + t * 0.04))
            pygame.draw.circle(surface, (int(255 * b), int(205 * b), int(90 * b)),
                               (int(px), int(y)), size)
        surface.blit(self.vignette, (0, 0))

        # Conteúdo em camada própria (fade-in)
        layer = self._layer
        layer.fill((0, 0, 0, 0))

        draw_text_glow(layer, self.title_font, "VHAROK FOI DERROTADO", COL_TEXT, (cx, 150),
                       glow=settings.COLOR_CORE)
        draw_divider(layer, cx, 200, half_width=210, color=COL_GOLD)

        sub = self.sub_font.render("Kael finalmente conseguiu sua vingança.", True, COL_MOON)
        layer.blit(sub, sub.get_rect(center=(cx, 240)))

        panel = pygame.Rect(cx - 190, 290, 380, 112)
        draw_panel(layer, panel, alpha=205)
        label = self.label_font.render("MOEDAS TOTAIS COLETADAS", True, COL_MOON_DIM)
        layer.blit(label, label.get_rect(center=(cx, panel.y + 28)))
        number = self.number_font.render(str(player.stats.total_coins_collected), True, COL_GOLD)
        nrect = number.get_rect(center=(cx + 16, panel.y + 74))
        layer.blit(number, nrect)
        draw_coin_icon(layer, (nrect.left - 22, nrect.centery), 12)

        layer.set_alpha(int(255 * min(1.0, t / self.FADE_FRAMES)))
        surface.blit(layer, (0, 0))

        # Aviso final (aparece depois do fade, piscando suave)
        if t > self.FADE_FRAMES:
            alpha = int(150 + 105 * math.sin(t * 0.05))
            hint = self.hint_font.render("Pressione ENTER para voltar ao menu", True, COL_TEXT)
            hint.set_alpha(alpha)
            surface.blit(hint, hint.get_rect(center=(cx, 462)))
