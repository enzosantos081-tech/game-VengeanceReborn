"""
core/debug_overlay.py
Ferramenta de DEBUG para desenvolvimento (tecla F3): grade de
referência sobre o mundo, hitboxes de colisão e um painel com FPS e
coordenadas do jogador/mouse (em espaço de mundo, já considerando a
câmera). Puramente visual - não cria nenhum sistema de colisão novo,
só desenha os Rects que o jogo já usa para física/colisão/gatilhos.

Quando o modo DEBUG está desligado, nada aqui é chamado - o jogo
permanece exatamente como antes (ver core/game.py).
"""

import pygame

GRID_SPACING = 100
GRID_COLOR = (90, 90, 110)
GRID_LABEL_COLOR = (170, 170, 200)

COLOR_PLAYER = (80, 220, 255)
COLOR_ENEMY = (255, 70, 70)
COLOR_PLATFORM = (255, 210, 60)
COLOR_OBSTACLE = (255, 110, 200)
COLOR_TRIGGER = (120, 255, 150)


class DebugOverlay:
    def __init__(self):
        self.font = pygame.font.Font(None, 16)
        self.panel_font = pygame.font.Font(None, 22)

    # ---------- Mundo: grade + hitboxes (afetado pela câmera, igual ao resto do jogo) ----------
    def draw_world(self, surf, camera_x, level, player):
        self._draw_grid(surf, camera_x)
        self._draw_hitboxes(surf, camera_x, level, player)

    def _draw_grid(self, surf, camera_x):
        w, h = surf.get_width(), surf.get_height()

        first_x = (int(camera_x) // GRID_SPACING) * GRID_SPACING
        x = first_x
        while x - camera_x < w:
            sx = int(x - camera_x)
            if sx >= 0:
                pygame.draw.line(surf, GRID_COLOR, (sx, 0), (sx, h), 1)
                label = self.font.render(str(x), True, GRID_LABEL_COLOR)
                surf.blit(label, (sx + 2, 2))
            x += GRID_SPACING

        y = 0
        while y < h:
            pygame.draw.line(surf, GRID_COLOR, (0, y), (w, y), 1)
            label = self.font.render(str(y), True, GRID_LABEL_COLOR)
            surf.blit(label, (2, y + 2))
            y += GRID_SPACING

    def _draw_rect(self, surf, camera_x, rect, color):
        r = rect.move(-camera_x, 0)
        pygame.draw.rect(surf, color, r, width=2)

    def _draw_hitboxes(self, surf, camera_x, level, player):
        # Chão, plataformas móveis/quebradiças - tudo que já
        # entra na checagem de colisão (level.platforms.rects()).
        for r in level.platforms.rects():
            self._draw_rect(surf, camera_x, r, COLOR_PLATFORM)

        # Obstáculos com dano por contato (espinhos etc.)
        for spike in level.obstacles.spikes:
            self._draw_rect(surf, camera_x, spike.rect, COLOR_OBSTACLE)

        # Estalactites-armadilha (world/obstacles.py -> Stalactite): tem
        # hitbox própria, separada dos espinhos normais, então precisa
        # ser desenhada à parte aqui também.
        for stal in level.obstacles.stalactites:
            if stal.state != "gone":
                self._draw_rect(surf, camera_x, stal.rect, COLOR_OBSTACLE)

        # Inimigos vivos (comuns, à distância, sentinelas, voadores)
        for enemy in level.enemies:
            if enemy.alive:
                self._draw_rect(surf, camera_x, enemy.rect, COLOR_ENEMY)

        # Boss, se presente e vivo
        if level.boss and level.boss.alive:
            self._draw_rect(surf, camera_x, level.boss.rect, COLOR_ENEMY)

        # Outros objetos com colisão/gatilho: moedas, checkpoints, zona
        # da loja e o gatilho de entrada do Boss.
        for coin in level.coins.coins:
            if not coin.collected:
                self._draw_rect(surf, camera_x, coin.rect, COLOR_TRIGGER)
        for cp in level.checkpoints:
            self._draw_rect(surf, camera_x, cp.rect, COLOR_TRIGGER)
        if level.shop_zone:
            self._draw_rect(surf, camera_x, level.shop_zone.rect, COLOR_TRIGGER)
        if level.boss_trigger:
            self._draw_rect(surf, camera_x, level.boss_trigger, COLOR_TRIGGER)

        # Jogador por último, pra ficar sempre visível por cima do resto.
        self._draw_rect(surf, camera_x, player.rect, COLOR_PLAYER)

    # ---------- Painel de texto: espaço de TELA, não se move com a câmera ----------
    def draw_panel(self, screen, fps, player, camera_x, mouse_screen_pos, shake_offset=(0, 0)):
        mx, my = mouse_screen_pos
        ox, oy = shake_offset
        # Desfaz o deslocamento do screen shake e soma a câmera, pra dar
        # a coordenada REAL do mundo sob o cursor.
        world_x = int(mx - ox + camera_x)
        world_y = int(my - oy)

        lines = [
            ("DEBUG: ON", (120, 255, 120)),
            (f"FPS: {int(fps)}", (230, 230, 235)),
            ("", None),
            ("PLAYER", (230, 230, 235)),
            (f"X: {int(player.rect.x)}", (230, 230, 235)),
            (f"Y: {int(player.rect.y)}", (230, 230, 235)),
            ("", None),
            ("MOUSE", (230, 230, 235)),
            (f"Screen X: {mx}", (230, 230, 235)),
            (f"Screen Y: {my}", (230, 230, 235)),
            (f"World X: {world_x}", (230, 230, 235)),
            (f"World Y: {world_y}", (230, 230, 235)),
        ]

        pad = 8
        line_h = 20
        panel_w = 210
        panel_h = pad * 2 + line_h * len(lines)
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((10, 10, 18, 225))
        screen.blit(panel, (0, 0))

        y = pad
        for text, color in lines:
            if text:
                rendered = self.panel_font.render(text, True, color)
                screen.blit(rendered, (pad, y))
            y += line_h
