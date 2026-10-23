#!/usr/bin/env python3
"""insert.py - monta um insert sobre a filmagem original, num dos formatos.

    python3 insert.py --formato vazado_maior \\
        --original bruto.mp4 --insert apoio.mp4 --matte matte.mp4 \\
        --saida saida.mp4 [--de 0 --dur 9.8]

    python3 insert.py --medir --matte matte.mp4      # so mede, nao renderiza

Formatos que nao precisam de recorte de pessoa:
    tela_cheia, moldura, dividida_foco_original, dividida_foco_insert

Formatos que precisam de --matte (gerado por mascara.py):
    vazado_maior, vazado_pequeno, react, react_miniatura

Geometria e origem de cada numero: references/edicao-inserts.md
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import subprocess
import sys
from pathlib import Path

L, A = 1080, 1920                 # quadro de saida, vertical 9:16
# Toda a geometria abaixo foi medida EM PIXEL neste quadro. Mudar L e A sem
# recalibrar as constantes produz insert deslocado, entao o render recusa bruto
# de outra resolucao em vez de tentar adivinhar.

# fps do quadro de saida. Comeca em 30 so como padrao do uso avulso do
# insert.py; o render.py chama definir_fps() com o fps do BRUTO antes de montar
# qualquer coisa. Cravar 30 fazia um bruto de 25 fps sair com quadro duplicado,
# justamente o erro contra o qual a estacoes/5-montagem.md adverte.
FPS = 30


def definir_fps(v):
    """Ajusta o fps de saida para o do bruto. Aceita float (25.0, 29.97)."""
    global FPS
    FPS = v

# --- formatos sem recorte -------------------------------------------------
DIVIDIDA_FOCO_ORIGINAL = (716, 1204)   # faixa do insert, faixa do original
DIVIDIDA_FOCO_INSERT = (1200, 720)
MOLDURA_AREA = (1003, 1498)            # area de encaixe da caixa arredondada
MOLDURA_RAIO = 84

# --- formatos com recorte -------------------------------------------------
PAINEL_ALT = 480                       # altura do painel nos vazados
VAZADO_MAIOR = {"esc": 1.0, "pl": 1080, "raio": 180}
VAZADO_PEQUENO = {"esc": 0.7, "pl": 756, "raio": 126}
FRACAO_VAZAMENTO = 0.38                # da altura da cabeca; ver inserts.md

REACT_FAIXA = 1200                     # altura da faixa do insert no react
REACT_CENTRO = 793                     # centro horizontal da pessoa
REACT_ALTURA = 800                     # altura da pessoa na tela
REACT_FOLGA = 74 / 646.0               # folga insert->cabeca, proporcional a altura
MINI_RAIO = 40
MINI_MARGEM = 56

MASCARA_EFETIVA = 460   # largura para onde a mascara e reamostrada, sempre
EROSAO_BASE = 4.7       # erosoes por unidade de escala; ver inserts.md
SIGMA_BASE = 5.0        # desfoque da borda por unidade de escala
OCUPACAO_LIMITE = 0.15  # acima disso o recorte sai amputado


def ffprobe_dim(caminho):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0",
                        str(caminho)], capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def medir_silhueta(matte, instante=None):
    """Le um quadro da mascara e devolve o que a geometria precisa saber.

    ocupacao_lateral e o gatilho da decisao entre recorte e miniatura: quando a
    pessoa encosta na borda do quadro original, o recorte sai com uma linha reta
    no corpo, com cara de membro amputado."""
    w, h = ffprobe_dim(matte)
    cmd = ["ffmpeg", "-v", "error"]
    if instante:
        cmd += ["-ss", str(instante)]
    cmd += ["-i", str(matte), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    d = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL).stdout
    if len(d) < w * h:
        sys.exit("nao consegui ler um quadro da mascara: %s" % matte)

    def linha(y):
        return [x for x in range(0, w, 2) if d[y * w + x] > 128]

    topo = next((y for y in range(h) if len(linha(y)) > 2), 0)
    base = next((y for y in range(h - 1, -1, -1) if len(linha(y)) > 2), h - 1)
    centros = []
    for y in (int(h * 0.88), int(h * 0.93), int(h * 0.98)):
        f = linha(y)
        if f:
            centros.append((f[0] + f[-1]) // 2)
    centro = sum(centros) // len(centros) if centros else w // 2

    # pescoco: a silhueta abre no cabelo, estrangula no pescoco e abre de novo
    # nos ombros. O minimo local depois do ponto mais largo da cabeca marca o
    # fim da cabeca. Sem isso a unica medida disponivel seria a silhueta
    # inteira, que vai ate o pe do quadro e nao serve para posicionar.
    def larg(y):
        f = linha(y)
        return (f[-1] - f[0]) if f else 0

    lim = topo + int((base - topo) * 0.6)
    perfil = [(y, larg(y)) for y in range(topo, max(topo + 8, lim), 4)]
    pescoco = None
    if len(perfil) > 6:
        imax = max(range(len(perfil)), key=lambda k: perfil[k][1])
        for k in range(imax + 1, len(perfil) - 1):
            if perfil[k][1] <= perfil[k - 1][1] and perfil[k][1] < perfil[k + 1][1]:
                pescoco = perfil[k][0]
                break
    if pescoco is None:
        pescoco = topo + int((base - topo) * 0.45)

    def ocup(pix):
        return sum(1 for v in pix if v > 128) / max(1, len(pix))

    esq = ocup([d[y * w] for y in range(0, h, 4)])
    dire = ocup([d[y * w + w - 1] for y in range(0, h, 4)])
    return {"largura": w, "altura": h, "topo": topo, "base": base,
            "pescoco": pescoco, "altura_cabeca": pescoco - topo, "centro": centro,
            "ocupacao_esquerda": round(esq, 3), "ocupacao_direita": round(dire, 3),
            "ocupacao_lateral": round(max(esq, dire), 3),
            "recorte_amputado": max(esq, dire) > OCUPACAO_LIMITE}


def cadeia_mascara(larg, alt, esc):
    """Tratamento da borda, identico em todos os formatos com recorte.

    A reamostragem para MASCARA_EFETIVA e o que mais importa: ela apaga o
    degrau de alta frequencia da mascara. Foi descoberta comparando o react,
    que ficava bom porque a pessoa entra pequena e a reducao fazia essa media
    sozinha, com os vazados, que entram grandes e mostravam o degrau."""
    n = max(1, round(EROSAO_BASE * esc))
    eros = ",".join(["erosion"] * n)
    sigma = round(SIGMA_BASE * esc, 2)
    return ("format=gray,scale=%d:%d,%s,"
            "scale=%d:-2:flags=area,scale=%d:%d:flags=bicubic,"
            "gblur=sigma=%s,tmix=frames=3:weights='1 1 1',fps=%s"
            % (larg, alt, eros, MASCARA_EFETIVA, larg, alt, sigma, FPS))


def alfa_arredondado(raio, so_topo):
    dy = ("max(%d-Y,0)" % raio if so_topo
          else "max(max(%d-Y,Y-(H-1-%d)),0)" % (raio, raio))
    return ("a='clip(255*(%d-sqrt(pow(max(max(%d-X,X-(W-1-%d)),0),2)"
            "+pow(%s,2))+0.5),0,255)'" % (raio, raio, raio, dy))


def cobre(rot, larg, alt, saida, dy=0):
    """Amplia ate cobrir a faixa e corta o excedente pelo miolo.

    dy desloca o corte na vertical, em pixels: negativo sobe (mostra mais do
    topo), positivo desce. Serve para o rosto nao ficar cortado na testa nem no
    queixo quando a faixa e mais baixa que a pessoa. O valor e limitado ao que
    existe de imagem, entao um dy exagerado encosta na borda em vez de deixar
    faixa preta."""
    if dy:
        corte = ("crop=%d:%d:(iw-%d)/2:max(0\\,min(ih-%d\\,(ih-%d)/2+(%d)))"
                 % (larg, alt, larg, alt, alt, dy))
    else:
        corte = "crop=%d:%d" % (larg, alt)
    return ("[%s]scale=%d:%d:force_original_aspect_ratio=increase,"
            "%s,setsar=1,fps=%s[%s];" % (rot, larg, alt, corte, FPS, saida))


def zona_tapada(f, sil, altura_pessoa=None):
    """A partir de que y do quadro este formato COBRE o insert, ou None quando
    ele nao cobre nada.

    Nos vazados o painel come os ultimos PAINEL_ALT pixels, e a cabeca recortada
    ainda vaza acima dele. Quem monta o insert precisa saber disso: em material
    real o painel comia a frase de fecho de uma arte ("A MESMA HISTORIA") e a
    ultima linha de uma lista de tres, justamente o que a arte existia para
    dizer."""
    if f in ("vazado_maior", "vazado_pequeno"):
        if not sil:
            return None
        cfg = VAZADO_MAIOR if f == "vazado_maior" else VAZADO_PEQUENO
        vaz = int(FRACAO_VAZAMENTO * sil["altura_cabeca"] * cfg["esc"])
        return A - PAINEL_ALT - vaz
    if f in ("react", "react_miniatura"):
        return A - int(altura_pessoa or REACT_ALTURA)
    return None


def camada(f, ins, orig, mt, saida, sil=None, altura_pessoa=None, pref="", enquadrar=0):
    """Filtro que produz UMA camada de insert, em quadro cheio, a partir de
    rotulos ja existentes no grafo.

    ins   rotulo do video de apoio
    orig  rotulo da filmagem (no render integrado ja vem cortada e acelerada)
    mt    rotulo da mascara (idem), ou None
    pref  prefixo dos rotulos internos, para varios inserts no mesmo grafo
    enquadrar  desloca na vertical o corte da FILMAGEM nas divididas, em pixels
    """
    altura_pessoa = altura_pessoa or REACT_ALTURA
    r = lambda n: "%s%s" % (pref, n)
    p = []
    if f == "tela_cheia":
        p.append(cobre(ins, L, A, saida))
        return "".join(p), None

    if f == "moldura":
        p.append("color=black:s=%dx%d:r=%s,setsar=1[%s];" % (L, A, FPS, r("preto")))
        p.append("[%s]scale=%d:%d:force_original_aspect_ratio=decrease,"
                 "scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,fps=%s,format=rgba,"
                 "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':%s[%s];"
                 % (ins, MOLDURA_AREA[0], MOLDURA_AREA[1], FPS,
                    alfa_arredondado(MOLDURA_RAIO, False), r("cx")))
        p.append("[%s][%s]overlay=(W-w)/2:(H-h)/2[%s];" % (r("preto"), r("cx"), saida))
        return "".join(p), None

    if f in ("dividida_foco_original", "dividida_foco_insert"):
        topo, base = (DIVIDIDA_FOCO_ORIGINAL if f == "dividida_foco_original"
                      else DIVIDIDA_FOCO_INSERT)
        p.append(cobre(ins, L, topo, r("topo")))
        p.append(cobre(orig, L, base, r("base"), dy=enquadrar))
        p.append("[%s][%s]vstack=inputs=2[%s];" % (r("topo"), r("base"), saida))
        return "".join(p), None

    # daqui para baixo precisa de mascara
    if f in ("vazado_maior", "vazado_pequeno"):
        cfg = VAZADO_MAIOR if f == "vazado_maior" else VAZADO_PEQUENO
        esc, pl, raio = cfg["esc"], cfg["pl"], cfg["raio"]
        lw, lh = int(L * esc) // 2 * 2, int(A * esc) // 2 * 2
        px, py = (L - pl) // 2, A - PAINEL_ALT
        cab = int(sil["topo"] * esc)
        vaz = int(FRACAO_VAZAMENTO * sil["altura_cabeca"] * esc)
        y0 = py - vaz - cab
        cy = py - y0
        p.append(cobre(ins, L, A, r("fundo")))
        p.append("[%s]scale=%d:%d,setsar=1,fps=%s,split=2[%s][%s];"
                 % (orig, lw, lh, FPS, r("oa"), r("ob")))
        p.append("[%s]crop=%d:%d:%d:%d,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':%s[%s];"
                 % (r("oa"), pl, PAINEL_ALT, (lw - pl) // 2, cy,
                    alfa_arredondado(raio, True), r("painel")))
        p.append("[%s]%s[%s];" % (mt, cadeia_mascara(lw, lh, esc), r("mt")))
        p.append("[%s]format=rgba[%s];[%s][%s]alphamerge[%s];"
                 % (r("ob"), r("obr"), r("obr"), r("mt"), r("rec")))
        p.append("[%s][%s]overlay=%d:%d[%s];" % (r("fundo"), r("painel"), px, py, r("p1")))
        p.append("[%s][%s]overlay=%d:%d[%s];" % (r("p1"), r("rec"), (L - lw) // 2, y0, saida))
        return "".join(p), {"y0": y0, "corte_y": cy, "vazamento": vaz}

    if f in ("react", "react_miniatura"):
        altp = altura_pessoa
        p.append("color=black:s=%dx%d:r=%s,setsar=1[%s];" % (L, A, FPS, r("preto")))
        p.append(cobre(ins, L, REACT_FAIXA, r("ins")))
        folga = round(REACT_FOLGA * altp)
        topo_cab = REACT_FAIXA + folga
        if f == "react_miniatura":
            lw = int(altp * L / A) // 2 * 2
            x0 = int(REACT_CENTRO - lw / 2)
            y0 = A - MINI_MARGEM - altp
            p.append("[%s]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
                     "setsar=1,fps=%s,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':%s[%s];"
                     % (orig, lw, altp, lw, altp, FPS,
                        alfa_arredondado(MINI_RAIO, False), r("rec")))
        else:
            esc = altp / float(sil["altura"] - sil["topo"])
            lw, lh = int(L * esc) // 2 * 2, int(A * esc) // 2 * 2
            y0 = int(topo_cab - sil["topo"] * esc)
            x0 = int(REACT_CENTRO - sil["centro"] * esc)
            p.append("[%s]scale=%d:%d,setsar=1,fps=%s,format=rgba[%s];"
                     % (orig, lw, lh, FPS, r("pes")))
            p.append("[%s]%s[%s];" % (mt, cadeia_mascara(lw, lh, esc), r("mt")))
            p.append("[%s][%s]alphamerge[%s];" % (r("pes"), r("mt"), r("rec")))
        p.append("[%s][%s]overlay=0:0[%s];" % (r("preto"), r("ins"), r("p1")))
        p.append("[%s][%s]overlay=%d:%d[%s];" % (r("p1"), r("rec"), x0, y0, saida))
        return "".join(p), {"x0": x0, "y0": y0, "altura_pessoa": altp}

    sys.exit("formato desconhecido: %s" % f)


PRECISA_MATTE = ("vazado_maior", "vazado_pequeno", "react")
SEM_ORIGINAL = ("tela_cheia", "moldura")   # nao usam a filmagem, so o apoio


def main():
    ap = argparse.ArgumentParser(description="Monta um insert sobre a filmagem")
    ap.add_argument("--formato", default=None)
    ap.add_argument("--original", default=None)
    ap.add_argument("--insert", default=None)
    ap.add_argument("--matte", default=None)
    ap.add_argument("--saida", default=None)
    ap.add_argument("--de", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--altura-pessoa", type=int, default=REACT_ALTURA,
                    dest="altura_pessoa", help="altura da pessoa na tela, no react")
    ap.add_argument("--medir", action="store_true",
                    help="so mede a silhueta e sai; nao renderiza")
    args = ap.parse_args()

    if args.medir:
        if not args.matte:
            sys.exit("--medir precisa de --matte")
        s = medir_silhueta(args.matte)
        print(json.dumps(s, indent=1, ensure_ascii=False))
        print("\nocupacao lateral %.0f%% (limite %.0f%%)"
              % (100 * s["ocupacao_lateral"], 100 * OCUPACAO_LIMITE))
        if s["recorte_amputado"]:
            print("")
            print("SO IMPORTA NO FORMATO 'react'. Nele a pessoa aparece inteira sobre o")
            print("fundo, entao o ombro encostado na borda vira uma linha reta cortando o")
            print("corpo: PERGUNTE se ela quer recortado assim mesmo ou com o video em")
            print("miniatura ('react_miniatura'). Nao decida sozinho.")
            print("")
            print("Nos vazados NAO importa: la so a cabeca aparece acima do painel e o")
            print("ombro fica DENTRO do painel, onde a imagem e a filmagem crua. Nao")
            print("perguntar por causa disso em vazado. Verificado em material real.")
        else:
            print("a silhueta nao encosta nas bordas: o recorte sai inteiro em qualquer formato.")
        return

    for campo in ("formato", "original", "insert", "saida"):
        if not getattr(args, campo):
            sys.exit("faltando --%s" % campo)
    if args.formato in PRECISA_MATTE and not args.matte:
        sys.exit("o formato %s precisa de --matte (gere com mascara.py)" % args.formato)

    sil = medir_silhueta(args.matte) if args.matte else None

    entradas = []
    corte = (["-ss", str(args.de)] if args.de else []) + \
            (["-t", str(args.dur)] if args.dur else [])
    entradas += corte + ["-i", str(Path(args.insert).expanduser())]
    entradas += corte + ["-i", str(Path(args.original).expanduser())]
    if args.matte:
        entradas += (["-t", str(args.dur)] if args.dur else []) + \
                    ["-i", str(Path(args.matte).expanduser())]

    filtro, info = camada(args.formato, "0:v", "1:v", "2:v" if args.matte else None,
                          "v", sil, args.altura_pessoa)
    filtro = filtro + "[v]format=yuv420p[vf]"
    rotulo = "[vf]"

    saida = Path(args.saida).expanduser()
    saida.parent.mkdir(parents=True, exist_ok=True)
    script = saida.parent / ("filtro-%s.txt" % args.formato)
    script.write_text(filtro, encoding="utf-8")

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + entradas + [
        comum.opcao_script_filtro(), str(script), "-map", rotulo, "-map", "1:a?",
        "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "128k", "-shortest", str(saida)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        sys.exit("ffmpeg falhou:\n%s" % r.stderr[-2000:])

    w, h = ffprobe_dim(saida)
    if (w, h) != (L, A):
        sys.exit("saida com dimensao errada: %dx%d. o grafo montou torto." % (w, h))
    print("pronto: %s (%dx%d)" % (saida, w, h))
    if info:
        print("  " + " | ".join("%s=%s" % kv for kv in info.items()))
    if sil and sil["recorte_amputado"] and args.formato == "react":
        print("  atencao: ocupacao lateral de %.0f%%, o recorte pode ter saido amputado"
              % (100 * sil["ocupacao_lateral"]))


if __name__ == "__main__":
    main()
