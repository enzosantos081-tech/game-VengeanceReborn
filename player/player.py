"""
player/player.py
Responsável pelo personagem Kael: posição, movimentação, pulo, gravidade,
vida e desenho. A física é propositalmente simples (não é um jogo de
precisão como Celeste): velocidade horizontal constante, gravidade
acumulativa e um pulo único, com pequenas margens de tolerância
(coyote time e jump buffer) para deixar os controles mais agradáveis.
"""

import pygame
from config import settings
from player.player_attack import PlayerAttack
from player.player_stats import PlayerStats
from player.player_sprites import SpriteAnimator


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT)
        self.spawn_x = x
        self.spawn_y = y

        self.vel_x = 0
        self.vel_y = 0
        self.facing_right = True

        # Direção usada apenas para a hitbox do ataque (definida pela
        # posição do mouse no momento do golpe). Independente de
        # facing_right, que continua representando para onde o
        # personagem está olhando/andando.
        self.attack_facing_right = True

        self.on_ground = False
        self.coyote_timer = 0
        self.jump_buffer_timer = 0

        self.stats = PlayerStats()
        self.health = self.stats.max_health

        self.attack = PlayerAttack()
        self.sprite = SpriteAnimator()

        self.invuln_timer = 0
        self.alive = True

        self.knockback_x = 0

        # Referência à plataforma móvel em que o jogador está apoiado
        # neste momento (ou None). Usada para "colar" o jogador nela
        # antes da gravidade ser aplicada, evitando que ele perca contato
        # e caia por baixo quando a plataforma desce (ver world/level.py).
        self.standing_platform = None

        # ---------- Dash (tecla Q) ----------
        self.dashing = False
        self.dash_timer = 0
        self.dash_charges = 1          # cargas de dash disponíveis agora
        self.max_dash_charges = 1      # recalculado a cada frame (1 + stats.extra_dash_charges)
        self.dash_recharge_timer = 0
        self.dash_dir = 1

        # ---------- Wall slide / wall jump ----------
        self.touching_wall = 0        # -1 esquerda, 0 nenhuma, 1 direita (só quando no ar)
        self.wall_jump_lock_timer = 0  # ignora input horizontal por alguns frames após um wall jump

        # ---------- Pulo duplo (melhoria da loja) ----------
        self.air_jumps_remaining = 0  # recarrega ao tocar o chão ou uma parede

        # Flags de eventos do frame atual (usados para disparar sons em core/game.py)
        self.just_jumped = False
        self.just_attacked = False
        self.just_dashed = False

    # ---------- Ciclo de vida ----------
    def respawn_at_core(self, core_x, core_y):
        """Chamado pelo systems/respawn.py: restaura vida e reposiciona Kael
        no ponto do Núcleo do Retorno, mantendo moedas e melhorias."""
        self.rect.x = core_x
        self.rect.y = core_y
        self.vel_x = 0
        self.vel_y = 0
        self.health = self.stats.max_health
        self.alive = True
        self.invuln_timer = settings.PLAYER_INVULN_FRAMES
        self.standing_platform = None
        self.dashing = False
        self.dash_timer = 0
        self.dash_charges = 1 + self.stats.extra_dash_charges
        self.max_dash_charges = self.dash_charges
        self.dash_recharge_timer = 0
        self.touching_wall = 0
        self.wall_jump_lock_timer = 0
        self.air_jumps_remaining = 0

    def take_damage(self, amount, knockback_dir=0):
        if self.invuln_timer > 0 or not self.alive:
            return
        self.health -= amount
        self.invuln_timer = settings.PLAYER_INVULN_FRAMES
        self.vel_y = settings.KNOCKBACK_Y
        self.knockback_x = settings.KNOCKBACK_X * knockback_dir
        if self.health <= 0:
            self.health = 0
            self.alive = False

    # ---------- Update ----------
    def handle_input(self, input_manager, camera_x=0):
        self.just_attacked = False
        move = 0
        if input_manager.move_left():
            move -= 1
            self.facing_right = False
        if input_manager.move_right():
            move += 1
            self.facing_right = True

        if self.wall_jump_lock_timer <= 0:
            self.vel_x = move * settings.PLAYER_SPEED
        # Enquanto o wall jump está "travado" (poucos frames), o input
        # horizontal é ignorado para garantir que o jogador realmente se
        # afaste da parede em vez de grudar nela de novo instantaneamente.

        if input_manager.jump_pressed():
            self.jump_buffer_timer = settings.JUMP_BUFFER_FRAMES

        if input_manager.attack_pressed():
            # Mira do ataque: qual lado do personagem o cursor está.
            # facing_right (a direção que o personagem olha/anda) NÃO
            # é alterado por isso - só a hitbox do golpe muda de lado.
            mouse_world_x = input_manager.mouse_world_x(camera_x)
            aim_right = mouse_world_x >= self.rect.centerx
            started = self.attack.try_start(cooldown=self.stats.attack_cooldown)
            if started:
                self.attack_facing_right = aim_right
            self.just_attacked = started

        if input_manager.dash_pressed():
            self._try_start_dash()

    def _try_start_dash(self):
        if self.dashing or self.dash_charges <= 0:
            return
        self.dash_charges -= 1
        self.dashing = True
        self.dash_timer = settings.DASH_DURATION_FRAMES
        self.dash_dir = 1 if self.facing_right else -1
        # O dash concede algumas frames de invencibilidade, um recurso
        # comum em jogos de plataforma para permitir atravessar perigos.
        self.invuln_timer = max(self.invuln_timer, settings.DASH_INVULN_FRAMES)
        self.just_dashed = True

    def _apply_jump_if_possible(self):
        if self.jump_buffer_timer <= 0:
            return
        can_ground_jump = self.on_ground or self.coyote_timer > 0
        if can_ground_jump:
            self._start_jump(self.stats.jump_force)
        elif self.touching_wall != 0:
            self._start_wall_jump()
        elif self.air_jumps_remaining > 0:
            self.air_jumps_remaining -= 1
            self._start_jump(self.stats.jump_force)

    def _start_jump(self, force):
        self.vel_y = force
        self.on_ground = False
        self.coyote_timer = 0
        self.jump_buffer_timer = 0
        self.just_jumped = True

    def _start_wall_jump(self):
        """Pulo na parede: impulso diagonal para longe dela. É um recurso
        independente do pulo duplo (não consome air_jumps_remaining)."""
        push_dir = -self.touching_wall
        self.vel_y = settings.WALL_JUMP_FORCE_Y
        self.vel_x = settings.WALL_JUMP_FORCE_X * push_dir
        self.knockback_x = 0
        self.wall_jump_lock_timer = settings.WALL_JUMP_LOCK_FRAMES
        self.facing_right = push_dir > 0
        self.touching_wall = 0
        self.coyote_timer = 0
        self.jump_buffer_timer = 0
        self.just_jumped = True

    def update(self, level):
        if not self.alive:
            return

        self.just_jumped = False
        self.just_dashed = False
        self._apply_jump_if_possible()

        # Recarga de cargas de dash: enquanto estiver abaixo do máximo
        # (1, ou 2 se a melhoria "carga extra de dash" foi comprada),
        # conta até settings.DASH_COOLDOWN_FRAMES e devolve uma carga.
        self.max_dash_charges = 1 + self.stats.extra_dash_charges
        if self.dash_charges < self.max_dash_charges:
            self.dash_recharge_timer += 1
            if self.dash_recharge_timer >= settings.DASH_COOLDOWN_FRAMES:
                self.dash_recharge_timer = 0
                self.dash_charges += 1
        else:
            self.dash_recharge_timer = 0

        if self.wall_jump_lock_timer > 0:
            self.wall_jump_lock_timer -= 1

        if self.dashing:
            # Durante o dash: velocidade horizontal fixa na direção do
            # dash, sem gravidade, movimento reto (comum em dashes de
            # plataforma - dá uma sensação de golpe rápido e confiável).
            self.dash_timer -= 1
            self.vel_y = 0
            horizontal_vel = settings.DASH_SPEED * self.dash_dir
            if self.dash_timer <= 0:
                self.dashing = False
        else:
            # Gravidade
            self.vel_y += settings.GRAVITY
            if self.vel_y > settings.MAX_FALL_SPEED:
                self.vel_y = settings.MAX_FALL_SPEED

            # Wall slide: se no frame anterior o jogador ficou encostado
            # numa parede (no ar) e continua segurando a direção dela,
            # a queda é freada até uma velocidade máxima - dá tempo de
            # reagir e mantém a janela pro wall jump.
            pressing_into_wall = (
                (self.touching_wall == 1 and self.vel_x > 0)
                or (self.touching_wall == -1 and self.vel_x < 0)
            )
            if not self.on_ground and self.touching_wall != 0 and pressing_into_wall:
                if self.vel_y > settings.WALL_SLIDE_MAX_FALL_SPEED:
                    self.vel_y = settings.WALL_SLIDE_MAX_FALL_SPEED

            horizontal_vel = self.vel_x

        # Timers
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= 1
        if self.invuln_timer > 0:
            self.invuln_timer -= 1

        # Knockback horizontal decai suavemente
        total_vx = horizontal_vel + self.knockback_x
        if self.knockback_x != 0:
            self.knockback_x *= 0.85
            if abs(self.knockback_x) < 0.3:
                self.knockback_x = 0

        # Movimento + colisão (delegado ao systems/collision.py via level)
        was_on_ground = self.on_ground
        level.move_and_collide(self, total_vx, self.vel_y)

        if was_on_ground and not self.on_ground:
            self.coyote_timer = settings.COYOTE_TIME_FRAMES
        elif self.coyote_timer > 0 and not self.on_ground:
            self.coyote_timer -= 1

        # O pulo aéreo extra (pulo duplo) recarrega sempre que o jogador
        # toca o chão OU uma parede - tocar numa parede "reseta" a
        # chance de pulo aéreo, como é comum em jogos com wall jump e
        # pulo duplo juntos.
        if self.on_ground or self.touching_wall != 0:
            self.air_jumps_remaining = self.stats.extra_jumps

        self.attack.update()

        # Fora da fase por baixo (buraco/queda) conta como dano fatal
        if self.rect.top > level.height + 200:
            self.health = 0
            self.alive = False

        self._update_sprite_state()
        self.sprite.update()

    def _update_sprite_state(self):
        """Escolhe qual animação mostrar, por ordem de prioridade -
        morte/ataque/dash sempre "vencem" o resto porque são estados
        curtos e importantes de comunicar claramente ao jogador."""
        if not self.alive:
            state = "death"
        elif self.dashing:
            state = "dash"
        elif self.attack.active:
            state = "attack"
        elif not self.on_ground:
            if self.touching_wall != 0:
                state = "wallslide"
            elif self.vel_y < 0:
                state = "jump"
            else:
                state = "fall"
        elif abs(self.vel_x) > 0.5:
            state = "run"
        else:
            state = "idle"
        self.sprite.set_state(state)

    # ---------- Desenho ----------
    def draw(self, surface, camera_x):
        blinking = self.invuln_timer > 0 and (self.invuln_timer // 4) % 2 == 0
        if not blinking:
            img = self.sprite.get_surface(self.facing_right)
            r = self.rect.move(-camera_x, 0)
            # Ancora o sprite pelo centro-baixo (pés), que é bem maior
            # que o hitbox de colisão (34x46) - a física continua usando
            # só o rect original, isso aqui é puramente visual.
            dest = img.get_rect(midbottom=(r.centerx, r.bottom + 6))
            surface.blit(img, dest)
