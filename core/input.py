"""
core/input.py
Centraliza os comandos do teclado, evitando espalhar pygame.key.get_pressed()
por todo o código. Também rastreia "just pressed" (apertado neste frame)
para ações que não devem repetir enquanto a tecla fica segurada (pulo, ataque,
pausa, interação).
"""

import pygame


class InputManager:
    def __init__(self):
        self._held = set()
        self._pressed_this_frame = set()
        self._released_this_frame = set()

        # Botões do mouse tratados separadamente do teclado (namespace
        # próprio), usados para o ataque com clique esquerdo.
        self._mouse_held = set()
        self._mouse_pressed_this_frame = set()
        self._mouse_released_this_frame = set()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key not in self._held:
                self._pressed_this_frame.add(event.key)
            self._held.add(event.key)
        elif event.type == pygame.KEYUP:
            self._held.discard(event.key)
            self._released_this_frame.add(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button not in self._mouse_held:
                self._mouse_pressed_this_frame.add(event.button)
            self._mouse_held.add(event.button)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._mouse_held.discard(event.button)
            self._mouse_released_this_frame.add(event.button)

    def end_frame(self):
        """Deve ser chamado no final de cada frame, após o loop processar eventos."""
        self._pressed_this_frame.clear()
        self._released_this_frame.clear()
        self._mouse_pressed_this_frame.clear()
        self._mouse_released_this_frame.clear()

    def is_held(self, key):
        return key in self._held

    def is_pressed(self, key):
        """True apenas no frame em que a tecla foi pressionada."""
        return key in self._pressed_this_frame

    def is_released(self, key):
        return key in self._released_this_frame

    # ---------- Ações de alto nível (facilita troca de bind no futuro) ----------
    def move_left(self):
        return self.is_held(pygame.K_a) or self.is_held(pygame.K_LEFT)

    def move_right(self):
        return self.is_held(pygame.K_d) or self.is_held(pygame.K_RIGHT)

    def jump_pressed(self):
        return self.is_pressed(pygame.K_SPACE) or self.is_pressed(pygame.K_w) or self.is_pressed(pygame.K_UP)

    def jump_held(self):
        return self.is_held(pygame.K_SPACE) or self.is_held(pygame.K_w) or self.is_held(pygame.K_UP)

    def attack_pressed(self):
        """Ataque agora é feito com o clique esquerdo do mouse. A mira
        (lado do golpe) é calculada em Player.handle_input a partir da
        posição do cursor, sem alterar a direção que o personagem olha."""
        return 1 in self._mouse_pressed_this_frame

    def mouse_world_x(self, camera_x):
        """Posição X do cursor no mundo (considera o scroll da câmera)."""
        mouse_x, _ = pygame.mouse.get_pos()
        return mouse_x + camera_x

    def dash_pressed(self):
        return self.is_pressed(pygame.K_q)

    def interact_pressed(self):
        return self.is_pressed(pygame.K_e) or self.is_pressed(pygame.K_RETURN)

    def pause_pressed(self):
        return self.is_pressed(pygame.K_ESCAPE) or self.is_pressed(pygame.K_p)

    def confirm_pressed(self):
        return self.is_pressed(pygame.K_RETURN) or self.is_pressed(pygame.K_SPACE)

    def down_pressed(self):
        return self.is_pressed(pygame.K_s) or self.is_pressed(pygame.K_DOWN)

    def up_pressed(self):
        return self.is_pressed(pygame.K_w) or self.is_pressed(pygame.K_UP)
