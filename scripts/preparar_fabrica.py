#!/usr/bin/env python3
"""Prepara a fabrica de inserts a partir do PLANO aprovado: base, filmagem e partituras.

    python preparar_fabrica.py --pasta <pasta-do-video>

Le `fabrica/janelas.json` (a fonte unica das janelas, em tempo do video FINAL)
e deixa pronto para os agentes:

1. `base/final-sem-insert.mp4`: o corte + velocidade em resolucao cheia. E dele
   que sai toda a filmagem que entra DENTRO de um insert e toda transcricao.
2. `fabrica/banco/filmagem/f<nome>.mp4`: para cada janela com "filmagem": true,
   o trecho exato, mudo, com keyframe a cada 30 quadros (sem isso o HyperFrames
   avisa "sparse keyframes" e o video congela dentro do insert). Entra na
   composicao sem acelerar, sem cortar e sem deslocar, senao a boca nao bate.
3. `fabrica/partituras.txt`: uma linha por insert,
   `nome|duracao|de-ate|palavra@segundo ...`, com o tempo relativo ao inicio do
   insert. Cada elemento entra no tempo da palavra dita. A transcricao e feita
   no video FINAL, nunca no bruto: num anuncio real dois inserts sairam
   0,8 s atrasados porque o tempo veio do bruto, que tinha derivado.

Formato do janelas.json (lista):
  {"nome": "02-taste-skill", "de": 7.00, "ate": 15.46, "formato": "moldura",
   "filmagem": false, "motivo": "linha 2 do PLANO.md"}
Insert reaproveitado de outro projeto, com tempo do ORIGINAL deste plano:
  {"nome": "16-botao", "arquivo": "/caminho/16-botao.mp4", "de_orig": 211.99,
   "ate_orig": 221.43, "formato": "vazado_pequeno", "origem_ini": 0.62}
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import subprocess
import sys
from pathlib import Path

import transcrever as tr


def ler_janelas(pasta):
    arq = pasta / "fabrica" / "janelas.json"
    if not arq.exists():
        sys.exit("falta %s. Escreva as janelas do PLANO.md aprovado ali (ver --help)." % arq)
    js = comum.ler_json(arq)
    for j in js:
        if "nome" not in j:
            sys.exit("janela sem 'nome' em janelas.json: %s" % j)
        if "de_orig" not in j and ("de" not in j or "ate" not in j):
            sys.exit("janela %s sem 'de'/'ate' (tempo do final) nem 'de_orig'/'ate_orig'" % j["nome"])
    return js


def garantir_base(pasta, refazer):
    base = pasta / "base" / "final-sem-insert.mp4"
    if base.exists() and not refazer:
        return base
    base.parent.mkdir(parents=True, exist_ok=True)
    print("renderizando a base (corte + velocidade, resolucao cheia)...", flush=True)
    r = subprocess.run([sys.executable, "-u", str(comum.SCRIPTS / "render.py"), "--pasta", str(pasta),
                        "--ate", "velocidade", "--saida", str(base)], stdin=subprocess.DEVNULL)
    if r.returncode != 0 or not base.exists():
        sys.exit("o render da base falhou")
    return base


def main():
    ap = argparse.ArgumentParser(description="Base, filmagem e partituras para a fabrica.")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--refazer-base", action="store_true",
                    help="renderiza a base de novo (depois de mudar o corte)")
    a = ap.parse_args()
    comum.exigir("ffmpeg", "ffprobe")
    pasta = Path(a.pasta).expanduser().resolve()
    js = ler_janelas(pasta)
    base = garantir_base(pasta, a.refazer_base)

    filmagem = pasta / "fabrica" / "banco" / "filmagem"
    for j in js:
        if not j.get("filmagem") or "de" not in j:
            continue
        filmagem.mkdir(parents=True, exist_ok=True)
        dest = filmagem / ("f%s.mp4" % j["nome"])
        comum.rodar(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % j["de"], "-i", str(base),
                     "-t", "%.3f" % (j["ate"] - j["de"]), "-an", "-c:v", "libx264", "-crf", "14",
                     "-pix_fmt", "yuv420p", "-g", "30", "-keyint_min", "30", str(dest)])
        print("filmagem: %s" % dest)

    print("transcrevendo a base (uma vez, para todas as partituras)...", flush=True)
    ws, motor = tr.palavras(base)
    comum.gravar_json(pasta / "base" / "final-palavras.json", ws)
    linhas = []
    for j in js:
        if "de" not in j:
            continue
        de, ate = float(j["de"]), float(j["ate"])
        dentro = [w for w in ws if w["f"] > de and w["t"] < ate]
        marcas = " ".join("%s@%.2f" % (w["p"], max(0.0, w["t"] - de)) for w in dentro)
        linhas.append("%s|%.2f|%.2f-%.2f|%s" % (j["nome"], ate - de, de, ate, marcas))
    comum.gravar_texto(pasta / "fabrica" / "partituras.txt", "\n".join(linhas) + "\n")
    print("partituras: %s (%d inserts, motor %s)" % (pasta / "fabrica" / "partituras.txt", len(linhas), motor))
    for w in tr.suspeitas(ws):
        print("SUSPEITA no final: '%s' dura %.2fs em %.2f. Retomada que o corte deixou?" %
              (w["p"], w["f"] - w["t"], w["t"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
