#!/usr/bin/env python3
"""Captura uma pagina real para entrar num insert: print inteiro ou rolagem gravada.

    # print completo (padrao): espera a rede, carrega imagem preguicosa, tira cookie
    python capturar_pagina.py https://exemplo.com -o banco/telas/pagina.png
    python capturar_pagina.py https://exemplo.com -o banco/telas/cel.png --celular

    # rapido: so o Chrome de linha de comando. Serve para pagina estatica e
    # arquivo local; pagina feita em JS costuma sair em branco por aqui
    python capturar_pagina.py file:///caminho/pag.html -o banco/local.png --rapido --altura 3400

    # rolagem AO VIVO gravada, ja em MP4 30 fps com keyframe a cada 30 quadros
    python capturar_pagina.py https://exemplo.com --gravar banco/gravacoes/pag.mp4 \
        --segundos 10 --chaves "0:0,2:0,6:1400,10:1400"

As chaves sao `segundo:pixel`. Entre duas chaves a pagina rola com suavidade;
fora delas fica parada. Leia o print antes para achar o pixel de cada secao.

Usa o Chrome que o HyperFrames ja baixou (`npx hyperframes browser ensure`).
O modo completo e a gravacao precisam do puppeteer-core, que este script
instala sozinho uma vez no cache da skill (precisa de rede e de `npm`).
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import shutil
import sys
from pathlib import Path

PUPPETEER = "puppeteer-core@24"
NOMES = ("chrome-headless-shell", "chrome-headless-shell.exe", "chrome", "chrome.exe",
         "Google Chrome for Testing")


def achar_chrome():
    """O Chrome que o HyperFrames baixou. Pergunta a ele primeiro (a pasta mudou:
    ~/.cache/puppeteer ate a 0.8.x antiga, ~/.cache/hyperframes/chrome depois),
    e so procura nas pastas conhecidas se a pergunta falhar."""
    if comum.tem("npx"):
        r = comum.rodar(["npx", "--yes", "hyperframes", "browser", "path"], checar=False, timeout=180)
        for linha in reversed((r.stdout or "").splitlines()):
            linha = linha.strip().strip('"')
            if linha and Path(linha).is_file():
                return linha
    raizes = [Path.home() / ".cache" / "hyperframes", Path.home() / ".cache" / "puppeteer"]
    if os.environ.get("PUPPETEER_CACHE_DIR"):
        raizes.insert(0, Path(os.environ["PUPPETEER_CACHE_DIR"]))
    achados = []
    for raiz in raizes:
        if not raiz.exists():
            continue
        for p in raiz.rglob("*"):
            if p.name in NOMES and p.is_file() and (os.access(p, os.X_OK) or p.suffix == ".exe"):
                prioridade = 0 if "headless-shell" in p.name else 1
                achados.append((prioridade, str(p)))
    if not achados:
        return None
    return sorted(achados)[0][1] if achados else None


def garantir_puppeteer():
    pasta = comum.cache("node")
    modulo = pasta / "node_modules" / "puppeteer-core"
    if modulo.exists():
        return pasta / "node_modules"
    if not comum.tem("npm"):
        sys.exit("falta o npm (vem com o Node.js). Rode o preflight.py.")
    print("instalando %s no cache da skill (uma vez so)..." % PUPPETEER)
    env = dict(os.environ, PUPPETEER_SKIP_DOWNLOAD="1")
    comum.rodar(["npm", "install", "--no-audit", "--no-fund", "--prefix", str(pasta), PUPPETEER],
                env=env)
    return pasta / "node_modules"


def node(args):
    mods = garantir_puppeteer()
    env = dict(os.environ, NODE_PATH=str(mods))
    js = comum.SCRIPTS / "pagina.js"
    r = comum.rodar(["node", str(js)] + [str(a) for a in args], checar=False, env=env)
    sys.stdout.write(r.stdout or "")
    if r.returncode != 0:
        sys.exit("a captura falhou:\n%s" % (r.stderr or "")[-1200:])


def rapido(chrome, a, saida):
    comum.rodar([chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
                 "--window-size=%d,%d" % (a.largura, a.altura),
                 "--virtual-time-budget=%d" % a.espera,
                 "--screenshot=%s" % saida, a.url], checar=False)


def main():
    ap = argparse.ArgumentParser(description="Captura pagina real para insert.")
    ap.add_argument("url", help="http(s):// ou file://")
    ap.add_argument("-o", "--saida", help="PNG de saida (print)")
    ap.add_argument("--gravar", metavar="MP4", help="grava a rolagem neste MP4")
    ap.add_argument("--celular", action="store_true", help="print em tela de celular (430px, 3x)")
    ap.add_argument("--rapido", action="store_true", help="so o Chrome de linha de comando")
    ap.add_argument("--largura", type=int, default=1440)
    ap.add_argument("--altura", type=int, default=1000, help="modo rapido: altura da janela")
    ap.add_argument("--altura-max", type=int, default=6000, help="print completo: corta aqui")
    ap.add_argument("--espera", type=int, default=6000, help="milissegundos depois de carregar")
    ap.add_argument("--segundos", type=float, default=12.0)
    ap.add_argument("--chaves", default="0:0")
    ap.add_argument("--escala", type=float, default=1.5)
    a = ap.parse_args()

    if not a.url.startswith(("http://", "https://", "file://")):
        sys.exit("a url precisa comecar com http://, https:// ou file://")
    if not a.saida and not a.gravar:
        sys.exit("diga onde salvar: -o arquivo.png ou --gravar arquivo.mp4")

    chrome = achar_chrome()
    if not chrome:
        sys.exit("nao achei o Chrome do HyperFrames.\n"
                 "rode: npx --yes hyperframes browser ensure")

    if a.gravar:
        comum.exigir("ffmpeg")
        destino = Path(a.gravar).expanduser().resolve()
        quadros = comum.cache("gravacao", destino.stem)
        for q in quadros.glob("q*.jpg"):
            q.unlink()
        node(["gravar", chrome, a.url, quadros, a.segundos, a.chaves,
              1280 if a.largura == 1440 else a.largura, 960 if a.altura == 1000 else a.altura,
              a.escala, a.espera])
        destino.parent.mkdir(parents=True, exist_ok=True)
        # -g 30: midia dentro de insert sem keyframe frequente congela no HyperFrames
        comum.rodar(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", str(quadros / "q%04d.jpg"),
                     "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "16",
                     "-pix_fmt", "yuv420p", "-g", "30", "-keyint_min", "30", str(destino)])
        shutil.rmtree(quadros, ignore_errors=True)
        print("gravacao: %s" % destino)
        return 0

    saida = Path(a.saida).expanduser().resolve()
    saida.parent.mkdir(parents=True, exist_ok=True)
    if a.rapido:
        rapido(chrome, a, saida)
    else:
        node(["print", chrome, a.url, saida, "celular" if a.celular else "desktop",
              a.espera, a.altura_max])
    if not saida.exists() or saida.stat().st_size < 2000:
        sys.exit("a captura saiu vazia. Causas comuns: URL 404, pagina com login,\n"
                 "ou (no --rapido) pagina feita em JS: tente sem --rapido.")
    kb = saida.stat().st_size // 1024
    print("%s  %d KB" % (saida, kb))
    if kb < 20:
        print("aviso: arquivo bem pequeno; abra o PNG e confira se a pagina renderizou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
