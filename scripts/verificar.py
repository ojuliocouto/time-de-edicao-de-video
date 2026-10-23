#!/usr/bin/env python3
"""Confere o arquivo renderizado antes de mandar para aprovacao.

    python verificar.py --pasta <pasta> <arquivo-renderizado>

Olha o ARQUIVO: duracao contra o plano, blocos curtos que picotam o audio,
trilha de audio presente. O auditar.py olha o CONTEUDO. Os dois rodam antes de
qualquer entrega; se este falhar, nao mande.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Confere o render contra o plano.json.")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("arquivo")
    a = ap.parse_args()

    pasta = Path(a.pasta).expanduser()
    arq = Path(a.arquivo).expanduser()
    if not (pasta / "plano.json").exists():
        sys.exit("plano.json nao existe em %s" % pasta)
    if not arq.exists():
        sys.exit("arquivo nao existe: %s" % arq)

    plano = comum.ler_json(pasta / "plano.json")
    manter, fator = plano["corte"]["manter"], float(plano["velocidade"]["fator"])
    esperado = sum(b - x for x, b in manter) / fator
    curtos = sum(1 for x, b in manter if b - x < 0.25)
    meta = comum.sondar(arq)
    dif = abs(meta["dur"] - esperado)

    print("duracao renderizada: %.3fs | esperada: %.3fs | diferenca: %.3fs" % (meta["dur"], esperado, dif))
    print("blocos: %d | blocos curtos (<0.25s): %d" % (len(manter), curtos))
    print("quadro: %dx%d a %.2f fps" % (meta["w"], meta["h"], meta["fps"]))
    falhas = 0
    if dif > 0.5:
        print("FALHA: a duracao renderizada nao bate com o plano.")
        falhas += 1
    if curtos > 3:
        print("FALHA: %d blocos curtos. O audio provavelmente picotou. Costuma ser respiracao "
              "a -50 dB entre pausas: tire com plano.py aplicar, tipo hesitacao." % curtos)
        falhas += 1
    if not meta["audio"]:
        print("FALHA: o arquivo saiu sem trilha de audio.")
        falhas += 1
    if falhas:
        print("%d falha(s). Nao mande para aprovacao assim." % falhas)
        return 1
    print("OK: render aprovado na verificacao.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
