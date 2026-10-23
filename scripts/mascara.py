#!/usr/bin/env python3
"""Mascara da pessoa: para os inserts com recorte e para a palavra atras dela.

    # mascara do video inteiro (vazado_maior, vazado_pequeno, react)
    python mascara.py bruto.mp4 -o analise/matte.mp4

    # so os trechos onde entra insert com recorte; o resto sai preto
    python mascara.py bruto.mp4 -o analise/matte.mp4 --janelas 12.4-19.8,61-66

    # recortes RGBA para a legenda (heroi atras da cabeca), um webm por trecho
    python mascara.py legenda/montado.mp4 --recortes cc-a@33.40+1.70,cc-b@41.46+1.64 \
        --pasta legenda/.work

    # quanto tempo vai levar, sem fazer
    python mascara.py bruto.mp4 -o analise/matte.mp4 --estimar

Dois motores, escolhidos sozinhos (--motor forca):

- vision (Mac): a API do "copiar assunto" do macOS, 0,10 s por quadro e a melhor
  borda de cabelo que testamos. Precisa do swiftc (Xcode Command Line Tools).
- hyperframes (Mac, Windows e Linux): o remove-background do HyperFrames,
  ~1,2 quadro por segundo num Mac com chip Apple e mais lento sem GPU. Qualidade
  conferida contra a Vision: IoU de 0,93 a 0,99. Por isso, fora do Mac, use
  sempre --janelas: so segmenta o que vai aparecer.

O que esta embutido aqui e custou uma rodada cada para descobrir:
- a mascara sai com a largura, a altura, o fps e a duracao do VIDEO, nunca
  cravados. Mascara a 30 em bruto de 25 descola o recorte sem acusar nada;
- a Vision para de entregar quadros no meio de arquivo longo sem dar erro
  (saiu 4768 de 10533 num video real). Por isso roda em blocos de 40 s, e cada
  bloco e forcado ao numero exato de quadros (corta o excesso, repete o ultimo);
- o decodificador libvpx-vp9 vai ANTES do -i ao ler alfa de webm, senao o
  alphaextract falha com 'Requested planes not available'.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BLOCO_S = 40.0
FOLGA = 0.3
VEL = {"vision": 10.0, "hyperframes": 1.2}   # quadros por segundo, medidos no Mac dela


# ---------------------------------------------------------------- motores

def binario_vision():
    if comum.SISTEMA != "mac":
        return None
    fonte = comum.SCRIPTS / "segvideo.swift"
    destino = comum.cache("bin") / "segvideo"
    if destino.exists() and destino.stat().st_mtime >= fonte.stat().st_mtime:
        return destino
    if not comum.tem("swiftc"):
        return None
    r = comum.rodar(["swiftc", "-O", str(fonte), "-o", str(destino)], checar=False)
    return destino if r.returncode == 0 and destino.exists() else None


def escolher_motor(pedido):
    if pedido in ("auto", "vision"):
        b = binario_vision()
        if b:
            return "vision", b
        if pedido == "vision":
            sys.exit("a Vision so existe no Mac e precisa do swiftc (xcode-select --install).")
    comum.exigir("npx")
    return "hyperframes", None


def encaixar(fluxo, n, tam, saida):
    """Le quadros crus de `fluxo` e escreve EXATAMENTE n em `saida`."""
    ultimo, lidos = bytes(tam), 0
    while lidos < n:
        q = fluxo.read(tam)
        if len(q) < tam:
            break
        saida.write(q)
        ultimo, lidos = q, lidos + 1
    for _ in range(n - lidos):
        saida.write(ultimo)
    while fluxo.read(1 << 20):   # drena o resto, senao o produtor trava
        pass
    return lidos


def quadros_vision(binario, video, meta, ini_q, n, saida):
    fps = meta["fps"]
    tam = meta["w"] * meta["h"]
    feito = 0
    bloco = int(round(BLOCO_S * fps))
    while feito < n:
        k = min(bloco, n - feito)
        q0 = ini_q + feito
        p = comum.popen([binario, video, meta["w"], meta["h"], "%.6f" % (q0 / fps), "%.6f" % (k / fps)],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        lidos = encaixar(p.stdout, k, tam, saida)
        p.wait()
        if lidos < k:
            print("  bloco em %.1fs: %d de %d quadros (completados com o ultimo)" % (q0 / fps, lidos, k),
                  flush=True)
        feito += k


def quadros_hyperframes(video, meta, ini_q, n, saida, tmp):
    fps = meta["fps"]
    a, dur = ini_q / fps, n / fps
    trecho = Path(tmp) / ("trecho-%d.mp4" % ini_q)
    recorte = Path(tmp) / ("recorte-%d.webm" % ini_q)
    comum.rodar(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % a, "-i", str(video), "-t", "%.3f" % dur,
                 "-an", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", "-r", meta["fps_txt"],
                 str(trecho)])
    t0 = time.time()
    r = comum.rodar(["npx", "--yes", "hyperframes", "remove-background", str(trecho), "-o", str(recorte),
                     "--quality", "best"], checar=False)
    if r.returncode != 0 or not recorte.exists():
        sys.exit("o remove-background falhou em %.2f-%.2f:\n%s" % (a, a + dur, (r.stderr or r.stdout)[-1200:]))
    print("  %d quadros em %.0fs" % (n, time.time() - t0), flush=True)
    p = comum.popen(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(recorte),
                     "-vf", "alphaextract,format=gray,scale=%d:%d" % (meta["w"], meta["h"]),
                     "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    encaixar(p.stdout, n, meta["w"] * meta["h"], saida)
    p.wait()


def produzir(motor, binario, video, meta, ini_q, n, saida, tmp):
    if motor == "vision":
        quadros_vision(binario, video, meta, ini_q, n, saida)
    else:
        quadros_hyperframes(video, meta, ini_q, n, saida, tmp)


def codificador(meta, destino):
    return comum.popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray",
                        "-s", "%dx%d" % (meta["w"], meta["h"]), "-r", meta["fps_txt"], "-i", "-",
                        "-c:v", "libx264", "-crf", "10", "-pix_fmt", "gray", str(destino)],
                       stdin=subprocess.PIPE)


# ---------------------------------------------------------------- modos

def ler_janelas(txt, dur):
    js = [(0.0, min(1.0, dur))]   # o insert.py --medir le o primeiro quadro
    for parte in (txt or "").split(","):
        parte = parte.strip()
        if not parte:
            continue
        try:
            a, b = (float(x) for x in parte.split("-"))
        except ValueError:
            sys.exit("janela invalida: '%s'. Use inicio-fim em segundos: 2.1-9.4" % parte)
        if b <= a:
            sys.exit("janela invalida: '%s'" % parte)
        js.append((max(0.0, a - FOLGA), min(dur, b + FOLGA)))
    js.sort()
    juntas = [list(js[0])]
    for a, b in js[1:]:
        if a <= juntas[-1][1]:
            juntas[-1][1] = max(juntas[-1][1], b)
        else:
            juntas.append([a, b])
    return [tuple(j) for j in juntas]


def mascara_inteira(video, destino, janelas, motor, binario, meta):
    fps = meta["fps"]
    total = comum.contar_quadros(video) or int(round(meta["dur"] * fps))
    if janelas is None:
        partes = [(0, total, True)]
    else:
        partes, cur = [], 0
        for a, b in janelas:
            qa, qb = max(cur, int(a * fps)), min(total, int(round(b * fps)))
            if qa > cur:
                partes.append((cur, qa - cur, False))
            if qb > qa:
                partes.append((qa, qb - qa, True))
            cur = max(cur, qb)
        if cur < total:
            partes.append((cur, total - cur, False))
    destino = Path(destino).expanduser()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temp = destino.with_name(destino.stem + "-tmp" + destino.suffix)
    enc = codificador(meta, temp)
    preto = bytes(meta["w"] * meta["h"])
    with tempfile.TemporaryDirectory() as tmp:
        for q0, n, segmenta in partes:
            if segmenta:
                print("segmentando %.2fs a %.2fs (%d quadros, %s)" % (q0 / fps, (q0 + n) / fps, n, motor),
                      flush=True)
                produzir(motor, binario, video, meta, q0, n, enc.stdin, tmp)
            else:
                for _ in range(n):
                    enc.stdin.write(preto)
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("o ffmpeg falhou ao gravar a mascara")
    temp.replace(destino)
    n = comum.contar_quadros(destino)
    print("mascara: %s (%d quadros, video tem %d)" % (destino, n, total))
    if n != total:
        print("ATENCAO: a mascara nao tem o mesmo numero de quadros do video. Nao use.")
        return 1
    return 0


def recortes(video, spec, pasta, motor, binario, meta):
    """Webm RGBA por trecho: pixel do proprio video + alfa da mascara."""
    pasta = Path(pasta).expanduser()
    pasta.mkdir(parents=True, exist_ok=True)
    fps = meta["fps"]
    with tempfile.TemporaryDirectory() as tmp:
        for item in spec.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                nome, resto = item.split("@")
                ini, dur = (float(x) for x in resto.split("+"))
            except ValueError:
                sys.exit("recorte invalido: '%s'. Use nome@inicio+duracao: cc-a@33.40+1.70" % item)
            q0, n = int(round(ini * fps)), int(round(dur * fps))
            rgb, msk = Path(tmp) / (nome + "-rgb.mp4"), Path(tmp) / (nome + "-mask.mp4")
            print("== %s  %.2fs + %.2fs (%d quadros)" % (nome, ini, dur, n), flush=True)
            comum.rodar(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "%.3f" % (q0 / fps), "-i", str(video),
                         "-frames:v", str(n), "-an", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p",
                         str(rgb)])
            enc = codificador(meta, msk)
            produzir(motor, binario, video, meta, q0, n, enc.stdin, tmp)
            enc.stdin.close()
            enc.wait()
            saida = pasta / (nome + "-recorte.webm")
            comum.rodar(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(rgb), "-i", str(msk),
                         "-filter_complex", "[1:v]format=gray[m];[0:v][m]alphamerge,format=yuva420p",
                         "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "18",
                         "-auto-alt-ref", "0", str(saida)])
            print("   %s" % saida)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Mascara da pessoa (Vision no Mac, HyperFrames nos tres).")
    ap.add_argument("video")
    ap.add_argument("-o", "--saida", help="matte.mp4 do video inteiro")
    ap.add_argument("--janelas", help="so estes trechos, em segundos do video: 2.1-9.4,40-44")
    ap.add_argument("--recortes", help="webm RGBA por trecho: nome@inicio+duracao,...")
    ap.add_argument("--pasta", default=".", help="onde gravar os --recortes")
    ap.add_argument("--motor", default="auto", choices=["auto", "vision", "hyperframes"])
    ap.add_argument("--estimar", action="store_true")
    a = ap.parse_args()

    comum.exigir("ffmpeg", "ffprobe")
    video = Path(a.video).expanduser().resolve()
    if not video.exists():
        sys.exit("video nao encontrado: %s" % video)
    if not a.saida and not a.recortes:
        sys.exit("diga o que gerar: -o matte.mp4 ou --recortes nome@ini+dur")
    meta = comum.sondar(video)
    motor, binario = escolher_motor(a.motor)

    if a.recortes:
        segundos = sum(float(x.split("@")[1].split("+")[1]) for x in a.recortes.split(",") if "@" in x)
    else:
        js = ler_janelas(a.janelas, meta["dur"]) if a.janelas else [(0, meta["dur"])]
        segundos = sum(b - x for x, b in js)
    q = segundos * meta["fps"]
    print("motor %s: %d quadros, estimado ~%.1f min" % (motor, q, q / VEL[motor] / 60))
    if motor == "hyperframes" and q > 3000 and not a.estimar:
        print("aviso: e muito quadro para o remove-background. Prefira --janelas so com os trechos usados.")
    if a.estimar:
        return 0
    if a.recortes:
        return recortes(video, a.recortes, a.pasta, motor, binario, meta)
    return mascara_inteira(video, a.saida, ler_janelas(a.janelas, meta["dur"]) if a.janelas else None,
                           motor, binario, meta)


if __name__ == "__main__":
    sys.exit(main())
