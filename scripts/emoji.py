#!/usr/bin/env python
"""Desenha um emoji num PNG transparente APARADO NO ALFA, para usar como
"elemento" do lettering no estilo destaque.

    python emoji.py "💩" 420 saida.png

A imagem vem do Noto Emoji do Google (licenca Apache 2.0), em 512px, baixada
uma vez e guardada no cache da skill. Assim o emoji sai igual no Mac, no Windows
e no Linux (o desenho e o do Noto, nao o da Apple).

POR QUE APARAR NO ALFA. O lettering desenha o elemento na altura do bloco de
texto. Sobrando transparencia em volta, quem encolhe e o emoji: na versao Mac
ele saiu com 72px ao lado de um bloco de 127px, com cara de coisa esquecida.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    comum.reexecutar_com("PIL")

URL = "https://fonts.gstatic.com/s/e/notoemoji/latest/%s/512.png"
CACHE = comum.cache("emoji")


def nome_noto(emoji):
    """O Noto nomeia pelos codigos em hexa, ligados por '_', sem o seletor de
    variacao FE0F: '💩' vira '1f4a9', '❤️' vira '2764'."""
    return "_".join("%04x" % ord(c) for c in emoji if ord(c) != 0xFE0F)


def baixar(emoji):
    nome = nome_noto(emoji)
    if not nome:
        sys.exit("emoji vazio")
    CACHE.mkdir(parents=True, exist_ok=True)
    local = CACHE / (nome + ".png")
    if local.exists() and local.stat().st_size > 0:
        return local
    try:
        with urllib.request.urlopen(URL % nome, timeout=30) as r:
            local.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sys.exit("'%s' nao existe no Noto Emoji (procurei o codigo %s)" % (emoji, nome))
        sys.exit("falhou ao baixar o emoji: HTTP %d" % e.code)
    except urllib.error.URLError as e:
        sys.exit("falhou ao baixar o emoji, confira a internet: %s" % e.reason)
    return local


def main(argv):
    if len(argv) != 4 or not argv[2].isdigit() or int(argv[2]) <= 0:
        sys.exit("uso: emoji.py <emoji> <lado-em-px> <saida.png>")
    emoji, lado, destino = argv[1], int(argv[2]), argv[3]
    img = Image.open(baixar(emoji)).convert("RGBA")
    # caixa da tinta: menor retangulo com alfa acima de 8, como na versao Mac
    caixa = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not caixa:
        sys.exit("a imagem do emoji veio vazia")
    tinta = img.crop(caixa)
    escala = lado / max(tinta.width, tinta.height)
    lw, lh = max(1, round(tinta.width * escala)), max(1, round(tinta.height * escala))
    tinta.resize((lw, lh), Image.LANCZOS).save(destino)
    print("pronto: %s (%dx%d, aparado no alfa)" % (destino, lw, lh))


if __name__ == "__main__":
    main(sys.argv)
