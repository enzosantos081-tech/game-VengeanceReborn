"""
systems/audio_events.py
"Diretor de áudio": observa o estado do jogo a cada frame e dispara os sons
certos nos momentos certos, SEM alterar nenhuma lógica de gameplay.

Em vez de espalhar chamadas de som pelos arquivos de inimigos, plataformas
e boss, o diretor compara o estado do frame atual com o do frame anterior
(ex.: "o inimigo passou de PATROL para ATTACK" -> toca o golpe dele).

Sons de inimigos, plataformas e estalactites são POSICIONAIS: ficam mais
baixos com a distância e saem mais pelo lado esquerdo/direito conforme a
posição relativa a Kael.
"""

import pygame


class AudioDirector:
    HEAR_RANGE = 720        # distância (px) além da qual um som de mundo some
    PAN_RANGE = 460         # distância lateral que leva o som a 100% de um lado

    def __init__(self, audio):
        self.audio = audio
        self.reset()

    # ------------------------------------------------------------------
    def reset(self):
        """Limpa a memória de estados (nova partida ou novo nível)."""
        self._level = None
        self._enemy = {}
        self._boss = None
        self._crumbling = []
        self._stalactites = []
        self._plat_state = {}
        self._stal_state = {}
        self._air_frames = 0
        self._fall_speed = 0.0
        self._prev_on_ground = False
        self._prev_air_jumps = 0
        self._prev_dash = 0
        self._heart_timer = 0
        self._void_played = False
        self._coin_step = 0
        self._coin_time = -10000
        self._boss_step_timer = 0
        self._windup_channel = None
        self._flap_cooldown = 0

    # ------------------------------------------------------------------
    # Som posicional
    # ------------------------------------------------------------------
    def at(self, name, x, player, volume=1.0, reach=None):
        """Toca `name` como se viesse da posição `x` do mundo."""
        reach = reach or self.HEAR_RANGE
        dx = x - player.rect.centerx
        dist = abs(dx)
        if dist >= reach:
            return None
        vol = volume * (1.0 - dist / reach) ** 1.3
        pan = max(-1.0, min(1.0, dx / self.PAN_RANGE)) * 0.85
        return self.audio.play(name, vol, pan)

    # ------------------------------------------------------------------
    # Chamadas feitas explicitamente pelo game.py
    # ------------------------------------------------------------------
    def coin(self):
        """Moedas seguidas sobem de tom (até 5 notas), como um pequeno combo."""
        now = pygame.time.get_ticks()
        if now - self._coin_time < 650:
            self._coin_step = min(4, self._coin_step + 1)
        else:
            self._coin_step = 0
        self._coin_time = now
        self.audio.play("coin_%d" % self._coin_step)

    @staticmethod
    def shop_snapshot(player):
        s = player.stats
        return (
            tuple(s.swords_owned), tuple(sorted(s.sword_levels.items())), s.equipped_sword_id,
            s.health_level, s.double_jump_level, s.magnet_level, player.health,
        )

    def shop_result(self, before, after, success=True):
        """Escolhe o som da compra comparando a loja antes/depois da ação."""
        if not success:
            return "denied"
        if after[1] != before[1]:
            return "sword_upgrade"
        if after[0] != before[0]:
            return "purchase_sword"
        if after[2] != before[2]:
            return "equip_sword"
        if after[3] != before[3]:
            return "purchase_health"
        if after[4] != before[4] or after[5] != before[5]:
            return "purchase_ability"
        if after[6] > before[6]:
            return "purchase_heal"
        return "purchase"

    def player_damaged(self, level, player):
        """Som extra conforme a causa do dano (espinho)."""
        for spike in level.obstacles.spikes:
            if spike.rect.colliderect(player.rect.inflate(6, 6)):
                self.audio.play("spike")
                return

    # ------------------------------------------------------------------
    # Ciclo por frame
    # ------------------------------------------------------------------
    def begin_frame(self, player):
        """Chamar ANTES de player.update(): guarda o que precisamos comparar."""
        self._fall_speed = player.vel_y
        self._prev_on_ground = player.on_ground
        self._prev_air_jumps = player.air_jumps_remaining
        self._prev_dash = player.dash_charges

    def update(self, level, player):
        """Chamar DEPOIS dos updates do frame (jogador, mundo, inimigos)."""
        if level is not self._level:
            self._level = level
            self._enemy = {}
            self._boss = None
            self._plat_state = {}
            self._stal_state = {}
            self._crumbling = [p for p in level.platforms.platforms
                               if type(p).__name__ == "CrumblingPlatform"]
            self._stalactites = list(level.obstacles.stalactites)
        self._player_events(level, player)
        self._enemy_events(level, player)
        self._boss_events(level, player)
        self._world_events(level, player)

    # ------------------------------------------------------------------
    # Kael
    # ------------------------------------------------------------------
    def _player_events(self, level, player):
        a = self.audio

        if player.just_jumped:
            double = player.air_jumps_remaining < self._prev_air_jumps
            a.play("double_jump" if double else "jump")
        if player.just_attacked:
            sword = player.stats.equipped_sword_id
            a.play("attack_%s" % sword if sword else "attack_base")
        if player.just_dashed:
            a.play("dash")

        # Pouso: leve em saltos comuns, pesado em quedas longas
        if player.on_ground:
            if not self._prev_on_ground and self._air_frames >= 6:
                if self._air_frames >= 55 or self._fall_speed >= 17.5:
                    a.play("land_hard")
                else:
                    a.play("land_soft", 0.55 + 0.45 * min(1.0, self._air_frames / 40.0))
            self._air_frames = 0
        else:
            self._air_frames += 1

        # Dash recarregado
        if (player.alive and not player.dashing and player.dash_charges > self._prev_dash):
            a.play("dash_ready")

        # Coração batendo quando a vida está crítica
        max_hp = max(1, player.stats.max_health)
        ratio = player.health / max_hp
        if player.alive and 0 < player.health and ratio <= 0.25:
            self._heart_timer -= 1
            if self._heart_timer <= 0:
                a.play("heartbeat")
                self._heart_timer = 42 if ratio <= 0.15 else 58
        else:
            self._heart_timer = 0

        # Queda no abismo
        if player.alive and player.rect.top > level.height - 60:
            if not self._void_played:
                a.play("fall_void")
                self._void_played = True
        elif player.rect.top < level.height - 200:
            self._void_played = False

    # ------------------------------------------------------------------
    # Inimigos comuns
    # ------------------------------------------------------------------
    def _enemy_events(self, level, player):
        if self._flap_cooldown > 0:
            self._flap_cooldown -= 1
        flap_budget = 1
        for e in level.enemies:
            kind = type(e).__name__
            st = self._enemy.get(e.id)
            if st is None:
                st = self._enemy[e.id] = {
                    "alive": e.alive,
                    "alerted": getattr(e, "alerted", False),
                    "combat": getattr(e, "combat_state", None),
                    "casting": getattr(e, "casting", False),
                    "released": getattr(e, "shot_released", False),
                    "proj": {},
                    "flap": 0,
                }
            x = e.rect.centerx

            # Morte
            if st["alive"] and not e.alive:
                if kind == "FlyingEnemy":
                    self.at("enemy_death_bat", x, player, 0.95)
                elif kind == "RangedEnemy":
                    self.at("enemy_death_ranged", x, player, 1.0)
                else:
                    self.at("enemy_death", x, player, 1.0)
            st["alive"] = e.alive
            if not e.alive:
                st["proj"] = {}
                continue

            if kind == "BasicEnemy":
                if e.alerted and not st["alerted"]:
                    self.at("enemy_alert", x, player, 0.9, reach=600)
                if e.combat_state == "ATTACK" and st["combat"] != "ATTACK":
                    self.at("enemy_swing", x, player, 1.0, reach=650)
                st["alerted"] = e.alerted
                st["combat"] = e.combat_state

            elif kind == "RangedEnemy":
                if e.casting and not st["casting"]:
                    self.at("cast_charge", x, player, 0.9, reach=760)
                if e.shot_released and not st["released"]:
                    self.at("fireball_shot", x, player, 1.0, reach=760)
                st["casting"] = e.casting
                st["released"] = e.shot_released
                self._projectile_impacts(e.projectiles, st, player, 0.9)

            elif kind == "FlyingEnemy":
                ticks = max(1, getattr(e, "_flap_ticks", 8))
                phase = (getattr(e, "_flap_tick", 0) // ticks) % 2
                if phase != st["flap"]:
                    st["flap"] = phase
                    if phase == 1 and flap_budget > 0 and self._flap_cooldown <= 0:
                        if self.at("bat_flap", x, player, 0.9, reach=380):
                            flap_budget -= 1
                            self._flap_cooldown = 4

    def _projectile_impacts(self, projectiles, st, player, volume):
        """Projétil que sumiu desde o frame anterior = bateu em algo."""
        current = {id(p): p["rect"].center for p in projectiles}
        for pid, pos in st["proj"].items():
            if pid not in current:
                self.at("magic_impact", pos[0], player, volume, reach=640)
        st["proj"] = current

    # ------------------------------------------------------------------
    # Boss (Vharok)
    # ------------------------------------------------------------------
    def _boss_events(self, level, player):
        b = level.boss
        if b is None:
            self._boss = None
            return
        st = self._boss
        if st is None:
            st = self._boss = {"state": b.state, "phase2": b.phase2, "x": b.rect.x, "proj": {}}
        if not b.alive:
            st["state"] = b.state
            return

        if b.state != st["state"]:
            if b.state == b.STATE_TELEGRAPH:
                if b.attack_type == b.ATTACK_SLAM:
                    name = "boss_windup_slam"
                elif b.attack_type == b.ATTACK_BARRAGE:
                    name = "boss_windup_barrage"
                else:
                    name = "boss_windup_charge"
                self._windup_channel = self.audio.play(name)
            elif b.state == b.STATE_DASH:
                self.audio.play("boss_charge")
            elif b.state == b.STATE_MELEE:
                # O golpe curto pode interromper o aviso do slam: corta o som do aviso.
                if st["state"] == b.STATE_TELEGRAPH and self._windup_channel is not None:
                    try:
                        self._windup_channel.fadeout(120)
                    except pygame.error:
                        pass
                    self._windup_channel = None
                self.audio.play("boss_windup_melee")
            st["state"] = b.state

        if b.phase2 and not st["phase2"]:
            self.audio.play("boss_phase2")
        st["phase2"] = b.phase2

        # Passos pesados enquanto persegue
        moved = abs(b.rect.x - st["x"]) > 0
        st["x"] = b.rect.x
        if b.state == b.STATE_CHASE and moved:
            self._boss_step_timer += 1
            if self._boss_step_timer >= (19 if b.phase2 else 30):
                self._boss_step_timer = 0
                self.at("boss_step", b.rect.centerx, player, 1.0, reach=1000)
        else:
            self._boss_step_timer = 0

        self._projectile_impacts(b.projectiles, st, player, 0.8)

    # ------------------------------------------------------------------
    # Mundo: plataformas quebradiças e estalactites
    # ------------------------------------------------------------------
    def _world_events(self, level, player):
        for p in self._crumbling:
            prev = self._plat_state.get(id(p), p.state)
            if p.state != prev:
                if p.state == "shaking":
                    self.at("crumble_warn", p.rect.centerx, player, 1.0)
                elif p.state == "gone":
                    self.at("crumble_fall", p.rect.centerx, player, 1.0)
            self._plat_state[id(p)] = p.state

        for s in self._stalactites:
            prev = self._stal_state.get(id(s), s.state)
            if s.state != prev:
                if s.state == "shake":
                    self.at("stalactite_warn", s.rect.centerx, player, 1.0, reach=620)
                elif s.state == "falling":
                    self.at("stalactite_fall", s.rect.centerx, player, 0.9, reach=620)
                elif s.state == "gone":
                    self.at("stalactite_crash", s.rect.centerx, player, 1.0, reach=620)
            self._stal_state[id(s)] = s.state
