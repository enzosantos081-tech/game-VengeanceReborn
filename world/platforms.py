"""
world/platforms.py
Responsável pelas plataformas do cenário: chão/blocos estáticos,
plataformas móveis (vaivém entre dois pontos) e plataformas
quebradiças (despencam pouco depois do jogador pisar e reaparecem
depois de um tempo). A colisão real é resolvida por systems/collision.py;
aqui vivem apenas o estado e o desenho de cada tipo.
"""

import pygame
from config import settings


class Platform:
    """Plataforma estática (chão ou bloco fixo)."""

    def __init__(self, x, y, width, height, is_ground=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.is_ground = is_ground
        self.delta_x = 0  # plataformas estáticas nunca "carregam" o jogador

    def update(self):
        pass

    def is_solid(self):
        return True

    def draw(self, surface, camera_x):
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        color = settings.COLOR_GROUND if self.is_ground else settings.COLOR_PLATFORM
        top_color = settings.COLOR_GROUND_TOP if self.is_ground else (
            min(settings.COLOR_PLATFORM[0] + 25, 255),
            min(settings.COLOR_PLATFORM[1] + 25, 255),
            min(settings.COLOR_PLATFORM[2] + 25, 255),
        )
        pygame.draw.rect(surface, color, r)
        pygame.draw.rect(surface, top_color, (r.x, r.y, r.width, 6))


class MovingPlatform(Platform):
    """Plataforma que se move em vaivém entre o ponto inicial e um ponto
    deslocado por (offset_x, offset_y). O jogador é "carregado" junto
    quando está em cima dela (ver world/level.py -> move_and_collide)."""

    def __init__(self, x, y, width, height, offset_x=0, offset_y=0, speed=None):
        super().__init__(x, y, width, height, is_ground=False)
        self.start_x = x
        self.start_y = y
        self.end_x = x + offset_x
        self.end_y = y + offset_y
        self.speed = speed if speed is not None else settings.MOVING_PLATFORM_SPEED
        self.progress = 0.0
        self.direction = 1
        self.delta_x = 0
        self.delta_y = 0

    def update(self):
        total_dist = max(1.0, ((self.end_x - self.start_x) ** 2 + (self.end_y - self.start_y) ** 2) ** 0.5)
        step = self.speed / total_dist
        self.progress += step * self.direction
        if self.progress >= 1.0:
            self.progress = 1.0
            self.direction = -1
        elif self.progress <= 0.0:
            self.progress = 0.0
            self.direction = 1

        old_x, old_y = self.rect.x, self.rect.y
        self.rect.x = round(self.start_x + (self.end_x - self.start_x) * self.progress)
        self.rect.y = round(self.start_y + (self.end_y - self.start_y) * self.progress)
        self.delta_x = self.rect.x - old_x
        self.delta_y = self.rect.y - old_y

    def draw(self, surface, camera_x):
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        pygame.draw.rect(surface, settings.COLOR_MOVING_PLATFORM, r, border_radius=4)
        pygame.draw.rect(surface, (120, 160, 190), (r.x, r.y, r.width, 5))


class CrumblingPlatform(Platform):
    """Plataforma que treme e despenca pouco depois do jogador pisar
    nela, e reaparece automaticamente depois de um tempo."""

    STATE_IDLE = "idle"
    STATE_SHAKING = "shaking"
    STATE_GONE = "gone"

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, is_ground=False)
        self.state = CrumblingPlatform.STATE_IDLE
        self.timer = 0
        self.delta_x = 0

    def is_solid(self):
        return self.state != CrumblingPlatform.STATE_GONE

    def trigger(self):
        if self.state == CrumblingPlatform.STATE_IDLE:
            self.state = CrumblingPlatform.STATE_SHAKING
            self.timer = settings.CRUMBLE_SHAKE_FRAMES

    def update(self):
        if self.state == CrumblingPlatform.STATE_SHAKING:
            self.timer -= 1
            if self.timer <= 0:
                self.state = CrumblingPlatform.STATE_GONE
                self.timer = settings.CRUMBLE_RESPAWN_FRAMES
        elif self.state == CrumblingPlatform.STATE_GONE:
            self.timer -= 1
            if self.timer <= 0:
                self.state = CrumblingPlatform.STATE_IDLE

    def draw(self, surface, camera_x):
        if self.state == CrumblingPlatform.STATE_GONE:
            return
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        offset = 0
        color = settings.COLOR_CRUMBLING_PLATFORM
        if self.state == CrumblingPlatform.STATE_SHAKING:
            import random
            offset = random.randint(-2, 2)
            fade = self.timer / settings.CRUMBLE_SHAKE_FRAMES
            color = (
                int(color[0] * fade + 200 * (1 - fade)),
                int(color[1] * fade + 60 * (1 - fade)),
                int(color[2] * fade + 60 * (1 - fade)),
            )
        pygame.draw.rect(surface, color, (r.x + offset, r.y, r.width, r.height))
        pygame.draw.rect(surface, (150, 110, 80), (r.x + offset, r.y, r.width, 5))


class PlatformGroup:
    def __init__(self):
        self.platforms = []

    def add(self, x, y, width, height, is_ground=False):
        p = Platform(x, y, width, height, is_ground)
        self.platforms.append(p)
        return p

    def add_moving(self, x, y, width, height, offset_x=0, offset_y=0, speed=None):
        p = MovingPlatform(x, y, width, height, offset_x, offset_y, speed)
        self.platforms.append(p)
        return p

    def add_crumbling(self, x, y, width, height):
        p = CrumblingPlatform(x, y, width, height)
        self.platforms.append(p)
        return p

    def update(self):
        for p in self.platforms:
            p.update()

    def rects(self):
        """Retornados apenas os sólidos no momento (plataformas quebradiças
        já despencadas não bloqueiam o movimento)."""
        return [p.rect for p in self.platforms if p.is_solid()]

    def moving_platforms(self):
        return [p for p in self.platforms if isinstance(p, MovingPlatform)]

    def crumbling_at(self, rect):
        """Retorna a plataforma quebradiça que colide com o retângulo dado
        (usada para disparar o tremor quando o jogador pisa nela)."""
        for p in self.platforms:
            if isinstance(p, CrumblingPlatform) and p.is_solid() and rect.colliderect(p.rect):
                return p
        return None

    def draw(self, surface, camera_x):
        for p in self.platforms:
            p.draw(surface, camera_x)
