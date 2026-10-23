#!/usr/bin/env python3
"""Entrega: confere o arquivo final, gera a versao leve e (so com a pasta indicada) sobe no Drive.

    python entrega.py final/meu-anuncio-legendado.mp4
    python entrega.py final/meu-anuncio-legendado.mp4 \
        --drive <id-da-pasta-do-drive> --nome AD-meu-anuncio-LEGENDADO.mp4

Sempre imprime a linha que a pessoa quer ver na entrega: resolucao, fps, duracao e
tamanho, e por que o arquivo e pequeno ("essa qualidade ta certa? so 46mb").

A versao leve 720p (~10 MB por minuto e meio) e a que vai por mensagem e no
chat; a cheia vai para o Drive.

--drive so depois que A PESSOA disser a pasta. Nunca criar pasta no Drive por conta
propria (ja reclamaram: "enchendo o Drive de pastas desorganizadas"). Usa o rclone com
o remote `gdrive:` e confere o tamanho no Drive contra o local.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import sys
from pathlib import Path


def leve(arq):
    destino = arq.with_name(arq.stem + "-720p.mp4")
    if destino.exists() and destino.stat().st_mtime >= arq.stat().st_mtime:
        return destino
    comum.rodar(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(arq), "-vf", "scale=720:-2",
                 "-c:v", "libx264", "-crf", "24", "-preset", "fast", "-c:a", "aac", "-b:a", "128k",
                 "-movflags", "+faststart", str(destino)])
    return destino


def linha(arq):
    m = comum.sondar(arq)
    mb = arq.stat().st_size / 1048576
    return m, "%s: %dx%d, %.0f fps, %.1f s, %.1f MB" % (arq.name, m["w"], m["h"], m["fps"], m["dur"], mb)


def main():
    ap = argparse.ArgumentParser(description="Confere, gera a versao leve e sobe no Drive.")
    ap.add_argument("arquivo")
    ap.add_argument("--drive", help="ID da pasta do Drive que a pessoa indicou")
    ap.add_argument("--nome", help="nome no Drive, ex.: ADxx-tema-LEGENDADO.mp4")
    ap.add_argument("--leve-no-drive", action="store_true", help="sobe tambem a versao 720p")
    a = ap.parse_args()
    comum.exigir("ffmpeg", "ffprobe")
    arq = Path(a.arquivo).expanduser().resolve()
    if not arq.exists():
        sys.exit("nao achei %s" % arq)

    m, txt = linha(arq)
    problemas = []
    if (m["w"], m["h"]) != (1080, 1920):
        problemas.append("o arquivo nao e 1080x1920")
    if not m["audio"]:
        problemas.append("o arquivo nao tem audio")
    if problemas:
        sys.exit("NAO ENTREGAR: " + "; ".join(problemas))
    l = leve(arq)
    print(txt)
    print(linha(l)[1])
    print("Vídeo curto em H.264 pesa pouco sem perder qualidade: 40 a 60 MB por minuto "
          "em 1080x1920 é o normal. A versão 720p é a de mandar por mensagem.")

    if not a.drive:
        return 0
    comum.exigir("rclone")
    nome = a.nome or arq.name
    subir = [(arq, nome)]
    if a.leve_no_drive:
        subir.append((l, Path(nome).stem.replace("-LEGENDADO", "") + "-LEVE-720p.mp4"))
    for local, remoto in subir:
        print("subindo %s como %s ..." % (local.name, remoto), flush=True)
        comum.rodar(["rclone", "copyto", str(local), "gdrive:%s" % remoto,
                     "--drive-root-folder-id", a.drive], capture_output=False)
        r = comum.rodar(["rclone", "lsjson", "gdrive:%s" % remoto, "--drive-root-folder-id", a.drive])
        info = json.loads(r.stdout or "[]")
        tam = info[0]["Size"] if info else -1
        ok = tam == local.stat().st_size
        print("  no Drive: %s bytes | local: %s bytes | %s" % (tam, local.stat().st_size, "IGUAL" if ok else "DIFERENTE"))
        if not ok:
            sys.exit("o tamanho no Drive nao bate com o local: suba de novo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
