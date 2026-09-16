"""
config/settings.py
Configurações globais do jogo Vengeance Reborn.
Centraliza constantes para facilitar ajustes de balanceamento.
"""

# ---------- Janela ----------
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 576
FPS = 60
GAME_TITLE = "Vengeance Reborn"

# ---------- Cores (paleta simples, sem assets externos) ----------
COLOR_BG_SKY = (25, 20, 40)
COLOR_BG_FAR = (40, 32, 60)
COLOR_GROUND = (60, 45, 70)
COLOR_GROUND_TOP = (90, 70, 100)
COLOR_PLATFORM = (80, 60, 90)
COLOR_PLAYER = (230, 200, 90)
COLOR_PLAYER_ATTACK = (255, 255, 255)
COLOR_ENEMY = (180, 50, 60)
COLOR_ENEMY_RANGED = (150, 70, 160)
COLOR_BOSS = (120, 20, 30)
COLOR_COIN = (255, 210, 60)
COLOR_SPIKE = (200, 200, 210)
SPIKE_DAMAGE = 12
COLOR_TEXT = (240, 240, 245)
COLOR_TEXT_SHADOW = (10, 10, 15)
COLOR_HP_BG = (50, 20, 20)
COLOR_HP_FG = (200, 40, 40)
COLOR_HP_BOSS_FG = (150, 20, 100)
COLOR_UI_PANEL = (20, 16, 30)
COLOR_UI_BORDER = (120, 100, 140)
COLOR_CORE = (90, 200, 220)
COLOR_MOVING_PLATFORM = (70, 100, 120)
COLOR_CRUMBLING_PLATFORM = (110, 80, 60)
COLOR_CHECKPOINT_OFF = (110, 100, 120)
COLOR_CHECKPOINT_ON = (90, 230, 160)
COLOR_SECRET = (200, 120, 220)

# ---------- Física ----------
GRAVITY = 0.9
MAX_FALL_SPEED = 18
PLAYER_SPEED = 5.2
PLAYER_JUMP_FORCE = -16.5
COYOTE_TIME_FRAMES = 6          # frames de tolerância para pular após sair da plataforma
JUMP_BUFFER_FRAMES = 6          # frames de tolerância para bufferizar o pulo

# ---------- Player ----------
PLAYER_WIDTH = 34
PLAYER_HEIGHT = 46
PLAYER_MAX_HEALTH = 100         # agora é uma barra (0-100), não corações
PLAYER_INVULN_FRAMES = 60       # invencibilidade após tomar dano
PLAYER_ATTACK_DAMAGE = 1
PLAYER_ATTACK_DURATION = 14
PLAYER_ATTACK_COOLDOWN = 20
PLAYER_ATTACK_RANGE = 40
PLAYER_ATTACK_HEIGHT = 30
KNOCKBACK_X = 6
KNOCKBACK_Y = -6

# ---------- Dash (tecla Q) ----------
DASH_SPEED = 13.0
DASH_DURATION_FRAMES = 10        # duração do impulso (sem gravidade)
DASH_COOLDOWN_FRAMES = 45
DASH_INVULN_FRAMES = 12          # i-frames concedidos durante o dash
COLOR_DASH_TRAIL = (210, 225, 255)

# ---------- Wall slide / wall jump ----------
WALL_SLIDE_MAX_FALL_SPEED = 2.5  # queda é freada até essa velocidade ao deslizar na parede
WALL_JUMP_FORCE_X = 6.5          # impulso horizontal para longe da parede
WALL_JUMP_FORCE_Y = -15.0
WALL_JUMP_LOCK_FRAMES = 10       # frames em que o input horizontal é ignorado, pra garantir o afastamento da parede

# ---------- Pulo duplo (melhoria da loja) ----------
UPGRADE_DOUBLE_JUMP_COST = 40

# ---------- Cura (item consumível da loja) ----------
SHOP_HEAL_COST = 15
SHOP_HEAL_AMOUNT = 25       # cura 1/4 da vida base por compra

# ---------- Ímã de moedas (melhoria da loja) ----------
UPGRADE_MAGNET_COST = 35
COIN_MAGNET_RADIUS = 110
COIN_MAGNET_PULL_SPEED = 6.5

# ---------- Carga extra de dash (melhoria da loja) ----------
UPGRADE_DASH_CHARGE_COST = 45

# ---------- Recompensas e respawn de inimigos ----------
ENEMY_COIN_DROP_BASIC = 10
ENEMY_COIN_DROP_RANGED = 15
ENEMY_COIN_DROP_BOSS = 100
ENEMY_RESPAWN_SECONDS = 60
ENEMY_RESPAWN_FRAMES = ENEMY_RESPAWN_SECONDS * FPS

# ---------- Checkpoint/loja ----------
CHECKPOINT_SHOP_RANGE_PADDING_X = 70
CHECKPOINT_SHOP_RANGE_PADDING_Y = 40

# ---------- Sentinela de parede (novo mob da Fenda Vertical) ----------
WALL_SENTINEL_WIDTH = 26
WALL_SENTINEL_HEIGHT = 26
WALL_SENTINEL_HEALTH = 2
WALL_SENTINEL_DAMAGE = 8
WALL_SENTINEL_COOLDOWN = 100          # frames entre disparos
WALL_SENTINEL_VERTICAL_RANGE = 75     # faixa de altura em que ela "enxerga" o jogador
COLOR_WALL_SENTINEL = (190, 90, 200)
ENEMY_COIN_DROP_SENTINEL = 8

# ---------- Corvo Sombrio (novo mob voador) ----------
FLYING_ENEMY_WIDTH = 30
FLYING_ENEMY_HEIGHT = 22
FLYING_ENEMY_HEALTH = 2
FLYING_ENEMY_DAMAGE = 8
FLYING_ENEMY_SPEED = 2.4
FLYING_ENEMY_PATROL_RANGE = 140   # quanto se afasta do ponto de origem, pra cada lado
FLYING_ENEMY_BOB_AMPLITUDE = 40   # altura do zigue-zague vertical
FLYING_ENEMY_BOB_SPEED = 0.05
COLOR_FLYING_ENEMY = (70, 60, 90)
ENEMY_COIN_DROP_FLYING = 10

# ---------- Plataformas móveis e quebradiças ----------
MOVING_PLATFORM_SPEED = 1.4
CRUMBLE_SHAKE_FRAMES = 25        # tempo pisando antes de despencar
CRUMBLE_RESPAWN_FRAMES = 150     # tempo até a plataforma reaparecer

# ---------- Checkpoints ----------
CHECKPOINT_WIDTH = 28
CHECKPOINT_HEIGHT = 60

# ---------- Área secreta ----------
SECRET_COIN_VALUE = 5

# ---------- Inimigos ----------
BASIC_ENEMY_WIDTH = 32
BASIC_ENEMY_HEIGHT = 32
BASIC_ENEMY_SPEED = 1.6
BASIC_ENEMY_HEALTH = 2
BASIC_ENEMY_DAMAGE = 10
BASIC_ENEMY_PATROL_RANGE = 90

RANGED_ENEMY_WIDTH = 30
RANGED_ENEMY_HEIGHT = 34
RANGED_ENEMY_HEALTH = 2
RANGED_ENEMY_DAMAGE = 10
RANGED_ENEMY_RANGE = 320
RANGED_ENEMY_COOLDOWN = 90
PROJECTILE_SPEED = 6
PROJECTILE_SIZE = 8

# ---------- Boss ----------
BOSS_WIDTH = 90
BOSS_HEIGHT = 110
BOSS_MAX_HEALTH = 30
BOSS_DAMAGE = 18
BOSS_SPEED = 2.2
BOSS_ATTACK_COOLDOWN = 75
BOSS_SLAM_TELEGRAPH = 40
BOSS_SLAM_ACTIVE_FRAMES = 16          # quanto tempo o golpe de terremoto fica realmente "ativo" podendo acertar
BOSS_SLAM_REACH = 130                 # alcance a partir do CENTRO do Boss (tem que passar da distância em que ele para de perseguir)
BOSS_PHASE2_HEALTH_RATIO = 0.5
BOSS_BARRAGE_PROJECTILE_COUNT = 5
BOSS_BARRAGE_PROJECTILE_SPEED = 10
BOSS_BARRAGE_TELEGRAPH = 45
BOSS_CHASE_STOP_DISTANCE = 70

# ---------- Economia / Progressão ----------
COIN_VALUE = 1
UPGRADE_HEALTH_COST = 10
UPGRADE_DAMAGE_COST = 15
UPGRADE_JUMP_COST = 20
UPGRADE_HEALTH_AMOUNT = 20   # por nível (5 níveis = +100 de vida máxima)
UPGRADE_DAMAGE_AMOUNT = 1
UPGRADE_JUMP_AMOUNT = 1.5
UPGRADE_ATTACK_SPEED_COST = 18
UPGRADE_ATTACK_SPEED_AMOUNT = 2   # reduz frames de cooldown por nível
MIN_ATTACK_COOLDOWN = 8
MAX_UPGRADE_LEVEL = 5

# ---------- Áudio (gerado proceduralmente, sem arquivos externos) ----------
AUDIO_SAMPLE_RATE = 44100
MASTER_VOLUME = 0.35

# ---------- Screen shake ----------
SHAKE_DECAY = 0.85

# ---------- Save ----------
SAVE_FILE = "savegame.json"

# ---------- Estados do jogo ----------
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_SHOP = "shop"
STATE_GAME_OVER = "game_over"
STATE_VICTORY = "victory"
STATE_BOSS_INTRO = "boss_intro"
