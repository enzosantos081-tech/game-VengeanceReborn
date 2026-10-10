"""
enemies/boss.py
Implementação de Vharok, o Rei do Abismo (Boss final).
Comportamento conforme a seção 17 do documento de escopo, com um
extra de Prioridade 3 (seção 21 - "Boss com mais de um padrão de
ataque"):
1. permanece na arena e se move em direção ao jogador;
2. na Fase 1 (vida > 50%), realiza apenas o ataque "slam" (investida +
   golpe corpo a corpo telegrafado);
3. ao cair para 50% de vida ou menos, entra na Fase 2: fica mais rápido
   e passa a alternar aleatoriamente entre "slam" e uma nova "rajada"
   de projéteis à distância;
3b. (extra) ocasionalmente faz uma INVESTIDA horizontal rápida em direção a
   Kael (telegraph -> dash -> recuperação), com intervalo mínimo entre
   investidas; cada investida causa no máximo um evento de dano;
3c. (extra) GOLPE CURTO: se Kael ficar muito perto, Vharok reage com um golpe
   de curta distância (aviso -> golpe -> recuperação), orientado para o lado
   de Kael e com intervalo mínimo entre golpes. Pode cancelar o aviso do slam
   (nada foi executado ainda) ou, se o slam já disparou, entra assim que o
   golpe do slam e sua animação terminam; veja _melee_allowed_now();
4. possui janelas em que pode receber dano (sempre que não está com
   nenhum ataque telegrafado / hiper-armadura);
5. barra de vida grande e visível, fixa na tela.

Visual: o corpo e os efeitos vêm da spritesheet (enemies/boss_sprites.py).
As animações apenas ACOMPANHAM a máquina de estados abaixo (estado, timers
e attack_triggered_this_frame); nenhuma lógica de dano, vida, fase ou
movimento depende de qual quadro está na tela.
"""

import math
import random
import pygame
from config import settings
from enemies.enemy import Enemy
from enemies import boss_sprites


class Boss(Enemy):
    STATE_CHASE = "chase"
    STATE_TELEGRAPH = "telegraph"
    STATE_ATTACK = "attack"
    STATE_RECOVER = "recover"
    STATE_DASH = "dash"   # avanço rápido da investida (o aviso usa STATE_TELEGRAPH)
    STATE_MELEE = "melee"  # golpe curto: aviso -> golpe -> recuperação (sub-etapas em melee_stage)

    ATTACK_SLAM = "slam"
    ATTACK_BARRAGE = "barrage"
    ATTACK_CHARGE = "charge"
    ATTACK_MELEE = "melee"   # só aparece em attack_triggered_this_frame (som/tremor); não entra em _choose_attack

    MELEE_WINDUP = "windup"
    MELEE_STRIKE = "strike"
    MELEE_RECOVER = "recover"

    def __init__(self, x, y, arena_left, arena_right):
        super().__init__(
            x, y,
            settings.BOSS_WIDTH, settings.BOSS_HEIGHT,
            settings.BOSS_MAX_HEALTH, settings.BOSS_DAMAGE,
            settings.COLOR_BOSS,
            coin_value=settings.ENEMY_COIN_DROP_BOSS,
        )
        # O Boss é único e derrotá-lo é a condição de vitória - ele nunca
        # deve reaparecer sozinho como os inimigos comuns.
        self.can_respawn = False
        self.arena_left = arena_left
        self.arena_right = arena_right
        self.state = Boss.STATE_CHASE
        self.attack_timer = settings.BOSS_ATTACK_COOLDOWN
        self.telegraph_timer = 0
        self.recover_timer = 0
        self.attack_rect = None
        self.attack_active_timer = 0
        self.attack_type = Boss.ATTACK_SLAM
        self.phase2 = False
        self.projectiles = []
        # ---- Investida (dash ofensivo) ----
        self.charge_cooldown = settings.BOSS_CHARGE_FIRST_DELAY
        self.charge_dir = 1
        self.charge_speed = 0.0
        self.charge_timer = 0
        self.charge_travelled = 0
        self.attack_triggered_this_frame = None  # "slam"/"barrage"/"melee" no frame em que o golpe é executado (p/ som)

        # ---- Golpe curto (Kael encostado) ----
        self.melee_cooldown = 0          # frames até poder golpear de novo
        self.melee_stage = None          # MELEE_WINDUP / MELEE_STRIKE / MELEE_RECOVER (só dentro de STATE_MELEE)
        self.melee_timer = 0             # frames restantes da etapa atual
        self.melee_dir = 1               # lado do golpe (1 direita, -1 esquerda); trava quando o golpe sai
        self.melee_rect = None           # hitbox ativa (só existe na etapa MELEE_STRIKE; recalculada a cada frame)
        self.melee_hit_done = False      # dano já aplicado nesta execução?
        self.melee_windup_start = 0      # quadro inicial do aviso (continua a pose se veio do aviso do slam)
        self.slam_interrupt_used = False  # um slam já foi cancelado pelo golpe curto: o próximo vai até o fim

        # ---- Estado puramente visual (não afeta a lógica de combate) ----
        self.sprites = boss_sprites.get_boss_sprites()   # None -> desenho retangular antigo
        self.anim_tick = 0            # contador de frames de jogo, p/ idle/caminhada
        self.strike_kind = None       # "slam"/"barrage": animação de execução em andamento
        self.strike_tick = 0          # frames desde a execução do golpe
        self.phase_flash_timer = 0    # pisca ao entrar na Fase 2
        self.impacts = []             # faíscas onde a rajada bateu: {"x", "y", "t"}

        # ---- HUD do chefe (somente visual; não participa do combate) ----
        self._hud_trail_health = float(self.max_health)
        self._hud_hit_flash_timer = 0
        self._hud_phase_transition_timer = 0
        self._hud_phase_transition_duration = 180  # 3 s a 60 FPS
        self._hud_anim_tick = 0
        self._hud_name_font = pygame.font.SysFont("georgia", 27, bold=True)
        self._hud_phase_font = pygame.font.SysFont("arial", 15, bold=True)
        self._hud_transition_font = pygame.font.SysFont("georgia", 34, bold=True)
        self._hud_transition_sub_font = pygame.font.SysFont("arial", 17, bold=True)

    def update(self, level, player):
        super().update(level, player)
        if not self.alive:
            return

        self.attack_triggered_this_frame = None
        if self.charge_cooldown > 0:
            self.charge_cooldown -= 1
        if self.melee_cooldown > 0:
            self.melee_cooldown -= 1
        if not self.phase2 and self.health <= self.max_health * settings.BOSS_PHASE2_HEALTH_RATIO:
            self.phase2 = True
            self.phase_flash_timer = settings.BOSS_PHASE2_FLASH_FRAMES
            # O HUD acompanha a mesma transição real usada pelo combate.
            self._hud_phase_transition_timer = self._hud_phase_transition_duration

        # Animações do HUD são atualizadas em frames, sem bloquear o loop.
        self._hud_anim_tick += 1
        if self._hud_hit_flash_timer > 0:
            self._hud_hit_flash_timer -= 1
        if self._hud_phase_transition_timer > 0:
            self._hud_phase_transition_timer -= 1
        current_health = max(0.0, float(self.health))
        if current_health >= self._hud_trail_health:
            self._hud_trail_health = current_health
        else:
            # Camada de dano atrasada, independente da vida real.
            self._hud_trail_health = max(current_health, self._hud_trail_health - max(0.12, self.max_health / 72.0))

        speed = settings.BOSS_SPEED * (1.4 if self.phase2 else 1.0)

        self.vel_y += settings.GRAVITY
        if self.vel_y > settings.MAX_FALL_SPEED:
            self.vel_y = settings.MAX_FALL_SPEED

        # Kael encostado? (só decide a TRANSIÇÃO; as regras de quando é seguro
        # interromper/esperar ficam em _melee_allowed_now)
        if self._melee_allowed_now(player):
            self._start_melee(player)

        if self.state == Boss.STATE_CHASE:
            self.vel_x = 0
            direction = 1 if player.rect.centerx > self.rect.centerx else -1
            self.facing_right = direction > 0
            distance = abs(player.rect.centerx - self.rect.centerx)
            if distance > settings.BOSS_CHASE_STOP_DISTANCE:
                self.vel_x = speed * direction

            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self._choose_attack(player)

        elif self.state == Boss.STATE_TELEGRAPH:
            self.vel_x = 0
            if self.attack_type == Boss.ATTACK_CHARGE:
                # Vira para o lado em que Kael está durante o aviso.
                self.facing_right = player.rect.centerx > self.rect.centerx
            self.telegraph_timer -= 1
            if self.telegraph_timer <= 0:
                if self.attack_type == Boss.ATTACK_CHARGE:
                    self._start_charge(player)
                else:
                    self.state = Boss.STATE_ATTACK
                    if self.attack_type == Boss.ATTACK_SLAM:
                        self._perform_slam(player)
                    else:
                        self._perform_barrage(player)

        elif self.state == Boss.STATE_DASH:
            # Avanço em linha reta; a direção foi travada em _start_charge.
            self.vel_x = self.charge_speed * self.charge_dir
            self.facing_right = self.charge_dir > 0
            self.charge_timer -= 1

        elif self.state == Boss.STATE_MELEE:
            self._update_melee(player)

        elif self.state == Boss.STATE_ATTACK:
            self.state = Boss.STATE_RECOVER
            self.recover_timer = 20

        elif self.state == Boss.STATE_RECOVER:
            self.vel_x = 0
            self.recover_timer -= 1
            if self.recover_timer <= 0:
                self.state = Boss.STATE_CHASE
                self.attack_timer = settings.BOSS_ATTACK_COOLDOWN

        x_before = self.rect.x
        level.move_and_collide_enemy(self, self.vel_x, self.vel_y)
        self.rect.x = max(self.arena_left, min(self.rect.x, self.arena_right - self.rect.width))

        if self.state == Boss.STATE_DASH:
            # Durante a investida o dano é decidido por _update_charge (no
            # máximo um evento por execução), não pelo contato contínuo.
            self._update_charge(player, x_before)
        elif self.state == Boss.STATE_MELEE:
            # O dano do golpe curto é só o da hitbox do golpe (no máximo uma vez
            # por execução); o contato corporal fica desligado, como no
            # telegraph, para nunca somar dois danos no mesmo golpe.
            self._update_melee_hit(player)
        elif self.state != Boss.STATE_TELEGRAPH:
            # Dano por contato corporal (sempre ativo, exceto durante telegraph)
            self.check_contact_damage(player)

        # Dano da área de ataque especial (slam/terremoto): fica ativa por
        # settings.BOSS_SLAM_ACTIVE_FRAMES, não só 1-2 frames como antes -
        # esse era o motivo do golpe "não acertar" mesmo quando o jogador
        # estava parado embaixo dele.
        if self.attack_rect:
            if player.alive and self.attack_rect.colliderect(player.rect):
                direction = 1 if player.rect.centerx > self.rect.centerx else -1
                player.take_damage(self.damage, knockback_dir=direction)
                self.attack_rect = None
                self.attack_active_timer = 0
            else:
                self.attack_active_timer -= 1
                if self.attack_active_timer <= 0:
                    self.attack_rect = None

        self._update_projectiles(level, player)
        self._update_visual()

    def _can_charge(self, player):
        """A investida só é sorteada com Kael vivo e longe o bastante, fora do
        intervalo mínimo e fora da animação de entrada na Fase 2."""
        if player is None or not player.alive or not self.alive:
            return False
        if self.charge_cooldown > 0 or self.phase_flash_timer > 0:
            return False
        return abs(player.rect.centerx - self.rect.centerx) >= settings.BOSS_CHARGE_MIN_DISTANCE

    def _choose_attack(self, player=None):
        """Na Fase 1 existem o slam e (ocasionalmente) a investida. Na Fase 2,
        Vharok alterna aleatoriamente entre slam e rajada, e também pode
        investir."""
        if self._can_charge(player) and random.random() < settings.BOSS_CHARGE_CHANCE:
            self.attack_type = Boss.ATTACK_CHARGE
            self.telegraph_timer = settings.BOSS_CHARGE_TELEGRAPH
            self.state = Boss.STATE_TELEGRAPH
            return
        if self.phase2 and random.random() < 0.5:
            self.attack_type = Boss.ATTACK_BARRAGE
            self.telegraph_timer = settings.BOSS_BARRAGE_TELEGRAPH
        else:
            self.attack_type = Boss.ATTACK_SLAM
            self.telegraph_timer = settings.BOSS_SLAM_TELEGRAPH
        self.state = Boss.STATE_TELEGRAPH

    # ---------- Investida ----------
    def _start_charge(self, player):
        """Fim do aviso: trava a direção para o lado em que Kael está agora e
        começa o avanço."""
        self.charge_dir = 1 if player.rect.centerx > self.rect.centerx else -1
        self.facing_right = self.charge_dir > 0
        speed = settings.BOSS_CHARGE_SPEED * (settings.BOSS_CHARGE_PHASE2_SPEED_MULT if self.phase2 else 1.0)
        # Passo por frame nunca maior que metade do corpo: junto com o
        # move_and_collide_enemy (eixo separado) impede atravessar sólidos.
        self.charge_speed = min(speed, self.rect.width // 2)
        self.charge_timer = settings.BOSS_CHARGE_MAX_FRAMES
        self.charge_travelled = 0
        self.strike_kind = None   # não sobrepõe animação de golpe anterior
        self.state = Boss.STATE_DASH

    def _update_charge(self, player, x_before):
        """Roda depois do movimento do frame: aplica o dano (no máximo uma vez)
        e decide se a investida acabou."""
        moved = abs(self.rect.x - x_before)
        self.charge_travelled += moved

        hit = False
        if player.alive and self.rect.colliderect(player.rect):
            health_before = player.health
            player.take_damage(self.damage, knockback_dir=self.charge_dir)
            # Se Kael estava invulnerável (dash/i-frames) nada foi aplicado:
            # a investida continua e só conta como acerto se o dano entrar.
            hit = player.health < health_before

        # Parede/limite da arena: o deslocamento real ficou menor que o pedido.
        blocked = moved < abs(round(self.vel_x))
        if (hit or blocked or self.charge_travelled >= settings.BOSS_CHARGE_MAX_DISTANCE
                or self.charge_timer <= 0):
            self._end_charge()

    def _end_charge(self):
        self.vel_x = 0
        self.state = Boss.STATE_RECOVER
        self.recover_timer = settings.BOSS_CHARGE_RECOVER
        mult = settings.BOSS_CHARGE_PHASE2_COOLDOWN_MULT if self.phase2 else 1.0
        self.charge_cooldown = int(settings.BOSS_CHARGE_COOLDOWN * mult)

    def _charge_preview_rect(self):
        """Faixa do chão/corpo que a investida pode percorrer (aviso)."""
        dist = settings.BOSS_CHARGE_MAX_DISTANCE
        if self.facing_right:
            x0 = self.rect.right
            x1 = min(self.arena_right, x0 + dist)
        else:
            x1 = self.rect.left
            x0 = max(self.arena_left, x1 - dist)
        return pygame.Rect(x0, self.rect.top, max(0, x1 - x0), self.rect.height)

    # ---------- Golpe curto (Kael encostado) ----------
    def _player_in_melee_range(self, player):
        """Kael está perto o bastante (horizontal) e na altura do corpo."""
        if abs(player.rect.centerx - self.rect.centerx) > settings.BOSS_MELEE_TRIGGER_DISTANCE:
            return False
        top = self.rect.top + settings.BOSS_MELEE_TOP_MARGIN
        return player.rect.bottom > top and player.rect.top < self.rect.bottom

    def _melee_allowed_now(self, player):
        """Decide se o golpe curto pode começar NESTE frame. Regras de segurança:

        - CHASE: sempre (com Kael em alcance e recarga pronta).
        - TELEGRAPH do slam: o aviso só tem timer/animação e nada foi executado
          (attack_rect ainda não existe), então cancelar é seguro - desde que
          falte mais tempo do que o próprio aviso do golpe curto (senão o slam,
          já comprometido, sai antes) e que o slam anterior não tenha sido
          cancelado (assim o soco no chão nunca fica sem sair).
        - RECOVER depois do slam: só quando a área de dano do slam (attack_rect)
          e a animação de impacto (strike_kind) já terminaram; assim não há duas
          animações nem dois danos ao mesmo tempo. A recuperação restante é
          pulada (no máx. alguns frames).
        - Aviso de rajada/investida, avanço da investida, ATTACK e o próprio
          golpe curto: nunca (esses ataques não mudaram).
        """
        if not self.alive or player is None or not player.alive:
            return False
        if self.melee_cooldown > 0:
            return False
        if self.attack_rect is not None or self.strike_kind is not None:
            return False
        if self.state == Boss.STATE_CHASE:
            pass
        elif self.state == Boss.STATE_TELEGRAPH:
            if (self.attack_type != Boss.ATTACK_SLAM or self.slam_interrupt_used
                    or self.telegraph_timer <= settings.BOSS_MELEE_WINDUP_FRAMES):
                return False
        elif self.state == Boss.STATE_RECOVER:
            if self.attack_type != Boss.ATTACK_SLAM:
                return False
        else:
            return False
        return self._player_in_melee_range(player)

    def _start_melee(self, player):
        # Ponto do aviso do slam em que estávamos (para a pose continuar, sem "pulo").
        start = 0
        if self.state == Boss.STATE_TELEGRAPH:
            self.slam_interrupt_used = True
            count = len(boss_sprites.BODY_ANIMS["slam_windup"])
            elapsed = max(0, settings.BOSS_SLAM_TELEGRAPH - self.telegraph_timer)
            start = min(count - 1, elapsed * count // max(1, settings.BOSS_SLAM_TELEGRAPH))
        self.melee_windup_start = start
        self.state = Boss.STATE_MELEE
        self.melee_stage = Boss.MELEE_WINDUP
        self.melee_timer = settings.BOSS_MELEE_WINDUP_FRAMES
        self.melee_hit_done = False
        self.melee_rect = None
        self.telegraph_timer = 0
        self.recover_timer = 0
        self.vel_x = 0
        self._aim_melee(player)

    def _aim_melee(self, player):
        self.melee_dir = 1 if player.rect.centerx > self.rect.centerx else -1
        self.facing_right = self.melee_dir > 0

    def _update_melee(self, player):
        """Etapas do golpe curto (só timers/estado; o dano vem de _update_melee_hit)."""
        self.vel_x = 0
        self.melee_timer -= 1
        if self.melee_stage == Boss.MELEE_WINDUP:
            self._aim_melee(player)   # acompanha Kael durante o aviso; trava quando o golpe sai
            if self.melee_timer <= 0:
                self.melee_stage = Boss.MELEE_STRIKE
                self.melee_timer = settings.BOSS_MELEE_ACTIVE_FRAMES
                self.attack_triggered_this_frame = Boss.ATTACK_MELEE
        elif self.melee_stage == Boss.MELEE_STRIKE:
            if self.melee_timer <= 0:
                self.melee_stage = Boss.MELEE_RECOVER
                self.melee_timer = settings.BOSS_MELEE_RECOVER_FRAMES
        elif self.melee_timer <= 0:
            self._end_melee()

    def _end_melee(self):
        self.state = Boss.STATE_CHASE
        self.melee_stage = None
        self.melee_rect = None
        self.attack_timer = settings.BOSS_ATTACK_COOLDOWN   # retoma o ciclo normal, como após o RECOVER
        mult = settings.BOSS_MELEE_PHASE2_COOLDOWN_MULT if self.phase2 else 1.0
        self.melee_cooldown = int(settings.BOSS_MELEE_COOLDOWN * mult)

    def _melee_hitbox(self):
        """Hitbox do golpe: do centro do corpo até BOSS_MELEE_REACH além da borda
        da frente. Sempre calculada a partir de self.rect atual e de melee_dir."""
        top = self.rect.top + settings.BOSS_MELEE_TOP_MARGIN
        height = self.rect.bottom - top
        if self.melee_dir > 0:
            left, right = self.rect.centerx, self.rect.right + settings.BOSS_MELEE_REACH
        else:
            left, right = self.rect.left - settings.BOSS_MELEE_REACH, self.rect.centerx
        return pygame.Rect(left, top, right - left, height)

    def _update_melee_hit(self, player):
        """Roda depois do movimento do frame. Dano no máximo uma vez por golpe;
        se Kael estiver invulnerável (i-frames/dash) o golpe é consumido sem dano,
        igual ao slam."""
        if self.melee_stage != Boss.MELEE_STRIKE:
            self.melee_rect = None
            return
        self.melee_rect = self._melee_hitbox()
        if self.melee_hit_done or not player.alive:
            return
        if self.melee_rect.colliderect(player.rect):
            self.melee_hit_done = True
            player.take_damage(self.damage, knockback_dir=self.melee_dir)

    def _perform_slam(self, player):
        # Alcance calculado a partir do CENTRO do Boss, garantindo que
        # sempre cubra a distância em que a perseguição para
        # (settings.BOSS_CHASE_STOP_DISTANCE) - antes o golpe tinha um
        # alcance menor que essa distância, então um jogador parado bem
        # onde o Boss parava de perseguir ficava fora do hitbox.
        width = settings.BOSS_SLAM_REACH * 2
        height = 36
        x = self.rect.centerx - width // 2
        y = self.rect.bottom - 6
        self.attack_rect = pygame.Rect(x, y, width, height)
        self.attack_active_timer = settings.BOSS_SLAM_ACTIVE_FRAMES
        self.attack_triggered_this_frame = Boss.ATTACK_SLAM
        self.slam_interrupt_used = False   # um slam saiu: o próximo aviso volta a poder ser interrompido

    def _perform_barrage(self, player):
        """Dispara um leque de projéteis na direção do jogador (Fase 2)."""
        count = settings.BOSS_BARRAGE_PROJECTILE_COUNT
        base_direction = 1 if player.rect.centerx > self.rect.centerx else -1
        for i in range(count):
            spread = (i - count // 2) * 0.12
            proj = pygame.Rect(self.rect.centerx, self.rect.centery, 12, 12)
            vy = spread * settings.BOSS_BARRAGE_PROJECTILE_SPEED
            self.projectiles.append({
                "rect": proj,
                "vx": base_direction * settings.BOSS_BARRAGE_PROJECTILE_SPEED,
                "vy": vy,
            })
        self.attack_triggered_this_frame = Boss.ATTACK_BARRAGE

    def _update_projectiles(self, level, player):
        alive_projectiles = []
        for p in self.projectiles:
            p["rect"].x += p["vx"]
            p["rect"].y += p["vy"]
            if level.rect_hits_solid(p["rect"]):
                self._add_impact(p["rect"])
                continue
            if p["rect"].colliderect(player.rect) and player.alive:
                direction = 1 if p["vx"] > 0 else -1
                player.take_damage(self.damage, knockback_dir=direction)
                self._add_impact(p["rect"])
                continue
            if -50 <= p["rect"].x <= level.width + 50:
                alive_projectiles.append(p)
        self.projectiles = alive_projectiles

    def is_vulnerable(self):
        """Vharok pode receber dano em qualquer estado, exceto durante o
        telegraph (fica com hiper-armadura preparando o golpe)."""
        return self.state != Boss.STATE_TELEGRAPH

    def take_damage(self, amount):
        if not self.is_vulnerable():
            return
        previous_health = self.health
        super().take_damage(amount)
        if self.health < previous_health:
            # Feedback exclusivamente visual; o dano real continua sendo
            # aplicado pelo Enemy.take_damage exatamente como antes.
            self._hud_hit_flash_timer = 10

    def _slam_preview_rect(self):
        """Mesma área do golpe de terremoto, calculada antecipadamente
        para mostrar ao jogador ONDE o golpe vai bater durante o
        telegraph (o aviso visual que faltava)."""
        width = settings.BOSS_SLAM_REACH * 2
        height = 36
        x = self.rect.centerx - width // 2
        y = self.rect.bottom - 6
        return pygame.Rect(x, y, width, height)

    # ------------------------------------------------------------------
    # Visual (spritesheet). Nada daqui altera estado de combate.
    # ------------------------------------------------------------------
    def _add_impact(self, rect):
        if self.sprites:
            self.impacts.append({"x": rect.centerx, "y": rect.centery, "t": 0})

    def _update_visual(self):
        self.anim_tick += 1
        if self.phase_flash_timer > 0:
            self.phase_flash_timer -= 1

        # Golpe executado neste frame -> começa a animação de execução.
        if self.attack_triggered_this_frame in (Boss.ATTACK_SLAM, Boss.ATTACK_BARRAGE):
            self.strike_kind = self.attack_triggered_this_frame
            self.strike_tick = 0
        elif self.strike_kind:
            self.strike_tick += 1

        if self.strike_kind == Boss.ATTACK_SLAM and self.strike_tick >= settings.BOSS_SLAM_ACTIVE_FRAMES:
            self.strike_kind = None
        elif (self.strike_kind == Boss.ATTACK_BARRAGE
              and self.strike_tick >= 2 * settings.BOSS_BARRAGE_RELEASE_FRAME_TICKS):
            self.strike_kind = None

        for imp in self.impacts:
            imp["t"] += 1
        self.impacts = [i for i in self.impacts
                        if i["t"] < len(boss_sprites.BURST_FRAMES) * 3]

    def _body_frame_name(self):
        """Quadro do corpo conforme o estado atual da máquina de estados."""
        if self.state == Boss.STATE_DASH:
            # Sem sprite de investida: reaproveita a caminhada, mais rápida.
            return boss_sprites.frame_name(
                "walk", (self.anim_tick // max(1, settings.BOSS_CHARGE_FRAME_TICKS)) % 8)

        if self.state == Boss.STATE_MELEE:
            return self._melee_frame_name()

        if self.state == Boss.STATE_TELEGRAPH:
            if self.attack_type in (Boss.ATTACK_SLAM, Boss.ATTACK_CHARGE):
                anim = "slam_windup"
                total = (settings.BOSS_SLAM_TELEGRAPH if self.attack_type == Boss.ATTACK_SLAM
                         else settings.BOSS_CHARGE_TELEGRAPH)
            else:
                anim, total = "barrage_charge", settings.BOSS_BARRAGE_TELEGRAPH
            count = len(boss_sprites.BODY_ANIMS[anim])
            elapsed = max(0, total - self.telegraph_timer)
            return boss_sprites.frame_name(anim, min(count - 1, elapsed * count // max(1, total)))

        if self.strike_kind == Boss.ATTACK_SLAM:
            idx = min(3, self.strike_tick // settings.BOSS_SLAM_STRIKE_FRAME_TICKS)
            return boss_sprites.frame_name("slam_strike", idx)
        if self.strike_kind == Boss.ATTACK_BARRAGE:
            idx = min(1, self.strike_tick // settings.BOSS_BARRAGE_RELEASE_FRAME_TICKS)
            return boss_sprites.frame_name("barrage_release", idx)

        if self.state in (Boss.STATE_ATTACK, Boss.STATE_RECOVER):
            return boss_sprites.frame_name("recover", 0)

        if abs(self.vel_x) > 0.1:
            ticks = (settings.BOSS_WALK_FRAME_TICKS_RAGE if self.phase2
                     else settings.BOSS_WALK_FRAME_TICKS)
            return boss_sprites.frame_name("walk", (self.anim_tick // ticks) % 8)
        return boss_sprites.frame_name("idle", (self.anim_tick // settings.BOSS_IDLE_FRAME_TICKS) % 8)

    def _melee_frame_name(self):
        """Golpe curto reaproveita a pose do slam: braços erguidos no aviso, os 3
        primeiros quadros do impacto (chamas ainda dentro do alcance da hitbox) no
        golpe e a postura baixa de recuperação."""
        if self.melee_stage == Boss.MELEE_WINDUP:
            total = settings.BOSS_MELEE_WINDUP_FRAMES
            count = len(boss_sprites.BODY_ANIMS["slam_windup"])
            elapsed = max(0, total - self.melee_timer)
            start = self.melee_windup_start
            idx = min(count - 1, start + (count - start) * elapsed // max(1, total))
            return boss_sprites.frame_name("slam_windup", idx)
        if self.melee_stage == Boss.MELEE_STRIKE:
            total = settings.BOSS_MELEE_ACTIVE_FRAMES
            elapsed = max(0, total - self.melee_timer)
            return boss_sprites.frame_name("slam_strike", min(2, elapsed * 3 // max(1, total)))
        return boss_sprites.frame_name("recover", 0)

    def _body_tint(self):
        if self.hit_flash_timer > 0:
            return "hit"
        if (self.state == Boss.STATE_MELEE and self.melee_stage == Boss.MELEE_WINDUP
                and (self.melee_timer // 4) % 2 == 0):
            return "tele_slam"
        if self.phase_flash_timer > 0 and (self.phase_flash_timer // 4) % 2 == 0:
            return "rage_flash"
        if self.state == Boss.STATE_TELEGRAPH and (self.telegraph_timer // 4) % 2 == 0:
            return {Boss.ATTACK_SLAM: "tele_slam",
                    Boss.ATTACK_CHARGE: "tele_charge"}.get(self.attack_type, "tele_barrage")
        if self.phase2:
            return "rage"
        return None

    def _draw_slam_wave(self, surface, camera_x):
        """Onda de choque no chão (efeito avulso), sincronizada com os quadros
        de impacto do corpo. Fica ATRÁS do corpo (e, no jogo, atrás de Kael)."""
        t = self.strike_tick
        stage = t // 3
        if stage < len(boss_sprites.WAVE_STAGES):
            name = boss_sprites.WAVE_STAGES[stage]
            alpha = 255
        else:
            name = "wave_full"
            fade_start = settings.BOSS_SLAM_ACTIVE_FRAMES - 4
            alpha = 255 if t < fade_start else max(0, 255 * (settings.BOSS_SLAM_ACTIVE_FRAMES - t) // 4)
        if alpha <= 0:
            return
        img, (ox, oy) = self.sprites.get(name, self.facing_right)
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        surface.blit(img, (self.rect.centerx - camera_x + ox, self.rect.bottom + 1 + oy))

    def _draw_sprite_boss(self, surface, camera_x):
        spr = self.sprites

        # Aura da Fase 2 (pulsa) - atrás do corpo
        if self.phase2:
            glow = spr.get_glow()
            pulse = 150 + int(80 * math.sin(self.anim_tick * 0.12))
            glow.set_alpha(max(0, min(255, pulse)))
            gx = self.rect.centerx - camera_x - glow.get_width() // 2
            gy = self.rect.bottom - int(glow.get_height() * 0.92)
            surface.blit(glow, (gx, gy))

        if self.strike_kind == Boss.ATTACK_SLAM:
            self._draw_slam_wave(surface, camera_x)

        img, (ox, oy) = spr.get(self._body_frame_name(), self.facing_right, self._body_tint())
        surface.blit(img, (self.rect.centerx - camera_x + ox, self.rect.bottom + oy))

        for p in self.projectiles:
            shard = spr.get_shard(p["vx"], p["vy"])
            pr = p["rect"]
            surface.blit(shard, (pr.centerx - camera_x - shard.get_width() // 2,
                                 pr.centery - shard.get_height() // 2))

        for imp in self.impacts:
            name = boss_sprites.BURST_FRAMES[min(len(boss_sprites.BURST_FRAMES) - 1, imp["t"] // 3)]
            img, (ox, oy) = spr.get(name, True, None, settings.BOSS_IMPACT_SCALE)
            surface.blit(img, (imp["x"] - camera_x + ox, imp["y"] + oy))

    def draw(self, surface, camera_x):
        if not self.alive:
            return
        if self.state == Boss.STATE_TELEGRAPH and self.attack_type == Boss.ATTACK_SLAM:
            # Zona de perigo no chão, pulsando, avisando onde o terremoto
            # vai bater - dá tempo real de reação antes do golpe.
            preview = self._slam_preview_rect().move(-camera_x, 0)
            pulse = 90 + int(70 * abs((self.telegraph_timer % 10) - 5) / 5)
            warn = pygame.Surface((preview.width, preview.height), pygame.SRCALPHA)
            warn.fill((255, 90, 40, pulse))
            surface.blit(warn, preview.topleft)
            pygame.draw.rect(surface, (255, 150, 60), preview, width=2)

        if self.state == Boss.STATE_TELEGRAPH and self.attack_type == Boss.ATTACK_CHARGE:
            # Faixa de perigo na direção da investida.
            lane = self._charge_preview_rect().move(-camera_x, 0)
            pulse = 50 + int(50 * abs((self.telegraph_timer % 10) - 5) / 5)
            warn = pygame.Surface((max(1, lane.width), lane.height), pygame.SRCALPHA)
            warn.fill((60, 200, 230, pulse))
            surface.blit(warn, lane.topleft)
            pygame.draw.rect(surface, (110, 225, 245), lane, width=2)

        if self.state == Boss.STATE_MELEE and self.melee_stage == Boss.MELEE_WINDUP:
            # Zona do golpe curto (a mesma hitbox que será usada), pulsando.
            zone = self._melee_hitbox().move(-camera_x, 0)
            pulse = 90 + int(70 * abs((self.melee_timer % 8) - 4) / 4)
            warn = pygame.Surface((zone.width, zone.height), pygame.SRCALPHA)
            warn.fill((255, 90, 40, pulse))
            surface.blit(warn, zone.topleft)
            pygame.draw.rect(surface, (255, 150, 60), zone, width=2)

        if self.sprites:
            self._draw_sprite_boss(surface, camera_x)
            return

        # ---- Reserva: desenho retangular original (sem a spritesheet) ----
        r = self.rect.move(-camera_x, 0)
        color = (255, 255, 255) if self.hit_flash_timer > 0 else self.color
        if self.state == Boss.STATE_TELEGRAPH:
            telegraph_color = {Boss.ATTACK_SLAM: (255, 210, 80),
                               Boss.ATTACK_CHARGE: (80, 200, 230)}.get(self.attack_type, (200, 100, 230))
            flash = telegraph_color if (self.telegraph_timer // 4) % 2 == 0 else color
            pygame.draw.rect(surface, flash, r, border_radius=6)
        else:
            pygame.draw.rect(surface, color, r, border_radius=6)

        if self.attack_rect:
            ar = self.attack_rect.move(-camera_x, 0)
            pygame.draw.rect(surface, (255, 120, 40), ar, border_radius=4)

        if self.melee_rect:
            mr = self.melee_rect.move(-camera_x, 0)
            pygame.draw.rect(surface, (255, 120, 40), mr, border_radius=4)

        for p in self.projectiles:
            pr = p["rect"].move(-camera_x, 0)
            pygame.draw.ellipse(surface, (200, 100, 230), pr)

    def draw_boss_bar(self, surface):
        """HUD temático de Vharok, fixo na tela e independente da câmera."""
        screen_w, screen_h = surface.get_size()
        if screen_w < 80 or screen_h < 80 or self.max_health <= 0:
            return

        # Dimensões relativas à superfície real: funciona com SCALED/fullscreen
        # e não depende da posição da câmera no mundo.
        bar_w = min(int(screen_w * 0.62), 720)
        bar_w = min(screen_w - 28, max(min(300, screen_w - 28), bar_w))
        bar_h = 17
        bx = (screen_w - bar_w) // 2
        panel = pygame.Rect(bx - 13, 37, bar_w + 26, 48)
        bar = pygame.Rect(bx, 57, bar_w, bar_h)

        # Painel de metal escurecido com borda dupla e pequenos recortes.
        pygame.draw.rect(surface, (7, 5, 10), panel.inflate(4, 4), border_radius=7)
        pygame.draw.rect(surface, (23, 13, 19), panel, border_radius=6)
        pygame.draw.rect(surface, (81, 32, 39), panel, width=1, border_radius=6)
        inner_panel = panel.inflate(-6, -6)
        pygame.draw.rect(surface, (42, 17, 24), inner_panel, width=1, border_radius=4)
        pygame.draw.line(surface, (130, 49, 52), (panel.x + 14, panel.y + 4),
                         (panel.right - 14, panel.y + 4), 1)
        # Pontas metálicas nos quatro cantos.
        for px, py, sx, sy in ((panel.left + 5, panel.top + 5, 1, 1),
                               (panel.right - 5, panel.top + 5, -1, 1),
                               (panel.left + 5, panel.bottom - 5, 1, -1),
                               (panel.right - 5, panel.bottom - 5, -1, -1)):
            pygame.draw.line(surface, (184, 119, 91), (px, py), (px + 6 * sx, py), 1)
            pygame.draw.line(surface, (184, 119, 91), (px, py), (px, py + 5 * sy), 1)

        # Nome e fase ficam acima da barra; o nome permanece centralizado.
        name = self._hud_name_font.render("VHAROK", True, (241, 224, 215))
        name_shadow = self._hud_name_font.render("VHAROK", True, (0, 0, 0))
        name_y = 7
        surface.blit(name_shadow, name_shadow.get_rect(center=(screen_w // 2 + 2, name_y + 2)))
        surface.blit(name, name.get_rect(center=(screen_w // 2, name_y)))

        phase_text = "FASE II  ·  FÚRIA DO ABISMO" if self.phase2 else "FASE I  ·  REI DO ABISMO"
        phase_pulse = (math.sin(self._hud_anim_tick * 0.12) + 1.0) * 0.5 if self.phase2 else 0.0
        phase_color = ((205 + int(40 * phase_pulse), 75 + int(18 * phase_pulse), 65 + int(12 * phase_pulse))
                       if self.phase2 else (177, 158, 157))
        phase = self._hud_phase_font.render(phase_text, True, phase_color)
        surface.blit(phase, phase.get_rect(center=(screen_w // 2, 29)))

        # Fundo da barra e preenchimento real (vida atual imediata).
        pygame.draw.rect(surface, (8, 5, 10), bar, border_radius=4)
        pygame.draw.rect(surface, (53, 12, 22), bar.inflate(-2, -2), border_radius=3)
        ratio = max(0.0, min(1.0, float(self.health) / float(self.max_health)))
        trail_ratio = max(ratio, min(1.0, self._hud_trail_health / float(self.max_health)))
        fill_w = int((bar.width - 2) * ratio)
        trail_w = int((bar.width - 2) * trail_ratio)
        fill_x = bar.x + 1
        fill_y = bar.y + 1
        inner_h = bar.height - 2

        if trail_w > fill_w:
            trail_color = (183, 62, 48) if self.phase2 else (126, 43, 43)
            pygame.draw.rect(surface, trail_color,
                             (fill_x + fill_w, fill_y, trail_w - fill_w, inner_h), border_radius=3)
        if fill_w > 0:
            if self.phase2:
                pulse = int(16 * (0.5 + 0.5 * math.sin(self._hud_anim_tick * 0.15)))
                fill_color = (min(255, 198 + pulse), 24 + pulse // 3, 35 + pulse // 4)
                highlight = (255, 100 + pulse, 76)
            else:
                fill_color = (151, 25, 43)
                highlight = (210, 63, 69)
            pygame.draw.rect(surface, fill_color, (fill_x, fill_y, fill_w, inner_h), border_radius=3)
            if fill_w > 12:
                pygame.draw.line(surface, highlight, (fill_x + 3, fill_y + 2),
                                 (fill_x + fill_w - 3, fill_y + 2), 1)
            # Poucos traços diagonais evocam metal rachado sem poluir a leitura.
            for slash_x in range(fill_x + 30, fill_x + fill_w - 6, 58):
                pygame.draw.line(surface, (105, 21, 34), (slash_x, fill_y + 3),
                                 (slash_x + 5, fill_y + inner_h - 3), 1)

        # O brilho do golpe é curto e não altera o valor de vida.
        if self._hud_hit_flash_timer > 0:
            alpha = int(105 * self._hud_hit_flash_timer / 10)
            flash = pygame.Surface((max(1, fill_w), inner_h), pygame.SRCALPHA)
            flash.fill((255, 205, 184, alpha))
            surface.blit(flash, (fill_x, fill_y))
            pygame.draw.rect(surface, (255, 106, 89), bar, width=1, border_radius=4)

        pygame.draw.rect(surface, (157, 103, 91), bar, width=1, border_radius=4)
        # Marcador discreto do limiar de transformação, sem criar outra condição.
        phase_x = bar.x + int((bar.width - 2) * settings.BOSS_PHASE2_HEALTH_RATIO)
        pygame.draw.line(surface, (228, 174, 139), (phase_x, bar.y - 2), (phase_x, bar.bottom + 2), 1)

        # Transição temporária disparada junto com a mudança real para phase2.
        if self._hud_phase_transition_timer > 0 and self.phase2:
            remaining = self._hud_phase_transition_timer
            elapsed = self._hud_phase_transition_duration - remaining
            fade_in = min(1.0, elapsed / 18.0)
            fade_out = min(1.0, remaining / 32.0)
            alpha = int(235 * min(fade_in, fade_out))
            if alpha > 0:
                center_y = min(screen_h // 2 - 20, 145)
                overlay_w = min(screen_w - 32, 600)
                overlay_h = 76
                overlay = pygame.Surface((overlay_w, overlay_h), pygame.SRCALPHA)
                overlay_rect = overlay.get_rect()
                pygame.draw.rect(overlay, (13, 4, 10, int(alpha * 0.88)), overlay_rect, border_radius=7)
                pygame.draw.rect(overlay, (190, 39, 49, alpha), overlay_rect, width=2, border_radius=7)
                pygame.draw.line(overlay, (255, 87, 65, alpha), (22, 8), (overlay_w - 22, 8), 1)
                title = self._hud_transition_font.render("VHAROK DESPERTOU", True, (255, 224, 211))
                subtitle = self._hud_transition_sub_font.render("FASE II  —  FÚRIA DO ABISMO", True, (255, 91, 76))
                # Entrada curta com deslocamento suave e leve escala.
                scale = 0.88 + 0.12 * fade_in
                title_size = (max(1, int(title.get_width() * scale)), max(1, int(title.get_height() * scale)))
                title = pygame.transform.smoothscale(title, title_size)
                title.set_alpha(alpha)
                subtitle.set_alpha(alpha)
                overlay.blit(title, title.get_rect(center=(overlay_w // 2, 29)))
                overlay.blit(subtitle, subtitle.get_rect(center=(overlay_w // 2, 56)))
                overlay.set_alpha(alpha)
                surface.blit(overlay, overlay.get_rect(center=(screen_w // 2, center_y)))
