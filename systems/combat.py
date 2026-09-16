"""
systems/combat.py
Responsável por organizar o dano entre jogador, inimigos e Boss.
O dano de inimigo -> jogador é resolvido dentro da própria classe do
inimigo (enemy.check_contact_damage), pois cada tipo tem sua lógica de
contato. Este módulo cuida da direção jogador -> inimigo, comum a todos
os alvos: usa a hitbox de ataque de Kael e aplica dano aos inimigos
atingidos (uma vez por golpe, controlado por PlayerAttack.hit_enemies_this_swing).
"""


def resolve_player_attack(player, enemies, particles=None):
    """Aplica o dano do ataque de Kael aos inimigos atingidos.
    Retorna (hit_ids, coins_awarded): hit_ids para o som de acerto,
    coins_awarded (soma das moedas dadas por qualquer inimigo derrotado
    neste golpe) para o som de moeda em core/game.py."""
    hitbox = player.attack.get_hitbox(player.rect, player.attack_facing_right)
    if hitbox is None:
        return [], 0

    hit_ids = []
    coins_awarded = 0
    for enemy in enemies:
        if not enemy.alive:
            continue
        if player.attack.has_hit(enemy.id):
            continue
        if hitbox.colliderect(enemy.rect):
            enemy.take_damage(player.stats.attack_damage)
            player.attack.register_hit(enemy.id)
            hit_ids.append(enemy.id)
            if particles:
                particles.emit_hit(enemy.rect.centerx, enemy.rect.centery)
            if not enemy.alive and enemy.coin_value:
                # Todo mob dá moedas ao ser derrotado (incluindo o Boss).
                player.stats.add_coins(enemy.coin_value)
                coins_awarded += enemy.coin_value
                if particles:
                    particles.emit_coin(enemy.rect.centerx, enemy.rect.centery)
    return hit_ids, coins_awarded
