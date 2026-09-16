"""
world/checkpoints.py
Checkpoints intermediários espalhados pela Fase 1. Quando Kael toca um
checkpoint pela primeira vez, ele é ativado e passa a ser o novo ponto
de retorno do Núcleo (systems/respawn.py), evitando que o jogador tenha
que percorrer toda a fase novamente a cada morte - uma extensão natural
da mecânica descrita na seção 15 do documento.
"""

import pygame
from config import settings


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

    def draw(self, surface, camera_x):
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        color = settings.COLOR_CHECKPOINT_ON if self.active else settings.COLOR_CHECKPOINT_OFF
        pygame.draw.rect(surface, color, r, border_radius=4)
        pygame.draw.rect(surface, (230, 230, 235), r, width=2, border_radius=4)
        # bandeira simples no topo
        flag_points = [(r.centerx, r.top), (r.centerx + 14, r.top + 8), (r.centerx, r.top + 16)]
        pygame.draw.polygon(surface, color, flag_points)
