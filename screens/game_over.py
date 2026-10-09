"""
screens/game_over.py
Tela apresentada após a morte de Kael. A morte NÃO é um Game Over
definitivo, apenas uma nova tentativa: a tela mostra brevemente o que foi
mantido e o jogador retorna ao Núcleo do Retorno / último checkpoint.

Visual: fundo vermelho-escuro com brasas subindo, título que surge em
fade e o aviso de "continuar" aparecendo só depois do tempo mínimo.
"""

import math
import random

import pygame
from config import settings
from screens.menu import (
    get_font, draw_text_glow, draw_panel, draw_divider, draw_coin_icon,
    vertical_gradient, make_vignette,
    COL_TEXT, COL_MOON_DIM, COL_CRIMSON, COL_GOLD,
)


class GameOverScreen:
    FADE_FRAMES = 40

    def __init__(self):
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        self.title_font = get_font(84, serif=True, bold=True)
        self.body_font = get_font(30)
        self.coin_font = get_font(34)
        self.hint_font = get_font(28)
        self.timer = 0
        self.MIN_DISPLAY_FRAMES = 90

        self.bg = vertical_gradient(w, h, (8, 4, 10), (42, 8, 16)).convert()
        self.vignette = make_vignette(w, h, strength=210)
        self._layer = pygame.Surface((w, h), pygame.SRCALPHA)  # conteúdo (faz o fade-in)

        # Brasas: [x, y, velocidade, fase, tamanho]
        rng = random.Random(11)
        self.embers = [
            [rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.4, 1.3),
             rng.uniform(0, 6.28), rng.choice((1, 2, 2, 3))]
            for _ in range(46)
        ]

    def reset(self):
        self.timer = 0

    def update(self):
        self.timer += 1
        h = settings.SCREEN_HEIGHT
        for e in self.embers:
            e[1] -= e[2]
            e[0] += math.sin(e[3] + self.timer * 0.03) * 0.35
            if e[1] < -6:
                e[1] = h + 6

    def ready_to_continue(self):
        return self.timer >= self.MIN_DISPLAY_FRAMES

    def draw(self, surface, player):
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        cx = w // 2

        surface.blit(self.bg, (0, 0))
        for x, y, _speed, phase, size in self.embers:
            b = 0.45 + 0.55 * abs(math.sin(phase + self.timer * 0.05))
            color = (int(255 * b), int(105 * b), int(45 * b))
            pygame.draw.circle(surface, color, (int(x), int(y)), size)
        surface.blit(self.vignette, (0, 0))

        # Conteúdo desenhado numa camada separada para poder fazer fade-in
        layer = self._layer
        layer.fill((0, 0, 0, 0))

        draw_text_glow(layer, self.title_font, "KAEL CAIU...", COL_CRIMSON, (cx, 190),
                       glow=COL_CRIMSON)
        draw_divider(layer, cx, 244, half_width=170, color=COL_CRIMSON)

        msg = self.body_font.render(
            "O Núcleo do Retorno reconstrói seu corpo no último ponto conhecido.",
            True, COL_TEXT)
        layer.blit(msg, msg.get_rect(center=(cx, 284)))

        # Moedas mantidas
        panel = pygame.Rect(cx - 170, 322, 340, 56)
        draw_panel(layer, panel, alpha=200, border=(150, 70, 80))
        coins = self.coin_font.render(f"Moedas mantidas: {player.stats.coins}", True, COL_GOLD)
        crect = coins.get_rect(center=(panel.centerx + 14, panel.centery))
        layer.blit(coins, crect)
        draw_coin_icon(layer, (crect.left - 20, panel.centery), 10)

        fade = min(1.0, self.timer / self.FADE_FRAMES)
        layer.set_alpha(int(255 * fade))
        surface.blit(layer, (0, 0))

        # Aviso para continuar (só depois do tempo mínimo, piscando suave)
        if self.ready_to_continue():
            since = self.timer - self.MIN_DISPLAY_FRAMES
            alpha = min(255, since * 8)
            alpha = int(alpha * (0.7 + 0.3 * math.sin(self.timer * 0.07)))
            hint = self.hint_font.render("Pressione ENTER ou ESPAÇO para retornar", True, COL_MOON_DIM)
            hint.set_alpha(max(0, alpha))
            surface.blit(hint, hint.get_rect(center=(cx, 430)))
