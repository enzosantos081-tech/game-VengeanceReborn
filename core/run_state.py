"""
core/run_state.py
Captura e restauração do estado de uma PARTIDA em andamento (a parte "run"
do arquivo de save; o I/O fica em core/save.py).

Como funciona: as fases do jogo são montadas por código e são
determinísticas (build_main_level / build_boss_level geram sempre os mesmos
inimigos, moedas, plataformas e checkpoints, na mesma ordem). Por isso o
save NÃO guarda o mapa: guarda só o que muda durante o jogo, identificado
pelo índice do objeto na lista da fase:

  * jogador: posição, vida, direção; progressão (stats) vai à parte;
  * Núcleo do Retorno / checkpoint atual e quais checkpoints estão ativos;
  * moedas já coletadas e gatilhos de história já disparados;
  * inimigos: posição, vida, vivo/morto e tempo para reaparecer;
  * plataformas móveis e quebradiças, estalactites (inclui a ponte do
    puzzle da fenda) e o Boss (vida, fase).

Na restauração a fase é reconstruída do zero e o estado salvo é aplicado
por cima. Se a fase mudou de estrutura desde o save (assinatura diferente)
ou o estado salvo estiver inconsistente, o estado do mundo é descartado e
Kael volta ao último Núcleo/checkpoint salvo - recuperação segura que
mantém a progressão.
"""

import math
import time

import pygame
from config import settings
from player.player import Player
from world.level import build_main_level, build_boss_level, FOREST_END
from world.platforms import MovingPlatform, CrumblingPlatform
from world.obstacles import Stalactite
from systems import collision

RUN_VERSION = 1
LEVEL_MAIN = "main"
LEVEL_BOSS = "boss"
_BUILDERS = {LEVEL_MAIN: build_main_level, LEVEL_BOSS: build_boss_level}
_BIOME_NAMES = {"forest": "Floresta", "cave": "Caverna", "castle": "Castelo de Vharok"}


# ------------------------------------------------------------ utilitários
def _level_id(level):
    return LEVEL_BOSS if level.is_boss_level else LEVEL_MAIN


def biome_of(level, x):
    """Bioma em que a coordenada x está (informativo, para o menu)."""
    if level.is_boss_level:
        return "castle"
    return "forest" if x < FOREST_END else "cave"


def _signature(level):
    return {
        "enemies": len(level.enemies),
        "coins": len(level.coins.coins),
        "checkpoints": len(level.checkpoints),
        "stories": len(level.story_triggers),
        "platforms": len(level.platforms.platforms),
        "stalactites": len(level.obstacles.stalactites),
        "boss": level.boss is not None,
    }


def _num(value, lo=None, hi=None):
    """Número finito (int/float, nunca bool) dentro de [lo, hi]."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("número esperado")
    if not math.isfinite(value):
        raise ValueError("número não finito")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        raise ValueError("número fora do intervalo")
    return value


def _indices(value, count):
    """Lista de índices únicos válidos para uma lista de tamanho count."""
    if not isinstance(value, list):
        raise ValueError("lista esperada")
    out = set()
    for v in value:
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < count:
            raise ValueError("índice inválido")
        out.add(v)
    return out


def _list_of_dicts(value):
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        raise ValueError("lista de objetos esperada")
    return value


# ----------------------------------------------------------------- captura
def capture_run(game):
    """Monta o dict "run" a partir do estado atual de um Game em jogo."""
    level, player = game.level, game.player
    core = (game.respawn_system.core_x, game.respawn_system.core_y)
    max_hp = player.stats.max_health

    dead = not player.alive or player.health <= 0
    if dead:
        # Morreu: o save de continuidade nunca guarda o ponto exato da
        # morte. Kael é salvo já no Núcleo/checkpoint, como o respawn faria.
        px, py, hp = core[0], core[1], max_hp
    else:
        px, py, hp = player.rect.x, player.rect.y, player.health

    run = {
        "version": RUN_VERSION,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "play_seconds": int(game.play_frames // settings.FPS),
        "level": {
            "id": _level_id(level),
            "biome": biome_of(level, px),
            "signature": _signature(level),
        },
        "player": {"x": px, "y": py, "health": hp,
                   "facing_right": bool(player.facing_right), "dead": dead},
        "respawn": {"x": core[0], "y": core[1]},
        "checkpoints": [i for i, cp in enumerate(level.checkpoints) if cp.active],
        "coins": [i for i, c in enumerate(level.coins.coins) if c.collected],
        "stories": [i for i, t in enumerate(level.story_triggers) if t["triggered"]],
        "enemies": [_capture_enemy(e) for e in level.enemies],
        "platforms": _capture_platforms(level),
        "stalactites": _capture_stalactites(level, player, dead),
        "boss": _capture_boss(level.boss),
    }
    return run


def _capture_enemy(e):
    rec = {"t": type(e).__name__, "x": e.rect.x, "y": e.rect.y, "hp": e.health,
           "a": 1 if e.alive else 0, "rt": int(e.respawn_timer),
           "f": 1 if e.facing_right else 0}
    if hasattr(e, "direction"):
        rec["d"] = e.direction
    return rec


def _capture_platforms(level):
    out = []
    for i, p in enumerate(level.platforms.platforms):
        if isinstance(p, MovingPlatform):
            out.append({"i": i, "k": "m", "p": p.progress, "d": p.direction})
        elif isinstance(p, CrumblingPlatform):
            if p.state != CrumblingPlatform.STATE_IDLE:
                out.append({"i": i, "k": "c", "s": p.state, "t": int(p.timer)})
    return out


def _capture_stalactites(level, player, dead):
    out = []
    for i, st in enumerate(level.obstacles.stalactites):
        state, shake = st.state, st.shake_timer
        triggered = st.triggered_by_death
        if (dead and st.trigger_on_death_zone and not triggered
                and state == Stalactite.STATE_IDLE):
            # Kael acabou de morrer dentro da fenda: a pedra do puzzle ainda
            # não teve um frame para reagir. Registra o gatilho agora, senão
            # o puzzle se perderia se o jogo fechasse nessa janela.
            left, right = st.trigger_on_death_zone
            if left <= player.rect.centerx <= right:
                state, shake, triggered = (Stalactite.STATE_SHAKE,
                                           Stalactite.SHAKE_FRAMES, True)
        if state == Stalactite.STATE_IDLE and not triggered:
            continue   # intacta: é o estado padrão da fase
        out.append({"i": i, "s": state, "y": st.y, "vy": st.vel_y, "sh": int(shake),
                    "lt": int(st.landed_timer), "ft": int(st.fade_timer),
                    "tr": bool(triggered), "ah": bool(st.already_hit)})
    return out


def _capture_boss(boss):
    if boss is None:
        return None
    return {"x": boss.rect.x, "hp": boss.health, "a": 1 if boss.alive else 0,
            "phase2": bool(boss.phase2), "f": 1 if boss.facing_right else 0}


# ------------------------------------------------------------ restauração
def restore_run(run, stats):
    """Reconstrói a partida a partir de (run, stats).

    Devolve (level, player, core_pos, play_frames). Levanta ValueError se o
    save for inutilizável; nesse caso nada do jogo em andamento foi
    alterado (o chamador só instala o resultado em caso de sucesso)."""
    try:
        return _restore(run, stats)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        raise ValueError(f"salvamento inválido: {exc}") from exc


def _restore(run, stats):
    if not isinstance(run, dict) or run.get("version") != RUN_VERSION:
        raise ValueError("versão de partida desconhecida")
    info = run["level"]
    level_id = info["id"]
    if level_id not in _BUILDERS:
        raise ValueError("fase desconhecida")

    level = _BUILDERS[level_id]()
    world_ok = info.get("signature") == _signature(level)
    if world_ok:
        try:
            _apply_world(level, run)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            level = _BUILDERS[level_id]()   # descarta qualquer aplicação parcial
            world_ok = False

    player = Player(*level.player_start)
    player.stats.from_dict(stats)
    max_hp = player.stats.max_health
    player.health = max_hp
    # O pulo duplo recarrega ao tocar o chão (player.update); começa carregado.
    player.air_jumps_remaining = player.stats.extra_jumps

    core = _valid_core(level, run.get("respawn")) or tuple(level.core_pos)

    pdata = run.get("player")
    placed = False
    if world_ok and isinstance(pdata, dict) and not pdata.get("dead"):
        try:
            x = int(_num(pdata["x"], 0, level.width))
            y = int(_num(pdata["y"], -200, level.height + 100))
            hp = int(_num(pdata["health"], 1, max_hp))
        except (ValueError, TypeError, KeyError):
            x = None                       # dados do jogador inválidos: recuperação segura
        if x is not None:
            player.rect.topleft = (x, y)
            spot = _safe_spot(level, player.rect)
            if spot is not None:
                player.rect.topleft = spot
                player.health = hp
                player.facing_right = bool(pdata.get("facing_right", True))
                placed = True
    if not placed:
        # Morto, mundo descartado ou posição inválida: recuperação segura
        # exatamente como a morte faz (Núcleo/checkpoint, vida cheia).
        player.respawn_at_core(*core)

    play_frames = int(_num(run.get("play_seconds", 0), 0, 10 ** 9)) * settings.FPS
    return level, player, core, play_frames


def _valid_core(level, data):
    try:
        x = _num(data["x"], 0, level.width)
        y = _num(data["y"], -200, level.height)
    except (ValueError, TypeError, KeyError):
        return None
    return (int(x), int(y))


def _safe_spot(level, rect):
    """Posição válida mais próxima de rect (dentro da fase e fora de sólidos)
    ou None. Tolera sobreposições de poucos pixels (arredondamento de
    plataformas móveis) subindo o jogador até 16 px."""
    solids = level.platforms.rects() + level.obstacles.landed_platform_rects()
    for lift in range(0, 17):
        test = rect.move(0, -lift)
        if not (0 <= test.left and test.right <= level.width):
            return None
        if not collision.rect_collides_any(test, solids):
            return (test.x, test.y)
    return None


def _apply_world(level, run):
    """Aplica o estado salvo à fase recém-construída. Valida tudo ANTES de
    mexer; qualquer erro levanta e o chamador reconstrói a fase."""
    cps = _indices(run["checkpoints"], len(level.checkpoints))
    coins = _indices(run["coins"], len(level.coins.coins))
    stories = _indices(run["stories"], len(level.story_triggers))

    enemy_recs = _list_of_dicts(run["enemies"])
    if len(enemy_recs) != len(level.enemies):
        raise ValueError("número de inimigos")
    for e, rec in zip(level.enemies, enemy_recs):
        if rec["t"] != type(e).__name__:
            raise ValueError("tipo de inimigo")
        _num(rec["x"]); _num(rec["y"]); _num(rec["hp"], 0, e.max_health)
        _num(rec["rt"], 0, 10 ** 7)
        if "d" in rec:
            _num(rec["d"], -1, 1)

    plat_recs = _list_of_dicts(run["platforms"])
    plats = level.platforms.platforms
    for rec in plat_recs:
        i = rec["i"]
        if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(plats):
            raise ValueError("índice de plataforma")
        if rec["k"] == "m":
            if not isinstance(plats[i], MovingPlatform):
                raise ValueError("plataforma móvel")
            _num(rec["p"], 0.0, 1.0); _num(rec["d"], -1, 1)
        elif rec["k"] == "c":
            if not isinstance(plats[i], CrumblingPlatform):
                raise ValueError("plataforma quebradiça")
            if rec["s"] not in (CrumblingPlatform.STATE_IDLE, CrumblingPlatform.STATE_SHAKING,
                                CrumblingPlatform.STATE_GONE):
                raise ValueError("estado de plataforma")
            _num(rec["t"], 0, 10 ** 7)
        else:
            raise ValueError("tipo de plataforma")

    stal = level.obstacles.stalactites
    states = (Stalactite.STATE_IDLE, Stalactite.STATE_SHAKE, Stalactite.STATE_FALLING,
              Stalactite.STATE_LANDED, Stalactite.STATE_FADING, Stalactite.STATE_GONE)
    stal_recs = _list_of_dicts(run["stalactites"])
    for rec in stal_recs:
        i = rec["i"]
        if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(stal):
            raise ValueError("índice de estalactite")
        if rec["s"] not in states:
            raise ValueError("estado de estalactite")
        _num(rec["y"], -5000, 5000); _num(rec["vy"], -100, 100)
        for key in ("sh", "lt", "ft"):
            _num(rec[key], 0, 10 ** 5)

    boss_rec = run.get("boss")
    if (boss_rec is None) != (level.boss is None):
        raise ValueError("boss")
    if boss_rec is not None:
        _num(boss_rec["x"], 0, level.width)
        _num(boss_rec["hp"], 1, level.boss.max_health)
        if not boss_rec["a"]:
            raise ValueError("boss já derrotado")

    # ---- tudo válido: aplica ----
    for i in cps:
        level.checkpoints[i].active = True
    for i in coins:
        level.coins.coins[i].collected = True
    for i in stories:
        level.story_triggers[i]["triggered"] = True

    for e, rec in zip(level.enemies, enemy_recs):
        e.rect.x, e.rect.y = int(rec["x"]), int(rec["y"])
        e.health = int(rec["hp"])
        e.alive = bool(rec["a"]) and e.health > 0
        e.respawn_timer = int(rec["rt"])
        e.facing_right = bool(rec.get("f", 0))
        if "d" in rec and rec["d"] in (-1, 1):
            e.direction = int(rec["d"])
        if not e.alive and e.can_respawn and e.respawn_timer <= 0:
            e.respawn_timer = 1   # morto sem contagem: reaparece logo, nunca fica preso

    for rec in plat_recs:
        p = plats[rec["i"]]
        if rec["k"] == "m":
            p.progress, p.direction = float(rec["p"]), int(rec["d"]) or 1
            p.rect.x = round(p.start_x + (p.end_x - p.start_x) * p.progress)
            p.rect.y = round(p.start_y + (p.end_y - p.start_y) * p.progress)
            p.delta_x = p.delta_y = 0
        else:
            p.state, p.timer = rec["s"], int(rec["t"])
    level.platforms.refresh()

    for rec in stal_recs:
        st = stal[rec["i"]]
        st.state, st.y, st.vel_y = rec["s"], float(rec["y"]), float(rec["vy"])
        st.shake_timer, st.landed_timer, st.fade_timer = int(rec["sh"]), int(rec["lt"]), int(rec["ft"])
        st.triggered_by_death, st.already_hit = bool(rec["tr"]), bool(rec["ah"])
        st._update_rect()

    if boss_rec is not None:
        boss = level.boss
        boss.rect.x = int(boss_rec["x"])
        boss.health = int(boss_rec["hp"])
        boss.phase2 = (bool(boss_rec.get("phase2"))
                       or boss.health <= boss.max_health * settings.BOSS_PHASE2_HEALTH_RATIO)
        boss.facing_right = bool(boss_rec.get("f", 0))
        boss._hud_trail_health = float(boss.health)   # barra de vida do HUD sem "rastro"
        boss.reset_combat_state()


# ----------------------------------------------------------------- resumo
def summarize(run, stats):
    """Resumo curto para o menu ("Caverna · 120 moedas · 20 min") ou None se
    a partida salva não for utilizável. Validação leve: o carregamento real
    (restore_run) ainda confere tudo e pode recusar."""
    try:
        if not isinstance(run, dict) or run.get("version") != RUN_VERSION:
            return None
        info = run["level"]
        if info["id"] not in _BUILDERS or info["biome"] not in _BIOME_NAMES:
            return None
        for key in ("player", "respawn", "enemies", "coins", "checkpoints"):
            if key not in run:
                return None
        coins = stats.get("coins", 0)
        coins = int(coins) if isinstance(coins, (int, float)) and not isinstance(coins, bool) else 0
        seconds = int(_num(run.get("play_seconds", 0), 0, 10 ** 9))
        return {"region": _BIOME_NAMES[info["biome"]], "coins": max(0, coins),
                "minutes": seconds // 60}
    except (ValueError, TypeError, KeyError, AttributeError):
        return None
