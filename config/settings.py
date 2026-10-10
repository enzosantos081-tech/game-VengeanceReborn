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
# Velocidade em pixels por segundo; duração e recarga usam milissegundos.
# Antes: 13 px/frame por 10 frames (~130 px em 167 ms) e recarga de 45 frames.
DASH_SPEED = 600.0
DASH_DURATION_MS = 180           # ~108 px a 60 FPS, com início/fim definidos
DASH_COOLDOWN_MS = 1000           # recarga de 1 s após gastar a carga
DASH_INVULN_FRAMES = 12           # mantém os i-frames existentes
COLOR_DASH_TRAIL = (210, 225, 255)

# ---------- Pulo duplo (melhoria da loja) ----------
UPGRADE_DOUBLE_JUMP_COST = 40

# ---------- Cura (item consumível da loja) ----------
SHOP_HEAL_COST = 15
SHOP_HEAL_AMOUNT = 25       # cura 1/4 da vida base por compra

# ---------- Ímã de moedas (melhoria da loja) ----------
UPGRADE_MAGNET_COST = 35
COIN_MAGNET_RADIUS = 130
COIN_MAGNET_PULL_SPEED = 6.5


# ---------- Recompensas e respawn de inimigos ----------
ENEMY_COIN_DROP_BASIC = 10
ENEMY_COIN_DROP_RANGED = 15
ENEMY_COIN_DROP_BOSS = 100
ENEMY_RESPAWN_SECONDS = 60
ENEMY_RESPAWN_FRAMES = ENEMY_RESPAWN_SECONDS * FPS

# ---------- Checkpoint/loja ----------
CHECKPOINT_SHOP_RANGE_PADDING_X = 70
CHECKPOINT_SHOP_RANGE_PADDING_Y = 40

# ---------- Morcego Sombrio (novo mob voador) ----------
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
# Visual (spritesheet em assets/morcego/). A hitbox acima é independente do tamanho do sprite.
FLYING_ENEMY_SPRITE_SCALE = None  # None = automática (2 px de tela por pixel da arte, ~ a hitbox); use múltiplos de 0.25 p/ manter o pixel art nítido
FLYING_ENEMY_FLAP_TICKS = 8       # frames de jogo por quadro de asa (menor = bate mais rápido)

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
BASIC_ENEMY_SPRITE_HEIGHT = 62       # altura visual; hitbox continua 32x32
BASIC_ENEMY_WALK_FRAME_TICKS = 7     # frames de jogo por quadro da caminhada
BASIC_ENEMY_IDLE_FRAME_TICKS = 12    # frames de jogo por quadro parado
BASIC_ENEMY_DETECTION_RANGE = 155   # distância entre hitboxes para perceber Kael
BASIC_ENEMY_PURSUIT_RANGE = 220    # distância máxima entre hitboxes antes de desistir
BASIC_ENEMY_DETECTION_LEASH = 45   # mantido por compatibilidade com configurações antigas
BASIC_ENEMY_ATTACK_RANGE = 30      # alcance curto, medido à frente da hitbox física
BASIC_ENEMY_ATTACK_FRAME_TICKS = 6 # duração de cada quadro da animação de ataque
BASIC_ENEMY_ATTACK_IMPACT_FRAME = 3 # quadro em que a lâmina atinge a área de golpe
BASIC_ENEMY_ATTACK_COOLDOWN = 72   # recuperação após o golpe (frames a 60 FPS)
# Avanço durante o golpe: o inimigo dá um passo curto na direção de Kael enquanto
# prepara o ataque (quadros ADVANCE_START_FRAME até o quadro de impacto, exclusivo).
BASIC_ENEMY_ATTACK_ADVANCE_SPEED = 3.0         # px/frame (patrulha/perseguição: 1.6)
BASIC_ENEMY_ATTACK_ADVANCE_MAX_DISTANCE = 36   # avanço total máximo por golpe (px, ~1 largura do corpo)
BASIC_ENEMY_ATTACK_ADVANCE_START_FRAME = 1     # quadro da animação em que o passo começa (0 = só antecipação)
BASIC_ENEMY_ATTACK_ADVANCE_STOP_GAP = 10       # para de avançar a esta distância entre hitboxes (nunca encosta/ultrapassa Kael)

RANGED_ENEMY_WIDTH = 30
RANGED_ENEMY_HEIGHT = 34
RANGED_ENEMY_HEALTH = 2
RANGED_ENEMY_DAMAGE = 10
RANGED_ENEMY_RANGE = 320
RANGED_ENEMY_COOLDOWN = 90
RANGED_ENEMY_SPRITE_HEIGHT = 54       # altura visual; hitbox física permanece 30x34
RANGED_ENEMY_IDLE_FRAME_TICKS = 12
RANGED_ENEMY_CAST_FRAME_TICKS = 6
RANGED_ENEMY_RELEASE_FRAME = 4        # solta a magia no quadro de lançamento
RANGED_ENEMY_PROJECTILE_VISUAL_SIZE = 22  # visual maior; hitbox continua 8x8
RANGED_ENEMY_AIM_MIN_DISTANCE = 4     # se Kael estiver quase no ponto de origem, atira na horizontal em vez de normalizar um vetor ~zero
PROJECTILE_SPEED = 6          # velocidade total (px/frame), igual em qualquer ângulo de disparo
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

# Investida ofensiva (dash em direção a Kael). Tempos em frames (60 FPS).
BOSS_CHARGE_CHANCE = 0.35             # chance de escolher a investida a cada ataque, quando fora do intervalo mínimo
BOSS_CHARGE_COOLDOWN = 360            # intervalo MÍNIMO entre investidas (6 s), contado a partir do fim da anterior
BOSS_CHARGE_FIRST_DELAY = 180         # espera inicial antes da 1a investida possível (3 s)
BOSS_CHARGE_MIN_DISTANCE = 240        # só investe se Kael estiver pelo menos tão longe (px, horizontal entre centros); mais perto o slam já cobre
BOSS_CHARGE_TELEGRAPH = 32            # preparação (aviso visual; hiper-armadura como nos outros telegraphs)
BOSS_CHARGE_SPEED = 8.0               # px/frame (caminhada: 2.2, ou 3.08 na Fase 2)
BOSS_CHARGE_MAX_FRAMES = 48           # duração máxima do avanço
BOSS_CHARGE_MAX_DISTANCE = 360        # distância máxima percorrida (px); o que vier primeiro encerra
BOSS_CHARGE_RECOVER = 55              # recuperação após a investida (frames; Vharok fica exposto)
BOSS_CHARGE_PHASE2_SPEED_MULT = 1.15  # ajuste moderado na Fase 2
BOSS_CHARGE_PHASE2_COOLDOWN_MULT = 0.85
BOSS_CHARGE_FRAME_TICKS = 3           # frames de jogo por quadro da animação durante a investida (só visual)

# Golpe de curta distância (reação de Vharok a Kael "encostado"). Tempos em frames (60 FPS).
# Vharok para de perseguir a BOSS_CHASE_STOP_DISTANCE (70); o golpe cobre essa faixa e pouco além.
BOSS_MELEE_TRIGGER_DISTANCE = 90      # distância HORIZONTAL entre centros para ativar o golpe (px)
BOSS_MELEE_REACH = 30                 # alcance da hitbox À FRENTE da borda do corpo (px); bem menor que o slam (130 a partir do centro)
BOSS_MELEE_TOP_MARGIN = 12            # px do topo do corpo (coroa) ignorados na checagem de altura e na hitbox
BOSS_MELEE_WINDUP_FRAMES = 16         # aviso (braços erguidos + zona de perigo); Kael ainda se afasta/usa dash a tempo
BOSS_MELEE_ACTIVE_FRAMES = 8          # janela em que a hitbox existe (dano no máximo UMA vez por golpe)
BOSS_MELEE_RECOVER_FRAMES = 24        # recuperação após o golpe, antes de voltar à perseguição
BOSS_MELEE_COOLDOWN = 100             # intervalo MÍNIMO entre golpes (~1,7 s), contado a partir do fim do anterior
BOSS_MELEE_PHASE2_COOLDOWN_MULT = 0.85

# Visual do Boss (enemies/boss_sprites.py). Puramente cosmético: não altera
# BOSS_WIDTH/BOSS_HEIGHT nem nenhuma colisão.
BOSS_SPRITE_SCALE = 1.5               # escala do corpo e das ondas de choque (a onda larga fica ~ do tamanho da área do slam)
BOSS_IMPACT_SCALE = 1.0               # escala das faíscas de impacto da rajada
BOSS_IDLE_FRAME_TICKS = 10            # frames de jogo por quadro do idle
BOSS_WALK_FRAME_TICKS = 6             # idem, caminhada (Fase 1)
BOSS_WALK_FRAME_TICKS_RAGE = 4        # idem, caminhada enfurecida (Fase 2 - ele anda 1.4x mais rápido)
BOSS_SLAM_STRIKE_FRAME_TICKS = 4      # 4 quadros x 4 = 16 = BOSS_SLAM_ACTIVE_FRAMES
BOSS_BARRAGE_RELEASE_FRAME_TICKS = 6
BOSS_PHASE2_FLASH_FRAMES = 48         # pisca vermelho ao entrar na Fase 2 (só visual; não pausa nada)

# ---------- Economia / Progressão ----------
COIN_VALUE = 1
UPGRADE_HEALTH_COST = 10
UPGRADE_HEALTH_AMOUNT = 20   # por nível (5 níveis = +100 de vida máxima)
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
