"""
world/obstacles.py
Responsável por obstáculos que causam dano ao jogador por contato,
como espinhos. Buracos não precisam de uma classe própria: são apenas
a ausência de plataforma, tratados pela verificação de queda em
player.py (rect.top > level.height).
"""

import os
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
    def __init__(self, x, y, width=32, height=16, facing="up", variant=1):
        # Espinhos de chão ("up") ficam no topo do chão; os de teto
        # ("down") pendem de cima, como estalactites fixas.
        self.rect = pygame.Rect(x, y, width, height)
        self.facing = facing
        self.variant = max(1, min(4, int(variant)))

    def check_damage(self, player):
        if player.alive and self.rect.colliderect(player.rect):
            direction = 1 if player.rect.centerx > self.rect.centerx else -1
            player.take_damage(settings.SPIKE_DAMAGE, knockback_dir=direction)

    def _draw_sprite(self, surface, r):
        if self.facing == "up":
            if _load("spike") is None:
                return False
            strip, m = _spike_strip(r.width, r.height)
            surface.blit(strip, (r.x - m, r.bottom + SPIKE_SINK - strip.get_height()))
            return True

        # Espinhos de teto usam os novos sprites rochosos, não o sprite de
        # espinhos de chão invertido. A hitbox continua independente do visual.
        sprite = Stalactite._load_sprite(self.variant)
        if sprite is None:
            return False
        visual_h = max(72, r.height)
        visual_w = max(r.width, round(visual_h * sprite.get_width() / sprite.get_height()))
        size = (visual_w, visual_h)
        key = (self.variant, size)
        if key not in Stalactite._scaled_cache:
            Stalactite._scaled_cache[key] = pygame.transform.smoothscale(sprite, size)
        surface.blit(Stalactite._scaled_cache[key], (r.centerx - visual_w // 2, r.y))
        return True

    def draw(self, surface, camera_x):
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        if self._draw_sprite(surface, r):
            return
        # Fileira de triângulos apontando para cima (chão) ou para baixo
        # (teto/estalactites), sem orientações laterais associadas a paredes.
        n = max(1, r.width // 16)
        seg_w = r.width / n
        for i in range(n):
            x0 = r.x + i * seg_w
            if self.facing == "up":
                points = [(x0, r.bottom), (x0 + seg_w / 2, r.top), (x0 + seg_w, r.bottom)]
            else:
                points = [(x0, r.top), (x0 + seg_w / 2, r.bottom), (x0 + seg_w, r.top)]
            pygame.draw.polygon(surface, settings.COLOR_SPIKE, points)


class Stalactite:
    """Estalactite visual do asset pack: espera no teto, treme como aviso,
    cai usando a gravidade do jogo e fica no local após atingir uma superfície.

    A posição (x, y) recebida é o canto superior esquerdo visual no mundo.
    A hitbox é menor que o sprite e fica alinhada à parte inferior da pedra,
    evitando que áreas transparentes contem como colisão.
    """

    STATE_IDLE = "idle"
    STATE_SHAKE = "shake"
    STATE_FALLING = "falling"
    STATE_LANDED = "landed"
    STATE_FADING = "fading"
    STATE_GONE = "gone"

    SHAKE_FRAMES = 26        # aviso de ~0,43 s a 60 FPS
    VISUAL_HEIGHT_FACTOR = 2.15
    # A hitbox acompanha melhor o volume visível da pedra. Mantemos uma
    # pequena margem transparente nas bordas, mas cobrimos quase toda a
    # largura e altura da formação, inclusive nas variantes maiores.
    HITBOX_WIDTH_FACTOR = 0.78
    HITBOX_HEIGHT_FACTOR = 0.88
    _sprite_cache = {}
    _scaled_cache = {}

    @classmethod
    def _load_sprite(cls, variant):
        if variant not in cls._sprite_cache:
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets", "images", f"stalactite_{variant}.png"
            )
            try:
                cls._sprite_cache[variant] = pygame.image.load(path).convert_alpha()
            except (pygame.error, FileNotFoundError):
                cls._sprite_cache[variant] = None
        return cls._sprite_cache[variant]

    def __init__(self, x, y, width=32, height=40, trigger_range=36, variant=1,
                 visual_size=None, fall_to_y=None, trigger_on_death_zone=None,
                 persistent_after_landing=False):
        self.anchor_x = float(x + width / 2)
        self.spawn_y = float(y)
        self.y = float(y)
        self.trigger_range = trigger_range
        self.variant = max(1, min(4, int(variant)))
        # Parâmetros opcionais usados pelo puzzle da fenda: a grande pedra só
        # cai quando o jogador morre dentro do buraco e pousa numa altura
        # inferior à tela, formando uma plataforma permanente.
        self.fall_to_y = float(fall_to_y) if fall_to_y is not None else None
        self.trigger_on_death_zone = trigger_on_death_zone
        # A estalactite do puzzle é explicitamente permanente; as normais
        # desaparecem dois segundos depois de pousar.
        self.persistent_after_landing = bool(persistent_after_landing)
        self.triggered_by_death = False
        self.state = Stalactite.STATE_IDLE
        self.shake_timer = 0
        self.landed_timer = 60   # 1 segundo a 60 FPS antes de começar a sumir
        self.fade_timer = 18     # transição suave de 0,3 s
        self.respawn_timer = 0
        self.vel_y = 0.0
        self.already_hit = False

        sprite = self._load_sprite(self.variant)
        if visual_size is not None:
            self.visual_width = max(1, int(visual_size[0]))
            self.visual_height = max(1, int(visual_size[1]))
        elif sprite is not None:
            aspect = sprite.get_width() / max(1, sprite.get_height())
            self.visual_height = max(82, int(height * self.VISUAL_HEIGHT_FACTOR))
            self.visual_width = max(48, int(self.visual_height * aspect))
        else:
            self.visual_height = max(40, int(height * self.VISUAL_HEIGHT_FACTOR))
            self.visual_width = max(32, int(width * 2))
        self._update_rect()

    def _update_rect(self):
        """Atualiza a hitbox a partir da posição visual atual."""
        hit_w = max(20, int(self.visual_width * self.HITBOX_WIDTH_FACTOR))
        hit_h = max(28, int(self.visual_height * self.HITBOX_HEIGHT_FACTOR))
        # A ponta inferior é a região mais perigosa, mas a hitbox começa
        # perto do topo para acompanhar o tamanho real do sprite.
        hit_top = self.y + int(self.visual_height * (1.0 - self.HITBOX_HEIGHT_FACTOR))
        self.rect = pygame.Rect(
            round(self.anchor_x - hit_w / 2), round(hit_top), hit_w, hit_h
        )

    def update(self, player, ground_y=None, solids=None):
        if self.state == Stalactite.STATE_IDLE:
            # Puzzle especial: a pedra gigante só é acionada quando Kael
            # morre por cair dentro da fenda marcada. O estado fica salvo
            # durante a tela de morte e continua caindo após o respawn.
            if self.trigger_on_death_zone and not self.triggered_by_death:
                zone_left, zone_right = self.trigger_on_death_zone
                died_in_pit = (
                    not player.alive
                    and zone_left <= player.rect.centerx <= zone_right
                )
                if died_in_pit:
                    self.triggered_by_death = True
                    self.state = Stalactite.STATE_SHAKE
                    self.shake_timer = Stalactite.SHAKE_FRAMES
            else:
                # Armadilhas normais ativam quando o jogador passa por baixo.
                # A largura visual permite ativar também pelas laterais.
                visual_left = self.anchor_x - self.visual_width / 2 - self.trigger_range
                visual_right = self.anchor_x + self.visual_width / 2 + self.trigger_range
                player_is_under = (
                    player.rect.right >= visual_left
                    and player.rect.left <= visual_right
                    and player.rect.top >= self.y + self.visual_height * 0.45
                )
                if player.alive and player_is_under:
                    self.state = Stalactite.STATE_SHAKE
                    self.shake_timer = Stalactite.SHAKE_FRAMES

        elif self.state == Stalactite.STATE_SHAKE:
            self.shake_timer -= 1
            if self.shake_timer <= 0:
                self.state = Stalactite.STATE_FALLING
                self.vel_y = 1.0
                self.already_hit = False

        elif self.state == Stalactite.STATE_FALLING:
            previous_bottom = self.rect.bottom
            self.vel_y += settings.GRAVITY
            self.y += self.vel_y
            self._update_rect()

            if not self.already_hit and player.alive and self.rect.colliderect(player.rect):
                direction = 1 if player.rect.centerx > self.rect.centerx else -1
                player.take_damage(settings.SPIKE_DAMAGE, knockback_dir=direction)
                self.already_hit = True

            # A estalactite pousa sobre plataformas sólidas quando cruza o topo
            # delas durante a queda, sem atravessar o chão ou plataformas elevadas.
            landed_on = None
            # A pedra do puzzle cai deliberadamente para dentro do vazio;
            # não pode pousar na borda do buraco por causa da largura do sprite.
            if self.fall_to_y is None and solids:
                for solid in solids:
                    if (self.rect.right > solid.left and self.rect.left < solid.right
                            and previous_bottom <= solid.top <= self.rect.bottom):
                        if landed_on is None or solid.top < landed_on.top:
                            landed_on = solid
            floor = ground_y if ground_y is not None else (self.spawn_y + 600)
            landing_y = self.fall_to_y if self.fall_to_y is not None else (landed_on.top if landed_on is not None else floor)
            if self.rect.bottom >= landing_y:
                self.y = landing_y - self.visual_height
                self.vel_y = 0.0
                self._update_rect()
                self.state = Stalactite.STATE_LANDED
                self.landed_timer = 60  # 1 segundo antes da transição de desaparecimento
                self.fade_timer = 18

        elif self.state == Stalactite.STATE_LANDED:
            # A pedra especial do puzzle permanece como plataforma. As normais
            # aguardam 1 segundo após pousar e então desaparecem suavemente.
            if not self.persistent_after_landing:
                self.landed_timer -= 1
                if self.landed_timer <= 0:
                    self.state = Stalactite.STATE_FADING
                    self.fade_timer = 18

        elif self.state == Stalactite.STATE_FADING:
            self.fade_timer -= 1
            if self.fade_timer <= 0:
                self.state = Stalactite.STATE_GONE

        elif self.state == Stalactite.STATE_GONE:
            # Desaparecida: não reaparece automaticamente.
            pass

    def platform_rect(self):
        """Superfície sólida no topo da pedra após ela pousar.

        Estalactites suspensas/em queda não bloqueiam o jogador como
        plataformas. A formação gigante do puzzle vira uma plataforma quando
        aterrissa no buraco.
        """
        if self.state != Stalactite.STATE_LANDED:
            return None
        platform_w = max(1, int(self.visual_width * 0.94))
        return pygame.Rect(
            round(self.anchor_x - platform_w / 2),
            round(self.y + 4),
            platform_w,
            18,
        )

    def draw(self, surface, camera_x):
        if self.state == Stalactite.STATE_GONE:
            return

        shake_x = 0
        if self.state == Stalactite.STATE_SHAKE:
            shake_x = 2 if (self.shake_timer // 3) % 2 == 0 else -2

        screen_x = round(self.anchor_x - self.visual_width / 2 - camera_x + shake_x)
        screen_y = round(self.y)
        if (screen_x + self.visual_width < 0 or screen_x > settings.SCREEN_WIDTH
                or screen_y + self.visual_height < 0 or screen_y > settings.SCREEN_HEIGHT):
            return

        sprite = self._load_sprite(self.variant)
        if sprite is not None:
            size = (self.visual_width, self.visual_height)
            key = (self.variant, size)
            if key not in Stalactite._scaled_cache:
                Stalactite._scaled_cache[key] = pygame.transform.smoothscale(sprite, size)
            image = Stalactite._scaled_cache[key]
            if self.state == Stalactite.STATE_FADING:
                image = image.copy()
                image.set_alpha(max(0, int(255 * self.fade_timer / 18)))
            surface.blit(image, (screen_x, screen_y))
            return

        # Fallback geométrico com suporte à transição alpha.
        r = self.rect.move(-camera_x, 0)
        points = [(r.left, r.top), (r.centerx, r.bottom), (r.right, r.top)]
        if self.state == Stalactite.STATE_FADING:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            color = (*settings.COLOR_SPIKE[:3], max(0, int(255 * self.fade_timer / 18)))
            pygame.draw.polygon(overlay, color, points)
            surface.blit(overlay, (0, 0))
        else:
            pygame.draw.polygon(surface, settings.COLOR_SPIKE, points)


class ObstacleGroup:
    def __init__(self):
        self.spikes = []
        self.stalactites = []
        self._ceiling_variant_counter = 0

    def add_spike(self, x, y, width=32, height=16):
        s = Spike(x, y, width, height, facing="up")
        self.spikes.append(s)
        return s

    def add_ceiling_spike(self, x, y, width=32, height=16):
        """Compatibilidade com chamadas antigas: toda estalactite presa ao
        teto agora é uma armadilha que avisa e cai quando o jogador passa
        por baixo. Não cria mais estalactites permanentemente decorativas."""
        return self.add_stalactite(x, y, width=width, height=height,
                                   trigger_range=56)

    def add_stalactite(self, x, y, width=32, height=40, trigger_range=36,
                       variant=None, visual_size=None, fall_to_y=None,
                       trigger_on_death_zone=None, persistent_after_landing=False):
        """Cria uma estalactite-armadilha. Parâmetros extras são usados pela
        grande estalactite do puzzle da fenda."""
        if variant is None:
            variant = (len(self.stalactites) % 4) + 1
        s = Stalactite(
            x, y, width, height, trigger_range=trigger_range, variant=variant,
            visual_size=visual_size, fall_to_y=fall_to_y,
            trigger_on_death_zone=trigger_on_death_zone,
            persistent_after_landing=persistent_after_landing,
        )
        self.stalactites.append(s)
        return s

    def landed_platform_rects(self):
        """Retângulos sólidos das estalactites que já pousaram."""
        return [rect for st in self.stalactites
                if (rect := st.platform_rect()) is not None]

    def update(self, player, ground_y=None, solids=None):
        for s in self.spikes:
            s.check_damage(player)
        for st in self.stalactites:
            st.update(player, ground_y=ground_y, solids=solids)

    def draw(self, surface, camera_x):
        for s in self.spikes:
            s.draw(surface, camera_x)
        for st in self.stalactites:
            st.draw(surface, camera_x)
