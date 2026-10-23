#!/usr/bin/env python3
"""Mede a silhueta do sujeito a partir do canal alpha de um matte.

Responde as duas perguntas que decidem onde a palavra-heroi pode ficar:
  - ate onde o topo da cabeca sobe em cada instante
  - qual a faixa horizontal ocupada em cada altura

Armadilha ja resolvida aqui: o ffmpeg so expoe o alpha de um WebM VP9 se o
decodificador for forcado com `-c:v libvpx-vp9` ANTES do `-i`. Sem isso o
filtro alphaextract falha com "Requested planes not available".
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import shutil
import subprocess
import sys


def _run(cmd, capture_stdout=True):
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE if capture_stdout else None,
        stderr=subprocess.PIPE,
        check=False,
     stdin=subprocess.DEVNULL)


def probe_size(path):
    """Devolve (largura, altura) do video."""
    res = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", path,
    ])
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe falhou em {path}: {res.stderr.decode(errors='replace').strip()}")
    parts = res.stdout.decode().strip().split(",")
    return int(parts[0]), int(parts[1])


def inspect_alpha(path):
    """Devolve (tem_alpha, codec, pix_fmt). Evita a mensagem cripitica do ffmpeg."""
    res = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,pix_fmt",
        "-show_entries", "stream_tags=alpha_mode,ALPHA_MODE",
        "-of", "default=nw=1:nk=0", path,
    ])
    info = {}
    for line in res.stdout.decode().splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            info[k.strip().lower().replace("tag:", "")] = v.strip()
    codec = info.get("codec_name", "")
    pix = info.get("pix_fmt", "")
    tagged = info.get("alpha_mode", "0") == "1"
    # yuva/rgba carregam alpha no proprio pix_fmt; VP9 carrega em canal separado com a tag
    return (tagged or pix.startswith("yuva") or pix.startswith("rgba") or pix.startswith("bgra")), codec, pix


def pick_decoder(codec):
    """VP9 so entrega alpha com o decodificador forcado; os outros nao precisam."""
    return "libvpx-vp9" if codec == "vp9" else None


def alpha_frame(matte, t, sample_w, sample_h, decoder):
    """Extrai um quadro do canal alpha como bytes em escala de cinza."""
    cmd = ["ffmpeg", "-v", "error", "-ss", str(t)]
    if decoder:
        cmd += ["-c:v", decoder]
    cmd += [
        "-i", matte, "-frames:v", "1",
        "-vf", f"alphaextract,scale={sample_w}:{sample_h}",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    res = _run(cmd)
    data = res.stdout
    if len(data) < sample_w * sample_h:
        first = res.stderr.decode(errors="replace").strip().splitlines()
        detalhe = first[0] if first else "sem detalhe do ffmpeg"
        raise RuntimeError(
            f"nao consegui ler o alpha em t={t}s. "
            f"Confira se esse instante existe dentro do arquivo. Detalhe: {detalhe}"
        )
    return data


def measure(matte, times, bands, threshold=128, sample_w=270, decoder="auto"):
    tem_alpha, codec, pix = inspect_alpha(matte)
    if not tem_alpha:
        raise RuntimeError(
            f"{matte} nao tem canal alpha (codec {codec or '?'}, pix_fmt {pix or '?'}).\n"
            "       Este script le o recorte do sujeito, nao o video base. "
            "Gere o recorte com scripts/make_cutout.py e aponte para o .webm dele."
        )
    if decoder == "auto":
        decoder = pick_decoder(codec)

    full_w, full_h = probe_size(matte)
    sample_h = max(1, round(sample_w * full_h / full_w))
    scale = full_w / sample_w

    out = []
    for t in times:
        buf = alpha_frame(matte, t, sample_w, sample_h, decoder)
        top = None
        rows = {}
        for y in range(sample_h):
            row = buf[y * sample_w:(y + 1) * sample_w]
            xmin = xmax = None
            for x in range(sample_w):
                if row[x] > threshold:
                    if xmin is None:
                        xmin = x
                    xmax = x
            if xmin is not None:
                if top is None:
                    top = y
                rows[y] = (xmin, xmax)

        entry = {"t": t, "subject_top": None if top is None else round(top * scale), "bands": {}}
        for band_y in bands:
            sy = round(band_y / scale)
            hit = rows.get(sy)
            entry["bands"][band_y] = None if hit is None else [round(hit[0] * scale), round(hit[1] * scale)]
        out.append(entry)

    return {"matte": matte, "width": full_w, "height": full_h, "samples": out}


def main():
    ap = argparse.ArgumentParser(
        description="Mede a silhueta do sujeito no canal alpha de um matte (WebM com alpha ou MOV).",
        epilog="exemplo: subject_envelope.py cc-subject.webm --at 13.5,14.2,14.9 --bands 200,300,400",
    )
    ap.add_argument("matte", help="arquivo do recorte, com canal alpha")
    ap.add_argument("--at", required=True, help="instantes em segundos, separados por virgula")
    ap.add_argument("--bands", default="", help="alturas em px da composicao para medir a faixa horizontal")
    ap.add_argument("--threshold", type=int, default=128, help="corte de opacidade, 0-255 (padrao 128)")
    ap.add_argument("--sample-width", type=int, default=270, help="largura de amostragem (padrao 270)")
    ap.add_argument("--decoder", default="auto",
                    help="decodificador: auto (padrao), none, ou um nome como libvpx-vp9")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    args = ap.parse_args()

    for exe in ("ffmpeg", "ffprobe"):
        if shutil.which(exe) is None:
            sys.exit(f"erro: {exe} nao encontrado no PATH")

    try:
        times = [float(x) for x in args.at.split(",") if x.strip()]
        bands = [int(x) for x in args.bands.split(",") if x.strip()]
    except ValueError as exc:
        sys.exit(f"erro: --at e --bands aceitam so numeros separados por virgula ({exc})")

    if not times:
        sys.exit("erro: --at nao pode ficar vazio")

    decoder = args.decoder if args.decoder == "auto" else (
        None if args.decoder.lower() == "none" else args.decoder)

    try:
        result = measure(args.matte, times, bands, args.threshold, args.sample_width, decoder)
    except (RuntimeError, OSError) as exc:
        sys.exit(f"erro: {exc}")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"{result['matte']}  {result['width']}x{result['height']}")
    for s in result["samples"]:
        top = s["subject_top"]
        line = f"  t={s['t']:<7} topo do sujeito y={'vazio' if top is None else top}"
        for band_y, rng in s["bands"].items():
            line += f"   y{band_y}: {'vazio' if rng is None else f'x {rng[0]}-{rng[1]}'}"
        print(line)


if __name__ == "__main__":
    main()
