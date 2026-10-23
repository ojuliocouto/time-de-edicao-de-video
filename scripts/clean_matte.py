#!/usr/bin/env python3
"""Limpa um recorte do sujeito, removendo o que a segmentacao inventou no fundo.

O u2net confunde formas do fundo desfocado (prateleira, luminaria, coluna clara)
com uma segunda pessoa e devolve manchas soltas alem do sujeito. Duas estrategias, combinaveis:

  --seed-edge   mantem so a regiao ligada a uma borda do quadro (o sujeito real
                encosta na de baixo, porque os ombros saem por ela). So resolve
                quando a mancha esta solta; se ela encostar no sujeito, sobrevive.

  --clip-above  zera tudo acima de uma altura medida, ANTES do preenchimento.
                Usadas juntas, resolvem o caso em que a mancha esta grudada na
                cabeca: o corte rompe a ponte, e o preenchimento descarta o resto
                que ficou solto abaixo da linha. E a saida quando a mancha
                esta grudada na cabeca, que e o caso comum: a palavra-heroi fica
                acima do sujeito, entao qualquer alpha acima da linha do cabelo e
                justamente o que estraga a profundidade. Meca o topo do cabelo em
                varios instantes e use o menor valor menos uma folga.

Nenhuma das duas resolve tudo. Se houver outra pessoa de verdade no quadro,
nenhuma regra salva. Confira a saida.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import shutil
import subprocess
import sys
from collections import deque

EDGES = ("bottom", "top", "left", "right")


def die(msg):
    sys.exit(f"erro: {msg}")


def probe(path, entries):
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", f"stream={entries}", "-of", "csv=p=0", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
     stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        die(f"ffprobe falhou em {path}: {res.stderr.decode(errors='replace').strip()}")
    return res.stdout.decode().strip()


def decoder_for(codec):
    return ["-c:v", "libvpx-vp9"] if codec == "vp9" else []


def seed_indices(w, h, edge, depth=2):
    if edge == "bottom":
        return [y * w + x for y in range(max(0, h - depth), h) for x in range(w)]
    if edge == "top":
        return [y * w + x for y in range(min(depth, h)) for x in range(w)]
    if edge == "left":
        return [y * w + x for y in range(h) for x in range(min(depth, w))]
    return [y * w + x for y in range(h) for x in range(max(0, w - depth), w)]


def keep_mask(frame, w, h, threshold, edge):
    """Flood fill a partir da borda escolhida. Devolve bytearray 0/255."""
    keep = bytearray(w * h)
    fila = deque()
    for i in seed_indices(w, h, edge):
        if frame[i] > threshold and not keep[i]:
            keep[i] = 255
            fila.append(i)

    if not fila:
        return None  # nada encosta na borda: nao ha o que decidir

    while fila:
        i = fila.popleft()
        y, x = divmod(i, w)
        if x > 0 and frame[i - 1] > threshold and not keep[i - 1]:
            keep[i - 1] = 255; fila.append(i - 1)
        if x < w - 1 and frame[i + 1] > threshold and not keep[i + 1]:
            keep[i + 1] = 255; fila.append(i + 1)
        if y > 0 and frame[i - w] > threshold and not keep[i - w]:
            keep[i - w] = 255; fila.append(i - w)
        if y < h - 1 and frame[i + w] > threshold and not keep[i + w]:
            keep[i + w] = 255; fila.append(i + w)

    # dilata uma celula para nao raspar a borda do sujeito ao voltar para o tamanho real
    dil = bytearray(keep)
    for i in range(w * h):
        if keep[i]:
            continue
        y, x = divmod(i, w)
        if ((x > 0 and keep[i - 1]) or (x < w - 1 and keep[i + 1])
                or (y > 0 and keep[i - w]) or (y < h - 1 and keep[i + w])):
            dil[i] = 255
    return dil


def main():
    ap = argparse.ArgumentParser(
        description="Remove manchas inventadas pela segmentacao, mantendo so o sujeito ligado a uma borda.",
        epilog="exemplo: clean_matte.py cc-subject-01.webm -o cc-subject-01-limpo.webm",
    )
    ap.add_argument("matte", help="recorte com alpha (.webm VP9 ou .mov)")
    ap.add_argument("-o", "--output", required=True, help="recorte limpo, .webm")
    ap.add_argument("--seed-edge", default="bottom", choices=EDGES,
                    help="borda em que o sujeito real encosta (padrao bottom)")
    ap.add_argument("--clip-above", type=int, default=None, metavar="Y",
                    help="zera todo alpha acima desta altura, em px da composicao")
    ap.add_argument("--no-seed-edge", action="store_true",
                    help="desliga o preenchimento por borda, usando so --clip-above")
    ap.add_argument("--threshold", type=int, default=40,
                    help="opacidade minima para contar como sujeito, 0-255 (padrao 40)")
    ap.add_argument("--sample-width", type=int, default=270,
                    help="largura de analise; menor e mais rapido (padrao 270)")
    ap.add_argument("--report-only", action="store_true",
                    help="so informar quanto seria removido, sem gravar")
    args = ap.parse_args()

    for exe in ("ffmpeg", "ffprobe"):
        if shutil.which(exe) is None:
            die(f"{exe} nao encontrado no PATH")
    if not os.path.isfile(args.matte):
        die(f"nao achei {args.matte}")

    codec = probe(args.matte, "codec_name")
    dims = probe(args.matte, "width,height").split(",")
    fps = probe(args.matte, "r_frame_rate").split(",")[0]
    full_w, full_h = int(dims[0]), int(dims[1])
    w = args.sample_width
    h = max(1, round(w * full_h / full_w))

    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", *decoder_for(codec), "-i", args.matte,
         "-vf", f"alphaextract,scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
     stdin=subprocess.DEVNULL)

    mask_path = os.path.splitext(args.output)[0] + ".keepmask.mkv"
    enc = None
    if not args.report_only:
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray",
             "-s", f"{w}x{h}", "-r", fps, "-i", "-",
             "-c:v", "ffv1", mask_path],
            stdin=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    corte_linha = None
    if args.clip_above is not None:
        if not 0 < args.clip_above < full_h:
            die(f"--clip-above precisa ficar entre 1 e {full_h - 1}")
        corte_linha = round(args.clip_above * h / full_h)
        print(f"cortando alpha acima de y={args.clip_above} da composicao "
              f"(linha {corte_linha} de {h} na analise)")

    frame_bytes = w * h
    n = 0
    sujos = 0
    removido_total = 0.0
    cheio = bytes([255]) * frame_bytes

    while True:
        buf = dec.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        n += 1
        # o corte por altura vem PRIMEIRO: ele rompe a ponte entre a mancha e o
        # sujeito, e so entao o preenchimento por borda consegue descartar o resto
        analise = buf
        if corte_linha is not None:
            analise = bytearray(buf)
            for i in range(min(corte_linha, h) * w):
                analise[i] = 0

        if args.no_seed_edge:
            km = bytearray(cheio)
            if corte_linha is not None:
                for i in range(min(corte_linha, h) * w):
                    km[i] = 0
        else:
            km = keep_mask(analise, w, h, args.threshold, args.seed_edge)
            if km is None:
                km = bytearray(cheio)
                if corte_linha is not None:
                    for i in range(min(corte_linha, h) * w):
                        km[i] = 0
        antes = sum(1 for v in buf if v > args.threshold)
        depois = sum(1 for i, v in enumerate(buf) if v > args.threshold and km[i])
        if antes and depois < antes:
            sujos += 1
            removido_total += (antes - depois) / antes
        if enc:
            enc.stdin.write(bytes(km))

    dec.wait()
    if enc:
        enc.stdin.close()
        enc.wait()

    if n == 0:
        die("nenhum quadro lido; confira se o arquivo tem canal alpha")

    media = (removido_total / sujos * 100) if sujos else 0.0
    print(f"quadros analisados  {n}")
    print(f"quadros sujos       {sujos} ({100 * sujos / n:.0f}%)")
    print(f"remocao media       {media:.1f}% da area nesses quadros")

    if args.report_only:
        if os.path.exists(mask_path):
            os.remove(mask_path)
        return

    if sujos == 0:
        print("\nnada a limpar: o recorte ja estava integro.")
        os.remove(mask_path)
        return

    compor = [
        "ffmpeg", "-y", "-v", "error", *decoder_for(codec), "-i", args.matte,
        "-i", mask_path,
        "-filter_complex",
        "[0:v]split=2[v1][v2];"
        "[v1]alphaextract[a];"
        f"[1:v]scale={full_w}:{full_h},format=gray[k];"
        "[a][k]blend=all_mode=multiply[na];"
        "[v2]format=rgb24[rgb];"
        "[rgb][na]alphamerge[out]",
        "-map", "[out]", "-an",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
        "-b:v", "0", "-crf", "20",
        args.output,
    ]
    res = subprocess.run(compor, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        die(f"recomposicao falhou: {res.stderr.decode(errors='replace').strip()[:400]}")

    os.remove(mask_path)
    size_mb = os.path.getsize(args.output) / 1_048_576
    print(f"\npronto: {args.output} ({size_mb:.1f} MB)")
    print("confira a mascara limpa antes de confiar: subject_envelope.py ou alphaextract.")


if __name__ == "__main__":
    main()
