"""
world/coins.py
Responsável pelas moedas coletáveis: recompensa pela exploração e
recurso para comprar melhorias na loja. Moedas coletadas permanecem
coletadas até a fase reiniciar (systems/respawn.py cuida de resetá-las
apenas quando o jogador retorna ao Núcleo após a morte, conforme a
regra "mantém progresso" do documento).
"""

import math
import pygame
from config import settings


class Coin:
    def __init__(self, x, y, value=settings.COIN_VALUE):
        self.rect = pygame.Rect(x, y, 16, 16)
        self.value = value
        self.collected = False
        self._bob_offset = 0.0

    def update(self):
        self._bob_offset += 0.12

    def draw(self, surface, camera_x):
        if self.collected:
            return
        bob = math.sin(self._bob_offset) * 3
        r = self.rect.move(-camera_x, int(bob))
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        pygame.draw.circle(surface, settings.COLOR_COIN, r.center, 8)
        pygame.draw.circle(surface, (180, 140, 20), r.center, 8, width=2)


class CoinGroup:
    def __init__(self):
        self.coins = []

    def add(self, x, y, value=settings.COIN_VALUE):
        c = Coin(x, y, value)
        self.coins.append(c)
        return c

    def update(self, player, particles=None):
        collected_value = 0
        magnet_radius = settings.COIN_MAGNET_RADIUS if player.stats.magnet_level else 0
        for c in self.coins:
            c.update()
            if c.collected:
                continue
            if magnet_radius and player.alive:
                dx = player.rect.centerx - c.rect.centerx
                dy = player.rect.centery - c.rect.centery
                dist_sq = dx * dx + dy * dy
                if dist_sq <= magnet_radius * magnet_radius:
                    dist = max(1.0, dist_sq ** 0.5)
                    pull = settings.COIN_MAGNET_PULL_SPEED
                    c.rect.x += round(dx / dist * pull)
                    c.rect.y += round(dy / dist * pull)
            if player.alive and c.rect.colliderect(player.rect):
                c.collected = True
                collected_value += c.value
                if particles:
                    particles.emit_coin(c.rect.centerx, c.rect.centery)
        if collected_value:
            player.stats.add_coins(collected_value)
        return collected_value

    def reset(self):
        """Reaparecem apenas as moedas ainda não gastas visualmente - na
        prática, como o valor já foi somado ao PlayerStats (que persiste),
        as moedas coletadas permanecem coletadas. Usado apenas se o design
        futuro exigir reset total de fase."""
        for c in self.coins:
            c.collected = False

    def draw(self, surface, camera_x):
        for c in self.coins:
            c.draw(surface, camera_x)
