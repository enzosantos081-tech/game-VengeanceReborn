"""
systems/audio.py
Responsável pelos efeitos sonoros. Como o projeto não recebeu nenhum
arquivo de áudio pronto (seção 23 do documento reserva assets/sounds/
para isso), os sons são gerados PROCEDURALMENTE com numpy: ondas simples
(seno/quadrada/ruído) com um envelope curto de ataque/decaimento, o
suficiente para dar feedback de pulo, ataque, dano, moeda, etc. Se o
mixer de áudio não estiver disponível no ambiente (ex.: sem placa de
som), o jogo continua funcionando normalmente e apenas fica mudo.
"""

import math
import pygame

from config import settings

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None
    _NUMPY_AVAILABLE = False


def _envelope(n, attack=0.05, decay=0.6):
    """Curva simples de volume: sobe rápido, desce em decaimento exponencial."""
    t = np.linspace(0, 1, n)
    attack_n = max(1, int(n * attack))
    env = np.ones(n)
    env[:attack_n] = np.linspace(0, 1, attack_n)
    env *= np.exp(-t * (1.0 / max(decay, 0.05)) * 3)
    return env


def _tone(freq, duration, wave="sine", volume=1.0, sweep_to=None, noise_amount=0.0):
    sr = settings.AUDIO_SAMPLE_RATE
    n = max(1, int(sr * duration))
    t = np.linspace(0, duration, n, endpoint=False)

    if sweep_to is not None:
        freqs = np.linspace(freq, sweep_to, n)
        phase = 2 * np.pi * np.cumsum(freqs) / sr
    else:
        phase = 2 * np.pi * freq * t

    if wave == "square":
        wav = np.sign(np.sin(phase))
    elif wave == "triangle":
        wav = 2 * np.abs(2 * ((phase / (2 * np.pi)) % 1) - 1) - 1
    else:
        wav = np.sin(phase)

    if noise_amount > 0:
        noise = np.random.uniform(-1, 1, n)
        wav = wav * (1 - noise_amount) + noise * noise_amount

    wav *= _envelope(n)
    wav *= volume * settings.MASTER_VOLUME
    wav = np.clip(wav, -1, 1)
    pcm = (wav * 32767).astype(np.int16)
    stereo = np.repeat(pcm.reshape(-1, 1), 2, axis=1)
    return np.ascontiguousarray(stereo)


class SoundManager:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        if not _NUMPY_AVAILABLE:
            # numpy não está instalado: o jogo continua funcionando
            # normalmente, apenas sem efeitos sonoros.
            return
        try:
            pygame.mixer.init(frequency=settings.AUDIO_SAMPLE_RATE, size=-16, channels=2)
            self._build_sounds()
            self.enabled = True
        except (pygame.error, Exception):
            self.enabled = False

    def _build_sounds(self):
        specs = {
            "jump": _tone(420, 0.12, wave="triangle", volume=0.6, sweep_to=680),
            "attack": _tone(200, 0.08, wave="square", volume=0.5, sweep_to=90),
            "hit": _tone(140, 0.09, wave="square", volume=0.6, noise_amount=0.3),
            "coin": _tone(900, 0.10, wave="sine", volume=0.5, sweep_to=1400),
            "damage": _tone(160, 0.18, wave="square", volume=0.7, sweep_to=60, noise_amount=0.2),
            "checkpoint": _tone(500, 0.22, wave="sine", volume=0.55, sweep_to=900),
            "death": _tone(300, 0.5, wave="triangle", volume=0.7, sweep_to=40),
            "boss_slam": _tone(90, 0.28, wave="square", volume=0.8, noise_amount=0.4),
            "boss_barrage": _tone(600, 0.15, wave="square", volume=0.45, sweep_to=1100, noise_amount=0.2),
            "victory": _tone(523, 0.5, wave="sine", volume=0.6, sweep_to=1046),
            "menu_move": _tone(300, 0.05, wave="square", volume=0.3),
            "menu_select": _tone(500, 0.09, wave="sine", volume=0.45, sweep_to=750),
            "purchase": _tone(700, 0.14, wave="sine", volume=0.5, sweep_to=1050),
            "denied": _tone(150, 0.10, wave="square", volume=0.4),
            "dash": _tone(250, 0.10, wave="triangle", volume=0.5, sweep_to=520),
        }
        for name, array in specs.items():
            self.sounds[name] = pygame.sndarray.make_sound(array)

    def play(self, name):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.play()
