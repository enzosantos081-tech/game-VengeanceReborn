"""
world/obstacles.py
Responsável por obstáculos que causam dano ao jogador por contato,
como espinhos. Buracos não precisam de uma classe própria: são apenas
a ausência de plataforma, tratados pela verificação de queda em
player.py (rect.top > level.height).
"""

import pygame
from config import settings
from world.platforms import _load, _scaled

# spike.png: aglomerado de espinhos com pedras na base (729x468 nativos).
# Antes a altura visual era hitbox_h * 1.25 (= 20 px para a hitbox de 16 px),
# o que deixava o sprite minúsculo. Agora a altura visual é independente da
# hitbox: SPIKE_VISUAL_HEIGHT_FACTOR * altura da hitbox (16 -> 40 px). A
# hitbox (self.rect) NÃO muda - só o desenho cresceu, apoiado na base dela.
SPIKE_VISUAL_HEIGHT_FACTOR = 4
# Em hitboxes estreitas (ex: 32 px) o sprite, mantendo a proporção, fica mais
# largo que a hitbox. Ele pode sobrar um pouco pros lados (centrado), mas
# nunca encolhe abaixo dessa fração da largura ideal (evita sprite espremido).
SPIKE_MIN_TILE_FRACTION = 0.8
SPIKE_SINK = 2      # px que a base (pedras) entra no chão, pra não parecer flutuando
_spike_cache = {}


def _spike_strip(length, thickness):
    """Faixa de espinhos para uma hitbox de 'length' x 'thickness' px, ponta
    pra cima, feita de peças do spike.png na proporção original (alternando
    espelhadas pra não repetir igual). Retorna (surface, margem): a faixa tem
    'margem' px extras de cada lado do comprimento da hitbox (sobra do sprite
    em hitboxes estreitas); o chamador desloca o blit por essa margem."""
    key = (length, thickness)
    if key not in _spike_cache:
        base = _load("spike")
        aspect = base.get_width() / base.get_height()
        vis_h = thickness * SPIKE_VISUAL_HEIGHT_FACTOR
        ideal_w = vis_h * aspect
        n = max(1, int(length / ideal_w + 0.5))
        step = length / n
        tw = max(1, round(max(step, ideal_w * SPIKE_MIN_TILE_FRACTION)))
        th = max(1, round(tw / aspect))
        margin = max(0, int(round((tw - step) / 2)))
        tile = _scaled("spike", (tw, th))
        mirrored = pygame.transform.flip(tile, True, False)
        strip = pygame.Surface((length + 2 * margin, th), pygame.SRCALPHA)
        for i in range(n):
            x = margin + round((i + 0.5) * step - tw / 2)
            strip.blit(mirrored if i % 2 else tile, (x, 0))
        _spike_cache[key] = (strip, margin)
    return _spike_cache[key]


class Spike:
    def __init__(self, x, y, width=32, height=16, facing="up"):
        # Espinhos de chão ("up") ficam grudados no topo do chão.
        # Espinhos de parede ("left"/"right") ficam grudados numa parede
        # vertical. Espinhos de teto ("down") pendem de cima (ex:
        # estalactites). Todas as orientações são suportadas de forma
        # genérica, mesmo que não estejam todas em uso no momento.
        self.rect = pygame.Rect(x, y, width, height)
        self.facing = facing

    def check_damage(self, player):
        if player.alive and self.rect.colliderect(player.rect):
            direction = 1 if player.rect.centerx > self.rect.centerx else -1
            player.take_damage(settings.SPIKE_DAMAGE, knockback_dir=direction)

    def _draw_sprite(self, surface, r):
        if _load("spike") is None:
            return False
        if self.facing == "up":
            strip, m = _spike_strip(r.width, r.height)
            surface.blit(strip, (r.x - m, r.bottom + SPIKE_SINK - strip.get_height()))
        elif self.facing == "down":
            strip, m = _spike_strip(r.width, r.height)
            surface.blit(pygame.transform.flip(strip, False, True), (r.x - m, r.y - SPIKE_SINK))
        elif self.facing == "right":   # parede à esquerda, pontas pra direita
            strip, m = _spike_strip(r.height, r.width)
            img = pygame.transform.rotate(strip, -90)
            surface.blit(img, (r.x - SPIKE_SINK, r.y - m))
        else:                          # "left": parede à direita, pontas pra esquerda
            strip, m = _spike_strip(r.height, r.width)
            img = pygame.transform.rotate(strip, 90)
            surface.blit(img, (r.right + SPIKE_SINK - img.get_width(), r.y - m))
        return True

    def draw(self, surface, camera_x):
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        if self._draw_sprite(surface, r):
            return
        if self.facing in ("up", "down"):
            # Fileira de triângulos apontando para cima (chão) ou para
            # baixo (teto/estalactite) - mesma lógica, só inverte o eixo Y.
            n = max(1, r.width // 16)
            seg_w = r.width / n
            for i in range(n):
                x0 = r.x + i * seg_w
                if self.facing == "up":
                    points = [(x0, r.bottom), (x0 + seg_w / 2, r.top), (x0 + seg_w, r.bottom)]
                else:
                    points = [(x0, r.top), (x0 + seg_w / 2, r.bottom), (x0 + seg_w, r.top)]
                pygame.draw.polygon(surface, settings.COLOR_SPIKE, points)
        else:
            # Fileira de triângulos apontando para o lado (grudados numa parede)
            n = max(1, r.height // 16)
            seg_h = r.height / n
            for i in range(n):
                y0 = r.y + i * seg_h
                if self.facing == "right":
                    # parede fica à esquerda do vão; espinhos apontam p/ direita
                    points = [(r.left, y0), (r.right, y0 + seg_h / 2), (r.left, y0 + seg_h)]
                else:  # "left": parede fica à direita do vão; espinhos apontam p/ esquerda
                    points = [(r.right, y0), (r.left, y0 + seg_h / 2), (r.right, y0 + seg_h)]
                pygame.draw.polygon(surface, settings.COLOR_SPIKE, points)


class Stalactite:
    """Estalactite-armadilha: parada (IDLE) até o jogador passar bem por
    baixo dela -> treme como aviso (SHAKE) -> cai acelerando com a
    mesma gravidade do resto do jogo (FALLING), causando dano se
    acertar o jogador -> some e depois de um tempo volta ao lugar
    original (IDLE de novo). Reaproveita settings.GRAVITY e
    settings.SPIKE_DAMAGE - não é um sistema de física novo, só usa os
    mesmos números que o resto do jogo já usa."""

    STATE_IDLE = "idle"
    STATE_SHAKE = "shake"
    STATE_FALLING = "falling"
    STATE_GONE = "gone"

    SHAKE_FRAMES = 26        # aviso tremendo antes de cair (~0.43s a 60fps)
    RESPAWN_FRAMES = 210     # tempo até reaparecer depois de cair (~3.5s)

    def __init__(self, x, y, width=32, height=40, trigger_range=36):
        self.spawn_rect = pygame.Rect(x, y, width, height)
        self.rect = self.spawn_rect.copy()
        self.state = Stalactite.STATE_IDLE
        self.shake_timer = 0
        self.respawn_timer = 0
        self.vel_y = 0.0
        self.trigger_range = trigger_range
        self.already_hit = False

    def update(self, player, ground_y=None):
        if self.state == Stalactite.STATE_IDLE:
            if (player.alive
                    and player.rect.centery > self.rect.bottom
                    and abs(player.rect.centerx - self.rect.centerx) <= self.trigger_range):
                self.state = Stalactite.STATE_SHAKE
                self.shake_timer = Stalactite.SHAKE_FRAMES

        elif self.state == Stalactite.STATE_SHAKE:
            self.shake_timer -= 1
            if self.shake_timer <= 0:
                self.state = Stalactite.STATE_FALLING
                self.vel_y = 1.0
                self.already_hit = False

        elif self.state == Stalactite.STATE_FALLING:
            self.vel_y += settings.GRAVITY
            self.rect.y += round(self.vel_y)

            if not self.already_hit and player.alive and self.rect.colliderect(player.rect):
                direction = 1 if player.rect.centerx > self.rect.centerx else -1
                player.take_damage(settings.SPIKE_DAMAGE, knockback_dir=direction)
                self.already_hit = True

            floor = ground_y if ground_y is not None else (self.spawn_rect.y + 600)
            if self.rect.top > floor + 100:
                self.state = Stalactite.STATE_GONE
                self.respawn_timer = Stalactite.RESPAWN_FRAMES

        elif self.state == Stalactite.STATE_GONE:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self.rect = self.spawn_rect.copy()
                self.vel_y = 0.0
                self.state = Stalactite.STATE_IDLE

    def draw(self, surface, camera_x):
        if self.state == Stalactite.STATE_GONE:
            return
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return

        shake_x = 0
        if self.state == Stalactite.STATE_SHAKE:
            shake_x = 2 if (self.shake_timer // 3) % 2 == 0 else -2

        n = max(1, r.width // 16)
        seg_w = r.width / n
        for i in range(n):
            x0 = r.x + i * seg_w + shake_x
            points = [(x0, r.top), (x0 + seg_w / 2, r.bottom), (x0 + seg_w, r.top)]
            pygame.draw.polygon(surface, settings.COLOR_SPIKE, points)


class ObstacleGroup:
    def __init__(self):
        self.spikes = []
        self.stalactites = []

    def add_spike(self, x, y, width=32, height=16):
        s = Spike(x, y, width, height, facing="up")
        self.spikes.append(s)
        return s

    def add_wall_spike(self, x, y, width, height, facing):
        """Espinhos grudados numa parede vertical. facing='right' se a
        parede fica à ESQUERDA do vão (espinhos apontam p/ direita);
        facing='left' se a parede fica à DIREITA do vão."""
        s = Spike(x, y, width, height, facing=facing)
        self.spikes.append(s)
        return s

    def add_ceiling_spike(self, x, y, width=32, height=16):
        """Estalactite decorativa/fixa: pende do teto, apontando para
        baixo, mas não cai (só machuca por contato direto, como
        qualquer outro espinho). Para a estalactite que CAI quando o
        jogador passa por baixo, use add_stalactite() abaixo."""
        s = Spike(x, y, width, height, facing="down")
        self.spikes.append(s)
        return s

    def add_stalactite(self, x, y, width=32, height=40, trigger_range=36):
        """Estalactite-armadilha: fica parada até o jogador passar bem
        por baixo dela, treme por um instante como aviso, e então cai
        (com a mesma gravidade do resto do jogo) até o chão, causando
        dano se acertar o jogador no caminho. Depois de cair, some e
        reaparece no lugar original depois de um tempo."""
        s = Stalactite(x, y, width, height, trigger_range=trigger_range)
        self.stalactites.append(s)
        return s

    def update(self, player, ground_y=None):
        for s in self.spikes:
            s.check_damage(player)
        for st in self.stalactites:
            st.update(player, ground_y=ground_y)

    def draw(self, surface, camera_x):
        for s in self.spikes:
            s.draw(surface, camera_x)
        for st in self.stalactites:
            st.draw(surface, camera_x)
