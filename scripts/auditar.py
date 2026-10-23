#!/usr/bin/env python3
"""auditar.py - confere se o video sobreviveu aos cortes com sentido e com imagem.

    python3 auditar.py --pasta <pasta-de-trabalho>

Roda DEPOIS de montar o plano e ANTES de mandar para aprovacao. Duas auditorias
independentes:

1. SENTIDO. Reconstroi o texto que sobrou depois dos cortes e procura abertura
   truncada, encerramento truncado e emenda quebrada.

2. IMAGEM. Varre a filmagem procurando trechos com compressao destruida.

Regra que vale para as duas: **separar o que o corte causou do que ja vinha
assim no bruto.** Defeito de origem nao se conserta cortando, e as vezes cortar
piora. Num teste real o video comecava em "e liberar um ingresso", no meio da
frase, e isso era do arquivo original: cortar teria destruido mais ainda.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Palavras que nao abrem um raciocinio. Comecar por uma delas quase sempre
# significa que falta o que vinha antes.
ABERTURA_TRUNCADA = (
    "e", "mas", "entao", "que", "porque", "pois", "ai", "ou", "nem", "logo",
    "portanto", "so", "tambem", "ainda", "dai", "quando", "se", "como", "por",
    "pra", "para", "com", "sem", "de", "da", "do", "em", "no", "na", "ao",
)
FIM_DE_FRASE = ".!?…\"'"
BLOCO = 8              # tamanho do bloco do H.264
MARGEM_BLOCO = 0.06    # quanto a blocagem precisa passar da mediana do proprio video
AMOSTRAS = 25          # quantos instantes varrer na auditoria de imagem


def sem_acento(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def limpo(p):
    return sem_acento(re.sub(r"[^\w\s]", "", p["texto"]).strip())


def dentro(t, manter):
    return any(a - 0.01 <= t <= b + 0.01 for a, b in manter)


# ------------------------------------------------------------- sentido

def auditar_sentido(plano, palavras):
    manter = plano["corte"]["manter"]
    mantidas = [p for p in palavras if dentro((p["ini"] + p["fim"]) / 2.0, manter)]
    achados = []
    if not mantidas:
        return ["nenhuma palavra sobreviveu aos cortes"], "", ""

    abre_final = " ".join(p["texto"] for p in mantidas[:12])
    fecha_final = " ".join(p["texto"] for p in mantidas[-12:])

    # --- abertura
    prim = mantidas[0]
    if limpo(prim) in ABERTURA_TRUNCADA:
        de_origem = palavras[0]["i"] == prim["i"]
        if de_origem:
            achados.append(
                "ABERTURA: o video comeca em %r, que nao abre raciocinio, e isso "
                "JA VEM DO BRUTO, nao foi corte. Cortar aqui pioraria. "
                "AVISE a pessoa e pergunte se ela quer assim mesmo." % prim["texto"])
        else:
            achados.append(
                "ABERTURA: o corte deixou o video comecando em %r, que nao abre "
                "raciocinio. O bruto comecava em %r. Reveja o primeiro corte."
                % (prim["texto"], palavras[0]["texto"]))

    # --- encerramento
    ult = mantidas[-1]
    if not ult["texto"].strip().endswith(tuple(FIM_DE_FRASE)):
        de_origem = palavras[-1]["i"] == ult["i"]
        if de_origem:
            achados.append(
                "ENCERRAMENTO: o video termina em %r, sem fechar a frase, e isso "
                "JA VEM DO BRUTO. AVISE a pessoa." % ult["texto"])
        else:
            achados.append(
                "ENCERRAMENTO: o corte deixou o video terminando em %r, sem fechar "
                "a frase. Reveja o ultimo corte." % ult["texto"])

    # --- emendas: so os cortes que removem fala
    idx = {p["i"]: k for k, p in enumerate(mantidas)}
    for c in plano["corte"]["removidos"]:
        if c["tipo"] == "pausa":
            continue
        antes = [p for p in mantidas if p["fim"] <= c["de"] + 0.01][-4:]
        depois = [p for p in mantidas if p["ini"] >= c["ate"] - 0.01][:4]
        emenda = " ".join(p["texto"] for p in antes + depois)
        achados.append("EMENDA em %.2f-%.2f (%s), leia em voz alta: \"...%s...\""
                       % (c["de"], c["ate"], c["tipo"], emenda))
    return achados, abre_final, fecha_final


# -------------------------------------------------------------- imagem

def blocagem(arq, t, w, h):
    """Mede o quanto a imagem esta quebrada em blocos de 8 pixels, que e a
    assinatura de compressao destruida: compara o degrau medio nas fronteiras
    de bloco com o degrau medio no meio do bloco.

    Precisa medir na RESOLUCAO NATIVA. Uma primeira versao reduzia a imagem
    antes de medir, o que desalinha a grade de 8 pixels e apaga justamente o
    sinal procurado: dava 1,08 em todo lugar, inclusive no trecho quebrado."""
    d = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(arq), "-frames:v", "1",
         "-vf", "format=gray", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, stdin=subprocess.DEVNULL).stdout
    if len(d) < w * h:
        return None
    borda = meio = 0
    nb = nm = 0
    for y in range(16, h - 16, 16):
        base = y * w
        for x in range(BLOCO, w - BLOCO):
            g = abs(d[base + x] - d[base + x - 1])
            if x % BLOCO == 0:
                borda += g; nb += 1
            else:
                meio += g; nm += 1
    if not nb or not nm or meio == 0:
        return None
    return (borda / nb) / max(0.01, meio / nm)


def taxa_de_bits(fonte):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=bit_rate", "-show_entries",
                        "format=bit_rate,size,duration", "-of", "json", str(fonte)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    try:
        d = json.loads(r.stdout)
        b = d["streams"][0].get("bit_rate") or d["format"].get("bit_rate")
        return int(b) / 1e6 if b else None
    except Exception:
        return None


def auditar_imagem(plano, fonte):
    """Devolve os trechos cuja blocagem se destaca do resto DO PROPRIO video.

    Limiar absoluto nao serve: a razao depende do quanto a imagem tem de
    detalhe. No material de teste a mediana era 1,33 e o trecho quebrado dava
    1,44, oito por cento acima. E pouco, entao a deteccao e fraca de proposito:
    ela levanta suspeita para conferir no olho, nao da veredito."""
    manter = plano["corte"]["manter"]
    dur = plano["meta"]["duracao"]
    w, h = plano["meta"]["largura"], plano["meta"]["altura"]
    passo = max(0.5, dur / AMOSTRAS)
    medidas = []
    t = passo / 2
    while t < dur:
        if dentro(t, manter):
            r = blocagem(fonte, t, w, h)
            if r:
                medidas.append((round(t, 2), r))
        t += passo
    if len(medidas) < 5:
        return [], None
    ord_ = sorted(v for _, v in medidas)
    mediana = ord_[len(ord_) // 2]
    ruins = [(t, round(v, 3)) for t, v in medidas if v > mediana * (1 + MARGEM_BLOCO)]
    return sorted(ruins, key=lambda x: -x[1]), round(mediana, 3)


def main():
    ap = argparse.ArgumentParser(description="Audita sentido e imagem antes da aprovacao")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--sem-imagem", action="store_true",
                    help="pula a auditoria de imagem, que e a mais lenta")
    args = ap.parse_args()

    pasta = Path(args.pasta).expanduser()
    plano = json.loads((pasta / "plano.json").read_text(encoding="utf-8"))
    palavras = json.loads((pasta / "analise" / "palavras.json").read_text(encoding="utf-8"))
    fonte = Path(plano["fonte"]).expanduser()

    achados, abre, fecha = auditar_sentido(plano, palavras)

    print("=" * 68)
    print("COMO O VIDEO COMECA:  \"%s...\"" % abre)
    print("COMO O VIDEO TERMINA: \"...%s\"" % fecha)
    print("=" * 68)

    problemas = 0
    if achados:
        print("\nSENTIDO:")
        for a in achados:
            print("  - %s" % a)
            if a.startswith(("ABERTURA", "ENCERRAMENTO")):
                problemas += 1
    else:
        print("\nSENTIDO: abertura e encerramento fecham frase, nenhum corte de fala.")

    if not args.sem_imagem:
        if not fonte.exists():
            print("\nIMAGEM: video original nao encontrado, auditoria pulada.")
        else:
            ruins, mediana = auditar_imagem(plano, fonte)
            mbps = taxa_de_bits(fonte)
            print("\nIMAGEM:")
            if mbps:
                folga = mbps / (plano["meta"]["largura"] * plano["meta"]["altura"] / 2073600.0)
                print("  taxa de bits do bruto: %.1f Mbps%s" %
                      (mbps, "  (baixa para 1080 vertical; abaixo de 6 costuma "
                             "quebrar em cena escura com ruido)" if folga < 6 else ""))
            if ruins:
                problemas += 1
                print("  %d trechos se destacam do resto do proprio video (mediana %.2f):"
                      % (len(ruins), mediana))
                for tt, r in ruins[:8]:
                    print("    - %.2fs do original, blocagem %.2f (%+.0f%% da mediana)"
                          % (tt, r, 100 * (r / mediana - 1)))
                if len(ruins) > 8:
                    print("    ... e mais %d" % (len(ruins) - 8))
                print("  Isso vem do arquivo de origem e nao se conserta na edicao.")
                print("  CONFIRA no olho e AVISE a pessoa, para ela nao achar que foi a skill.")
            else:
                print("  nenhum trecho se destaca. mediana de blocagem %.2f." % (mediana or 0))

    print()
    if problemas:
        print("%d ponto(s) para AVISAR a pessoa antes da aprovacao." % problemas)
        print("Avisar, nao consertar sozinho: defeito de origem as vezes piora com corte.")
        sys.exit(1)
    print("nada a sinalizar.")


if __name__ == "__main__":
    main()
