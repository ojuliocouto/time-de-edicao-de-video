#!/usr/bin/env python3
"""Gera lista-inserts.json (tempo do ORIGINAL) a partir de fabrica/janelas.json (tempo do FINAL).

    python montar_lista.py --pasta <pasta-do-video>
    python plano.py inserts --pasta <pasta-do-video> --arquivo <pasta>/lista-inserts.json --substituir

A fabrica trabalha no tempo do video final, que e o que ela ve e o que o
agente transcreve. O plano.json so aceita tempo do original. Converter na mao
foi onde mais se errou: este script usa a mesma conta do render.

Tambem avisa, no tempo do FINAL, o que ela reprovou antes:
- rosto voltando por menos de 1 s entre dois inserts (parece falha, nao corte);
- insert cujo arquivo e curto demais para a janela (o rosto aparece no fim);
- arquivo que perde mais da metade (so um pedaco dele vai aparecer).
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import sys
from pathlib import Path

from tempo import Tempo

ROSTO_MIN = 1.0


def duracao(arq):
    r = comum.rodar(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                     str(arq)], checar=False)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description="janelas.json (final) -> lista-inserts.json (original)")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--saida", default=None, help="padrao: <pasta>/lista-inserts.json")
    a = ap.parse_args()
    pasta = Path(a.pasta).expanduser().resolve()
    t = Tempo(pasta)
    js = comum.ler_json(pasta / "fabrica" / "janelas.json")

    lista, avisos = [], []
    for j in js:
        arq = Path(os.path.expanduser(j.get("arquivo") or str(pasta / "fabrica" / "renders" / (j["nome"] + ".mp4"))))
        if not arq.is_absolute():
            arq = pasta / arq
        if "de_orig" in j:
            de, ate = float(j["de_orig"]), float(j["ate_orig"])
            fde, fate = t.final(de), t.final(ate)
        else:
            fde, fate = float(j["de"]), float(j["ate"])
            de, ate = t.orig(fde), t.orig(fate)
            if fde <= 0.001:
                de = 0.0
        item = {"de": round(de, 3), "ate": round(ate, 3), "arquivo": str(arq),
                "formato": j.get("formato", "tela_cheia"), "origem_ini": float(j.get("origem_ini", 0.0)),
                "motivo": j.get("motivo", "insert %s" % j["nome"])}
        for extra in ("subir", "altura_pessoa", "enquadrar"):
            if extra in j:
                item[extra] = j[extra]
        lista.append((fde, fate, j["nome"], item))
        if not arq.exists():
            avisos.append("%s: o arquivo ainda nao existe (%s)" % (j["nome"], arq))
            continue
        d = duracao(arq)
        if d and d > 0.05:
            precisa = fate - fde
            sobra = d - item["origem_ini"]
            if sobra < precisa - 0.05:
                avisos.append("%s: a janela pede %.2fs e o arquivo da %.2fs. O rosto aparece no fim."
                              % (j["nome"], precisa, sobra))
            elif precisa < d / 2:
                avisos.append("%s: so %.2fs de um arquivo de %.2fs vao aparecer. Era isso?"
                              % (j["nome"], precisa, d))

    lista.sort(key=lambda x: x[0])
    for (a0, b0, n0, _), (a1, b1, n1, _) in zip(lista, lista[1:]):
        vao = a1 - b0
        if vao < -0.02:
            avisos.append("%s e %s se sobrepoem no final (%.2f-%.2f e %.2f-%.2f)" % (n0, n1, a0, b0, a1, b1))
        elif 0.02 < vao < ROSTO_MIN:
            avisos.append("%.2fs de rosto entre %s e %s: encoste os dois (estique o primeiro ou "
                          "antecipe o segundo) e avise ela" % (vao, n0, n1))

    saida = Path(a.saida).expanduser() if a.saida else pasta / "lista-inserts.json"
    comum.gravar_json(saida, [x[3] for x in lista])
    print("%-24s %8s %8s   %8s %8s  %s" % ("insert", "final", "", "original", "", "formato"))
    for fde, fate, nome, it in lista:
        print("%-24s %8.2f %8.2f   %8.3f %8.3f  %s" % (nome, fde, fate, it["de"], it["ate"], it["formato"]))
    print("\n%s" % saida)
    if avisos:
        print("\nATENCAO:")
        for x in avisos:
            print("  - " + x)
    recorte = [it for _, _, _, it in lista if it["formato"] in ("vazado_maior", "vazado_pequeno", "react")]
    if recorte:
        # folga de 0,4 s no FINAL antes do insert: o filtro da borda mistura 3
        # quadros, e uma pausa cortada logo antes do insert comia a folga da
        # mascara (cabeca transparente nos 2 primeiros quadros, validacao)
        js = ",".join("%.2f-%.2f" % (t.orig(max(0.0, fde - 0.4)), t.orig(fate + 0.2))
                      for fde, fate, _, it in lista if it in recorte)
        print("\nformatos com recorte: gere a mascara ANTES do plano.py inserts")
        print("  mascara.py <bruto> -o \"%s\" --janelas %s" % (pasta / "analise" / "matte.mp4", js))
    print("\nproximo: plano.py inserts --pasta \"%s\" --arquivo \"%s\" --substituir" % (pasta, saida))
    return 0


if __name__ == "__main__":
    sys.exit(main())
