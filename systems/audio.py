"""
systems/audio.py
Responsável pelo áudio do jogo:
  - SoundManager: efeitos sonoros. Como o projeto não tem arquivos de áudio
    de efeitos, TODOS os sons são sintetizados em tempo de execução com
    numpy (veja systems/sfx_synth.py, onde estão as "receitas" de cada som).
    A geração roda numa thread em segundo plano ao abrir o jogo (~4 s): o
    menu aparece na hora e cada som fica disponível assim que é gerado.
    Suporta volume e posição estéreo (pan), usados para sons de inimigos.
  - MusicManager: música de fundo em loop (assets/sounds/).
Se o mixer ou o numpy não estiverem disponíveis, o jogo continua normalmente,
apenas sem som.
"""

import os
import random
import threading
import pygame

from config import settings

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None
    _NUMPY_AVAILABLE = False


class SoundManager:
    SFX_CHANNELS = 24   # sons simultâneos (o padrão do pygame são só 8)

    # Nomes antigos continuam funcionando (compatibilidade com o resto do código).
    ALIASES = {"attack": "attack_base", "coin": "coin_0"}

    def __init__(self):
        self.enabled = False
        self.sounds = {}      # nome -> [pygame.mixer.Sound, ...] (variações)
        self._arrays = {}     # nome -> [array int16, ...] entregues pela thread
        self._last = {}       # última variação tocada de cada som (evita repetir igual)
        self._thread = None
        if not _NUMPY_AVAILABLE:
            # numpy não está instalado: o jogo continua funcionando
            # normalmente, apenas sem efeitos sonoros.
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=settings.AUDIO_SAMPLE_RATE, size=-16, channels=2)
            pygame.mixer.set_num_channels(self.SFX_CHANNELS)
            self.enabled = True
        except (pygame.error, Exception):
            self.enabled = False
            return
        self._thread = threading.Thread(target=self._build_in_background, daemon=True)
        self._thread.start()

    # ---------- Geração ----------
    def _build_in_background(self):
        try:
            from systems import sfx_synth
            sfx_synth.build_all(on_ready=self._store)
        except Exception:
            pass   # sem som é melhor do que travar o jogo

    def _store(self, name, arrays):
        self._arrays[name] = arrays

    def ready(self):
        """True quando todos os sons já foram gerados."""
        return self._thread is None or not self._thread.is_alive()

    def _variants(self, name):
        name = self.ALIASES.get(name, name)
        variants = self.sounds.get(name)
        if variants is None:
            arrays = self._arrays.get(name)
            if arrays is None:
                return name, None   # ainda gerando (ou som inexistente)
            variants = []
            try:
                for arr in arrays:
                    snd = pygame.sndarray.make_sound(arr)   # conversão feita na thread principal
                    snd.set_volume(settings.MASTER_VOLUME)
                    variants.append(snd)
            except Exception:
                variants = []   # formato de áudio incompatível: este som fica mudo
            self.sounds[name] = variants
        return name, variants

    # ---------- Reprodução ----------
    def play(self, name, volume=1.0, pan=0.0):
        """Toca um som. volume: 0 a 1 (multiplica o volume do som).
        pan: -1 (só esquerda) a +1 (só direita). Retorna o canal (ou None)."""
        if not self.enabled or volume <= 0.01:
            return None
        key, variants = self._variants(name)
        if not variants:
            return None
        idx = 0
        if len(variants) > 1:
            choices = [i for i in range(len(variants)) if i != self._last.get(key)]
            idx = random.choice(choices)
            self._last[key] = idx
        channel = variants[idx].play()
        if channel is not None and (volume != 1.0 or pan != 0.0):
            left = volume * (1.0 - max(0.0, pan))
            right = volume * (1.0 - max(0.0, -pan))
            channel.set_volume(min(1.0, left), min(1.0, right))
        return channel

    def stop_all(self):
        """Silencia todos os efeitos que ainda estão tocando."""
        if self.enabled:
            pygame.mixer.stop()


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
