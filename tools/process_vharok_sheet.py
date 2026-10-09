"""
Converte a spritesheet original do Vharok (JPG, fundo liso claro, sem
transparência) em PNG RGBA com fundo transparente.

Uso (ferramenta de desenvolvimento - NÃO é necessária para jogar):
    python tools/process_vharok_sheet.py <entrada.jpg> <saida.png>
Requer Pillow + numpy.

Método: o fundo é uma cor lisa (mediana da imagem). O alfa de cada pixel
é proporcional à distância dele até essa cor (com uma zona de transição
curta para absorver o ruído de compressão JPG) e a cor é "des-misturada"
do fundo, evitando halo claro em volta dos sprites sobre a arena escura.
"""
import sys
import numpy as np
from PIL import Image

LOW, HIGH = 36, 90          # distância L1 (soma dos canais): abaixo de LOW = transparente; acima de HIGH = opaco


def process(src, dst):
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    bg = np.median(a.reshape(-1, 3), axis=0)
    d = np.abs(a - bg).sum(axis=2)
    alpha = np.clip((d - LOW) / (HIGH - LOW), 0.0, 1.0)
    alpha_safe = np.where(alpha > 0, alpha, 1.0)[..., None]
    color = (a - bg * (1.0 - alpha[..., None])) / alpha_safe
    color = np.clip(color, 0, 255)
    out = np.dstack([color, alpha * 255.0]).round().astype(np.uint8)
    out[alpha == 0, :3] = 0
    Image.fromarray(out, "RGBA").save(dst)
    return bg


if __name__ == "__main__":
    print("fundo detectado:", process(sys.argv[1], sys.argv[2]))
