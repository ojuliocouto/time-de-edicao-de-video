#!/usr/bin/env python3
"""Mede a composicao de um quadro: respiro, banda intocada, numero de elementos.

LEIA ANTES DE CONFIAR: das quatro medidas, so "elementos" reprova alguma coisa.
Medimos as onze referencias de motion escolhidas pela pessoa contra seis inserts
nossos: respiro, banda limpa e tamanho da ancora deram praticamente iguais nos
dois grupos. Ou seja, composicao nunca foi o nosso problema. Os tres saem como
informacao, nao como veredito. Ver references/fabrica-numeros.md.

    python3 medir_quadro.py print.png
    python3 medir_quadro.py render.mp4 --em 2.5
    python3 medir_quadro.py print.png --acento "#c8f24a"

Sai com codigo 1 se estourar algum limite.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import subprocess
import sys

L, A = 135, 240          # grade de analise
TOL = 26                 # distancia de cor para considerar "mesmo fundo"


def rgb(caminho, em=None):
    cmd = ["ffmpeg", "-v", "error"]
    if em is not None:
        cmd += ["-ss", str(em)]
    cmd += ["-i", caminho, "-frames:v", "1",
            "-vf", f"scale={L}:{A}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    r = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0 or len(r.stdout) < L * A * 3:
        return None
    d = r.stdout
    return [(d[i * 3], d[i * 3 + 1], d[i * 3 + 2]) for i in range(L * A)]


def perto(a, b, tol=TOL):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) <= tol * 3


def hex2rgb(h):
    h = h.strip().lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def dilatar(marca, raio):
    """Engorda a mascara. Sem isso, cada LETRA vira uma ilha e a contagem mente:
    um insert nosso deu 30 "elementos" que na verdade eram letras e linhas."""
    if raio <= 0:
        return marca
    out = list(marca)
    for _ in range(raio):
        novo = list(out)
        for i, v in enumerate(out):
            if not v:
                continue
            x, y = i % L, i // L
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < L and 0 <= ny < A:
                    novo[ny * L + nx] = True
        out = novo
    return out


def aglomerados(marca):
    """Conta ilhas conectadas na grade booleana, e devolve as caixas de cada uma."""
    visto = [False] * (L * A)
    caixas = []
    for i in range(L * A):
        if not marca[i] or visto[i]:
            continue
        pilha, cel = [i], []
        visto[i] = True
        while pilha:
            p = pilha.pop()
            cel.append(p)
            x, y = p % L, p // L
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < L and 0 <= ny < A:
                    q = ny * L + nx
                    if marca[q] and not visto[q]:
                        visto[q] = True
                        pilha.append(q)
        if len(cel) < 6:          # respingo de antialias, nao e elemento
            continue
        xs = [c % L for c in cel]
        ys = [c // L for c in cel]
        caixas.append((min(xs), min(ys), max(xs), max(ys), len(cel)))
    return caixas


def main():
    ap = argparse.ArgumentParser(description="Mede a composicao de um quadro.")
    ap.add_argument("arquivo", help="png, jpg ou video")
    ap.add_argument("--em", type=float, default=None, help="segundo a amostrar, se for video")
    ap.add_argument("--fundo", default=None, help='cor de fundo, ex "#101216" (padrao: a mais frequente)')
    ap.add_argument("--acento", default=None, help='cor de acento, ex "#c8f24a"')
    ap.add_argument("--respiro-minimo", type=float, default=30.0,
                    help="piso frouxo; nas medicoes ninguem chegou perto de reprovar")
    ap.add_argument("--elementos-maximo", type=int, default=6)
    ap.add_argument("--juntar", type=int, default=4,
                    help="raio de dilatacao que junta letras e linhas num elemento so (padrao 4)")
    a = ap.parse_args()

    if not comum.tem("ffmpeg"):
        print("erro: ffmpeg nao esta no PATH. Instale com `brew install ffmpeg`.", file=sys.stderr)
        return 2
    if not os.path.exists(a.arquivo):
        print(f"erro: nao achei {a.arquivo}", file=sys.stderr)
        return 2

    px = rgb(a.arquivo, a.em)
    if px is None:
        print(f"erro: o ffmpeg nao leu um quadro de {a.arquivo}.", file=sys.stderr)
        return 2

    if a.fundo:
        fundo = hex2rgb(a.fundo)
    else:
        cont = {}
        for p in px:
            k = (p[0] // 8, p[1] // 8, p[2] // 8)
            cont[k] = cont.get(k, 0) + 1
        k = max(cont, key=cont.get)
        fundo = (k[0] * 8 + 4, k[1] * 8 + 4, k[2] * 8 + 4)

    ehfundo = [perto(p, fundo) for p in px]
    respiro = 100 * sum(ehfundo) / len(px)

    # maior banda horizontal totalmente limpa
    limpa = [all(ehfundo[y * L:(y + 1) * L]) for y in range(A)]
    maior = atual = 0
    for c in limpa:
        atual = atual + 1 if c else 0
        maior = max(maior, atual)
    banda = 100 * maior / A

    tinta = [not f for f in ehfundo]
    caixas = aglomerados(dilatar(tinta, a.juntar))
    caixas.sort(key=lambda c: c[4], reverse=True)

    print(f"{os.path.basename(a.arquivo)}" + (f"  em {a.em}s" if a.em is not None else ""))
    print(f"  fundo detectado ...... #{fundo[0]:02x}{fundo[1]:02x}{fundo[2]:02x}")
    print(f"  respiro .............. {respiro:.0f}% do quadro e fundo puro")
    print(f"  maior banda limpa .... {banda:.0f}% da altura   (informativo)")
    print(f"  elementos ............ {len(caixas)}")
    if caixas:
        x0, y0, x1, y1, n = caixas[0]
        larg = 100 * (x1 - x0 + 1) / L
        print(f"  ancora ............... {larg:.0f}% da largura   (informativo)")
        if len(caixas) > 1:
            seg = caixas[1]
            razao = caixas[0][4] / seg[4]
            print(f"  ancora / 2o elemento . {razao:.1f}x em area")

    if a.acento:
        ac = hex2rgb(a.acento)
        marca = [perto(p, ac, 40) for p in px]
        cob = 100 * sum(marca) / len(px)
        pontos = aglomerados(dilatar(marca, a.juntar))
        print(f"  acento ............... {cob:.1f}% do quadro em {len(pontos)} ponto(s)"
              "   (limite de 3 herdado do guia VOX, nao validado aqui)")

    ruim = []
    # respiro e banda saem so como informacao: medidos, nao discriminam.
    if respiro < a.respiro_minimo:
        ruim.append(f"respiro de {respiro:.0f}% abaixo do minimo de {a.respiro_minimo:.0f}%")
    if len(caixas) > a.elementos_maximo:
        ruim.append(f"{len(caixas)} elementos passa do maximo de {a.elementos_maximo}")
    if a.acento and len(pontos) > 3:
        ruim.append(f"acento em {len(pontos)} pontos, o maximo e 3")

    if ruim:
        print("\n  REPROVADO")
        for r in ruim:
            print(f"  {r}")
        return 1
    print("\n  ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
