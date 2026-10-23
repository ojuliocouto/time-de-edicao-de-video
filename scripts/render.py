#!/usr/bin/env python3
"""render.py - le o plano.json e produz o video, sempre a partir do ORIGINAL.

    python3 render.py --pasta <pasta> --ate inserts [--preview]

Nunca empilha etapa sobre etapa. Cada render e uma passada unica de ffmpeg
sobre o arquivo original aplicando todas as decisoes acumuladas ate a etapa
pedida. Isso mantem o resultado identico para o mesmo plano e evita a imagem
degradar por recodificacao sucessiva.

Os inserts entram nesta mesma passada. Um video pode ter varios inserts de
formatos diferentes, cada um ligado so na sua janela de tempo.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insert as fmt

ETAPAS = ["corte", "velocidade", "inserts", "zoom", "audio", "lettering"]

# Qualidade do encode. O preview em crf 28 foi comparado com crf 23 sobre
# material real e o resultado foi visualmente identico: a blocagem que parecia
# defeito do preview estava no arquivo de origem. Se algum dia um preview sair
# quebrado, rodar auditar.py antes de mexer aqui.
PREVIEW_Q = ["-crf", "28", "-preset", "veryfast", "-b:a", "128k"]
FINAL_Q = ["-crf", "18", "-preset", "veryfast", "-b:a", "192k"]   # rapido: arquivo maior, mesma qualidade (pedido de quem aprova)
NAO_IMPLEMENTADAS = set()

SUPER = 2               # quanto a imagem e ampliada antes do zoompan
RAMPA = 12              # quadros de entrada e saida do zoom suave


def projetar(t, manter, fator):
    """Converte tempo do video ORIGINAL para tempo do video final.

    E o que permite o plano.json guardar tudo em timecode do original: o
    insert e marcado em 'aos 19,4s do bruto' e aqui se descobre onde isso caiu
    depois dos cortes e da aceleracao. Tempo que cai dentro de um trecho
    removido vira o inicio do proximo bloco mantido."""
    acc = 0.0
    for a, b in manter:
        if t < a:
            return acc / fator
        if t <= b:
            return (acc + (t - a)) / fator
        acc += b - a
    return acc / fator


def curva_zoom(tipo, nframes, z):
    """Expressao do fator de zoom ao longo da janela, em funcao do quadro.

    O zoompan calcula a janela em pixel inteiro, o que faz a imagem tremer. Por
    isso a entrada e ampliada SUPER vezes antes: medido sobre um quadro parado,
    a irregularidade entre quadros cai de 0,083 para 0,041 com 2x. Com 4x cai
    so para 0,037, entao 2x e o ponto de equilibrio."""
    g = z - 1.0
    if tipo == "seco":
        return "%.4f" % z
    if tipo == "lento":
        return "1+%.4f*on/%d" % (g, max(1, nframes - 1))
    saida_r = max(RAMPA + 1, nframes - RAMPA)
    return ("1+%.4f*(min(1,max(0,on/%d))-min(1,max(0,(on-%d)/%d)))"
            % (g, RAMPA, saida_r, RAMPA))


def camada_zoom(rot, pde, pate, tipo, z, saida):
    n = max(2, int(round((pate - pde) * fmt.FPS)))
    return ("[%s]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS,"
            "scale=%d:%d:flags=bicubic,"
            "zoompan=z='%s':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            "d=1:s=%dx%d:fps=%s,setsar=1,"
            "tpad=start_duration=%.3f:color=black[%s];"
            % (rot, pde, pate, fmt.L * SUPER, fmt.A * SUPER,
               curva_zoom(tipo, n, z), fmt.L, fmt.A, fmt.FPS, pde, saida))


def cadeia_corte(rot, manter, saida, audio=False):
    """trim + concat dos blocos mantidos. Preferido ao 'select' por ser preciso
    bloco a bloco."""
    t, s, rotulos, linhas = ("atrim", "asetpts", [], [])
    if not audio:
        t, s = "trim", "setpts"
    for i, (a, b) in enumerate(manter):
        r = "%s%s%d" % (saida, "a" if audio else "v", i)
        linhas.append("[%s]%s=start=%.3f:end=%.3f,%s=PTS-STARTPTS[%s];" % (rot, t, a, b, s, r))
        rotulos.append("[%s]" % r)
    linhas.append("%sconcat=n=%d:v=%d:a=%d[%s];"
                  % ("".join(rotulos), len(manter), 0 if audio else 1, 1 if audio else 0, saida))
    return "".join(linhas)


def cadeia_velocidade(rot, fator, saida, audio=False):
    if abs(fator - 1.0) <= 0.001:
        return "[%s]%s[%s];" % (rot, "anull" if audio else "null", saida)
    if audio:
        restante, etapas = fator, []
        while restante > 2.0:
            etapas.append(2.0)
            restante /= 2.0
        etapas.append(restante)
        return "[%s]%s[%s];" % (rot, ",".join("atempo=%.4f" % e for e in etapas), saida)
    return "[%s]setpts=PTS/%.4f[%s];" % (rot, fator, saida)


def main():
    ap = argparse.ArgumentParser(description="Renderiza o plano de edicao")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--ate", default="velocidade", choices=ETAPAS)
    ap.add_argument("--saida", default=None)
    ap.add_argument("--preview", action="store_true",
                    help="720p e compressao rapida, para aprovacao")
    args = ap.parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg nao encontrado")

    pasta = Path(args.pasta).expanduser()
    caminho = pasta / "plano.json"
    if not caminho.exists():
        sys.exit("plano.json nao existe em %s" % pasta)
    plano = json.loads(caminho.read_text(encoding="utf-8"))

    alvo = ETAPAS.index(args.ate)
    pendentes = [e for e in ETAPAS[:alvo + 1] if e in NAO_IMPLEMENTADAS]
    if pendentes:
        ultima = [e for e in ETAPAS if e not in NAO_IMPLEMENTADAS][-1]
        sys.exit("etapa ainda nao construida nesta versao da skill: %s.\n"
                 "renderize ate '%s' e trate o resto com a pessoa."
                 % (", ".join(pendentes), ultima))

    fonte = Path(plano["fonte"]).expanduser()
    if not fonte.exists():
        sys.exit("video original nao encontrado: %s" % fonte)

    manter = plano["corte"]["manter"]
    if not manter:
        sys.exit("o plano nao tem nenhum bloco mantido")
    fator = plano["velocidade"]["fator"] if alvo >= ETAPAS.index("velocidade") else 1.0
    meta = plano["meta"]

    inserts = plano.get("inserts") or []
    if alvo < ETAPAS.index("inserts"):
        inserts = []
    inserts = sorted(inserts, key=lambda x: x["de"])

    som = ((plano.get("audio") or {}).get("efeitos") or []) \
        if alvo >= ETAPAS.index("audio") else []

    lettering = plano.get("lettering") if alvo >= ETAPAS.index("lettering") else None

    zooms = plano.get("zoom") or []
    if alvo < ETAPAS.index("zoom"):
        zooms = []
    zooms = sorted(zooms, key=lambda x: x["de"])

    # O fps de saida sai do BRUTO. Cravar 30 fazia um bruto de 25 fps sair com
    # quadro duplicado e movimento irregular, exatamente o erro que a fase 5.2
    # adverte para a mascara e que estava dentro do proprio codigo.
    fmt.definir_fps(meta["fps"])

    # A resolucao NAO e ajustavel: toda a geometria de insert e zoom foi medida
    # em pixel num quadro de 1080x1920, e a base nunca e reescalada. Num bruto
    # de outro tamanho o grafo mistura tamanhos e a saida sai torta. Recusar e
    # honesto; adivinhar nao e.
    if (meta["largura"], meta["altura"]) != (fmt.L, fmt.A):
        sys.exit("este bruto e %dx%d e a skill foi calibrada para %dx%d.\n"
                 "a geometria dos inserts e do zoom esta medida em pixel nesse "
                 "quadro, entao outra resolucao sai torta.\n\n"
                 "normalize antes e refaca a analise:\n"
                 "  ffmpeg -i \"<bruto>\" -vf "
                 "\"scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d\" "
                 "-c:a copy \"<bruto>-9x16.mp4\""
                 % (meta["largura"], meta["altura"], fmt.L, fmt.A,
                    fmt.L, fmt.A, fmt.L, fmt.A))

    precisa_matte = any(i["formato"] in fmt.PRECISA_MATTE for i in inserts)
    matte = pasta / "analise" / "matte.mp4"
    if precisa_matte and matte.exists():
        def dur_de(caminho):
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "format=duration", "-of", "csv=p=0", str(caminho)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
            try:
                return float(r.stdout.strip())
            except ValueError:
                return None
        def tamanho_de(caminho):
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=width,height",
                                "-of", "csv=p=0", str(caminho)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
            try:
                w, h = r.stdout.strip().split(",")[:2]
                return int(w), int(h)
            except ValueError:
                return None

        dm, dv = dur_de(matte), meta["duracao"]
        # a mascara tem que cobrir o video inteiro e na mesma duracao. Se ela foi
        # embrulhada num fps diferente do bruto, fica mais curta e o recorte vai
        # descolando da imagem ao longo do video, sem nada acusar.
        if dm is not None and abs(dm - dv) > 0.5:
            sys.exit("a mascara dura %.2fs e o video dura %.2fs.\n"
                     "quase sempre e o '-r' do ffmpeg diferente do fps do bruto "
                     "(%.2f fps). gere de novo com o mascara.py; ver estacoes/5-montagem.md."
                     % (dm, dv, meta["fps"]))

        # e tem que ter o MESMO tamanho do bruto. O comando da mascara ja veio
        # com 1080x1920 cravado; num bruto de outra resolucao o recorte sai
        # deslocado e esticado, e nada acusa. Mesma classe do erro de fps.
        tm = tamanho_de(matte)
        tv = (meta["largura"], meta["altura"])
        if tm is not None and tm != tv:
            sys.exit("a mascara e %dx%d e o video e %dx%d.\n"
                     "gere de novo passando a largura e a altura do BRUTO para o "
                     "mascara.py; ver estacoes/5-montagem.md."
                     % (tm[0], tm[1], tv[0], tv[1]))

    if precisa_matte and not matte.exists():
        sys.exit("os formatos %s precisam da mascara em %s.\n"
                 "gere com mascara.py; ver estacoes/5-montagem.md."
                 % (", ".join(sorted({i["formato"] for i in inserts
                                      if i["formato"] in fmt.PRECISA_MATTE})), matte))

    # ---------------------------------------------------------- entradas
    # contar '-i' em vez de dividir a lista por dois: a entrada do lettering usa
    # quatro itens ('-framerate N -i caminho'), e a conta por posicao fazia todos
    # os indices seguintes sairem errados, mandando o som para a trilha errada.
    def indice(lista):
        return len([a for a in lista if a == "-i"]) - 1

    def e_imagem(caminho):
        """Insert pode ser imagem parada, e nao so video: print de carrossel,
        criativo, thumbnail. Sem '-loop 1' o ffmpeg entrega um quadro so e o
        insert aparece por um trigesimo de segundo."""
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=format_name", "-of", "csv=p=0", str(caminho)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        f = r.stdout.strip().lower()
        return "_pipe" in f or f.startswith("image2")

    entradas = ["-i", str(fonte)]
    idx_insert = {}
    parado = {}
    for n, i in enumerate(inserts):
        arq = Path(i["arquivo"])
        if not arq.is_absolute():
            arq = pasta / arq
        if not arq.exists():
            sys.exit("arquivo de insert nao encontrado: %s" % arq)
        parado[n] = e_imagem(arq)
        if parado[n]:
            entradas += ["-loop", "1", "-framerate", str(fmt.FPS), "-i", str(arq)]
        else:
            entradas += ["-i", str(arq)]
        idx_insert[n] = indice(entradas)
    idx_matte = None
    if precisa_matte:
        entradas += ["-i", str(matte)]
        idx_matte = indice(entradas)

    # o lettering e desenhado pelo lettering.py (Pillow) em PNG transparente,
    # nao pelo 'drawtext' do ffmpeg: muita build do ffmpeg (a do Mac dela, por
    # exemplo) vem sem libfreetype e sem libass, e o drawtext nem existe nela.
    idx_lt = None
    if lettering:
        # sequencia de quadros, nao PNG unico: as animacoes medidas mudam o
        # TAMANHO do lettering ao longo do tempo, e o ffmpeg nao redimensiona
        # ao longo do tempo.
        seq = pasta / "analise" / "lettering"
        if seq.exists():
            shutil.rmtree(seq)
        spec = dict(lettering)
        spec["fps"] = fmt.FPS
        desenho = Path(__file__).resolve().parent / "lettering.py"
        py = comum.python_com("PIL")
        if not py:
            sys.exit("o lettering precisa do Pillow. Rode o preflight.py da skill.")
        r = subprocess.run([py, str(desenho), json.dumps(spec, ensure_ascii=False),
                            "--seq", str(seq)], capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        quadros = sorted(seq.glob("*.png")) if seq.exists() else []
        if r.returncode != 0 or not quadros:
            sys.exit("o desenho do lettering falhou:\n%s" % (r.stderr or r.stdout)[-1200:])
        entradas += ["-framerate", str(fmt.FPS), "-i", str(seq / "%04d.png")]
        idx_lt = indice(entradas)

    biblioteca = Path((plano.get("audio") or {}).get("biblioteca", ""))
    idx_som = {}
    for k, e in enumerate(som):
        arq = biblioteca / (e["nome"] + ".mp3")
        if not arq.exists():
            sys.exit("efeito sonoro nao encontrado: %s" % arq)
        entradas += ["-i", str(arq)]
        idx_som[k] = indice(entradas)

    # ------------------------------------------------------------ grafo
    g = []
    g.append(cadeia_corte("0:v", manter, "cv"))
    g.append(cadeia_velocidade("cv", fator, "bv0"))
    g.append(cadeia_corte("0:a", manter, "ca", audio=True))
    g.append(cadeia_velocidade("ca", fator, "ba0", audio=True))
    g.append("[ba0]aformat=channel_layouts=stereo:sample_rates=48000[ba1];")
    efx = plano.get("efeitos_video") or []
    if efx:
        # janelas em timecode do ORIGINAL, projetadas para o tempo final; o
        # efeito entra na base antes dos overlays, entao insert nao recebe.
        cadeia = []
        for e in efx:
            pde = projetar(float(e["de"]), manter, fator)
            pate = projetar(float(e["ate"]), manter, fator)
            if pate - pde < 0.04:
                continue
            if e["tipo"] == "pb":
                cadeia.append("hue=s=0:enable='between(t,%.3f,%.3f)'" % (pde, pate))
            else:
                sys.exit("efeito de video desconhecido no plano: %s" % e["tipo"])
        if cadeia:
            g.append("[bv0]%s,setsar=1,fps=%s[bv];" % (",".join(cadeia), fmt.FPS))
        else:
            g.append("[bv0]setsar=1,fps=%s[bv];" % fmt.FPS)
    else:
        g.append("[bv0]setsar=1,fps=%s[bv];" % fmt.FPS)

    if precisa_matte:
        g.append(cadeia_corte("%d:v" % idx_matte, manter, "cm"))
        g.append(cadeia_velocidade("cm", fator, "bm0"))
        g.append("[bm0]setsar=1,fps=%s[bm];" % fmt.FPS)

    sil = fmt.medir_silhueta(matte) if precisa_matte else None

    # so divide a base para os inserts que de fato usam a filmagem: tela_cheia e
    # moldura mostram so o apoio, e uma saida de split sem consumidor faz o
    # ffmpeg recusar o grafo inteiro.
    usam_orig = [n for n, i in enumerate(inserts) if i["formato"] not in fmt.SEM_ORIGINAL]
    rotulos = ["bv0"] + ["bvo%d" % n for n in usam_orig] + ["bvz%d" % k for k in range(len(zooms))]
    if len(rotulos) == 1:
        g.append("[bv]null[bv0];")
    else:
        g.append("[bv]split=%d%s;" % (len(rotulos), "".join("[%s]" % r for r in rotulos)))
    if precisa_matte:
        usam = [n for n, i in enumerate(inserts) if i["formato"] in fmt.PRECISA_MATTE]
        if len(usam) == 1:
            g.append("[bm]null[bm%d];" % usam[0])
        else:
            g.append("[bm]split=%d%s;" % (len(usam), "".join("[bm%d]" % k for k in usam)))

    acc = "bv0"
    avisos = []

    # zoom primeiro, insert por cima: insert nao recebe zoom, e se por engano
    # houvesse sobreposicao o insert venceria. plano.py ja recusa a sobreposicao.
    for k, z in enumerate(zooms):
        pde = projetar(z["de"], manter, fator)
        pate = projetar(z["ate"], manter, fator)
        if pate - pde < 0.2:
            avisos.append("zoom %d dura %.2fs depois dos cortes, quase nada" % (k, pate - pde))
            continue
        g.append(camada_zoom("bvz%d" % k, pde, pate, z["tipo"],
                             float(z.get("z", 1.12)), "cz%d" % k))
        g.append("[%s][cz%d]overlay=0:0:enable='between(t,%.3f,%.3f)':eof_action=pass[oz%d];"
                 % (acc, k, pde, pate, k))
        acc = "oz%d" % k

    # Dois inserts grudados na MESMA borda deixavam 1 quadro do rosto entre eles
    # (achado num anuncio real): o fim do primeiro arredonda para baixo e o comeco
    # do segundo para cima. O primeiro passa a durar 1 quadro alem da borda, por
    # baixo do segundo, que e desenhado por cima. Nada aparece do primeiro.
    # Numa validacao: so estender a janela nao bastava, porque o arquivo do
    # insert acabava antes do quadro extra e o eof_action=pass mostrava o rosto.
    # Agora: bordas presas na grade de quadros, e o fluxo do insert ganha
    # quadros clonados do fim (tpad clone) alem da janela.
    quadro = 1.0 / fmt.FPS
    grade = lambda t: round(t * fmt.FPS) / fmt.FPS
    janelas_ins = [[grade(projetar(i["de"], manter, fator)), grade(projetar(i["ate"], manter, fator))]
                   for i in inserts]
    for k in range(len(janelas_ins) - 1):
        if 0 <= janelas_ins[k + 1][0] - janelas_ins[k][1] < 1.5 * quadro:
            janelas_ins[k][1] = janelas_ins[k + 1][0] + quadro

    for n, i in enumerate(inserts):
        pde, pate = janelas_ins[n]
        dur = pate - pde
        if dur < 0.2:
            avisos.append("insert %d dura %.2fs depois dos cortes, quase nada" % (n, dur))
            continue
        oi = 0.0 if parado[n] else float(i.get("origem_ini", 0.0))
        # 'subir' desloca a arte para cima antes de qualquer composicao, para
        # que o painel do vazado ou a pessoa do react nao comam o fecho dela.
        # Corta do topo e completa embaixo com preto; como a folga de cima
        # costuma ser margem vazia, nao se perde nada.
        sb = int(i.get("subir", 0))
        desloca = ""
        if sb > 0:
            desloca = ("crop=iw:ih-%d:0:%d,pad=iw:%d:0:0:black,setsar=1,"
                       % (sb, sb, fmt.A))
        g.append("[%d:v]trim=start=%.3f:duration=%.3f,setpts=PTS-STARTPTS,"
                 "%sfps=%s,tpad=stop_mode=clone:stop_duration=0.5,"
                 "tpad=start_duration=%.3f:color=black[ins%d];"
                 % (idx_insert[n], oi, dur, desloca, fmt.FPS, pde, n))
        filtro, _ = fmt.camada(i["formato"], "ins%d" % n,
                               "bvo%d" % n if n in usam_orig else None,
                               "bm%d" % n if i["formato"] in fmt.PRECISA_MATTE else None,
                               "cam%d" % n, sil, i.get("altura_pessoa"), pref="i%d_" % n,
                               enquadrar=int(i.get("enquadrar", 0)))
        g.append(filtro)
        g.append("[%s][cam%d]overlay=0:0:enable='between(t,%.3f,%.3f)':eof_action=pass[ov%d];"
                 % (acc, n, pde, pate, n))
        acc = "ov%d" % n

    # --- som: cada efeito vira uma trilha atrasada ate o seu instante
    rot_audio = "ba1"
    if som:
        rots = []
        for k, e in enumerate(som):
            ms = int(round(projetar(float(e["em"]), manter, fator) * 1000))
            oi = float(e.get("origem_ini", 0.0))
            corte = ("atrim=start=%.3f,asetpts=PTS-STARTPTS," % oi) if oi > 0.001 else ""
            g.append("[%d:a]aformat=channel_layouts=stereo:sample_rates=48000,"
                     "%svolume=%.4f,adelay=%d:all=1[sfx%d];"
                     % (idx_som[k], corte, float(e.get("volume", 0.35)), ms, k))
            rots.append("[sfx%d]" % k)
        # normalize=0 e essencial: sem isso o amix divide o volume de todas as
        # trilhas pelo numero de entradas e a voz afunda a cada efeito.
        g.append("[ba1]%samix=inputs=%d:duration=first:normalize=0:"
                 "dropout_transition=0[ba];" % ("".join(rots), 1 + len(som)))
        rot_audio = "ba"

    if lettering and idx_lt is not None:
        de = projetar(float(lettering.get("de", 0.0)), manter, fator)
        ate = de + float(lettering.get("dur", 3.0))
        g.append("[%d:v]format=rgba,setpts=PTS-STARTPTS,fps=%s,"
                 "tpad=start_duration=%.3f:color=black@0[lt];"
                 % (idx_lt, fmt.FPS, de))
        g.append("[%s][lt]overlay=0:0:eof_action=pass[olt];" % acc)
        acc = "olt"

    escala = 1.0
    if args.preview:
        escala = min(1.0, 720.0 / min(meta["largura"], meta["altura"]))
    if escala < 0.999:
        g.append("[%s]scale=trunc(iw*%.5f/2)*2:trunc(ih*%.5f/2)*2[vs];" % (acc, escala, escala))
        acc = "vs"
    g.append("[%s]format=yuv420p[v]" % acc)

    grafo = "\n".join(g)
    script = pasta / "analise" / "filtro.txt"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(grafo, encoding="utf-8")

    if args.saida:
        saida = Path(args.saida).expanduser()
    else:
        n = ETAPAS.index(args.ate) + 1
        sub = "previews" if args.preview else "final"
        saida = pasta / sub / ("%02d-%s.mp4" % (n, args.ate))
    saida.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"] + entradas + [
        comum.opcao_script_filtro(), str(script), "-map", "[v]", "-map", "[%s]" % rot_audio,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart"]
    cmd += PREVIEW_Q if args.preview else FINAL_Q
    cmd.append(str(saida))

    print("renderizando %d blocos, velocidade %.2fx, %d inserts, %d zooms, %d efeitos%s"
          % (len(manter), fator, len(inserts), len(zooms), len(som),
             ", preview" if args.preview else ""))
    if lettering:
        print("lettering '%s' de %.2fs por %.2fs"
              % (lettering.get("estilo"), lettering.get("de", 0), lettering.get("dur", 0)))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        sys.exit("ffmpeg falhou:\n%s" % r.stderr[-2500:])

    esperado = sum(b[1] - b[0] for b in manter) / fator
    print("pronto: %s" % saida)
    print("duracao esperada: %.2fs" % esperado)
    for a in avisos:
        print("alerta: %s" % a)


if __name__ == "__main__":
    main()
