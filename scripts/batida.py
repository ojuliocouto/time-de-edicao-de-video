#!/usr/bin/env python3
"""Batida de fundo bem baixa, com virada na hora da oportunidade, e a mixagem dela.

    # gera e ja mistura no video (o caso normal)
    python batida.py --video previews/05-audio.mp4 --virada 71.04 -o previews/06-montado-batida.mp4

    # so gera o wav
    python batida.py --duracao 158.6 --virada 124.44 --wav audio/batida.wav

A virada e o segundo do video FINAL em que a fala muda para a oportunidade
("E pra isso eu tenho uma boa noticia", "Bom", "Vem ai"). O pedido foi: "quando
ele fala 'e pra isso eu tenho uma boa noticia' a musica tem que dar uma virada,
ficar mais animada, pra acompanhar a oportunidade". Sem --virada, a batida fica
calma do comeco ao fim.

O que foi aprovado depois de reprovar a primeira versao:
- 104 BPM, kick no 1 e no 3, clap no 2 e no 4, chimbal em colcheias;
- compasso antes da virada com rufar que sobe; depois dela, kick em todo tempo,
  chimbal em semicolcheias, chimbal aberto no contratempo e baixo pulsando;
- volume: ~21 dB ABAIXO da voz. A primeira, 10 dB abaixo, "diminui
  drasticamente a musica de fundo, deixa bem baixinha mesmo". Este script mede
  a voz do video e a batida e acerta o ganho sozinho; --abaixo muda a distancia.

Python puro, sem numpy: roda igual no Mac, no Windows e no Linux.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import array
import math
import random
import re
import sys
import tempfile
import wave
from pathlib import Path

SR = 44100
BPM = 104.0


def sintetizar(dur, virada=None, semente=7):
    n = int(SR * dur)
    mix = array.array("f", bytes(4 * n))
    rnd = random.Random(semente)
    bat = 60.0 / BPM
    comp = 4 * bat
    if virada is None or virada <= 0 or virada >= dur:
        virada = dur + comp * 2          # nunca chega: fica tudo na parte 1
    t0 = virada - math.ceil(virada / comp) * comp  # grade ancorada na virada

    def ruido(k):
        return [rnd.gauss(0, 1) for _ in range(k)]

    def kick():
        k = int(0.32 * SR)
        fase, out = 0.0, []
        for i in range(k):
            t = i / SR
            fase += 2 * math.pi * (38 + 30 * math.exp(-t * 28)) / SR
            out.append(math.sin(fase) * math.exp(-t * 9))
        return out

    def passa_alta(x, vezes=1):
        for _ in range(vezes):
            x = [x[0]] + [x[i] - x[i - 1] for i in range(1, len(x))]
        return x

    def clap():
        k = int(0.22 * SR)
        r = passa_alta(ruido(k))
        return [r[i] * math.exp(-(i / SR) * 22) * 0.5 for i in range(k)]

    def caixa():
        k = int(0.12 * SR)
        r = passa_alta(ruido(k))
        return [(r[i] * 0.6 + math.sin(2 * math.pi * 190 * i / SR) * 0.4) * math.exp(-(i / SR) * 30)
                for i in range(k)]

    def hat(aberto=False):
        k = int((0.14 if aberto else 0.05) * SR)
        r = passa_alta(ruido(k), 2)
        dec = 24 if aberto else 80
        return [r[i] * math.exp(-(i / SR) * dec) * 0.18 for i in range(k)]

    def baixo(freq, d):
        k = int(d * SR)
        return [(math.sin(2 * math.pi * freq * i / SR) + 0.3 * math.sin(4 * math.pi * freq * i / SR))
                * min(1.0, (i / SR) / 0.01) * math.exp(-(i / SR) * 6) * 0.35 for i in range(k)]

    def soma(t, x, g):
        i = int(round(t * SR))
        a = 0
        if i < 0:
            a, i = -i, 0
        j = min(n, i + len(x) - a)
        for k in range(i, j):
            mix[k] += x[a + k - i] * g

    K, C = kick(), clap()
    hats = [hat() for _ in range(8)]
    abertos = [hat(True) for _ in range(4)]
    caixas = [caixa() for _ in range(4)]
    notas = [55.0, 55.0, 65.41, 49.0]
    baixos = {f: baixo(f, bat * 0.45) for f in set(notas)}
    b = 0
    while True:
        t = t0 + b * bat
        if t >= dur:
            break
        pos = b % 4
        if t < virada - comp:                         # parte 1, calma
            if pos in (0, 2):
                soma(t, K, 0.8)
            if pos in (1, 3):
                soma(t, C, 0.45)
            soma(t, hats[b % 8], 0.4)
            soma(t + bat / 2, hats[(b + 3) % 8], 0.3)
        elif t < virada:                              # compasso da virada: rufar que sobe
            k = (t - (virada - comp)) / comp
            if pos in (0, 2):
                soma(t, K, 0.8)
            div = 2 if pos < 2 else 4
            for s in range(div):
                soma(t + s * bat / div, caixas[s % 4], 0.25 + 0.5 * k)
            soma(t, hats[b % 8], 0.4)
        else:                                         # parte 2, animada
            c = int((t - virada) // comp)
            soma(t, K, 0.95)
            if pos in (1, 3):
                soma(t, C, 0.6)
            for s in range(4):
                soma(t + s * bat / 4, hats[(b + s) % 8], 0.32 if s % 2 else 0.42)
            soma(t + bat / 2, abertos[b % 4], 0.45)
            soma(t + bat / 2, baixos[notas[c % 4]], 1.0)
        b += 1
    f = int(0.5 * SR)
    for i in range(min(f, n)):
        mix[i] *= i / f
        mix[n - 1 - i] *= i / f
    pico = max(1e-9, max(abs(v) for v in mix))
    g = 1.0 / (pico * 1.12)
    pcm = array.array("h", (int(max(-1.0, min(1.0, v * g)) * 32767) for v in mix))
    return pcm, t0


def gravar_wav(pcm, destino):
    est = array.array("h", bytes(4 * len(pcm)))
    est[0::2] = pcm
    est[1::2] = pcm
    if sys.byteorder == "big":
        est.byteswap()
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(est.tobytes())


def lufs(arq):
    r = comum.rodar(["ffmpeg", "-hide_banner", "-nostats", "-i", str(arq), "-vn",
                     "-af", "ebur128=framelog=quiet", "-f", "null", "-"], checar=False)
    m = re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr or "")
    return float(m[-1]) if m else None


def mixar(video, wav, abaixo, saida):
    voz, bat = lufs(video), lufs(wav)
    if voz is None or bat is None:
        sys.exit("nao consegui medir o volume (voz %s, batida %s)" % (voz, bat))
    ganho = (voz - abaixo) - bat
    print("voz %.1f LUFS | batida %.1f LUFS | ganho %+.1f dB (batida %.0f dB abaixo da voz)"
          % (voz, bat, ganho, abaixo))
    comum.rodar(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(video), "-i", str(wav),
                 "-filter_complex", "[1:a]volume=%.2fdB,aresample=48000[b];"
                 "[0:a]aresample=48000[v];[v][b]amix=inputs=2:duration=first:normalize=0[a]" % ganho,
                 "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                 "-movflags", "+faststart", str(saida)])
    print("pronto: %s" % saida)


def main():
    ap = argparse.ArgumentParser(description="Batida de fundo com virada, e a mixagem.")
    ap.add_argument("--video", help="video final para mixar (a duracao sai dele)")
    ap.add_argument("--duracao", type=float, help="so para gerar sem video")
    ap.add_argument("--virada", type=float, help="segundo do FINAL em que a batida vira")
    ap.add_argument("--abaixo", type=float, default=21.0, help="dB abaixo da voz (padrao 21)")
    ap.add_argument("--wav", help="onde gravar a batida (padrao: ao lado da saida)")
    ap.add_argument("-o", "--saida", help="video com a batida")
    a = ap.parse_args()
    comum.exigir("ffmpeg", "ffprobe")
    if a.video:
        dur = comum.sondar(a.video)["dur"]
    elif a.duracao:
        dur = a.duracao
    else:
        sys.exit("passe --video (para mixar) ou --duracao (so gerar)")
    print("sintetizando %.1fs a %.0f BPM%s..." % (dur, BPM, " com virada em %.2fs" % a.virada if a.virada else ""),
          flush=True)
    pcm, t0 = sintetizar(dur, a.virada)
    wav = Path(a.wav) if a.wav else (Path(a.saida).with_suffix(".batida.wav") if a.saida
                                     else Path(tempfile.gettempdir()) / "batida.wav")
    gravar_wav(pcm, wav)
    print("batida: %s (grade comeca em %.3fs)" % (wav, t0))
    if a.video and a.saida:
        mixar(a.video, wav, a.abaixo, a.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
