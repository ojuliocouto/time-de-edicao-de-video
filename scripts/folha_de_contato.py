#!/usr/bin/env python3
"""Monta uma folha de contato de um video, para ler o movimento de uma referencia.

Serve tanto para uma referencia baixada quanto para conferir um insert rendido
sem ter que assistir quadro a quadro.

    python3 folha_de_contato.py referencia.mp4 -o /tmp/folha.png
    python3 folha_de_contato.py ref.mp4 -o folha.png --quadros 8 --largura 240
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import subprocess
import sys
import tempfile


def duracao(caminho):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", caminho],
        capture_output=True,
        text=True,
     encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description="Folha de contato de um video.")
    ap.add_argument("video")
    ap.add_argument("-o", "--saida", required=True)
    ap.add_argument("--quadros", type=int, default=6)
    ap.add_argument("--largura", type=int, default=260, help="largura de cada quadro em px")
    ap.add_argument("--colunas", type=int, default=8, help="quadros por linha (grade); 0 = uma linha so")
    a = ap.parse_args()

    if not comum.tem("ffmpeg"):
        print("erro: ffmpeg nao esta no PATH. Instale com `brew install ffmpeg`.", file=sys.stderr)
        return 1

    video = os.path.abspath(os.path.expanduser(a.video))
    if not os.path.exists(video):
        print(f"erro: nao achei {video}", file=sys.stderr)
        return 1

    d = duracao(video)
    if not d:
        print(f"erro: o ffprobe nao leu a duracao de {video}. O arquivo e um video valido?", file=sys.stderr)
        return 1

    if a.quadros < 2:
        print("erro: --quadros precisa ser 2 ou mais.", file=sys.stderr)
        return 1

    saida = os.path.abspath(os.path.expanduser(a.saida))
    os.makedirs(os.path.dirname(saida) or ".", exist_ok=True)

    # amostra dentro das bordas: nem o primeiro nem o ultimo quadro, que
    # costumam pegar fade de entrada ou de saida e nao dizem nada do movimento
    pontos = [0.04 + (0.92 * i / (a.quadros - 1)) for i in range(a.quadros)]

    with tempfile.TemporaryDirectory() as tmp:
        quadros = []
        for i, p in enumerate(pontos):
            alvo = os.path.join(tmp, f"q{i:02d}.jpg")
            r = subprocess.run(
                ["ffmpeg", "-v", "error", "-ss", f"{d * p:.2f}", "-i", video,
                 "-frames:v", "1", "-vf", f"scale={a.largura}:-2", "-y", alvo],
                capture_output=True,
             stdin=subprocess.DEVNULL)
            if r.returncode == 0 and os.path.exists(alvo):
                quadros.append(alvo)

        if len(quadros) < 2:
            print("erro: nao consegui extrair quadros suficientes.", file=sys.stderr)
            return 1

        cmd = ["ffmpeg", "-v", "error"]
        for q in quadros:
            cmd += ["-i", q]
        col = a.colunas if a.colunas and a.colunas < len(quadros) else len(quadros)
        if col == len(quadros):
            filtro = f"hstack=inputs={len(quadros)}"
        else:
            # grade: completa a ultima linha com o ultimo quadro para o xstack fechar
            linhas = -(-len(quadros) // col)
            while len(quadros) < linhas * col:
                quadros.append(quadros[-1]); cmd += ["-i", quadros[-1]]
            pos = "|".join("%s_%s" % ("+".join(["w0"] * (i % col)) or "0", "+".join(["h0"] * (i // col)) or "0")
                           for i in range(len(quadros)))
            filtro = f"xstack=inputs={len(quadros)}:layout={pos}"
        cmd += ["-filter_complex", filtro, "-y", saida]
        if subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL).returncode != 0:
            print("erro: o ffmpeg falhou ao montar a folha.", file=sys.stderr)
            return 1

    tempos = ", ".join(f"{d * p:.1f}s" for p in pontos[: len(quadros)])
    print(f"{saida}  {len(quadros)} quadros  ({tempos})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
