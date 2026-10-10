"""
player/player_stats.py
Responsável pelas estatísticas de Kael, pelas melhorias permanentes e pela
progressão das espadas equipáveis. O progresso é serializado no save do jogo.
"""

from config import settings
from systems.swords import SWORDS, sword_damage, next_upgrade_cost


class PlayerStats:
    def __init__(self):
        self.max_health = settings.PLAYER_MAX_HEALTH
        self.attack_damage = settings.PLAYER_ATTACK_DAMAGE
        self.jump_force = settings.PLAYER_JUMP_FORCE
        self.attack_cooldown = settings.PLAYER_ATTACK_COOLDOWN

        self.health_level = 0
        self.double_jump_level = 0   # 0 = não comprado, 1 = pulo duplo desbloqueado (compra única)
        self.extra_jumps = 0         # pulos extras no ar disponíveis (usado por player.py)
        self.magnet_level = 0        # 0 ou 1 - ímã de moedas (compra única)
        # O dash extra não é mais comprável; o zero mantém o contrato de player.py.
        self.extra_dash_charges = 0

        self.swords_owned = []
        self.sword_levels = {sword_id: 0 for sword_id in SWORDS}
        self.equipped_sword_id = None

        self.coins = 0
        self.total_coins_collected = 0

    # ---------- Moedas ----------
    def add_coins(self, amount):
        self.coins += amount
        self.total_coins_collected += amount

    def spend_coins(self, amount):
        if self.coins >= amount:
            self.coins -= amount
            return True
        return False

    # ---------- Melhorias ----------
    def can_upgrade_health(self):
        return self.health_level < settings.MAX_UPGRADE_LEVEL and self.coins >= settings.UPGRADE_HEALTH_COST

    def can_upgrade_double_jump(self):
        return self.double_jump_level < 1 and self.coins >= settings.UPGRADE_DOUBLE_JUMP_COST

    def can_upgrade_magnet(self):
        return self.magnet_level < 1 and self.coins >= settings.UPGRADE_MAGNET_COST

    def upgrade_health(self):
        if self.can_upgrade_health() and self.spend_coins(settings.UPGRADE_HEALTH_COST):
            self.health_level += 1
            self.max_health += settings.UPGRADE_HEALTH_AMOUNT
            return True
        return False

    def upgrade_double_jump(self):
        if self.can_upgrade_double_jump() and self.spend_coins(settings.UPGRADE_DOUBLE_JUMP_COST):
            self.double_jump_level = 1
            self.extra_jumps = 1
            return True
        return False

    def upgrade_magnet(self):
        if self.can_upgrade_magnet() and self.spend_coins(settings.UPGRADE_MAGNET_COST):
            self.magnet_level = 1
            return True
        return False

    # ---------- Espadas ----------
    @property
    def attack_damage(self):
        """Dano efetivo usado pelo combate: espada equipada ou valor legado."""
        if self.equipped_sword_id in self.swords_owned:
            return sword_damage(self.equipped_sword_id,
                                self.sword_levels.get(self.equipped_sword_id, 0))
        return self._legacy_attack_damage

    @attack_damage.setter
    def attack_damage(self, value):
        # Mantém compatibilidade com saves antigos que armazenam attack_damage.
        self._legacy_attack_damage = max(1, int(value))

    def owns_sword(self, sword_id):
        return sword_id in self.swords_owned

    def buy_sword(self, sword_id):
        if sword_id not in SWORDS or self.owns_sword(sword_id):
            return False
        if not self.spend_coins(SWORDS[sword_id]["price"]):
            return False
        self.swords_owned.append(sword_id)
        self.sword_levels.setdefault(sword_id, 0)
        self.equipped_sword_id = sword_id
        return True

    def equip_sword(self, sword_id):
        if not self.owns_sword(sword_id):
            return False
        self.equipped_sword_id = sword_id
        return True

    def can_upgrade_sword(self, sword_id):
        if not self.owns_sword(sword_id):
            return False
        level = self.sword_levels.get(sword_id, 0)
        cost = next_upgrade_cost(sword_id, level)
        return cost is not None and self.coins >= cost

    def upgrade_sword(self, sword_id):
        if not self.owns_sword(sword_id):
            return False
        level = self.sword_levels.get(sword_id, 0)
        cost = next_upgrade_cost(sword_id, level)
        if cost is None or not self.spend_coins(cost):
            return False
        self.sword_levels[sword_id] = level + 1
        return True

    def to_dict(self):
        return {
            "max_health": self.max_health,
            "attack_damage": self._legacy_attack_damage,
            "jump_force": settings.PLAYER_JUMP_FORCE,
            "attack_cooldown": settings.PLAYER_ATTACK_COOLDOWN,
            "health_level": self.health_level,
            "double_jump_level": self.double_jump_level,
            "extra_jumps": self.extra_jumps,
            "magnet_level": self.magnet_level,
            "swords_owned": list(self.swords_owned),
            "sword_levels": dict(self.sword_levels),
            "equipped_sword_id": self.equipped_sword_id,
            "coins": self.coins,
            "total_coins_collected": self.total_coins_collected,
        }

    def from_dict(self, data):
        self.max_health = data.get("max_health", settings.PLAYER_MAX_HEALTH)
        # Upgrades removidos não são reaplicados ao carregar saves antigos.
        self._legacy_attack_damage = settings.PLAYER_ATTACK_DAMAGE
        self.jump_force = settings.PLAYER_JUMP_FORCE
        self.attack_cooldown = settings.PLAYER_ATTACK_COOLDOWN
        self.health_level = data.get("health_level", 0)
        self.double_jump_level = data.get("double_jump_level", 0)
        self.extra_jumps = data.get("extra_jumps", 0)
        self.magnet_level = data.get("magnet_level", 0)
        # A carga extra de dash foi removida; o atributo 0 mantém o contrato
        # esperado por player.py sem modificar o dash básico.
        self.extra_dash_charges = 0
        self.swords_owned = [sid for sid in data.get("swords_owned", []) if sid in SWORDS]
        saved_levels = data.get("sword_levels", {})
        self.sword_levels = {sid: max(0, min(SWORDS[sid]["max_level"], int(saved_levels.get(sid, 0))))
                             for sid in SWORDS}
        equipped = data.get("equipped_sword_id")
        self.equipped_sword_id = equipped if equipped in self.swords_owned else None
        self.coins = max(0, int(data.get("coins", 0)))
        self.total_coins_collected = data.get("total_coins_collected", 0)
