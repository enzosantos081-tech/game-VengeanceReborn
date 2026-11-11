"""
Remove a borda branca/bege (halo de 1-2 px) que veio "queimada" na spritesheet.
Uso:  python limpar_borda.py kael_spritesheet.png kael_spritesheet_limpa.png
Só mexe em pixels da BORDA externa (encostados em transparência); o
interior do personagem não é alterado.
"""
import sys
from PIL import Image


def limpar(entrada, saida):
    im = Image.open(entrada).convert("RGBA")
    px = im.load()
    w, h = im.size

    def na_borda(x, y):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] == 0:
                    return True
        return False

    def eh_halo_branco(p):      # camada 1: quase branco
        return min(p[:3]) >= 220

    def eh_halo_bege(p):        # camada 2: claro e pouco saturado
        return sum(p[:3]) / 3 >= 135 and (max(p[:3]) - min(p[:3])) <= 40

    # Branco: repete até 4 vezes para pegar manchas brancas maiores que
    # encostam no contorno (ex.: sob a capa). Depois uma passada no bege.
    for criterio, vezes in ((eh_halo_branco, 4), (eh_halo_bege, 1)):
        for _ in range(vezes):
            apagar = [(x, y) for y in range(h) for x in range(w)
                      if px[x, y][3] == 255 and criterio(px[x, y]) and na_borda(x, y)]
            if not apagar:
                break
            for x, y in apagar:
                px[x, y] = (0, 0, 0, 0)
    im.save(saida)


if __name__ == "__main__":
    limpar(sys.argv[1], sys.argv[2])
