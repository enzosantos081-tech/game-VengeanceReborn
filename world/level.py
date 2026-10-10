"""
world/level.py
Responsável pela criação e gerenciamento da fase. A Fase 1 (Jornada) é
dividida visualmente em 8 regiões dentro do MESMO mapa de 12.800 px
(sem telas de carregamento separadas):
  Regiões 1 a 4 - Área inicial, floresta, ruínas e primeira aproximação do castelo
  Região 5 - Desfiladeiro
  Região 6 - Caminho das cinzas
  Região 7 - Muralha exterior
  Região 8 - Portões do castelo (acesso à Fase 2)
Todas as regiões compartilham a MESMA identidade visual (ver
world/background.py) - são só trechos de conteúdo (plataformas,
inimigos, decoração) dentro de um único cenário contínuo, não biomas
separados.
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
            enemy.update(self, player)
        self.enemies = [e for e in self.enemies if True]  # mantidos p/ desenhar corpo caído; sem despawn
        self.obstacles.update(player, ground_y=GROUND_Y)
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

        for enemy in self.enemies:
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


def build_main_level():
    """Constrói a Fase 1 - Jornada, com oito regiões em um mapa contínuo."""
    import random
    rng = random.Random(42)  # seed fixa: fase consistente entre tentativas

    # A Jornada agora tem 12.800 px de extensão horizontal. As quatro
    # regiões originais permanecem intactas; as regiões 5 a 8 ampliam a
    # travessia antes da entrada para o castelo de Vharok.
    level_width = 12800
    level_height = settings.SCREEN_HEIGHT
    level = Level(level_width, level_height)

    plat = level.platforms
    ground_h = 64

    # ---------- Região 1: Área inicial (0 - 900) ----------
    plat.add(0, GROUND_Y, 900, ground_h, is_ground=True)
    level.core_pos = (80, GROUND_Y - settings.PLAYER_HEIGHT)
    level.player_start = level.core_pos
    level.shop_zone = ShopZone(300, GROUND_Y - 80, 120, 80)
    level.coins.add(420, GROUND_Y - 40)
    level.coins.add(460, GROUND_Y - 40)
    level.coins.add(500, GROUND_Y - 40)

    level.add_story_trigger(150, "Kael reconstruiu o Nucleo do Retorno. Sua jornada de vinganca comeca aqui.")
    level.add_story_trigger(850, "A antiga estrada leva a floresta que outrora protegia sua vila.")

    # ---------- Região 2: Floresta (900 - 3000) ----------
    plat.add(900, GROUND_Y, 300, ground_h, is_ground=True)
    # buraco entre 1200 e 1320
    plat.add(1320, GROUND_Y, 260, ground_h, is_ground=True)
    plat.add(1680, GROUND_Y - 90, 140, 24)
    plat.add(1900, GROUND_Y - 160, 140, 24)
    plat.add(2120, GROUND_Y, 320, ground_h, is_ground=True)
    # buraco entre 2440 e 2560
    plat.add(2560, GROUND_Y, 440, ground_h, is_ground=True)

    # Plataforma móvel atravessando o segundo buraco (rota alternativa/mais segura)
    plat.add_moving(2460, GROUND_Y - 40, 90, 20, offset_x=0, offset_y=-70, speed=1.2)

    # Checkpoint ao fim da Região 2
    level.add_checkpoint(2900, GROUND_Y - settings.CHECKPOINT_HEIGHT)

    for cx in (960, 1000, 1360, 1400, 1720, 1940, 2160, 2600, 2650, 2700):
        level.coins.add(cx, GROUND_Y - 40)

    level.obstacles.add_spike(1050, GROUND_Y - 16, width=64)
    level.obstacles.add_spike(2650, GROUND_Y - 16, width=64)

    level.enemies.append(BasicEnemy(1000, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(BasicEnemy(2200, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(RangedEnemy(1720, GROUND_Y - 90 - settings.RANGED_ENEMY_HEIGHT))
    level.enemies.append(FlyingEnemy(1260, GROUND_Y - 140, patrol_range=90))

    # ---------- Área secreta: trecho alto acima da Região 2 ----------
    # Sequência de plataformas pequenas levando a um esconderijo com moedas
    # de maior valor - não é necessária para progredir, recompensa exploração.
    plat.add(1780, GROUND_Y - 250, 70, 18)
    plat.add(1950, GROUND_Y - 320, 70, 18)
    plat.add(2120, GROUND_Y - 380, 140, 18)
    level.coins.add(2150, GROUND_Y - 420, value=settings.SECRET_COIN_VALUE)
    level.coins.add(2190, GROUND_Y - 420, value=settings.SECRET_COIN_VALUE)
    level.coins.add(2230, GROUND_Y - 420, value=settings.SECRET_COIN_VALUE)
    level.add_story_trigger(2150, "Uma area secreta escondida sobre a floresta... valeu a pena explorar.", max_y=GROUND_Y - 300)

    level.add_story_trigger(3000, "As Ruinas guardam conhecimento antigo - foi aqui que Kael reconstruiu o Nucleo.")

    # ---------- Região 3: Ruínas (3000 - 4900) ----------
    plat.add(3000, GROUND_Y, 220, ground_h, is_ground=True)
    plat.add_crumbling(3320, GROUND_Y - 60, 120, 24)
    plat.add(3540, GROUND_Y - 140, 120, 24)
    plat.add_crumbling(3760, GROUND_Y - 60, 120, 24)
    plat.add(3980, GROUND_Y, 260, ground_h, is_ground=True)
    plat.add_moving(4340, GROUND_Y - 100, 100, 20, offset_x=160, offset_y=0, speed=1.6)
    plat.add(4600, GROUND_Y, 300, ground_h, is_ground=True)

    level.add_checkpoint(4650, GROUND_Y - settings.CHECKPOINT_HEIGHT)

    level.obstacles.add_spike(4020, GROUND_Y - 16, width=64)
    level.obstacles.add_spike(4680, GROUND_Y - 16, width=48)

    for cx in (3350, 3570, 3790, 4020, 4060, 4370, 4400, 4650, 4700, 4750):
        level.coins.add(cx, GROUND_Y - 90)

    level.enemies.append(BasicEnemy(3030, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(BasicEnemy(4010, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(RangedEnemy(4360, GROUND_Y - 100 - settings.RANGED_ENEMY_HEIGHT))
    level.enemies.append(BasicEnemy(4630, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(FlyingEnemy(3650, GROUND_Y - 190, patrol_range=150))

    level.add_story_trigger(4900, "O castelo de Vharok se ergue no horizonte. O fim da jornada se aproxima.")

    # ---------- Região 4: Entrada do castelo (4900 - 6400) ----------
    # Mantém o trecho original como primeira visão do castelo, mas o portão
    # final só é alcançado depois das novas regiões.
    plat.add(4900, GROUND_Y, 1500, ground_h, is_ground=True)
    for cx in (5000, 5040, 5080, 6100, 6140, 6180):
        level.coins.add(cx, GROUND_Y - 40)
    level.enemies.append(BasicEnemy(5200, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(BasicEnemy(5800, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(FlyingEnemy(5600, GROUND_Y - 160, patrol_range=170))
    level.add_checkpoint(6200, GROUND_Y - settings.CHECKPOINT_HEIGHT)

    # ---------- Região 5: Desfiladeiro (6400 - 8000) ----------
    # Saltos sobre vãos curtos, com plataformas elevadas como rotas seguras.
    plat.add(6400, GROUND_Y, 340, ground_h, is_ground=True)
    plat.add(6860, GROUND_Y, 440, ground_h, is_ground=True)
    plat.add(7040, GROUND_Y - 100, 120, 22)
    plat.add(7220, GROUND_Y - 170, 120, 22)
    plat.add(7440, GROUND_Y, 560, ground_h, is_ground=True)
    plat.add(7600, GROUND_Y - 90, 130, 22)
    level.obstacles.add_spike(6960, GROUND_Y - 16, width=64)
    level.obstacles.add_spike(7740, GROUND_Y - 16, width=64)
    for cx, cy in ((6460, GROUND_Y - 40), (6500, GROUND_Y - 40),
                   (7060, GROUND_Y - 145), (7240, GROUND_Y - 215),
                   (7500, GROUND_Y - 40), (7540, GROUND_Y - 40),
                   (7620, GROUND_Y - 135), (7820, GROUND_Y - 40)):
        level.coins.add(cx, cy)
    level.enemies.append(BasicEnemy(6900, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(RangedEnemy(7510, GROUND_Y - settings.RANGED_ENEMY_HEIGHT))
    level.enemies.append(FlyingEnemy(7200, GROUND_Y - 210, patrol_range=130))
    level.add_checkpoint(7900, GROUND_Y - settings.CHECKPOINT_HEIGHT)
    level.add_story_trigger(6500, "O caminho antigo termina num desfiladeiro. Encontre uma passagem segura.")

    # Perigos de teto exclusivos da caverna (x >= 7000). As camadas
    # parallax_cave já fornecem decoração rochosa; estas instâncias usam
    # o comportamento de aviso/queda existente em ObstacleGroup.
    for sx, sy, sw, sh in (
        (7130, GROUND_Y - 500, 30, 42),
        (7480, GROUND_Y - 470, 34, 46),
        (8030, GROUND_Y - 490, 30, 42),
        (8580, GROUND_Y - 470, 34, 46),
        (9060, GROUND_Y - 500, 30, 42),
        (9740, GROUND_Y - 485, 34, 46),
        (10380, GROUND_Y - 495, 30, 42),
        (11020, GROUND_Y - 470, 34, 46),
        (11880, GROUND_Y - 490, 30, 42),
        (12500, GROUND_Y - 480, 34, 46),
    ):
        level.obstacles.add_stalactite(sx, sy, width=sw, height=sh, trigger_range=44)

    # ---------- Região 6: Caminho das cinzas (8000 - 9600) ----------
    # Trecho da caverna simplificado: removidas as duas paredes e a
    # plataforma elevada que só servia à rota vertical antiga.
    # O vão de 140 px entre o chão e a próxima área pode ser atravessado
    # com o pulo normal ou dash; a plataforma quebradiça oferece apoio opcional.
    plat.add(8000, GROUND_Y, 320, ground_h, is_ground=True)
    plat.add(8460, GROUND_Y, 340, ground_h, is_ground=True)
    plat.add_crumbling(8350, GROUND_Y - 70, 90, 22)
    plat.add(8580, GROUND_Y - 110, 120, 22)
    plat.add_crumbling(8750, GROUND_Y - 70, 100, 22)
    plat.add(8800, GROUND_Y, 450, ground_h, is_ground=True)
    plat.add_moving(9220, GROUND_Y - 45, 100, 20, offset_x=0, offset_y=-75, speed=1.35)
    plat.add(9380, GROUND_Y, 220, ground_h, is_ground=True)
    level.obstacles.add_spike(8500, GROUND_Y - 16, width=64)
    level.obstacles.add_spike(8910, GROUND_Y - 16, width=80)
    for cx, cy in ((8050, GROUND_Y - 40), (8090, GROUND_Y - 40),
                   (8370, GROUND_Y - 110), (8610, GROUND_Y - 150),
                   (8780, GROUND_Y - 110), (8840, GROUND_Y - 40),
                   (8880, GROUND_Y - 40), (9270, GROUND_Y - 90),
                   (9410, GROUND_Y - 40), (9450, GROUND_Y - 40)):
        level.coins.add(cx, cy)
    level.enemies.append(BasicEnemy(8500, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(BasicEnemy(8970, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(RangedEnemy(9400, GROUND_Y - settings.RANGED_ENEMY_HEIGHT))
    level.enemies.append(FlyingEnemy(8720, GROUND_Y - 190, patrol_range=140))
    level.add_checkpoint(9500, GROUND_Y - settings.CHECKPOINT_HEIGHT)
    level.add_story_trigger(8100, "A fumaça cobre a estrada. As defesas do castelo estão cada vez mais próximas.")

    # ---------- Região 7: Muralha exterior (9600 - 11200) ----------
    plat.add(9600, GROUND_Y, 400, ground_h, is_ground=True)
    plat.add(10140, GROUND_Y, 360, ground_h, is_ground=True)
    plat.add(10020, GROUND_Y - 100, 100, 22)
    plat.add_moving(10480, GROUND_Y - 80, 110, 20, offset_x=100, offset_y=-35, speed=1.5)
    plat.add(10500, GROUND_Y, 700, ground_h, is_ground=True)
    plat.add(10720, GROUND_Y - 120, 130, 22)
    plat.add(10910, GROUND_Y - 190, 120, 22)
    level.obstacles.add_spike(9710, GROUND_Y - 16, width=64)
    level.obstacles.add_spike(10640, GROUND_Y - 16, width=80)
    for cx, cy in ((9650, GROUND_Y - 40), (9690, GROUND_Y - 40),
                   (10040, GROUND_Y - 140), (10180, GROUND_Y - 40),
                   (10220, GROUND_Y - 40), (10530, GROUND_Y - 40),
                   (10750, GROUND_Y - 160), (10940, GROUND_Y - 230),
                   (11000, GROUND_Y - 40), (11040, GROUND_Y - 40)):
        level.coins.add(cx, cy)
    level.enemies.append(BasicEnemy(10200, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(RangedEnemy(10570, GROUND_Y - settings.RANGED_ENEMY_HEIGHT))
    level.enemies.append(FlyingEnemy(10800, GROUND_Y - 220, patrol_range=150))
    level.add_checkpoint(11100, GROUND_Y - settings.CHECKPOINT_HEIGHT)
    level.add_story_trigger(9700, "A muralha exterior está em ruínas, mas os guardas ainda protegem o acesso.")

    # ---------- Região 8: Portões do castelo (11200 - 12800) ----------
    plat.add(11200, GROUND_Y, 300, ground_h, is_ground=True)
    plat.add(11620, GROUND_Y, 480, ground_h, is_ground=True)
    plat.add(11780, GROUND_Y - 90, 120, 22)
    plat.add(11960, GROUND_Y - 155, 120, 22)
    plat.add(12220, GROUND_Y, 580, ground_h, is_ground=True)
    plat.add(12380, GROUND_Y - 95, 140, 22)
    level.obstacles.add_spike(11690, GROUND_Y - 16, width=64)
    level.obstacles.add_spike(12470, GROUND_Y - 16, width=64)
    for cx, cy in ((11250, GROUND_Y - 40), (11290, GROUND_Y - 40),
                   (11790, GROUND_Y - 130), (11980, GROUND_Y - 195),
                   (12040, GROUND_Y - 40), (12080, GROUND_Y - 40),
                   (12260, GROUND_Y - 40), (12300, GROUND_Y - 40),
                   (12400, GROUND_Y - 140), (12550, GROUND_Y - 40),
                   (12590, GROUND_Y - 40), (12630, GROUND_Y - 40)):
        level.coins.add(cx, cy)
    level.enemies.append(BasicEnemy(11700, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(BasicEnemy(12120, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(RangedEnemy(12400, GROUND_Y - settings.RANGED_ENEMY_HEIGHT))
    level.enemies.append(FlyingEnemy(11900, GROUND_Y - 210, patrol_range=160))
    level.add_checkpoint(12580, GROUND_Y - settings.CHECKPOINT_HEIGHT)
    level.add_story_trigger(12400, "As portas do castelo se abrem. Vharok o espera la dentro.")
    level.boss_trigger = pygame.Rect(12700, GROUND_Y - 200, 40, 200)

    # Background panorâmico em três trechos: deserto (0-6000), transição
    # (6000-7000) e caverna (7000-12800). Mantém fallback se faltarem assets.
    if SegmentedWorldBackdrop.available():
        level.backdrop = SegmentedWorldBackdrop(level_width)
    elif MundoBackdrop.available():
        level.backdrop = MundoBackdrop(level_width)
    else:
        level.backdrop = VillageBackdrop(level_width, GROUND_Y)


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
