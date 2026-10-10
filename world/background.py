"""
world/background.py
Cenários de fundo das duas grandes áreas do jogo (puramente visual -
nenhum desses elementos tem colisão ou afeta gameplay):

  VillageBackdrop - usado em TODO o mapa principal (build_main_level),
  da Região 1 até a Região 4. É uma única identidade visual contínua:
  noite, lua grande, nuvens, montanhas, uma vila destruída ao fundo,
  entulho, e fogueiras com brasas/fumaça. As 4 regiões não são biomas
  diferentes - são só trechos de conteúdo de jogo dentro do MESMO
  cenário.

  CastleBackdrop - usado só na arena do Boss (build_boss_level):
  castelo sombrio em ruínas, colunas quebradas, fogo, iluminação
  vermelha/laranja, vinheta escura - uma identidade visual
  propositalmente muito mais ameaçadora que a área inicial.

Desempenho: tudo que é uma textura "parada" (céu em gradiente, brilho
da lua/fogueiras, nuvens, vinheta) é pré-computado UMA vez em
pygame.Surface e só desenhado (blit) a cada frame com o deslocamento
de paralaxe - nada de recalcular gradientes/círculos todo frame. Só os
elementos realmente animados (chamas, brasas, fumaça, deriva das
nuvens) são recalculados por frame, e são poucos e simples (math.sin/
poucos pygame.draw por item).
"""

import math
import os
import random

import pygame

from config import settings


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _vertical_gradient(w, h, top_color, bottom_color, bands=48):
    surf = pygame.Surface((w, h))
    band_h = h / bands
    for i in range(bands):
        t = i / (bands - 1) if bands > 1 else 0
        color = _lerp_color(top_color, bottom_color, t)
        y0 = int(i * band_h)
        y1 = int((i + 1) * band_h) + 1
        pygame.draw.rect(surf, color, (0, y0, w, y1 - y0))
    return surf


def _glow_surface(radius, color, max_alpha, steps=16):
    """Brilho radial simples (várias circunferências semi-transparentes
    sobrepostas, de fora pra dentro) - pré-computado uma vez e reusado
    via blit (alpha normal, NÃO aditivo - aditivo em cima de um céu
    bem escuro "estoura" e vira uma bolha sólida em vez de um halo
    suave) nos pontos de luz (lua, fogueiras, janelas)."""
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(steps, 0, -1):
        t = i / steps
        r = max(1, int(radius * t))
        a = int(max_alpha * (1 - t) ** 2.2)
        if a <= 0:
            continue
        pygame.draw.circle(surf, (*color, a), (radius, radius), r)
    return surf


def _vignette_surface(w, h, color=(0, 0, 0), max_alpha=160):
    """Escurece as bordas da tela - usado na arena do Boss pra dar um
    clima mais fechado/ameaçador."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = 10
    cx, cy = w / 2, h / 2
    max_r = math.hypot(cx, cy)
    for i in range(steps):
        t = i / (steps - 1)
        r = int(max_r * (0.55 + t * 0.6))
        a = int(max_alpha * t)
        if a <= 0:
            continue
        pygame.draw.circle(surf, (*color, a), (int(cx), int(cy)), r, width=int(max_r * 0.18) + 2)
    return surf


class _EmberSource:
    """Pontinho de luz com brasas subindo e fumaça - usado tanto pelas
    fogueiras da vila quanto pelas fogueiras maiores da arena do Boss.
    Totalmente auto-contido (não usa o systems/particles.py do jogo,
    que é pra efeitos de combate) - desenhado como parte do fundo,
    sempre atrás do player/plataformas."""

    def __init__(self, x, seed, scale=1.0):
        self.x = x
        self.seed = seed
        self.scale = scale


class _Backdrop:
    """Base comum: gradiente de céu + nuvens + brasas/fogueiras. As
    subclasses (Village/Castle) definem paleta e as camadas extras
    (montanhas vs. castelo) e chamam os helpers daqui."""

    SCREEN_W = settings.SCREEN_WIDTH
    SCREEN_H = settings.SCREEN_HEIGHT

    def __init__(self):
        self._t = 0

    def update(self):
        self._t += 1

    # ---------- Fogueiras / brasas / fumaça (reaproveitado pelas duas) ----------
    def _make_fires(self, rng, level_width, spacing, margin=200):
        fires = []
        x = margin
        while x < level_width - margin:
            fires.append(_EmberSource(x, rng.random() * 100))
            x += rng.randint(*spacing)
        return fires

    def _draw_fires(self, surface, camera_x, fires, parallax, ground_y,
                     glow_surf, smoke_surf, flame_colors, ember_color):
        t = self._t
        for fire in fires:
            sx = fire.x - camera_x * parallax
            if sx < -80 or sx > self.SCREEN_W + 80:
                continue
            base_y = ground_y + 2
            local_t = t * 0.1 + fire.seed
            flicker = 1.0 + 0.18 * math.sin(local_t * 3.1) + 0.08 * math.sin(local_t * 7.3)

            gw = glow_surf.get_width()
            surface.blit(glow_surf, (sx - gw / 2, base_y - gw / 2 + 4))

            flame_h = 20 * flicker * fire.scale
            flame_w = 9 * fire.scale
            outer, inner = flame_colors
            pygame.draw.polygon(surface, outer, [
                (sx - flame_w, base_y), (sx, base_y - flame_h), (sx + flame_w, base_y),
            ])
            pygame.draw.polygon(surface, inner, [
                (sx - flame_w * 0.45, base_y), (sx, base_y - flame_h * 0.55), (sx + flame_w * 0.45, base_y),
            ])

            # Brasas subindo em loop (sem alocar nada novo por frame)
            for i in range(4):
                phase = ((local_t * 0.45) + i / 4) % 1.0
                ex = sx + math.sin(local_t * 1.3 + i) * 7 * fire.scale
                ey = base_y - phase * 42 * fire.scale - 6
                ea = max(0, int(230 * (1 - phase)))
                if ea > 10:
                    s = pygame.Surface((4, 4), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*ember_color, ea), (2, 2), 2)
                    surface.blit(s, (ex - 2, ey - 2))

            # Fumaça subindo (puffs pré-computados, só reposicionados)
            for i in range(2):
                phase = ((local_t * 0.18) + i / 2) % 1.0
                smx = sx + math.sin(local_t * 0.4 + i) * 10
                smy = base_y - 18 - phase * 80 * fire.scale
                alpha = max(0, int(80 * (1 - phase)))
                if alpha > 6:
                    smoke_surf.set_alpha(alpha)
                    sw = smoke_surf.get_width()
                    surface.blit(smoke_surf, (smx - sw / 2, smy - sw / 2))


# ======================================================================
# Área inicial -> Região 4 (TODA a jornada principal): vila destruída à
# noite. Uma única identidade visual contínua.
# ======================================================================
class VillageBackdrop(_Backdrop):
    PARALLAX_MOUNTAINS_FAR = 0.10
    PARALLAX_MOUNTAINS_NEAR = 0.22
    PARALLAX_HOUSES = 0.40
    PARALLAX_RUBBLE = 0.55
    PARALLAX_CLOUDS = 0.05
    PARALLAX_MOON = 0.02
    PARALLAX_FIRES = 0.8

    COLOR_SKY_TOP = (7, 8, 20)
    COLOR_SKY_HORIZON = (33, 29, 56)
    COLOR_MOUNTAIN_FAR = (31, 29, 52)
    COLOR_MOUNTAIN_NEAR = (19, 18, 35)
    COLOR_HOUSE = (9, 8, 15)
    COLOR_RUBBLE = (36, 32, 40)
    COLOR_CLOUD = (58, 60, 90)
    COLOR_MOON = (231, 227, 202)
    COLOR_MOON_GLOW = (235, 228, 195)
    COLOR_WARM_LIGHT = (255, 150, 70)

    def __init__(self, level_width, ground_y, seed=11):
        super().__init__()
        rng = random.Random(seed)
        self.ground_y = ground_y
        self.level_width = level_width

        self.sky = _vertical_gradient(self.SCREEN_W, self.SCREEN_H, self.COLOR_SKY_TOP, self.COLOR_SKY_HORIZON)
        self.moon_pos = (self.SCREEN_W * 0.76, 95)
        self.moon_glow = _glow_surface(62, self.COLOR_MOON_GLOW, 50)
        self.light_glow = _glow_surface(13, self.COLOR_WARM_LIGHT, 100)
        self.smoke_surf = _glow_surface(24, (85, 80, 90), 95)
        self.fire_glow = _glow_surface(24, self.COLOR_WARM_LIGHT, 110)

        # Nuvens: 3 variantes de tamanho pré-renderizadas, reusadas por
        # várias instâncias (nunca redimensionadas por frame).
        self._cloud_variants = [self._make_cloud_surface(w) for w in (170, 230, 300)]
        self.clouds = []
        x = -300
        while x < level_width + 400:
            variant = rng.choice(self._cloud_variants)
            y = rng.randint(35, 150)
            self.clouds.append((x, y, variant))
            x += rng.randint(260, 520)

        self.mountains_far = self._make_ridge(rng, level_width, (260, 420), (90, 170))
        self.mountains_near = self._make_ridge(rng, level_width, (200, 340), (50, 120))

        self.houses = self._make_houses(rng, level_width)
        self.rubble = self._make_rubble(rng, level_width)
        self.fires = self._make_fires(rng, level_width, spacing=(800, 1300))
        self.lights = self._make_window_lights(rng, self.houses)

    # ---------- construção (uma vez) ----------
    def _make_cloud_surface(self, w):
        h = int(w * 0.3)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        blobs = [
            (0.20, 0.62, 0.34, 0.55), (0.45, 0.40, 0.42, 0.62),
            (0.68, 0.55, 0.36, 0.55), (0.85, 0.65, 0.26, 0.42),
        ]
        for bx, by, bw, bh in blobs:
            rect = (bx * w - bw * w / 2, by * h - bh * h / 2, bw * w, bh * h)
            pygame.draw.ellipse(surf, (*self.COLOR_CLOUD, 85), rect)
        return surf

    def _make_ridge(self, rng, level_width, seg_w, h_range):
        points = [(-50, self.ground_y)]
        x = -50
        while x < level_width + seg_w[1]:
            x += rng.randint(*seg_w)
            y = self.ground_y - rng.randint(*h_range)
            points.append((x, y))
        points.append((x, self.ground_y))
        return points

    def _make_houses(self, rng, level_width):
        houses = []
        x = -100
        while x < level_width + 100:
            w = rng.randint(90, 170)
            h = rng.randint(70, 135)
            broken = rng.random() < 0.65
            houses.append({"x": x, "w": w, "h": h, "broken": broken})
            x += w + rng.randint(50, 230)
        return houses

    def _make_rubble(self, rng, level_width):
        items = []
        x = -50
        while x < level_width + 50:
            w = rng.randint(22, 48)
            h = rng.randint(10, 24)
            items.append((x, w, h, rng.random() < 0.5))
            x += rng.randint(140, 420)
        return items

    def _make_window_lights(self, rng, houses):
        lights = []
        for house in houses:
            if house["broken"] and rng.random() < 0.55:
                continue  # casas muito destruídas ficam às escuras
            if rng.random() < 0.6:
                lx = house["x"] + house["w"] * rng.uniform(0.25, 0.75)
                ly = self.ground_y - house["h"] * rng.uniform(0.3, 0.7)
                lights.append((lx, ly))
        return lights

    # ---------- desenho (todo frame) ----------
    def draw(self, surface, camera_x):
        self.update()
        surface.blit(self.sky, (0, 0))
        self._draw_moon(surface, camera_x)
        self._draw_clouds(surface, camera_x)
        self._draw_ridge(surface, camera_x, self.mountains_far, self.PARALLAX_MOUNTAINS_FAR, self.COLOR_MOUNTAIN_FAR)
        self._draw_ridge(surface, camera_x, self.mountains_near, self.PARALLAX_MOUNTAINS_NEAR, self.COLOR_MOUNTAIN_NEAR)
        self._draw_houses(surface, camera_x)
        self._draw_rubble(surface, camera_x)
        self._draw_window_lights(surface, camera_x)
        self._draw_fires(surface, camera_x, self.fires, self.PARALLAX_FIRES, self.ground_y,
                          self.fire_glow, self.smoke_surf,
                          ((255, 110, 30), (255, 195, 80)), (255, 160, 60))

    def _draw_moon(self, surface, camera_x):
        mx, my = self.moon_pos
        sx = mx - camera_x * self.PARALLAX_MOON
        g = self.moon_glow
        surface.blit(g, (sx - g.get_width() / 2, my - g.get_height() / 2))
        pygame.draw.circle(surface, self.COLOR_MOON, (int(sx), int(my)), 30)
        pygame.draw.circle(surface, (208, 202, 178), (int(sx - 9), int(my - 6)), 5)
        pygame.draw.circle(surface, (208, 202, 178), (int(sx + 7), int(my + 9)), 4)
        pygame.draw.circle(surface, (208, 202, 178), (int(sx + 1), int(my + 12)), 3)

    def _draw_clouds(self, surface, camera_x):
        drift = self._t * 0.06
        for cx, cy, img in self.clouds:
            sx = cx - camera_x * self.PARALLAX_CLOUDS + drift
            w = img.get_width()
            if sx + w < -40 or sx > self.SCREEN_W + 40:
                continue
            surface.blit(img, (sx, cy))

    def _draw_ridge(self, surface, camera_x, points, parallax, color):
        poly = [(px - camera_x * parallax, py) for px, py in points]
        poly = [(poly[0][0], self.ground_y + 4)] + poly + [(poly[-1][0], self.ground_y + 4)]
        pygame.draw.polygon(surface, color, poly)

    def _draw_houses(self, surface, camera_x):
        parallax = self.PARALLAX_HOUSES
        for house in self.houses:
            sx = house["x"] - camera_x * parallax
            w, h = house["w"], house["h"]
            if sx + w < -20 or sx > self.SCREEN_W + 20:
                continue
            base_y = self.ground_y + 6
            top_y = base_y - h
            pygame.draw.rect(surface, self.COLOR_HOUSE, (sx, top_y, w, h))
            peak_y = top_y - h * 0.35
            if house["broken"]:
                pts = [
                    (sx - 6, top_y), (sx + w * 0.18, peak_y + h * 0.18),
                    (sx + w * 0.36, top_y - 6), (sx + w * 0.5, peak_y),
                    (sx + w * 0.66, top_y - 12), (sx + w * 0.82, peak_y + h * 0.22),
                    (sx + w + 6, top_y),
                ]
                pygame.draw.polygon(surface, self.COLOR_HOUSE, pts)
                # viga quebrada saindo do telhado
                bx = sx + w * 0.58
                pygame.draw.line(surface, self.COLOR_HOUSE, (bx, top_y - 8), (bx + 14, top_y - 34), 4)
            else:
                pts = [(sx - 6, top_y), (sx + w * 0.5, peak_y), (sx + w + 6, top_y)]
                pygame.draw.polygon(surface, self.COLOR_HOUSE, pts)

    def _draw_rubble(self, surface, camera_x):
        parallax = self.PARALLAX_RUBBLE
        for x, w, h, is_wood in self.rubble:
            sx = x - camera_x * parallax
            if sx + w < -10 or sx > self.SCREEN_W + 10:
                continue
            base_y = self.ground_y + 10
            if is_wood:
                pygame.draw.rect(surface, (52, 38, 30), (sx, base_y - h * 0.4, w, h * 0.4))
            else:
                pts = [(sx, base_y), (sx + w * 0.3, base_y - h), (sx + w * 0.62, base_y - h * 0.65), (sx + w, base_y)]
                pygame.draw.polygon(surface, self.COLOR_RUBBLE, pts)

    def _draw_window_lights(self, surface, camera_x):
        parallax = self.PARALLAX_HOUSES
        for lx, ly in self.lights:
            sx = lx - camera_x * parallax
            if sx < -40 or sx > self.SCREEN_W + 40:
                continue
            g = self.light_glow
            surface.blit(g, (sx - g.get_width() / 2, ly - g.get_height() / 2))


# ======================================================================
# Arena do Boss: castelo sombrio em ruínas, domínio de Vharok.
# ======================================================================
class CastleBackdrop(_Backdrop):
    PARALLAX_SKY_GLOW = 0.03
    PARALLAX_CASTLE_FAR = 0.15
    PARALLAX_CASTLE_NEAR = 0.32
    PARALLAX_COLUMNS = 0.55
    PARALLAX_FIRES = 0.75

    COLOR_SKY_TOP = (10, 4, 6)
    COLOR_SKY_HORIZON = (66, 20, 16)
    COLOR_CASTLE_FAR = (24, 11, 13)
    COLOR_CASTLE_NEAR = (38, 15, 15)
    COLOR_COLUMN = (30, 13, 14)
    COLOR_EMBER_GLOW = (255, 110, 40)

    def __init__(self, level_width, ground_y, seed=77):
        super().__init__()
        rng = random.Random(seed)
        self.ground_y = ground_y
        self.level_width = level_width

        self.sky = _vertical_gradient(self.SCREEN_W, self.SCREEN_H, self.COLOR_SKY_TOP, self.COLOR_SKY_HORIZON)
        self.sky_glow = _glow_surface(180, (200, 60, 30), 38)
        self.vignette = _vignette_surface(self.SCREEN_W, self.SCREEN_H, (0, 0, 0), 150)
        self.smoke_surf = _glow_surface(28, (60, 40, 38), 100)
        self.fire_glow = _glow_surface(30, self.COLOR_EMBER_GLOW, 120)

        self.skyline_far = self._make_skyline(rng, level_width, (70, 150), (140, 260))
        self.skyline_near = self._make_skyline(rng, level_width, (90, 190), (80, 180))
        self.columns = self._make_columns(rng, level_width)
        self.fires = self._make_fires(rng, level_width, spacing=(380, 560), margin=60)

    def _make_skyline(self, rng, level_width, w_range, h_range):
        segs = []
        x = -100
        while x < level_width + 100:
            w = rng.randint(*w_range)
            h = rng.randint(*h_range)
            segs.append({
                "x": x, "w": w, "h": h,
                "broken": rng.random() < 0.75,
                "crenellations": rng.random() < 0.5,
            })
            x += w + rng.randint(-15, 35)
        return segs

    def _make_columns(self, rng, level_width):
        cols = []
        x = 120
        while x < level_width - 120:
            if rng.random() < 0.6:
                h = rng.randint(90, 180)
                cols.append({"x": x, "h": h, "broken": rng.random() < 0.7})
            x += rng.randint(220, 420)
        return cols

    def draw(self, surface, camera_x):
        self.update()
        surface.blit(self.sky, (0, 0))
        g = self.sky_glow
        gx = self.SCREEN_W * 0.5 - camera_x * self.PARALLAX_SKY_GLOW
        surface.blit(g, (gx - g.get_width() / 2, -g.get_height() * 0.55))

        self._draw_skyline(surface, camera_x, self.skyline_far, self.PARALLAX_CASTLE_FAR, self.COLOR_CASTLE_FAR)
        self._draw_skyline(surface, camera_x, self.skyline_near, self.PARALLAX_CASTLE_NEAR, self.COLOR_CASTLE_NEAR)
        self._draw_columns(surface, camera_x)
        self._draw_fires(surface, camera_x, self.fires, self.PARALLAX_FIRES, self.ground_y,
                          self.fire_glow, self.smoke_surf,
                          ((255, 90, 20), (255, 175, 60)), (255, 130, 40))

        surface.blit(self.vignette, (0, 0))

    def _draw_skyline(self, surface, camera_x, segs, parallax, color):
        base_y = self.ground_y + 4
        for seg in segs:
            sx = seg["x"] - camera_x * parallax
            w, h = seg["w"], seg["h"]
            if sx + w < -20 or sx > self.SCREEN_W + 20:
                continue
            top_y = base_y - h
            if seg["broken"]:
                step = max(10, w // 5)
                pts = [(sx, base_y)]
                xx = sx
                while xx < sx + w:
                    jag = top_y + random.Random(int(xx)).randint(-18, 22)
                    pts.append((xx, jag))
                    xx += step
                pts.append((sx + w, base_y))
                pygame.draw.polygon(surface, color, pts)
            else:
                pygame.draw.rect(surface, color, (sx, top_y, w, h))
                if seg["crenellations"]:
                    tooth_w = max(8, w // 8)
                    for i in range(0, int(w), tooth_w * 2):
                        pygame.draw.rect(surface, color, (sx + i, top_y - 10, tooth_w, 10))

    def _draw_columns(self, surface, camera_x):
        parallax = self.PARALLAX_COLUMNS
        base_y = self.ground_y + 6
        for col in self.columns:
            sx = col["x"] - camera_x * parallax
            h = col["h"]
            if sx < -30 or sx > self.SCREEN_W + 30:
                continue
            w = 22
            top_y = base_y - h
            pygame.draw.rect(surface, self.COLOR_COLUMN, (sx - w / 2, top_y, w, h))
            # capitel (topo mais largo), quebrado ou não
            if col["broken"]:
                pygame.draw.polygon(surface, self.COLOR_COLUMN, [
                    (sx - w / 2 - 4, top_y + 10), (sx + 2, top_y - 6), (sx + w / 2 + 6, top_y + 14),
                ])
            else:
                pygame.draw.rect(surface, self.COLOR_COLUMN, (sx - w / 2 - 6, top_y - 8, w + 12, 10))


# ======================================================================
# Background panorâmico oficial da fase principal (assets/images/mundo.png).
# Puramente visual, sem colisão. Vila destruída -> ruínas -> caminho ->
# castelo de Vharok, da esquerda para a direita.
# ======================================================================
class MundoBackdrop:
    """Desenha o mundo.png preso à câmera existente (camera_x).

    A imagem é escalada só para a altura da tela (mantendo a proporção,
    sem distorcer) e alinhada embaixo. Como ela é bem mais estreita que a
    fase, o deslocamento é mapeado linearmente: camera_x = 0 mostra a
    vila (borda esquerda da imagem) e camera_x = máximo mostra o castelo
    (borda direita), revelando as regiões aos poucos conforme o jogador
    avança. Não cria câmera nova - só usa o camera_x recebido.
    """

    ASSET_PATH = os.path.join("assets", "images", "mundo.png")

    # Ajuste de "discrição" do cenário, aplicado UMA vez ao carregar (nunca por
    # frame). Objetivo: o fundo não competir com Kael, inimigos, moedas,
    # plataformas e armadilhas, sem perder a identidade visual.
    TONE_BRIGHTNESS = 0.86        # ~14% mais escuro
    TONE_CONTRAST = 0.90          # puxa os valores em direção à média
    TONE_SATURATION = 0.82        # dessatura levemente (azuis/roxos/laranjas)
    TONE_VEIL_COLOR = (26, 34, 50)   # camada azul-acinzentada escura
    TONE_VEIL_ALPHA = 0.08           # 8% de opacidade

    def __init__(self, level_width):
        self.level_width = level_width
        raw = pygame.image.load(self._resolve_path()).convert()
        scale = settings.SCREEN_HEIGHT / raw.get_height()
        new_w = max(settings.SCREEN_WIDTH, round(raw.get_width() * scale))
        self.image = pygame.transform.smoothscale(raw, (new_w, settings.SCREEN_HEIGHT))
        self.image = self._tone_down(self.image)
        self.max_camera = max(1, level_width - settings.SCREEN_WIDTH)
        self.max_scroll = self.image.get_width() - settings.SCREEN_WIDTH

    @classmethod
    def _tone_down(cls, image):
        """Versão mais discreta do background (mesmas dimensões, sem
        distorção): saturação e contraste um pouco menores, brilho reduzido e
        um véu azul-acinzentado. Roda uma vez; o resultado é reutilizado."""
        try:
            import numpy as np
            rgb = pygame.surfarray.array3d(image).astype(np.float32)
            luma = (rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114)[..., None]
            rgb = luma + (rgb - luma) * cls.TONE_SATURATION          # saturação
            mean = luma.mean()
            rgb = mean + (rgb - mean) * cls.TONE_CONTRAST            # contraste
            rgb *= cls.TONE_BRIGHTNESS                               # brilho
            veil = np.array(cls.TONE_VEIL_COLOR, dtype=np.float32)
            rgb = rgb * (1 - cls.TONE_VEIL_ALPHA) + veil * cls.TONE_VEIL_ALPHA
            out = pygame.surfarray.make_surface(np.clip(rgb, 0, 255).astype(np.uint8))
            return out.convert()
        except Exception:
            # Sem numpy: só escurece levemente + véu (ainda uma única vez).
            out = image.copy()
            out.fill((int(255 * cls.TONE_BRIGHTNESS),) * 3, special_flags=pygame.BLEND_RGB_MULT)
            veil = pygame.Surface(out.get_size())
            veil.fill(cls.TONE_VEIL_COLOR)
            veil.set_alpha(int(255 * cls.TONE_VEIL_ALPHA))
            out.blit(veil, (0, 0))
            return out

    @classmethod
    def _resolve_path(cls):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, cls.ASSET_PATH)

    @classmethod
    def available(cls):
        return os.path.isfile(cls._resolve_path())

    def draw(self, surface, camera_x):
        t = max(0.0, min(1.0, camera_x / self.max_camera))
        scroll = int(round(t * self.max_scroll))
        surface.blit(self.image, (-scroll, 0))




class SegmentedWorldBackdrop:
    """Fundo em camadas de parallax para deserto e caverna.

    Cada PNG é uma camada independente com transparência. As camadas são
    preparadas uma vez, mantêm a proporção e se repetem horizontalmente.
    O movimento é relativo à câmera e cada profundidade tem uma velocidade.
    Entre x=6000 e x=7000, as duas composições fazem crossfade.
    """
    PARALLAX_FACTORS = (0.04, 0.08, 0.13, 0.19, 0.25, 0.32, 0.40, 0.48)
    TRANSITION_START = 6000
    TRANSITION_END = 7000

    @classmethod
    def _resolve_dir(cls, name):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "assets", "images", name)

    @classmethod
    def available(cls):
        desert = cls._resolve_dir("parallax_desert")
        cave = cls._resolve_dir("parallax_cave")
        return (all(os.path.isfile(os.path.join(desert, f"{i}.png")) for i in range(1, 5))
                and all(os.path.isfile(os.path.join(cave, f"{i}.png")) for i in range(1, 8)))

    def __init__(self, level_width):
        self.level_width = level_width
        self.screen_w = settings.SCREEN_WIDTH
        self.screen_h = settings.SCREEN_HEIGHT
        self.desert = self._load_desert_layers()
        self.cave = self._load_layers("parallax_cave", list(range(7, 0, -1)))
        self._flipped_cache = {}

    def _load_desert_layers(self):
        """Camadas do pacote Desert: céu, sol, montanhas e ruínas.

        Os fundos quadrados são escalados uniformemente pela altura; o sol
        fica numa superfície transparente do tamanho da tela para manter sua
        escala visual pequena e estável. Tudo é preparado só na inicialização.
        """
        folder = self._resolve_dir("parallax_desert")
        loaded = []
        factors = {"1.png": 0.02, "2.png": 0.035, "3.png": 0.10, "4.png": 0.22}
        for filename in ("1.png", "2.png", "3.png", "4.png"):
            raw = pygame.image.load(os.path.join(folder, filename)).convert_alpha()
            if filename == "2.png":
                layer = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
                sun_size = max(24, round(self.screen_h * 0.12))
                sun = pygame.transform.smoothscale(raw, (sun_size, sun_size))
                layer.blit(sun, (round(self.screen_w * 0.72 - sun_size / 2), round(self.screen_h * 0.14)))
            else:
                scale = self.screen_h / raw.get_height()
                size = (max(1, round(raw.get_width() * scale)), self.screen_h)
                layer = pygame.transform.smoothscale(raw, size)
            loaded.append((layer, factors[filename]))
        return loaded

    def _load_layers(self, folder, indices):
        result = []
        for order, index in enumerate(indices):
            path = os.path.join(self._resolve_dir(folder), f"{index}.png")
            raw = pygame.image.load(path).convert_alpha()
            # Escala uniforme pela altura; a arte 16:9 não é deformada.
            scale = self.screen_h / raw.get_height()
            size = (max(1, round(raw.get_width() * scale)), self.screen_h)
            image = pygame.transform.smoothscale(raw, size)
            factor = self.PARALLAX_FACTORS[min(order, len(self.PARALLAX_FACTORS)-1)]
            result.append((image, factor))
        return result

    def _draw_layers(self, surface, layers, camera_x, alpha=255):
        for image, factor in layers:
            tile_w = image.get_width()
            offset = int((camera_x * factor) % tile_w)
            x = -offset
            tile_num = 0
            while x < self.screen_w:
                tile = image
                if tile_num % 2:
                    key = (id(image), "flip")
                    if key not in self._flipped_cache:
                        self._flipped_cache[key] = pygame.transform.flip(image, True, False)
                    tile = self._flipped_cache[key]
                if alpha >= 255:
                    surface.blit(tile, (x, 0))
                elif tile.get_flags() & pygame.SRCALPHA:
                    # Não altera as camadas originais; alpha temporário só durante a transição.
                    faded = tile.copy()
                    faded.set_alpha(alpha)
                    surface.blit(faded, (x, 0))
                else:
                    faded = tile.copy()
                    faded.set_alpha(alpha)
                    surface.blit(faded, (x, 0))
                x += tile_w
                tile_num += 1

    def draw(self, surface, camera_x):
        x = max(0, camera_x)
        surface.fill((16, 18, 25))
        if x < self.TRANSITION_START:
            self._draw_layers(surface, self.desert, x)
        elif x >= self.TRANSITION_END:
            self._draw_layers(surface, self.cave, x)
        else:
            t = (x - self.TRANSITION_START) / (self.TRANSITION_END - self.TRANSITION_START)
            # Renderiza as duas composições em superfícies de tela e mistura,
            # para que o alpha seja aplicado à composição inteira e não por camada.
            if not hasattr(self, "_transition_surface"):
                self._transition_surface = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
                self._cave_surface = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            self._transition_surface.fill((16, 18, 25, 255))
            self._cave_surface.fill((16, 18, 25, 255))
            self._draw_layers(self._transition_surface, self.desert, x)
            self._draw_layers(self._cave_surface, self.cave, x)
            surface.blit(self._transition_surface, (0, 0))
            self._cave_surface.set_alpha(round(255 * t))
            surface.blit(self._cave_surface, (0, 0))
            self._cave_surface.set_alpha(255)

# ======================================================================
# Background exclusivo da arena do Boss Vharok (assets/images/boss_arena.png).
# Puramente visual, sem colisão. Salão gótico simétrico com trono ao fundo.
# ======================================================================
class BossArenaBackdrop:
    """Desenha o boss_arena.png preso à câmera existente (camera_x).

    A imagem é escalada UMA vez, sem distorcer, de modo que a linha onde a
    parede encontra o piso ilustrado (FLOOR_LINE_SRC, em px nativos) fique
    logo atrás do topo do chão real da arena (floor_y). O piso ilustrado
    fica escondido atrás do chão do jogo, evitando um "segundo piso". Como a
    arena (1400 px) é mais larga que a tela, o deslocamento é mapeado
    linearmente: camera_x = 0 mostra a borda esquerda da imagem e
    camera_x = máximo mostra a direita, com o trono no centro da arena.
    Não cria câmera nova - só usa o camera_x recebido.
    """

    ASSET_PATH = os.path.join("assets", "images", "boss_arena.png")
    FLOOR_LINE_SRC = 490     # px nativos: base da parede/degraus do trono = início do piso ilustrado
    FLOOR_OVERLAP = 4        # px: a linha do piso fica um pouco atrás do topo do chão real

    def __init__(self, level_width, floor_y):
        self.level_width = level_width
        raw = pygame.image.load(self._resolve_path()).convert()
        scale = (floor_y + self.FLOOR_OVERLAP) / self.FLOOR_LINE_SRC
        # nunca menor que a tela (cobre altura e largura, sem distorcer)
        scale = max(scale, settings.SCREEN_HEIGHT / raw.get_height(),
                    settings.SCREEN_WIDTH / raw.get_width())
        size = (round(raw.get_width() * scale), round(raw.get_height() * scale))
        self.image = pygame.transform.smoothscale(raw, size)
        self.max_camera = max(1, level_width - settings.SCREEN_WIDTH)
        self.max_scroll = max(0, self.image.get_width() - settings.SCREEN_WIDTH)

    @classmethod
    def _resolve_path(cls):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, cls.ASSET_PATH)

    @classmethod
    def available(cls):
        return os.path.isfile(cls._resolve_path())

    def draw(self, surface, camera_x):
        t = max(0.0, min(1.0, camera_x / self.max_camera))
        scroll = int(round(t * self.max_scroll))
        surface.blit(self.image, (-scroll, 0))
