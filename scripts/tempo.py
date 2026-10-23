#!/usr/bin/env python3
"""Converte tempo entre o video FINAL (cortado e acelerado) e o ORIGINAL.

    python tempo.py --pasta <pasta> fin 69 83          # "em 1:09" que a pessoa viu -> original
    python tempo.py --pasta <pasta> fin 1:09 1:23      # aceita minuto:segundo
    python tempo.py --pasta <pasta> orig 116.9         # original -> final

A pessoa sempre fala do tempo que ve no player do preview ("em 1:09 tem uma
duplicidade"), e o plano.json so aceita tempo do ORIGINAL. Converter de cabeca
pondo (de - ate) / 1,3 erra: um corte que inclui pausa ja encurtada tira menos
do final do que a conta simples (2,90 s contra 3,22 s num caso real). Use
sempre este script, que le os blocos mantidos do proprio plano.json.

Tambem e importavel: `from tempo import Tempo; t = Tempo(pasta); t.orig(12.5)`.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import sys
from pathlib import Path


def segundos(txt):
    txt = str(txt).strip().replace(",", ".")
    if ":" in txt:
        m, s = txt.split(":", 1)
        return int(m) * 60 + float(s)
    return float(txt)


class Tempo:
    def __init__(self, pasta):
        plano = comum.ler_json(Path(pasta).expanduser() / "plano.json")
        self.manter = plano["corte"]["manter"]
        self.fator = float(plano["velocidade"]["fator"])
        if not self.manter:
            sys.exit("o plano.json nao tem blocos mantidos")

    def orig(self, t_final):
        """Final -> original. Fim de bloco vai para o fim do bloco mantido."""
        acc = 0.0
        for a, b in self.manter:
            d = (b - a) / self.fator
            if t_final <= acc + d + 1e-9:
                return a + (t_final - acc) * self.fator
            acc += d
        return self.manter[-1][1]

    def final(self, t_orig):
        """Original -> final (mesma conta do render.py). Tempo dentro de trecho
        cortado vira o inicio do proximo bloco mantido."""
        acc = 0.0
        for a, b in self.manter:
            if t_orig < a:
                return acc / self.fator
            if t_orig <= b:
                return (acc + (t_orig - a)) / self.fator
            acc += b - a
        return acc / self.fator

    def duracao_final(self):
        return sum(b - a for a, b in self.manter) / self.fator


def main():
    ap = argparse.ArgumentParser(description="Tempo do video final <-> original.")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("sentido", choices=["fin", "orig"], help="fin: final->original | orig: original->final")
    ap.add_argument("tempos", nargs="+")
    a = ap.parse_args()
    t = Tempo(a.pasta)
    for v in a.tempos:
        s = segundos(v)
        r = t.orig(s) if a.sentido == "fin" else t.final(s)
        print("%9.3f -> %9.3f" % (s, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
