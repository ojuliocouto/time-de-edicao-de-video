#!/usr/bin/env python3
"""Monta o video legendado: recortes, camadas com alfa e composicao, numa linha so.

    python montar_legenda.py --pasta <video>/legenda --recortes --saida <video>/final/meu-anuncio-legendado.mp4
    python montar_legenda.py --pasta <video>/legenda --saida ...      # recortes ja feitos

Ordem, cada passo herdado de um montar.sh que deu certo:
1. (--recortes) um webm RGBA por heroi, com a mascara da pessoa no proprio
   video montado: `mascara.py --recortes`. Na Vision o recorte segue o cabelo
   fio a fio; o `matte_fitness.py` reprova cabelo escuro em parede escura por
   contraste, mas a borda esta certa: confira no `snapshot --zoom`, nao no numero.
2. `gerar_legenda.py`: escreve as composicoes a partir do legenda.json.
3. render das duas camadas com alfa (tras e frente), em PRIMEIRO PLANO: render
   do HyperFrames disparado em segundo plano e cancelado quando a chamada
   termina (render_cancelled_parent_exited).
4. `composite_overlay.py`: video + tras + recortes no tempo + frente, CRF 18.
5. versao leve 720p ao lado, para mandar no chat e por mensagem.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import subprocess
import sys
from pathlib import Path


def py(script, *args):
    r = subprocess.run([sys.executable, "-u", str(comum.SCRIPTS / script)] + [str(x) for x in args], stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        sys.exit("%s falhou" % script)


def render_camada(pasta, nome, workers):
    print("render da camada %s..." % nome, flush=True)
    r = comum.rodar(["npx", "--yes", "hyperframes", "render", "-c", ".work/%s.html" % nome,
                     "-o", ".work/%s.webm" % nome, "--format", "webm", "--workers", str(workers), "--quiet"],
                    checar=False, cwd=str(pasta), capture_output=False)
    alvo = pasta / ".work" / ("%s.webm" % nome)
    if r.returncode != 0 or not alvo.exists():
        sys.exit("o render da camada %s falhou. Com pouca memoria, tente --workers 1." % nome)
    return alvo


def versao_leve(arq):
    leve = arq.with_name(arq.stem + "-720p.mp4")
    comum.rodar(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(arq), "-vf", "scale=720:-2",
                 "-c:v", "libx264", "-crf", "24", "-preset", "fast", "-c:a", "aac", "-b:a", "128k",
                 "-movflags", "+faststart", str(leve)])
    return leve


def main():
    ap = argparse.ArgumentParser(description="Recortes + camadas + composicao da legenda.")
    ap.add_argument("--pasta", required=True, help="pasta da legenda (com legenda.json e o video)")
    ap.add_argument("--saida", required=True, help="video final legendado")
    ap.add_argument("--recortes", action="store_true", help="gera os recortes dos herois antes")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    comum.exigir("ffmpeg", "ffprobe", "npx")
    pasta = Path(a.pasta).expanduser().resolve()
    spec = comum.ler_json(pasta / "legenda.json")
    video = pasta / spec.get("video", "montado.mp4")
    recortes = spec.get("recortes", {})

    if a.recortes and recortes:
        lista = ",".join("%s@%.3f+%.3f" % (k, float(r["inicio"]), float(r["duracao"])) for k, r in recortes.items())
        py("mascara.py", video, "--recortes", lista, "--pasta", pasta / ".work")
    faltam = [k for k in recortes if not (pasta / ".work" / ("%s-recorte.webm" % k)).exists()]
    if faltam:
        sys.exit("faltam os recortes %s. Rode com --recortes." % ", ".join(faltam))

    py("gerar_legenda.py", "--pasta", pasta)
    tras = render_camada(pasta, "tras", a.workers)
    frente = render_camada(pasta, "frente", a.workers)

    saida = Path(a.saida).expanduser().resolve()
    saida.parent.mkdir(parents=True, exist_ok=True)
    camadas = [str(tras)] + ["%s@%.3f" % (pasta / ".work" / ("%s-recorte.webm" % k), float(r["inicio"]))
                             for k, r in recortes.items()] + [str(frente)]
    py("composite_overlay.py", video, *camadas, "-o", saida)
    leve = versao_leve(saida)
    for arq in (saida, leve):
        m = comum.sondar(arq)
        print("%s  %dx%d  %.2f fps  %.2fs  %.1f MB" % (arq.name, m["w"], m["h"], m["fps"], m["dur"],
                                                      arq.stat().st_size / 1048576))
    return 0


if __name__ == "__main__":
    sys.exit(main())
