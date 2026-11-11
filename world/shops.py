"""
world/shops.py
Barraca de loja (sprite assets/images/shop.png) posicionada no cenário.

A loja é puramente decorativa + uma zona de interação (ShopZone, de
systems/shop.py): não tem colisão sólida, então nunca bloqueia a passagem.
Os checkpoints só salvam o progresso; a compra acontece SOMENTE aqui.
"""

import pygame
from config import settings
from systems.shop import ShopZone
from world.platforms import _load

_shop_cache = {}


def _shop_image():
    """Sprite redimensionada uma única vez para a altura de exibição,
    mantendo a proporção original (sem distorção)."""
    if "img" not in _shop_cache:
        base = _load("shop")
        if base is None:
            _shop_cache["img"] = None
        else:
            h = settings.SHOP_VISUAL_HEIGHT
            w = max(1, round(base.get_width() * h / base.get_height()))
            _shop_cache["img"] = pygame.transform.smoothscale(base, (w, h))
    return _shop_cache["img"]


def shop_visual_width():
    img = _shop_image()
    return img.get_width() if img else settings.SHOP_FALLBACK_WIDTH


class ShopStall:
    def __init__(self, center_x, ground_y):
        self.center_x = round(center_x)
        self.ground_y = ground_y
        w = settings.SHOP_INTERACT_WIDTH
        h = settings.SHOP_INTERACT_HEIGHT
        # Zona onde o jogador pode abrir a loja: o balcão, ao nível do chão.
        self.zone = ShopZone(self.center_x - w // 2, ground_y - h, w, h)

    @property
    def rect(self):
        return self.zone.rect

    def player_in_range(self, player):
        return self.zone.player_in_range(player)

    def draw(self, surface, camera_x):
        img = _shop_image()
        if img is None:
            r = self.zone.rect.move(-camera_x, 0)
            if r.right > 0 and r.left < settings.SCREEN_WIDTH:
                pygame.draw.rect(surface, (70, 40, 50), r, border_radius=4)
                pygame.draw.rect(surface, (150, 90, 100), r, width=2, border_radius=4)
            return
        x = self.center_x - img.get_width() // 2 - camera_x
        if x + img.get_width() < 0 or x > settings.SCREEN_WIDTH:
            return
        # base de pedra levemente "enterrada" na face do chão: sem flutuar
        y = self.ground_y + settings.SHOP_FOOT_OFFSET - img.get_height()
        surface.blit(img, (x, y))
