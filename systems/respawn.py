"""
systems/respawn.py
Responsável pelo retorno de Kael ao ponto inicial (Núcleo do Retorno)
após a morte. Conforme a seção 15 do documento: as moedas e melhorias
já estão salvas em player.stats (que não é resetado), então "retornar"
significa apenas reposicionar o personagem e restaurar a vida - a
progressão é mantida.
"""


class RespawnSystem:
    def __init__(self, core_x, core_y):
        self.core_x = core_x
        self.core_y = core_y

    def set_core(self, x, y):
        self.core_x = x
        self.core_y = y

    def respawn(self, player):
        player.respawn_at_core(self.core_x, self.core_y)
