#!/usr/bin/env python3
"""Mede quanto de uma palavra-heroi o sujeito realmente cobre.

A skill exige um `occlusionBudget` por heroi de fundo, entre 0,10 e 0,22 como
alvo e 0,35 como teto duro. Sem medir, esse numero e chute, e o erro cai dos
dois lados: coberto demais a palavra some, coberto de menos a profundidade nao
aparece e o texto fica boiando.

Mede area de GLIFO, nao de caixa. A caixa de uma palavra e quase toda vazia
entre as letras, entao medir caixa superestima a cobertura e reprova
posicionamento bom.

Entradas: a camada de tipografia com alpha (o mesmo `.webm` que o pipeline ja
renderiza para compor) e o recorte do sujeito. A intersecao dos dois canais
alpha e a resposta exata.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import shutil
import subprocess
import sys

ALVO_MIN, ALVO_MAX, TETO = 0.10, 0.22, 0.35


def die(msg):
    sys.exit(f"erro: {msg}")


def probe(path, entries, stream=True):
    alvo = "stream" if stream else "format"
    cmd = ["ffprobe", "-v", "error"]
    if stream:
        cmd += ["-select_streams", "v:0"]
    cmd += ["-show_entries", f"{alvo}={entries}", "-of", "csv=p=0", path]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        die(f"ffprobe falhou em {path}: {r.stderr.decode(errors='replace').strip()}")
    return r.stdout.decode().strip()


def alpha(path, t, w, h):
    codec = probe(path, "codec_name")
    cmd = ["ffmpeg", "-v", "error", "-ss", str(t)]
    if codec == "vp9":
        cmd += ["-c:v", "libvpx-vp9"]
    cmd += ["-i", path, "-frames:v", "1",
            "-vf", f"alphaextract,scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if len(r.stdout) < w * h:
        det = r.stderr.decode(errors="replace").strip().splitlines()
        die(f"nao consegui ler o alpha de {path} em t={t}s. "
            f"O arquivo tem canal alpha e esse instante existe nele? "
            f"Detalhe: {det[0] if det else 'sem detalhe'}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser(
        description="Mede a fracao da area de glifo coberta pelo sujeito.",
        epilog="exemplo: occlusion.py --tipo camada-tras.webm --matte recorte.webm "
               "--at 0.5,1.0 --matte-offset 7.55",
    )
    ap.add_argument("--tipo", required=True,
                    help="camada de tipografia com alpha (so o texto que fica atras)")
    ap.add_argument("--matte", required=True, help="recorte do sujeito, com alpha")
    ap.add_argument("--at", required=True,
                    help="instantes em segundos na linha do tempo da COMPOSICAO, separados por virgula")
    ap.add_argument("--tipo-offset", type=float, default=0.0,
                    help="segundo da composicao em que a camada de tipografia comeca (padrao 0)")
    ap.add_argument("--matte-offset", type=float, default=0.0,
                    help="segundo da composicao em que o recorte comeca (o data-start dele)")
    ap.add_argument("--threshold", type=int, default=128,
                    help="corte de opacidade do SUJEITO, 0-255 (padrao 128). O glifo entra pesado pela propria opacidade.")
    ap.add_argument("--largura", type=int, default=540,
                    help="largura de amostragem; maior e mais preciso e mais lento (padrao 540)")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    args = ap.parse_args()

    for exe in ("ffmpeg", "ffprobe"):
        if shutil.which(exe) is None:
            die(f"{exe} nao encontrado no PATH")

    try:
        tempos = [float(x) for x in args.at.split(",") if x.strip()]
    except ValueError:
        die("--at aceita so numeros separados por virgula")
    if not tempos:
        die("--at nao pode ficar vazio")

    dims = probe(args.tipo, "width,height").split(",")
    w = args.largura
    h = max(1, round(w * int(dims[1]) / int(dims[0])))

    saida = []
    for t in tempos:
        g = alpha(args.tipo, round(t - args.tipo_offset, 3), w, h)
        m = alpha(args.matte, round(t - args.matte_offset, 3), w, h)
        thr = args.threshold
        # Peso pela opacidade do proprio glifo, nao contagem binaria: um heroi de
        # vidro tem miolo em ~44% de opacidade, abaixo de qualquer corte razoavel.
        # Contando binario, so a borda entraria na conta e a medida sairia errada.
        glifo = coberto = 0
        for i in range(w * h):
            a = g[i]
            if a > 8:
                glifo += a
                if m[i] > thr:
                    coberto += a
        if glifo == 0:
            saida.append({"t": t, "erro": "nenhum glifo visivel neste instante"})
            continue
        frac = coberto / glifo
        if frac > TETO:
            veredito, acao = "REPROVADO", "suba ou reduza a palavra: passou do teto de 0,35"
        elif frac < ALVO_MIN:
            veredito, acao = "fraco", "desca a palavra: a profundidade quase nao aparece"
        elif frac > ALVO_MAX:
            veredito, acao = "forte", "aceitavel, mas confira se a grafia continua obvia"
        else:
            veredito, acao = "ok", "dentro da faixa alvo"
        saida.append({"t": t, "occlusionBudget": round(frac, 3),
                      "glifoPeso": glifo, "cobertoPeso": coberto,
                      "veredito": veredito, "acao": acao})

    validos = [s for s in saida if "occlusionBudget" in s]
    pior = max((s["occlusionBudget"] for s in validos), default=None)

    if args.json:
        print(json.dumps({"amostras": saida, "pior": pior}, ensure_ascii=False, indent=2))
        return

    for s in saida:
        if "erro" in s:
            print(f"  t={s['t']:<7} {s['erro']}")
        else:
            print(f"  t={s['t']:<7} {s['occlusionBudget']:.1%} coberto  [{s['veredito']}]  {s['acao']}")
    if pior is not None:
        print(f"\npior caso: {pior:.1%}   alvo 10-22%, teto 35%")
        if pior > TETO:
            print("REPROVADO: reposicione antes de seguir.")


if __name__ == "__main__":
    main()
