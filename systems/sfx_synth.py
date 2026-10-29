"""
systems/sfx_synth.py
Sintetizador dos efeitos sonoros de Vengeance Reborn. TUDO é gerado em
tempo de execução com numpy (nenhum arquivo de áudio): osciladores aditivos,
FM, sinos inarmônicos, ruído colorido, filtros por FFT, filtro "varrido"
(whoosh), reverb por convolução, saturação e estéreo.

Este módulo não depende do pygame: ele só devolve arrays int16 estéreo
(n, 2). Quem toca os sons é o systems/audio.py (SoundManager).

Direção sonora (tema do jogo): fantasia sombria. Aço frio e pesado, pedra e
eco de castelo em ruínas, o vermelho do Abismo (graves, dissonância, brasa)
contra o azul cristalino do Núcleo do Retorno (sinos de vidro, brilho).

Para adicionar um som novo: escreva uma função e decore com
@sound("nome", ganho, variantes). O ganho (0 a 1) é o volume relativo do
som; as variantes são versões levemente diferentes sorteadas ao tocar
(evita o efeito "metralhadora" de ouvir o mesmo arquivo repetido).
"""

import zlib
import numpy as np

from config import settings

SR = settings.AUDIO_SAMPLE_RATE
TWO_PI = 2.0 * np.pi


# =====================================================================
# Utilidades básicas
# =====================================================================
def _n(sec):
    return max(1, int(round(sec * SR)))


def _tt(n):
    return np.arange(n) / SR


def _rng(name, variant=0):
    """Gerador aleatório determinístico: o mesmo som sai igual a cada execução."""
    return np.random.default_rng(zlib.crc32(name.encode("utf-8")) + 7919 * variant)


def _glide(a, b, n):
    """Glissando exponencial (soa linear para o ouvido) de a até b."""
    return a * (b / a) ** np.linspace(0.0, 1.0, n)


def _semi(step):
    return 2.0 ** (step / 12.0)


# =====================================================================
# Envelopes
# =====================================================================
def _env(n, a=0.003, tau=0.1, hold=0.0, tail=0.004):
    """Ataque suave -> sustenta `hold` s -> decaimento exponencial (tau)."""
    t = _tt(n)
    att = np.clip(t / max(a, 1e-4), 0.0, 1.0)
    att = att * att * (3 - 2 * att)
    dec = np.exp(-np.maximum(t - a - hold, 0.0) / max(tau, 1e-4))
    e = att * dec
    k = min(n, _n(tail))
    e[-k:] *= np.linspace(1.0, 0.0, k)
    return e


def _swell(n, peak=0.5, power=2.0):
    """Sobe até `peak` (fração do tempo) e desce, em forma de sino."""
    x = np.linspace(0.0, 1.0, n)
    left = np.clip(x / max(peak, 1e-3), 0, 1) ** power
    right = np.clip((1 - x) / max(1 - peak, 1e-3), 0, 1) ** power
    return np.minimum(left, right)


# =====================================================================
# Osciladores
# =====================================================================
def _phase(freq, n):
    f = freq if np.ndim(freq) else np.full(n, float(freq))
    return TWO_PI * np.cumsum(f.astype(np.float64)) / SR


_TABLES = {}
_TABLE_N = 4096


def _table(kind, K):
    """Tabela de onda (um ciclo) limitada a K harmônicos; gerada uma vez só."""
    key = (kind, K)
    if key not in _TABLES:
        x = np.arange(_TABLE_N) / _TABLE_N * TWO_PI
        tab = np.zeros(_TABLE_N)
        for k in range(1, K + 1):
            if kind == "saw":
                tab += np.sin(k * x) / k
            elif kind == "square" and k % 2 == 1:
                tab += np.sin(k * x) / k
            elif kind == "tri" and k % 2 == 1:
                tab += (1 if ((k - 1) // 2) % 2 == 0 else -1) * np.sin(k * x) / k ** 2
        tab /= np.max(np.abs(tab))
        _TABLES[key] = np.append(tab, tab[0])
    return _TABLES[key]


def _osc(kind, freq, n, K):
    """Oscilador por tabela com interpolação. K é reduzido automaticamente
    para o agudo mais alto da nota não gerar aliasing."""
    f = freq if np.ndim(freq) else np.full(n, float(freq))
    fmax = max(float(np.max(f)), 20.0)
    K = int(max(1, min(K, 0.45 * SR / fmax)))
    tab = _table(kind, K)
    ph = (np.cumsum(f.astype(np.float64)) / SR) % 1.0
    pos = ph * _TABLE_N
    i0 = pos.astype(np.int64)
    fr = pos - i0
    return tab[i0] * (1.0 - fr) + tab[i0 + 1] * fr


def sine(freq, n):
    return np.sin(_phase(freq, n))


def saw(freq, n, K=32):
    return _osc("saw", freq, n, K)


def square(freq, n, K=32):
    return _osc("square", freq, n, K)


def tri(freq, n, K=12):
    return _osc("tri", freq, n, K)


def bell(freq, dur, partials=None, tau=0.25, bright=1.0):
    """Sino/metal: parciais inarmônicas com decaimentos diferentes."""
    if partials is None:
        partials = ((1.0, 1.0, 1.0), (2.76, 0.55, 0.65), (5.40, 0.30, 0.40),
                    (8.93, 0.16, 0.28))
    n = _n(dur)
    t = _tt(n)
    out = np.zeros(n)
    for ratio, amp, dscale in partials:
        if freq * ratio > 0.45 * SR:
            continue
        a = amp * (bright if ratio > 1.5 else 1.0)
        out += a * np.sin(TWO_PI * freq * ratio * t) * np.exp(-t / (tau * dscale))
    att = np.clip(t / 0.0012, 0, 1)
    k = min(n, _n(min(0.03, dur * 0.25)))
    rel = np.ones(n)
    rel[-k:] = np.linspace(1.0, 0.0, k) ** 2
    return out * att * rel


def fm(carrier, ratio, index, dur, tau=0.2):
    """FM simples (timbre metálico/cristalino)."""
    n = _n(dur)
    t = _tt(n)
    idx = index * np.exp(-t / tau)
    return np.sin(TWO_PI * carrier * t + idx * np.sin(TWO_PI * carrier * ratio * t))


# =====================================================================
# Ruído e filtros (por FFT)
# =====================================================================
def noise(n, rng, color="white"):
    x = rng.standard_normal(n)
    if color != "white":
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(n, 1.0 / SR)
        f[0] = f[1] if len(f) > 1 else 1.0
        X *= f ** (-0.5 if color == "pink" else -1.0)
        x = np.fft.irfft(X, n)
    s = np.std(x)
    return x / s if s > 0 else x


def _filter(x, resp):
    n = len(x)
    N = 1 << int(np.ceil(np.log2(max(n, 16))))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1.0 / SR)
    return np.fft.irfft(X * resp(f), N)[:n]


def lp(x, fc, order=2):
    return _filter(x, lambda f: 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order)))


def hp(x, fc, order=2):
    def r(f):
        g = np.zeros_like(f)
        nz = f > 0
        g[nz] = 1.0 / np.sqrt(1.0 + (fc / f[nz]) ** (2 * order))
        return g
    return _filter(x, r)


def bp(x, f1, f2, order=2):
    return lp(hp(x, f1, order), f2, order)


def resonant(x, fc, q=4.0):
    """Passa-banda ressonante em torno de fc (som de 'voz'/corpo)."""
    def r(f):
        g = np.zeros_like(f)
        nz = f > 0
        g[nz] = 1.0 / np.sqrt(1.0 + (q * (f[nz] / fc - fc / f[nz])) ** 2)
        return g
    return _filter(x, r)


def sweep_bp(x, fc, q=2.0, B=1024):
    """Passa-banda cuja frequência central varia no tempo (efeito whoosh).
    fc: array (um valor por amostra). Processa em blocos com overlap-add."""
    n = len(x)
    hop = B // 2
    w = 0.5 - 0.5 * np.cos(TWO_PI * np.arange(B) / B)
    xp = np.pad(x, (B, B))
    out = np.zeros(len(xp))
    f = np.fft.rfftfreq(B, 1.0 / SR)
    nz = f > 0
    for s in range(0, len(xp) - B, hop):
        idx = min(max(s + B // 2 - B, 0), n - 1)
        c = max(float(fc[idx]), 30.0)
        h = np.zeros_like(f)
        h[nz] = 1.0 / np.sqrt(1.0 + (q * (f[nz] / c - c / f[nz])) ** 2)
        out[s:s + B] += np.fft.irfft(np.fft.rfft(xp[s:s + B] * w) * h, B)
    return out[B:B + n]


def sat(x, drive=2.0):
    """Saturação (distorção suave) para sons agressivos/graves."""
    return np.tanh(x * drive) / np.tanh(drive)


def clicks(n, rng, density, decay=0.002, tone=None):
    """Estalos/faíscas: impulsos aleatórios (density = estalos por segundo)."""
    out = np.zeros(n)
    count = max(1, int(density * n / SR))
    pos = rng.integers(0, n, count)
    amp = rng.uniform(0.3, 1.0, count) * rng.choice([-1, 1], count)
    out[pos] = amp
    k = _n(decay * 6)
    kern = np.exp(-np.arange(k) / (decay * SR))
    out = np.convolve(out, kern)[:n]
    if tone:
        out = hp(out, tone, 1)
    return out


# =====================================================================
# Reverb (convolução com resposta ao impulso sintética) e mixagem
# =====================================================================
_IR_CACHE = {}


def _impulse(t60, seed, damp):
    key = (round(t60, 2), seed, int(damp))
    if key not in _IR_CACHE:
        n = _n(t60 * 1.05)
        r = np.random.default_rng(9000 + seed)
        t = _tt(n)
        ir = r.standard_normal(n) * np.exp(-6.9 * t / t60)
        ir = lp(ir, damp, 1)
        pre = _n(0.007)
        ir[:pre] = 0.0
        for ms, g in ((11, 0.8), (17, 0.6), (26, 0.5), (37, 0.4)):
            i = _n(ms / 1000.0 * (1.0 + 0.07 * seed))
            if i < n:
                ir[i] += g * np.max(np.abs(ir)) * 0.9
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        _IR_CACHE[key] = ir
    return _IR_CACHE[key]


def reverb(x, t60=0.8, wet=0.3, damp=4500):
    """x: estéreo (n,2). Devolve estéreo com cauda (mais longo que x)."""
    n = len(x)
    irl, irr = _impulse(t60, 1, damp), _impulse(t60, 2, damp)
    m = len(irl)
    N = 1 << int(np.ceil(np.log2(n + m)))
    out = np.zeros((n + m, 2))
    out[:n] += x
    for c, ir in ((0, irl), (1, irr)):
        w = np.fft.irfft(np.fft.rfft(x[:, c], N) * np.fft.rfft(ir, N), N)[:n + m]
        out[:, c] += wet * w
    return out


class Mix:
    """Mesa de mixagem simples: soma sinais (mono ou estéreo) com tempo/pan."""

    def __init__(self, dur):
        self.n = _n(dur)
        self.buf = np.zeros((self.n, 2))

    def add(self, sig, t=0.0, gain=1.0, pan=0.0):
        s = np.asarray(sig, dtype=np.float64)
        if s.ndim == 1:
            a = (pan + 1.0) * np.pi / 4.0
            s = np.stack([s * np.cos(a), s * np.sin(a)], axis=1) * 1.41
        i = _n(t) if t > 0 else 0
        j = min(self.n, i + len(s))
        if j > i:
            seg = s[:j - i] * gain
            k = min(len(seg), _n(0.006))
            if k > 1:
                seg = seg.copy()
                seg[-k:] *= np.linspace(1.0, 0.0, k)[:, None]
            self.buf[i:j] += seg
        return self

    def out(self):
        return self.buf


def widen(x, ms=9.0, mix=0.5):
    """Dá largura estéreo a um sinal mono (pequeno atraso entre os lados)."""
    d = _n(ms / 1000.0)
    l = x.copy()
    r = np.concatenate([np.zeros(d), x])[:len(x)]
    return np.stack([l * (1 - mix * 0.5) + r * mix * 0.5,
                     r * (1 - mix * 0.5) + l * mix * 0.5], axis=1)


def finish(buf, gain=0.8, fade_out=0.012):
    """Normaliza o volume percebido, limita picos, tira DC/subgrave e converte."""
    buf = np.asarray(buf, dtype=np.float64)
    for c in range(2):
        buf[:, c] = hp(buf[:, c], 22.0, 2)
    ref = np.percentile(np.abs(buf), 99.6)
    if ref < 1e-9:
        return np.zeros((len(buf), 2), dtype=np.int16)
    buf = np.tanh(buf * (0.62 / ref))            # compressão suave de picos
    buf /= max(np.max(np.abs(buf)), 1e-9)
    fi, fo = _n(0.0007), min(len(buf), _n(fade_out))
    buf[:fi] *= np.linspace(0.0, 1.0, fi)[:, None]
    buf[-fo:] *= np.linspace(1.0, 0.0, fo)[:, None]
    return np.ascontiguousarray((buf * gain * 32767).astype(np.int16))


def _trim_tail(buf, thresh=0.004):
    """Corta o silêncio no fim (caudas de reverb ficam sem 'arrasto' inútil)."""
    a = np.max(np.abs(buf), axis=1)
    idx = np.where(a > thresh * np.max(a))[0]
    if len(idx) == 0:
        return buf
    return buf[:min(len(buf), idx[-1] + _n(0.03))]


# =====================================================================
# Registro de sons
# =====================================================================
REGISTRY = []   # (nome, ganho, variantes, função). A ORDEM = prioridade de geração.


def sound(name, gain=0.8, variants=1):
    def deco(fn):
        REGISTRY.append((name, gain, variants, fn))
        return fn
    return deco


# =====================================================================
# KAEL: movimento
# =====================================================================
@sound("jump", 0.50, 3)
def _jump(v):
    r = _rng("jump", v)
    d = 0.18
    n = _n(d)
    f0 = 230 * (1 + 0.07 * (v - 1))
    m = Mix(d)
    m.add(tri(_glide(f0, f0 * 1.9, n), n) * _env(n, 0.004, 0.06), 0, 0.35)
    air = sweep_bp(noise(n, r), _glide(500, 1900, n), 1.3) * _env(n, 0.012, 0.05)
    m.add(air, 0, 0.9)
    m.add(lp(noise(n, r, "pink"), 700) * _env(n, 0.002, 0.03), 0, 0.5)   # roçar de capa/couro
    return m.out()


@sound("double_jump", 0.55, 2)
def _double_jump(v):
    r = _rng("double_jump", v)
    d = 0.5
    m = Mix(d)
    n = _n(0.2)
    air = sweep_bp(noise(n, r), _glide(700, 4200, n), 1.6) * _env(n, 0.01, 0.07)
    m.add(air, 0, 0.8)
    m.add(tri(_glide(300, 620, n), n) * _env(n, 0.003, 0.07), 0, 0.3)
    base = 880 * (1 + 0.04 * v)
    for i, ratio in enumerate((1.0, 1.5, 2.0, 3.0)):
        ping = bell(base * ratio, 0.3, tau=0.09, partials=((1, 1, 1), (2.0, 0.3, 0.5)))
        m.add(ping, 0.035 * i, 0.30 / (1 + 0.25 * i), pan=(-0.3 + 0.2 * i))
    return reverb(m.out(), 0.5, 0.25)


@sound("land_soft", 0.45, 2)
def _land_soft(v):
    r = _rng("land_soft", v)
    d = 0.16
    n = _n(d)
    m = Mix(d)
    m.add(sine(_glide(125 - 8 * v, 55, n), n) * _env(n, 0.002, 0.045), 0, 0.9)
    m.add(lp(noise(n, r), 900 + 200 * v) * _env(n, 0.001, 0.022), 0, 0.7)
    return m.out()


@sound("land_hard", 0.70, 2)
def _land_hard(v):
    r = _rng("land_hard", v)
    d = 0.4
    n = _n(d)
    m = Mix(d)
    m.add(sine(_glide(105, 38, n), n) * _env(n, 0.002, 0.11), 0, 1.0)
    m.add(lp(noise(n, r), 1600) * _env(n, 0.001, 0.05), 0, 0.9)
    m.add(clicks(n, r, 180, 0.0015, 1500) * _env(n, 0.001, 0.07), 0.01, 0.5)   # cascalho
    m.add(sat(sine(_glide(60, 30, n), n), 2.5) * _env(n, 0.004, 0.14), 0, 0.5)
    return reverb(m.out(), 0.35, 0.15, 3000)


# =====================================================================
# KAEL: ataque com cada espada (o timbre acompanha a espada equipada)
# =====================================================================
def _swing(name, v, fc0, fc1, q, d, peak, whoosh=1.0):
    r = _rng(name, v)
    n = _n(d)
    fc = _glide(fc0, fc1, n)
    sw = sweep_bp(noise(n, r), fc, q) * _swell(n, peak, 1.6) * np.exp(-np.linspace(0, 1, n) * 1.6)
    return r, n, sw * whoosh


@sound("attack_base", 0.55, 2)
def _attack_base(v):
    r, n, sw = _swing("attack_base", v, 700, 2800, 1.1, 0.22, 0.30)
    m = Mix(0.25)
    m.add(sw, 0, 1.0)
    m.add(lp(noise(n, r, "pink"), 500) * _env(n, 0.01, 0.05), 0, 0.3)
    return m.out()


@sound("attack_survivor", 0.60, 3)
def _attack_survivor(v):
    # Aço simples: assobio de lâmina + "shing" metálico curto.
    r, n, sw = _swing("attack_survivor", v, 900, 3800, 1.3, 0.24, 0.30)
    m = Mix(0.4)
    m.add(sw, 0, 1.0)
    f = 3300 * (1 + 0.05 * (v - 1))
    m.add(bell(f, 0.2, tau=0.07, partials=((1, 1, 1), (1.51, 0.6, 0.8), (2.2, 0.3, 0.5))), 0.06, 0.20)
    m.add(lp(noise(n, r), 800) * _env(n, 0.005, 0.04), 0.0, 0.25)
    return m.out()


@sound("attack_shadow", 0.60, 3)
def _attack_shadow(v):
    # Lâmina Sombria: whoosh grave e "sussurro" que bebe a luz.
    r, n, sw = _swing("attack_shadow", v, 260, 1500, 0.9, 0.27, 0.35)
    m = Mix(0.42)
    m.add(sw, 0, 1.2)
    m.add(sine(_glide(110, 55, n), n) * _env(n, 0.02, 0.1), 0, 0.5)
    whisper = hp(noise(n, r), 3500) * _swell(n, 0.5, 2) * 0.35
    m.add(whisper, 0.02, 0.5, pan=0.3)
    m.add(sine(_glide(1500, 640, n), n) * _env(n, 0.02, 0.09), 0.03, 0.12)   # "sugar" a luz
    return reverb(m.out(), 0.4, 0.18, 3500)


@sound("attack_abyss", 0.70, 3)
def _attack_abyss(v):
    # Espada do Abismo: pesada, brasa vermelha estalando.
    r, n, sw = _swing("attack_abyss", v, 180, 1000, 0.8, 0.30, 0.30)
    m = Mix(0.5)
    m.add(sat(sw, 1.6), 0, 1.3)
    m.add(sat(saw(_glide(150, 80, n), n), 3) * _env(n, 0.01, 0.12) * 0.25, 0, 0.8)
    m.add(sine(_glide(90, 45, n), n) * _env(n, 0.002, 0.08), 0.0, 0.8)
    m.add(clicks(n, r, 260, 0.0012, 2200) * _env(n, 0.01, 0.12), 0.05, 0.55)   # brasas
    return reverb(m.out(), 0.45, 0.18, 3000)


@sound("attack_fallen_king", 0.70, 3)
def _attack_fallen_king(v):
    # Lâmina do Rei Caído: golpe real, sino dourado e metal de coroa.
    r, n, sw = _swing("attack_fallen_king", v, 500, 2600, 1.0, 0.28, 0.32)
    m = Mix(0.9)
    m.add(sw, 0, 1.1)
    base = 523.25 * (1 + 0.03 * (v - 1))
    m.add(bell(base, 0.8, tau=0.34, partials=((1, 1, 1), (2.0, 0.5, 0.8), (3.0, 0.35, 0.6), (4.2, 0.2, 0.4))),
          0.07, 0.30)
    m.add(lp(saw(220 * _semi(v), n), 900) * _swell(n, 0.4, 1.5) * 0.22, 0.02, 1.0)
    m.add(lp(noise(n, r), 1000) * _env(n, 0.004, 0.04), 0, 0.2)
    return reverb(m.out(), 0.7, 0.22, 4500)


# =====================================================================
# KAEL: dash, dano, morte, retorno
# =====================================================================
@sound("dash", 0.60, 2)
def _dash(v):
    r = _rng("dash", v)
    d = 0.3
    n = _n(d)
    m = Mix(d)
    fc = np.concatenate([_glide(350, 2800, n // 2), _glide(2800, 700, n - n // 2)])
    sw = sweep_bp(noise(n, r), fc, 1.4) * _swell(n, 0.35, 1.5)
    m.add(sw, 0, 1.0)
    m.add(sine(_glide(140, 60, n), n) * _env(n, 0.002, 0.07), 0, 0.5)
    flutter = bp(noise(n, r), 600, 1300) * (0.5 + 0.5 * np.sin(TWO_PI * 52 * _tt(n))) * _env(n, 0.02, 0.1)
    m.add(flutter, 0.01, 0.3, pan=-0.2)
    return m.out()


@sound("dash_ready", 0.25, 1)
def _dash_ready(v):
    m = Mix(0.3)
    m.add(bell(1318.5, 0.22, tau=0.05, partials=((1, 1, 1), (2.0, 0.3, 0.6))), 0.0, 0.6, -0.2)
    m.add(bell(1760.0, 0.22, tau=0.05, partials=((1, 1, 1), (2.0, 0.3, 0.6))), 0.07, 0.6, 0.2)
    return m.out()


@sound("damage", 0.90, 2)
def _damage(v):
    r = _rng("damage", v)
    d = 0.55
    n = _n(d)
    m = Mix(d)
    m.add(sine(_glide(115, 42, n), n) * _env(n, 0.002, 0.09), 0, 1.0)
    m.add(bp(noise(n, r), 250, 3200) * _env(n, 0.001, 0.04), 0, 0.9)
    m.add(sat(saw(_glide(210, 100, n), n), 4) * _env(n, 0.004, 0.11) * 0.5, 0, 0.8)
    m.add(lp(saw(_glide(310, 150, n), n), 1200) * _env(n, 0.004, 0.09), 0, 0.3)          # trítono dissonante
    t = _tt(n)
    m.add(np.sin(TWO_PI * 3100 * t) * np.exp(-t / 0.22) * 0.5, 0.01, 0.06)                # zumbido no ouvido
    return reverb(m.out(), 0.35, 0.15, 3500)


@sound("spike", 0.65, 2)
def _spike(v):
    r = _rng("spike", v)
    d = 0.3
    n = _n(d)
    m = Mix(d)
    m.add(bell(2300 * _semi(v), 0.15, tau=0.045, partials=((1, 1, 1), (1.6, 0.6, 0.8), (2.4, 0.4, 0.6))), 0, 0.5)
    m.add(bp(noise(n, r), 900, 6500) * _env(n, 0.001, 0.025), 0, 0.8)
    m.add(sine(_glide(160, 60, n), n) * _env(n, 0.002, 0.05), 0, 0.5)
    return m.out()


@sound("death", 0.95, 1)
def _death(v):
    r = _rng("death", v)
    d = 2.4
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 0.6)
    # impacto final
    ni = _n(0.5)
    m.add(sine(_glide(120, 40, ni), ni) * _env(ni, 0.002, 0.1), 0, 1.0)
    m.add(bp(noise(ni, r), 250, 3200) * _env(ni, 0.001, 0.04), 0, 0.8)
    # essência se esvaindo: pad que desce e escurece
    pad = np.zeros(n)
    for det in (0.994, 1.0, 1.006):
        pad += saw(_glide(330 * det, 82 * det, n), n, 20)
    sweep_fc = _glide(2400, 140, n)
    pad = sweep_bp(pad, sweep_fc, 0.8) * _swell(n, 0.12, 1.0) * np.exp(-t * 0.9)
    m.add(pad, 0.05, 0.55)
    # sub grave caindo
    m.add(sine(_glide(60, 28, n), n) * _swell(n, 0.1, 1.0) * np.exp(-t * 0.8), 0.05, 0.8)
    # cristal do Núcleo se partindo e subindo: brilhos que se dissolvem
    for i in range(14):
        tt = 0.12 + i * 0.11 + r.uniform(0, 0.05)
        f = r.uniform(2200, 6200)
        m.add(bell(f, 0.5, tau=0.12, partials=((1, 1, 1), (2.01, 0.3, 0.6))), tt,
              0.13 * np.exp(-i * 0.18), pan=r.uniform(-0.8, 0.8))
    return _trim_tail(reverb(m.out(), 1.4, 0.35, 3800))


@sound("respawn", 0.75, 1)
def _respawn(v):
    # Núcleo do Retorno: azul, cristalino, a essência se recompondo.
    r = _rng("respawn", v)
    d = 1.9
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 1.2)
    shimmer = np.zeros(n)
    for k, f0 in enumerate((220.0, 330.0, 440.0, 660.0, 880.0)):
        f = _glide(f0 * 0.5, f0 * 1.0, n)
        shimmer += sine(f, n) * (0.7 ** k)
    m.add(widen(shimmer * _swell(n, 0.7, 1.4)), 0, 0.35)
    air = sweep_bp(noise(n, r), _glide(300, 5200, n), 1.1) * _swell(n, 0.75, 1.5)
    m.add(air, 0, 0.45)
    for i, ratio in enumerate((1.0, 1.25, 1.5, 2.0, 2.5, 3.0)):
        m.add(bell(880 * ratio, 1.0, tau=0.33, bright=1.4), 0.9 + 0.07 * i, 0.20, pan=-0.6 + 0.24 * i)
    m.add(sine(55, _n(1.4)) * _env(_n(1.4), 0.2, 0.5), 1.0, 0.35)
    return _trim_tail(reverb(m.out(), 1.8, 0.4, 5500))


@sound("heartbeat", 0.60, 1)
def _heartbeat(v):
    d = 0.75
    n = _n(d)
    m = Mix(d)
    for t0, g, f0 in ((0.0, 1.0, 66.0), (0.2, 0.65, 74.0)):
        k = _n(0.2)
        beat = sine(_glide(f0, f0 * 0.65, k), k) * _env(k, 0.006, 0.05)
        m.add(lp(beat, 160), t0, g)
    return m.out()


# =====================================================================
# MOEDAS e CHECKPOINT
# =====================================================================
def _make_coin(step):
    def fn(v):
        r = _rng("coin%d" % step, v)
        f = 1318.5 * _semi(step * 2)
        d = 0.45
        m = Mix(d)
        m.add(bell(f, d, tau=0.13, partials=((1, 1, 1), (1.5, 0.55, 0.8), (2.0, 0.4, 0.6), (3.2, 0.2, 0.35))), 0, 0.75)
        k = _n(0.02)
        m.add(bp(noise(k, r), 3000, 9000) * _env(k, 0.0005, 0.005), 0, 0.5)
        m.add(bell(f * 2.0, 0.2, tau=0.05, partials=((1, 1, 1),)), 0.045, 0.25)
        return reverb(m.out(), 0.3, 0.12, 6000)
    return fn


for _i in range(5):
    sound("coin_%d" % _i, 0.40, 1)(_make_coin(_i))


@sound("checkpoint", 0.80, 1)
def _checkpoint(v):
    # Chama que acende + sinos de vidro: o Núcleo registra o novo ponto.
    r = _rng("checkpoint", v)
    d = 1.3
    n = _n(0.5)
    m = Mix(d + 0.8)
    fire = sweep_bp(noise(n, r), _glide(400, 2600, n), 0.9) * _swell(n, 0.4, 1.4)
    m.add(fire, 0, 0.7)
    m.add(clicks(n, r, 140, 0.002, 1800) * _swell(n, 0.4, 1.0), 0.05, 0.4)
    m.add(sine(_glide(90, 60, n), n) * _env(n, 0.02, 0.15), 0, 0.5)
    for i, (f, g) in enumerate(((659.3, 1.0), (880.0, 0.85), (1318.5, 0.7))):
        m.add(bell(f, 1.1, tau=0.38, bright=1.3), 0.18 + 0.12 * i, 0.38 * g, pan=-0.3 + 0.3 * i)
    return _trim_tail(reverb(m.out(), 1.3, 0.35, 5000))


# =====================================================================
# INIMIGOS
# =====================================================================
@sound("enemy_alert", 0.65, 2)
def _enemy_alert(v):
    r = _rng("enemy_alert", v)
    d = 0.5
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 0.3)
    growl = resonant(noise(n, r), 320 + 40 * v, 2.0)
    growl *= 0.55 + 0.45 * np.sin(TWO_PI * 36 * t)                       # rosnado (AM grave)
    m.add(growl * _swell(n, 0.35, 1.3), 0, 1.0)
    m.add(lp(sat(saw(_glide(140 + 10 * v, 92, n), n), 3), 700) * _swell(n, 0.4, 1.3), 0, 0.6)
    m.add(hp(noise(n, r), 4000) * _swell(n, 0.2, 2) * 0.15, 0, 0.5)      # chiado de armadura
    return reverb(m.out(), 0.45, 0.2, 3000)


@sound("enemy_swing", 0.70, 2)
def _enemy_swing(v):
    # Começa no INÍCIO do ataque: ranger/rosnar de preparação -> golpe no ~0,3 s.
    r = _rng("enemy_swing", v)
    d = 0.55
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 0.3)
    prep = lp(noise(n, r, "pink"), 900) * np.clip(t / 0.28, 0, 1) ** 2 * (t < 0.3) * 0.5
    m.add(prep, 0, 0.6)
    k = _n(0.25)
    sw = sweep_bp(noise(k, r), _glide(260, 1300, k), 0.9) * _swell(k, 0.4, 1.6)
    m.add(sat(sw, 1.5), 0.22, 1.0)
    m.add(sine(_glide(95, 50, k), k) * _env(k, 0.002, 0.07), 0.33, 0.7)
    m.add(bell(1400 * _semi(v), 0.25, tau=0.08, partials=((1, 1, 1), (1.7, 0.5, 0.7))), 0.34, 0.12)
    return reverb(m.out(), 0.4, 0.15, 3500)


@sound("enemy_death", 0.80, 2)
def _enemy_death(v):
    r = _rng("enemy_death", v)
    d = 0.8
    n = _n(d)
    m = Mix(d + 0.4)
    m.add(sine(_glide(120, 45, n), n) * _env(n, 0.002, 0.12), 0, 0.9)
    m.add(lp(noise(n, r), 1800) * _env(n, 0.001, 0.09), 0, 0.8)
    m.add(lp(saw(_glide(170 + 12 * v, 62, n), n), 520) * _env(n, 0.01, 0.22), 0, 0.5)           # gemido
    for i in range(6):                                                                        # armadura caindo
        tt = 0.08 + i * 0.07 + r.uniform(0, 0.04)
        m.add(bell(r.uniform(700, 2200), 0.2, tau=0.05,
                   partials=((1, 1, 1), (2.3, 0.5, 0.7), (4.1, 0.3, 0.5))),
              tt, 0.18 * np.exp(-i * 0.25), pan=r.uniform(-0.5, 0.5))
    return _trim_tail(reverb(m.out(), 0.5, 0.2, 3500))


@sound("enemy_death_ranged", 0.75, 2)
def _enemy_death_ranged(v):
    r = _rng("enemy_death_ranged", v)
    d = 0.9
    n = _n(d)
    m = Mix(d + 0.5)
    for k, det in enumerate((1.0, 1.01, 0.5)):
        m.add(sine(_glide(680 * det, 150 * det, n), n) * _env(n, 0.01, 0.25) * 0.4, 0, 0.7)
    m.add(sweep_bp(noise(n, r), _glide(4200, 450, n), 1.2) * _env(n, 0.01, 0.2), 0, 0.8)
    for i in range(8):
        m.add(bell(r.uniform(1800, 5200), 0.35, tau=0.09, partials=((1, 1, 1), (2.0, 0.3, 0.5))),
              0.05 + i * 0.06, 0.12, pan=r.uniform(-0.7, 0.7))
    m.add(sine(_glide(100, 45, n), n) * _env(n, 0.002, 0.1), 0, 0.6)
    return _trim_tail(reverb(m.out(), 0.7, 0.3, 5000))


@sound("enemy_death_bat", 0.65, 2)
def _enemy_death_bat(v):
    r = _rng("enemy_death_bat", v)
    d = 0.55
    n = _n(d)
    t = _tt(n)
    m = Mix(d)
    f = _glide(2700 - 100 * v, 1100, n) * (1 + 0.04 * np.sin(TWO_PI * 15 * t))
    m.add(sine(f, n) * _env(n, 0.005, 0.12), 0, 0.5)
    m.add(sine(f * 2.01, n) * _env(n, 0.005, 0.07), 0, 0.2)
    m.add(bp(noise(n, r), 2500, 7000) * _env(n, 0.003, 0.06), 0, 0.5)
    m.add(sine(_glide(130, 60, n), n) * _env(n, 0.002, 0.05), 0.12, 0.4)
    return m.out()


@sound("cast_charge", 0.55, 2)
def _cast_charge(v):
    r = _rng("cast_charge", v)
    d = 0.42
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 0.2)
    f = _glide(200 + 12 * v, 520, n)
    tone = lp(saw(f, n), 1500) * (0.65 + 0.35 * np.sin(TWO_PI * 13 * t))
    m.add(tone * _swell(n, 0.9, 1.3), 0, 0.7)
    m.add(hp(noise(n, r), 3000) * np.clip(t / d, 0, 1) ** 2 * 0.2, 0, 0.6)
    for i in range(5):
        m.add(bell(r.uniform(1500, 3800), 0.2, tau=0.05, partials=((1, 1, 1),)), 0.1 + i * 0.06, 0.09,
              pan=r.uniform(-0.5, 0.5))
    return reverb(m.out(), 0.35, 0.15, 4500)


@sound("fireball_shot", 0.65, 2)
def _fireball_shot(v):
    r = _rng("fireball_shot", v)
    d = 0.45
    n = _n(d)
    m = Mix(d + 0.2)
    m.add(sweep_bp(noise(n, r), _glide(500, 2400, n), 0.9) * _env(n, 0.02, 0.13), 0, 0.9)
    m.add(lp(saw(_glide(190, 110, n), n), 900) * _env(n, 0.01, 0.12) * 0.5, 0, 0.7)
    m.add(clicks(n, r, 220, 0.0012, 1800) * _env(n, 0.01, 0.2), 0.02, 0.5)
    m.add(sine(_glide(120, 55, n), n) * _env(n, 0.003, 0.07), 0, 0.5)
    return reverb(m.out(), 0.4, 0.15, 3500)


@sound("magic_impact", 0.55, 2)
def _magic_impact(v):
    r = _rng("magic_impact", v)
    d = 0.35
    n = _n(d)
    m = Mix(d + 0.2)
    m.add(lp(noise(n, r), 2800) * _env(n, 0.001, 0.07), 0, 0.9)
    m.add(sine(_glide(130, 52, n), n) * _env(n, 0.002, 0.08), 0, 0.8)
    m.add(clicks(n, r, 260, 0.001, 2200) * _env(n, 0.002, 0.1), 0, 0.5)
    m.add(sine(_glide(1600, 600, n), n) * _env(n, 0.002, 0.1), 0, 0.2)
    return reverb(m.out(), 0.3, 0.12, 4000)


@sound("bat_flap", 0.30, 3)
def _bat_flap(v):
    r = _rng("bat_flap", v)
    d = 0.16
    n = _n(d)
    m = Mix(d)
    k = _n(0.05)
    for i, t0 in enumerate((0.0, 0.075)):
        puff = bp(noise(k, r), 260 + 40 * v, 950) * _env(k, 0.004, 0.018)
        m.add(puff, t0, 1.0 - 0.3 * i)
    return m.out()


# =====================================================================
# BOSS: Vharok, o Rei do Abismo
# =====================================================================
@sound("boss_windup_slam", 0.85, 1)
def _boss_windup_slam(v):
    r = _rng("boss_windup_slam", v)
    d = 0.7
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 0.5)
    rumble = sat(saw(_glide(38, 88, n), n, 24), 2.5)
    m.add(lp(rumble, 400) * _env(n, 0.25, 1.0), 0, 0.9)
    m.add(lp(noise(n, r), 600) * (0.55 + 0.45 * np.sin(TWO_PI * 22 * t)) * np.clip(t / d, 0, 1) ** 1.5, 0, 0.7)
    m.add(sweep_bp(noise(n, r), _glide(500, 3200, n), 3.5) * np.clip(t / d, 0, 1) ** 2 * 0.35, 0, 0.5)   # ranger de ferro
    m.add(sine(_glide(45, 70, n), n) * _env(n, 0.3, 1.0), 0, 0.8)
    return reverb(m.out(), 0.8, 0.25, 3000)


@sound("boss_windup_barrage", 0.80, 1)
def _boss_windup_barrage(v):
    r = _rng("boss_windup_barrage", v)
    d = 0.78
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 0.5)
    trem_rate = _glide(6, 34, n)
    trem = 0.6 + 0.4 * np.sin(np.cumsum(TWO_PI * trem_rate / SR))
    chord = np.zeros(n)
    for f0 in (196.0, 207.65, 293.66, 311.13):                           # cluster dissonante vermelho
        chord += lp(saw(_glide(f0, f0 * 2.2, n), n), 2200)
    m.add(chord * trem * _swell(n, 0.92, 1.4), 0, 0.35)
    m.add(clicks(n, r, 90, 0.0015, 2000) * np.clip(t / d, 0, 1) ** 2, 0, 0.6)
    m.add(sine(_glide(55, 90, n), n) * _env(n, 0.3, 1.0), 0, 0.6)
    return reverb(m.out(), 0.8, 0.25, 4000)


@sound("boss_windup_charge", 0.80, 1)
def _boss_windup_charge(v):
    r = _rng("boss_windup_charge", v)
    d = 0.56
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 0.4)
    growl = resonant(noise(n, r), 150, 2.0) * (0.5 + 0.5 * np.sin(TWO_PI * 28 * t))
    m.add(sat(growl, 2.5) * _env(n, 0.15, 0.5), 0, 0.9)
    m.add(hp(noise(n, r), 3500) * _env(n, 0.05, 0.25) * 0.25, 0, 0.6)    # vapor/ar saindo
    for i in range(4):                                                    # pateando o chão
        k = _n(0.1)
        m.add(sine(_glide(75, 38, k), k) * _env(k, 0.002, 0.04), 0.06 + 0.13 * i, 0.5 + 0.12 * i)
    return reverb(m.out(), 0.6, 0.2, 3000)


@sound("boss_charge", 0.90, 1)
def _boss_charge(v):
    r = _rng("boss_charge", v)
    d = 0.7
    n = _n(d)
    m = Mix(d + 0.4)
    m.add(sat(sweep_bp(noise(n, r), np.concatenate([_glide(200, 1100, n // 2), _glide(1100, 300, n - n // 2)]), 0.9), 1.5)
          * _swell(n, 0.3, 1.4), 0, 1.0)
    m.add(sine(_glide(80, 36, n), n) * _env(n, 0.002, 0.14), 0, 0.9)
    for i in range(5):
        k = _n(0.12)
        m.add(sine(_glide(70, 34, k), k) * _env(k, 0.002, 0.05), 0.04 + 0.1 * i, 0.55)
        m.add(lp(noise(k, r), 800) * _env(k, 0.001, 0.03), 0.04 + 0.1 * i, 0.3)
    return reverb(m.out(), 0.7, 0.22, 3000)


@sound("boss_windup_melee", 0.70, 1)
def _boss_windup_melee(v):
    r = _rng("boss_windup_melee", v)
    d = 0.3
    n = _n(d)
    m = Mix(d + 0.2)
    m.add(sweep_bp(noise(n, r), _glide(250, 1400, n), 1.0) * _swell(n, 0.85, 1.4), 0, 0.8)
    m.add(lp(saw(_glide(70, 120, n), n), 500) * _env(n, 0.1, 0.4), 0, 0.5)
    return reverb(m.out(), 0.3, 0.12, 3000)


@sound("boss_melee", 0.90, 1)
def _boss_melee(v):
    r = _rng("boss_melee", v)
    d = 0.5
    n = _n(d)
    m = Mix(d + 0.4)
    m.add(sat(sweep_bp(noise(n, r), _glide(180, 1200, n), 0.8), 1.8) * _env(n, 0.01, 0.1), 0, 1.0)
    m.add(sine(_glide(95, 38, n), n) * _env(n, 0.002, 0.13), 0.01, 1.0)
    m.add(lp(noise(n, r), 1300) * _env(n, 0.001, 0.05), 0.02, 0.8)
    m.add(bell(560, 0.4, tau=0.15, partials=((1, 1, 1), (2.4, 0.5, 0.7), (4.1, 0.3, 0.5))), 0.02, 0.12)
    return reverb(m.out(), 0.6, 0.2, 3000)


@sound("boss_slam", 1.00, 1)
def _boss_slam(v):
    r = _rng("boss_slam", v)
    d = 1.1
    n = _n(d)
    m = Mix(d + 1.0)
    m.add(sat(sine(_glide(75, 26, n), n), 2.0) * _env(n, 0.002, 0.3), 0, 1.0)
    m.add(lp(noise(n, r), 900) * _env(n, 0.001, 0.2), 0, 1.0)
    m.add(bp(noise(n, r), 1000, 5000) * _env(n, 0.001, 0.03), 0, 0.7)                     # estalo do impacto
    m.add(clicks(n, r, 120, 0.003, 700) * _env(n, 0.02, 0.35), 0.03, 0.7)                 # pedras caindo
    m.add(sine(_glide(48, 30, n), n) * _env(n, 0.05, 0.5), 0.02, 0.8)
    m.add(lp(noise(n, r, "brown"), 220) * _env(n, 0.05, 0.4), 0.0, 1.0)
    return _trim_tail(reverb(m.out(), 1.2, 0.3, 2800))


@sound("boss_barrage", 0.90, 1)
def _boss_barrage(v):
    r = _rng("boss_barrage", v)
    d = 0.7
    m = Mix(d + 0.5)
    for i in range(5):
        k = _n(0.2)
        t0 = 0.0 + i * 0.028
        bolt = sat(saw(_glide(900 - 70 * i, 200, k), k), 2) * _env(k, 0.002, 0.07)
        m.add(lp(bolt, 2800), t0, 0.35, pan=-0.6 + 0.3 * i)
        m.add(bp(noise(k, r), 800, 6000) * _env(k, 0.001, 0.05), t0, 0.4, pan=-0.6 + 0.3 * i)
    m.add(sine(_glide(110, 50, _n(0.3)), _n(0.3)) * _env(_n(0.3), 0.002, 0.08), 0, 0.8)
    return reverb(m.out(), 0.5, 0.2, 4000)


@sound("boss_step", 0.60, 2)
def _boss_step(v):
    r = _rng("boss_step", v)
    d = 0.3
    n = _n(d)
    m = Mix(d + 0.3)
    m.add(sine(_glide(68 - 4 * v, 32, n), n) * _env(n, 0.002, 0.1), 0, 1.0)
    m.add(lp(noise(n, r), 500) * _env(n, 0.001, 0.05), 0, 0.8)
    m.add(bell(380 + 40 * v, 0.2, tau=0.05, partials=((1, 1, 1), (2.7, 0.5, 0.6), (5.2, 0.3, 0.4))), 0.0, 0.08)  # placas de armadura
    return reverb(m.out(), 0.45, 0.2, 2500)


@sound("hit_boss", 0.90, 2)
def _hit_boss(v):
    r = _rng("hit_boss", v)
    d = 0.4
    n = _n(d)
    m = Mix(d + 0.3)
    m.add(bp(noise(n, r), 1200, 5500) * _env(n, 0.001, 0.025), 0, 0.9)
    m.add(sine(_glide(170, 55, n), n) * _env(n, 0.002, 0.06), 0, 0.9)
    m.add(sine(_glide(80, 36, n), n) * _env(n, 0.002, 0.16), 0, 0.8)
    m.add(lp(sat(saw(_glide(100 + 8 * v, 66, n), n), 3), 600) * _env(n, 0.01, 0.12) * 0.7, 0.01, 0.6)      # rugido de dor
    m.add(bell(1700 * _semi(v), 0.15, tau=0.05), 0, 0.15)
    return reverb(m.out(), 0.4, 0.15, 3000)


@sound("boss_armor", 0.80, 2)
def _boss_armor(v):
    # Golpe na hiper-armadura: aço contra aço, sem dano.
    r = _rng("boss_armor", v)
    d = 0.7
    m = Mix(d + 0.4)
    f0 = 480 * _semi(v * 2)
    m.add(bell(f0, d, tau=0.3, partials=((1, 1, 1), (2.32, 0.7, 0.85), (4.25, 0.5, 0.7),
                                       (6.63, 0.35, 0.5), (9.38, 0.25, 0.4))), 0, 0.7)
    k = _n(0.03)
    m.add(bp(noise(k, r), 1500, 8000) * _env(k, 0.0005, 0.007), 0, 0.9)
    m.add(sine(_glide(140, 80, _n(0.1)), _n(0.1)) * _env(_n(0.1), 0.002, 0.03), 0, 0.4)
    return reverb(m.out(), 0.5, 0.18, 6000)


@sound("boss_phase2", 1.00, 1)
def _boss_phase2(v):
    # FÚRIA DO ABISMO: grave que cresce, dissonância, sino fúnebre, rugido.
    r = _rng("boss_phase2", v)
    d = 3.0
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 1.4)
    m.add(sine(_glide(36, 41, n), n) * _swell(n, 0.35, 1.2), 0, 0.9)
    cluster = np.zeros(n)
    for f0 in (55.0, 58.27, 82.41, 87.31, 116.54):
        for det in (0.995, 1.005):
            cluster += saw(f0 * det, n, 18)
    fc = _glide(150, 1800, n)
    m.add(widen(sweep_bp(cluster, fc, 0.9) * _swell(n, 0.5, 1.3)), 0, 0.4)
    roar_t0 = 0.55
    k = _n(2.0)
    kt = _tt(k)
    roar = resonant(noise(k, r), 190, 1.6) * (0.6 + 0.4 * np.sin(TWO_PI * 31 * kt))
    roar = sat(roar, 3) * _env(k, 0.08, 0.7)
    m.add(roar, roar_t0, 0.9)
    m.add(lp(sat(saw(_glide(95, 62, k), k, 20), 4), 800) * _env(k, 0.08, 0.8), roar_t0, 0.55)
    # explosão central e tolling do sino
    kb = _n(1.2)
    m.add(sat(sine(_glide(70, 24, kb), kb), 2) * _env(kb, 0.002, 0.3), 0.5, 1.0)
    m.add(lp(noise(kb, r), 1100) * _env(kb, 0.001, 0.18), 0.5, 0.8)
    for i, t0 in enumerate((0.55, 1.5, 2.45)):
        m.add(bell(164.8, 2.0, tau=0.9, partials=((1, 1, 1), (2.76, 0.6, 0.8), (5.4, 0.35, 0.6),
                                                  (8.93, 0.2, 0.4))), t0, 0.35)
    m.add(hp(noise(n, r), 4500) * _swell(n, 0.8, 2.0), 0, 0.15)
    return _trim_tail(reverb(m.out(), 2.0, 0.4, 3500))


@sound("boss_enter", 0.95, 1)
def _boss_enter(v):
    # Portões do castelo se fechando atrás de Kael.
    r = _rng("boss_enter", v)
    d = 2.8
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 1.5)
    kb = _n(1.2)
    m.add(sat(sine(_glide(62, 24, kb), kb), 2) * _env(kb, 0.002, 0.35), 0.0, 1.0)
    m.add(lp(noise(kb, r), 800) * _env(kb, 0.001, 0.15), 0.0, 0.8)
    m.add(bell(110.0, 2.2, tau=0.8, partials=((1, 1, 1), (2.32, 0.7, 0.8), (4.25, 0.5, 0.6),
                                              (6.63, 0.35, 0.5), (9.38, 0.2, 0.4))), 0.02, 0.4)
    for i in range(14):                                                    # correntes
        k = _n(0.05)
        m.add(bp(noise(k, r), 1800, 6500) * _env(k, 0.001, 0.012), 0.12 + i * 0.037 + r.uniform(0, 0.02), 0.28,
              pan=r.uniform(-0.6, 0.6))
    drone = (sine(41.2, n) * 0.8 + lp(saw(82.41, n, 14) + saw(82.41 * 1.006, n, 14), 450) * 0.5)
    fade = np.concatenate([_swell(n - _n(0.6), 0.5, 1.3), np.zeros(_n(0.6))])
    m.add(widen(drone * fade), 0.9, 0.55)
    return _trim_tail(reverb(m.out(), 2.4, 0.42, 3000))


@sound("boss_death", 1.00, 1)
def _boss_death(v):
    # A queda do Rei do Abismo: gemido, rachaduras, cristais estilhaçando.
    r = _rng("boss_death", v)
    d = 4.2
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 2.0)
    kb = _n(1.5)
    m.add(sat(sine(_glide(80, 22, kb), kb), 2) * _env(kb, 0.002, 0.5), 0.0, 1.0)
    m.add(lp(noise(kb, r), 1000) * _env(kb, 0.001, 0.25), 0.0, 0.9)
    vib = 1 + 0.03 * np.sin(TWO_PI * 5.5 * t)
    groan = lp(sat(saw(_glide(120, 30, n) * vib, n, 24), 3), 700) * np.exp(-t * 0.6) * _swell(n, 0.05, 1.0)
    m.add(widen(groan), 0.05, 0.9)
    m.add(resonant(noise(n, r), 170, 1.8) * (0.6 + 0.4 * np.sin(TWO_PI * 24 * t)) * np.exp(-t * 0.9)
          * np.clip(t / 0.05, 0, 1), 0.1, 0.7)
    rumble = lp(noise(n, r, "brown"), 260) * (np.exp(-t * 0.5))
    m.add(rumble, 0.0, 1.4)
    for i in range(36):                                                    # cristais se estilhaçando
        tt = 0.3 + i * 0.09 + r.uniform(0, 0.05)
        m.add(bell(r.uniform(1800, 7000), 0.6, tau=0.14, partials=((1, 1, 1), (1.83, 0.4, 0.7), (3.1, 0.2, 0.4))),
              tt, 0.14 * np.exp(-i * 0.04), pan=r.uniform(-0.9, 0.9))
    m.add(clicks(n, r, 90, 0.003, 600) * np.exp(-t * 0.7), 0.2, 0.7)       # pedras
    m.add(bell(82.4, 4.0, tau=1.6, partials=((1, 1, 1), (2.76, 0.6, 0.8), (5.4, 0.35, 0.6))), 1.8, 0.4)
    return _trim_tail(reverb(m.out(), 2.4, 0.42, 3200))


# =====================================================================
# MUNDO
# =====================================================================
@sound("crumble_warn", 0.60, 2)
def _crumble_warn(v):
    r = _rng("crumble_warn", v)
    d = 0.45
    n = _n(d)
    t = _tt(n)
    m = Mix(d)
    rate = 18 + 40 * (t / d)
    trig = (np.sin(np.cumsum(TWO_PI * rate / SR)) > 0.92).astype(float)
    k = _n(0.012)
    kern = np.exp(-np.arange(k) / (0.002 * SR))
    ticks = np.convolve(trig, kern)[:n]
    m.add(lp(noise(n, r), 2200) * ticks * 0.9, 0, 1.0)
    m.add(lp(noise(n, r, "brown"), 300) * np.clip(t / d, 0, 1) * 0.5, 0, 0.8)
    return m.out()


@sound("crumble_fall", 0.75, 2)
def _crumble_fall(v):
    r = _rng("crumble_fall", v)
    d = 0.9
    n = _n(d)
    m = Mix(d + 0.3)
    m.add(lp(noise(n, r), 1600) * _env(n, 0.005, 0.2), 0, 0.9)
    m.add(clicks(n, r, 170, 0.0025, 900) * _env(n, 0.01, 0.35), 0, 0.8)
    m.add(sine(_glide(85, 35, n), n) * _env(n, 0.003, 0.15), 0.0, 0.8)
    m.add(lp(noise(n, r, "brown"), 400) * _env(n, 0.02, 0.3), 0, 0.9)
    return reverb(m.out(), 0.5, 0.2, 2800)


@sound("stalactite_warn", 0.55, 2)
def _stalactite_warn(v):
    r = _rng("stalactite_warn", v)
    d = 0.45
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 0.3)
    for i, t0 in enumerate((0.0, 0.11, 0.2, 0.28, 0.34)):
        k = _n(0.04)
        m.add(bp(noise(k, r), 800, 4500) * _env(k, 0.0005, 0.01), t0, 0.7)
    grit = hp(noise(n, r), 2500) * (0.5 + 0.5 * np.sin(TWO_PI * 30 * t)) * np.clip(t / d, 0, 1) * 0.25
    m.add(grit, 0, 0.5)
    m.add(bell(2400 * _semi(v), 0.25, tau=0.08, partials=((1, 1, 1),)), 0.3, 0.07)
    return reverb(m.out(), 0.5, 0.2, 4000)


@sound("stalactite_fall", 0.55, 1)
def _stalactite_fall(v):
    r = _rng("stalactite_fall", v)
    d = 0.45
    n = _n(d)
    m = Mix(d)
    m.add(sweep_bp(noise(n, r), _glide(3800, 700, n), 2.5) * _swell(n, 0.4, 1.4), 0, 0.7)
    m.add(sine(_glide(1500, 400, n), n) * _swell(n, 0.5, 1.5) * 0.15, 0, 0.5)
    return m.out()


@sound("stalactite_crash", 0.85, 2)
def _stalactite_crash(v):
    r = _rng("stalactite_crash", v)
    d = 0.8
    n = _n(d)
    m = Mix(d + 0.4)
    m.add(bp(noise(n, r), 700, 6000) * _env(n, 0.0008, 0.04), 0, 0.9)
    m.add(lp(noise(n, r), 1500) * _env(n, 0.001, 0.12), 0, 0.8)
    m.add(sine(_glide(100, 42, n), n) * _env(n, 0.002, 0.1), 0, 0.8)
    m.add(clicks(n, r, 200, 0.0015, 1600) * _env(n, 0.01, 0.25), 0.02, 0.7)
    return reverb(m.out(), 0.6, 0.22, 3500)


@sound("fall_void", 0.55, 1)
def _fall_void(v):
    r = _rng("fall_void", v)
    d = 1.3
    n = _n(d)
    t = _tt(n)
    m = Mix(d + 0.6)
    f = _glide(1700, 170, n)
    m.add(sine(f, n) * _swell(n, 0.1, 1.0) * np.exp(-t * 1.2), 0, 0.4)
    m.add(sweep_bp(noise(n, r), _glide(2500, 220, n), 1.1) * _swell(n, 0.15, 1.2) * np.exp(-t * 1.0), 0, 0.6)
    return reverb(m.out(), 1.0, 0.35, 3000)


# =====================================================================
# INTERFACE: menu, pausa, loja, história
# =====================================================================
@sound("menu_move", 0.40, 2)
def _menu_move(v):
    r = _rng("menu_move", v)
    d = 0.1
    n = _n(d)
    m = Mix(d)
    m.add(bp(noise(n, r), 600, 3200) * _env(n, 0.0005, 0.007), 0, 0.7)
    m.add(sine(210 + 14 * v, n) * _env(n, 0.001, 0.025), 0, 0.5)
    m.add(bell(1250, 0.1, tau=0.03, partials=((1, 1, 1),)), 0, 0.12)
    return m.out()


@sound("menu_select", 0.60, 1)
def _menu_select(v):
    r = _rng("menu_select", v)
    d = 0.5
    n = _n(d)
    m = Mix(d + 0.3)
    m.add(sine(_glide(130, 60, n), n) * _env(n, 0.002, 0.07), 0, 0.8)
    m.add(bp(noise(n, r), 800, 5000) * _env(n, 0.0005, 0.012), 0, 0.5)
    m.add(bell(740.0, 0.45, tau=0.15, partials=((1, 1, 1), (2.76, 0.4, 0.7), (5.4, 0.2, 0.5))), 0.0, 0.3)
    return reverb(m.out(), 0.5, 0.2, 4000)


@sound("game_start", 0.85, 1)
def _game_start(v):
    # Kael desembainha a espada: raspar de aço + grave de abismo + sino.
    r = _rng("game_start", v)
    d = 1.6
    n = _n(d)
    m = Mix(d + 1.0)
    k = _n(0.55)
    scrape = sweep_bp(noise(k, r), _glide(1500, 6500, k), 1.6) * _swell(k, 0.7, 1.4)
    m.add(scrape, 0, 0.7)
    m.add(bell(2600, 0.9, tau=0.4, partials=((1, 1, 1), (1.51, 0.6, 0.8), (2.2, 0.35, 0.6))), 0.5, 0.25)
    drone = sine(55, n) * 0.7 + lp(saw(110, n, 14) + saw(110 * 1.007, n, 14), 600) * 0.4
    m.add(widen(drone * _swell(n, 0.45, 1.3)), 0.2, 0.55)
    kb = _n(1.0)
    m.add(sine(_glide(80, 40, kb), kb) * _env(kb, 0.002, 0.2), 0.5, 0.9)
    m.add(bell(164.8, 1.6, tau=0.6), 0.5, 0.3)
    return _trim_tail(reverb(m.out(), 1.5, 0.35, 3500))


@sound("pause_open", 0.50, 1)
def _pause_open(v):
    r = _rng("pause_open", v)
    d = 0.35
    n = _n(d)
    m = Mix(d + 0.2)
    m.add(lp(noise(n, r), 900) * _swell(n, 0.25, 1.4), 0, 0.6)
    m.add(sine(_glide(190, 70, n), n) * _env(n, 0.005, 0.1), 0, 0.8)
    m.add(bell(420, 0.3, tau=0.1, partials=((1, 1, 1), (2.76, 0.4, 0.6))), 0, 0.12)
    return reverb(m.out(), 0.4, 0.2, 2500)


@sound("pause_close", 0.45, 1)
def _pause_close(v):
    r = _rng("pause_close", v)
    d = 0.28
    n = _n(d)
    m = Mix(d + 0.2)
    m.add(lp(noise(n, r), 1400) * _swell(n, 0.7, 1.4), 0, 0.5)
    m.add(sine(_glide(80, 200, n), n) * _env(n, 0.04, 0.08), 0, 0.7)
    return reverb(m.out(), 0.3, 0.15, 3000)


@sound("shop_open", 0.60, 1)
def _shop_open(v):
    # Sininho de mercador + moedas mexendo na bolsa.
    r = _rng("shop_open", v)
    d = 0.9
    m = Mix(d + 0.5)
    m.add(bell(1568.0, 0.7, tau=0.22, partials=((1, 1, 1), (2.4, 0.5, 0.6), (4.1, 0.3, 0.4))), 0, 0.5)
    m.add(bell(1318.5, 0.7, tau=0.22, partials=((1, 1, 1), (2.4, 0.5, 0.6), (4.1, 0.3, 0.4))), 0.14, 0.4)
    for i in range(7):
        k = _n(0.12)
        m.add(bell(r.uniform(2200, 4200), 0.15, tau=0.03, partials=((1, 1, 1), (1.5, 0.5, 0.6))),
              0.18 + i * 0.05 + r.uniform(0, 0.02), 0.18, pan=r.uniform(-0.5, 0.5))
    m.add(lp(noise(_n(0.4), r), 700) * _env(_n(0.4), 0.05, 0.15), 0.1, 0.25)
    return reverb(m.out(), 0.5, 0.2, 5000)


@sound("shop_close", 0.45, 1)
def _shop_close(v):
    r = _rng("shop_close", v)
    d = 0.45
    m = Mix(d + 0.2)
    for i in range(3):
        m.add(bell(r.uniform(1800, 3200), 0.15, tau=0.03, partials=((1, 1, 1), (1.5, 0.5, 0.6))),
              i * 0.05, 0.18, pan=r.uniform(-0.4, 0.4))
    k = _n(0.2)
    m.add(lp(noise(k, r), 900) * _env(k, 0.01, 0.06), 0.1, 0.4)
    m.add(sine(_glide(150, 70, k), k) * _env(k, 0.002, 0.05), 0.15, 0.4)
    return reverb(m.out(), 0.3, 0.12, 4000)


def _coin_cascade(m, r, start, count, base=1600.0, gain=0.3):
    for i in range(count):
        m.add(bell(base * (1 + 0.12 * r.uniform(-1, 1)), 0.25, tau=0.07,
                   partials=((1, 1, 1), (1.5, 0.5, 0.6), (2.0, 0.3, 0.5))),
              start + i * 0.045 + r.uniform(0, 0.015), gain * (0.92 ** i), pan=r.uniform(-0.5, 0.5))


@sound("purchase", 0.60, 1)
def _purchase(v):
    r = _rng("purchase", v)
    m = Mix(1.0)
    _coin_cascade(m, r, 0.0, 5)
    m.add(bell(880.0, 0.7, tau=0.25, bright=1.2), 0.2, 0.25)
    return reverb(m.out(), 0.4, 0.15, 5000)


@sound("purchase_sword", 0.75, 1)
def _purchase_sword(v):
    # Espada sacada da bainha: raspão de aço subindo + moedas + brilho.
    r = _rng("purchase_sword", v)
    d = 1.3
    m = Mix(d + 0.8)
    k = _n(0.5)
    m.add(sweep_bp(noise(k, r), _glide(1200, 7000, k), 1.8) * _swell(k, 0.75, 1.4), 0, 0.7)
    m.add(bell(3100, 1.0, tau=0.45, partials=((1, 1, 1), (1.51, 0.6, 0.8), (2.2, 0.35, 0.6), (3.1, 0.2, 0.5))), 0.45, 0.28)
    m.add(sine(_glide(110, 55, k), k) * _env(k, 0.002, 0.08), 0.47, 0.5)
    _coin_cascade(m, r, 0.55, 5, 1700.0, 0.25)
    return _trim_tail(reverb(m.out(), 0.8, 0.25, 5500))


@sound("equip_sword", 0.60, 2)
def _equip_sword(v):
    r = _rng("equip_sword", v)
    d = 0.4
    m = Mix(d + 0.2)
    k = _n(0.16)
    m.add(sweep_bp(noise(k, r), _glide(4800, 1500, k), 1.8) * _swell(k, 0.4, 1.4), 0, 0.5)
    m.add(bell(1800 * _semi(v * 2), 0.2, tau=0.05, partials=((1, 1, 1), (1.7, 0.5, 0.7), (2.6, 0.3, 0.5))), 0.15, 0.3)
    m.add(sine(_glide(140, 60, k), k) * _env(k, 0.002, 0.04), 0.15, 0.6)
    m.add(bp(noise(k, r), 800, 5000) * _env(k, 0.001, 0.012), 0.15, 0.6)
    return reverb(m.out(), 0.35, 0.12, 4500)


@sound("sword_upgrade", 0.85, 1)
def _sword_upgrade(v):
    # Martelo na bigorna e fagulhas: o aço sendo reforçado.
    r = _rng("sword_upgrade", v)
    d = 1.6
    m = Mix(d + 1.0)
    for i, t0 in enumerate((0.0, 0.26, 0.52)):
        f0 = 620 * (1.0 + 0.06 * i)
        m.add(bell(f0, 0.8, tau=0.28, partials=((1, 1, 1), (2.32, 0.7, 0.85), (4.25, 0.5, 0.7),
                                               (6.63, 0.35, 0.5), (9.38, 0.2, 0.4))), t0, 0.5 + 0.1 * i)
        k = _n(0.05)
        m.add(bp(noise(k, r), 1200, 8000) * _env(k, 0.0005, 0.01), t0, 0.7)
        m.add(sine(_glide(150, 70, _n(0.1)), _n(0.1)) * _env(_n(0.1), 0.002, 0.03), t0, 0.5)
        m.add(clicks(_n(0.3), r, 400, 0.0007, 3500) * _env(_n(0.3), 0.001, 0.08), t0, 0.35)
    for i, ratio in enumerate((1.0, 1.25, 1.5, 2.0)):
        m.add(bell(880 * ratio, 1.0, tau=0.35, bright=1.4), 0.75 + 0.06 * i, 0.22, pan=-0.4 + 0.27 * i)
    return _trim_tail(reverb(m.out(), 1.0, 0.28, 5500))


@sound("purchase_health", 0.75, 1)
def _purchase_health(v):
    # Mais vida: batida de coração + acorde quente subindo.
    r = _rng("purchase_health", v)
    d = 1.4
    m = Mix(d + 0.8)
    for t0, g, f0 in ((0.0, 1.0, 66.0), (0.2, 0.75, 74.0)):
        k = _n(0.22)
        m.add(lp(sine(_glide(f0, f0 * 0.65, k), k) * _env(k, 0.006, 0.06), 180), t0, g)
    for i, f in enumerate((220.0, 277.18, 329.63, 440.0)):
        n = _n(1.0)
        m.add(widen(tri(f, n) * _swell(n, 0.25, 1.3)), 0.25 + 0.06 * i, 0.25)
    for i, ratio in enumerate((1.0, 1.5, 2.0)):
        m.add(bell(880 * ratio, 0.9, tau=0.3, bright=1.2), 0.5 + 0.08 * i, 0.22, pan=-0.3 + 0.3 * i)
    return _trim_tail(reverb(m.out(), 0.9, 0.28, 5000))


@sound("purchase_ability", 0.75, 1)
def _purchase_ability(v):
    # Poder arcano desbloqueado: glissando brilhante + cacho de sinos.
    r = _rng("purchase_ability", v)
    d = 1.5
    n = _n(0.8)
    m = Mix(d + 0.8)
    sh = np.zeros(n)
    for k, f0 in enumerate((330.0, 495.0, 660.0, 990.0)):
        sh += sine(_glide(f0, f0 * 2.0, n), n) * (0.7 ** k)
    m.add(widen(sh * _swell(n, 0.75, 1.3)), 0, 0.3)
    m.add(sweep_bp(noise(n, r), _glide(500, 6500, n), 1.2) * _swell(n, 0.8, 1.4), 0, 0.5)
    for i, ratio in enumerate((1.0, 1.26, 1.5, 1.89, 2.0, 2.52)):
        m.add(bell(784 * ratio, 1.0, tau=0.35, bright=1.4), 0.6 + 0.07 * i, 0.22, pan=-0.6 + 0.24 * i)
    m.add(sine(_glide(80, 160, _n(0.7)), _n(0.7)) * _swell(_n(0.7), 0.7, 1.3), 0, 0.4)
    return _trim_tail(reverb(m.out(), 1.2, 0.32, 5500))


@sound("purchase_heal", 0.70, 1)
def _purchase_heal(v):
    # Poção: rolha, goles borbulhantes e um acorde de cura.
    r = _rng("purchase_heal", v)
    d = 1.3
    m = Mix(d + 0.8)
    k = _n(0.08)
    m.add(sine(_glide(420, 180, k), k) * _env(k, 0.001, 0.02), 0, 0.5)                    # "pop" da rolha
    m.add(bp(noise(k, r), 800, 4000) * _env(k, 0.0005, 0.008), 0, 0.5)
    for i in range(4):                                                                     # goles
        kk = _n(0.13)
        m.add(sine(_glide(180 + 40 * i, 340 + 60 * i, kk), kk) * _env(kk, 0.01, 0.05)
              * (0.6 + 0.4 * np.sin(TWO_PI * 38 * _tt(kk))), 0.15 + i * 0.15, 0.55)
        m.add(lp(noise(kk, r), 800) * _env(kk, 0.01, 0.05), 0.15 + i * 0.15, 0.25)
    for i, f in enumerate((523.25, 659.25, 783.99)):
        m.add(bell(f, 0.9, tau=0.32, bright=1.1), 0.78 + 0.09 * i, 0.28, pan=-0.3 + 0.3 * i)
    return _trim_tail(reverb(m.out(), 0.8, 0.25, 5000))


@sound("denied", 0.50, 1)
def _denied(v):
    r = _rng("denied", v)
    d = 0.34
    m = Mix(d)
    for t0 in (0.0, 0.13):
        k = _n(0.12)
        m.add(lp(sat(saw(_glide(120, 88, k), k), 2.5), 700) * _env(k, 0.002, 0.045), t0, 0.7)
        m.add(sine(_glide(75, 55, k), k) * _env(k, 0.002, 0.05), t0, 0.5)
    return m.out()


@sound("story", 0.40, 1)
def _story(v):
    # Pergaminho/runa: sopro e sino distante, para o texto de história.
    r = _rng("story", v)
    d = 1.0
    n = _n(d)
    m = Mix(d + 0.9)
    m.add(sweep_bp(noise(n, r), _glide(700, 2200, n), 1.0) * _swell(n, 0.4, 1.6), 0, 0.35)
    m.add(bell(329.63, 1.6, tau=0.7, partials=((1, 1, 1), (2.76, 0.4, 0.7), (5.4, 0.2, 0.5))), 0.12, 0.3)
    m.add(bell(493.88, 1.4, tau=0.55, partials=((1, 1, 1), (2.76, 0.4, 0.7))), 0.25, 0.2)
    return _trim_tail(reverb(m.out(), 1.4, 0.4, 3500))


# =====================================================================
# Impacto do jogador (golpe acertando inimigos). Fica depois dos sons UI
# porque o ataque já define o "feedback"; este é o retorno do acerto.
# =====================================================================
@sound("hit", 0.75, 3)
def _hit(v):
    r = _rng("hit", v)
    d = 0.3
    n = _n(d)
    m = Mix(d + 0.2)
    m.add(bp(noise(n, r), 1300 + 200 * v, 5200) * _env(n, 0.0008, 0.022), 0, 0.9)
    m.add(sine(_glide(190 - 10 * v, 70, n), n) * _env(n, 0.002, 0.05), 0, 0.9)
    m.add(lp(noise(n, r), 700) * _env(n, 0.001, 0.04), 0, 0.5)
    m.add(bell(1850 * _semi(v * 2 - 2), 0.2, tau=0.055, partials=((1, 1, 1), (2.1, 0.4, 0.6))), 0, 0.2)
    return reverb(m.out(), 0.3, 0.1, 4000)


# =====================================================================
# VITÓRIA
# =====================================================================
def _horn(freq, dur, vib=0.003):
    n = _n(dur)
    t = _tt(n)
    f = freq * (1 + vib * np.sin(TWO_PI * 5.2 * t) * np.clip(t / 0.35, 0, 1))
    s = saw(f, n, 24) + saw(f * 1.004, n, 24)
    s = lp(s, 900 + 1500 * np.mean(np.clip(t / 0.4, 0, 1)))
    a = np.clip(t / 0.07, 0, 1) ** 1.5
    r = np.clip((dur - t) / 0.12, 0, 1)
    return s * a * r


def _pad(freqs, dur, a=0.25):
    n = _n(dur)
    t = _tt(n)
    s = np.zeros(n)
    for f in freqs:
        for det in (0.996, 1.0, 1.004):
            s += saw(f * det, n, 16)
    s = lp(s, 1100, 2)
    env = np.clip(t / a, 0, 1) ** 1.2 * np.clip((dur - t) / 0.35, 0, 1)
    return s * env


@sound("victory", 1.00, 1)
def _victory(v):
    # Fanfarra heroica e sombria: começa em ré menor e resolve em ré MAIOR
    # (a vingança cumprida, o primeiro raio de esperança).
    d = 7.0
    m = Mix(d + 2.5)
    D3, A3, D4, F4, Fs4, A4 = 146.83, 220.0, 293.66, 349.23, 369.99, 440.0
    D5, F5, Fs5, A5 = 587.33, 698.46, 739.99, 880.0
    # toques graves de tímpano
    for t0 in (0.0, 0.5, 1.0, 1.5):
        k = _n(0.5)
        m.add(sine(_glide(95, 48, k), k) * _env(k, 0.002, 0.12), t0, 0.8 if t0 < 1.5 else 1.0)
        m.add(lp(noise(k, _rng("vic", int(t0 * 10))), 500) * _env(k, 0.001, 0.05), t0, 0.4)
    m.add(widen(_pad((D3, A3, F4), 2.9)), 0.0, 0.28)
    m.add(widen(_pad((D3, A3, D4, Fs4, A4), 4.8, 0.2)), 2.6, 0.32)
    melody = ((D4, 0.0, 0.5), (A4, 0.5, 0.5), (D5, 1.0, 0.6), (F5, 1.6, 0.5), (A5, 2.1, 0.5), (Fs5, 2.6, 3.4))
    for f, t0, dur in melody:
        m.add(widen(_horn(f, dur)), t0, 0.5)
        m.add(widen(_horn(f * 0.5, dur)), t0, 0.28)
    for i, f in enumerate((1174.7, 1480.0, 1760.0, 2349.3)):
        m.add(bell(f, 1.8, tau=0.7, bright=1.3), 2.65 + 0.1 * i, 0.16, pan=-0.5 + 0.33 * i)
    m.add(bell(73.42, 4.0, tau=1.6, partials=((1, 1, 1), (2.76, 0.5, 0.8), (5.4, 0.3, 0.6))), 2.6, 0.45)
    return _trim_tail(reverb(m.out(), 2.4, 0.35, 4200))


# =====================================================================
# Construção
# =====================================================================
def build_all(on_ready=None):
    """Gera todos os sons. Retorna {nome: [array_int16, ...]}.
    on_ready(nome, lista) é chamado a cada som pronto (usado na geração em
    segundo plano, para o jogo já poder tocar o que ficou pronto)."""
    result = {}
    for name, gain, variants, fn in REGISTRY:
        try:
            arrays = []
            for v in range(variants):
                buf = fn(v)
                arrays.append(finish(_trim_tail(buf) if len(buf) > _n(0.05) else buf, gain))
            result[name] = arrays
            if on_ready:
                on_ready(name, arrays)
        except Exception:        # um som com defeito nunca derruba o jogo
            continue
    return result
