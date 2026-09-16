"""
player/player_sprites.py
Carrega e gerencia as animações do sprite do Kael, extraídas da sprite
sheet fornecida (assets/player/*.png - fundo já removido/transparente).

Cada animação é uma lista de frames (pygame.Surface) com uma duração
(em frames de jogo) por imagem. O sprite original olha para a DIREITA
por padrão; quando o personagem está olhando pra esquerda, o frame é
espelhado na hora de desenhar (ver SpriteAnimator.get_frame).

As dimensões de colisão do jogador (player.rect) continuam exatamente
as mesmas de antes - isso aqui é só a camada visual, desenhada por
cima/ao redor do hitbox, então não afeta física nem colisão.
"""

import os
import pygame

_ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "player")

# Escala aplicada a todos os frames (extraídos em alta resolução da
# sprite sheet original). Um único fator uniforme preserva a proporção
# entre frames diferentes (ex: braço erguido no ataque vs parado no idle).
SPRITE_SCALE = 0.42

# Nome da animação -> (lista de nomes de arquivo sem extensão, duração em frames por imagem)
_ANIMATION_DEFS = {
    "idle": (["idle_0", "idle_1"], 22),
    "run": (["run_0", "run_1", "run_2", "run_3", "run_4", "run_5", "run_6", "run_7"], 6),
    "jump": (["jump_0"], 8),
    "fall": (["fall_0"], 8),
    "wallslide": (["wallslide_0"], 8),
    "dash": (["dash_0", "dash_1", "dash_2", "dash_3"], 4),
    "attack": (["attack_0", "attack_1", "attack_2", "attack_3"], 5),
    "death": (["death_0"], 10),
}

_cache = None  # {anim_name: {"frames": [Surface,...], "flipped": [Surface,...], "duration": int}}


def _load_all():
    global _cache
    if _cache is not None:
        return _cache
    _cache = {}
    for anim_name, (filenames, duration) in _ANIMATION_DEFS.items():
        frames = []
        flipped = []
        for fname in filenames:
            path = os.path.join(_ASSET_DIR, f"{fname}.png")
            raw = pygame.image.load(path).convert_alpha()
            if SPRITE_SCALE != 1.0:
                w = max(1, round(raw.get_width() * SPRITE_SCALE))
                h = max(1, round(raw.get_height() * SPRITE_SCALE))
                raw = pygame.transform.scale(raw, (w, h))
            frames.append(raw)
            flipped.append(pygame.transform.flip(raw, True, False))
        _cache[anim_name] = {"frames": frames, "flipped": flipped, "duration": duration}
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
            self.frame_index = (self.frame_index + 1) % len(anim["frames"])

    def get_surface(self, facing_right):
        anims = _load_all()
        anim = anims.get(self.state, anims["idle"])
        idx = min(self.frame_index, len(anim["frames"]) - 1)
        return anim["frames"][idx] if facing_right else anim["flipped"][idx]
