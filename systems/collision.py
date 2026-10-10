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
    Retorna (novo_rect, on_ground). As colisões laterais continuam
    bloqueando o movimento, sem ativar habilidades especiais."""
    rect = entity_rect.copy()
    on_ground = False

    # Eixo X
    rect.x += round(vel_x)
    for solid in solids:
        if rect.colliderect(solid):
            if vel_x > 0:
                rect.right = solid.left
            elif vel_x < 0:
                rect.left = solid.right

    # Eixo Y
    rect.y += round(vel_y)
    for solid in solids:
        if rect.colliderect(solid):
            if vel_y > 0:
                rect.bottom = solid.top
                on_ground = True
            elif vel_y < 0:
                rect.top = solid.bottom

    return rect, on_ground


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


def segment_hits_rect(start, end, rect):
    """True se o segmento start->end atravessa o INTERIOR do retângulo
    (clipping de Liang-Barsky). Apenas tocar numa quina não conta como
    bloqueio; usa só left/right/top/bottom do rect."""
    x0, y0 = start
    dx = end[0] - x0
    dy = end[1] - y0
    t0, t1 = 0.0, 1.0
    for p_, q_ in ((-dx, x0 - rect.left), (dx, rect.right - x0),
                   (-dy, y0 - rect.top), (dy, rect.bottom - y0)):
        if p_ == 0:
            if q_ < 0:
                return False  # paralelo e fora da faixa deste lado
            continue
        t = q_ / p_
        if p_ < 0:
            if t > t1:
                return False
            t0 = max(t0, t)
        else:
            if t < t0:
                return False
            t1 = min(t1, t)
    return t0 < t1


def line_of_sight_clear(start, end, solids):
    """True se nenhum retângulo sólido bloqueia o segmento start->end."""
    for s in solids:
        if segment_hits_rect(start, end, s):
            return False
    return True
