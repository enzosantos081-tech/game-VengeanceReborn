"""
world/level.py
Responsável pela criação e gerenciamento da fase. Conforme a seção 16
do documento, a Fase 1 (Jornada) é dividida visualmente em 4 regiões
dentro do MESMO mapa (sem telas de carregamento separadas):
  Região 1 - Área inicial (Núcleo do Retorno + Loja)
  Região 2 - Floresta (plataformas, inimigos, buracos, moedas)
  Região 3 - Ruínas (obstáculos maiores, inimigos, plataformas difíceis)
  Região 4 - Entrada do castelo (acesso à Fase 2)
A Fase 2 (Castelo de Vharok) é construída separadamente por build_boss_level().
"""

import pygame
from config import settings
from world.platforms import PlatformGroup
from world.obstacles import ObstacleGroup
from world.coins import CoinGroup
from world.checkpoints import Checkpoint
from enemies.basic_enemy import BasicEnemy, RangedEnemy
from enemies.wall_sentinel import WallSentinel
from enemies.flying_enemy import FlyingEnemy
from enemies.boss import Boss
from systems import collision
from systems.shop import ShopZone

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
        new_rect, on_ground, wall_dir = collision.move_and_collide(player.rect, vel_x, vel_y, solids)
        player.rect = new_rect
        player.on_ground = on_ground
        # Só conta como "encostado na parede" se estiver no ar - andar
        # colado numa parede no chão não deve ativar o wall slide.
        player.touching_wall = wall_dir if not on_ground else 0
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
        new_rect, on_ground, _wall_dir = collision.move_and_collide(enemy.rect, vel_x, vel_y, solids)
        enemy.rect = new_rect
        if on_ground:
            enemy.vel_y = 0

    def has_ground_ahead(self, rect, direction):
        return collision.ground_exists_below(rect, direction, self.platforms.rects())

    def rect_hits_solid(self, rect):
        return collision.rect_collides_any(rect, self.platforms.rects())

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
        self.obstacles.update(player)
        coins_collected = self.coins.update(player, particles)
        if self.boss:
            self.boss.update(self, player)
        return coins_collected

    def living_enemies(self):
        return [e for e in self.enemies if e.alive]

    # ---------- Desenho ----------
    def draw_background(self, surface, camera_x):
        surface.fill(settings.COLOR_BG_SKY)
        # Parallax simples: montanhas/silhuetas distantes
        for i, (bx, bw, bh) in enumerate(self.background_decor):
            factor = 0.3
            sx = bx - camera_x * factor
            if -bw < sx < settings.SCREEN_WIDTH:
                pygame.draw.polygon(
                    surface, settings.COLOR_BG_FAR,
                    [(sx, GROUND_Y), (sx + bw / 2, GROUND_Y - bh), (sx + bw, GROUND_Y)],
                )

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
    """Constrói a Fase 1 - Jornada, com as regiões 1 a 4."""
    import random
    rng = random.Random(42)  # seed fixa: fase consistente entre tentativas

    level_width = 6400
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

    level.obstacles.add_spike(1050, GROUND_Y - 16)
    level.obstacles.add_spike(2650, GROUND_Y - 16)

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

    level.add_story_trigger(4740, "Um poco vertical se abre entre as pedras - talvez valha a pena escalar.")

    # ---------- Fenda Vertical: área bônus opcional (acima da Região 3) ----------
    # Estrutura flutuante acima do chão normal (que continua intacto por
    # baixo, sem bloquear o caminho principal) - inspirada na área secreta
    # da Região 2, mas usando de verdade o wall jump: duas paredes altas
    # flanqueiam um corredor estreito. A entrada é por cima (descendo de
    # uma escada de plataformas), então o jogador desce pelo corredor
    # encadeando wall jumps para pegar o tesouro no meio do caminho. Se
    # errar e cair, só volta a cair no chão normal logo abaixo - sem
    # punição, pode tentar de novo.
    plat.add(4750, 390, 60, 18, is_ground=False)
    plat.add(4820, 270, 60, 18, is_ground=False)
    plat.add(4750, 150, 60, 18, is_ground=False)

    fenda_wall_top = 70
    fenda_wall_height = 350
    fenda_left_x = 4840
    fenda_wall_thickness = 30
    fenda_corridor_width = 64
    fenda_right_x = fenda_left_x + fenda_wall_thickness + fenda_corridor_width  # 4934

    plat.add(fenda_left_x, fenda_wall_top, fenda_wall_thickness, fenda_wall_height, is_ground=False)
    plat.add(fenda_right_x, fenda_wall_top, fenda_wall_thickness, fenda_wall_height, is_ground=False)

    # Espinhos grudados na parede direita: obrigam a preferir a esquerda
    # nessa altura durante a descida.
    level.obstacles.add_wall_spike(fenda_right_x - 16, 320, 16, 60, facing="left")

    # Sentinelas de parede (novo mob): só disparam quando o jogador está
    # na mesma faixa de altura que elas.
    level.enemies.append(WallSentinel(fenda_left_x + 2, 237, facing_dir=1))
    level.enemies.append(WallSentinel(fenda_right_x + 2, 120, facing_dir=-1))

    # Saliência com o tesouro, grudada na parede direita - só dá pra
    # alcançar com um wall jump bem cronometrado saindo da esquerda.
    plat.add(fenda_right_x - 26, 250, 26, 18, is_ground=False)
    level.coins.add(fenda_right_x - 20, 225, value=settings.SECRET_COIN_VALUE)
    level.coins.add(4780, 120, value=settings.SECRET_COIN_VALUE)

    level.add_story_trigger(4855, "O eco de moedas la embaixo... valeu a pena escalar a fenda.", max_y=260)

    level.add_story_trigger(4900, "O castelo de Vharok se ergue no horizonte. O fim da jornada se aproxima.")

    # ---------- Região 4: Entrada do castelo (4900 - 6400) ----------
    plat.add(4900, GROUND_Y, 1500, ground_h, is_ground=True)
    for cx in (5000, 5040, 5080, 6100, 6140, 6180):
        level.coins.add(cx, GROUND_Y - 40)
    level.enemies.append(BasicEnemy(5200, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(BasicEnemy(5800, GROUND_Y - settings.BASIC_ENEMY_HEIGHT))
    level.enemies.append(FlyingEnemy(5600, GROUND_Y - 160, patrol_range=170))

    level.add_checkpoint(6200, GROUND_Y - settings.CHECKPOINT_HEIGHT)
    level.add_story_trigger(6250, "As portas do castelo se abrem. Vharok o espera la dentro.")

    level.boss_trigger = pygame.Rect(6300, GROUND_Y - 200, 40, 200)

    _add_decor(level, rng, -200, level_width + 200)

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

    _add_decor(level, rng, -100, level_width + 100)

    return level
