"""
world/checkpoints.py
Checkpoints intermediários espalhados pela Fase 1. Quando Kael toca um
checkpoint pela primeira vez, ele é ativado e passa a ser o novo ponto
de retorno do Núcleo (systems/respawn.py), evitando que o jogador tenha
que percorrer toda a fase novamente a cada morte - uma extensão natural
da mecânica descrita na seção 15 do documento.
"""

import math

import pygame
from config import settings
from world.platforms import _load

# checkpoint.png: o torreão de runas fica maior que o rect de ativação
# (que não muda); a base apoiada no chão, alinhada ao fundo do rect.
CHECKPOINT_VISUAL_HEIGHT = 84
CHECKPOINT_FOOT_OFFSET = 3     # px: base do sprite um pouco abaixo do rect (apoiada na face do chão)
CHECKPOINT_FLAME_ROWS = 70     # linhas nativas do topo do PNG que são a chama
_cp_cache = {}


def _checkpoint_images():
    """(apagado, aceso, brilho). Apagado = sem chama e escurecido; aceso =
    sprite original. Derivados do mesmo PNG, nada de arquivo novo."""
    if not _cp_cache:
        base = _load("checkpoint")
        w = max(1, round(base.get_width() * CHECKPOINT_VISUAL_HEIGHT / base.get_height()))
        on = pygame.transform.smoothscale(base, (w, CHECKPOINT_VISUAL_HEIGHT))
        off = on.copy()
        flame_h = round(CHECKPOINT_FLAME_ROWS * CHECKPOINT_VISUAL_HEIGHT / base.get_height())
        off.fill((0, 0, 0, 0), pygame.Rect(0, 0, w, flame_h))
        off.fill((120, 115, 130, 255), special_flags=pygame.BLEND_RGBA_MULT)
        size = 56
        glow = pygame.Surface((size, size), pygame.SRCALPHA)
        for i in range(size // 2, 0, -2):
            pygame.draw.circle(glow, (255, 110, 60, int(70 * (1 - i / (size / 2)) ** 1.5) + 2),
                               (size // 2, size // 2), i)
        _cp_cache["imgs"] = (off, on, glow, flame_h)
    return _cp_cache["imgs"]



class Checkpoint:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, settings.CHECKPOINT_WIDTH, settings.CHECKPOINT_HEIGHT)
        self.active = False

    def try_activate(self, player):
        """Retorna True apenas no momento em que é ativado pela primeira vez."""
        if not self.active and self.rect.colliderect(player.rect):
            self.active = True
            return True
        return False

    def player_in_shop_range(self, player):
        """Todo checkpoint já ativado também funciona como acesso à loja,
        não só a zona fixa da Região 1 - assim o jogador não precisa
        voltar lá toda vez que quiser gastar moedas. A zona é um pouco
        maior que o poste em si, pra não exigir sobreposição exata."""
        if not self.active:
            return False
        zone = self.rect.inflate(
            settings.CHECKPOINT_SHOP_RANGE_PADDING_X * 2,
            settings.CHECKPOINT_SHOP_RANGE_PADDING_Y * 2,
        )
        return zone.colliderect(player.rect)

    def respawn_point(self):
        return (self.rect.centerx - settings.PLAYER_WIDTH // 2, self.rect.bottom - settings.PLAYER_HEIGHT)

    def _draw_sprite(self, surface, r):
        if _load("checkpoint") is None:
            return False
        off, on, glow, flame_h = _checkpoint_images()
        img = on if self.active else off
        x = r.centerx - img.get_width() // 2
        y = r.bottom + CHECKPOINT_FOOT_OFFSET - img.get_height()
        if self.active:
            # brilho pulsante atrás da chama (só visual)
            pulse = 0.85 + 0.15 * math.sin(pygame.time.get_ticks() * 0.008)
            g = pygame.transform.smoothscale(glow, (round(glow.get_width() * pulse),) * 2)
            surface.blit(g, (r.centerx - g.get_width() // 2, y + flame_h // 2 - g.get_height() // 2))
        surface.blit(img, (x, y))
        return True

    def draw(self, surface, camera_x):
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        if self._draw_sprite(surface, r):
            return
        color = settings.COLOR_CHECKPOINT_ON if self.active else settings.COLOR_CHECKPOINT_OFF
        pygame.draw.rect(surface, color, r, border_radius=4)
        pygame.draw.rect(surface, (230, 230, 235), r, width=2, border_radius=4)
        # bandeira simples no topo
        flag_points = [(r.centerx, r.top), (r.centerx + 14, r.top + 8), (r.centerx, r.top + 16)]
        pygame.draw.polygon(surface, color, flag_points)
