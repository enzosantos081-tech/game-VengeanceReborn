"""
enemies/basic_enemy.py
Inimigo comum: patrulha, detecta Kael e usa uma animação de ataque corpo a corpo.
O inimigo à distância continua usando a lógica original de projéteis.
"""

import math
import os
import pygame
from config import settings
from enemies.enemy import Enemy

# As sprites olham para a esquerda; são espelhadas apenas ao desenhar.
_SPRITE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "assets", "basic_enemy")


def _load_frames(prefix, count):
    frames = []
    for i in range(count):
        path = os.path.join(_SPRITE_DIR, f"{prefix}_{i}.png")
        try:
            frames.append(pygame.image.load(path).convert_alpha())
        except (pygame.error, OSError):
            return []
    return frames


_IDLE_FRAMES = None
_WALK_FRAMES = None
_ATTACK_FRAMES = None


def _get_basic_enemy_frames():
    global _IDLE_FRAMES, _WALK_FRAMES, _ATTACK_FRAMES
    if _IDLE_FRAMES is None:
        try:
            _IDLE_FRAMES = _load_frames("idle", 4)
            _WALK_FRAMES = _load_frames("walk", 6)
            _ATTACK_FRAMES = _load_frames("attack", 6)
        except pygame.error:
            _IDLE_FRAMES, _WALK_FRAMES, _ATTACK_FRAMES = [], [], []
    return _IDLE_FRAMES, _WALK_FRAMES, _ATTACK_FRAMES


class BasicEnemy(Enemy):
    """Patrulha, persegue Kael e executa ataques corpo a corpo."""

    PATROL = "PATROL"
    CHASE = "CHASE"
    ATTACK = "ATTACK"
    RECOVERY = "RECOVERY"

    def __init__(self, x, y):
        super().__init__(
            x, y,
            settings.BASIC_ENEMY_WIDTH, settings.BASIC_ENEMY_HEIGHT,
            settings.BASIC_ENEMY_HEALTH, settings.BASIC_ENEMY_DAMAGE,
            settings.COLOR_ENEMY,
            coin_value=settings.ENEMY_COIN_DROP_BASIC,
        )
        self.left_bound = x - settings.BASIC_ENEMY_PATROL_RANGE
        self.right_bound = x + settings.BASIC_ENEMY_PATROL_RANGE
        self.direction = 1
        self.animation_timer = 0
        self.animation_frame = 0
        self.combat_state = self.PATROL
        self.attack_timer = 0
        self.recovery_timer = 0
        self.attack_impact_checked = False
        self.attack_advanced = 0   # px já avançados no golpe atual
        self.alerted = False
        self._was_alive = True

    def respawn(self):
        super().respawn()
        self.direction = 1
        self.animation_timer = 0
        self.animation_frame = 0
        self.combat_state = self.PATROL
        self.attack_timer = 0
        self.recovery_timer = 0
        self.attack_impact_checked = False
        self.attack_advanced = 0
        self.alerted = False
        self._was_alive = True

    def _start_attack(self, player):
        self.combat_state = self.ATTACK
        self.attack_timer = 0
        self.attack_impact_checked = False
        self.attack_advanced = 0
        self.facing_right = player.rect.centerx > self.rect.centerx

    def _attack_frame_index(self):
        ticks = max(1, settings.BASIC_ENEMY_ATTACK_FRAME_TICKS)
        return min(self.attack_timer // ticks, 5)

    @staticmethod
    def _horizontal_gap(rect_a, rect_b):
        """Distância horizontal entre hitboxes (zero quando se sobrepõem)."""
        if rect_a.right < rect_b.left:
            return rect_b.left - rect_a.right
        if rect_b.right < rect_a.left:
            return rect_a.left - rect_b.right
        return 0

    def _attack_advance_velocity(self, level, player):
        """Velocidade horizontal durante o golpe: um passo curto e limitado na
        direção travada do ataque. Só ocorre na fase de preparação (antes do
        impacto), nunca depois; para ao ficar perto o bastante, ao esgotar a
        distância máxima, se Kael ficou atrás do inimigo ou se não houver
        chão à frente. Paredes continuam sendo resolvidas pelo
        move_and_collide_enemy."""
        if not player.alive or self.attack_impact_checked:
            return 0.0
        frame = self._attack_frame_index()
        if not (settings.BASIC_ENEMY_ATTACK_ADVANCE_START_FRAME <= frame
                < settings.BASIC_ENEMY_ATTACK_IMPACT_FRAME):
            return 0.0
        direction = 1 if self.facing_right else -1
        ahead = (player.rect.centerx >= self.rect.centerx if self.facing_right
                 else player.rect.centerx <= self.rect.centerx)
        if not ahead:
            return 0.0  # Kael passou para trás: não vira nem ultrapassa
        gap = self._horizontal_gap(self.rect, player.rect)
        step = min(settings.BASIC_ENEMY_ATTACK_ADVANCE_SPEED,
                   settings.BASIC_ENEMY_ATTACK_ADVANCE_MAX_DISTANCE - self.attack_advanced,
                   gap - settings.BASIC_ENEMY_ATTACK_ADVANCE_STOP_GAP)
        if step <= 0 or not level.has_ground_ahead(self.rect, direction):
            return 0.0
        return step * direction

    def _build_attack_hitbox(self):
        """Hitbox curta, na frente do corpo e no espaço mundial do jogo."""
        enemy_box = self.rect
        reach = settings.BASIC_ENEMY_ATTACK_RANGE
        # A faixa vertical cobre o tronco/pernas, mas não a altura inteira do
        # sprite visual (que é maior que a hitbox física de 32x32).
        hit_y = enemy_box.top + max(2, enemy_box.height // 6)
        hit_h = max(1, enemy_box.height - max(4, enemy_box.height // 4))
        if self.facing_right:
            return pygame.Rect(enemy_box.right, hit_y, reach, hit_h), 1
        return pygame.Rect(enemy_box.left - reach, hit_y, reach, hit_h), -1

    def _apply_attack_impact(self, player):
        """Resolve o golpe uma única vez, no quadro de impacto da animação."""
        if not player.alive:
            return False

        attack_box, knockback_dir = self._build_attack_hitbox()
        # As duas rects estão em coordenadas de mundo (camera_x só é usada no
        # draw). A colisão é revalidada no frame do impacto para permitir que
        # pulo, knockback e dash evitem o golpe. take_damage preserva i-frames.
        target_box = player.rect
        on_attacked_side = (
            target_box.centerx >= self.rect.centerx if self.facing_right
            else target_box.centerx <= self.rect.centerx
        )
        if on_attacked_side and attack_box.colliderect(target_box):
            player.take_damage(self.damage, knockback_dir=knockback_dir)
            return True
        return False

    def update(self, level, player):
        was_alive = self.alive
        super().update(level, player)
        if not self.alive:
            self.vel_x = 0
            return
        # Se acabou de reaparecer, respawn() já reinicializou o estado.
        if not was_alive:
            return

        self.animation_timer += 1
        player_alive = bool(player.alive)
        distance_x = player.rect.centerx - self.rect.centerx if player_alive else 10**9
        abs_center_distance = abs(distance_x)
        hitbox_gap = self._horizontal_gap(self.rect, player.rect) if player_alive else 10**9

        detect_range = settings.BASIC_ENEMY_DETECTION_RANGE
        pursuit_range = settings.BASIC_ENEMY_PURSUIT_RANGE
        attack_range = settings.BASIC_ENEMY_ATTACK_RANGE

        # A detecção inicia o combate; uma distância maior encerra a perseguição.
        # Isso cria histerese e evita alternância rápida perto do limite.
        if player_alive and not self.alerted and hitbox_gap <= detect_range:
            self.alerted = True
        elif not player_alive or (self.alerted and hitbox_gap > pursuit_range):
            self.alerted = False

        engaged = self.alerted and player_alive
        if engaged and self.combat_state != self.ATTACK:
            self.facing_right = distance_x > 0

        if self.combat_state == self.ATTACK:
            # A direção fica travada durante a animação; o inimigo só dá um
            # passo curto na preparação do golpe (ver _attack_advance_velocity).
            self.attack_timer += 1
            self.vel_x = self._attack_advance_velocity(level, player)
            impact_frame = settings.BASIC_ENEMY_ATTACK_IMPACT_FRAME
            if (not self.attack_impact_checked
                    and self._attack_frame_index() >= impact_frame):
                self.attack_impact_checked = True
                self._apply_attack_impact(player)

            attack_duration = 6 * max(1, settings.BASIC_ENEMY_ATTACK_FRAME_TICKS)
            if self.attack_timer >= attack_duration:
                self.combat_state = self.RECOVERY
                self.recovery_timer = settings.BASIC_ENEMY_ATTACK_COOLDOWN

        elif self.combat_state == self.RECOVERY:
            self.vel_x = 0
            if not engaged:
                self.combat_state = self.PATROL
                self.recovery_timer = 0
            else:
                self.recovery_timer -= 1
                if self.recovery_timer <= 0:
                    if hitbox_gap <= attack_range:
                        self._start_attack(player)
                    else:
                        # Continua aproximando-se após a recuperação se Kael
                        # estiver perto, mas ainda fora do alcance do golpe.
                        self.combat_state = self.CHASE

        elif engaged:
            # Quando estiver no alcance efetivo, para e inicia o golpe.
            if hitbox_gap <= attack_range:
                self.vel_x = 0
                self._start_attack(player)
            else:
                # Persegue caminhando na direção da posição atual de Kael.
                self.combat_state = self.CHASE
                chase_direction = 1 if distance_x > 0 else -1
                self.direction = chase_direction
                self.facing_right = chase_direction > 0
                self.vel_x = settings.BASIC_ENEMY_SPEED * chase_direction
                # Evita perseguir para dentro de um buraco. Paredes e plataformas
                # continuam sendo resolvidas pelo move_and_collide_enemy existente.
                if not level.has_ground_ahead(self.rect, chase_direction):
                    self.vel_x = 0

        else:
            # Sem alvo: volta à patrulha normal e aos limites de origem.
            self.combat_state = self.PATROL
            self.vel_x = settings.BASIC_ENEMY_SPEED * self.direction
            if self.rect.x <= self.left_bound:
                self.direction = 1
            elif self.rect.x >= self.right_bound:
                self.direction = -1
            if not level.has_ground_ahead(self.rect, self.direction):
                self.direction *= -1
            self.vel_x = settings.BASIC_ENEMY_SPEED * self.direction
            self.facing_right = self.direction > 0

        # Gravidade e colisões existentes são processadas em todos os estados.
        self.vel_y += settings.GRAVITY
        if self.vel_y > settings.MAX_FALL_SPEED:
            self.vel_y = settings.MAX_FALL_SPEED
        x_before = self.rect.x
        level.move_and_collide_enemy(self, self.vel_x, self.vel_y)
        if self.combat_state == self.ATTACK:
            # Conta o avanço REAL (parede/colisão não conta como progresso).
            self.attack_advanced += abs(self.rect.x - x_before)

    def draw(self, surface, camera_x):
        if not self.alive:
            return

        idle_frames, walk_frames, attack_frames = _get_basic_enemy_frames()
        if not idle_frames or not walk_frames:
            super().draw(surface, camera_x)
            return

        if self.combat_state == self.ATTACK and attack_frames:
            frame_index = self._attack_frame_index()
            frame = attack_frames[frame_index]
        else:
            moving = self.combat_state in (self.PATROL, self.CHASE) and abs(self.vel_x) > 0.1
            frames = walk_frames if moving else idle_frames
            ticks = (settings.BASIC_ENEMY_WALK_FRAME_TICKS if moving
                     else settings.BASIC_ENEMY_IDLE_FRAME_TICKS)
            frame_index = (self.animation_timer // max(1, ticks)) % len(frames)
            frame = frames[frame_index]

        target_h = settings.BASIC_ENEMY_SPRITE_HEIGHT
        target_w = max(1, round(frame.get_width() * target_h / frame.get_height()))
        sprite = pygame.transform.scale(frame, (target_w, target_h))
        if self.facing_right:
            sprite = pygame.transform.flip(sprite, True, False)

        draw_rect = sprite.get_rect(midbottom=(self.rect.centerx - camera_x,
                                               self.rect.bottom + 2))
        if self.hit_flash_timer > 0:
            flash = sprite.copy()
            flash.fill((130, 130, 130, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(flash, draw_rect)
        else:
            surface.blit(sprite, draw_rect)


# Sprites do inimigo à distância (extraídas da spritesheet fornecida).
_RANGED_SPRITE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "assets", "ranged_enemy")
_RANGED_FRAMES = None
_RANGED_PROJECTILE = None


def _load_ranged_frames(prefix, count):
    frames = []
    for i in range(count):
        path = os.path.join(_RANGED_SPRITE_DIR, f"{prefix}_{i}.png")
        try:
            frames.append(pygame.image.load(path).convert_alpha())
        except (pygame.error, OSError):
            return []
    return frames


def _get_ranged_frames():
    global _RANGED_FRAMES, _RANGED_PROJECTILE
    if _RANGED_FRAMES is None:
        try:
            _RANGED_FRAMES = {
                "idle": _load_ranged_frames("idle", 4),
                "walk": _load_ranged_frames("walk", 6),
                "cast": _load_ranged_frames("cast", 6),
            }
            projectile_path = os.path.join(_RANGED_SPRITE_DIR, "projectile.png")
            _RANGED_PROJECTILE = pygame.image.load(projectile_path).convert_alpha()
        except (pygame.error, OSError):
            _RANGED_FRAMES = {"idle": [], "walk": [], "cast": []}
            _RANGED_PROJECTILE = None
    return _RANGED_FRAMES, _RANGED_PROJECTILE


class RangedEnemy(Enemy):
    """Atirador com sprites animadas. Mira na posição atual de Kael (vetor
    normalizado, qualquer ângulo) e só ataca com linha de visão livre; os
    projéteis colidem com os mesmos sólidos do resto do jogo."""

    def __init__(self, x, y):
        super().__init__(
            x, y,
            settings.RANGED_ENEMY_WIDTH, settings.RANGED_ENEMY_HEIGHT,
            settings.RANGED_ENEMY_HEALTH, settings.RANGED_ENEMY_DAMAGE,
            settings.COLOR_ENEMY_RANGED,
            coin_value=settings.ENEMY_COIN_DROP_RANGED,
        )
        self.cooldown = 0
        self.projectiles = []
        self.animation_timer = 0
        self.casting = False
        self.cast_timer = 0
        self.pending_shot_dir = 0
        self.shot_released = False

    def respawn(self):
        super().respawn()
        self.cooldown = 0
        self.projectiles = []
        self.animation_timer = 0
        self.casting = False
        self.cast_timer = 0
        self.pending_shot_dir = 0
        self.shot_released = False

    def update(self, level, player):
        super().update(level, player)
        if not self.alive:
            return

        self.animation_timer += 1
        self.vel_y += settings.GRAVITY
        if self.vel_y > settings.MAX_FALL_SPEED:
            self.vel_y = settings.MAX_FALL_SPEED
        # Mantém a rotina de colisão original: o ranged enemy não caminha no chão.
        level.move_and_collide_enemy(self, 0, self.vel_y)

        distance = player.rect.centerx - self.rect.centerx
        if player.alive:
            self.facing_right = distance > 0

        if self.cooldown > 0:
            self.cooldown -= 1

        if self.casting:
            self.cast_timer += 1
            ticks = max(1, settings.RANGED_ENEMY_CAST_FRAME_TICKS)
            frame_index = min(self.cast_timer // ticks, 5)
            if not self.shot_released and frame_index >= settings.RANGED_ENEMY_RELEASE_FRAME:
                self._release_projectile(level, player)
                self.shot_released = True
            if self.cast_timer >= 6 * ticks:
                self.casting = False
                self.cast_timer = 0
                self.pending_shot_dir = 0
                self.shot_released = False
        elif (self.cooldown <= 0 and player.alive
              and self._player_in_range(player)
              and self._visible_aim_point(level, player) is not None):
            # Alcance e linha de visão são verificações separadas. Sem
            # visão livre o inimigo não inicia o ataque nem gasta o
            # cooldown: fica parado e dispara assim que Kael ficar visível.
            self.pending_shot_dir = 1 if distance > 0 else -1
            self.facing_right = self.pending_shot_dir > 0
            self.casting = True
            self.cast_timer = 0
            self.shot_released = False
            self.cooldown = settings.RANGED_ENEMY_COOLDOWN

        self._update_projectiles(level, player)

    # ---------- Mira e linha de visão ----------
    def _player_in_range(self, player):
        """Alcance: distância entre os centros das hitboxes (sem considerar
        paredes - a visão é checada à parte em _visible_aim_point)."""
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        return math.hypot(dx, dy) <= settings.RANGED_ENEMY_RANGE

    def _visible_aim_point(self, level, player):
        """Ponto do corpo de Kael visível a partir do centro do inimigo, ou
        None se os sólidos bloquearem a visão. O centro da hitbox tem
        prioridade; topo/base servem de alternativa para quinas de
        plataforma (se qualquer parte está exposta, a bola de fogo
        consegue atingi-lo)."""
        origin = self.rect.center
        pr = player.rect
        for target in ((pr.centerx, pr.centery),
                       (pr.centerx, pr.top + 3),
                       (pr.centerx, pr.bottom - 3)):
            if level.has_line_of_sight(origin, target):
                return target
        return None

    def _release_projectile(self, level, player):
        """Dispara no quadro de lançamento, mirando na posição ATUAL de
        Kael. A direção é fixada aqui (sem perseguição depois). Se Kael
        morreu ou ficou atrás de um sólido durante a animação, não dispara."""
        if not player.alive:
            return
        target = self._visible_aim_point(level, player)
        if target is None:
            return

        ox, oy = self.rect.center
        dx, dy = target[0] - ox, target[1] - oy
        length = math.hypot(dx, dy)
        if length < settings.RANGED_ENEMY_AIM_MIN_DISTANCE:
            dx, dy, length = (1 if self.facing_right else -1), 0, 1
        ux, uy = dx / length, dy / length  # vetor unitário

        # Nasce logo à frente do corpo, na direção da mira. Na horizontal
        # fica exatamente onde nascia antes (borda lateral da hitbox).
        offset = self.rect.width / 2 + settings.PROJECTILE_SIZE / 2
        cx = ox + ux * offset
        cy = oy + uy * offset
        speed = settings.PROJECTILE_SPEED  # mesma velocidade em qualquer ângulo
        vx, vy = ux * speed, uy * speed

        # A hitbox permanece pequena; a arte da magia é apenas visual.
        proj = pygame.Rect(0, 0, settings.PROJECTILE_SIZE, settings.PROJECTILE_SIZE)
        proj.center = (round(cx), round(cy))
        self.projectiles.append({
            "rect": proj, "pos": [cx, cy], "vel": (vx, vy),
            "dir": 1 if vx >= 0 else -1, "anim": 0,
        })

    def _update_projectiles(self, level, player):
        alive_projectiles = []
        # Movimento em passos de no máximo metade da hitbox: o projétil não
        # "pula" por cima de um sólido fino entre dois frames.
        max_step = max(1, settings.PROJECTILE_SIZE // 2)
        for p in self.projectiles:
            vx, vy = p["vel"]
            steps = max(1, math.ceil(math.hypot(vx, vy) / max_step))
            p["anim"] = p.get("anim", 0) + 1
            hit = False
            for _ in range(steps):
                p["pos"][0] += vx / steps
                p["pos"][1] += vy / steps
                p["rect"].center = (round(p["pos"][0]), round(p["pos"][1]))
                if level.rect_hits_solid(p["rect"]):
                    hit = True
                    break
                if player.alive and p["rect"].colliderect(player.rect):
                    player.take_damage(self.damage, knockback_dir=p["dir"])
                    hit = True
                    break
            if hit:
                continue
            if 0 <= p["rect"].x <= level.width and -200 <= p["rect"].y <= level.height + 200:
                alive_projectiles.append(p)
        self.projectiles = alive_projectiles

    def draw(self, surface, camera_x):
        if not self.alive:
            return
        frames_by_state, projectile_image = _get_ranged_frames()
        frames = frames_by_state.get("cast" if self.casting else "idle", [])
        if frames:
            if self.casting:
                ticks = max(1, settings.RANGED_ENEMY_CAST_FRAME_TICKS)
                frame_index = min(self.cast_timer // ticks, len(frames) - 1)
            else:
                ticks = max(1, settings.RANGED_ENEMY_IDLE_FRAME_TICKS)
                frame_index = (self.animation_timer // ticks) % len(frames)
            frame = frames[frame_index]
            target_h = settings.RANGED_ENEMY_SPRITE_HEIGHT
            target_w = max(1, round(frame.get_width() * target_h / frame.get_height()))
            sprite = pygame.transform.scale(frame, (target_w, target_h))
            if self.facing_right:
                sprite = pygame.transform.flip(sprite, True, False)
            draw_rect = sprite.get_rect(midbottom=(self.rect.centerx - camera_x,
                                                   self.rect.bottom + 2))
            if self.hit_flash_timer > 0:
                flash = sprite.copy()
                flash.fill((130, 130, 130, 0), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(flash, draw_rect)
            else:
                surface.blit(sprite, draw_rect)
        else:
            super().draw(surface, camera_x)

        for p in self.projectiles:
            r = p["rect"].move(-camera_x, 0)
            if projectile_image is not None:
                visual_size = settings.RANGED_ENEMY_PROJECTILE_VISUAL_SIZE
                orb = pygame.transform.scale(projectile_image, (visual_size, visual_size))
                vx, vy = p["vel"]
                if vx < 0:
                    orb = pygame.transform.flip(orb, True, False)
                # Inclina o orbe para o ângulo do disparo (0 na horizontal,
                # então o visual antigo não muda).
                angle = math.degrees(math.atan2(-vy, vx)) - (180 if vx < 0 else 0)
                if abs(angle) > 0.5:
                    orb = pygame.transform.rotate(orb, angle)
                surface.blit(orb, orb.get_rect(center=r.center))
            else:
                pygame.draw.ellipse(surface, settings.COLOR_ENEMY_RANGED, r)
