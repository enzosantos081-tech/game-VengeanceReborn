"""Catálogo de espadas da loja e valores usados diretamente pelo combate."""

SWORDS = {
    "survivor": {
        "name": "Espada do Sobrevivente",
        "subtitle": "Aço simples, vontade inquebrável.",
        "price": 30,
        "damage": 1,
        "upgrade_damage": 1,
        "max_level": 2,
        "upgrade_costs": (20, 35),
        "color": (183, 190, 204),
    },
    "shadow": {
        "name": "Lâmina Sombria",
        "subtitle": "Uma lâmina que bebe a luz.",
        "price": 80,
        "damage": 2,
        "upgrade_damage": 1,
        "max_level": 2,
        "upgrade_costs": (35, 55),
        "color": (151, 112, 194),
    },
    "abyss": {
        "name": "Espada do Abismo",
        "subtitle": "Forjada sob um céu sem estrelas.",
        "price": 160,
        "damage": 3,
        "upgrade_damage": 1,
        "max_level": 2,
        "upgrade_costs": (60, 90),
        "color": (222, 72, 82),
    },
    "fallen_king": {
        "name": "Lâmina do Rei Caído",
        "subtitle": "O legado de um reino condenado.",
        "price": 280,
        "damage": 4,
        "upgrade_damage": 1,
        "max_level": 2,
        "upgrade_costs": (95, 140),
        "color": (237, 174, 76),
    },
}


def sword_damage(sword_id, level=0):
    """Dano total de uma espada no nível informado."""
    data = SWORDS[sword_id]
    return data["damage"] + data["upgrade_damage"] * min(level, data["max_level"])


def next_upgrade_cost(sword_id, level):
    costs = SWORDS[sword_id]["upgrade_costs"]
    return costs[level] if 0 <= level < len(costs) else None
