"""
systems/progression.py
Responsável pelas melhorias do personagem. A lógica de custo/efeito já
vive em player/player_stats.py (que é o dono do estado); este módulo
oferece funções utilitárias de alto nível usadas pela loja (systems/shop.py)
e pela HUD, como texto de status e descrições, mantendo a UI desacoplada
das regras de negócio.
"""

from config import settings


def upgrade_description(kind):
    if kind == "health":
        return f"+{settings.UPGRADE_HEALTH_AMOUNT} Vida máxima — {settings.UPGRADE_HEALTH_COST} moedas"
    if kind == "damage":
        return f"+{settings.UPGRADE_DAMAGE_AMOUNT} Dano — {settings.UPGRADE_DAMAGE_COST} moedas"
    if kind == "jump":
        return f"+Força de pulo — {settings.UPGRADE_JUMP_COST} moedas"
    if kind == "attack_speed":
        return f"+Velocidade de ataque — {settings.UPGRADE_ATTACK_SPEED_COST} moedas"
    if kind == "double_jump":
        return f"Pulo duplo — {settings.UPGRADE_DOUBLE_JUMP_COST} moedas"
    if kind == "magnet":
        return f"Ímã de moedas — {settings.UPGRADE_MAGNET_COST} moedas"
    if kind == "dash_charge":
        return f"Carga extra de dash — {settings.UPGRADE_DASH_CHARGE_COST} moedas"
    if kind == "heal":
        return f"Curar {settings.SHOP_HEAL_AMOUNT} de vida — {settings.SHOP_HEAL_COST} moedas"
    return ""


def apply_full_heal_on_upgrade(player):
    """Ao melhorar a vida máxima, também restaura a vida atual ao máximo -
    sensação de recompensa imediata ao investir moedas."""
    player.health = player.stats.max_health
