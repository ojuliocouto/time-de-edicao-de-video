#!/usr/bin/env python3
"""Gera o recorte do sujeito de um trecho, aplicando o controle de custo da skill.

Segmentacao roda a ~1,2 quadros por segundo, entao o custo e o numero de quadros.
Este script corta os dois desperdicios de uma vez:

  1. processa so o trecho pedido, com folga nas pontas
  2. processa na taxa de quadros do render, nao na do arquivo de origem

A copia de trabalho reduz a taxa DESCARTANDO quadros (filtro fps, sem
interpolar nem misturar) e e reencodada em qualidade visualmente sem perda,
porque o sujeito inteiro do resultado final vem dela. O arquivo de origem
nunca e tocado.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import shutil
import subprocess
import sys

FRAMES_PER_SECOND_ESTIMATE = 1.2  # medido em Apple Silicon com CoreML


def die(msg):
    sys.exit(f"erro: {msg}")


def probe(path, entries, stream=True):
    cmd = ["ffprobe", "-v", "error"]
    if stream:
        cmd += ["-select_streams", "v:0"]
    cmd += ["-show_entries", f"{'stream' if stream else 'format'}={entries}",
            "-of", "csv=p=0", path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        die(f"ffprobe falhou em {path}: {res.stderr.decode(errors='replace').strip()}")
    return res.stdout.decode().strip()


def source_fps(path):
    raw = probe(path, "r_frame_rate").split(",")[0]
    if "/" in raw:
        num, den = raw.split("/")
        return float(num) / float(den) if float(den) else 0.0
    return float(raw)


def main():
    ap = argparse.ArgumentParser(
        description="Recorta o sujeito de um trecho do video, na taxa de quadros do render.",
        epilog="exemplo: make_cutout.py bruto.mp4 --start 13.2 --end 15.0 --fps 30 -o cc-subject-01.webm",
    )
    ap.add_argument("source", help="video de origem (nunca e modificado)")
    ap.add_argument("--start", type=float, required=True, help="inicio do trecho, em segundos")
    ap.add_argument("--end", type=float, required=True, help="fim do trecho, em segundos")
    ap.add_argument("--fps", type=float, required=True, help="taxa de quadros DO RENDER, nao a da origem")
    ap.add_argument("-o", "--output", required=True, help="arquivo .webm de saida, com alpha")
    ap.add_argument("--handle", type=float, default=0.5,
                    help="folga em segundos em cada ponta (padrao 0.5)")
    ap.add_argument("--crf", type=int, default=12,
                    help="qualidade da copia de trabalho, menor e melhor (padrao 12)")
    ap.add_argument("--keep-working-copy", action="store_true",
                    help="nao apagar a copia de trabalho no final")
    ap.add_argument("--dry-run", action="store_true",
                    help="so estimar o tempo e mostrar os comandos")
    args = ap.parse_args()

    for exe in ("ffmpeg", "ffprobe", "npx"):
        if shutil.which(exe) is None:
            die(f"{exe} nao encontrado no PATH")
    if not os.path.isfile(args.source):
        die(f"nao achei {args.source}")
    if args.end <= args.start:
        die("--end tem que ser maior que --start")
    if args.fps <= 0:
        die("--fps tem que ser positivo")

    start = max(0.0, args.start - args.handle)
    end = args.end + args.handle
    duration = end - start
    frames = int(round(duration * args.fps))
    minutes = frames / FRAMES_PER_SECOND_ESTIMATE / 60

    src_fps = source_fps(args.source)
    saved = ""
    if src_fps > args.fps:
        would_be = int(round(duration * src_fps))
        saved = f"  (na taxa da origem, {src_fps:g} fps, seriam {would_be} quadros)"

    print(f"trecho    {start:.2f}s a {end:.2f}s  ({duration:.2f}s, folga de {args.handle}s em cada ponta)")
    print(f"quadros   {frames} a {args.fps:g} fps{saved}")
    print(f"estimado  ~{minutes:.1f} min de segmentacao")

    root, _ = os.path.splitext(args.output)
    working = f"{root}.working.mp4"

    extract = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{start:.3f}", "-i", args.source, "-t", f"{duration:.3f}",
        # filtro fps descarta/duplica quadros inteiros; nao interpola nem mistura
        "-vf", f"fps={args.fps}",
        "-an",
        "-c:v", "libx264", "-crf", str(args.crf), "-preset", "slow",
        "-pix_fmt", "yuv420p",
        working,
    ]
    segment = [comum.exe("npx"), "--yes", "hyperframes", "remove-background", working,
               "-o", args.output, "--quality", "best"]

    if args.dry_run:
        print("\ncomandos:")
        print("  " + " ".join(extract))
        print("  " + " ".join(segment))
        return

    print("\n1/2 copia de trabalho...")
    res = subprocess.run(extract, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        die(f"extracao falhou: {res.stderr.decode(errors='replace').strip()[:400]}")

    print("2/2 segmentacao (demora)...")
    res = subprocess.run(segment, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        if not args.keep_working_copy and os.path.exists(working):
            os.remove(working)
        die("remove-background falhou; veja a saida acima")

    if not args.keep_working_copy and os.path.exists(working):
        os.remove(working)

    if not os.path.isfile(args.output):
        die(f"a segmentacao terminou mas {args.output} nao existe")

    size_mb = os.path.getsize(args.output) / 1_048_576
    print(f"\npronto: {args.output} ({size_mb:.1f} MB)")
    print(f"na composicao: data-start=\"{start:.2f}\" data-duration=\"{duration:.2f}\" data-media-start=\"0\"")
    print("confira o encaixe em tres quadros com movimento antes de confiar.")


if __name__ == "__main__":
    main()
