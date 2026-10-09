"""
enemies/flying_enemy_sprites.py
Carrega e recorta a spritesheet do morcego (assets/morcego/morcego_sheet_96px.png).

A sheet tem 192x192 px, em uma grade de 96x96 (2 colunas x 2 linhas):

    linha 0  olhando para a DIREITA   col 0 = asas erguidas | col 1 = asas abaixadas
    linha 1  olhando para a ESQUERDA  col 0 = asas erguidas | col 1 = asas abaixadas

Alinhamento: cada quadro é a CÉLULA INTEIRA 96x96, posicionada pelo centro
da célula (48, 48) no centro do hitbox. As duas posições de asa compartilham
o mesmo corpo na mesma posição, então o sprite não "pula" ao bater as asas.
A hitbox (settings.FLYING_ENEMY_WIDTH/HEIGHT) não é alterada.

Se o arquivo da sheet não existir ou não carregar, get_flying_enemy_sprites()
devolve None e enemies/flying_enemy.py usa o desenho simples antigo.

Opcional em settings.py:
    FLYING_ENEMY_SPRITESHEET_PATH  caminho da imagem
    FLYING_ENEMY_SPRITE_SCALE      escala do sprite (padrão: automática, ver default_scale();
                                   múltiplos de 0.25 mantêm o pixel art nítido)
"""

import os
import pygame
from config import settings

SHEET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "assets", "morcego", "morcego_sheet_96px.png")

CELL = 96            # tamanho de cada célula da sheet, em pixels
CELL_CENTER = 48
SHEET_UPSCALE = 4    # a sheet de 96px é a arte original (24px) ampliada 4x sem suavização
CONTENT_PIXELS = 20  # largura do desenho do morcego na arte original (asas abertas), em pixels
WING_MARGIN = 10     # quanto as asas passam do hitbox (5 px de cada lado)

ROW_RIGHT = 0
ROW_LEFT = 1
FLAP_FRAMES = 2


def default_scale():
    """Escala automática: cada pixel da arte original vira um número INTEIRO
    de pixels na tela (com a hitbox atual de 30 px: 2 px por pixel -> o
    morcego fica com 40x22 px, quase exatamente a hitbox). Escala inteira
    mantém o pixel art nítido e uniforme; escalas quebradas deixam pixels
    de tamanhos diferentes."""
    px_per_art_pixel = max(1, round((settings.FLYING_ENEMY_WIDTH + WING_MARGIN) / CONTENT_PIXELS))
    return px_per_art_pixel / SHEET_UPSCALE


class FlyingEnemySprites:
    def __init__(self, sheet):
        self.scale = getattr(settings, "FLYING_ENEMY_SPRITE_SCALE", None) or default_scale()
        self._sheet = sheet
        self._cache = {}   # (facing_right, flap_frame, flash) -> Surface

    def get(self, facing_right=True, flap_frame=0, flash=False):
        """Devolve a Surface do quadro. Desenhe-a com
        surf.get_rect(center=centro_do_hitbox)."""
        key = (facing_right, flap_frame % FLAP_FRAMES, flash)
        surf = self._cache.get(key)
        if surf is not None:
            return surf

        row = ROW_RIGHT if facing_right else ROW_LEFT
        col = flap_frame % FLAP_FRAMES
        cell = self._sheet.subsurface(pygame.Rect(col * CELL, row * CELL, CELL, CELL)).copy()
        size = max(1, round(CELL * self.scale))
        # scale (e não smoothscale) mantém o pixel art nítido
        surf = pygame.transform.scale(cell, (size, size))
        if flash:
            # silhueta branca (acerto do jogador), preservando o contorno
            mask = pygame.mask.from_surface(surf)
            surf = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        self._cache[key] = surf
        return surf


_instance = None
_tried = False


def get_flying_enemy_sprites():
    """Singleton compartilhado por todos os morcegos; None se a sheet não
    puder ser carregada (fallback)."""
    global _instance, _tried
    if _tried:
        return _instance
    _tried = True
    path = getattr(settings, "FLYING_ENEMY_SPRITESHEET_PATH", SHEET_PATH)
    try:
        if not os.path.isfile(path):
            print(f"[FlyingEnemy] Spritesheet não encontrada em: {path} - usando desenho simples.")
            return None
        sheet = pygame.image.load(path)
        sheet = sheet.convert_alpha() if pygame.display.get_surface() is not None else sheet
        _instance = FlyingEnemySprites(sheet)
    except (pygame.error, OSError):
        _instance = None
    return _instance
