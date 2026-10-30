"""
screens/menu.py
Tela inicial do jogo + um pequeno "kit de UI" usado pelas outras telas
(fontes, painéis, texto com brilho, vinheta, fundo...). Assim todas as
telas compartilham a mesma identidade visual: noite azul, lua pálida e
brasas laranja/vermelhas (combinando com o panorama do castelo em chamas).

FUNDO: se existir uma imagem em  assets/backgrounds/panorama.png  ela é
usada (escalada na altura da tela, com um leve efeito de câmera lenta no
menu). Se o arquivo não existir, é gerado um céu noturno simples, então o
jogo continua funcionando sem a imagem.
"""

import math
import os
import random

import pygame
from config import settings

# ---------- Paleta ----------
COL_TEXT = (236, 238, 250)
COL_MOON = (205, 220, 250)
COL_MOON_DIM = (150, 165, 205)
COL_EMBER = (255, 150, 70)
COL_GOLD = (255, 214, 100)
COL_CRIMSON = (222, 62, 78)
COL_PANEL = (10, 13, 30)
COL_BORDER = (96, 112, 170)

# ---------- Fontes ----------
_SERIF = "georgia,palatinolinotype,constantia,timesnewroman,serif"
_font_cache = {}


def get_font(size, serif=False, bold=False):
    """Fonte com cache. serif=True usa uma fonte com serifa (títulos);
    se nenhuma estiver instalada o pygame cai na fonte padrão sozinho."""
    key = (size, serif, bold)
    if key not in _font_cache:
        if serif:
            _font_cache[key] = pygame.font.SysFont(_SERIF, size, bold=bold)
        else:
            _font_cache[key] = pygame.font.Font(None, size)
    return _font_cache[key]


# ---------- Texto ----------
def text_surface(font, text, color, spacing=0):
    """Renderiza texto; 'spacing' adiciona espaço extra entre as letras."""
    if spacing == 0:
        return font.render(text, True, color)
    glyphs = [font.render(ch, True, color) for ch in text]
    width = sum(g.get_width() for g in glyphs) + spacing * (len(glyphs) - 1)
    height = max(g.get_height() for g in glyphs)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    x = 0
    for g in glyphs:
        surf.blit(g, (x, 0))
        x += g.get_width() + spacing
    return surf


def draw_text_glow(surface, font, text, color, center, glow=None, spacing=0):
    """Texto com sombra e (opcionalmente) um halo colorido ao redor."""
    main = text_surface(font, text, color, spacing)
    rect = main.get_rect(center=center)
    if glow:
        halo = text_surface(font, text, glow, spacing)
        halo.set_alpha(70)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)):
            surface.blit(halo, rect.move(dx, dy))
    shadow = text_surface(font, text, (0, 0, 0), spacing)
    shadow.set_alpha(190)
    surface.blit(shadow, rect.move(3, 3))
    surface.blit(main, rect)
    return rect


# ---------- Formas ----------
def draw_panel(surface, rect, alpha=205, border=COL_BORDER, radius=12):
    """Painel translúcido com borda dupla (uma grossa e uma fina por dentro)."""
    rect = pygame.Rect(rect)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    full = panel.get_rect()
    pygame.draw.rect(panel, (*COL_PANEL, alpha), full, border_radius=radius)
    pygame.draw.rect(panel, (*border, 255), full, width=2, border_radius=radius)
    pygame.draw.rect(panel, (*border, 70), full.inflate(-10, -10), width=1,
                     border_radius=max(2, radius - 4))
    surface.blit(panel, rect.topleft)


def draw_divider(surface, cx, y, half_width=150, color=COL_EMBER):
    """Linha decorativa com um losango no meio."""
    pygame.draw.line(surface, color, (cx - half_width, y), (cx - 12, y), 2)
    pygame.draw.line(surface, color, (cx + 12, y), (cx + half_width, y), 2)
    pygame.draw.polygon(surface, color, [(cx, y - 6), (cx + 6, y), (cx, y + 6), (cx - 6, y)])


def draw_coin_icon(surface, center, radius=8):
    pygame.draw.circle(surface, (255, 214, 90), center, radius)
    pygame.draw.circle(surface, (170, 120, 20), center, radius, width=2)
    pygame.draw.circle(surface, (255, 245, 190), (center[0] - radius // 3, center[1] - radius // 3),
                       max(1, radius // 4))


def draw_key_chip(surface, x, y, label, font):
    """Desenha uma 'tecla' (ex.: [Q]) e devolve o Rect dela."""
    txt = font.render(label, True, COL_TEXT)
    rect = pygame.Rect(x, y, txt.get_width() + 16, 26)
    pygame.draw.rect(surface, (30, 38, 72), rect, border_radius=6)
    pygame.draw.rect(surface, COL_BORDER, rect, width=2, border_radius=6)
    surface.blit(txt, txt.get_rect(center=rect.center))
    return rect


def vertical_gradient(width, height, top, bottom):
    """Gradiente vertical. Cores podem ter 4 valores (RGBA)."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(height):
        t = y / max(1, height - 1)
        col = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(len(top)))
        pygame.draw.line(surf, col, (0, y), (width, y))
    return surf


def make_vignette(width, height, strength=170, steps=36):
    """Escurece as bordas da tela (pré-calcule uma vez e reutilize)."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for i in range(steps):
        t = 1.0 - i / steps
        alpha = int(strength * t * t * t)
        rect = pygame.Rect(0, 0, width, height).inflate(-i * 12, -i * 7)
        pygame.draw.rect(surf, (0, 0, 0, alpha), rect, width=7)
    return surf


# ---------- Fundo ----------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKDROP_FILES = ("panorama.png", "menu_bg.png", "background.png")
_backdrop_cache = None


def _fallback_backdrop(w, h):
    """Céu noturno simples (usado quando não há imagem de fundo)."""
    surf = vertical_gradient(w, h, (6, 8, 22), (30, 32, 74)).convert()
    rng = random.Random(3)
    for _ in range(110):
        sx, sy = rng.randint(0, w), rng.randint(0, int(h * 0.65))
        b = rng.randint(120, 255)
        pygame.draw.circle(surf, (b, b, min(255, b + 20)), (sx, sy), rng.choice((1, 1, 2)))
    glow = pygame.Surface((w, h), pygame.SRCALPHA)
    mx, my = int(w * 0.6), int(h * 0.27)
    for r, a in ((78, 16), (60, 28), (44, 46)):
        pygame.draw.circle(glow, (190, 205, 255, a), (mx, my), r)
    surf.blit(glow, (0, 0))
    pygame.draw.circle(surf, (225, 232, 250), (mx, my), 30)
    pts = [(0, h)]
    for x in range(0, w + 20, 20):
        pts.append((x, h - 120 - 38 * math.sin(x * 0.004) - 22 * math.sin(x * 0.011 + 1)))
    pts.append((w, h))
    pygame.draw.polygon(surf, (9, 11, 26), pts)
    pygame.draw.rect(surf, (14, 12, 28), (0, h - 64, w, 64))
    return surf


def load_backdrop():
    """Surface larga com a altura da tela. Carrega 1x e guarda em cache."""
    global _backdrop_cache
    if _backdrop_cache is not None:
        return _backdrop_cache
    w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
    for name in _BACKDROP_FILES:
        path = os.path.join(_ROOT, "assets", "backgrounds", name)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert()
                scale = h / img.get_height()
                img = pygame.transform.smoothscale(img, (max(w, int(img.get_width() * scale)), h))
                _backdrop_cache = img
                return img
            except pygame.error:
                pass
    _backdrop_cache = _fallback_backdrop(w, h)
    return _backdrop_cache


# ====================================================================
# Tela inicial
# ====================================================================
class MenuScreen:
    # Com uma partida salva, o menu mostra estas opções (as strings são
    # usadas por core/game.py - se mudar o texto, mude lá também).
    OPTIONS = ["Continuar", "Novo jogo"]
    CONFIRM_OPTIONS = ["Cancelar", "Substituir"]
    MESSAGE_FRAMES = 240

    # (teclas, descrição) - coluna da esquerda e da direita
    CONTROLS_LEFT = [
        (["A", "D"], "Mover (ou setas)"),
        (["ESPAÇO"], "Pular (2x no ar: pulo duplo)"),
        (["MOUSE 1"], "Atacar na direção do mouse"),
    ]
    CONTROLS_RIGHT = [
        (["Q"], "Dash"),
        (["E"], "Interagir / abrir a loja"),
        (["ESC", "P"], "Pausar"),
        (["ENTER"], "Confirmar"),
    ]

    def __init__(self):
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        self.t = 0
        self.title_font = get_font(92, serif=True, bold=True)
        self.reborn_font = get_font(38, serif=True, bold=True)
        self.tag_font = get_font(28)
        self.prompt_font = get_font(30)
        self.head_font = get_font(22)
        self.key_font = get_font(20)
        self.desc_font = get_font(23)

        self.backdrop = load_backdrop()
        self.shade = vertical_gradient(w, h, (3, 5, 16, 120), (3, 5, 16, 170))
        self.vignette = make_vignette(w, h, strength=190)

        # Partida salva (resumo vindo de core/run_state.summarize) e estado
        # da seleção / confirmação de "Novo jogo".
        self.saved = None
        self.selected_index = 0
        self.confirming_new = False
        self.confirm_index = 0
        self.message = ""
        self.message_timer = 0

    # ---------- Partida salva ----------
    def set_saved_run(self, summary):
        """summary: dict com region/coins/minutes, ou None se não há partida."""
        self.saved = summary
        self.selected_index = 0
        self.confirming_new = False
        self.confirm_index = 0

    def has_saved_run(self):
        return self.saved is not None

    def move_selection(self, delta):
        self.selected_index = (self.selected_index + delta) % len(MenuScreen.OPTIONS)

    def selected_option(self):
        return MenuScreen.OPTIONS[self.selected_index]

    def begin_confirm_new(self):
        self.confirming_new = True
        self.confirm_index = 0          # começa em "Cancelar": nada é apagado sem querer

    def cancel_confirm(self):
        self.confirming_new = False

    def toggle_confirm(self):
        self.confirm_index = 1 - self.confirm_index

    def confirm_is_replace(self):
        return MenuScreen.CONFIRM_OPTIONS[self.confirm_index] == "Substituir"

    def show_message(self, text):
        self.message = text
        self.message_timer = MenuScreen.MESSAGE_FRAMES

    def update(self):
        self.t += 1
        if self.message_timer > 0:
            self.message_timer -= 1

    def draw(self, surface):
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        cx = w // 2

        # Fundo com "câmera" passeando bem devagar pelo panorama
        span = self.backdrop.get_width() - w
        offset = int(span * (1 - math.cos(self.t * 0.0025)) / 2) if span > 0 else 0
        surface.blit(self.backdrop, (-offset, 0))
        surface.blit(self.shade, (0, 0))
        surface.blit(self.vignette, (0, 0))

        # Título
        draw_text_glow(surface, self.title_font, "VENGEANCE", COL_TEXT, (cx, 112), glow=COL_EMBER)
        draw_text_glow(surface, self.reborn_font, "REBORN", COL_EMBER, (cx, 176), spacing=18)
        draw_divider(surface, cx, 212, half_width=190)

        tagline = self.tag_font.render("Kael busca vingança contra Vharok, o Rei do Abismo",
                                       True, COL_MOON)
        surface.blit(tagline, tagline.get_rect(center=(cx, 242)))

        if self.saved is None:
            # "Pressione ENTER" piscando
            alpha = int(165 + 90 * math.sin(self.t * 0.05))
            prompt = self.prompt_font.render("Pressione ENTER ou ESPAÇO para começar", True, COL_TEXT)
            prompt.set_alpha(alpha)
            prect = prompt.get_rect(center=(cx, 298))
            surface.blit(prompt, prect)
            for side in (-1, 1):
                px = prect.left - 22 if side < 0 else prect.right + 22
                pygame.draw.polygon(surface, COL_EMBER,
                                    [(px, 298 - 5), (px + 5, 298), (px, 298 + 5), (px - 5, 298)])
            controls_top = 338
        else:
            self._draw_options(surface, cx)
            controls_top = 356

        self._draw_controls(surface, cx, controls_top)
        if self.message_timer > 0:
            msg = self.head_font.render(self.message, True, COL_CRIMSON)
            msg.set_alpha(min(255, self.message_timer * 5))
            surface.blit(msg, msg.get_rect(center=(cx, 266)))
        if self.confirming_new:
            self._draw_confirm(surface, cx)

    def _draw_options(self, surface, cx):
        """Lista "Continuar" / "Novo jogo" (só quando há partida salva)."""
        pulse = 0.5 + 0.5 * math.sin(self.t * 0.1)
        y = 286
        for i, option in enumerate(MenuScreen.OPTIONS):
            selected = i == self.selected_index and not self.confirming_new
            label = self.prompt_font.render(option, True, COL_TEXT if selected else COL_MOON_DIM)
            detail = None
            if option == "Continuar":
                s = self.saved
                detail = self.desc_font.render(
                    f"{s['region']}  ·  {s['coins']} moedas  ·  {s['minutes']} min", True, COL_MOON_DIM)
            width = label.get_width() + (detail.get_width() + 18 if detail else 0)
            left = cx - width // 2
            row = label.get_rect(midleft=(left, y))
            surface.blit(label, row)
            if detail:
                surface.blit(detail, detail.get_rect(midleft=(row.right + 18, y + 1)))
            if selected:
                mx, my = left - 22, y
                color = (255, int(130 + 40 * pulse), 70)
                pygame.draw.polygon(surface, color,
                                    [(mx, my - 6), (mx + 6, my), (mx, my + 6), (mx - 6, my)])
            y += 38

    def _draw_confirm(self, surface, cx):
        """Janela de confirmação: novo jogo substitui a partida salva."""
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        dim = pygame.Surface((w, h), pygame.SRCALPHA)
        dim.fill((3, 5, 16, 170))
        surface.blit(dim, (0, 0))
        panel = pygame.Rect(0, 0, 600, 210)
        panel.center = (cx, h // 2)
        draw_panel(surface, panel, alpha=255)
        title = get_font(40, serif=True, bold=True).render("Substituir partida salva?", True, COL_TEXT)
        surface.blit(title, title.get_rect(center=(cx, panel.y + 42)))
        draw_divider(surface, cx, panel.y + 72, half_width=110)
        body = self.desc_font.render("Um novo jogo apaga o progresso salvo. Isso não pode ser desfeito.",
                                     True, COL_MOON_DIM)
        surface.blit(body, body.get_rect(center=(cx, panel.y + 104)))
        for i, option in enumerate(MenuScreen.CONFIRM_OPTIONS):
            btn = pygame.Rect(0, 0, 200, 46)
            btn.center = (cx + (-120 if i == 0 else 120), panel.y + 160)
            selected = i == self.confirm_index
            color = COL_CRIMSON if option == "Substituir" else COL_EMBER
            if selected:
                pygame.draw.rect(surface, color, btn, width=2, border_radius=8)
            text = self.prompt_font.render(option, True, COL_TEXT if selected else COL_MOON_DIM)
            surface.blit(text, text.get_rect(center=btn.center))

    def _draw_controls(self, surface, cx, top=338):
        panel = pygame.Rect(cx - 410, top, 820, 204)
        draw_panel(surface, panel, alpha=190)

        head = self.head_font.render("CONTROLES", True, COL_EMBER)
        surface.blit(head, head.get_rect(center=(cx, panel.y + 22)))

        for col, entries in enumerate((self.CONTROLS_LEFT, self.CONTROLS_RIGHT)):
            col_x = panel.x + 34 + col * 402
            y = panel.y + 48
            for keys, desc in entries:
                x = col_x
                for key in keys:
                    x = draw_key_chip(surface, x, y, key, self.key_font).right + 5
                text = self.desc_font.render(desc, True, COL_MOON_DIM)
                surface.blit(text, text.get_rect(midleft=(col_x + 118, y + 13)))
                y += 36
