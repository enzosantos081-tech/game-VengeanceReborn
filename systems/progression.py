"""Utilitários de progressão usados pela loja."""

from config import settings


def upgrade_description(kind):
    """Descrições apenas para as melhorias que continuam disponíveis."""
    if kind == "health":
        return f"+{settings.UPGRADE_HEALTH_AMOUNT} Vida máxima — {settings.UPGRADE_HEALTH_COST} moedas"
    if kind == "double_jump":
        return f"Pulo duplo — {settings.UPGRADE_DOUBLE_JUMP_COST} moedas"
    if kind == "magnet":
        return f"Ímã de moedas — {settings.UPGRADE_MAGNET_COST} moedas"
    if kind == "heal":
        return f"Curar {settings.SHOP_HEAL_AMOUNT} de vida — {settings.SHOP_HEAL_COST} moedas"
    return ""


def apply_full_heal_on_upgrade(player):
    """Ao melhorar a vida máxima, restaura a vida atual ao máximo."""
    player.health = player.stats.max_health
