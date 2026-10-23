#!/usr/bin/env python
"""Desenha o lettering em PNG 1080x1920 transparente, para o ffmpeg sobrepor.

    python lettering.py '<json>' <saida.png>
    python lettering.py '<json>' --seq <pasta-da-sequencia>

Versao Windows do lettering.swift da versao Mac, com a mesma geometria e as
mesmas animacoes, desenhada com Pillow (pip install pillow). A geometria de
cada estilo foi medida em pixel nas referencias; ver references/edicao-lettering.md.

Sequencia de quadros em vez de PNG unico: as animacoes mudam o TAMANHO do
lettering ao longo do tempo, e o ffmpeg nao redimensiona ao longo do tempo.
O conteudo e desenhado uma vez so; cada quadro so aplica a animacao.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import json
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    comum.reexecutar_com("PIL")

W, H = 1080, 1920

# Arial Bold e a fonte do sistema mais proxima da Helvetica Neue Bold das
# referencias, e existe no Mac e no Windows: o mesmo codigo sai igual nos dois.
# No Linux a Liberation Sans Bold tem as mesmas medidas da Arial. Sem nenhuma,
# cai na Inter que vem com a skill, em peso 700.
FONTES = [
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf",
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/Library/Fonts/Arial Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    Path("/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf"),
]
INTER = comum.FONTES / "Inter-Variable.ttf"


def achar_fonte():
    for f in FONTES:
        if f.exists():
            return str(f)
    return str(INTER)


CAMINHO_FONTE = achar_fonte()


def fonte(tam):
    f = ImageFont.truetype(CAMINHO_FONTE, int(round(tam)))
    if CAMINHO_FONTE == str(INTER):
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
    return f


def cor(s, padrao):
    h = (s or "").strip().lstrip("#")
    if len(h) != 6:
        return padrao
    try:
        v = int(h, 16)
    except ValueError:
        return padrao
    return ((v >> 16) & 255, (v >> 8) & 255, v & 255)


def largura(txt, f, kern):
    """O AppKit soma o kern depois de cada caractere, inclusive o ultimo."""
    return sum(f.getlength(c) for c in txt) + kern * len(txt)


def escrever(draw, x, y, txt, f, tinta, kern):
    """Caractere por caractere, porque o Pillow nao tem espacamento entre letras."""
    for c in txt:
        draw.text((x, y), c, font=f, fill=tinta, anchor="la")
        x += f.getlength(c) + kern


def quebrar(txt, f, kern, largura_max):
    """Quebra de linha por palavra, como o boundingRect do AppKit faz na caixa."""
    saida, atual = [], ""
    for palavra in txt.split(" "):
        teste = (atual + " " + palavra).strip()
        if atual and largura(teste, f, kern) > largura_max:
            saida.append(atual)
            atual = palavra
        else:
            atual = teste
    saida.append(atual)
    return saida


def base_caixa(spec, linhas, posicao):
    fundo = cor(spec.get("cor_fundo"), (255, 255, 255))
    tinta = cor(spec.get("cor_texto"), (0, 0, 0))
    tam, entre, pad, larg_caixa, kern = 63, 84, 36, 1016, 0.5
    f = fonte(tam)
    # 60 de margem da caixa mais 10 do lineFragmentPadding do AppKit
    util = larg_caixa - 70
    visuais = []
    for linha in linhas:
        visuais += quebrar(linha.upper(), f, kern, util)
    alt_texto = entre * len(visuais)
    alt_caixa = alt_texto + pad * 2
    # centro vertical, contado do TOPO: padrao 62,4%, medido na referencia.
    # meio sobe, abaixo desce para o terco inferior, onde nao tapa o rosto.
    fracao = 0.50 if posicao == "meio" else (0.78 if posicao == "abaixo" else 0.624)
    y_caixa = H * fracao - alt_caixa / 2
    x_caixa = (W - larg_caixa) / 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x_caixa, y_caixa, x_caixa + larg_caixa, y_caixa + alt_caixa],
                        radius=40, fill=fundo + (255,))
    asc, desc = f.getmetrics()
    larg_max = 0
    for k, txt in enumerate(visuais):
        lw = largura(txt, f, kern)
        larg_max = max(larg_max, lw)
        topo = y_caixa + pad + entre * k + (entre - (asc + desc)) / 2
        escrever(d, (W - lw) / 2, topo, txt, f, tinta + (255,), kern)
    print("caixa %dx%d | texto %dx%d" % (larg_caixa, alt_caixa, larg_max, alt_texto))
    return img


def base_destaque(spec, linhas, posicao):
    c1 = cor(spec.get("cor_linha1"), (0xFA, 0xFA, 0xFE))
    c2 = cor(spec.get("cor_linha2"), (0x69, 0xE2, 0xFE))
    folga, disponivel, kern = 25, 940, 1.0
    textos = [l.upper() for l in linhas]
    n = len(textos)
    # qualquer numero de linhas: a ULTIMA sai na cor de destaque
    cores = [c2 if k == n - 1 else c1 for k in range(n)]
    lista = spec.get("cores")
    if isinstance(lista, list):
        cores = [cor(lista[k], cores[k]) if k < len(lista) else cores[k] for k in range(n)]

    elemento = None
    cam = spec.get("elemento")
    if cam and Path(cam).exists():
        elemento = Image.open(cam).convert("RGBA")
    prop = (elemento.width / max(1, elemento.height)) if elemento else 0

    def medir(tam):
        f = fonte(tam)
        entre = tam * 0.88
        return [largura(t, f, kern) for t in textos], entre * n, entre

    # cada linha e UMA linha: o corpo encolhe ate o conjunto caber
    tam = 84
    while tam > 30:
        ls, alt, _ = medir(tam)
        larg_elem = folga + alt * prop if elemento else 0
        if max(ls) + larg_elem <= disponivel:
            break
        tam -= 2
    ls, alt, entre = medir(tam)
    larg_texto = max(ls)
    larg_elem = folga + alt * prop if elemento else 0
    x0 = (W - (larg_texto + larg_elem)) / 2
    fracao = 0.50 if posicao == "meio" else (0.78 if posicao == "abaixo" else 0.54)
    y_topo = H * fracao - alt / 2

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if elemento:
        e = elemento.resize((max(1, int(round(alt * prop))), max(1, int(round(alt)))),
                            Image.LANCZOS)
        img.alpha_composite(e, (int(round(x0 + larg_texto + folga)), int(round(y_topo))))

    f = fonte(tam)
    asc, desc = f.getmetrics()
    brilho = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    texto = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    db, dt = ImageDraw.Draw(brilho), ImageDraw.Draw(texto)
    for k, txt in enumerate(textos):
        topo = y_topo + entre * k + (entre - (asc + desc)) / 2
        # brilho branco, calibrado contra a sombra do AppKit (55%, desfoque 26)
        escrever(db, x0, topo, txt, f, (255, 255, 255, 255), kern)
        escrever(dt, x0, topo, txt, f, cores[k] + (255,), kern)
    brilho = brilho.filter(ImageFilter.GaussianBlur(9))
    brilho.putalpha(brilho.getchannel("A").point(lambda v: min(255, int(v * 1.25))))
    img.alpha_composite(brilho)
    img.alpha_composite(texto)
    print("corpo %d | texto %d | elemento %d | bloco %dx%d"
          % (tam, larg_texto, larg_elem, larg_texto + larg_elem, alt))
    return img


def quadro(base, estilo, tempo, duracao):
    """Aplica a animacao medida nas referencias sobre o desenho pronto.
    caixa:    entra pronta e SAI encolhendo para perto da base em 0,13s
    destaque: ENTRA deslizando 46px da esquerda em 0,9s, desacelerando,
              e sai deslizando e sumindo em 0,25s"""
    if estilo == "caixa":
        saida = 0.13
        if tempo <= duracao - saida:
            return base
        p = min(1.0, max(0.0, (tempo - (duracao - saida)) / saida))
        e = 1.0 - p * p
        vazio = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if e <= 0.02:
            return vazio
        ax, ay = W / 2, H * 0.70          # ancora: 30% contado de baixo
        menor = base.resize((max(1, int(W * e)), max(1, int(H * e))), Image.LANCZOS)
        vazio.paste(menor, (int(round(ax - ax * e)), int(round(ay - ay * e))))
        return vazio

    dx, alfa = 0.0, 1.0
    entrada, desloc, saida = 0.9, 46.0, 0.25
    if tempo < entrada:
        p = tempo / entrada
        dx -= desloc * (1 - p) * (1 - p)
    if tempo > duracao - saida:
        p = min(1.0, max(0.0, (tempo - (duracao - saida)) / saida))
        dx += desloc * p * p
        alfa = 1 - p
    if dx == 0 and alfa == 1:
        return base
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # out esta vazio: paste basta, e aceita deslocamento negativo
    out.paste(base, (int(round(dx)), 0))
    if alfa < 1:
        a = out.getchannel("A").point(lambda v: int(v * alfa))
        out.putalpha(a)
    return out


def main(argv):
    if len(argv) < 3:
        sys.exit("uso: lettering.py '<json>' <saida.png|--seq pasta>")
    try:
        spec = json.loads(argv[1])
    except ValueError:
        sys.exit("o primeiro argumento tem que ser o JSON do lettering")
    como_seq = "--seq" in argv
    # o destino e sempre o ULTIMO argumento
    destino = Path(argv[-1])
    fps = float(spec.get("fps", 30))
    duracao = float(spec.get("dur", 3.5))
    estilo = spec.get("estilo", "caixa")
    linhas = spec.get("linhas") or [spec.get("texto", "")]
    posicao = spec.get("posicao", "padrao")

    base = (base_caixa if estilo == "caixa" else base_destaque)(spec, linhas, posicao)
    if not como_seq:
        base.save(destino)
        return
    destino.mkdir(parents=True, exist_ok=True)
    n = max(1, int(duracao * fps))
    for q in range(n):
        quadro(base, estilo, q / fps, duracao).save(destino / ("%04d.png" % q))
    print("sequencia: %d quadros a %d fps em %s" % (n, fps, destino))


if __name__ == "__main__":
    main(sys.argv)
