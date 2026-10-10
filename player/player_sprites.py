"""
player/player_sprites.py
Carrega e gerencia as animações do sprite do Kael a partir de UMA
spritesheet (assets/player/kael_spritesheet.png, RGBA com transparência
real, pixel art, sem suavização).

Layout da spritesheet: grade de células de 128x128 px, 6 colunas x 10
linhas (768x1280). O Kael olha para a DIREITA em todos os quadros; quando
ele está virado para a esquerda o frame é espelhado na hora de desenhar
(mecanismo que já existia - ver SpriteAnimator.get_surface). Em todas as
células o corpo fica centrado em x=64 e os pés em y=124 (4 px de margem
embaixo); por isso cada quadro é recortado em (0, 0, 128, 124): assim o
midbottom usado em Player.draw continua sendo os pés, sem deslocamentos
entre animações.

Linhas da sheet (linha: quadros -> uso):
    0: 4  idle                          -> "idle"
    1: 6  walk                          -> (o jogo não tem estado de caminhada)
    2: 6  run                           -> "run"
    3: 4  agachar/impulso + subida      -> "jump" (quadros 1-2)
    4: 2  queda com a capa para cima    -> "fall"
    5: 6  ataque 1 (golpe de cima)      -> "attack" (quadros 1-3)
    6: 6  ataque 2 (estocada)           -> (não usado)
    7: 4  dash                          -> "dash"
    8: 2  guarda / reação               -> (não usado, sem estado equivalente)
    9: 6  dano -> queda -> morte        -> "death" (quadros 1-5, fica no último)

As dimensões de colisão do jogador (player.rect) NÃO dependem deste
arquivo - isso aqui é só a camada visual.
"""

import os
import pygame

_SHEET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "player", "kael_spritesheet.png",
)

CELL_W = 128
CELL_H = 128
# Margem transparente abaixo dos pés dentro de cada célula (os pés ficam
# em y=124). É removida no recorte para o midbottom ser os pés.
FOOT_PAD = 4

# 1.0 = pixels da arte 1:1 (nítido). Use apenas múltiplos inteiros (2.0...)
# para manter o pixel art sem distorção; a escala usa vizinho mais próximo.
SPRITE_SCALE = 1.0

# Nome da animação -> (linha da sheet, colunas dos quadros, duração em
# frames de jogo por imagem, repete?). Animações com repete=False
# ficam paradas no último quadro até o estado mudar.
_ANIMATION_DEFS = {
    "idle": (0, [0, 1, 2, 3], 14, True),
    "run": (2, [0, 1, 2, 3, 4, 5], 7, True),
    "jump": (3, [1, 2], 8, False),
    "fall": (4, [0, 1], 8, True),
    "dash": (7, [0, 1, 2, 3], 4, True),
    # PLAYER_ATTACK_DURATION = 14 frames: 3 quadros de 5 frames cobrem o golpe inteiro.
    "attack": (5, [1, 2, 3], 5, False),
    "death": (9, [1, 2, 3, 4, 5], 8, False),
}

_cache = None  # {anim_name: {"frames": [...], "flipped": [...], "duration": int, "loop": bool}}


def _load_all():
    global _cache
    if _cache is not None:
        return _cache
    # A spritesheet é carregada uma única vez (lazy, no primeiro uso).
    sheet = pygame.image.load(_SHEET_PATH).convert_alpha()
    _cache = {}
    for anim_name, (row, cols, duration, loop) in _ANIMATION_DEFS.items():
        frames = []
        flipped = []
        for col in cols:
            rect = pygame.Rect(col * CELL_W, row * CELL_H, CELL_W, CELL_H - FOOT_PAD)
            frame = sheet.subsurface(rect).copy()
            if SPRITE_SCALE != 1.0:
                w = max(1, round(frame.get_width() * SPRITE_SCALE))
                h = max(1, round(frame.get_height() * SPRITE_SCALE))
                frame = pygame.transform.scale(frame, (w, h))
            frames.append(frame)
            flipped.append(pygame.transform.flip(frame, True, False))
        _cache[anim_name] = {"frames": frames, "flipped": flipped,
                             "duration": duration, "loop": loop}
    return _cache


class SpriteAnimator:
    """Controla qual animação/frame mostrar para um Player. Uma instância
    por Player (guarda o estado da animação atual)."""

    def __init__(self):
        self.state = "idle"
        self.frame_index = 0
        self.frame_timer = 0

    def set_state(self, state):
        """Troca de animação. Reinicia do frame 0 apenas se o estado
        realmente mudou (senão a animação atual continua tocando)."""
        if state != self.state:
            self.state = state
            self.frame_index = 0
            self.frame_timer = 0

    def update(self):
        anims = _load_all()
        anim = anims.get(self.state, anims["idle"])
        self.frame_timer += 1
        if self.frame_timer >= anim["duration"]:
            self.frame_timer = 0
            last = len(anim["frames"]) - 1
            if self.frame_index < last:
                self.frame_index += 1
            elif anim["loop"]:
                self.frame_index = 0
            # senão: animação sem repetição fica no último quadro

    def get_surface(self, facing_right):
        anims = _load_all()
        anim = anims.get(self.state, anims["idle"])
        idx = min(self.frame_index, len(anim["frames"]) - 1)
        return anim["frames"][idx] if facing_right else anim["flipped"][idx]
