#!/usr/bin/env python3
"""Rascunho das legendas a partir das palavras transcritas do montado.

    python cues_de_palavras.py --pasta <video>/legenda --sem 0-5.02,46.6-95.7

Le `palavras.json` (saida do `transcrever.py --json`) e escreve as cues no
`legenda.json`: cria o arquivo se ele nao existe, ou troca so a lista "cues"
se ja existe (zonas, herois e recortes ficam). Antes de trocar, guarda o
anterior em `legenda.json.bak`.

Como corta as frases, nesta ordem:
- pausa de 0,25 s ou mais entre duas palavras abre legenda nova;
- ponto, interrogacao ou exclamacao fecham a legenda;
- passou de 34 caracteres, quebra antes da palavra que estoura (a 62 px, mais
  que isso vira duas linhas) e nunca deixa uma palavra so na legenda seguinte
  se der para evitar;
- `--sem` tira os trechos (tempo do video) onde a arte ja escreve a fala ou nao
  ha espaco: as palavras dali nao viram legenda.

O rascunho nao decide enfase, zona nem heroi: isso e julgamento, e e o que o
agente faz depois em cima dele (ver estacoes/6-legenda.md). Correcao de
grafia vai com `--corrigir "Cloud=Claude,IA=I.A."`.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import re
import shutil
import sys
from pathlib import Path

PAUSA = 0.25
MAX_CHARS = 34
FINAL = re.compile(r"[.?!…]$")
LIGACAO = {"a", "o", "as", "os", "e", "de", "da", "do", "das", "dos", "que", "um", "uma", "em", "no", "na",
           "nos", "nas", "pra", "para", "por", "com", "se", "ao", "à", "mas", "ou", "eu", "você", "seu", "sua"}


def janelas(txt):
    out = []
    for parte in (txt or "").split(","):
        parte = parte.strip()
        if parte:
            a, b = (float(x) for x in parte.split("-"))
            out.append((a, b))
    return out


def dentro(w, sem):
    meio = (w["t"] + w["f"]) / 2
    return any(a <= meio < b for a, b in sem)


def corrigir(txt, pares):
    for de, para in pares:
        txt = re.sub(r"(?<!\w)%s(?!\w)" % re.escape(de), para, txt)
    return txt


def agrupar(ws):
    grupos, atual = [], []
    for i, w in enumerate(ws):
        if atual:
            texto = " ".join(x["p"] for x in atual + [w])
            pausa = w["t"] - atual[-1]["f"]
            if pausa >= PAUSA or len(texto) > MAX_CHARS or FINAL.search(atual[-1]["p"]):
                levar = []
                # quebra por tamanho nao termina em artigo, preposicao ou conjuncao
                while pausa < PAUSA and len(atual) > 2 and atual[-1]["p"].lower().strip(",") in LIGACAO \
                        and not FINAL.search(atual[-1]["p"]):
                    levar.insert(0, atual.pop())
                grupos.append(atual)
                atual = levar
        atual.append(w)
    if atual:
        grupos.append(atual)
    # evita palavra solta: junta grupo de 1 palavra curta ao anterior se couber
    out = []
    for g in grupos:
        if out and len(g) == 1 and len(" ".join(x["p"] for x in out[-1] + g)) <= MAX_CHARS + 6 \
                and g[0]["t"] - out[-1][-1]["f"] < PAUSA:
            out[-1] = out[-1] + g
        else:
            out.append(g)
    return out


def main():
    ap = argparse.ArgumentParser(description="Rascunho das cues da legenda a partir do palavras.json.")
    ap.add_argument("--pasta", required=True, help="pasta da legenda (com palavras.json)")
    ap.add_argument("--palavras", default=None, help="padrao: <pasta>/palavras.json")
    ap.add_argument("--sem", default="", help="trechos sem legenda, tempo do video: a-b,c-d")
    ap.add_argument("--corrigir", default="", help="grafia: errado=certo,errado2=certo2")
    a = ap.parse_args()
    pasta = Path(a.pasta).expanduser().resolve()
    arq = Path(a.palavras).expanduser() if a.palavras else pasta / "palavras.json"
    if not arq.exists():
        sys.exit("falta %s: rode transcrever.py <montado> --json %s" % (arq, arq))
    ws = [w for w in comum.ler_json(arq) if w.get("p", "").strip()]
    sem = janelas(a.sem)
    pares = [tuple(x.split("=", 1)) for x in a.corrigir.split(",") if "=" in x]

    cues, k, grupo = [], 0, 0
    trecho = [w for w in ws if not dentro(w, sem)]
    blocos, atual = [], []
    for w in trecho:   # palavras separadas por um trecho "sem" nao se juntam
        if atual and any(atual[-1]["f"] <= x < w["t"] or atual[-1]["f"] < y <= w["t"] for x, y in sem):
            blocos.append(atual)
            atual = []
        atual.append(w)
    if atual:
        blocos.append(atual)
    for bloco in blocos:
        grupo += 1
        gs = agrupar(bloco)
        for i, g in enumerate(gs):
            k += 1
            ini = g[0]["t"]
            prox = gs[i + 1][0]["t"] if i + 1 < len(gs) else g[-1]["f"] + 0.25
            fim = max(g[-1]["f"], min(prox - 0.02, g[-1]["f"] + 0.6))
            cues.append({"id": "cc-%03d" % k, "de": round(ini, 2), "ate": round(fim, 2),
                         "texto": corrigir(" ".join(x["p"] for x in g), pares),
                         "papel": "setup", "enfase": "support", "zona": "rail", "grupo": "g%02d" % grupo})

    destino = pasta / "legenda.json"
    if destino.exists():
        shutil.copy2(destino, pasta / "legenda.json.bak")
        spec = comum.ler_json(destino)
    else:
        spec = {"video": "montado.mp4", "acento": "#F94E03", "trilho_base": 1590, "zonas": {},
                "shots": [], "herois": {}, "recortes": {}, "correcoes": [],
                "sem_legenda": "trechos onde a arte escreve a fala: %s" % (a.sem or "nenhum")}
    spec["cues"] = cues
    if pares:
        spec["correcoes"] = [{"de": de, "para": para, "confirmado": "pedido no rascunho"} for de, para in pares]
    comum.gravar_json(destino, spec, indent=1)
    longas = [c for c in cues if len(c["texto"]) > MAX_CHARS]
    print("%d legendas em %s (%d palavras, %d fora pelos trechos --sem)"
          % (len(cues), destino, len(ws), len(ws) - len(trecho)))
    if longas:
        print("acima de %d caracteres (divida ou aceite duas linhas): %s"
              % (MAX_CHARS, ", ".join(c["id"] for c in longas[:10])))
    print("proximo: marque enfase (anchor, letter, hero), zonas por insert e herois; depois gerar_legenda.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
