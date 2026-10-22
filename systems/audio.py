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
import os
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


def _trim_for_loop(sound):
    """Corta o silêncio do começo/fim de uma música para o loop emendar sem
    pausa. Precisa de numpy; sem ele (ou se algo falhar) devolve o som original."""
    if not _NUMPY_AVAILABLE:
        return sound
    try:
        arr = pygame.sndarray.array(sound)
        sample_rate = pygame.mixer.get_init()[0]
        level = np.abs(arr.astype(np.int32))
        if level.ndim > 1:
            level = level.max(axis=1)
        loud = np.where(level > settings.MUSIC_TRIM_THRESHOLD)[0]
        if loud.size == 0:
            return sound

        min_trim = int(sample_rate * settings.MUSIC_TRIM_MIN_MS / 1000)
        start = int(loud[0]) if loud[0] >= min_trim else 0
        end = int(loud[-1]) + 1 if (len(arr) - 1 - loud[-1]) >= min_trim else len(arr)
        if start == 0 and end == len(arr):
            return sound  # já emenda bem (ex.: o wav do boss)

        data = arr[start:end].astype(np.float32)
        fade = max(1, int(sample_rate * settings.MUSIC_LOOP_FADE_MS / 1000))
        fade = min(fade, len(data) // 2)
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        if data.ndim > 1:
            ramp = ramp.reshape(-1, 1)
        if start > 0:
            data[:fade] *= ramp
        if end < len(arr):
            data[-fade:] *= ramp[::-1]
        data = np.ascontiguousarray(np.clip(data, -32768, 32767).astype(np.int16))
        return pygame.sndarray.make_sound(data)
    except Exception:
        return sound


class MusicManager:
    """Música de fundo em loop. Cada música é carregada na memória uma vez
    (no início do jogo) e toca num canal reservado do mixer, o que dá loop
    sample-a-sample, sem o 'clique/pausa' que o pygame.mixer.music tem em mp3.
    Se o mixer ou os arquivos não existirem, o jogo continua normalmente, mudo."""

    CHANNEL_ID = 0  # canal reservado: os efeitos sonoros nunca usam este

    def __init__(self):
        self.enabled = False
        self.current = None
        self.tracks = {}
        self.channel = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=settings.AUDIO_SAMPLE_RATE, size=-16, channels=2)
            pygame.mixer.set_reserved(self.CHANNEL_ID + 1)
            self.channel = pygame.mixer.Channel(self.CHANNEL_ID)
            self.enabled = True
        except pygame.error:
            return
        self._load_tracks()

    def _load_tracks(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        folder = os.path.join(base, "assets", "sounds")
        for key, filename in settings.MUSIC_FILES.items():
            path = os.path.join(folder, filename)
            if not os.path.isfile(path):
                continue
            try:
                sound = _trim_for_loop(pygame.mixer.Sound(path))
                sound.set_volume(settings.MUSIC_VOLUME)
                self.tracks[key] = sound
            except pygame.error:
                pass

    def play(self, key):
        """Começa a música `key` ('level' ou 'boss') em loop. Se já é a que
        está tocando, não faz nada (não reinicia)."""
        if not self.enabled or key == self.current:
            return
        sound = self.tracks.get(key)
        if sound is None:
            return
        self.channel.play(sound, loops=-1, fade_ms=settings.MUSIC_FADE_MS)
        self.current = key

    def stop(self):
        if self.enabled:
            self.channel.stop()
        self.current = None

    def pause(self):
        if self.enabled:
            self.channel.pause()

    def unpause(self):
        if self.enabled:
            self.channel.unpause()
