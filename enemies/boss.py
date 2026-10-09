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

    ATTACK_SLAM = "slam"
    ATTACK_BARRAGE = "barrage"

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
        self.attack_triggered_this_frame = None  # "slam"/"barrage" no frame em que o golpe é executado (p/ som)

        # ---- Estado puramente visual (não afeta a lógica de combate) ----
        self.sprites = boss_sprites.get_boss_sprites()   # None -> desenho retangular antigo
        self.anim_tick = 0            # contador de frames de jogo, p/ idle/caminhada
        self.strike_kind = None       # "slam"/"barrage": animação de execução em andamento
        self.strike_tick = 0          # frames desde a execução do golpe
        self.phase_flash_timer = 0    # pisca ao entrar na Fase 2
        self.impacts = []             # faíscas onde a rajada bateu: {"x", "y", "t"}

    def update(self, level, player):
        super().update(level, player)
        if not self.alive:
            return

        self.attack_triggered_this_frame = None
        if not self.phase2 and self.health <= self.max_health * settings.BOSS_PHASE2_HEALTH_RATIO:
            self.phase2 = True
            self.phase_flash_timer = settings.BOSS_PHASE2_FLASH_FRAMES

        speed = settings.BOSS_SPEED * (1.4 if self.phase2 else 1.0)

        self.vel_y += settings.GRAVITY
        if self.vel_y > settings.MAX_FALL_SPEED:
            self.vel_y = settings.MAX_FALL_SPEED

        if self.state == Boss.STATE_CHASE:
            self.vel_x = 0
            direction = 1 if player.rect.centerx > self.rect.centerx else -1
            self.facing_right = direction > 0
            distance = abs(player.rect.centerx - self.rect.centerx)
            if distance > settings.BOSS_CHASE_STOP_DISTANCE:
                self.vel_x = speed * direction

            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self._choose_attack()

        elif self.state == Boss.STATE_TELEGRAPH:
            self.vel_x = 0
            self.telegraph_timer -= 1
            if self.telegraph_timer <= 0:
                self.state = Boss.STATE_ATTACK
                if self.attack_type == Boss.ATTACK_SLAM:
                    self._perform_slam(player)
                else:
                    self._perform_barrage(player)

        elif self.state == Boss.STATE_ATTACK:
            self.state = Boss.STATE_RECOVER
            self.recover_timer = 20

        elif self.state == Boss.STATE_RECOVER:
            self.vel_x = 0
            self.recover_timer -= 1
            if self.recover_timer <= 0:
                self.state = Boss.STATE_CHASE
                self.attack_timer = settings.BOSS_ATTACK_COOLDOWN

        level.move_and_collide_enemy(self, self.vel_x, self.vel_y)
        self.rect.x = max(self.arena_left, min(self.rect.x, self.arena_right - self.rect.width))

        # Dano por contato corporal (sempre ativo, exceto durante telegraph)
        if self.state != Boss.STATE_TELEGRAPH:
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

    def _choose_attack(self):
        """Na Fase 1 só existe o slam. Na Fase 2, Vharok alterna
        aleatoriamente entre os dois padrões de ataque."""
        if self.phase2 and random.random() < 0.5:
            self.attack_type = Boss.ATTACK_BARRAGE
            self.telegraph_timer = settings.BOSS_BARRAGE_TELEGRAPH
        else:
            self.attack_type = Boss.ATTACK_SLAM
            self.telegraph_timer = settings.BOSS_SLAM_TELEGRAPH
        self.state = Boss.STATE_TELEGRAPH

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
        super().take_damage(amount)

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
        if self.attack_triggered_this_frame:
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
        if self.state == Boss.STATE_TELEGRAPH:
            if self.attack_type == Boss.ATTACK_SLAM:
                anim, total = "slam_windup", settings.BOSS_SLAM_TELEGRAPH
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

    def _body_tint(self):
        if self.hit_flash_timer > 0:
            return "hit"
        if self.phase_flash_timer > 0 and (self.phase_flash_timer // 4) % 2 == 0:
            return "rage_flash"
        if self.state == Boss.STATE_TELEGRAPH and (self.telegraph_timer // 4) % 2 == 0:
            return "tele_slam" if self.attack_type == Boss.ATTACK_SLAM else "tele_barrage"
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

        if self.sprites:
            self._draw_sprite_boss(surface, camera_x)
            return

        # ---- Reserva: desenho retangular original (sem a spritesheet) ----
        r = self.rect.move(-camera_x, 0)
        color = (255, 255, 255) if self.hit_flash_timer > 0 else self.color
        if self.state == Boss.STATE_TELEGRAPH:
            telegraph_color = (255, 210, 80) if self.attack_type == Boss.ATTACK_SLAM else (200, 100, 230)
            flash = telegraph_color if (self.telegraph_timer // 4) % 2 == 0 else color
            pygame.draw.rect(surface, flash, r, border_radius=6)
        else:
            pygame.draw.rect(surface, color, r, border_radius=6)

        if self.attack_rect:
            ar = self.attack_rect.move(-camera_x, 0)
            pygame.draw.rect(surface, (255, 120, 40), ar, border_radius=4)

        for p in self.projectiles:
            pr = p["rect"].move(-camera_x, 0)
            pygame.draw.ellipse(surface, (200, 100, 230), pr)

    def draw_boss_bar(self, surface):
        """Barra de vida grande, fixa na tela, típica de batalhas de boss."""
        bar_w = int(settings.SCREEN_WIDTH * 0.6)
        bar_h = 22
        bx = (settings.SCREEN_WIDTH - bar_w) // 2
        by = 24
        pygame.draw.rect(surface, settings.COLOR_UI_PANEL, (bx - 4, by - 4, bar_w + 8, bar_h + 8), border_radius=6)
        pygame.draw.rect(surface, settings.COLOR_HP_BG, (bx, by, bar_w, bar_h))
        ratio = max(0, self.health / self.max_health)
        pygame.draw.rect(surface, settings.COLOR_HP_BOSS_FG, (bx, by, int(bar_w * ratio), bar_h))
        pygame.draw.rect(surface, settings.COLOR_UI_BORDER, (bx - 4, by - 4, bar_w + 8, bar_h + 8), width=2, border_radius=6)

        font = pygame.font.Font(None, 22)
        label_text = "VHAROK, REI DO ABISMO" + ("  [FASE 2]" if self.phase2 else "")
        label = font.render(label_text, True, settings.COLOR_TEXT)
        surface.blit(label, (bx, by - 22))
