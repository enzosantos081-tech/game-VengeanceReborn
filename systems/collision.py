"""
systems/collision.py
Responsável pelas colisões entre entidades (jogador/inimigos) e as
plataformas sólidas do cenário. Usa resolução por eixo separado
(mover em X, resolver colisões em X; mover em Y, resolver colisões em Y),
uma técnica simples e robusta o suficiente para um platformer sem
física realista.
"""


def move_and_collide(entity_rect, vel_x, vel_y, solids):
    """Move um retângulo contra uma lista de retângulos sólidos.
    Retorna (novo_rect, on_ground, wall_dir).
    wall_dir: 0 se não bateu lateralmente neste frame, 1 se bateu num
    sólido à direita (movendo-se para a direita), -1 se bateu à
    esquerda. Usado pelo wall slide/wall jump do jogador."""
    rect = entity_rect.copy()
    on_ground = False
    wall_dir = 0

    # Eixo X
    rect.x += round(vel_x)
    for solid in solids:
        if rect.colliderect(solid):
            if vel_x > 0:
                rect.right = solid.left
                wall_dir = 1
            elif vel_x < 0:
                rect.left = solid.right
                wall_dir = -1

    # Eixo Y
    rect.y += round(vel_y)
    for solid in solids:
        if rect.colliderect(solid):
            if vel_y > 0:
                rect.bottom = solid.top
                on_ground = True
            elif vel_y < 0:
                rect.top = solid.bottom

    return rect, on_ground, wall_dir


def rect_collides_any(rect, solids):
    for s in solids:
        if rect.colliderect(s):
            return True
    return False


def ground_exists_below(rect, direction, solids, probe_distance=12):
    """Verifica se existe chão à frente na direção do movimento, usado
    para impedir que inimigos comuns andem para dentro de buracos."""
    import pygame
    probe_x = rect.right if direction > 0 else rect.left - 4
    probe = pygame.Rect(probe_x, rect.bottom, 4, probe_distance)
    return rect_collides_any(probe, solids)
