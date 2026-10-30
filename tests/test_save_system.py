"""
tests/test_save_system.py
Testes do sistema de salvamento e continuação (core/save.py, core/run_state.py
e a integração em core/game.py / screens/menu.py).

Rodam o jogo de verdade, sem janela nem som (drivers "dummy" do SDL):

    python -m unittest tests.test_save_system -v

Cada teste usa uma pasta de save temporária (VENGEANCE_SAVE_DIR), então nunca
toca no seu savegame real.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402
from config import settings  # noqa: E402
from core import save, run_state  # noqa: E402
from core.game import Game  # noqa: E402
from world.level import build_main_level  # noqa: E402
import screens.menu as menu_module  # noqa: E402


def _fresh_game():
    # O cache de fontes do menu é global do módulo; ao reabrir o jogo no MESMO
    # processo (só nos testes) ele precisa ser limpo, pois pygame.quit() invalida as fontes.
    menu_module._font_cache.clear()
    return Game()


class SaveTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vr_save_")
        self._old_env = os.environ.get("VENGEANCE_SAVE_DIR")
        os.environ["VENGEANCE_SAVE_DIR"] = self.tmp
        self.game = _fresh_game()

    def tearDown(self):
        pygame.quit()
        if self._old_env is None:
            os.environ.pop("VENGEANCE_SAVE_DIR", None)
        else:
            os.environ["VENGEANCE_SAVE_DIR"] = self._old_env
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------- ajudantes ----------
    def new_game(self, g=None):
        g = g or self.game
        g.start_new_game()
        return g

    def frames(self, n, keys=(), g=None):
        g = g or self.game
        for k in keys:
            g.input._held.add(k)
        for _ in range(n):
            g._update()
            g.input.end_frame()
            if g.states.current != settings.STATE_PLAYING:
                break
        for k in keys:
            g.input._held.discard(k)

    def press(self, *keys, g=None):
        g = g or self.game
        for k in keys:
            g.input._pressed_this_frame.add(k)
        g._update()
        g.input.end_frame()

    def reopen(self, save_on_exit=True):
        """Simula fechar o jogo (salvando como o QUIT faz) e abrir de novo.
        save_on_exit=False: o teste já preparou o arquivo e não quer que o
        fechamento o sobrescreva."""
        if save_on_exit:
            self.game._save_on_exit()
        pygame.quit()
        self.game = _fresh_game()
        return self.game

    def read_raw(self):
        with open(save.save_path(), encoding="utf-8") as f:
            return json.load(f)

    def read_bytes(self, path=None):
        with open(path or save.save_path(), "rb") as f:
            return f.read()


class TestFluxoCompleto(SaveTestCase):
    def test_01_a_03_nova_partida_fechar_continuar_posicao(self):
        g = self.new_game()
        self.frames(240, keys=[pygame.K_d])           # anda para a direita
        pos = g.player.rect.topleft
        self.assertGreater(pos[0], g.level.player_start[0] + 100)
        g = self.reopen()
        self.assertTrue(g.menu_screen.has_saved_run())
        self.assertEqual(g.menu_screen.selected_option(), "Continuar")
        self.press(pygame.K_RETURN)                    # seleciona "Continuar"
        self.assertEqual(g.states.current, settings.STATE_PLAYING)
        self.assertEqual(g.player.rect.topleft, pos)   # não voltou ao início
        self.assertNotEqual(g.player.rect.topleft, g.level.player_start)

    def test_04_moedas_melhorias_e_habilidades(self):
        g = self.new_game()
        st = g.player.stats
        st.coins = 500
        self.assertTrue(st.upgrade_health())
        self.assertTrue(st.upgrade_double_jump())
        self.assertTrue(st.upgrade_magnet())
        self.assertTrue(st.buy_sword("survivor"))
        coins, hp_max = st.coins, st.max_health
        g.save_run("shop")
        g = self.reopen()
        self.press(pygame.K_RETURN)
        st = g.player.stats
        self.assertEqual((st.coins, st.max_health), (coins, hp_max))
        self.assertEqual((st.health_level, st.double_jump_level, st.magnet_level), (1, 1, 1))
        self.assertIn("survivor", st.swords_owned)
        self.assertEqual(st.equipped_sword_id, "survivor")

    def test_05_inimigos_derrotados_e_itens_coletados(self):
        g = self.new_game()
        lv = g.level
        killed = [0, 3, 7]
        for i in killed:
            lv.enemies[i].take_damage(10 ** 6)
        picked = [0, 1, 40]
        for i in picked:
            c = lv.coins.coins[i]
            g.player.rect.center = c.rect.center
            lv.coins.update(g.player)
        wounded = lv.enemies[5]
        wounded.health = max(1, wounded.max_health - 1)
        timer = lv.enemies[3].respawn_timer
        coins_now = g.player.stats.coins
        g.save_run("test")
        g = self.reopen()
        self.press(pygame.K_RETURN)
        lv2 = g.level
        for i in range(len(lv2.enemies)):
            self.assertEqual(lv2.enemies[i].alive, i not in killed, f"inimigo {i}")
        self.assertEqual(lv2.enemies[3].respawn_timer, timer)
        self.assertEqual(lv2.enemies[5].health, wounded.health)
        for i in range(len(lv2.coins.coins)):
            self.assertEqual(lv2.coins.coins[i].collected, i in picked, f"moeda {i}")
        self.assertEqual(g.player.stats.coins, coins_now)   # moedas não duplicam

    def test_06_07_checkpoints_e_morte_apos_carregar(self):
        g = self.new_game()
        cp0, cp1 = g.level.checkpoints[0], g.level.checkpoints[1]
        g.player.rect.topleft = cp0.respawn_point()
        self.frames(2)
        self.assertTrue(cp0.active)
        core_after_cp0 = (g.respawn_system.core_x, g.respawn_system.core_y)
        self.assertEqual(core_after_cp0, cp0.respawn_point())
        # anda um pouco adiante e fecha o jogo
        g.player.rect.x += 300
        self.frames(30)
        spot = g.player.rect.topleft
        g = self.reopen()
        self.press(pygame.K_RETURN)
        self.assertEqual(g.player.rect.topleft, spot)
        self.assertTrue(g.level.checkpoints[0].active)
        self.assertFalse(g.level.checkpoints[1].active)
        self.assertEqual((g.respawn_system.core_x, g.respawn_system.core_y), core_after_cp0)
        # checkpoint seguinte continua ativável
        g.player.rect.topleft = g.level.checkpoints[1].respawn_point()
        self.frames(2)
        self.assertTrue(g.level.checkpoints[1].active)
        # morre depois de carregar: volta ao checkpoint MAIS RECENTE, não à morte
        g.player.rect.x += 200
        g.player.take_damage(10 ** 6)
        self.frames(1)
        self.assertEqual(g.states.current, settings.STATE_GAME_OVER)
        g.game_over_screen.timer = 10 ** 6
        self.press(pygame.K_RETURN)
        self.assertEqual(g.states.current, settings.STATE_PLAYING)
        self.assertEqual(g.player.rect.topleft, g.level.checkpoints[1].respawn_point())
        self.assertEqual(g.player.health, g.player.stats.max_health)

    def test_08_sem_arquivo_de_save(self):
        self.assertFalse(os.path.exists(save.save_path()))
        self.assertIsNone(save.read_save())
        self.assertFalse(self.game.menu_screen.has_saved_run())
        self.press(pygame.K_RETURN)               # só "Novo jogo": comportamento original
        self.assertEqual(self.game.states.current, settings.STATE_PLAYING)

    def test_10_sair_pelo_menu_de_pausa_mantem_o_progresso(self):
        g = self.new_game()
        self.frames(120, keys=[pygame.K_d])
        spot = g.player.rect.topleft
        g.player.stats.add_coins(50)
        coins = g.player.stats.coins
        self.press(pygame.K_ESCAPE)
        self.assertEqual(g.states.current, settings.STATE_PAUSED)
        g.pause_menu.selected_index = g.pause_menu.OPTIONS.index("Sair para o menu")
        self.press(pygame.K_RETURN)
        self.assertEqual(g.states.current, settings.STATE_MENU)
        self.assertTrue(os.path.exists(save.save_path()))     # não foi apagado
        self.assertTrue(g.menu_screen.has_saved_run())
        self.press(pygame.K_RETURN)                            # Continuar
        self.assertEqual(g.player.rect.topleft, spot)
        self.assertEqual(g.player.stats.coins, coins)

    def test_11_novo_jogo_pede_confirmacao_e_nao_mistura_dados(self):
        g = self.new_game()
        g.player.stats.coins = 777
        g.level.enemies[0].take_damage(10 ** 6)
        g.level.coins.coins[0].collected = True
        g.save_run("test")
        g = self.reopen()
        # Novo jogo -> confirmação, nada é apagado ainda
        self.press(pygame.K_s)
        self.assertEqual(g.menu_screen.selected_option(), "Novo jogo")
        self.press(pygame.K_RETURN)
        self.assertTrue(g.menu_screen.confirming_new)
        self.assertEqual(g.states.current, settings.STATE_MENU)
        self.assertEqual(save.read_save()["stats"]["coins"], 777)
        # Cancelar (padrão) mantém tudo
        self.press(pygame.K_RETURN)
        self.assertFalse(g.menu_screen.confirming_new)
        self.assertEqual(save.read_save()["stats"]["coins"], 777)
        # Confirma a substituição
        self.press(pygame.K_RETURN)               # abre a confirmação de novo
        self.press(pygame.K_d)                    # vai para "Substituir"
        self.press(pygame.K_RETURN)
        self.assertEqual(g.states.current, settings.STATE_PLAYING)
        self.assertEqual(g.player.stats.coins, 0)
        self.assertTrue(g.level.enemies[0].alive)
        self.assertFalse(g.level.coins.coins[0].collected)
        saved = save.read_save()
        self.assertEqual(saved["stats"]["coins"], 0)       # o save antigo foi trocado
        self.assertEqual(saved["run"]["coins"], [])
        self.assertTrue(all(e["a"] == 1 for e in saved["run"]["enemies"]))


class TestMortePausaEEventos(SaveTestCase):
    def test_morte_nao_salva_posicao_da_morte(self):
        g = self.new_game()
        g.player.rect.x += 400
        death_x = g.player.rect.x
        g.player.take_damage(10 ** 6)
        self.frames(1)
        self.assertEqual(g.states.current, settings.STATE_GAME_OVER)
        run = save.read_save()["run"]
        self.assertTrue(run["player"]["dead"])
        self.assertEqual((run["player"]["x"], run["player"]["y"]),
                         (g.respawn_system.core_x, g.respawn_system.core_y))
        self.assertNotEqual(run["player"]["x"], death_x)
        # fecha durante a tela de derrota: continua vivo no Núcleo, vida cheia
        g = self.reopen()
        self.press(pygame.K_RETURN)
        self.assertTrue(g.player.alive)
        self.assertEqual(g.player.health, g.player.stats.max_health)
        self.assertEqual(g.player.rect.topleft, tuple(g.level.core_pos))

    def test_puzzle_da_fenda_persiste_depois_de_morrer_no_buraco(self):
        g = self.new_game()
        st = next(s for s in g.level.obstacles.stalactites if s.trigger_on_death_zone)
        left, right = st.trigger_on_death_zone
        g.player.rect.centerx = (left + right) // 2
        g.player.rect.y = g.level.height + 400          # caiu no buraco
        self.frames(1)                                   # morte
        self.assertEqual(g.states.current, settings.STATE_GAME_OVER)
        for _ in range(400):                             # a pedra cai durante a tela de morte
            g._update()
            g.input.end_frame()
        self.assertEqual(st.state, "landed")
        y = st.y
        g = self.reopen()
        self.press(pygame.K_RETURN)
        st2 = next(s for s in g.level.obstacles.stalactites if s.trigger_on_death_zone)
        self.assertEqual((st2.state, st2.y, st2.triggered_by_death), ("landed", y, True))
        self.assertIsNotNone(st2.platform_rect())        # a ponte continua sólida

    def test_puzzle_salvo_antes_de_a_pedra_reagir_a_morte(self):
        g = self.new_game()
        st = next(s for s in g.level.obstacles.stalactites if s.trigger_on_death_zone)
        g.player.rect.centerx = sum(st.trigger_on_death_zone) // 2
        g.player.take_damage(10 ** 6)                    # morreu, mas a pedra ainda não teve um frame
        self.assertEqual(st.state, "idle")
        g.save_run("death")
        g = self.reopen(save_on_exit=False)
        self.press(pygame.K_RETURN)
        st2 = next(s for s in g.level.obstacles.stalactites if s.trigger_on_death_zone)
        self.assertTrue(st2.triggered_by_death)          # o gatilho não se perdeu
        self.assertNotEqual(st2.state, "idle")
        self.assertTrue(g.player.alive)                   # e Kael está vivo no Núcleo

    def test_plataforma_movel_e_quebradica(self):
        g = self.new_game()
        moving = g.level.platforms.moving_platforms()[0]
        for _ in range(37):
            moving.update()
        crumbling = next(p for p in g.level.platforms.platforms if type(p).__name__ == "CrumblingPlatform")
        crumbling.trigger()
        state = (moving.progress, moving.direction, moving.rect.topleft, crumbling.state)
        g.save_run("test")
        g = self.reopen()
        self.press(pygame.K_RETURN)
        m2 = g.level.platforms.moving_platforms()[0]
        c2 = next(p for p in g.level.platforms.platforms if type(p).__name__ == "CrumblingPlatform")
        self.assertEqual((m2.progress, m2.direction, m2.rect.topleft, c2.state), state)

    def test_fase_do_boss_e_continuacao(self):
        g = self.new_game()
        g.enter_boss_level()                             # também salva
        boss = g.level.boss
        boss.health = boss.max_health // 3
        g.player.stats.coins = 123
        g.save_run("test")
        g = self.reopen()
        self.press(pygame.K_RETURN)
        self.assertTrue(g.level.is_boss_level)
        self.assertEqual(g.level.boss.health, boss.max_health // 3)
        self.assertTrue(g.level.boss.phase2)
        self.assertEqual(g.player.stats.coins, 123)
        self.frames(60)                                  # a luta segue sem erros
        self.assertEqual(g.states.current, settings.STATE_PLAYING)

    def test_vitoria_encerra_a_campanha_e_limpa_o_save(self):
        g = self.new_game()
        g.enter_boss_level()
        g.level.boss.take_damage(10 ** 7)
        self.frames(2)
        self.assertEqual(g.states.current, settings.STATE_VICTORY)
        self.assertIsNone(save.read_save())
        g._save_on_exit()                                # fechar na tela de vitória não ressuscita o save
        self.assertIsNone(save.read_save())

    def test_loja_e_checkpoint_salvam_na_hora(self):
        g = self.new_game()
        g.player.rect.topleft = g.level.checkpoints[0].respawn_point()
        self.frames(2)                                   # ativa o checkpoint 0
        self.assertEqual(save.read_save()["run"]["checkpoints"], [0])
        # compra real na loja (melhoria de vida): o save já reflete a compra
        g.player.stats.coins = 100
        g.states.change(settings.STATE_SHOP)
        with mock.patch.object(g.shop, "purchase_selected",
                               side_effect=lambda p: p.stats.upgrade_health()):
            self.press(pygame.K_RETURN)
        saved = save.read_save()
        self.assertEqual(saved["stats"]["health_level"], 1)
        self.assertEqual(saved["stats"]["coins"], 100 - settings.UPGRADE_HEALTH_COST)

    def test_ida_e_volta_do_estado_e_identica(self):
        """capturar -> restaurar -> capturar de novo precisa dar o MESMO estado."""
        g = self.new_game()
        lv = g.level
        for i in (1, 4, 9, 20):
            lv.enemies[i].take_damage(10 ** 6)
        lv.enemies[6].health -= 1
        for i in (0, 2, 50, 100, 150):
            lv.coins.coins[i].collected = True
        lv.story_triggers[0]["triggered"] = True
        lv.checkpoints[0].active = True
        g.respawn_system.set_core(*lv.checkpoints[0].respawn_point())
        for m in lv.platforms.moving_platforms():
            for _ in range(53):
                m.update()
        next(p for p in lv.platforms.platforms if type(p).__name__ == "CrumblingPlatform").trigger()
        puzzle = next(s for s in lv.obstacles.stalactites if s.trigger_on_death_zone)
        puzzle.state, puzzle.y, puzzle.triggered_by_death = "landed", 690 - puzzle.visual_height, True
        g.player.rect.x += 700
        self.frames(20)
        g.play_frames = 60 * 61
        run1 = run_state.capture_run(g)
        stats = g.player.stats.to_dict()
        level, player, core, frames = run_state.restore_run(json.loads(json.dumps(run1)), stats)
        g2 = self.game
        g2.level, g2.player, g2.play_frames = level, player, frames
        g2.respawn_system.set_core(*core)
        run2 = run_state.capture_run(g2)
        run1.pop("saved_at"); run2.pop("saved_at")
        self.assertEqual(run1, run2)
        self.assertEqual(frames, 60 * 61)


class TestAutosave(SaveTestCase):
    def test_autosave_periodico_sem_gravar_a_cada_quadro(self):
        g = self.new_game()
        with mock.patch.object(save, "save_game", wraps=save.save_game) as spy:
            self.frames(settings.AUTOSAVE_INTERVAL_FRAMES * 2 + 30)
        # 2 intervalos completos => ~2 gravações (nunca uma por quadro)
        self.assertGreaterEqual(spy.call_count, 2)
        self.assertLessEqual(spy.call_count, 4)
        self.assertEqual(g.states.current, settings.STATE_PLAYING)

    def test_falha_ao_gravar_nao_derruba_nem_apaga_o_ultimo_save(self):
        g = self.new_game()
        g.player.stats.coins = 11
        g.save_run("test")
        good = self.read_bytes()
        g.player.stats.coins = 99
        with mock.patch("os.replace", side_effect=OSError("disco cheio")):
            self.assertFalse(g.save_run("test"))
        self.assertEqual(self.read_bytes(), good)
        self.assertFalse(os.path.exists(save.save_path() + ".tmp"))
        self.frames(5)                                   # o jogo segue normalmente

    def test_gravacao_interrompida_no_meio_nao_destroi_o_save(self):
        g = self.new_game()
        g.save_run("test")
        good = self.read_bytes()
        real_fsync = os.fsync
        with mock.patch("os.fsync", side_effect=OSError("queda de energia")):
            self.assertFalse(g.save_run("test"))
        self.assertEqual(self.read_bytes(), good)
        os.fsync = real_fsync


class TestArquivosInvalidos(SaveTestCase):
    def _make_run_save(self):
        g = self.new_game()
        g.player.stats.coins = 321
        g.save_run("test")
        return g

    def test_09_arquivo_corrompido_usa_backup(self):
        g = self._make_run_save()
        g.player.stats.coins = 400
        g.save_run("test")                       # agora existe .bak com 321
        with open(save.save_path(), "w") as f:
            f.write('{"version": 2, "stats": {"coi')   # truncado
        data = save.read_save()
        self.assertEqual(data["stats"]["coins"], 321)
        g = self.reopen(save_on_exit=False)
        self.assertTrue(g.menu_screen.has_saved_run())
        self.press(pygame.K_RETURN)
        self.assertEqual(g.player.stats.coins, 321)

    def test_09_arquivo_e_backup_corrompidos(self):
        self._make_run_save()
        self.game.save_run("test")
        for p in (save.save_path(), save.save_path() + ".bak"):
            with open(p, "wb") as f:
                f.write(b"\x00\xff\xfe lixo")
        self.assertIsNone(save.read_save())
        g = self.reopen(save_on_exit=False)      # não trava
        self.assertFalse(g.menu_screen.has_saved_run())
        self.press(pygame.K_RETURN)              # novo jogo normal
        self.assertEqual(g.states.current, settings.STATE_PLAYING)

    def test_09_formatos_invalidos_nao_travam(self):
        self._make_run_save()
        bad_payloads = [
            "", "null", "[]", "42", '"texto"', "{}",
            '{"version": 99, "stats": {}, "run": null}',
            '{"version": 2, "stats": [], "run": null}',
            '{"version": 2, "stats": {}, "run": "x"}',
            '{"version": "2", "stats": {}, "run": null}',
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                for p in (save.save_path(), save.save_path() + ".bak"):
                    with open(p, "w") as f:
                        f.write(payload)
                data = save.read_save()
                run = data["run"] if data else None
                self.assertIsNone(run)

    def test_09_run_com_dados_malucos_cai_em_recuperacao_segura(self):
        g = self._make_run_save()
        good = save.read_save()
        mutations = {
            "posição NaN": lambda r: r["player"].update(x=float("nan")),
            "posição texto": lambda r: r["player"].update(x="abc"),
            "posição fora do mapa": lambda r: r["player"].update(x=10 ** 9),
            "posição dentro da parede": lambda r: r["player"].update(x=0, y=-100),
            "vida negativa": lambda r: r["player"].update(health=-5),
            "índice de moeda inválido": lambda r: r.update(coins=[10 ** 6]),
            "inimigos truncados": lambda r: r.update(enemies=r["enemies"][:3]),
            "inimigo de outro tipo": lambda r: r["enemies"][0].update(t="Boss"),
            "estalactite com estado inválido": lambda r: r.update(
                stalactites=[{"i": 0, "s": "xyz", "y": 0, "vy": 0, "sh": 0, "lt": 0, "ft": 0, "tr": 1, "ah": 0}]),
            "checkpoints não é lista": lambda r: r.update(checkpoints="a"),
            "fase desconhecida": lambda r: r["level"].update(id="lava"),
            "assinatura diferente": lambda r: r["level"]["signature"].update(enemies=1),
            "respawn inválido": lambda r: r.update(respawn={"x": None, "y": 1}),
        }
        refused, recovered = [], []
        for name, mutate in mutations.items():
            with self.subTest(name):
                data = json.loads(json.dumps(good))
                mutate(data["run"])
                try:
                    level, player, core, _ = run_state.restore_run(data["run"], data["stats"])
                except ValueError:
                    refused.append(name)
                    continue                        # recusado com elegância
                recovered.append(name)
                # aceito: o jogador tem de estar numa posição válida e viva
                self.assertTrue(player.alive)
                self.assertGreater(player.health, 0)
                self.assertLessEqual(player.health, player.stats.max_health)
                solids = level.platforms.rects()
                self.assertFalse(any(player.rect.colliderect(s) for s in solids))
                self.assertEqual(data["stats"]["coins"], player.stats.coins)
        self.assertEqual(len(refused) + len(recovered), len(mutations))
        self.assertTrue(refused and recovered, (refused, recovered))   # os dois caminhos foram exercitados

    def test_continuar_com_run_ilegivel_avisa_e_nao_apaga(self):
        self._make_run_save()
        data = self.read_raw()
        data["run"]["level"]["id"] = "lava"
        with open(save.save_path(), "w") as f:
            json.dump(data, f)
        g = self.reopen(save_on_exit=False)
        self.assertFalse(g.menu_screen.has_saved_run())          # resumo recusa
        data["run"]["level"]["id"] = "main"
        data["run"]["player"]["x"] = "quebrado"
        with open(save.save_path(), "w") as f:
            json.dump(data, f)
        g.refresh_saved_run()
        self.assertTrue(g.menu_screen.has_saved_run())
        self.press(pygame.K_RETURN)                              # tenta continuar
        self.assertEqual(g.states.current, settings.STATE_PLAYING)   # recuperação segura
        self.assertEqual(g.player.rect.topleft, tuple(g.level.core_pos))
        self.assertTrue(os.path.exists(save.save_path()))

    def test_save_antigo_somente_progressao_continua_valendo(self):
        legacy = {"max_health": 120, "attack_damage": 1, "jump_force": -16.5, "attack_cooldown": 20,
                  "health_level": 1, "double_jump_level": 0, "extra_jumps": 0, "magnet_level": 0,
                  "swords_owned": [], "sword_levels": {}, "equipped_sword_id": None,
                  "coins": 55, "total_coins_collected": 90}
        with open(save.save_path(), "w") as f:
            json.dump(legacy, f)
        g = self.reopen(save_on_exit=False)
        self.assertFalse(g.menu_screen.has_saved_run())          # sem partida para continuar
        self.press(pygame.K_RETURN)                              # novo jogo mantém a progressão como antes
        self.assertEqual(g.player.stats.coins, 55)
        self.assertEqual(g.player.stats.max_health, 120)

    def test_fase_mudou_desde_o_save_volta_ao_nucleo_salvo(self):
        g = self.new_game()
        g.player.rect.x += 500
        g.player.stats.coins = 42
        g.save_run("test")
        data = self.read_raw()
        data["run"]["level"]["signature"]["enemies"] += 1        # simula atualização do mapa
        with open(save.save_path(), "w") as f:
            json.dump(data, f)
        g = self.reopen(save_on_exit=False)
        self.press(pygame.K_RETURN)
        self.assertEqual(g.states.current, settings.STATE_PLAYING)
        self.assertEqual(g.player.stats.coins, 42)               # progressão preservada
        self.assertEqual(g.player.rect.topleft, tuple(g.level.core_pos))


class TestMenuEDesenho(SaveTestCase):
    def test_menu_desenha_todos_os_estados_sem_erro(self):
        g = self.game
        g._draw()                                                # sem save
        self.new_game()
        g.save_run("test")
        g.return_to_menu()
        g.menu_screen.update()
        g._draw()                                                # Continuar / Novo jogo
        g.menu_screen.begin_confirm_new()
        g._draw()                                                # confirmação
        g.menu_screen.cancel_confirm()
        g.menu_screen.show_message("Não foi possível carregar a partida salva.")
        g._draw()
        self.press(pygame.K_RETURN)                              # continua
        g._save_notice = 50
        g._draw()                                                # aviso "Progresso salvo"

    def test_continuar_desabilitado_sem_save(self):
        g = self.game
        self.assertFalse(g.menu_screen.has_saved_run())
        self.press(pygame.K_s)                                   # setas não fazem nada
        self.assertEqual(g.states.current, settings.STATE_MENU)

    def test_local_do_save_e_formato(self):
        g = self.new_game()
        self.assertTrue(save.save_path().startswith(self.tmp))
        raw = self.read_raw()
        self.assertEqual(raw["version"], save.SAVE_VERSION)
        self.assertIn("stats", raw)
        self.assertIn("run", raw)
        self.assertLess(os.path.getsize(save.save_path()), 60_000)


class TestProcessoRealFechandoAJanela(unittest.TestCase):
    """Dois processos Python de verdade: joga, fecha a janela (evento QUIT), reabre."""

    SCRIPT = r'''
import os, sys, json
sys.path.insert(0, {root!r})
import pygame
from config import settings
from core.game import Game
from core import save

mode = sys.argv[1]
g = Game()
if mode == "play":
    g.start_new_game()
    g.input._held.add(pygame.K_d)
    for _ in range(180):
        g._update(); g.input.end_frame()
    g.input._held.clear()
    g.level.enemies[2].take_damage(10**6)
    g.player.stats.coins = 88
    print(json.dumps({{"pos": list(g.player.rect.topleft)}}))
    pygame.event.post(pygame.event.Event(pygame.QUIT))   # fecha a janela
    try:
        g.run()
    except SystemExit:
        pass
else:
    assert g.menu_screen.has_saved_run()
    g.input._pressed_this_frame.add(pygame.K_RETURN)
    g._update()
    print(json.dumps({{"pos": list(g.player.rect.topleft), "coins": g.player.stats.coins,
                      "enemy2_alive": g.level.enemies[2].alive}}))
'''

    def test_fechar_e_abrir_em_outro_processo(self):
        tmp = tempfile.mkdtemp(prefix="vr_proc_")
        try:
            env = dict(os.environ, VENGEANCE_SAVE_DIR=tmp, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
            code = self.SCRIPT.format(root=ROOT)
            out1 = subprocess.run([sys.executable, "-c", code, "play"], env=env, cwd=ROOT,
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(out1.returncode, 0, out1.stderr)
            before = json.loads(out1.stdout.strip().splitlines()[-1])
            out2 = subprocess.run([sys.executable, "-c", code, "resume"], env=env, cwd=ROOT,
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(out2.returncode, 0, out2.stderr)
            after = json.loads(out2.stdout.strip().splitlines()[-1])
            self.assertEqual(after["pos"], before["pos"])
            self.assertEqual(after["coins"], 88)
            self.assertFalse(after["enemy2_alive"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
