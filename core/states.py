"""
core/states.py
Responsável por controlar os estados do jogo: menu, jogo, pausa,
loja, vitória e derrota. Um StateMachine simples baseado em string,
suficiente para o escopo do projeto (não é necessário over-engineering
com classes abstratas para cada estado).
"""

from config import settings


class StateMachine:
    def __init__(self, initial_state=settings.STATE_MENU):
        self.current = initial_state
        self.previous = None

    def change(self, new_state):
        if new_state != self.current:
            self.previous = self.current
            self.current = new_state

    def is_(self, state):
        return self.current == state

    def revert(self):
        """Volta ao estado anterior (usado por exemplo ao sair da pausa)."""
        if self.previous is not None:
            self.current, self.previous = self.previous, self.current
