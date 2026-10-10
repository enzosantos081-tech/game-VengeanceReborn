"""
enemies/boss_sprites.py
Carrega e recorta a spritesheet do Vharok (assets/boss/vharok_spritesheet.png).

A sheet tem 768x576 px, em uma grade de 96x96 (8 colunas x 6 linhas). Os
quadros NÃO são percorridos automaticamente: cada animação é uma lista
explícita de (linha, coluna) definida abaixo.

    linha 0  idle (8 quadros; vários são idênticos - respiração sutil)
    linha 1  caminhada (8 quadros; os pés se alternam)
    linha 2  slam: col 1-3 braços erguidos (preparação) | col 4-7 golpe/impacto
    linha 3  rajada: col 1-4 carga | col 5-6 liberação | col 7 recuperação
    linha 4  pulo (col 1-4) - NÃO usado, o Vharok não pula
             col 5-7: ondas de choque no chão (efeito avulso, crescendo)
    linha 5  col 0-1: onda de choque larga (efeito avulso, 1 quadro de 190px)
             col 2-5: faíscas vermelhas em leque (efeito avulso, crescendo)

Alinhamento: cada quadro do corpo é recortado como a CÉLULA INTEIRA 96x96
(sem cortar coroa, braços, esferas de energia...) e posicionado pela "linha
dos pés" do próprio quadro (_FEET_EDGE, medida na sheet) no chão da arena
(rect.bottom), e pelo centro da célula (x=48) no centro do hitbox. Assim o
sprite não "pula" entre quadros, mesmo nos quadros em que a imagem original
está 2 px mais baixa. A hitbox (settings.BOSS_WIDTH/HEIGHT) não é alterada.

Se o arquivo da sheet não existir ou não carregar, get_boss_sprites()
devolve None e enemies/boss.py usa o desenho retangular antigo.
"""

import math
import os
import pygame
from config import settings

SHEET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "assets", "boss", "vharok_spritesheet.png")

CELL = 96
CELL_CENTER_X = 48

# Borda inferior (exclusiva) da última linha "sólida" (>= 8 px opacos) de cada
# quadro do corpo = sola dos pés. Medido na sheet processada.
_FEET_EDGE = {
    (0, 0): 88, (0, 1): 90, (0, 2): 88, (0, 3): 88, (0, 4): 88, (0, 5): 90, (0, 6): 88, (0, 7): 88,
    (1, 0): 90, (1, 1): 88, (1, 2): 88, (1, 3): 90, (1, 4): 88, (1, 5): 88, (1, 6): 90, (1, 7): 88,
    (2, 0): 88, (2, 1): 88, (2, 2): 88, (2, 3): 88, (2, 4): 88, (2, 5): 88, (2, 6): 88, (2, 7): 88,
    (3, 0): 88, (3, 1): 88, (3, 2): 88, (3, 3): 88, (3, 4): 88, (3, 5): 88, (3, 6): 88, (3, 7): 88,
    (4, 4): 88,
}


def _cells(row, cols):
    return [(row, c) for c in cols]


# Animações do corpo: nome -> lista de (linha, coluna)
BODY_ANIMS = {
    "idle": _cells(0, range(8)),
    "walk": _cells(1, range(8)),
    "slam_windup": _cells(2, (1, 2, 3)),       # braços erguidos, último quadro = "carregado" (listras vermelhas)
    "slam_strike": _cells(2, (4, 5, 6, 7)),    # agacha e bate no chão; as chamas sobem e se espalham
    "barrage_charge": _cells(3, (1, 2, 3, 4)),  # braços abertos, esferas nas mãos, energia no peito
    "barrage_release": _cells(3, (5, 6)),      # energia explode para fora
    "recover": [(3, 7)],                       # postura baixa, sem efeitos (idêntica a (4, 4))
}

# Efeitos avulsos (sem corpo): nome -> (x, y, w, h, âncora_x, âncora_y) em px da sheet.
# Âncora = ponto do recorte que fica sobre o ponto de referência no jogo.
_GROUND_EDGE = 87  # borda inferior (exclusiva) das ondas, medida na sheet
EFFECTS = {
    "wave_0": (5 * CELL, 4 * CELL, CELL, CELL, CELL_CENTER_X, _GROUND_EDGE),
    "wave_1": (6 * CELL, 4 * CELL, CELL, CELL, CELL_CENTER_X, _GROUND_EDGE),
    "wave_2": (7 * CELL, 4 * CELL, CELL, CELL, CELL_CENTER_X, _GROUND_EDGE),
    "wave_full": (0, 5 * CELL, 198, CELL, 97, _GROUND_EDGE),
    "burst_0": (2 * CELL, 5 * CELL, CELL, CELL, 50, 60),
    "burst_1": (3 * CELL, 5 * CELL, CELL, CELL, 50, 60),
    "burst_2": (4 * CELL, 5 * CELL, CELL, CELL, 50, 60),
    "burst_3": (5 * CELL, 5 * CELL, CELL, CELL, 50, 60),
    "shard": (450, 542, 17, 10, 8, 5),          # projétil: cabeça à direita, rastro à esquerda
}

WAVE_STAGES = ("wave_0", "wave_1", "wave_2")
BURST_FRAMES = ("burst_0", "burst_1", "burst_2")

# Tinturas aditivas (RGB somado ao quadro; o alfa é preservado)
TINTS = {
    "hit": (200, 200, 200),          # acerto do jogador (antes: corpo todo branco)
    "tele_slam": (80, 55, 0),        # telegraph do slam (antes: retângulo amarelo piscando)
    "tele_barrage": (70, 0, 95),     # telegraph da rajada (antes: retângulo roxo piscando)
    "tele_charge": (0, 65, 85),      # telegraph da investida (azul-ciano, distinto do slam e da rajada)
    "rage": (34, 0, 6),              # Fase 2: armadura avermelhada
    "rage_flash": (170, 30, 25),     # pisca ao entrar na Fase 2
}


class BossSprites:
    def __init__(self, sheet):
        self.scale = settings.BOSS_SPRITE_SCALE
        self._sheet = sheet
        self._cache = {}         # (nome, flipped, tint) -> (Surface, (ox, oy))
        self._shard_cache = {}   # (dir, ângulo) -> Surface
        self._glow = None

    # ---- recorte / escala ----
    def _raw_frame(self, name):
        """Recorte (sem escala) + âncora para 'name' (corpo ou efeito)."""
        if name in EFFECTS:
            x, y, w, h, ax, ay = EFFECTS[name]
        else:
            row, col = BODY_NAMES[name]
            x, y, w, h = col * CELL, row * CELL, CELL, CELL
            ax, ay = CELL_CENTER_X, _FEET_EDGE[(row, col)]
        return self._sheet.subsurface(pygame.Rect(x, y, w, h)).copy(), ax, ay

    def get(self, name, facing_right=True, tint=None, scale=None):
        """Devolve (Surface, (ox, oy)): desenhe em (ref_x + ox, ref_y + oy),
        onde ref = (centro do hitbox, chão) para o corpo/ondas, ou o ponto
        de impacto/centro para os demais efeitos."""
        scale = self.scale if scale is None else scale
        key = (name, facing_right, tint, scale)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        surf, ax, ay = self._raw_frame(name)
        w, h = surf.get_size()
        if scale != 1.0:
            surf = pygame.transform.scale(surf, (max(1, round(w * scale)), max(1, round(h * scale))))
        sw, sh = surf.get_size()
        ox, oy = -round(ax * scale), -round(ay * scale)
        if not facing_right:
            surf = pygame.transform.flip(surf, True, False)
            ox = -(sw - round(ax * scale))
        if tint:
            surf = surf.copy()
            surf.fill(TINTS[tint] + (0,), special_flags=pygame.BLEND_RGB_ADD)
        result = (surf, (ox, oy))
        self._cache[key] = result
        return result

    def get_shard(self, vx, vy):
        """Projétil da rajada, girado conforme a trajetória."""
        direction = 1 if vx >= 0 else -1
        ang = math.degrees(math.atan2(vy, abs(vx))) if vx else 0.0
        key = (direction, int(round(ang)))
        surf = self._shard_cache.get(key)
        if surf is None:
            base, _ax, _ay = self._raw_frame("shard")
            w, h = base.get_size()
            base = pygame.transform.scale(base, (round(w * self.scale), round(h * self.scale)))
            if direction < 0:
                base = pygame.transform.flip(base, True, False)
            surf = pygame.transform.rotate(base, -direction * key[1]) if key[1] else base
            self._shard_cache[key] = surf
        return surf

    def get_glow(self):
        """Aura vermelha suave (Fase 2), desenhada atrás do corpo."""
        if self._glow is None:
            w = int(CELL * self.scale * 1.15)
            h = int(CELL * self.scale * 1.1)
            glow = pygame.Surface((w, h), pygame.SRCALPHA)
            # draw.ellipse SOBRESCREVE os pixels (não acumula alfa): por isso o
            # alfa cresce do anel externo (fraco) para o interno (mais forte).
            steps = 7
            for i in range(steps):
                t = i / (steps - 1)
                inset_x = int(t * w * 0.42)
                inset_y = int(t * h * 0.42)
                rect = pygame.Rect(inset_x, inset_y, w - 2 * inset_x, h - 2 * inset_y)
                pygame.draw.ellipse(glow, (190, 20, 30, int(14 + 46 * t)), rect)
            self._glow = glow
        return self._glow


# nome do quadro de corpo -> (linha, coluna), ex.: "walk_3" -> (1, 3)
BODY_NAMES = {}
for _anim, _cells_list in BODY_ANIMS.items():
    for _i, _cell in enumerate(_cells_list):
        BODY_NAMES[f"{_anim}_{_i}"] = _cell


def frame_name(anim, index):
    return f"{anim}_{index}"


_instance = None
_tried = False


def get_boss_sprites():
    """Singleton; None se a sheet não puder ser carregada (fallback)."""
    global _instance, _tried
    if _tried:
        return _instance
    _tried = True
    try:
        if not os.path.isfile(SHEET_PATH):
            return None
        sheet = pygame.image.load(SHEET_PATH)
        sheet = sheet.convert_alpha() if pygame.display.get_surface() is not None else sheet
        _instance = BossSprites(sheet)
    except (pygame.error, OSError):
        _instance = None
    return _instance
