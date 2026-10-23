#!/usr/bin/env python3
"""Versao do insert com a voz do trecho, para ela aprovar cada insert separado.

    python com_voz.py --pasta <pasta-do-video> 02-taste-skill S1-time-conteudo
    python com_voz.py --pasta <pasta-do-video> --todos

Insert mudo nao se julga: ela precisa ouvir a fala para ver se a palavra entra
na hora certa. Sai em 720p (leve para o chat) em
`fabrica/renders/com-voz/<nome>-com-voz.mp4`, com o audio da base final no
trecho exato da janela.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Insert com a voz do trecho, 720p.")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("nomes", nargs="*")
    ap.add_argument("--todos", action="store_true")
    a = ap.parse_args()
    pasta = Path(a.pasta).expanduser().resolve()
    base = pasta / "base" / "final-sem-insert.mp4"
    if not base.exists():
        sys.exit("falta %s: rode o preparar_fabrica.py antes" % base)
    js = {j["nome"]: j for j in comum.ler_json(pasta / "fabrica" / "janelas.json") if "de" in j}
    nomes = list(js) if a.todos else a.nomes
    if not nomes:
        sys.exit("diga quais inserts (nomes do janelas.json) ou use --todos")
    destino = pasta / "fabrica" / "renders" / "com-voz"
    destino.mkdir(parents=True, exist_ok=True)
    for n in nomes:
        if n not in js:
            print("pulei %s: nao esta no janelas.json com tempo do final" % n)
            continue
        arte = pasta / "fabrica" / "renders" / (n + ".mp4")
        if not arte.exists():
            print("pulei %s: ainda nao renderizado (%s)" % (n, arte))
            continue
        de, ate = float(js[n]["de"]), float(js[n]["ate"])
        saida = destino / (n + "-com-voz.mp4")
        comum.rodar(["ffmpeg", "-v", "error", "-y", "-i", str(arte), "-ss", "%.3f" % de, "-t", "%.3f" % (ate - de),
                     "-i", str(base), "-map", "0:v", "-map", "1:a", "-vf", "scale=720:-2",
                     "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest",
                     "-movflags", "+faststart", str(saida)])
        print(saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
