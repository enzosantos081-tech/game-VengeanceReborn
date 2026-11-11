"""
screens/cutscene.py
Toca um vídeo (mp4/webm/...) em tela cheia como cutscene, com áudio, e avisa
quando termina. O jogo fica parado enquanto isso (estado STATE_BOSS_INTRO em
core/game.py) e volta ao normal quando o vídeo acaba ou é pulado.

Como funciona:
- Vídeo: lido quadro a quadro com OpenCV (cv2) e desenhado com pygame. O
  quadro mostrado é escolhido pelo relógio (tempo decorrido), então o vídeo
  não "atrasa" se o jogo engasgar: quadros atrasados são descartados.
- Áudio: extraído uma vez para um .wav temporário com o ffmpeg que vem no
  pacote imageio-ffmpeg (ou um ffmpeg instalado no sistema) e tocado pelo
  pygame.mixer.

Dependências opcionais (requirements.txt): opencv-python, imageio-ffmpeg. Sem elas, toca
os quadros pré-extraídos em assets/cutscenes/boss_intro_frames/ + boss_intro.ogg (só pygame).
Se o arquivo do vídeo ou as bibliotecas não existirem, start() devolve False
e o jogo simplesmente segue sem a cutscene (nunca quebra).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import pygame

from config import settings

try:
    import cv2
except ImportError:          # sem OpenCV: a cutscene é pulada
    cv2 = None

FADE_SECONDS = 0.5           # escurece no começo e no fim do vídeo
SKIP_HINT_DELAY = 1.0        # s até aparecer "ENTER - pular"
FRAMES_FPS = 24.0            # taxa dos quadros pré-extraídos (modo sem OpenCV)


def _ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def _extract_audio(video_path):
    """Extrai o áudio do vídeo para um .wav temporário (com cache).
    Devolve o caminho do .wav ou None (vídeo sem áudio / ffmpeg ausente)."""
    exe = _ffmpeg_exe()
    if not exe:
        return None
    stamp = int(os.path.getmtime(video_path))
    name = f"vengeance_{os.path.splitext(os.path.basename(video_path))[0]}_{stamp}.wav"
    wav_path = os.path.join(tempfile.gettempdir(), name)
    if os.path.isfile(wav_path) and os.path.getsize(wav_path) > 1024:
        return wav_path
    cmd = [exe, "-y", "-loglevel", "error", "-i", video_path, "-vn",
           "-acodec", "pcm_s16le", "-ar", str(settings.AUDIO_SAMPLE_RATE), "-ac", "2", wav_path]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        subprocess.run(cmd, check=True, timeout=120, creationflags=flags,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    if os.path.isfile(wav_path) and os.path.getsize(wav_path) > 1024:
        return wav_path
    return None


class VideoCutscene:
    def __init__(self, path):
        self.path = path
        self.cap = None
        self.fps = 30.0
        self.total_frames = 0
        self.duration = 0.0
        self.frame_idx = -1          # índice do último quadro lido
        self.surface = None          # último quadro já convertido p/ pygame
        self.dest = None             # onde desenhar (vídeo centralizado, sem distorcer)
        self.start_ms = 0
        self.audio = None
        self.audio_channel = None
        self.finished = False
        self._hint_font = None
        self.frame_files = []        # modo sem OpenCV: lista de .jpg pré-extraídos
        self.frames_mode = False

    # ---------- Ciclo de vida ----------
    def start(self):
        """Abre o vídeo e começa a tocar. Devolve False se não der (arquivo
        ausente, OpenCV não instalado, vídeo ilegível)."""
        # Sem OpenCV (ou se ele não abrir o vídeo), usa os quadros .jpg
        # pré-extraídos em <nome>_frames/ - assim só o pygame é necessário.
        if cv2 is None:
            print("[cutscene] OpenCV não instalado; usando os quadros pré-extraídos.")
            return self._start_frames()
        if not os.path.isfile(self.path):
            print(f"[cutscene] vídeo não encontrado: {self.path}; tentando quadros.")
            return self._start_frames()
        cap = cv2.VideoCapture(self.path)
        if not cap.isOpened():
            print(f"[cutscene] não consegui abrir o vídeo: {self.path}; tentando quadros.")
            return self._start_frames()
        self.cap = cap
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.duration = self.total_frames / self.fps if self.total_frames else 0.0

        w = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or settings.SCREEN_WIDTH
        h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or settings.SCREEN_HEIGHT
        scale = min(settings.SCREEN_WIDTH / w, settings.SCREEN_HEIGHT / h)
        size = (max(1, round(w * scale)), max(1, round(h * scale)))
        self.dest = pygame.Rect((0, 0), size)
        self.dest.center = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2)

        self._start_audio()
        self.start_ms = pygame.time.get_ticks()
        return True

    def _start_frames(self):
        """Modo sem OpenCV: toca os quadros <nome>_frames/*.jpg + <nome>.ogg."""
        base = os.path.splitext(self.path)[0]
        folder = base + "_frames"
        if not os.path.isdir(folder):
            print(f"[cutscene] pasta de quadros não encontrada: {folder}; cutscene ignorada.")
            return False
        files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png")))
        if not files:
            print(f"[cutscene] pasta de quadros vazia: {folder}; cutscene ignorada.")
            return False
        self.frame_files = [os.path.join(folder, f) for f in files]
        self.frames_mode = True
        self.fps = FRAMES_FPS
        self.total_frames = len(self.frame_files)
        self.duration = self.total_frames / self.fps
        first = pygame.image.load(self.frame_files[0])
        w, h = first.get_size()
        scale = min(settings.SCREEN_WIDTH / w, settings.SCREEN_HEIGHT / h)
        self.dest = pygame.Rect((0, 0), (max(1, round(w * scale)), max(1, round(h * scale))))
        self.dest.center = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2)
        self._start_audio()
        self.start_ms = pygame.time.get_ticks()
        return True

    def _start_audio(self):
        if not pygame.mixer.get_init():
            return
        pre = os.path.splitext(self.path)[0] + ".ogg"
        wav = pre if os.path.isfile(pre) else _extract_audio(self.path)
        if not wav:
            return
        try:
            self.audio = pygame.mixer.Sound(wav)
            self.audio.set_volume(settings.BOSS_INTRO_VOLUME)
            self.audio_channel = self.audio.play()
        except pygame.error:
            self.audio = None

    def stop(self):
        if self.audio_channel is not None:
            self.audio_channel.stop()
        elif self.audio is not None:
            self.audio.stop()
        self.audio = None
        self.audio_channel = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.finished = True

    # ---------- Loop ----------
    def elapsed(self):
        return (pygame.time.get_ticks() - self.start_ms) / 1000.0

    def update(self, skip=False):
        """Avança o vídeo conforme o relógio. Devolve True quando acabou
        (ou foi pulado)."""
        if self.finished or (self.cap is None and not self.frames_mode):
            return True
        if skip:
            self.stop()
            return True

        if self.frames_mode:
            idx = int(self.elapsed() * self.fps)
            if idx >= self.total_frames:
                self.stop()
                return True
            if idx != self.frame_idx:
                self.frame_idx = idx
                try:
                    img = pygame.image.load(self.frame_files[idx]).convert()
                    self.surface = pygame.transform.smoothscale(img, self.dest.size)
                except pygame.error:
                    pass
            return False

        target = int(self.elapsed() * self.fps)
        grabbed_any = False
        while self.frame_idx < target:
            if not self.cap.grab():          # acabou o vídeo
                self.stop()
                return True
            self.frame_idx += 1
            grabbed_any = True
        if grabbed_any:
            ok, frame = self.cap.retrieve()
            if ok:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = rgb.shape[:2]
                surf = pygame.image.frombuffer(rgb.tobytes(), (w, h), "RGB")
                self.surface = pygame.transform.smoothscale(surf, self.dest.size)
        return False

    def draw(self, screen):
        screen.fill((0, 0, 0))
        if self.surface is not None:
            screen.blit(self.surface, self.dest)

        # Fade preto no começo e no fim.
        t = self.elapsed()
        fade = 0.0
        if t < FADE_SECONDS:
            fade = 1.0 - t / FADE_SECONDS
        elif self.duration and t > self.duration - FADE_SECONDS:
            fade = min(1.0, (t - (self.duration - FADE_SECONDS)) / FADE_SECONDS)
        if fade > 0:
            veil = pygame.Surface(screen.get_size())
            veil.set_alpha(int(255 * fade))
            screen.blit(veil, (0, 0))

        if t > SKIP_HINT_DELAY:
            if self._hint_font is None:
                self._hint_font = pygame.font.Font(None, 22)
            hint = self._hint_font.render("ENTER / ESPAÇO / ESC  -  pular", True, (200, 200, 205))
            hint.set_alpha(150)
            screen.blit(hint, hint.get_rect(bottomright=(settings.SCREEN_WIDTH - 20,
                                                         settings.SCREEN_HEIGHT - 14)))
