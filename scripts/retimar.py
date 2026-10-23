#!/usr/bin/env python3
"""Retima uma composicao quando a narracao oficial chega.

O modo audio resolve METADE do problema: ele acha os tempos da fala. A outra
metade e que os tempos ficam travados no HTML, dezenas deles, e refazer na mao
e lento e e onde se erra.

A REGRA: desloca os DISPAROS, preserva as DURACOES.

Se uma batida entra 0,4 s mais cedo, tudo que dispara dentro dela anda 0,4 s
junto. Mas um carimbo de 0,34 s continua com 0,34 s: esticar o gesto porque a
frase encolheu estraga o que foi ajustado no olho.

    # so mostra o que mudaria
    python3 retimar.py inserts/A/index.html --inicio 0 \
        --de 0,3.32,5.96,10.22 --para 0,3.10,5.61,9.74

    # aplica, guardando .bak
    python3 retimar.py ... --aplicar

As listas sao as FRONTEIRAS das batidas em tempo absoluto do reel, e --inicio e
onde esta composicao comeca. Tire os dois de `transcrever.py`.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import re
import shutil
import sys

DISPARO = re.compile(r"(,\s*)(\d+\.?\d*)(\s*\);)")
# Uma linha marcada com // @tempos tem TODOS os seus decimais tratados como
# posicao de timeline. Existe porque tempo dentro de array nao cai no padrao
# acima, e reescrever numero cegamente corromperia tabela de valor: o GAPS do
# ritmo de token e o CONTA dos indicadores sao numeros que NAO sao tempo.
MARCA = "@tempos"
DECIMAL = re.compile(r"\d+\.\d+")


# Um corte e quase sempre autorado um triz ANTES da fronteira da batida, para
# a imagem trocar junto com a palavra. Sem tolerancia ele fica na batida
# anterior e nao anda, enquanto tudo depois dele anda: a cena aparece atrasada
# e o conteudo dela ja animou invisivel. Custou exatamente isso uma vez.
BEIRADA = 0.30


def mapear(t, de, para):
    """Acha a batida de t e devolve o tempo deslocado. Um disparo ate BEIRADA
    antes de uma fronteira e tratado como pertencente a batida SEGUINTE."""
    for i in range(1, len(de)):
        if de[i] - BEIRADA <= t < de[i]:
            return t + (para[i] - de[i]), i
    for i in range(len(de) - 1):
        if de[i] <= t < de[i + 1]:
            return t + (para[i] - de[i]), i
    if t >= de[-1]:
        return t + (para[-1] - de[-1]), len(de) - 1
    return t + (para[0] - de[0]), 0


def main():
    ap = argparse.ArgumentParser(description="Retima uma composicao para uma narracao nova.")
    ap.add_argument("html")
    ap.add_argument("--inicio", type=float, required=True,
                    help="onde esta composicao comeca, em tempo do reel")
    ap.add_argument("--de", required=True, help="fronteiras das batidas, hoje")
    ap.add_argument("--para", required=True, help="fronteiras das batidas, novas")
    ap.add_argument("--aplicar", action="store_true", help="escreve o arquivo (guarda .bak)")
    a = ap.parse_args()

    if not os.path.exists(a.html):
        print(f"erro: nao achei {a.html}", file=sys.stderr)
        return 2
    de = [float(x) for x in a.de.split(",")]
    para = [float(x) for x in a.para.split(",")]
    if len(de) != len(para):
        print("erro: --de e --para precisam ter o mesmo numero de fronteiras.", file=sys.stderr)
        return 2
    if len(de) < 2:
        print("erro: sao precisas ao menos duas fronteiras.", file=sys.stderr)
        return 2

    fonte = open(a.html, encoding="utf-8").read()
    mudancas = []

    def troca_nu(antigo):
        abs_novo, batida = mapear(a.inicio + antigo, de, para)
        novo = round(abs_novo - a.inicio, 3)
        if abs(novo - antigo) > 0.0005:
            mudancas.append((antigo, novo, batida))
        return novo

    def troca(m):
        antigo = float(m.group(2))
        abs_antigo = a.inicio + antigo
        abs_novo, batida = mapear(abs_antigo, de, para)
        novo = round(abs_novo - a.inicio, 3)
        if abs(novo - antigo) > 0.0005:
            mudancas.append((antigo, novo, batida))
        return f"{m.group(1)}{novo:g}{m.group(3)}"

    saida = DISPARO.sub(troca, fonte)

    # e as linhas marcadas explicitamente
    linhas = saida.split("\n")
    for i, linha in enumerate(linhas):
        if MARCA in linha:
            linhas[i] = DECIMAL.sub(
                lambda m: f"{troca_nu(float(m.group(0))):g}", linha)
    saida = "\n".join(linhas)

    dur_antiga = de[-1] - de[0]
    dur_nova = para[-1] - para[0]
    print(f"{os.path.basename(a.html)}")
    print(f"  disparos deslocados ... {len(mudancas)}")
    print(f"  duracao da peca ....... {dur_antiga:.2f}s  ->  {dur_nova:.2f}s")
    print(f"  duracoes de gesto ..... preservadas (nenhuma tocada)")
    marcadas = sum(1 for l in fonte.split("\n") if MARCA in l)
    print(f"  linhas com {MARCA} ..... {marcadas}")

    # avisa sobre decimais que ficaram de fora, para nao passar batido
    soltos = []
    for i, l in enumerate(fonte.split("\n"), 1):
        if MARCA in l or "//" in l.strip()[:2]:
            continue
        if DECIMAL.search(l) and DISPARO.search(l) is None and (
                ".forEach" in l or l.strip().startswith("const ") and "[" in l):
            soltos.append((i, l.strip()[:74]))
    if soltos:
        print(f"\n  NAO TOCADAS, confira se alguma e tempo e marque com {MARCA}:")
        for i, l in soltos:
            print(f"    linha {i}: {l}")

    if mudancas:
        print(f"\n  {'antes':>8}{'depois':>9}{'delta':>8}   batida")
        for antigo, novo, b in sorted(mudancas)[:40]:
            print(f"  {antigo:>8.2f}{novo:>9.2f}{novo-antigo:>+8.2f}   {b+1}")
        if len(mudancas) > 40:
            print(f"  ... e mais {len(mudancas)-40}")

    # aviso: batida que encolheu pode fazer gesto vazar para a proxima
    print()
    for i in range(len(de) - 1):
        antes, agora = de[i+1] - de[i], para[i+1] - para[i]
        if agora < antes - 0.15:
            print(f"  ATENCAO batida {i+1} encolheu {antes:.2f}s -> {agora:.2f}s. "
                  f"Confira se algum gesto vaza para a seguinte.")

    if not a.aplicar:
        print("\n  simulacao. Rode de novo com --aplicar para escrever.")
        return 0

    shutil.copy2(a.html, a.html + ".bak")
    with open(a.html, "w", encoding="utf-8") as fh:
        fh.write(saida)
    print(f"\n  escrito. Original em {os.path.basename(a.html)}.bak")
    print("  Agora: lint, check, render, medir_ritmo, e OLHE os prints.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
