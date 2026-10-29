"""
enemies/boss_sprites.py
Carrega os quadros do Cavaleiro Sombrio (novo visual de Vharok) e define as
tabelas de animação usadas por enemies/boss.py.

Origem dos quadros
------------------
As 7 spritesheets originais (assets/boss/source/*.webp) NÃO são grades
regulares: os quadros têm larguras diferentes, efeitos que encostam nos
vizinhos e o personagem está em escala levemente diferente em cada folha.
tools/process_knight_sheets.py segmenta cada folha, iguala as escalas e grava
um PNG por quadro em assets/boss/knight/ mais o manifest.json, que guarda para
cada quadro o tamanho e a ÂNCORA (ax, ay):

    corpo   ax = centro do tronco, ay = linha da sola dos pés
    efeito  ax, ay = centro (ou base, para efeitos de chão)

Desenhar um quadro significa colocar a âncora sobre um ponto do jogo: o centro
do hitbox no chão (rect.centerx, rect.bottom) para o corpo. Como a âncora são
os pés, o personagem não "pula" entre quadros de tamanhos diferentes (agachado,
braços erguidos, investida...) e o tamanho do sprite não altera a hitbox
(settings.BOSS_WIDTH/HEIGHT), a posição física nem a colisão.

Os quadros olham para a DIREITA; virado para a esquerda é um flip horizontal
com a âncora espelhada.

Mapa dos quadros (prefixo = folha de origem)
--------------------------------------------
    burst_0                      idle (estável, parado)
    walk_0 .. walk_5             caminhada (ciclo de 6 quadros, folha pixel_walk_sheet)
    smash_1, smash_2             slam: braços erguidos (preparação)
    smash_3                      slam: queda do golpe, poeira
    gexp_3, gexp_5, gexp_6       slam: erupção de fogo no chão (corpo + fogo)
    smash_5                      slam: recuperação
    burst_1, burst_2             rajada: esferas nas mãos / energia no peito
    burst_3..burst_5             rajada: liberação (pétalas se espalhando)
    burst_6                      rajada: recuperação
    chg_0, chg_1                 investida: preparação
    chg_2 .. chg_5               investida: arranque e corrida (chg_3..5 em ciclo)
    chg_6, chg_7                 investida: golpe de impacto / derrapagem
    punch_0 .. punch_4           golpe curto: preparação, braço, carga, impacto, recuperação
    orb_1, orb_2, orb_5          orbe: concentração, carga no peito, esfera na mão
    orb_6, orb_3                 orbe: arremesso (sem a esfera: ela vira projétil)
    orb_7                        orbe: recuperação
    orb_trail, orb_round         esfera do projétil (com rastro / redonda)
    fx_shard_0..3                estilhaço da rajada (giro)
    fx_star_0..2, fx_puff_0..1   faíscas e fumaça de impacto
    fx_embers                    brasas que se dissipam no chão (fim do slam)

Se o manifesto ou algum PNG não puder ser carregado, get_boss_sprites()
devolve None e enemies/boss.py usa o desenho retangular de reserva.
"""

import json
import math
import os
import pygame
from config import settings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES_DIR = os.path.join(_ROOT, "assets", "boss", "knight")
MANIFEST_PATH = os.path.join(FRAMES_DIR, "manifest.json")

IDLE_FRAME = "burst_0"
WALK_FRAMES = tuple(f"walk_{i}" for i in range(6))   # ordem de leitura da folha, em ciclo

# ---- Tabelas de animação: [(quadro, peso)] ---------------------------------
# O quadro mostrado é escolhido pela PROPORÇÃO do tempo decorrido (timers da
# máquina de estados do boss), então a animação sempre acompanha o tempo real
# do ataque, qualquer que seja o valor configurado em settings.
SLAM_WINDUP = [("smash_1", 2), ("smash_2", 3)]
SLAM_STRIKE = [("smash_3", 3), ("gexp_3", 2), ("gexp_5", 3), ("gexp_6", 8)]   # soma = BOSS_SLAM_ACTIVE_FRAMES
BARRAGE_CHARGE = [("burst_1", 1), ("burst_2", 1)]
BARRAGE_RELEASE = [("burst_3", 1), ("burst_4", 1), ("burst_5", 1)]
CHARGE_WINDUP = [("chg_0", 1), ("chg_1", 2)]
ORB_WINDUP = [("orb_1", 2), ("orb_2", 2), ("orb_5", 3)]
ORB_RELEASE = [("orb_6", 1), ("orb_3", 1)]
MELEE_WINDUP = [("punch_0", 1), ("punch_1", 2), ("punch_2", 2)]
MELEE_STRIKE = [("punch_3", 1)]
MELEE_RECOVER = [("punch_4", 1)]

CHARGE_LAUNCH = "chg_2"
CHARGE_RUN = ("chg_3", "chg_4", "chg_5")
CHARGE_HIT = "chg_6"
CHARGE_SKID = "chg_7"

# Pose mantida durante a recuperação (RECOVER) de cada ataque
RECOVER_FRAME = {
    "slam": "smash_5",
    "barrage": "burst_6",
    "orb": "orb_7",
    "charge": CHARGE_SKID,
}

# Sequências de impacto dos projéteis: quadros de efeito (IMPACT_FRAME_TICKS cada)
IMPACT_SEQ = {
    "shard": ("fx_star_0", "fx_star_1", "fx_star_2"),
    "orb": ("fx_star_1", "fx_star_2", "fx_puff_0", "fx_puff_1"),
}
IMPACT_FRAME_TICKS = 3
SHARD_SPIN = ("fx_shard_0", "fx_shard_1", "fx_shard_2", "fx_shard_3")
SHARD_SPIN_TICKS = 3

# Tinturas aditivas (RGB somado ao quadro; o alfa é preservado)
TINTS = {
    "hit": (200, 200, 200),          # acerto do jogador
    "tele_slam": (60, 40, 0),        # telegraph do slam
    "tele_barrage": (70, 0, 95),     # telegraph da rajada
    "tele_charge": (0, 65, 85),      # telegraph da investida (azul-ciano)
    "tele_orb": (60, 4, 14),         # telegraph do orbe (vermelho)
    "rage": (16, 0, 3),              # Fase 2: armadura avermelhada
    "rage_flash": (170, 30, 25),     # pisca ao entrar na Fase 2
}


def weighted_frame(table, elapsed, total):
    """Quadro de 'table' ([(nome, peso)]) para 'elapsed' de 'total' ticks."""
    total = max(1, total)
    weights = sum(w for _, w in table)
    pos = max(0, min(total - 1, elapsed)) * weights / total
    acc = 0
    for name, w in table:
        acc += w
        if pos < acc:
            return name
    return table[-1][0]


class BossSprites:
    def __init__(self, frames, manifest):
        self.scale = settings.BOSS_SPRITE_SCALE
        self._frames = frames            # nome -> (Surface, ax, ay)
        self._manifest = manifest["frames"]
        self._cache = {}                 # (nome, flipped, tint, scale) -> (Surface, (ox, oy))
        self._rot_cache = {}             # projéteis girados
        self._glow = None

    def size(self, name):
        return self._frames[name][0].get_size()

    # ---- quadros ----
    def get(self, name, facing_right=True, tint=None, scale=None):
        """Devolve (Surface, (ox, oy)): desenhe em (ref_x + ox, ref_y + oy), onde
        ref = (centro do hitbox, chão) para o corpo, ou o ponto central/base
        do efeito."""
        scale = self.scale if scale is None else scale
        key = (name, facing_right, tint, scale)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        surf, ax, ay = self._frames[name]
        if scale != 1.0:
            w, h = surf.get_size()
            surf = pygame.transform.smoothscale(surf, (max(1, round(w * scale)), max(1, round(h * scale))))
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

    # ---- projéteis ----
    def get_shard(self, tick):
        """Estilhaço da rajada. Gira alternando os 4 quadros de efeito (vertical /
        horizontal), sem rotacionar a imagem; assim parece um cristal girando."""
        name = SHARD_SPIN[(tick // SHARD_SPIN_TICKS) % len(SHARD_SPIN)]
        surf, _off = self.get(name, True, None, settings.BOSS_SHARD_SCALE)
        return surf

    def get_orb(self, vx, vy):
        """Esfera de energia do orbe, com o rastro apontando para trás da trajetória."""
        direction = 1 if vx >= 0 else -1
        ang = int(round(math.degrees(math.atan2(-vy, abs(vx) if vx else 1)) / 5.0)) * 5
        key = (direction, ang)
        surf = self._rot_cache.get(key)
        if surf is None:
            base, _off = self.get("orb_trail", direction > 0, None, settings.BOSS_ORB_SPRITE_SCALE)
            surf = pygame.transform.rotate(base, ang * direction) if ang else base
            self._rot_cache[key] = surf
        return surf

    # ---- aura da Fase 2 ----
    def get_glow(self):
        """Aura vermelha suave (Fase 2), desenhada atrás do corpo."""
        if self._glow is None:
            iw, ih = self.size(IDLE_FRAME)
            w = int(iw * self.scale * 1.25)
            h = int(ih * self.scale * 1.1)
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

    # ---- derivados do manifesto ----
    def orb_spawn_offset(self):
        """(dx, dy) do centro da esfera em relação a (centro do corpo, chão), virado
        para a direita, na escala do jogo. dy é negativo (acima do chão)."""
        info = self._manifest.get("orb_trail", {})
        dx = info.get("dx_from_body", 120.0)
        dy = info.get("dy_from_feet", -85.0)
        return dx * self.scale, dy * self.scale


def _required_names():
    names = set(WALK_FRAMES)
    names |= {IDLE_FRAME, CHARGE_LAUNCH, CHARGE_HIT, CHARGE_SKID, "orb_trail", "orb_round", "fx_embers"}
    for table in (SLAM_WINDUP, SLAM_STRIKE, BARRAGE_CHARGE, BARRAGE_RELEASE, CHARGE_WINDUP,
                  ORB_WINDUP, ORB_RELEASE, MELEE_WINDUP, MELEE_STRIKE, MELEE_RECOVER):
        names.update(n for n, _ in table)
    names.update(CHARGE_RUN)
    names.update(RECOVER_FRAME.values())
    for seq in IMPACT_SEQ.values():
        names.update(seq)
    names.update(SHARD_SPIN)
    return names


_instance = None
_tried = False


def get_boss_sprites():
    """Singleton; None se os quadros não puderem ser carregados (fallback)."""
    global _instance, _tried
    if _tried:
        return _instance
    _tried = True
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        frames = {}
        convert = pygame.display.get_surface() is not None
        for name in _required_names():
            info = manifest["frames"][name]
            surf = pygame.image.load(os.path.join(FRAMES_DIR, info["file"]))
            surf = surf.convert_alpha() if convert else surf
            frames[name] = (surf, info["ax"], info["ay"])
        _instance = BossSprites(frames, manifest)
    except (pygame.error, OSError, KeyError, ValueError):
        _instance = None
    return _instance
