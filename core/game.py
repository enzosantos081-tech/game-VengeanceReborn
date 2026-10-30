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
from core import save, run_state

from player.player import Player
from world.level import build_main_level, build_boss_level
from systems.combat import resolve_player_attack
from systems.respawn import RespawnSystem
from systems.shop import Shop
from systems.particles import ParticleSystem
from systems.audio import SoundManager, MusicManager
from systems.audio_events import AudioDirector

from screens.menu import MenuScreen, get_font, COL_MOON_DIM
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
        self.music = MusicManager()
        self.sfx = AudioDirector(self.audio)   # detecta eventos do jogo e toca os sons (systems/audio_events.py)

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
        self._victory_timer = 0

        self.shake_timer = 0
        self.shake_magnitude = 0.0

        # ---------- Salvamento (core/save.py + core/run_state.py) ----------
        self.play_frames = 0          # tempo jogado na partida atual (em frames)
        self._autosave_frames = 0     # frames desde o último salvamento
        self._save_notice = 0         # frames restantes do aviso "Progresso salvo"
        self._save_notice_font = get_font(22)
        self.refresh_saved_run()      # decide se o menu mostra "Continuar"

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
    def _begin_session(self, level, player, core_pos, play_frames=0):
        """Instala uma partida (nova ou carregada) e entra em STATE_PLAYING."""
        self.level = level
        self.player = player
        self.respawn_system = RespawnSystem(*core_pos)
        self.particles = ParticleSystem()
        self.story = StoryPopup()
        self._prev_on_ground = False
        self._prev_health = self.player.health
        self._victory_sound_played = False
        self._victory_timer = 0
        self.sfx.reset()
        self.shake_timer = 0
        self.shake_magnitude = 0.0
        self.play_frames = play_frames
        self._autosave_frames = 0
        self.camera_x = 0
        self._update_camera()
        self.music.play("boss" if level.is_boss_level else "level")
        self.states.change(settings.STATE_PLAYING)

    def start_new_game(self):
        """Nova partida do zero. Se já existe uma partida salva, o menu só
        chega aqui depois de o jogador confirmar a substituição; o save novo
        é gravado já em seguida, trocando o antigo de uma vez."""
        level = build_main_level()
        player = Player(*level.player_start)
        save.load_game(player.stats)  # só saves antigos (sem partida): mantém a progressão
        player.health = player.stats.max_health
        self._begin_session(level, player, level.core_pos)
        self.save_run("new_game")

    def continue_game(self):
        """Retoma a partida salva exatamente de onde parou. Devolve False (e
        avisa no menu) se o salvamento não puder ser carregado."""
        data = save.read_save()
        run = data["run"] if data else None
        if run is None:
            self.menu_screen.show_message("Nenhuma partida salva para continuar.")
            self.refresh_saved_run()
            return False
        try:
            level, player, core, frames = run_state.restore_run(run, data["stats"])
        except ValueError as exc:
            print(f"[save] não foi possível carregar a partida: {exc}", file=sys.stderr)
            self.menu_screen.show_message("Não foi possível carregar a partida salva.")
            return False
        self._begin_session(level, player, core, play_frames=frames)
        return True

    # ---------- Salvamento ----------
    _SAVE_NOTICE_REASONS = ("autosave", "checkpoint", "shop", "boss")

    def refresh_saved_run(self):
        """Relê o arquivo e informa ao menu se há partida salva utilizável."""
        data = save.read_save()
        summary = run_state.summarize(data["run"], data["stats"]) if data and data["run"] else None
        self.menu_screen.set_saved_run(summary)

    def save_run(self, reason=""):
        """Grava progressão + estado da partida. Nunca levanta: se falhar, o
        jogo segue e o último salvamento válido continua intacto."""
        if self.level is None or self.player is None:
            return False
        try:
            run = run_state.capture_run(self)
            ok = save.save_game(self.player.stats, run)
        except Exception as exc:  # o salvamento jamais pode derrubar o jogo
            print(f"[save] falha ao salvar ({reason}): {exc}", file=sys.stderr)
            return False
        self._autosave_frames = 0
        if ok and reason in self._SAVE_NOTICE_REASONS:
            self._save_notice = settings.SAVE_NOTICE_FRAMES
        elif not ok:
            print(f"[save] não foi possível gravar o arquivo ({reason})", file=sys.stderr)
        return ok

    def _tick_autosave(self):
        """Salvamento periódico. Espera um momento com Kael no chão (até uma
        tolerância) para não gravar no meio de um salto/dash."""
        self.play_frames += 1
        self._autosave_frames += 1
        if self._autosave_frames < settings.AUTOSAVE_INTERVAL_FRAMES:
            return
        grounded = self.player.on_ground and not self.player.dashing
        waited = self._autosave_frames - settings.AUTOSAVE_INTERVAL_FRAMES
        if self.player.alive and (grounded or waited >= settings.AUTOSAVE_AIR_GRACE_FRAMES):
            self.save_run("autosave")

    def _save_on_exit(self):
        """Fechar a janela salva a partida em andamento (menos na vitória,
        que encerra a campanha e já limpou o save)."""
        if self.states.current in (settings.STATE_PLAYING, settings.STATE_PAUSED,
                                   settings.STATE_SHOP, settings.STATE_GAME_OVER):
            self.save_run("quit")

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
        self.audio.play("boss_enter")
        self.music.play("boss")
        self.save_run("boss")

    def restart_attempt(self):
        """Usado pelo menu de pausa: volta ao último ponto do Núcleo/
        checkpoint imediatamente, sem passar pela tela de derrota."""
        self.respawn_system.respawn(self.player)
        self._reset_boss_attacks()
        self._prev_health = self.player.health
        self.audio.play("respawn")
        self.states.change(settings.STATE_PLAYING)
        self.save_run("restart")

    def _reset_boss_attacks(self):
        """Kael renasceu: projéteis e golpes do Boss em andamento não continuam."""
        if self.level.boss and self.level.boss.alive:
            self.level.boss.reset_combat_state()

    def return_to_menu(self):
        """Volta ao menu SEM apagar o salvamento (quem quiser encerrar a
        campanha, como a vitória, chama save.delete_save() antes)."""
        self.music.stop()
        self.states.change(settings.STATE_MENU)
        self.level = None
        self.player = None
        self.refresh_saved_run()

    # ---------- Loop principal ----------
    def run(self):
        while self.running:
            self._process_events()
            self._update()
            self._draw()
            self.input.end_frame()
            self.clock.tick(settings.FPS)
            self.frame_dt_ms = self.clock.get_time()
        self._save_on_exit()
        pygame.quit()
        sys.exit()

    def _process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_F11, pygame.K_l):
                pygame.display.toggle_fullscreen()
            else:
                self.input.handle_event(event)

    # ---------- Update ----------
    def _update(self):
        state = self.states.current
        self._update_shake()
        if self._save_notice > 0:
            self._save_notice -= 1

        # F3 liga/desliga o modo DEBUG a qualquer momento, em qualquer
        # tela - é uma ferramenta de desenvolvimento, não uma mecânica
        # do jogo, então fica fora do dispatch por estado abaixo.
        if self.input.debug_toggle_pressed():
            self.debug_mode = not self.debug_mode

        if state == settings.STATE_MENU:
            self.menu_screen.update()
            self._update_menu()

        elif state == settings.STATE_PLAYING:
            self._update_playing()

        elif state == settings.STATE_SHOP:
            self._update_shop()

        elif state == settings.STATE_PAUSED:
            self._update_pause()

        elif state == settings.STATE_GAME_OVER:
            self.game_over_screen.update()
            # Mantém a estalactite especial do puzzle atualizando durante a tela
            # de morte. Sem isso, a simulação pausa antes de a pedra terminar a queda.
            if self.level is not None:
                self.level.obstacles.update(
                    self.player,
                    ground_y=settings.SCREEN_HEIGHT - 64,
                    solids=self.level.platforms.rects(),
                )
            if self.game_over_screen.ready_to_continue() and self.input.confirm_pressed():
                self.respawn_system.respawn(self.player)
                self._reset_boss_attacks()
                self._prev_health = self.player.health
                self.audio.play("respawn")
                self.states.change(settings.STATE_PLAYING)
                self.save_run("respawn")

        elif state == settings.STATE_VICTORY:
            if not self._victory_sound_played:
                # A queda de Vharok (boss_death) toca primeiro; a fanfarra entra ~2,5 s depois.
                self._victory_timer += 1
                if self._victory_timer >= 150:
                    self.audio.play("victory")
                    self._victory_sound_played = True
            if self.input.confirm_pressed():
                save.delete_save()
                self.audio.stop_all()
                self.return_to_menu()

    def _update_menu(self):
        menu, inp = self.menu_screen, self.input
        if menu.confirming_new:
            # Confirmação antes de substituir uma partida salva.
            if inp.left_pressed() or inp.right_pressed() or inp.up_pressed() or inp.down_pressed():
                menu.toggle_confirm()
                self.audio.play("menu_move")
            if inp.pause_pressed():
                menu.cancel_confirm()
            elif inp.confirm_pressed():
                if menu.confirm_is_replace():
                    self.audio.play("game_start")
                    self.start_new_game()
                else:
                    self.audio.play("menu_select")
                    menu.cancel_confirm()
        elif menu.has_saved_run():
            if inp.down_pressed():
                menu.move_selection(1)
                self.audio.play("menu_move")
            if inp.up_pressed():
                menu.move_selection(-1)
                self.audio.play("menu_move")
            if inp.confirm_pressed():
                if menu.selected_option() == "Continuar":
                    self.audio.play("game_start")
                    self.continue_game()
                else:
                    self.audio.play("menu_select")
                    menu.begin_confirm_new()
        elif inp.confirm_pressed():
            self.audio.play("game_start")
            self.start_new_game()

    def _update_playing(self):
        if self.input.pause_pressed():
            self.pause_menu.reset_selection()
            self.audio.play("pause_open")
            self.states.change(settings.STATE_PAUSED)
            self.save_run("pause")
            return

        self._prev_health = self.player.health
        self.sfx.begin_frame(self.player)
        self.player.handle_input(self.input, self.camera_x)
        if self.player.just_dashed:
            self.audio.play("dash")
        # Plataformas móveis avançam antes do jogador, para que o "colamento"
        # em cima delas (world/level.py -> move_and_collide) use o
        # deslocamento deste mesmo frame (ver comentário lá).
        self.level.update_platforms()
        self.player.update(self.level, self.frame_dt_ms)

        # Sons de pulo / pulo duplo / ataque (por espada) / dash / pouso / coração:
        # tocados pelo AudioDirector (self.sfx.update, mais abaixo).
        if self.player.dashing:
            self.particles.emit_dash_trail(self.player.rect.centerx, self.player.rect.centery)

        # Poeira ao pousar (transição queda -> chão)
        if self.player.on_ground and not self._prev_on_ground:
            self.particles.emit_dust(self.player.rect.centerx, self.player.rect.bottom)
        self._prev_on_ground = self.player.on_ground

        coins_collected = self.level.update(self.player, self.particles)

        # Dano sofrido nesta rodada (comparando vida antes/depois dos updates).
        # CORREÇÃO: esta checagem ficava ANTES de self.level.update(), que é
        # onde inimigos, espinhos, estalactites e projéteis causam o dano, então
        # o som de dano (e o tremor de tela) nunca disparavam. Agora disparam.
        if self.player.alive and self.player.health < self._prev_health:
            self.audio.play("damage")
            self.sfx.player_damaged(self.level, self.player)
            self.trigger_shake(4, 10)

        if coins_collected:
            self.sfx.coin()

        all_targets = self.level.living_enemies() + ([self.level.boss] if self.level.boss and self.level.boss.alive else [])
        boss = self.level.boss
        boss_hp_before = boss.health if boss else 0
        hit_ids, coins_awarded = resolve_player_attack(
            self.player, all_targets, self.particles,
        )
        if hit_ids:
            boss_hit = bool(boss) and boss.id in hit_ids
            if len(hit_ids) > (1 if boss_hit else 0):
                self.audio.play("hit")
            if boss_hit:
                # Com hiper-armadura (aviso do golpe) o boss não leva dano: soa aço contra aço.
                self.audio.play("hit_boss" if boss.health < boss_hp_before else "boss_armor")
        if coins_awarded:
            self.sfx.coin()

        # Ataques do Boss (para som e screen shake)
        if self.level.boss and self.level.boss.attack_triggered_this_frame:
            if self.level.boss.attack_triggered_this_frame == "slam":
                self.audio.play("boss_slam")
                self.trigger_shake(8, 16)
            elif self.level.boss.attack_triggered_this_frame == "melee":
                self.audio.play("boss_melee")   # golpe curto: som próprio, tremor menor
                self.trigger_shake(4, 8)
            else:
                self.audio.play("boss_barrage")
                self.trigger_shake(3, 8)

        self.sfx.update(self.level, self.player)   # eventos de Kael, inimigos, boss e mundo
        self.particles.update()
        self.story.update()

        # Checkpoints
        checkpoint_activated = False
        for cp in self.level.checkpoints:
            if cp.try_activate(self.player):
                self.respawn_system.set_core(*cp.respawn_point())
                self.particles.emit_checkpoint(cp.rect.centerx, cp.rect.centery)
                self.audio.play("checkpoint")
                checkpoint_activated = True
        if checkpoint_activated and self.player.alive:
            self.save_run("checkpoint")

        # História apresentada durante o jogo
        story_text = self.level.check_story_triggers(self.player.rect.centerx, self.player.rect.centery)
        if story_text:
            self.story.show(story_text)
            self.audio.play("story")

        # Loja: zona fixa da Região 1 OU qualquer checkpoint já ativado
        # (assim o jogador não precisa voltar à área inicial toda vez
        # que quiser gastar moedas em melhorias).
        if self._near_shop():
            if self.input.interact_pressed():
                self.audio.play("shop_open")
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
            self.save_run("death")
            self.game_over_screen.reset()
            self.states.change(settings.STATE_GAME_OVER)
            return

        # Vitória (Boss derrotado)
        if self.level.boss and not self.level.boss.alive:
            save.delete_save()   # a campanha acabou: não há mais o que continuar
            self._victory_sound_played = False
            self._victory_timer = 0
            self.music.stop()
            self.audio.play("boss_death")
            self.states.change(settings.STATE_VICTORY)
            return

        self._tick_autosave()
        self._update_camera()

    def _update_shop(self):
        if self.input.pause_pressed():
            self.audio.play("shop_close")
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
            before = self.sfx.shop_snapshot(self.player)
            success = self.shop.upgrade_selected(self.player)
            self.audio.play(self.sfx.shop_result(before, self.sfx.shop_snapshot(self.player), success))
            if success:
                self.save_run("shop")
        elif self.input.interact_pressed() or self.input.confirm_pressed():
            before = self.sfx.shop_snapshot(self.player)
            success = self.shop.purchase_selected(self.player)
            self.audio.play(self.sfx.shop_result(before, self.sfx.shop_snapshot(self.player), success))
            if success:
                self.save_run("shop")

        if self.input.mouse_pressed(1):
            before = self.sfx.shop_snapshot(self.player)
            nav_before = (self.shop.tab_index, self.shop.selected_index)
            result = self.hud.handle_shop_click(pygame.mouse.get_pos(), self.player, self.shop)
            if result is not None:
                self.audio.play(self.sfx.shop_result(before, self.sfx.shop_snapshot(self.player), result))
                if result:
                    self.save_run("shop")
            elif (self.shop.tab_index, self.shop.selected_index) != nav_before:
                self.audio.play("menu_move")   # clicou numa aba ou num item

    def _update_pause(self):
        if self.input.pause_pressed():
            self.audio.play("pause_close")
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
            self.audio.play("pause_close" if option == "Continuar" else "menu_select")
            if option == "Continuar":
                self.states.change(settings.STATE_PLAYING)
            elif option == "Reiniciar tentativa":
                self.restart_attempt()
            elif option == "Sair para o menu":
                self.save_run("exit")
                self.return_to_menu()

    def _update_camera(self):
        target = self.player.rect.centerx - settings.SCREEN_WIDTH // 2
        max_camera = max(0, self.level.width - settings.SCREEN_WIDTH)
        self.camera_x = max(0, min(target, max_camera))

    # ---------- Desenho ----------
    def _draw_save_notice(self):
        """Aviso discreto no canto inferior direito após um salvamento."""
        if self._save_notice <= 0:
            return
        text = self._save_notice_font.render("Progresso salvo", True, COL_MOON_DIM)
        text.set_alpha(min(255, self._save_notice * 6))
        self.screen.blit(text, text.get_rect(
            bottomright=(settings.SCREEN_WIDTH - 20, settings.SCREEN_HEIGHT - 16)))

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

            self.hud.draw(self.screen, self.player, self.level)
            self.story.draw(self.screen)
            self._draw_save_notice()

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
