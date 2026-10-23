#!/usr/bin/env python3
"""Aprova ou reprova um recorte do sujeito antes de confiar nele para profundidade.

Gerar recorte nao e o mesmo que ter profundidade utilizavel. Este script responde
os tres criterios do `## Matte fitness test` com numero, no lugar de olho:

  1. A borda da mascara cai em cima de uma borda real da imagem?
     Onde a mascara termina, a imagem tem que mudar. Se a mascara acaba no meio de
     uma regiao lisa, ela esta inflada ou inventada ali, e o texto seria cortado
     por uma linha flutuando no vazio.

  2. Sobra mancha solta, longe do sujeito?
     O modelo le forma clara e vertical do fundo desfocado como uma segunda pessoa.

  3. A borda de cima e uma reta artificial?
     Assinatura de corte por altura. Texto cruzando isso le como borrao, nao como cabelo.

Erro que este script existe para impedir: produzir uma imagem inutil, olhar para
ela, e concluir alguma coisa mesmo assim.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import shutil
import subprocess
import sys
from collections import deque


def die(msg):
    sys.exit(f"erro: {msg}")


def probe(path, entries):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", f"stream={entries}", "-of", "csv=p=0", path],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        die(f"ffprobe falhou em {path}: {r.stderr.decode(errors='replace').strip()}")
    return r.stdout.decode().strip()


def plano(path, t, w, h, alpha=False, decoder=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(t)]
    if decoder:
        cmd += ["-c:v", decoder]
    vf = f"alphaextract,scale={w}:{h}" if alpha else f"scale={w}:{h},format=gray"
    cmd += ["-i", path, "-frames:v", "1", "-vf", vf,
            "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if len(r.stdout) < w * h:
        det = r.stderr.decode(errors="replace").strip().splitlines()
        die(f"nao consegui ler {'o alpha de ' if alpha else ''}{path} em t={t}s. "
            f"Detalhe: {det[0] if det else 'sem detalhe do ffmpeg'}")
    return r.stdout


def maior_componente(mask, w, h, thr):
    visto = bytearray(w * h)
    melhor, area_total = 0, 0
    for s in range(w * h):
        if mask[s] > thr:
            area_total += 1
        if mask[s] <= thr or visto[s]:
            continue
        fila, tam = deque([s]), 0
        visto[s] = 1
        while fila:
            i = fila.popleft()
            tam += 1
            y, x = divmod(i, w)
            for j, ok in ((i - 1, x > 0), (i + 1, x < w - 1), (i - w, y > 0), (i + w, y < h - 1)):
                if ok and not visto[j] and mask[j] > thr:
                    visto[j] = 1
                    fila.append(j)
        melhor = max(melhor, tam)
    return melhor, area_total


def topo_por_coluna(mask, w, h, thr):
    tops = []
    for x in range(w):
        t = None
        for y in range(h):
            if mask[y * w + x] > thr:
                t = y
                break
        tops.append(t)
    return tops


def analisa(fonte, matte, t_fonte, t_matte, w, thr, faixa):
    dims = probe(matte, "width,height").split(",")
    h = max(1, round(w * int(dims[1]) / int(dims[0])))
    dec = "libvpx-vp9" if probe(matte, "codec_name") == "vp9" else None

    mask = plano(matte, t_matte, w, h, alpha=True, decoder=dec)
    img = plano(fonte, t_fonte, w, h)

    tops = topo_por_coluna(mask, w, h, thr)
    cols = [(x, y) for x, y in enumerate(tops) if y is not None and faixa <= y < h - faixa]

    # 1. a borda cai em cima de mudanca real da imagem?
    contrastes = []
    for x, y in cols:
        acima = sum(img[(y - k) * w + x] for k in range(1, faixa + 1)) / faixa
        abaixo = sum(img[(y + k) * w + x] for k in range(1, faixa + 1)) / faixa
        contrastes.append(abs(acima - abaixo))
    contrastes.sort()
    mediana = contrastes[len(contrastes) // 2] if contrastes else 0.0

    # 2. quanto da mascara esta fora do corpo principal?
    maior, total = maior_componente(mask, w, h, thr)
    solto = 0.0 if total == 0 else 1 - maior / total

    # 3. a borda de cima e uma reta?
    # Reta artificial significa y EXATAMENTE constante ao longo de muitas colunas.
    # Tolerar um pixel de variacao confunde o topo arredondado de uma cabeca, que e
    # naturalmente chato no alto, com a linha de um corte por altura. Testado: com
    # tolerancia de 1px o caso bom marcava 43% e reprovava sem motivo.
    corrida = melhor_corrida = 0
    ant = None
    for _, y in cols:
        if ant is not None and y == ant:
            corrida += 1
            melhor_corrida = max(melhor_corrida, corrida)
        else:
            corrida = 1
        ant = y
    reta = 0.0 if not cols else melhor_corrida / len(cols)

    return {"t": t_fonte, "contrasteNaBorda": round(mediana, 1),
            "areaSolta": round(solto, 3), "bordaReta": round(reta, 3),
            "colunasMedidas": len(cols)}


def main():
    ap = argparse.ArgumentParser(
        description="Aprova ou reprova um recorte do sujeito para uso com profundidade.",
        epilog="exemplo: matte_fitness.py --fonte bruto.mp4 --matte recorte.webm --at 8.5,9.0,9.5 --matte-offset 7.55",
    )
    ap.add_argument("--fonte", required=True, help="video original")
    ap.add_argument("--matte", required=True, help="recorte com alpha")
    ap.add_argument("--at", required=True, help="instantes da COMPOSICAO, com movimento, separados por virgula")
    ap.add_argument("--matte-offset", type=float, default=0.0, help="segundo em que o recorte comeca (data-start)")
    ap.add_argument("--threshold", type=int, default=128, help="corte de opacidade 0-255 (padrao 128)")
    ap.add_argument("--largura", type=int, default=360, help="largura de analise (padrao 360)")
    ap.add_argument("--faixa", type=int, default=4, help="pixels amostrados de cada lado da borda (padrao 4)")
    ap.add_argument("--min-contraste", type=float, default=12.0,
                    help="contraste minimo aceitavel na borda, 0-255 (padrao 12)")
    ap.add_argument("--max-solto", type=float, default=0.04, help="area solta maxima (padrao 0.04)")
    ap.add_argument("--max-reta", type=float, default=0.25, help="fracao reta maxima da borda (padrao 0.25)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for exe in ("ffmpeg", "ffprobe"):
        if shutil.which(exe) is None:
            die(f"{exe} nao encontrado no PATH")

    try:
        tempos = [float(x) for x in args.at.split(",") if x.strip()]
    except ValueError:
        die("--at aceita so numeros separados por virgula")
    if len(tempos) < 3:
        print("aviso: a skill pede tres quadros COM MOVIMENTO; menos que isso nao decide nada\n")

    amostras = [analisa(args.fonte, args.matte, t, round(t - args.matte_offset, 3),
                        args.largura, args.threshold, args.faixa) for t in tempos]

    pior_contraste = min(a["contrasteNaBorda"] for a in amostras)
    pior_solto = max(a["areaSolta"] for a in amostras)
    pior_reta = max(a["bordaReta"] for a in amostras)

    falhas = []
    if pior_contraste < args.min_contraste:
        falhas.append(f"borda sem contraste ({pior_contraste} < {args.min_contraste}): "
                      "a mascara termina no meio de regiao lisa, ou seja, esta inflada ou inventada ali")
    if pior_solto > args.max_solto:
        falhas.append(f"mancha solta ({pior_solto:.1%} da area fora do corpo principal): "
                      "o modelo recortou algo que nao e o sujeito; tente scripts/clean_matte.py")
    if pior_reta > args.max_reta:
        falhas.append(f"borda de cima reta em {pior_reta:.0%} das colunas: "
                      "assinatura de corte por altura; texto cruzando isso le como borrao")

    if args.json:
        print(json.dumps({"amostras": amostras, "aprovado": not falhas, "falhas": falhas},
                         ensure_ascii=False, indent=2))
        return

    for a in amostras:
        print(f"  t={a['t']:<7} contraste na borda {a['contrasteNaBorda']:>5}   "
              f"area solta {a['areaSolta']:>6.1%}   borda reta {a['bordaReta']:>5.0%}   "
              f"({a['colunasMedidas']} colunas)")
    print()
    if falhas:
        print("REPROVADO para profundidade:")
        for f in falhas:
            print(f"  - {f}")
        print("\nA palavra grande vai na frente, em espaco negativo verificado. "
              "Isso e resultado pleno, nao consolo.")
    else:
        print("APROVADO para profundidade nos tres criterios.")


if __name__ == "__main__":
    main()
