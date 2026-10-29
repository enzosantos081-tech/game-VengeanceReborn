"""
tools/export_sfx.py
Exporta os efeitos sonoros sintetizados (systems/sfx_synth.py) como arquivos
.wav, para você ouvir e comparar fora do jogo (ou mostrar pro grupo).

Uso (rode da pasta raiz do projeto):
    python tools/export_sfx.py              # exporta todos para ./sfx_preview/
    python tools/export_sfx.py boss_slam    # exporta só os que tiverem esse nome
"""

import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings            # noqa: E402
from systems import sfx_synth          # noqa: E402


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    out_dir = "sfx_preview"
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for name, gain, variants, fn in sfx_synth.REGISTRY:
        if only and only not in name:
            continue
        for v in range(variants):
            audio = sfx_synth.finish(sfx_synth._trim_tail(fn(v)), gain)
            suffix = "" if variants == 1 else "_v%d" % v
            path = os.path.join(out_dir, "%s%s.wav" % (name, suffix))
            with wave.open(path, "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(settings.AUDIO_SAMPLE_RATE)
                w.writeframes(audio.tobytes())
            count += 1
    print("%d arquivos .wav em ./%s/" % (count, out_dir))


if __name__ == "__main__":
    main()
