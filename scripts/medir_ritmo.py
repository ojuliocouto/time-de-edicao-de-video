#!/usr/bin/env python3
"""Mede o ritmo de um insert rendido: quanto da duracao tem alguma coisa se mexendo.

O `check` do HyperFrames nao ve tela parada. Este script ve.

CALIBRACAO. Os limites nao sao chute. Rodei este script nas referencias de
motion que a pessoa escolheu e nos inserts que ja entregamos:

    referencias dela ..... 59% a 100% em movimento, mediana 90%
    nossos inserts ....... 54% a 76%,               mediana 68%

Dai saem os padroes: 55% de movimento e parada maxima de 0,8 s. Com eles o
script aprova as referencias dela e reprova dois dos nossos quatro inserts.

O BORRAO NAO E ENFEITE. A analise passa um boxblur antes de comparar os quadros
porque o grao de filme animado, que e acabamento legitimo, muda pixel em todo
quadro e INFLA a medida: a mesma composicao deu 83% com grao e 59% sem. Com o
borrao as duas dao igual. Sem isso, qualquer peca com grao passaria de graca.

    python3 medir_ritmo.py renders/insert.mp4
    python3 medir_ritmo.py renders/insert.mp4 --parada-maxima 1.5

Sai com codigo 1 se estourar o limite.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import subprocess
import sys

L, A = 270, 480          # grade de analise
BORRAO = 6               # raio do boxblur que mata grao sem matar movimento
DELTA = 8                # mudanca minima por pixel para contar
PISO = 0.0008            # fracao de pixels mudados para o quadro contar como vivo


def quadros(video, fps, borrao):
    filtro = f"boxblur={borrao}:1,scale={L}:{A},format=gray" if borrao > 0 \
        else f"scale={L}:{A},format=gray"
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video, "-r", str(fps),
         "-vf", filtro, "-f", "rawvideo", "-"],
        capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        return None
    n = L * A
    return [r.stdout[i * n:(i + 1) * n] for i in range(len(r.stdout) // n)]


def main():
    ap = argparse.ArgumentParser(description="Mede o ritmo de um insert rendido.")
    ap.add_argument("video")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--movimento-minimo", type=float, default=55.0,
                    help="percentual minimo da duracao com movimento (padrao 55)")
    ap.add_argument("--parada-maxima", type=float, default=None,
                    help="maior parada tolerada em segundos "
                         "(padrao: 0,8 s, ou 2%% da duracao se for maior)")
    ap.add_argument("--borrao", type=int, default=BORRAO,
                    help="raio do boxblur anti-grao; 0 desliga (padrao 6)")
    a = ap.parse_args()

    if not comum.tem("ffmpeg"):
        print("erro: ffmpeg nao esta no PATH. Instale com `brew install ffmpeg`.", file=sys.stderr)
        return 2
    if not os.path.exists(a.video):
        print(f"erro: nao achei {a.video}", file=sys.stderr)
        return 2

    qs = quadros(a.video, a.fps, a.borrao)
    if not qs or len(qs) < 2:
        print(f"erro: o ffmpeg nao extraiu quadros de {a.video}.", file=sys.stderr)
        return 2

    total = L * A
    vivos = [
        sum(1 for x, y in zip(qs[i - 1], qs[i]) if abs(x - y) > DELTA) / total > PISO
        for i in range(1, len(qs))
    ]

    paradas, ini = [], None
    for i, v in enumerate(vivos):
        if not v and ini is None:
            ini = i
        elif v and ini is not None:
            paradas.append((ini, i))
            ini = None
    if ini is not None:
        paradas.append((ini, len(vivos)))

    dur = len(qs) / a.fps
    movimento = 100 * sum(vivos) / len(vivos)
    maior = max((f - i for i, f in paradas), default=0) / a.fps
    limite = a.parada_maxima if a.parada_maxima is not None else max(0.8, dur * 0.02)

    passo = max(1, a.fps // 2)
    perfil = "".join("#" if any(vivos[i:i + passo]) else "."
                     for i in range(0, len(vivos), passo))

    print(f"{os.path.basename(a.video)}  {dur:.2f}s  {len(qs)} quadros a {a.fps}fps")
    print(f"  em movimento ......... {movimento:.0f}%   (minimo {a.movimento_minimo:.0f}%)")
    print(f"  maior parada ......... {maior:.2f}s   (maximo {limite:.2f}s)")
    print(f"  perfil (0,5s cada) ... [{perfil}]   # = mexe, . = parado")

    ruim = []
    if maior > limite:
        pi, pf = max(paradas, key=lambda p: p[1] - p[0])
        ruim.append(f"parada de {maior:.2f}s passa do limite de {limite:.2f}s, "
                    f"de {pi / a.fps:.2f}s a {pf / a.fps:.2f}s")
    if movimento < a.movimento_minimo:
        ruim.append(f"{movimento:.0f}% de movimento fica abaixo do minimo de "
                    f"{a.movimento_minimo:.0f}%")

    if ruim:
        print("\n  REPROVADO")
        for r in ruim:
            print(f"  {r}")
        print("\n  Deriva lenta de camera NAO resolve: uma escala de 5% em 6s foi\n"
              "  medida e nao registra. O que resolve e continuar entrando coisa.")
        return 1
    print("\n  ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
