"""
world/level.py
Responsável pela criação e gerenciamento da fase. A Fase 1 (Jornada) tem
30 telas (30 x 1024 = 30.720 px) no MESMO mapa, sem telas de carregamento:
  Floresta - 15 telas (x = 0 a 15.360), com o Núcleo/loja no início
  Caverna  - 15 telas (x = 15.360 a 30.720), com o puzzle da fenda e o
             salão final que leva ao castelo de Vharok (acesso à Fase 2)
Há apenas 3 checkpoints: meio da floresta, transição floresta -> caverna e
meio da caverna. O mapa é montado por módulos de terreno (ver
_JourneyBuilder); o fundo em parallax faz crossfade floresta -> caverna no
limite entre as duas áreas (world/background.py).
A Fase 2 (Castelo de Vharok) é construída separadamente por build_boss_level().
"""

import pygame
from config import settings
from world.platforms import PlatformGroup
from world.obstacles import ObstacleGroup
from world.coins import CoinGroup
from world.checkpoints import Checkpoint
from enemies.basic_enemy import BasicEnemy, RangedEnemy
from enemies.flying_enemy import FlyingEnemy
from enemies.boss import Boss
from systems import collision
from systems.shop import ShopZone
from world.background import VillageBackdrop, CastleBackdrop, MundoBackdrop, SegmentedWorldBackdrop, BossArenaBackdrop

GROUND_Y = settings.SCREEN_HEIGHT - 64


class Level:
    def __init__(self, width, height, is_boss_level=False):
        self.width = width
        self.height = height
        self.is_boss_level = is_boss_level
        self.platforms = PlatformGroup()
        self.obstacles = ObstacleGroup()
        self.coins = CoinGroup()
        self.enemies = []
        self.core_pos = (64, GROUND_Y - settings.PLAYER_HEIGHT)
        self.player_start = self.core_pos
        self.shop_zone = None
        self.boss_trigger = None
        self.boss = None
        self.background_decor = []
        self.backdrop = None  # VillageBackdrop ou CastleBackdrop (ver world/background.py)
        self.tint_zones = []  # [(start_x, end_x, (r,g,b,a)), ...] - usado por biomas p/ dar clima (ex: cave escura)
        self.checkpoints = []
        self.story_triggers = []  # lista de dicts: {"x": int, "text": str, "triggered": bool}

    def add_checkpoint(self, x, y):
        cp = Checkpoint(x, y)
        self.checkpoints.append(cp)
        return cp

    def add_story_trigger(self, x, text, max_y=None):
        """max_y opcional: só dispara se o jogador também estiver acima
        dessa altura (usado para o gatilho da área secreta, por exemplo)."""
        self.story_triggers.append({"x": x, "text": text, "max_y": max_y, "triggered": False})

    def check_story_triggers(self, player_x, player_y):
        """Retorna o texto do primeiro gatilho de história recém-cruzado,
        ou None. Marca o gatilho como usado para não repetir."""
        for trig in self.story_triggers:
            if trig["triggered"] or player_x < trig["x"]:
                continue
            if trig["max_y"] is not None and player_y > trig["max_y"]:
                continue
            trig["triggered"] = True
            return trig["text"]
        return None

    # ---------- Colisão ----------
    def move_and_collide(self, player, vel_x, vel_y):
        # Se o jogador estava apoiado sobre uma plataforma móvel no frame
        # anterior, ele é deslocado junto com ela ANTES da gravidade/colisão
        # deste frame (usando o delta que a plataforma acabou de sofrer em
        # world/platforms.py -> PlatformGroup.update(), chamado no início
        # deste frame por core/game.py, antes do player.update()).
        #
        # Correção do bug de "cair no limbo" nas plataformas móveis:
        # antes, o jogador só era "colado" na plataforma DEPOIS de resolver
        # a colisão normal, usando o delta da plataforma referente ao frame
        # ANTERIOR (defasagem de 1 frame). Quando a plataforma descia mais
        # rápido que a gravidade acumulada do jogador naquele instante, a
        # sobreposição entre os dois retângulos deixava de existir por um
        # frame, o on_ground virava False e o jogador caía direto pelo
        # buraco que a própria plataforma estava atravessando. Colando o
        # jogador na plataforma primeiro, o contato nunca se perde.
        if player.standing_platform is not None and player.standing_platform.is_solid():
            player.rect.x += player.standing_platform.delta_x
            player.rect.y += player.standing_platform.delta_y

        solids = self.platforms.rects()
        # Uma estalactite só vira plataforma depois de pousar. Isso permite
        # usar a grande formação como ponte/parkour após o puzzle da fenda.
        solids.extend(self.obstacles.landed_platform_rects())
        new_rect, on_ground = collision.move_and_collide(player.rect, vel_x, vel_y, solids)
        player.rect = new_rect
        player.on_ground = on_ground
        player.standing_platform = None
        if on_ground:
            player.vel_y = 0
            # Plataforma quebradiça: pisar nela inicia o tremor
            crumbling = self.platforms.crumbling_at(player.rect)
            if crumbling:
                crumbling.trigger()
            # Identifica se está sobre uma plataforma móvel específica,
            # para colar nela no início do próximo frame.
            for mp in self.platforms.moving_platforms():
                touching = (abs(player.rect.bottom - mp.rect.top) <= 2
                            and player.rect.right > mp.rect.left
                            and player.rect.left < mp.rect.right)
                if touching:
                    player.standing_platform = mp
                    break

    def move_and_collide_enemy(self, enemy, vel_x, vel_y):
        solids = self.platforms.rects()
        new_rect, on_ground = collision.move_and_collide(enemy.rect, vel_x, vel_y, solids)
        enemy.rect = new_rect
        if on_ground:
            enemy.vel_y = 0

    def has_ground_ahead(self, rect, direction):
        return collision.ground_exists_below(rect, direction, self.platforms.rects())

    def rect_hits_solid(self, rect):
        return collision.rect_collides_any(rect, self.platforms.rects())

    def has_line_of_sight(self, start, end):
        """Linha de visão livre entre dois pontos do mundo. Usa os mesmos
        sólidos que a física e os projéteis (platforms.rects())."""
        return collision.line_of_sight_clear(start, end, self.platforms.rects())

    # ---------- Update ----------
    def update_platforms(self):
        """Atualiza somente as plataformas (chamado ANTES de player.update()
        em core/game.py, para que o jogador use o deslocamento das
        plataformas móveis do frame atual, e não do frame anterior)."""
        self.platforms.update()

    def update(self, player, particles=None):
        """Retorna o valor total de moedas coletadas neste frame (0 se
        nenhuma), usado por core/game.py para disparar o som de moeda."""
        for enemy in self.enemies:
            # Fase de 30 telas: inimigos muito longe de Kael ficam parados no
            # ponto de spawn (não há como vê-los nem como eles o alcançarem).
            if abs(enemy.rect.centerx - player.rect.centerx) > ENEMY_ACTIVE_RANGE:
                continue
            enemy.update(self, player)
        self.enemies = [e for e in self.enemies if True]  # mantidos p/ desenhar corpo caído; sem despawn
        self.obstacles.update(player, ground_y=GROUND_Y, solids=self.platforms.rects())
        coins_collected = self.coins.update(player, particles)
        if self.boss:
            self.boss.update(self, player)
        return coins_collected

    def living_enemies(self):
        return [e for e in self.enemies if e.alive]

    # ---------- Desenho ----------
    def draw_background(self, surface, camera_x):
        if self.backdrop is not None:
            self.backdrop.draw(surface, camera_x)
        else:
            # Reserva (não deveria acontecer nas fases reais do jogo -
            # ambas definem um backdrop em world/background.py): céu liso
            # + silhuetas simples, só pra nunca deixar a tela em branco.
            surface.fill(settings.COLOR_BG_SKY)
            for bx, bw, bh in self.background_decor:
                sx = bx - camera_x * 0.3
                if -bw < sx < settings.SCREEN_WIDTH:
                    pygame.draw.polygon(
                        surface, settings.COLOR_BG_FAR,
                        [(sx, GROUND_Y), (sx + bw / 2, GROUND_Y - bh), (sx + bw, GROUND_Y)],
                    )
        self._draw_tint_zones(surface, camera_x)

    def _draw_tint_zones(self, surface, camera_x):
        """Escurece/tinge um trecho do mapa (usado por biomas como a
        CAVE pra dar uma sensação de ambiente fechado). Puramente
        visual - desenha um overlay semi-transparente por cima do céu,
        na mesma superfície de sempre, sem mexer em mais nada."""
        for start_x, end_x, color in self.tint_zones:
            sx0 = start_x - camera_x
            sx1 = end_x - camera_x
            if sx1 < 0 or sx0 > settings.SCREEN_WIDTH:
                continue
            rx0 = max(0, sx0)
            rx1 = min(settings.SCREEN_WIDTH, sx1)
            if rx1 <= rx0:
                continue
            tint = pygame.Surface((rx1 - rx0, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
            tint.fill(color)
            surface.blit(tint, (rx0, 0))

    def draw(self, surface, camera_x):
        self.draw_background(surface, camera_x)
        self.platforms.draw(surface, camera_x)
        self.obstacles.draw(surface, camera_x)
        self.coins.draw(surface, camera_x)

        # Núcleo do Retorno (visual)
        core_rect = pygame.Rect(self.core_pos[0] - 10, self.core_pos[1] - 10,
                                 settings.PLAYER_WIDTH + 20, settings.PLAYER_HEIGHT + 20)
        cr = core_rect.move(-camera_x, 0)
        if -50 < cr.x < settings.SCREEN_WIDTH:
            pygame.draw.ellipse(surface, settings.COLOR_CORE, cr, width=3)

        if self.shop_zone:
            sr = self.shop_zone.rect.move(-camera_x, 0)
            if -50 < sr.x < settings.SCREEN_WIDTH:
                pygame.draw.rect(surface, (255, 210, 60), sr, width=2, border_radius=6)

        for cp in self.checkpoints:
            cp.draw(surface, camera_x)

        screen_center = camera_x + settings.SCREEN_WIDTH / 2
        for enemy in self.enemies:
            if abs(enemy.rect.centerx - screen_center) > settings.SCREEN_WIDTH / 2 + ENEMY_DRAW_MARGIN:
                continue   # longe demais para aparecer (nem projéteis dele chegam à tela)
            enemy.draw(surface, camera_x)
            enemy.draw_health_bar(surface, camera_x)

        if self.boss:
            self.boss.draw(surface, camera_x)


def _add_decor(level, rng, start, end):
    x = start
    while x < end:
        w = rng.randint(120, 260)
        h = rng.randint(60, 160)
        level.background_decor.append((x, w, h))
        x += w * rng.uniform(0.6, 1.1)


# ---------- Ajudantes de posicionamento de moedas ----------
# A moeda é um quadrado de COIN_SIZE px e Level.coins.add() recebe o canto
# superior esquerdo. Estes ajudantes recebem o CENTRO x e a superfície onde a
# moeda "descansa" (topo do chão/plataforma): assim a altura é sempre derivada
# da geometria, e moedas não nascem mais dentro de plataformas, no fundo de
# poços ou fora do alcance. Distância padrão: o topo da moeda fica COIN_LIFT px
# acima da superfície, de modo que o jogador a pega só andando.
COIN_SIZE = 16
COIN_LIFT = 40
COIN_STEP = 40


def _coin(level, cx, surface_y, lift=COIN_LIFT, value=None):
    kwargs = {} if value is None else {"value": value}
    level.coins.add(round(cx - COIN_SIZE / 2), round(surface_y - lift), **kwargs)


def _coins_centered(level, cx, count, surface_y=GROUND_Y, step=COIN_STEP, lift=COIN_LIFT):
    """'count' moedas em fileira, centralizadas em cx, sobre a superfície dada."""
    start = cx - (count - 1) * step / 2
    for i in range(count):
        _coin(level, start + i * step, surface_y, lift)


def _coins_on(level, platform, count=1, step=COIN_STEP, lift=COIN_LIFT):
    """Moedas centralizadas sobre o topo de uma plataforma."""
    _coins_centered(level, platform.rect.centerx, count, platform.rect.top, step, lift)


def _coin_arc(level, cx_from, cx_to, surface_y=GROUND_Y, rise=45, count=3, base=COIN_LIFT):
    """Arco de moedas sobre um vão ou espinho: as pontas ficam a 'base' px da
    superfície e o meio sobe 'rise' px; é a recompensa de saltar o perigo.
    Sobre ESPINHOS use base=SPIKE_ARC_BASE: as pontas ficam acima da cabeça de
    quem anda no chão, então só se pega a moeda saltando (nunca se pisa no
    espinho para pegá-la). rise + base <= ~110 mantém o arco no alcance do pulo."""
    for i in range(count):
        t = i / (count - 1) if count > 1 else 0.5
        _coin(level, cx_from + (cx_to - cx_from) * t, surface_y,
              lift=base + rise * 4 * t * (1 - t))


SPIKE_ARC_BASE = 72


# ======================================================================
# Fase 1 - Jornada (30 telas): Floresta (15 telas) + Caverna (15 telas)
# ======================================================================
# A Jornada é montada por MÓDULOS (trechos prontos de terreno, perigos,
# inimigos e moedas) encadeados da esquerda para a direita. Cada módulo
# começa e termina em chão na altura GROUND_Y, então qualquer ordem de
# módulos continua jogável. Os módulos reaproveitam as geometrias da fase
# antiga (vãos <= 140 px, degraus <= 90 px, espinhos longe das bordas).
#
# Para mudar o tamanho das áreas basta editar FOREST_SCREENS / CAVE_SCREENS
# (e ajustar a lista de módulos em _JourneyBuilder.build()).
FOREST_SCREENS = 15
CAVE_SCREENS = 15
FOREST_END = FOREST_SCREENS * settings.SCREEN_WIDTH                       # 15360: limite floresta | caverna
JOURNEY_WIDTH = (FOREST_SCREENS + CAVE_SCREENS) * settings.SCREEN_WIDTH   # 30720
GROUND_H = 64

# Com a fase bem maior, só inimigos perto de Kael são atualizados/desenhados
# (os distantes ficam parados no ponto de spawn). Os valores são folgados:
# o alcance do ranged é 320 px e o projétil dele percorre no máximo ~1100 px.
ENEMY_ACTIVE_RANGE = 2600
ENEMY_DRAW_MARGIN = 1300


class _JourneyBuilder:
    """Monta a Fase 1 por módulos. Ver comentário acima."""

    def __init__(self, level):
        self.level = level
        self.plat = level.platforms
        self.obst = level.obstacles
        self.no_stalactite = []     # [(x0, x1)] trechos sem estalactite-armadilha comum
        self.checkpoint_xs = []

    # ---------- Primitivas ----------
    def ground(self, x, w):
        return self.plat.add(x, GROUND_Y, w, GROUND_H, is_ground=True)

    def spike(self, x, w=64, arc=True):
        self.obst.add_spike(x, GROUND_Y - 16, width=w)
        if arc:
            _coin_arc(self.level, x - 4, x + w + 4, rise=36, base=SPIKE_ARC_BASE)

    def basic(self, cx, surface_y=GROUND_Y):
        self.level.enemies.append(BasicEnemy(
            round(cx - settings.BASIC_ENEMY_WIDTH / 2), surface_y - settings.BASIC_ENEMY_HEIGHT))

    def ranged(self, cx, surface_y=GROUND_Y):
        self.level.enemies.append(RangedEnemy(
            round(cx - settings.RANGED_ENEMY_WIDTH / 2), surface_y - settings.RANGED_ENEMY_HEIGHT))

    def flyer(self, cx, height, patrol):
        self.level.enemies.append(FlyingEnemy(round(cx), GROUND_Y - height, patrol_range=patrol))

    def checkpoint(self, cx):
        self.checkpoint_xs.append(cx)
        self.level.add_checkpoint(round(cx - settings.CHECKPOINT_WIDTH / 2),
                                  GROUND_Y - settings.CHECKPOINT_HEIGHT)

    def story(self, x, text, max_y=None):
        self.level.add_story_trigger(round(x), text, max_y=max_y)

    # ---------- Trechos neutros ----------
    def plain(self, x, w, basic=0, ranged=0, flyer=0):
        """Chão reto; inimigos distribuídos igualmente ao longo dele."""
        self.ground(x, w)
        walkers = ["b"] * basic + ["r"] * ranged
        for i, kind in enumerate(walkers):
            cx = x + w * (i + 1) / (len(walkers) + 1)
            (self.basic if kind == "b" else self.ranged)(cx)
        for i in range(flyer):
            self.flyer(x + w * (i + 1) / (flyer + 1), 150 + 30 * (i % 2), 120)
        _coins_centered(self.level, x + w * 0.25, 2)
        _coins_centered(self.level, x + w * 0.75, 2)
        return x + w

    def rest(self, x, end_x, cp_x):
        """Chão reto com um checkpoint em cp_x. Inimigos só longe do checkpoint."""
        assert x <= cp_x - 200 and cp_x + 200 <= end_x, (x, cp_x, end_x)
        self.ground(x, end_x - x)
        p = x + 250
        while p <= cp_x - 320:
            self.basic(p)
            p += 380
        _coins_centered(self.level, cp_x - 150, 2)
        _coins_centered(self.level, cp_x + 150, 2)
        self.checkpoint(cp_x)
        self.no_stalactite.append((cp_x - 280, cp_x + 280))
        return end_x

    # ---------- Módulos da floresta ----------
    def spike_run(self, x, ranged=False):
        w = 560
        self.ground(x, w)
        self.spike(x + 260)
        if ranged:
            self.ranged(x + 490)
        else:
            self.basic(x + 430)
        _coins_centered(self.level, x + 110, 2)
        return x + w

    def gap(self, x, g, hard=False):
        """Vão simples de g px (<= 130). Largura total: 680 + g."""
        self.ground(x, 320)
        gx = x + 320
        self.ground(gx + g, 360)
        _coin_arc(self.level, gx - 30, gx + g + 30, rise=45)
        self.basic(x + 160)
        self.basic(gx + g + (190 if hard else 230))
        self.flyer(gx + g / 2, 140, 90)
        if hard:
            self.ranged(gx + g + 310)
        return gx + g + 360

    def steps(self, x, secret=False, hard=False):
        """Duas plataformas sobre um vão de 540 px (largura 1100)."""
        self.ground(x, 240)
        gs = x + 240
        a = self.plat.add(gs + 100, GROUND_Y - 90, 140, 24)
        b = self.plat.add(gs + 320, GROUND_Y - 160, 140, 24)
        self.ground(gs + 540, 320)
        _coins_on(self.level, a)
        _coins_on(self.level, b)
        self.basic(x + 120)
        self.ranged(a.rect.left + 55, GROUND_Y - 90)
        self.basic(gs + 540 + 170)
        if hard:
            self.flyer(gs + 270, 240, 130)
        if secret:
            # Área secreta acima do trecho: moedas de maior valor, opcional.
            self.plat.add(gs + 200, GROUND_Y - 250, 70, 18)
            self.plat.add(gs + 370, GROUND_Y - 320, 70, 18)
            top = self.plat.add(gs + 540, GROUND_Y - 380, 140, 18)
            _coins_centered(self.level, top.rect.centerx, 3, top.rect.top, lift=COIN_LIFT)
            for coin in self.level.coins.coins[-3:]:
                coin.value = settings.SECRET_COIN_VALUE
            self.story(gs + 570, "Uma area secreta escondida sobre a floresta... valeu a pena explorar.",
                       max_y=GROUND_Y - 300)
        return gs + 540 + 320

    def moving_gap(self, x):
        """Vão de 120 px com elevador (largura 880)."""
        self.ground(x, 320)
        gs = x + 320
        self.plat.add_moving(gs + 20, GROUND_Y - 40, 90, 20, offset_x=0, offset_y=-70, speed=1.2)
        self.ground(gs + 120, 440)
        _coin_arc(self.level, gs - 30, gs + 150, rise=45)
        self.spike(gs + 120 + 180)
        self.basic(x + 170)
        self.basic(gs + 120 + 340)
        return gs + 560

    def ruins(self, x, hard=False):
        """Plataformas quebradiças + uma fixa sobre um vão de 760 px (largura 1240)."""
        self.ground(x, 220)
        gs = x + 220
        c1 = self.plat.add_crumbling(gs + 100, GROUND_Y - 60, 120, 24)
        mid = self.plat.add(gs + 320, GROUND_Y - 140, 120, 24)
        c2 = self.plat.add_crumbling(gs + 540, GROUND_Y - 60, 120, 24)
        self.ground(gs + 760, 260)
        for p in (c1, mid, c2):
            _coins_on(self.level, p)
        self.basic(x + 110)
        self.flyer(gs + 380, 190, 150)
        self.basic(gs + 760 + 150)
        if hard:
            self.ranged(mid.rect.centerx, GROUND_Y - 140)
        return gs + 760 + 260

    def h_lift(self, x, gap=360, travel=160):
        """Plataforma móvel horizontal sobre um vão grande (largura 620 + gap)."""
        self.ground(x, 260)
        gs = x + 260
        lift = self.plat.add_moving(gs + 100, GROUND_Y - 100, 100, 20,
                                    offset_x=travel, offset_y=0, speed=1.6)
        self.ground(gs + gap, 300)
        _coins_centered(self.level, lift.rect.centerx + travel / 2, 2, lift.rect.top)
        self.basic(x + 130)
        self.spike(gs + gap + 130, 48)
        self.ranged(gs + gap + 235)
        return gs + gap + 300

    def double_spike(self, x):
        w = 760
        self.ground(x, w)
        self.spike(x + 230)
        self.spike(x + 480)
        self.basic(x + 110)
        self.flyer(x + 380, 150, 110)
        self.basic(x + 650)
        return x + w

    def arena(self, x):
        """Chão de 800 px com vários inimigos e uma prateleira."""
        w = 800
        self.ground(x, w)
        shelf = self.plat.add(x + 330, GROUND_Y - 100, 140, 22)
        _coins_on(self.level, shelf, 2)
        self.basic(x + 190)
        self.ranged(shelf.rect.centerx, GROUND_Y - 100)
        self.basic(x + 650)
        self.flyer(x + 420, 170, 150)
        return x + w

    def pit_stairs(self, x):
        """Poço de 400 px com duas plataformas escalonadas (largura 960)."""
        self.ground(x, 260)
        gs = x + 260
        p1 = self.plat.add(gs + 80, GROUND_Y - 70, 100, 22)
        p2 = self.plat.add(gs + 230, GROUND_Y - 130, 100, 22)
        self.ground(gs + 400, 300)
        _coins_on(self.level, p1)
        _coins_on(self.level, p2)
        self.basic(x + 130)
        self.flyer(gs + 200, 200, 120)
        self.basic(gs + 400 + 170)
        return gs + 400 + 300

    # ---------- Módulos da caverna ----------
    def cave_stairs(self, x):
        """Escada sobre espinho e vão de 140 px (largura 1140)."""
        self.ground(x, 440)
        self.ground(x + 580, 560)
        self.obst.add_spike(x + 100, GROUND_Y - 16, width=64)
        a1 = self.plat.add(x + 190, GROUND_Y - 80, 110, 22)
        a2 = self.plat.add(x + 350, GROUND_Y - 140, 110, 22)
        a3 = self.plat.add(x + 510, GROUND_Y - 80, 110, 22)
        cb = self.plat.add(x + 840, GROUND_Y - 90, 140, 22)
        self.obst.add_spike(x + 880, GROUND_Y - 16, width=64)
        for p in (a1, a2, a3):
            _coins_on(self.level, p)
        _coins_on(self.level, cb, 2)
        self.basic(x + 40)
        self.ranged(x + 650)
        self.flyer(x + 340, 210, 130)
        return x + 1140

    def ashes(self, x):
        """Ponte quebradiça, arcos sobre espinhos e elevador (largura 1600)."""
        self.ground(x, 320)
        self.ground(x + 460, 340)
        self.ground(x + 800, 450)
        self.ground(x + 1380, 220)
        cb = self.plat.add_crumbling(x + 345, GROUND_Y - 60, 90, 22)
        c2 = self.plat.add(x + 570, GROUND_Y - 90, 120, 22)
        c3 = self.plat.add(x + 740, GROUND_Y - 150, 110, 22)
        c4 = self.plat.add(x + 900, GROUND_Y - 90, 110, 22)
        self.plat.add_moving(x + 1265, GROUND_Y - 45, 100, 20, offset_x=0, offset_y=-75, speed=1.35)
        self.obst.add_spike(x + 620, GROUND_Y - 16, width=64)
        self.obst.add_spike(x + 910, GROUND_Y - 16, width=80)
        _coins_centered(self.level, x + 80, 2)
        _coins_on(self.level, cb)
        _coins_on(self.level, c2, 2)
        _coins_on(self.level, c3, 2)
        _coins_on(self.level, c4)
        _coin(self.level, x + 1315, GROUND_Y, lift=175)
        _coins_centered(self.level, x + 1460, 2)
        self.basic(x + 540)
        self.basic(x + 1060)
        self.ranged(x + 1400)
        self.flyer(x + 720, 190, 140)
        return x + 1600

    def fenda(self, x):
        """Puzzle obrigatório da fenda (largura 1600): o salto é largo demais;
        Kael precisa cair na fenda, o que derruba a grande estalactite que
        vira ponte permanente depois do respawn."""
        pit0, pit1 = x + 400, x + 900
        self.ground(x, 400)
        self.ground(pit1, 700)
        self.obst.add_spike(x + 110, GROUND_Y - 16, width=64)
        self.obst.add_spike(x + 1040, GROUND_Y - 16, width=80)
        self.obst.add_stalactite(
            x + 500, GROUND_Y - 500, width=300, height=245,
            trigger_range=0, variant=3, visual_size=(300, 245),
            fall_to_y=690, trigger_on_death_zone=(pit0, pit1),
            persistent_after_landing=True,
        )
        self.no_stalactite.append((pit0 - 150, pit1 + 150))
        d1 = self.plat.add(x + 1140, GROUND_Y - 85, 120, 22)
        d2 = self.plat.add(x + 1310, GROUND_Y - 150, 120, 22)
        _coins_centered(self.level, x + 330, 2)
        # moedas no topo da pedra do puzzle (y=449 depois que ela cai)
        _coins_centered(self.level, x + 650, 3, GROUND_Y - 63)
        _coin_arc(self.level, x + 1046, x + 1114, rise=36, base=SPIKE_ARC_BASE)
        _coins_on(self.level, d1)
        _coins_on(self.level, d2)
        _coins_centered(self.level, x + 1560, 2)
        self.basic(x + 280)
        self.ranged(x + 970)
        self.flyer(x + 1200, 220, 150)
        self.story(x + 100, "A muralha exterior está em ruínas, mas os guardas ainda protegem o acesso.")
        self.story(x + 250, "A fenda e larga demais para um salto comum. O teto rachado parece instavel...")
        return x + 1600

    def gates(self, x):
        """Pontes quebradiças e arcos sobre espinhos e vãos de 120 px (largura 1600)."""
        self.ground(x, 300)
        self.ground(x + 420, 480)
        self.ground(x + 1020, 580)
        e1 = self.plat.add_crumbling(x + 315, GROUND_Y - 55, 90, 22)
        e2 = self.plat.add(x + 550, GROUND_Y - 85, 120, 22)
        e3 = self.plat.add(x + 720, GROUND_Y - 150, 120, 22)
        e4 = self.plat.add(x + 905, GROUND_Y - 85, 110, 22)
        f = self.plat.add(x + 1200, GROUND_Y - 95, 140, 22)
        self.obst.add_spike(x + 580, GROUND_Y - 16, width=64)
        self.obst.add_spike(x + 1270, GROUND_Y - 16, width=64)
        _coins_centered(self.level, x + 90, 2)
        for p in (e1, e2, e3, e4):
            _coins_on(self.level, p)
        _coins_on(self.level, f, 2)
        _coins_centered(self.level, x + 1440, 2)
        self.basic(x + 500)
        self.basic(x + 840)
        self.ranged(x + 1200)
        self.flyer(x + 700, 210, 160)
        return x + 1600

    def double_gap(self, x, hard=False):
        """Duas ilhas e dois vãos de 140 px em sequência (largura 1080)."""
        self.ground(x, 300)
        self.ground(x + 440, 200)
        self.ground(x + 780, 300)
        _coin_arc(self.level, x + 270, x + 470, rise=45)
        _coin_arc(self.level, x + 610, x + 810, rise=45)
        self.basic(x + 120)
        self.flyer(x + 370, 150, 100)
        self.flyer(x + 710, 170, 100)
        self.ranged(x + 960)
        if hard:
            self.spike(x + 780 + 170)
        return x + 1080

    def crumble_run(self, x, hard=False):
        """Três plataformas quebradiças sobre um poço de 620 px (largura 1180)."""
        self.ground(x, 240)
        gs = x + 240
        c1 = self.plat.add_crumbling(gs + 80, GROUND_Y - 60, 90, 22)
        c2 = self.plat.add_crumbling(gs + 260, GROUND_Y - 100, 90, 22)
        c3 = self.plat.add_crumbling(gs + 440, GROUND_Y - 60, 90, 22)
        self.ground(gs + 620, 320)
        for p in (c1, c2, c3):
            _coins_on(self.level, p)
        self.basic(x + 120)
        self.flyer(gs + 300, 190, 130)
        self.basic(gs + 620 + 130)
        if hard:
            self.ranged(gs + 620 + 250)
        return gs + 620 + 320

    def gauntlet(self, x, count=3):
        """Corredor de espinhos com atirador no fim (largura 220 + 240 * count)."""
        w = 220 + 240 * count
        self.ground(x, w)
        for i in range(count):
            self.spike(x + 200 + 240 * i)
        self.ranged(x + w - 90)
        self.flyer(x + w * 0.55, 160, 130)
        return x + w

    def cave_lift(self, x, hard=False):
        """Plataforma móvel horizontal sobre um vão de 420 px (largura 980)."""
        self.ground(x, 260)
        gs = x + 260
        lift = self.plat.add_moving(gs + 90, GROUND_Y - 70, 100, 20,
                                    offset_x=220, offset_y=0, speed=1.6)
        self.ground(gs + 420, 300)
        _coins_centered(self.level, lift.rect.centerx + 110, 2, lift.rect.top)
        self.basic(x + 130)
        self.flyer(gs + 210, 200, 120)
        self.ranged(gs + 420 + 220)
        if hard:
            self.spike(gs + 420 + 100, 48)
        return gs + 420 + 300

    # ---------- Armadilhas de teto da caverna ----------
    def ceiling_traps(self, start_x, end_x):
        import random
        rng = random.Random(1337)   # seed fixa: fase consistente entre tentativas
        small = ((30, 42, 500), (34, 46, 470), (30, 42, 490), (34, 46, 480))
        x = start_x
        i = 0
        while x < end_x:
            if not any(a <= x <= b for a, b in self.no_stalactite):
                if i % 2 == 0:
                    sw, sh, off = rng.choice(small)
                    self.obst.add_stalactite(x, GROUND_Y - off, width=sw, height=sh, trigger_range=44)
                else:
                    self.obst.add_ceiling_spike(x, GROUND_Y - rng.randint(485, 500), width=48, height=78)
            i += 1
            x += rng.randint(330, 470)

    # ---------- Montagem ----------
    def build(self):
        level = self.level
        forest_mid = FOREST_END // 2                                   # 7680
        cave_mid = FOREST_END + (JOURNEY_WIDTH - FOREST_END) // 2      # 23040

        # Região inicial (0 - 900): Núcleo do Retorno e loja
        self.ground(0, 900)
        level.core_pos = (80, GROUND_Y - settings.PLAYER_HEIGHT)
        level.player_start = level.core_pos
        level.shop_zone = ShopZone(300, GROUND_Y - 80, 120, 80)
        _coins_centered(level, 520, 3)          # logo depois da loja (que termina em x=420)
        self.story(150, "Kael reconstruiu o Nucleo do Retorno. Sua jornada de vinganca comeca aqui.")
        self.story(850, "A antiga estrada leva a floresta que outrora protegia sua vila.")

        # ----- FLORESTA, 1a metade (900 - 8010), checkpoint no meio da floresta -----
        x = 900
        x = self.plain(x, 500, basic=1)
        x = self.gap(x, 110)
        x = self.spike_run(x)
        x = self.steps(x, secret=True)
        x = self.moving_gap(x)
        x = self.plain(x, 420, basic=1)
        self.story(x, "As Ruinas guardam conhecimento antigo - foi aqui que Kael reconstruiu o Nucleo.")
        x = self.ruins(x)
        x = self.double_spike(x)
        x = self.rest(x, forest_mid + 330, forest_mid)                 # CHECKPOINT 1 (meio da floresta)

        # ----- FLORESTA, 2a metade (até o limite com a caverna) - mais difícil -----
        x = self.arena(x)
        x = self.gap(x, 130, hard=True)
        x = self.spike_run(x, ranged=True)
        x = self.pit_stairs(x)
        self.story(x, "O castelo de Vharok se ergue no horizonte. O fim da jornada se aproxima.")
        x = self.h_lift(x)
        x = self.steps(x, hard=True)
        x = self.ruins(x, hard=True)
        x = self.spike_run(x)
        self.story(FOREST_END - 330, "O caminho antigo termina num desfiladeiro. Encontre uma passagem segura.")
        x = self.rest(x, FOREST_END + 330, FOREST_END)                 # CHECKPOINT 2 (transição floresta -> caverna)

        # ----- CAVERNA, 1a metade (até o meio da caverna) -----
        x = self.cave_stairs(x)
        x = self.plain(x, 230, basic=1)
        x = self.gauntlet(x, count=3)
        x = self.double_gap(x)
        x = self.cave_lift(x)
        x = self.crumble_run(x)
        self.story(x, "A fumaça cobre a estrada. As defesas do castelo estão cada vez mais próximas.")
        x = self.ashes(x)
        x = self.rest(x, x + 400, x + 200)                             # CHECKPOINT 3 (meio da caverna)
        assert self.checkpoint_xs[-1] == cave_mid, self.checkpoint_xs

        # ----- CAVERNA, 2a metade (puzzle da fenda + portões) - mais difícil -----
        x = self.fenda(x)
        x = self.gates(x)
        x = self.cave_lift(x, hard=True)
        x = self.crumble_run(x, hard=True)
        x = self.gauntlet(x, count=4)

        # Salão final antes do castelo
        end = JOURNEY_WIDTH
        self.story(x + 300, "As portas do castelo se abrem. Vharok o espera la dentro.")
        self.plain(x, end - x, basic=2, ranged=2, flyer=1)
        level.boss_trigger = pygame.Rect(end - 100, GROUND_Y - 200, 40, 200)

        # Estalactites-armadilha por toda a caverna (depois do crossfade do fundo)
        self.ceiling_traps(FOREST_END + 520, end - 400)

        # Gatilhos de história em ordem de x (check_story_triggers percorre a lista em ordem)
        level.story_triggers.sort(key=lambda t: t["x"])


def build_main_level():
    """Constrói a Fase 1 - Jornada: 30 telas (Floresta 15 + Caverna 15) em um
    mapa contínuo, com apenas 3 checkpoints (meio da floresta, transição
    floresta -> caverna e meio da caverna)."""
    level = Level(JOURNEY_WIDTH, settings.SCREEN_HEIGHT)
    _JourneyBuilder(level).build()

    # Background em camadas de parallax: floresta (0 - FOREST_END) e caverna
    # (FOREST_END - fim), com crossfade de 1000 px centrado no limite.
    # Mantém fallback se faltarem assets.
    if SegmentedWorldBackdrop.available():
        level.backdrop = SegmentedWorldBackdrop(
            JOURNEY_WIDTH, transition=(FOREST_END - 500, FOREST_END + 500))
    elif MundoBackdrop.available():
        level.backdrop = MundoBackdrop(JOURNEY_WIDTH)
    else:
        level.backdrop = VillageBackdrop(JOURNEY_WIDTH, GROUND_Y)

    return level


def build_boss_level():
    """Constrói a Fase 2 - Castelo de Vharok (arena do Boss)."""
    import random
    rng = random.Random(7)

    level_width = 1400
    level_height = settings.SCREEN_HEIGHT
    level = Level(level_width, level_height, is_boss_level=True)

    plat = level.platforms
    ground_h = 64
    plat.add(0, GROUND_Y, level_width, ground_h, is_ground=True)

    level.player_start = (60, GROUND_Y - settings.PLAYER_HEIGHT)
    level.core_pos = level.player_start  # respawn na entrada da arena, sem voltar à Região 1

    arena_left = 40
    arena_right = level_width - 40
    boss_x = level_width - 220
    boss_y = GROUND_Y - settings.BOSS_HEIGHT
    level.boss = Boss(boss_x, boss_y, arena_left, arena_right)

    # Background exclusivo da arena (boss_arena.png). Se o arquivo faltar,
    # cai no CastleBackdrop procedural de antes.
    if BossArenaBackdrop.available():
        level.backdrop = BossArenaBackdrop(level_width, GROUND_Y)
    else:
        level.backdrop = CastleBackdrop(level_width, GROUND_Y)

    return level
