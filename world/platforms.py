"""
world/platforms.py
Responsável pelas plataformas do cenário: chão/blocos estáticos,
plataformas móveis (vaivém entre dois pontos) e plataformas
quebradiças (despencam pouco depois do jogador pisar e reaparecem
depois de um tempo). A colisão real é resolvida por systems/collision.py;
aqui vivem apenas o estado e o desenho de cada tipo.
"""

import os

import pygame
from config import settings

# ----------------------------------------------------------------------
# Sprites de terreno e estruturas (assets/images/*.png).
# São SOMENTE visuais: a colisão continua sendo o Rect de cada plataforma.
# Se algum PNG faltar (ou não houver janela de vídeo ainda), cada classe
# cai no desenho geométrico antigo, então o jogo nunca quebra por isso.
# ----------------------------------------------------------------------
_IMG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "images"
)

# ground.png / ground_underside.png usam a mesma escala (mesma "pedra").
GROUND_SCALE = 0.12
GROUND_FEET_Y = 170       # linha do ground.png (px nativos) = topo do collider (onde o jogador pisa)
GROUND_CAP_W = 260        # px nativos de cada ponta arredondada do ground.png
UNDERSIDE_OVERLAP = 30    # px de tela: o underside entra por trás da base do ground.png (esconde a emenda)
UNDERSIDE_INSET = 3       # px: recuo lateral do underside nas pontas, pra não passar da silhueta

# hole.png: o buraco é só o vão entre dois trechos de chão (a lógica de queda
# continua sendo "não há plataforma ali"). O sprite é escalado pra abertura
# do poço bater com a largura do vão; as bordas (ledges) ficam por cima das
# pontas do chão, fora do vão.
HOLE_SCALE = 0.40
HOLE_CAP_W = 215          # px nativos de cada borda (ledge) do hole.png
HOLE_RIM_Y = 55           # px nativos: centro da face de cima da borda = centro da face de cima do chão
GROUND_FACE_CENTER = -2   # px relativos ao topo do collider do chão
# Vãos largos: o miolo do sprite (com o "coração" do topo) repetido ficaria
# com cara de fileira de figuras, então eles usam só a parede rachada do
# interior do poço, repetida (espelhada) entre as duas bordas.
HOLE_SIMPLE_MAX = 160     # até essa largura de vão usa o sprite inteiro
HOLE_WALL_ROWS = (130, 330)   # linhas nativas da parede interior (textura)
HOLE_WALL_TOP = 28        # px (escala do jogo) do topo da parede dentro da faixa
HOLE_WALL_FADE = 14       # px de degradê no topo da parede (some na névoa do cenário, sem borda reta)

# Linha (px nativos do PNG já recortado) onde o jogador pisa em cada plataforma.
PLATFORM_FEET_Y = {"platform_static": 80, "platform_moving": 95}

_raw_cache = {}
_scaled_cache = {}
_strip_cache = {}


def _load(name):
    """Carrega assets/images/<name>.png (com alpha). None se não der."""
    if name not in _raw_cache:
        try:
            _raw_cache[name] = pygame.image.load(
                os.path.join(_IMG_DIR, name + ".png")
            ).convert_alpha()
        except (pygame.error, FileNotFoundError):
            _raw_cache[name] = None
    return _raw_cache[name]


def _scaled(name, size):
    key = (name, size)
    if key not in _scaled_cache:
        _scaled_cache[key] = pygame.transform.smoothscale(_load(name), size)
    return _scaled_cache[key]


def _mirror_fill(tile, width, height, offset=0):
    """Surface (width x height) preenchida repetindo 'tile' com espelhamento
    alternado. Espelhar faz a borda de uma peça coincidir exatamente com a
    da vizinha, então não aparece linha/emenda entre elas. 'offset' é a
    distância entre a origem da grade de peças e a borda esquerda da faixa
    (usar coordenada de mundo deixa trechos vizinhos contínuos)."""
    tw, th = tile.get_size()
    variants = {
        (False, False): tile,
        (True, False): pygame.transform.flip(tile, True, False),
        (False, True): pygame.transform.flip(tile, False, True),
        (True, True): pygame.transform.flip(tile, True, True),
    }
    out = pygame.Surface((width, height), pygame.SRCALPHA)
    first = offset // tw
    x0 = first * tw - offset
    cols = (width - x0) // tw + 1
    rows = height // th + 1
    for j in range(rows):
        for i in range(cols):
            piece = variants[((first + i) % 2 == 1, j % 2 == 1)]
            out.blit(piece, (x0 + i * tw, j * th))
    return out


def _ground_slab(width, x, cap_left, cap_right):
    """Faixa do ground.png para um trecho de chão: pontas arredondadas só
    nos lados livres, miolo repetido (espelhado) no meio."""
    ground = _scaled("ground", (round(_load("ground").get_width() * GROUND_SCALE),
                                round(_load("ground").get_height() * GROUND_SCALE)))
    gw, gh = ground.get_size()
    cw = max(1, round(GROUND_CAP_W * GROUND_SCALE))
    mid_w = gw - 2 * cw
    offset = 0 if cap_left else x
    key = ("slab", width, cap_left, cap_right, offset % (2 * mid_w))
    if key not in _strip_cache:
        if width < 2 * cw + 8:
            _strip_cache[key] = pygame.transform.smoothscale(ground, (max(1, width), gh))
        else:
            mid = ground.subsurface(pygame.Rect(cw, 0, mid_w, gh)).copy()
            mx0 = cw if cap_left else 0
            mx1 = width - cw if cap_right else width
            out = pygame.Surface((width, gh), pygame.SRCALPHA)
            out.blit(_mirror_fill(mid, mx1 - mx0, gh, offset), (mx0, 0))
            # A ponta direita do PNG tem um brilho vermelho (lado do castelo);
            # usar a ponta esquerda espelhada nos dois lados evita manchas
            # vermelhas em todo buraco do mapa.
            cap = ground.subsurface(pygame.Rect(0, 0, cw, gh)).copy()
            if cap_left:
                out.blit(cap, (0, 0))
            if cap_right:
                out.blit(pygame.transform.flip(cap, True, False), (width - cw, 0))
            _strip_cache[key] = out
    return _strip_cache[key]


def _underside_strip(width, height, x):
    base = _load("ground_underside")
    size = (round(base.get_width() * GROUND_SCALE), round(base.get_height() * GROUND_SCALE))
    tile = _scaled("ground_underside", size)
    key = ("under", width, height, x % (2 * size[0]))
    if key not in _strip_cache:
        _strip_cache[key] = _mirror_fill(tile, width, height, x)
    return _strip_cache[key]


def _blit_visible(surface, strip, pos):
    """Blit só da parte da faixa que aparece na tela."""
    x, y = pos
    sw = settings.SCREEN_WIDTH
    vx0 = max(0, -x)
    vx1 = min(strip.get_width(), sw - x)
    if vx1 <= vx0:
        return
    surface.blit(strip, (x + vx0, y), pygame.Rect(vx0, 0, vx1 - vx0, strip.get_height()))


def _hole_strip(gap):
    """Faixa do hole.png para um vão de 'gap' px: borda esquerda do sprite,
    miolo (espelhado, pra caber qualquer largura) e a mesma borda espelhada
    à direita. Simétrica, então as emendas ficam contínuas."""
    base = _load("hole")
    full = _scaled("hole", (round(base.get_width() * HOLE_SCALE),
                            round(base.get_height() * HOLE_SCALE)))
    gw, gh = full.get_size()
    cw = round(HOLE_CAP_W * HOLE_SCALE)
    key = ("hole", gap)
    if key not in _strip_cache:
        half = (gap + 1) // 2
        cap = full.subsurface(pygame.Rect(0, 0, cw, gh)).copy()
        out = pygame.Surface((2 * cw + 2 * half, gh), pygame.SRCALPHA)
        if gap <= HOLE_SIMPLE_MAX:
            mid = full.subsurface(pygame.Rect(cw, 0, gw - 2 * cw, gh)).copy()
            left_fill = _mirror_fill(mid, half, gh, 0)
            top = 0
        else:
            r0 = round(HOLE_WALL_ROWS[0] * HOLE_SCALE)
            r1 = round(HOLE_WALL_ROWS[1] * HOLE_SCALE)
            wall = full.subsurface(pygame.Rect(cw, r0, gw - 2 * cw, r1 - r0)).copy()
            for i in range(HOLE_WALL_FADE):
                wall.fill((255, 255, 255, int(255 * i / HOLE_WALL_FADE)),
                          pygame.Rect(0, i, wall.get_width(), 1),
                          special_flags=pygame.BLEND_RGBA_MULT)
            left_fill = _mirror_fill(wall, half, r1 - r0, 0)
            top = HOLE_WALL_TOP
        out.blit(left_fill, (cw, top))
        out.blit(pygame.transform.flip(left_fill, True, False), (cw + half, top))
        out.blit(cap, (0, 0))
        out.blit(pygame.transform.flip(cap, True, False), (cw + 2 * half, 0))
        _strip_cache[key] = out
    return _strip_cache[key], cw


def _draw_slab_sprite(surface, r, name, tint=None):
    """Plataforma (fixa/móvel): sprite na largura do collider, mantendo a
    proporção; a linha de pisada do sprite fica no topo do collider.
    'tint' (r, g, b) opcional soma cor ao sprite (aviso da quebradiça)."""
    base = _load(name)
    if base is None:
        return False
    scale = r.width / base.get_width()
    img = _scaled(name, (max(1, r.width), max(1, round(base.get_height() * scale))))
    if tint is not None:
        img = img.copy()
        img.fill(tint, special_flags=pygame.BLEND_RGB_ADD)
    surface.blit(img, (r.x, r.y - round(PLATFORM_FEET_Y[name] * scale)))
    return True



class Platform:
    """Plataforma estática (chão ou bloco fixo)."""

    def __init__(self, x, y, width, height, is_ground=False, color_override=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.is_ground = is_ground
        # Preenchidos por PlatformGroup: trecho de chão colado em outro
        # (sem ponta arredondada nesse lado).
        self.joins_left = False
        self.joins_right = False
        self.delta_x = 0  # plataformas estáticas nunca "carregam" o jogador
        # Opcional: permite uma plataforma específica usar uma cor
        # diferente da paleta padrão, sem mexer no resto do jogo - se
        # None, usa exatamente as cores de sempre.
        self.color_override = color_override

    def update(self):
        pass

    def is_solid(self):
        return True

    def _draw_ground(self, surface, r):
        if _load("ground") is None or _load("ground_underside") is None:
            return False
        slab = _ground_slab(self.rect.width, self.rect.x,
                            not self.joins_left, not self.joins_right)
        slab_y = r.y - round(GROUND_FEET_Y * GROUND_SCALE)
        # Massa de terra/pedra embaixo (só visual), atrás do ground.png.
        under_top = slab_y + slab.get_height() - UNDERSIDE_OVERLAP
        under_h = r.bottom - under_top
        if under_h > 0:
            il = 0 if self.joins_left else UNDERSIDE_INSET
            ir = 0 if self.joins_right else UNDERSIDE_INSET
            under = _underside_strip(r.width - il - ir, under_h, self.rect.x + il)
            _blit_visible(surface, under, (r.x + il, under_top))
        _blit_visible(surface, slab, (r.x, slab_y))
        return True

    def _draw_sprite(self, surface, r):
        if self.is_ground:
            return self._draw_ground(surface, r)
        if self.color_override:
            return False
        return _draw_slab_sprite(surface, r, "platform_static")

    def draw(self, surface, camera_x):
        r = self.rect.move(-camera_x, 0)
        if r.right < 0 or r.left > settings.SCREEN_WIDTH:
            return
        if self._draw_sprite(surface, r):
            return
        if self.color_override:
            color = self.color_override
            top_color = (
                min(color[0] + 25, 255),
                min(color[1] + 25, 255),
                min(color[2] + 25, 255),
            )
        else:
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
        if _draw_slab_sprite(surface, r, "platform_moving"):
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
        tint = None
        if self.state == CrumblingPlatform.STATE_SHAKING:
            import random
            offset = random.randint(-2, 2)
            fade = self.timer / settings.CRUMBLE_SHAKE_FRAMES
            color = (
                int(color[0] * fade + 200 * (1 - fade)),
                int(color[1] * fade + 60 * (1 - fade)),
                int(color[2] * fade + 60 * (1 - fade)),
            )
            # Aviso de desabamento: avermelha o sprite aos poucos.
            tint = (int(70 * (1 - fade)), 0, 0)
        # Sprite oficial (o mesmo das plataformas fixas); o retângulo antigo
        # só aparece se o PNG não puder ser carregado.
        if _draw_slab_sprite(surface, r.move(offset, 0), "platform_static", tint):
            return
        pygame.draw.rect(surface, color, (r.x + offset, r.y, r.width, r.height))
        pygame.draw.rect(surface, (150, 110, 80), (r.x + offset, r.y, r.width, 5))


class PlatformGroup:
    def __init__(self):
        self.platforms = []
        self._linked_count = -1
        self._gaps = []   # (x_esq, x_dir, y_topo) de cada buraco entre trechos de chão

    def add(self, x, y, width, height, is_ground=False, color_override=None):
        p = Platform(x, y, width, height, is_ground, color_override=color_override)
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

    def _link_ground(self):
        """Marca trechos de chão encostados um no outro (mesma altura) pra
        o visual formar uma massa contínua, sem ponta arredondada no meio.
        Só visual: não mexe em nenhum rect."""
        grounds = [p for p in self.platforms if p.is_ground and type(p) is Platform]
        for p in grounds:
            p.joins_left = p.rect.left <= 0
            p.joins_right = False
            for q in grounds:
                if q is p or q.rect.y != p.rect.y:
                    continue
                if abs(q.rect.right - p.rect.left) <= 2:
                    p.joins_left = True
                if abs(q.rect.left - p.rect.right) <= 2:
                    p.joins_right = True
        # Buracos = vãos entre dois trechos de chão consecutivos na mesma
        # altura. Só visual: a queda continua sendo "sem plataforma ali".
        self._gaps = []
        by_y = {}
        for p in grounds:
            by_y.setdefault(p.rect.y, []).append(p)
        for y, row in by_y.items():
            row.sort(key=lambda g: g.rect.x)
            for a, b in zip(row, row[1:]):
                if b.rect.left - a.rect.right > 2:
                    self._gaps.append((a.rect.right, b.rect.left, y))
        self._linked_count = len(self.platforms)

    def _draw_holes(self, surface, camera_x):
        if not self._gaps or _load("hole") is None:
            return
        for x0, x1, y in self._gaps:
            strip, cw = _hole_strip(x1 - x0)
            sx = x0 - cw - camera_x
            if sx + strip.get_width() < 0 or sx > settings.SCREEN_WIDTH:
                continue
            sy = y + GROUND_FACE_CENTER - round(HOLE_RIM_Y * HOLE_SCALE)
            _blit_visible(surface, strip, (sx, sy))

    def draw(self, surface, camera_x):
        if self._linked_count != len(self.platforms):
            self._link_ground()
        # Ordem: chão -> buracos (bordas por cima das pontas do chão) -> resto.
        for p in self.platforms:
            if p.is_ground:
                p.draw(surface, camera_x)
        self._draw_holes(surface, camera_x)
        for p in self.platforms:
            if not p.is_ground:
                p.draw(surface, camera_x)
