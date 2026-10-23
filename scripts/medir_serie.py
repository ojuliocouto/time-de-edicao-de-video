#!/usr/bin/env python3
"""Mede a SERIE inteira, nao um insert por vez.

Os outros verificadores abrem um arquivo. Um insert pode marcar 87% de
movimento e passar limpo sendo o setimo cartao de texto chapado seguido. Este
olha o conjunto.

CALIBRACAO. Medi as referencias de motion escolhidas pela pessoa e doze inserts
que entregamos em dois anuncios:

    referencias (6) ..... trocas de plano 0, 0, 3, 6, 8, 10
    nossos (12) ......... dez com ZERO troca de plano

Dai sai o piso: pelo menos metade da serie tem troca de plano interna.

    python3 medir_serie.py renders/*.mp4
    python3 medir_serie.py renders/ --corte-minimo 0.4

Sai com codigo 1 se a serie reprovar.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import subprocess
import sys

L, A = 180, 320
LIMIAR_TEXTURA = 24      # gradiente local que conta como textura
LIMIAR_CORTE = 6         # diferenca media que conta como troca de plano


def tira(video, filtro, taxa=None):
    cmd = ["ffmpeg", "-v", "error", "-i", video]
    if taxa:
        cmd += ["-r", str(taxa)]
    cmd += ["-vf", filtro, "-f", "rawvideo", "-"]
    r = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        return []
    n = L * A
    return [r.stdout[i * n:(i + 1) * n] for i in range(len(r.stdout) // n)]


def detalhe(video, amostras=8):
    """Fracao de pixels com textura local. Foto tem em todo lugar; tipografia e
    forma chapada so tem na borda. E o indicador de 'entrou coisa real'."""
    qs = tira(video, f"scale={L}:{A},format=gray")
    if not qs:
        return 0.0
    passo = max(1, len(qs) // amostras)
    alvo = qs[::passo][:amostras]
    tot = 0.0
    for f in alvo:
        c = 0
        for y in range(1, A - 1):
            base = y * L
            for x in range(1, L - 1, 2):
                i = base + x
                g = (abs(f[i] - f[i - 1]) + abs(f[i] - f[i + 1])
                     + abs(f[i] - f[i - L]) + abs(f[i] - f[i + L]))
                if g > LIMIAR_TEXTURA:
                    c += 1
        tot += 100 * c / ((A - 2) * (L // 2))
    return tot / len(alvo)


def cortes(video, fps=30):
    """Quantas trocas grandes de quadro. O borrao mata grao e ruido de
    compressao, senao acabamento vira 'corte'."""
    qs = tira(video, f"boxblur=6:1,scale={L}:{A},format=gray", taxa=fps)
    if len(qs) < 2:
        return 0
    n = L * A
    d = [sum(abs(x - y) for x, y in zip(qs[i - 1], qs[i])) / n for i in range(1, len(qs))]
    pico = max(d) if d else 0
    return sum(1 for v in d if v > max(pico * 0.45, LIMIAR_CORTE))


def main():
    ap = argparse.ArgumentParser(description="Mede a serie inteira de inserts.")
    ap.add_argument("alvos", nargs="+", help="arquivos de render, ou a pasta renders/")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--corte-minimo", type=float, default=0.5,
                    help="fracao da serie que precisa ter troca de plano (padrao 0,5)")
    a = ap.parse_args()

    if not comum.tem("ffmpeg"):
        print("erro: ffmpeg nao esta no PATH. Instale com `brew install ffmpeg`.", file=sys.stderr)
        return 2

    videos = []
    for t in a.alvos:
        if os.path.isdir(t):
            videos += [os.path.join(t, f) for f in sorted(os.listdir(t))
                       if f.lower().endswith((".mp4", ".mov", ".webm"))]
        elif os.path.exists(t):
            videos.append(t)
    if not videos:
        print("erro: nao achei nenhum video nos alvos dados.", file=sys.stderr)
        return 2

    print(f"{'insert':<34}{'detalhe':>9}{'cortes':>9}")
    print("-" * 54)
    linhas = []
    for v in sorted(videos):
        det, ct = detalhe(v), cortes(v, a.fps)
        linhas.append((os.path.basename(v), det, ct))
        print(f"{os.path.basename(v)[:33]:<34}{det:>8.1f}%{ct:>9}")

    com_corte = sum(1 for _, _, c in linhas if c > 0)
    frac = com_corte / len(linhas)
    dets = [d for _, d, _ in linhas]

    print()
    print(f"  inserts na serie ......... {len(linhas)}")
    print(f"  com troca de plano ....... {com_corte}  ({100*frac:.0f}%, minimo {100*a.corte_minimo:.0f}%)")
    print(f"  detalhe de textura ....... {min(dets):.1f}% a {max(dets):.1f}%")

    print("\n  CONFIRA NA MAO, contra o PLANO.md:")
    print("   - pelo menos um terco dos inserts carrega material real?")
    print("   - algum dispositivo se repete em sequencia?")
    print("   - o tamanho de plano varia ao longo da serie?")
    print("   - existe pelo menos uma virada de registro?")

    if frac < a.corte_minimo:
        print(f"\n  REPROVADO")
        print(f"  so {com_corte} de {len(linhas)} inserts tem troca de plano.")
        print("  A serie inteira acontece numa tela so, que foi exatamente o")
        print("  defeito medido nos doze primeiros inserts. Volte ao PLANO.md.")
        return 1
    print("\n  ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
