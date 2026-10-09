"""
player/player_stats.py
Responsável pelas estatísticas de Kael: vida máxima, dano, força do pulo
e o nível de cada melhoria comprada na loja. Estes valores persistem
entre tentativas (mortes), pois representam a progressão do "roguelite".
"""

from config import settings


class PlayerStats:
    def __init__(self):
        self.max_health = settings.PLAYER_MAX_HEALTH
        self.attack_damage = settings.PLAYER_ATTACK_DAMAGE
        self.jump_force = settings.PLAYER_JUMP_FORCE
        self.attack_cooldown = settings.PLAYER_ATTACK_COOLDOWN

        self.health_level = 0
        self.damage_level = 0
        self.jump_level = 0
        self.attack_speed_level = 0
        self.double_jump_level = 0   # 0 = não comprado, 1 = pulo duplo desbloqueado (compra única)
        self.extra_jumps = 0         # pulos extras no ar disponíveis (usado por player.py)
        self.magnet_level = 0        # 0 ou 1 - ímã de moedas (compra única)
        self.dash_charge_level = 0   # 0 ou 1 - carga extra de dash (compra única)
        self.extra_dash_charges = 0  # cargas de dash além da primeira (usado por player.py)

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

    def can_upgrade_damage(self):
        return self.damage_level < settings.MAX_UPGRADE_LEVEL and self.coins >= settings.UPGRADE_DAMAGE_COST

    def can_upgrade_jump(self):
        return self.jump_level < settings.MAX_UPGRADE_LEVEL and self.coins >= settings.UPGRADE_JUMP_COST

    def can_upgrade_attack_speed(self):
        return (self.attack_speed_level < settings.MAX_UPGRADE_LEVEL
                and self.coins >= settings.UPGRADE_ATTACK_SPEED_COST
                and self.attack_cooldown > settings.MIN_ATTACK_COOLDOWN)

    def can_upgrade_double_jump(self):
        return self.double_jump_level < 1 and self.coins >= settings.UPGRADE_DOUBLE_JUMP_COST

    def can_upgrade_magnet(self):
        return self.magnet_level < 1 and self.coins >= settings.UPGRADE_MAGNET_COST

    def can_upgrade_dash_charge(self):
        return self.dash_charge_level < 1 and self.coins >= settings.UPGRADE_DASH_CHARGE_COST

    def upgrade_health(self):
        if self.can_upgrade_health() and self.spend_coins(settings.UPGRADE_HEALTH_COST):
            self.health_level += 1
            self.max_health += settings.UPGRADE_HEALTH_AMOUNT
            return True
        return False

    def upgrade_damage(self):
        if self.can_upgrade_damage() and self.spend_coins(settings.UPGRADE_DAMAGE_COST):
            self.damage_level += 1
            self.attack_damage += settings.UPGRADE_DAMAGE_AMOUNT
            return True
        return False

    def upgrade_jump(self):
        if self.can_upgrade_jump() and self.spend_coins(settings.UPGRADE_JUMP_COST):
            self.jump_level += 1
            self.jump_force -= settings.UPGRADE_JUMP_AMOUNT
            return True
        return False

    def upgrade_attack_speed(self):
        if self.can_upgrade_attack_speed() and self.spend_coins(settings.UPGRADE_ATTACK_SPEED_COST):
            self.attack_speed_level += 1
            self.attack_cooldown = max(
                settings.MIN_ATTACK_COOLDOWN,
                self.attack_cooldown - settings.UPGRADE_ATTACK_SPEED_AMOUNT,
            )
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

    def upgrade_dash_charge(self):
        if self.can_upgrade_dash_charge() and self.spend_coins(settings.UPGRADE_DASH_CHARGE_COST):
            self.dash_charge_level = 1
            self.extra_dash_charges = 1
            return True
        return False

    def to_dict(self):
        return {
            "max_health": self.max_health,
            "attack_damage": self.attack_damage,
            "jump_force": self.jump_force,
            "attack_cooldown": self.attack_cooldown,
            "health_level": self.health_level,
            "damage_level": self.damage_level,
            "jump_level": self.jump_level,
            "attack_speed_level": self.attack_speed_level,
            "double_jump_level": self.double_jump_level,
            "extra_jumps": self.extra_jumps,
            "magnet_level": self.magnet_level,
            "dash_charge_level": self.dash_charge_level,
            "extra_dash_charges": self.extra_dash_charges,
            "coins": self.coins,
            "total_coins_collected": self.total_coins_collected,
        }

    def from_dict(self, data):
        self.max_health = data.get("max_health", settings.PLAYER_MAX_HEALTH)
        self.attack_damage = data.get("attack_damage", settings.PLAYER_ATTACK_DAMAGE)
        self.jump_force = data.get("jump_force", settings.PLAYER_JUMP_FORCE)
        self.attack_cooldown = data.get("attack_cooldown", settings.PLAYER_ATTACK_COOLDOWN)
        self.health_level = data.get("health_level", 0)
        self.damage_level = data.get("damage_level", 0)
        self.jump_level = data.get("jump_level", 0)
        self.attack_speed_level = data.get("attack_speed_level", 0)
        self.double_jump_level = data.get("double_jump_level", 0)
        self.extra_jumps = data.get("extra_jumps", 0)
        self.magnet_level = data.get("magnet_level", 0)
        self.dash_charge_level = data.get("dash_charge_level", 0)
        self.extra_dash_charges = data.get("extra_dash_charges", 0)
        self.coins = data.get("coins", 0)
        self.total_coins_collected = data.get("total_coins_collected", 0)
