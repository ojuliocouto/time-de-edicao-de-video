#!/usr/bin/env python3
"""Junta uma ou mais camadas com alpha ao video de origem, em uma passada de ffmpeg.

As camadas sao aplicadas na ordem em que aparecem, de baixo para cima. Para
profundidade real a ordem e: tipografia de tras, recorte do sujeito, tipografia
da frente.

Uma camada que nao cobre o video inteiro, como um recorte de trecho, entra com
`arquivo.webm@INICIO`: ela e deslocada para esse instante e so aparece durante a
sua propria duracao. Sem isso o recorte apareceria desde o quadro zero.

O material de origem nunca e reencodado pelo pipeline de legenda ate aqui:
esta e a unica passada de compressao que ele sofre. Por isso o padrao e CRF 18,
que e transparente na pratica para conteudo de camera.

Armadilha ja resolvida: um WebM VP9 com alpha so entrega o canal alpha se o
decodificador for forcado com `-c:v libvpx-vp9` ANTES do `-i` daquela entrada.
Para .mov (ProRes 4444) nao precisa.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import shutil
import subprocess
import sys


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


def probe_format(path, entries):
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", f"format={entries}",
         "-of", "csv=p=0", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
     stdin=subprocess.DEVNULL)
    return res.stdout.decode().strip() if res.returncode == 0 else None


def has_audio(path):
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
     stdin=subprocess.DEVNULL)
    return res.returncode == 0 and "audio" in res.stdout.decode()


def main():
    ap = argparse.ArgumentParser(
        description="Sobrepoe a camada de legenda (com alpha) ao video de origem.",
        epilog="exemplo: composite_overlay.py bruto.mp4 tras.webm recorte-a.webm@7.55 recorte-b.webm@27.87 frente.webm -o final.mp4",
    )
    ap.add_argument("source", help="video de origem")
    ap.add_argument("overlay", nargs="+",
                    help="camadas com alpha, de baixo para cima. Use arquivo@INICIO "
                         "para uma camada que so vale a partir daquele segundo")
    ap.add_argument("-o", "--output", required=True, help="arquivo final")
    ap.add_argument("--crf", type=int, default=18, help="qualidade do encode final (padrao 18)")
    ap.add_argument("--preset", default="veryfast", help="preset do x264 (padrao veryfast: rapido, arquivo maior, mesma qualidade)")
    ap.add_argument("--no-audio", action="store_true", help="descartar o audio da origem")
    ap.add_argument("--dry-run", action="store_true", help="so mostrar o comando")
    args = ap.parse_args()

    for exe in ("ffmpeg", "ffprobe"):
        if shutil.which(exe) is None:
            die(f"{exe} nao encontrado no PATH")
    camadas = []
    for item in args.overlay:
        if "@" in item:
            caminho, _, quando = item.rpartition("@")
            try:
                inicio = float(quando)
            except ValueError:
                die(f"'{item}': depois do @ tem que vir o segundo de inicio")
        else:
            caminho, inicio = item, None
        camadas.append((caminho, inicio))

    for path in [args.source] + [c for c, _ in camadas]:
        if not os.path.isfile(path):
            die(f"nao achei {path}")

    src_size = probe(args.source, "width,height")
    for path, _ in camadas:
        size = probe(path, "width,height")
        if size != src_size:
            die(f"tamanhos diferentes: origem {src_size}, {path} {size}. "
                "Toda camada tem que ter exatamente as dimensoes da composicao.")

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", args.source]
    janelas = []
    for path, inicio in camadas:
        if inicio is not None:
            dur = probe_format(path, "duration")
            try:
                fim = inicio + float(dur)
            except (TypeError, ValueError):
                die(f"nao consegui ler a duracao de {path} para posicionar a camada")
            janelas.append((inicio, round(fim, 3)))
            cmd += ["-itsoffset", f"{inicio}"]
        else:
            janelas.append(None)
        # WebM VP9 so entrega alpha com o decodificador forcado antes do -i
        if os.path.splitext(path)[1].lower() == ".webm":
            cmd += ["-c:v", "libvpx-vp9"]
        cmd += ["-i", path]

    steps, prev = [], "0:v"
    for i, janela in enumerate(janelas):
        label = "v" if i == len(camadas) - 1 else f"s{i}"
        extra = ":eof_action=pass"
        if janela:
            extra += f":enable='between(t,{janela[0]},{janela[1]})'"
        steps.append(f"[{prev}][{i + 1}:v]overlay=0:0{extra}[{label}]")
        prev = label
    cmd += ["-filter_complex", ";".join(steps), "-map", "[v]"]
    keep_audio = has_audio(args.source) and not args.no_audio
    if keep_audio:
        cmd += ["-map", "0:a", "-c:a", "copy"]
    cmd += [
        "-c:v", "libx264", "-crf", str(args.crf), "-preset", args.preset,
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        args.output,
    ]

    if args.dry_run:
        print(" ".join(cmd))
        return

    posicionadas = sum(1 for j in janelas if j)
    print(f"compondo {len(camadas)} camada(s) sobre {args.source} ({src_size})"
          f"{f', {posicionadas} posicionada(s) no tempo' if posicionadas else ''}"
          f"{'' if keep_audio else '  [sem audio]'}...")
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        die(f"ffmpeg falhou: {res.stderr.decode(errors='replace').strip()[:500]}")

    if not os.path.isfile(args.output):
        die(f"o comando terminou mas {args.output} nao existe")

    size_mb = os.path.getsize(args.output) / 1_048_576
    print(f"pronto: {args.output} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
