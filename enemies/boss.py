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
"""

import random
import pygame
from config import settings
from enemies.enemy import Enemy


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

    def update(self, level, player):
        super().update(level, player)
        if not self.alive:
            return

        self.attack_triggered_this_frame = None
        if not self.phase2 and self.health <= self.max_health * settings.BOSS_PHASE2_HEALTH_RATIO:
            self.phase2 = True

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
                continue
            if p["rect"].colliderect(player.rect) and player.alive:
                direction = 1 if p["vx"] > 0 else -1
                player.take_damage(self.damage, knockback_dir=direction)
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
