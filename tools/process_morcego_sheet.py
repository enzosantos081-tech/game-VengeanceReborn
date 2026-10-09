"""
Gera as spritesheets do Morcego Sombrio a partir da imagem de origem
(assets/morcego/morcego_inimigo_original.webp: 2 quadros de asa, 512x256).

Uso (ferramenta de desenvolvimento - NÃO é necessária para jogar):
    python tools/process_morcego_sheet.py <entrada.webp> <pasta_de_saida>
Ex.: python tools/process_morcego_sheet.py assets/morcego/morcego_inimigo_original.webp assets/morcego
Requer Pillow + numpy.

Etapas:
1. A imagem de origem é uma arte de 48x24 pixels ampliada ~10,67x. Cada
   pixel da arte é amostrado no centro do seu bloco, recuperando a grade
   original (2 quadros de 24x24).
2. As cores (ruído de compressão/ampliação) são reduzidas a uma paleta
   curta: 6 tons de cinza-arroxeado do corpo + olho laranja + barriga marrom.
3. O olho do quadro 2 estava do lado oposto ao do quadro 1; é colocado do
   mesmo lado para não "pular" ao bater as asas.
4. A arte original olha para a ESQUERDA (olho à esquerda). Os quadros são
   espelhados para gerar a versão que olha para a DIREITA.
5. Saída: morcego_sheet_24px.png (48x48) e morcego_sheet_96px.png (192x192,
   ampliação 4x sem suavização). Layout: linha 0 = direita, linha 1 =
   esquerda; coluna 0 = asas erguidas, coluna 1 = asas abaixadas.
"""
import os
import sys
import numpy as np
from PIL import Image

LOGICAL_W, LOGICAL_H = 48, 24     # tamanho da arte original (2 quadros de 24x24)
FRAME = 24
BODY_TONES = 6
EYE_ROW = 11                      # linha do olho
EYE_X_FRAME0 = 10                 # coluna do olho (relativa ao quadro) no quadro 1
EYE_X_FRAME1_OLD = 13             # onde o quadro 2 trazia o olho (lado oposto)


def recover_grid(src):
    big = np.asarray(Image.open(src).convert("RGBA"))
    step_x = big.shape[1] / LOGICAL_W
    step_y = big.shape[0] / LOGICAL_H
    grid = np.zeros((LOGICAL_H, LOGICAL_W, 4), dtype=np.int32)
    for gy in range(LOGICAL_H):
        for gx in range(LOGICAL_W):
            grid[gy, gx] = big[int((gy + 0.5) * step_y), int((gx + 0.5) * step_x)]
    return grid


def clean_palette(grid):
    opaque = grid[..., 3] > 0
    warm = opaque & ((grid[..., 0] - grid[..., 2]) > 25)
    eye_mask = warm & (grid[..., 0] > 140)
    belly_mask = warm & ~eye_mask
    body_mask = opaque & ~warm

    body_px = grid[body_mask][:, :3].astype(float)
    weights = np.array([0.299, 0.587, 0.114])
    lum = body_px @ weights
    centers = np.array([
        body_px[(lum >= np.quantile(lum, i / BODY_TONES)) & (lum <= np.quantile(lum, (i + 1) / BODY_TONES))].mean(axis=0)
        for i in range(BODY_TONES)
    ])
    for _ in range(30):                                   # k-means determinístico
        labels = ((body_px[:, None, :] - centers[None]) ** 2).sum(-1).argmin(1)
        for k in range(BODY_TONES):
            if (labels == k).any():
                centers[k] = body_px[labels == k].mean(axis=0)
    centers = centers[np.argsort(centers @ weights)].round().astype(int)

    eye_col = grid[eye_mask][:, :3].mean(axis=0).round().astype(int)
    belly_col = grid[belly_mask][:, :3].mean(axis=0).round().astype(int)

    out = np.zeros_like(grid)
    ys, xs = np.nonzero(body_mask)
    out[ys, xs, :3] = centers[((grid[ys, xs, :3][:, None, :] - centers[None]) ** 2).sum(-1).argmin(1)]
    out[ys, xs, 3] = 255
    for mask, col in ((eye_mask, eye_col), (belly_mask, belly_col)):
        out[mask, :3] = col
        out[mask, 3] = 255
    return out, eye_col


def fix_eye_side(out, eye_col):
    old_x = FRAME + EYE_X_FRAME1_OLD
    new_x = FRAME + EYE_X_FRAME0
    if tuple(out[EYE_ROW, old_x, :3]) != tuple(eye_col):
        raise SystemExit("Olho não está onde o esperado no quadro 2 - confira a imagem de origem.")
    out[EYE_ROW, old_x, :3] = out[EYE_ROW, old_x - 1, :3]   # cor da cabeça ao lado
    out[EYE_ROW, new_x, :3] = eye_col


def build_sheet(frames_right, frames_left, scale):
    cell = FRAME * scale
    sheet = Image.new("RGBA", (2 * cell, 2 * cell), (0, 0, 0, 0))
    for row, frames in enumerate((frames_right, frames_left)):
        for col, f in enumerate(frames):
            im = Image.fromarray(f, "RGBA").resize((cell, cell), Image.NEAREST)
            sheet.paste(im, (col * cell, row * cell))
    return sheet


def process(src, out_dir):
    grid = recover_grid(src)
    out, eye_col = clean_palette(grid)
    fix_eye_side(out, eye_col)
    base = out.astype(np.uint8)
    frames_left = [base[:, 0:FRAME], base[:, FRAME:2 * FRAME]]        # arte original: olho à esquerda
    frames_right = [f[:, ::-1] for f in frames_left]                  # espelhada: olho à direita
    os.makedirs(out_dir, exist_ok=True)
    build_sheet(frames_right, frames_left, 1).save(os.path.join(out_dir, "morcego_sheet_24px.png"))
    build_sheet(frames_right, frames_left, 4).save(os.path.join(out_dir, "morcego_sheet_96px.png"))
    print("OK ->", out_dir)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    process(sys.argv[1], sys.argv[2])
