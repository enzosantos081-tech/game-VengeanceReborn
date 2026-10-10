"""
core/game.py
Responsável pelo funcionamento principal do jogo e pelo Game Loop.
Orquestra: estados (core/states.py), input (core/input.py), o jogador,
a fase atual (world/level.py), a loja (systems/shop.py), o respawn
(systems/respawn.py), o áudio (systems/audio.py) e as telas (screens/*).
É o único módulo que "conhece" todos os outros - os demais não dependem
de Game diretamente, o que mantém o acoplamento baixo.
"""

import random
import sys
import pygame

from config import settings
from core.states import StateMachine
from core.input import InputManager
from core.debug_overlay import DebugOverlay
from core import save

from player.player import Player
from world.level import build_main_level, build_boss_level
from systems.combat import resolve_player_attack
from systems.respawn import RespawnSystem
from systems.shop import Shop
from systems.particles import ParticleSystem
from systems.audio import SoundManager

from screens.menu import MenuScreen
from screens.hud import HUD
from screens.game_over import GameOverScreen
from screens.victory import VictoryScreen
from screens.story import StoryPopup
from screens.pause import PauseMenu


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(settings.GAME_TITLE)
        self.screen = pygame.display.set_mode(
        (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
        pygame.SCALED | pygame.FULLSCREEN,)
        self.world_surface = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.frame_dt_ms = 1000.0 / settings.FPS

        self.states = StateMachine(settings.STATE_MENU)
        self.input = InputManager()
        self.audio = SoundManager()

        self.menu_screen = MenuScreen()
        self.hud = HUD()
        self.game_over_screen = GameOverScreen()
        self.victory_screen = VictoryScreen()
        self.shop = Shop()
        self.pause_menu = PauseMenu()
        self.particles = ParticleSystem()
        self.story = StoryPopup()

        self.level = None
        self.player = None
        self.respawn_system = None
        self.camera_x = 0
        self._prev_on_ground = False
        self._prev_health = None
        self._victory_sound_played = False

        self.shake_timer = 0
        self.shake_magnitude = 0.0

        # ---------- Modo DEBUG (F3) ----------
        # Ferramenta de desenvolvimento: grade + hitboxes + painel de
        # coordenadas. Não afeta nenhuma mecânica - só desenha por cima
        # quando ligado (ver core/debug_overlay.py).
        self.debug_mode = False
        self.debug_overlay = DebugOverlay()

        self.running = True

    # ---------- Screen shake ----------
    def trigger_shake(self, magnitude, frames):
        self.shake_magnitude = max(self.shake_magnitude, magnitude)
        self.shake_timer = max(self.shake_timer, frames)

    # ---------- Loja ----------
    def _near_shop(self):
        """True se o jogador pode abrir a loja agora: perto da zona fixa
        da Região 1 OU perto de qualquer checkpoint já ativado."""
        if self.level.shop_zone and self.level.shop_zone.player_in_range(self.player):
            return True
        return any(cp.player_in_shop_range(self.player) for cp in self.level.checkpoints)

    def _update_shake(self):
        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.shake_magnitude *= settings.SHAKE_DECAY
        else:
            self.shake_magnitude = 0.0

    # ---------- Ciclo de vida de uma partida ----------
    def start_new_game(self):
        self.level = build_main_level()
        self.player = Player(*self.level.player_start)
        save.load_game(self.player.stats)  # continua progressão salva, se existir
        self.player.health = self.player.stats.max_health
        self.respawn_system = RespawnSystem(*self.level.core_pos)
        self.camera_x = 0
        self.particles = ParticleSystem()
        self.story = StoryPopup()
        self._prev_on_ground = False
        self._prev_health = self.player.health
        self._victory_sound_played = False
        self.shake_timer = 0
        self.shake_magnitude = 0.0
        self.states.change(settings.STATE_PLAYING)

    def enter_boss_level(self):
        self.level = build_boss_level()
        self.player.rect.topleft = self.level.player_start
        self.player.vel_x = 0
        self.player.vel_y = 0
        self.player.standing_platform = None
        self.respawn_system.set_core(*self.level.core_pos)
        self.camera_x = 0
        self.particles = ParticleSystem()
        self._prev_on_ground = False

    def restart_attempt(self):
        """Usado pelo menu de pausa: volta ao último ponto do Núcleo/
        checkpoint imediatamente, sem passar pela tela de derrota."""
        self.respawn_system.respawn(self.player)
        self._prev_health = self.player.health
        self.states.change(settings.STATE_PLAYING)

    def return_to_menu(self):
        save.delete_save()
        self.states.change(settings.STATE_MENU)
        self.level = None
        self.player = None

    # ---------- Loop principal ----------
    def run(self):
        while self.running:
            self._process_events()
            self._update()
            self._draw()
            self.input.end_frame()
            self.clock.tick(settings.FPS)
            self.frame_dt_ms = self.clock.get_time()
        pygame.quit()
        sys.exit()

    def _process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            else:
                self.input.handle_event(event)

    # ---------- Update ----------
    def _update(self):
        state = self.states.current
        self._update_shake()

        # F3 liga/desliga o modo DEBUG a qualquer momento, em qualquer
        # tela - é uma ferramenta de desenvolvimento, não uma mecânica
        # do jogo, então fica fora do dispatch por estado abaixo.
        if self.input.debug_toggle_pressed():
            self.debug_mode = not self.debug_mode

        if state == settings.STATE_MENU:
            self.menu_screen.update()
            if self.input.confirm_pressed():
                self.audio.play("menu_select")
                self.start_new_game()

        elif state == settings.STATE_PLAYING:
            self._update_playing()

        elif state == settings.STATE_SHOP:
            self._update_shop()

        elif state == settings.STATE_PAUSED:
            self._update_pause()

        elif state == settings.STATE_GAME_OVER:
            self.game_over_screen.update()
            if self.game_over_screen.ready_to_continue() and self.input.confirm_pressed():
                self.respawn_system.respawn(self.player)
                self._prev_health = self.player.health
                self.states.change(settings.STATE_PLAYING)

        elif state == settings.STATE_VICTORY:
            if not self._victory_sound_played:
                self.audio.play("victory")
                self._victory_sound_played = True
            if self.input.confirm_pressed():
                save.delete_save()
                self.return_to_menu()

    def _update_playing(self):
        if self.input.pause_pressed():
            self.pause_menu.reset_selection()
            self.states.change(settings.STATE_PAUSED)
            return

        self._prev_health = self.player.health
        self.player.handle_input(self.input, self.camera_x)
        # Plataformas móveis avançam antes do jogador, para que o "colamento"
        # em cima delas (world/level.py -> move_and_collide) use o
        # deslocamento deste mesmo frame (ver comentário lá).
        self.level.update_platforms()
        self.player.update(self.level, self.frame_dt_ms)

        if self.player.just_jumped:
            self.audio.play("jump")
        if self.player.just_attacked:
            self.audio.play("attack")
        if self.player.just_dashed:
            self.audio.play("dash")
        if self.player.dashing:
            self.particles.emit_dash_trail(self.player.rect.centerx, self.player.rect.centery)

        # Poeira ao pousar (transição queda -> chão)
        if self.player.on_ground and not self._prev_on_ground:
            self.particles.emit_dust(self.player.rect.centerx, self.player.rect.bottom)
        self._prev_on_ground = self.player.on_ground

        # Dano sofrido nesta rodada (comparando vida antes/depois do update)
        if self.player.alive and self.player.health < self._prev_health:
            self.audio.play("damage")
            self.trigger_shake(4, 10)

        coins_collected = self.level.update(self.player, self.particles)
        if coins_collected:
            self.audio.play("coin")

        all_targets = self.level.living_enemies() + ([self.level.boss] if self.level.boss and self.level.boss.alive else [])
        hit_ids, coins_awarded = resolve_player_attack(
            self.player, all_targets, self.particles,
        )
        if hit_ids:
            self.audio.play("hit")
        if coins_awarded:
            self.audio.play("coin")

        # Ataques do Boss (para som e screen shake)
        if self.level.boss and self.level.boss.attack_triggered_this_frame:
            if self.level.boss.attack_triggered_this_frame == "slam":
                self.audio.play("boss_slam")
                self.trigger_shake(8, 16)
            elif self.level.boss.attack_triggered_this_frame == "melee":
                self.audio.play("boss_slam")   # golpe curto: mesmo som do slam, tremor menor
                self.trigger_shake(4, 8)
            else:
                self.audio.play("boss_barrage")
                self.trigger_shake(3, 8)

        self.particles.update()
        self.story.update()

        # Checkpoints
        for cp in self.level.checkpoints:
            if cp.try_activate(self.player):
                self.respawn_system.set_core(*cp.respawn_point())
                self.particles.emit_checkpoint(cp.rect.centerx, cp.rect.centery)
                self.audio.play("checkpoint")

        # História apresentada durante o jogo
        story_text = self.level.check_story_triggers(self.player.rect.centerx, self.player.rect.centery)
        if story_text:
            self.story.show(story_text)

        # Loja: zona fixa da Região 1 OU qualquer checkpoint já ativado
        # (assim o jogador não precisa voltar à área inicial toda vez
        # que quiser gastar moedas em melhorias).
        if self._near_shop():
            if self.input.interact_pressed():
                self.audio.play("menu_select")
                self.states.change(settings.STATE_SHOP)

        # Transição para a fase do Boss
        if (not self.level.is_boss_level and self.level.boss_trigger
                and self.player.rect.colliderect(self.level.boss_trigger)):
            self.enter_boss_level()

        # Morte
        if not self.player.alive:
            self.particles.emit_death(self.player.rect.centerx, self.player.rect.centery)
            self.audio.play("death")
            self.trigger_shake(6, 14)
            save.save_game(self.player.stats)
            self.game_over_screen.reset()
            self.states.change(settings.STATE_GAME_OVER)
            return

        # Vitória (Boss derrotado)
        if self.level.boss and not self.level.boss.alive:
            save.save_game(self.player.stats)
            self._victory_sound_played = False
            self.states.change(settings.STATE_VICTORY)
            return

        self._update_camera()

    def _update_shop(self):
        if self.input.pause_pressed():
            self.states.change(settings.STATE_PLAYING)
            return

        if self.input.left_pressed():
            self.shop.switch_tab(-1)
            self.audio.play("menu_move")
        elif self.input.right_pressed():
            self.shop.switch_tab(1)
            self.audio.play("menu_move")

        if self.input.down_pressed():
            self.shop.move_selection(1)
            self.audio.play("menu_move")
        elif self.input.up_pressed():
            self.shop.move_selection(-1)
            self.audio.play("menu_move")

        # F aprimora a espada selecionada; ENTER/E compra ou equipa.
        if self.input.is_pressed(pygame.K_f):
            success = self.shop.upgrade_selected(self.player)
            self.audio.play("purchase" if success else "denied")
            if success:
                save.save_game(self.player.stats)
        elif self.input.interact_pressed() or self.input.confirm_pressed():
            success = self.shop.purchase_selected(self.player)
            self.audio.play("purchase" if success else "denied")
            if success:
                save.save_game(self.player.stats)

        if self.input.mouse_pressed(1):
            result = self.hud.handle_shop_click(pygame.mouse.get_pos(), self.player, self.shop)
            if result is not None:
                self.audio.play("purchase" if result else "denied")
                if result:
                    save.save_game(self.player.stats)

    def _update_pause(self):
        if self.input.pause_pressed():
            self.states.change(settings.STATE_PLAYING)
            return
        if self.input.down_pressed():
            self.pause_menu.move_selection(1)
            self.audio.play("menu_move")
        if self.input.up_pressed():
            self.pause_menu.move_selection(-1)
            self.audio.play("menu_move")
        if self.input.confirm_pressed() or self.input.interact_pressed():
            option = self.pause_menu.selected_option()
            self.audio.play("menu_select")
            if option == "Continuar":
                self.states.change(settings.STATE_PLAYING)
            elif option == "Reiniciar tentativa":
                self.restart_attempt()
            elif option == "Sair para o menu":
                save.save_game(self.player.stats)
                self.return_to_menu()

    def _update_camera(self):
        target = self.player.rect.centerx - settings.SCREEN_WIDTH // 2
        max_camera = max(0, self.level.width - settings.SCREEN_WIDTH)
        self.camera_x = max(0, min(target, max_camera))

    # ---------- Desenho ----------
    def _draw(self):
        state = self.states.current

        if state == settings.STATE_MENU:
            self.menu_screen.draw(self.screen)

        elif state in (settings.STATE_PLAYING, settings.STATE_PAUSED, settings.STATE_SHOP):
            surf = self.world_surface
            self.level.draw(surf, self.camera_x)
            self.player.draw(surf, self.camera_x)
            self.particles.draw(surf, self.camera_x)

            if self.debug_mode:
                self.debug_overlay.draw_world(surf, self.camera_x, self.level, self.player)

            offset_x, offset_y = 0, 0
            if self.shake_magnitude >= 0.5:
                m = int(self.shake_magnitude)
                offset_x = random.randint(-m, m)
                offset_y = random.randint(-m, m)
            self.screen.fill((0, 0, 0))
            self.screen.blit(surf, (offset_x, offset_y))

            self.hud.draw(self.screen, self.player)
            self.story.draw(self.screen)

            if self.level.boss and self.level.boss.alive:
                self.level.boss.draw_boss_bar(self.screen)

            if self._near_shop() and state == settings.STATE_PLAYING:
                self.hud.draw_prompt(self.screen, "Pressione E para abrir a loja")

            if state == settings.STATE_PAUSED:
                self.pause_menu.draw(self.screen)
            elif state == settings.STATE_SHOP:
                self.hud.draw_shop(self.screen, self.player, self.shop)

            if self.debug_mode:
                self.debug_overlay.draw_panel(
                    self.screen,
                    self.clock.get_fps(),
                    self.player,
                    self.camera_x,
                    pygame.mouse.get_pos(),
                    shake_offset=(offset_x, offset_y),
                )

        elif state == settings.STATE_GAME_OVER:
            self.game_over_screen.draw(self.screen, self.player)

        elif state == settings.STATE_VICTORY:
            self.victory_screen.draw(self.screen, self.player)

        pygame.display.flip()
