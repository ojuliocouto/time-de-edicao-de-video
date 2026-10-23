#!/usr/bin/env python3
"""Prepara o bruto: 1080x1920, voz em -24 LUFS e, quando preciso, trechos de mais de um video.

Roda SEMPRE na etapa 0, mesmo com um video so (um trecho com "ate": null): o
render recusa qualquer coisa que nao seja 1080x1920, e bruto 4K ou .mov com
rotacao so falharia la na frente, depois dos cortes. E e aqui que a voz vai
para -24 LUFS (a versao em -14,5 ficou alta demais).

    python montar_bruto.py --pasta <pasta-do-video> --trechos trechos.json
    python montar_bruto.py --pasta <pasta-do-video> --trechos trechos.json --estimar

trechos.json (lista, na ordem em que entram):
  [{"arquivo": "~/Videos/meu-anuncio/bruto.mp4", "de": 0.0, "ate": 197.6667,
    "fala": "do inicio ate '...antes do dia da abertura,'"},
   {"arquivo": "~/Videos/meu-anuncio/cta.mp4", "de": 130.70, "ate": null,
    "fala": "'Nossa oferta e diferente...' ate 'Vamos nessa!'"}]

`ate: null` vai ate o fim do arquivo. Os pontos de corte tem que ser
conferidos ANTES, com `transcrever.py <arquivo> --de X --ate Y --isolado` e com
os silencios: os tempos que a pessoa passa vem de transcricao que deriva.

O que este script garante, cada item uma reprovacao ou um retrabalho real:
- VIDEO E AUDIO dos dois trechos. So o audio do CTA sobre outra imagem ficou
  "meio nada a ver" num anuncio real. A troca de imagem ganha whoosh e
  efeito de montagem depois, na etapa de inserts.
- volume igualado por ganho FIXO, voz em -24 LUFS. Nunca denoise, nunca
  compressor: nas vezes em que trataram o audio ele piorou.
- fade de 20 ms em cada emenda, para nao estalar.
- tudo convertido para o mesmo tamanho e fps do primeiro trecho.
- um MONTAGEM.md com o offset de cada trecho (tempo no montado = tempo na
  fonte + offset), que e o que permite reaproveitar inserts feitos sobre o
  mesmo trecho em outro projeto.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import os
import re
import sys
from pathlib import Path

ALVO_LUFS = -24.0
FADE = 0.02


def lufs(arq, de, ate):
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-ss", "%.3f" % de]
    if ate is not None:
        cmd += ["-t", "%.3f" % (ate - de)]
    cmd += ["-i", str(arq), "-vn", "-af", "ebur128=framelog=quiet", "-f", "null", "-"]
    r = comum.rodar(cmd, checar=False)
    m = re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr or "")
    return float(m[-1]) if m else None


def main():
    ap = argparse.ArgumentParser(description="Bruto unico de varios trechos, volume igualado.")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--trechos", required=True)
    ap.add_argument("--nome", default="montado.mp4")
    ap.add_argument("--lufs", type=float, default=ALVO_LUFS)
    ap.add_argument("--estimar", action="store_true", help="so mede e mostra")
    ap.add_argument("--largura", type=int, default=1080)
    ap.add_argument("--altura", type=int, default=1920)
    a = ap.parse_args()
    comum.exigir("ffmpeg", "ffprobe")

    pasta = Path(a.pasta).expanduser().resolve()
    trechos = comum.ler_json(a.trechos)
    if not trechos:
        sys.exit("trechos.json vazio")
    info = []
    for k, t in enumerate(trechos):
        arq = Path(os.path.expanduser(t["arquivo"])).resolve()
        if not arq.exists():
            sys.exit("trecho %d: nao achei %s" % (k + 1, arq))
        meta = comum.sondar(arq)
        de = float(t.get("de", 0.0))
        ate = meta["dur"] if t.get("ate") in (None, "fim") else float(t["ate"])
        if not 0 <= de < ate <= meta["dur"] + 0.05:
            sys.exit("trecho %d: %.2f-%.2f fora do arquivo (%.2fs)" % (k + 1, de, ate, meta["dur"]))
        medido = lufs(arq, de, ate)
        ganho = (a.lufs - medido) if medido is not None else 0.0
        info.append(dict(arq=arq, meta=meta, de=de, ate=min(ate, meta["dur"]), lufs=medido, ganho=ganho,
                         fala=t.get("fala", "")))
        print("trecho %d: %s %.3f-%.3f (%.2fs) | %s LUFS -> ganho %+.1f dB"
              % (k + 1, arq.name, de, ate, ate - de, "%.1f" % medido if medido is not None else "?", ganho))
    if a.estimar:
        return 0

    w, h, fps = a.largura, a.altura, info[0]["meta"]["fps_txt"]
    cmd, filtros, rot = ["ffmpeg", "-v", "error", "-y"], [], []
    for k, t in enumerate(info):
        cmd += ["-ss", "%.4f" % t["de"], "-t", "%.4f" % (t["ate"] - t["de"]), "-i", str(t["arq"])]
        d = t["ate"] - t["de"]
        filtros.append("[%d:v]scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,"
                       "fps=%s,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v%d]" % (k, w, h, w, h, fps, k))
        filtros.append("[%d:a]aresample=48000,aformat=channel_layouts=stereo,volume=%.2fdB,"
                       "afade=t=in:d=%.3f,afade=t=out:st=%.3f:d=%.3f,asetpts=PTS-STARTPTS[a%d]"
                       % (k, t["ganho"], FADE, max(0.0, d - FADE), FADE, k))
        rot.append("[v%d][a%d]" % (k, k))
    filtros.append("%sconcat=n=%d:v=1:a=1[v][a]" % ("".join(rot), len(info)))
    saida = pasta / "bruto-montado" / a.nome
    saida.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["-filter_complex", ";".join(filtros), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(saida)]
    print("montando %s ..." % saida, flush=True)
    comum.rodar(cmd)

    linhas = ["# Bruto montado", "", "Fonte unica para o plano.json. Gerado por montar_bruto.py.", "",
              "| trecho | origem | de | ate | no montado | offset (montado = fonte + offset) | fala |",
              "|---|---|---|---|---|---|---|"]
    acc = 0.0
    for k, t in enumerate(info):
        d = t["ate"] - t["de"]
        linhas.append("| %d | %s | %.3f | %.3f | %.3f a %.3f | %+.4f | %s |"
                      % (k + 1, t["arq"].name, t["de"], t["ate"], acc, acc + d, acc - t["de"], t["fala"]))
        acc += d
    linhas += ["", "Audio: ganho fixo para %.0f LUFS em cada trecho, sem denoise e sem compressor, "
               "fade de %d ms nas emendas." % (a.lufs, FADE * 1000),
               "Medido: " + "; ".join("%s %s LUFS (%+.1f dB)" % (t["arq"].name,
                                      "%.1f" % t["lufs"] if t["lufs"] is not None else "?", t["ganho"]) for t in info)]
    comum.gravar_texto(saida.parent / "MONTAGEM.md", "\n".join(linhas) + "\n")
    comum.gravar_json(saida.parent / "trechos.json", json.loads(json.dumps(trechos)))
    final = comum.sondar(saida)
    print("pronto: %s (%.2fs, %dx%d) | MONTAGEM.md ao lado" % (saida, final["dur"], final["w"], final["h"]))
    print("medido no montado: %s LUFS" % lufs(saida, 0.0, None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
