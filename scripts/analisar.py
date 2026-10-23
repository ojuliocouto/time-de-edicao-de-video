#!/usr/bin/env python3
"""analisar.py - le o video bruto e produz a materia prima da etapa de corte.

    python3 analisar.py <video> --pasta <pasta-de-trabalho> [--contexto "..."]

Gera dentro de <pasta-de-trabalho>/analise/:
    palavras.json      uma entrada por palavra, com inicio e fim em segundos
    silencios.json     trechos de silencio detectados pelo ffmpeg
    transcricao.txt    texto legivel com marcacao de tempo, para o agente ler

Nao decide nada. Apenas mede. As decisoes ficam em plano.py.

Divisao de trabalho entre as duas fontes, aprendida em material real:
o silencedetect e exato no TEMPO e o whisper e confiavel no TEXTO. Onde os
dois discordam, o tempo do silencedetect vence.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import array
import bisect
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

MODELO_PADRAO = Path.home() / ".cache" / "whisper-cpp" / "ggml-large-v3-turbo.bin"
MIN_SILENCIO = 0.10        # so registra silencio a partir daqui
ABAIXO_DA_FALA = 14.0      # quantos dB abaixo do nivel de fala fica o limiar
ACIMA_DO_PISO = 8.0        # ... mas nunca colado no piso de ruido
LIMIAR_MIN, LIMIAR_MAX = -65.0, -28.0
SILENCIO_ALUCINACAO = 0.5  # silencio a partir do qual palavra dentro dele e suspeita


def exigir(binario):
    if not comum.tem(binario):
        sys.exit("faltando: %s. instale antes de rodar." % binario)


def rodar(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        sys.exit("falhou: %s\n%s" % (" ".join(cmd[:3]), r.stderr[-1500:]))
    return r


def metadados(video):
    r = rodar(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,r_frame_rate",
               "-show_entries", "format=duration",
               "-of", "json", str(video)])
    d = json.loads(r.stdout)
    if not d.get("streams"):
        sys.exit("o arquivo nao tem trilha de video: %s" % video)
    s = d["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {
        "duracao": round(float(d["format"]["duration"]), 3),
        "fps": round(float(num) / float(den), 3),
        "largura": s["width"],
        "altura": s["height"],
    }


def extrair_audio(video, destino):
    rodar(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
           "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(destino)])


# ------------------------------------------------------------ limiar

def niveis(wav, janela=0.02):
    """dBFS por janela curta, lido em blocos para nao carregar o audio inteiro."""
    w = wave.open(str(wav), "rb")
    sr = w.getframerate()
    n = int(janela * sr)
    saida = []
    while True:
        bruto = w.readframes(n * 200)
        if not bruto:
            break
        a = array.array("h")
        a.frombytes(bruto)
        for i in range(0, len(a) - n + 1, n):
            s = 0
            for v in a[i:i + n]:
                s += v * v
            s /= n
            saida.append(20 * math.log10(math.sqrt(s) / 32768.0) if s > 0 else -99.0)
    w.close()
    return saida


def limiar_de_silencio(wav):
    """Limiar fixo nao serve. Material bem gravado tem fala perto de -12 dBFS e
    material captado de longe tem fala em -40. No video de teste a fala vivia
    entre -33 e -48, e um limiar fixo de -35 dB classificava 89% do audio como
    abaixo do limiar, ou seja, engolia a fala inteira.

    Aqui o limiar sai da distribuicao do proprio audio: 14 dB abaixo do nivel
    de fala (percentil 85), mas nunca a menos de 8 dB do piso de ruido
    (percentil 5), que e o que impede o limiar de cair tao fundo que so pegue
    silencio absoluto e perca as pausas com ruido de sala.

    Calibrado num anuncio falado de 69s: fala em -36,9 e piso em -74,2 dao
    limiar de -50,9, e nessa faixa o video de 69s sai com 24% de silencio e
    encolhe para 58s. Com o limiar fixo de -35 que havia antes, 89% do audio
    ficava abaixo do limiar; com -61, so 9%."""
    v = niveis(wav)
    if not v:
        return -35.0, None
    v.sort()
    piso = v[int(len(v) * 0.05)]
    fala = v[int(len(v) * 0.85)]
    lim = max(fala - ABAIXO_DA_FALA, piso + ACIMA_DO_PISO)
    lim = max(LIMIAR_MIN, min(LIMIAR_MAX, lim))
    return round(lim, 1), {"piso": round(piso, 1), "fala": round(fala, 1)}


def detectar_silencios(wav, duracao, limiar):
    import re
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(wav),
         "-af", "silencedetect=n=%sdB:d=%s" % (limiar, MIN_SILENCIO),
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    log = r.stderr
    inicios = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", log)]
    fins = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", log)]
    silencios = []
    for n, ini in enumerate(inicios):
        fim = fins[n] if n < len(fins) else duracao
        ini = max(0.0, ini)
        if fim > ini:
            silencios.append({"ini": round(ini, 3), "fim": round(fim, 3),
                              "dur": round(fim - ini, 3)})
    return silencios


# -------------------------------------------------------- transcricao

MOTOR = "auto"   # definido no main: mlx, faster ou whispercpp


def transcrever(wav, modelo, idioma, contexto, saida_base):
    """Palavras com i, texto, ini e fim. O motor sai do transcrever.py: mlx no
    Mac, faster-whisper nos tres sistemas, whisper.cpp de reserva. Os reparos
    abaixo (trecho perdido, cauda, alucinacao, encaixe nos silencios) valem para
    qualquer motor."""
    import transcrever as tr
    ws, _ = tr.palavras(wav, idioma, motor=MOTOR, contexto=contexto)
    palavras = [{"i": i, "texto": w["p"], "ini": round(w["t"], 3), "fim": round(w["f"], 3)}
                for i, w in enumerate(ws)]
    if not palavras:
        sys.exit("a transcricao voltou vazia. modelo errado ou audio mudo.")
    return palavras


# --- trecho que o transcritor perdeu ------------------------------------------
# O whisper as vezes entra em loop: para de acompanhar a fala e passa a repetir a
# ultima frase, esticando cada palavra por segundos. Em material real ele comeu
# 32s de um anuncio de 121s, justamente a oferta e o CTA, e repetiu "nao e a
# falta de ideias" ate o fim. Nada acusava: o arquivo tinha palavras, tempos e
# texto plausivel.
#
# A assinatura e sempre a mesma: palavra curta durando segundos NUM TRECHO ONDE
# O AUDIO TEM FALA. Se o audio estivesse mudo seria alucinacao, que o
# descartar_alucinacao ja trata. Aqui e o contrario: tem fala e falta texto.
PALAVRA_ESTICADA = 0.9     # segundos; acima disso uma palavra curta e suspeita
LETRAS_CURTAS = 8          # ate quantas letras a palavra conta como curta
TRECHO_MINIMO = 3.0        # so vale reparar trecho a partir deste tamanho
# Folga generosa a ESQUERDA: o loop comeca antes da primeira palavra esticada,
# entao margem curta deixa lixo na emenda. Com 1,5s sumiu "digital nao e a falta
# de ideias" logo no comeco do reparo.
MARGEM_ESQ = 4.0
MARGEM_DIR = 1.0
# Trechos proximos viram UM SO. Reparar em dois blocos com um vao no meio deixa
# o texto ruim justamente na emenda: em material real sumiu "digital nao e a
# falta de ideias" e "na Operacao Claude Code", cada um caindo numa borda. O
# whisper acerta muito mais recebendo o raciocinio inteiro de uma vez.
COLAR_TRECHOS = 12.0
BURACO_MIN = 1.5          # segundos de fala sem palavra nenhuma = trecho perdido


def trechos_perdidos(palavras, silencios, duracao):
    """Devolve os intervalos em que o transcritor provavelmente entrou em loop."""
    def em_silencio(t):
        return any(s["ini"] <= t <= s["fim"] for s in silencios)

    suspeitas = [(w["ini"], w["fim"]) for w in palavras
                 if (w["fim"] - w["ini"]) > PALAVRA_ESTICADA
                 and len(w["texto"].strip()) <= LETRAS_CURTAS
                 and not em_silencio((w["ini"] + w["fim"]) / 2.0)]
    # Buraco sem palavra que NAO e silencio: fala que o transcritor pulou. Na
    # validacao o 2o take inteiro de uma frase (26 palavras) sumiu
    # assim, sem palavra esticada nenhuma para denunciar.
    def falado(a, b):
        tot = b - a
        for sl in silencios:
            tot -= max(0.0, min(b, sl["fim"]) - max(a, sl["ini"]))
        return tot
    marcos = [(0.0, 0.0)] + [(w["ini"], w["fim"]) for w in palavras] + [(duracao, duracao)]
    for (a0, f0), (a1, f1) in zip(marcos, marcos[1:]):
        if a1 - f0 > BURACO_MIN and falado(f0, a1) > BURACO_MIN:
            suspeitas.append((f0, a1))
    if not suspeitas:
        return []
    suspeitas.sort()

    trechos, ini, fim = [], suspeitas[0][0], suspeitas[0][1]
    for a, b in suspeitas[1:]:
        if a - fim <= COLAR_TRECHOS:
            fim = max(fim, b)
        else:
            trechos.append((ini, fim))
            ini, fim = a, b
    trechos.append((ini, fim))
    # Devolve (contexto_ini, contexto_fim, troca_ini, troca_fim). A folga da
    # esquerda serve para o whisper pegar o raciocinio, mas SO se substitui do
    # inicio do loop em diante: com margem larga na troca, texto bom do original
    # ("que trava o crescimento de um negocio digital") era jogado fora e voltava
    # pior.
    # O whisper arredonda o clipe para multiplo de 30s e pode devolver palavras
    # com tempo ALEM do fim do audio; um "trecho" que comece depois da duracao
    # vira janela invertida no clamp e derruba o ffmpeg. Nao ha nada real para
    # reparar ali, entao o filtro final exige a janela dentro do video.
    return [t for t in
            ((max(0.0, a - MARGEM_ESQ), min(duracao, b + MARGEM_DIR),
              max(0.0, a - MARGEM_ESQ), min(duracao, b + MARGEM_DIR))
             for a, b in trechos if b - a >= min(TRECHO_MINIMO, BURACO_MIN))
            if t[0] < t[1]]


def sem_repeticao(ws):
    """Duas passadas: sobreposicao e sequencia repetida."""
    ws = _sem_sobreposicao(sorted(ws, key=lambda w: (w["ini"], w["fim"])))
    return _sem_sequencia_repetida(ws)


def _sem_sobreposicao(ws):
    """Palavra de fala nao se sobrepoe a outra. Quando o whisper repete a ultima
    frase, a copia sai com tempos EM CIMA da primeira, e depois de ordenar as
    duas viram sopa: "so tocar garantir no botao a aqui sua embaixo". Aqui cai
    fora toda palavra que ocupa mais de 60% do mesmo tempo de uma ja aceita."""
    fora = []
    for w in ws:
        alvo = w["texto"].strip().lower()
        # So descarta copia LITERAL sobreposta. Uma primeira versao descartava
        # por sobreposicao de tempo sozinha e comeu fala legitima: em fala
        # rapida o whisper devolve palavras com duracao quase zero que se
        # encostam, e sumiram "falta de ideias, e o tempo que ele demora para
        # transformar" e metade do CTA.
        if any(j["texto"].strip().lower() == alvo
               and min(w["fim"], j["fim"]) - max(w["ini"], j["ini"]) > 0
               for j in fora):
            continue
        fora.append(w)
    return fora


def _sem_sequencia_repetida(ws):
    """Tira sequencia identica colada. O whisper costuma repetir a ultima frase
    ao fechar um bloco, e depois de ordenar por tempo as duas copias ficam
    INTERCALADAS e viram sopa: "so tocar garantir no botao aqui embaixo a e
    garantir sua vaga. a sua vaga.". Por isso a limpeza roda no bloco recem
    transcrito, onde as palavras ainda estao na ordem em que foram ditas."""
    limpo, k = [], 0
    while k < len(ws):
        rep = 0
        for n in range(6, 1, -1):
            if k + 2 * n <= len(ws):
                a = [x["texto"].strip().lower() for x in ws[k:k + n]]
                b = [x["texto"].strip().lower() for x in ws[k + n:k + 2 * n]]
                if a == b and any(len(s) > 2 for s in a):
                    rep = n
                    break
        limpo.extend(ws[k:k + rep] if rep else [ws[k]])
        k += 2 * rep if rep else 1
    return limpo


def reparar_trechos(palavras, trechos, wav, modelo, idioma, base):
    """Retranscreve cada trecho perdido isolado e costura no lugar.

    Vai SEM --prompt de proposito: o contexto ajuda nome proprio, mas alimenta o
    loop quando ele ja comecou."""
    reparados = 0
    for k, (a, b, ta, tb) in enumerate(trechos):
        pedaco = Path(str(base) + "-reparo%d.wav" % k)
        rodar(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % a, "-to", "%.3f" % b,
               "-i", str(wav), "-ac", "1", "-ar", "16000", str(pedaco)])
        try:
            novas = transcrever(pedaco, modelo, idioma, None,
                                Path(str(base) + "-reparo%d" % k))
        except SystemExit:
            continue
        finally:
            pedaco.unlink(missing_ok=True)
        # O whisper.cpp arredonda o clipe para multiplo de 30s e estica o fim:
        # num trecho de 38,9s ele devolveu palavras ate 60s. Sem corrigir isto
        # ANTES de somar o deslocamento, a janela de troca descarta metade do
        # texto recuperado, que foi como o CTA sumiu duas vezes seguidas.
        corrigir_cauda(novas, b - a)
        for w in novas:
            w["ini"] = round(w["ini"] + a, 3)
            w["fim"] = round(w["fim"] + a, 3)
        novas = sem_repeticao([w for w in novas
                               if w["ini"] >= ta - 0.01 and w["fim"] <= tb + 0.01])
        palavras[:] = [w for w in palavras
                       if w["fim"] <= ta + 0.01 or w["ini"] >= tb - 0.01]
        palavras.extend(novas)
        palavras.sort(key=lambda w: (w["ini"], w["fim"]))
        reparados += 1

    for i, w in enumerate(palavras):
        w["i"] = i
    return reparados


def corrigir_cauda(palavras, duracao):
    """O whisper.cpp processa em blocos de 30s e estende o ultimo segmento ate a
    fronteira do bloco, nao ate o fim real do audio. Num video de 69s ele devolve
    palavras terminando em 90s."""
    fora = [p for p in palavras if p["fim"] > duracao + 0.01]
    if not fora:
        return 0
    i0 = palavras.index(fora[0])
    ini0 = palavras[i0]["ini"]
    span = palavras[-1]["fim"] - ini0
    disp = duracao - ini0
    if span <= 0 or disp <= 0:
        for w in palavras[i0:]:
            w["ini"] = round(min(w["ini"], duracao - 0.05), 3)
            w["fim"] = round(min(w["fim"], duracao), 3)
        return len(fora)
    f = disp / span
    for w in palavras[i0:]:
        w["ini"] = round(ini0 + (w["ini"] - ini0) * f, 3)
        w["fim"] = round(ini0 + (w["fim"] - ini0) * f, 3)
    return len(fora)


def descartar_alucinacao(palavras, silencios):
    """Whisper inventa um encerramento plausivel quando o audio acaba. No video
    de teste ele colocou 14 palavras dentro de um trecho medido em -70 dBFS,
    isto e, silencio absoluto.

    O filtro varre SO DE TRAS PARA A FRENTE e para na primeira palavra que nao
    cai em silencio. Uma primeira versao varria o video inteiro e descartou 33
    palavras, das quais 8 grupos eram fala real: como o whisper erra o tempo em
    cerca de 0,14s, palavra curta legitima cai dentro de silencio detectado com
    facilidade. Alucinacao de verdade fica no rabo, e so ali."""
    longos = [s for s in silencios if s["dur"] >= SILENCIO_ALUCINACAO]
    if not longos or not palavras:
        return 0
    # margem folgada no lado direito: o silencio final termina junto com o
    # arquivo, e a ultima palavra alucinada encosta nele por centesimos.
    dentro = lambda w: any(s["ini"] + 0.05 <= (w["ini"] + w["fim"]) / 2.0 <= s["fim"] + 0.10
                           for s in longos)
    n = 0
    while palavras and dentro(palavras[-1]):
        palavras.pop()
        n += 1
    for k, w in enumerate(palavras):
        w["i"] = k
    return n


def encaixar_nos_silencios(palavras, silencios, tol=0.30):
    """Uma palavra termina onde o silencio comeca e a proxima comeca onde ele
    acaba. Cada borda de palavra e puxada para a borda de silencio mais proxima
    quando houver uma dentro da tolerancia."""
    if not silencios:
        return 0
    comecos = sorted(s["ini"] for s in silencios)
    fins = sorted(s["fim"] for s in silencios)

    def perto(t, lista):
        i = bisect.bisect_left(lista, t)
        cands = lista[max(0, i - 1):i + 1]
        if not cands:
            return t, False
        b = min(cands, key=lambda v: abs(v - t))
        return (b, True) if abs(b - t) <= tol else (t, False)

    ajustes = 0
    for w in palavras:
        f, ok1 = perto(w["fim"], comecos)
        i, ok2 = perto(w["ini"], fins)
        if ok1 and f > w["ini"] + 0.02:
            w["fim"] = round(f, 3); ajustes += 1
        if ok2 and i < w["fim"] - 0.02:
            w["ini"] = round(i, 3); ajustes += 1
    for a, b in zip(palavras, palavras[1:]):
        if a["fim"] > b["ini"]:
            a["fim"] = b["ini"]
    return ajustes


def aparar_silencio(palavras, silencios):
    """O whisper estica a palavra por cima do silencio seguinte: no material de
    teste 'botao' aparecia ocupando 1,52s. Isso faz a regra de fronteira recusar
    cortes de pausa legitimos, porque o corte cai 'dentro de uma palavra' que na
    verdade e silencio."""
    if not silencios:
        return 0
    n = 0
    for w in palavras:
        for s in silencios:
            if s["fim"] <= w["ini"] + 0.001 or s["ini"] >= w["fim"] - 0.001:
                continue
            if s["ini"] <= w["ini"]:
                novo = min(s["fim"], w["fim"] - 0.03)
                if novo > w["ini"]:
                    w["ini"] = round(novo, 3); n += 1
            elif s["fim"] >= w["fim"]:
                novo = max(s["ini"], w["ini"] + 0.03)
                if novo < w["fim"]:
                    w["fim"] = round(novo, 3); n += 1
            else:
                if (s["ini"] - w["ini"]) >= (w["fim"] - s["fim"]):
                    w["fim"] = round(s["ini"], 3)
                else:
                    w["ini"] = round(s["fim"], 3)
                n += 1
    return n


def transcricao_legivel(palavras, silencios):
    """Texto com marcacao de tempo e o tamanho de cada pausa no meio.
    E isto que o agente le para julgar gagueira e comeco falso."""
    longos = [s for s in silencios if s["dur"] >= 0.35]
    quebra = {}
    for s in longos:
        alvo = min(palavras, key=lambda w: abs(w["fim"] - s["ini"]))
        if abs(alvo["fim"] - s["ini"]) <= 0.35:
            quebra[alvo["i"]] = s["dur"]

    linhas, buffer, ini_bloco = [], [], None
    for p in palavras:
        if ini_bloco is None:
            ini_bloco = p["ini"]
        buffer.append(p["texto"])
        if p["i"] in quebra:
            linhas.append("[%07.3f -> %07.3f] %s" % (ini_bloco, p["fim"], " ".join(buffer)))
            linhas.append("            (pausa de %.2fs)" % quebra[p["i"]])
            buffer, ini_bloco = [], None
    if buffer:
        linhas.append("[%07.3f -> %07.3f] %s" % (ini_bloco, palavras[-1]["fim"], " ".join(buffer)))
    return "\n".join(linhas)


def main():
    ap = argparse.ArgumentParser(description="Mede o video bruto para a etapa de corte")
    ap.add_argument("video")
    ap.add_argument("--pasta", required=True, help="pasta de trabalho do video")
    ap.add_argument("--modelo", default=os.environ.get("WHISPER_MODELO", str(MODELO_PADRAO)))
    ap.add_argument("--idioma", default="pt")
    ap.add_argument("--contexto", default=None,
                    help="termos do assunto; melhora nomes proprios e jargao")
    ap.add_argument("--motor", default="auto", choices=["auto", "mlx", "faster", "whispercpp"],
                    help="motor de transcricao; auto escolhe o melhor instalado")
    ap.add_argument("--limiar", type=float, default=None,
                    help="limiar de silencio em dBFS; por padrao sai do proprio audio")
    args = ap.parse_args()

    global MOTOR
    comum.exigir("ffmpeg", "ffprobe")
    import transcrever as tr
    MOTOR, onde = tr.escolher(args.motor)
    print("motor de transcricao: %s (%s)" % (MOTOR, onde))

    video = Path(args.video).expanduser()
    if not video.exists():
        sys.exit("video nao encontrado: %s" % video)
    modelo = Path(args.modelo).expanduser()

    pasta = Path(args.pasta).expanduser()
    analise = pasta / "analise"
    analise.mkdir(parents=True, exist_ok=True)

    meta = metadados(video)
    print("video: %.1fs, %dx%d, %.2f fps" %
          (meta["duracao"], meta["largura"], meta["altura"], meta["fps"]))

    wav = analise / "audio.wav"
    extrair_audio(video, wav)

    if args.limiar is not None:
        limiar, perfil = args.limiar, None
        print("limiar de silencio: %.1f dBFS (informado)" % limiar)
    else:
        limiar, perfil = limiar_de_silencio(wav)
        print("limiar de silencio: %.1f dBFS (piso %.1f, fala %.1f)" %
              (limiar, perfil["piso"], perfil["fala"]))

    silencios = detectar_silencios(wav, meta["duracao"], limiar)

    print("transcrevendo (pode levar alguns minutos; sem GPU, ate o tempo do video)...")
    palavras = transcrever(wav, modelo, args.idioma, args.contexto, analise / "whisper")

    perdidos = trechos_perdidos(palavras, silencios, meta["duracao"])
    if perdidos:
        print("o transcritor parece ter perdido %d trecho(s) com fala:" % len(perdidos))
        for _, _, ta, tb in perdidos:
            print("   %.1fs a %.1fs (%.1fs)" % (ta, tb, tb - ta))
        print("retranscrevendo isolado...")
        reparar_trechos(palavras, perdidos, wav, modelo, args.idioma, analise / "whisper")

    invadidas = corrigir_cauda(palavras, meta["duracao"])
    inventadas = descartar_alucinacao(palavras, silencios)
    encaixadas = encaixar_nos_silencios(palavras, silencios)
    aparadas = aparar_silencio(palavras, silencios)

    meta["limiar_silencio"] = limiar
    (analise / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (analise / "palavras.json").write_text(json.dumps(palavras, indent=1, ensure_ascii=False), encoding="utf-8")
    (analise / "silencios.json").write_text(json.dumps(silencios, indent=1, ensure_ascii=False), encoding="utf-8")
    (analise / "transcricao.txt").write_text(transcricao_legivel(palavras, silencios), encoding="utf-8")

    mudo = sum(s["dur"] for s in silencios)
    print("%d palavras, %d silencios, %.0f%% do video e silencio" %
          (len(palavras), len(silencios), 100.0 * mudo / meta["duracao"]))
    if perdidos:
        print("%d trecho(s) foram retranscritos isolados; CONFIRA a transcricao ali"
              % len(perdidos))
    if invadidas:
        print("%d palavras vinham com tempo alem do fim do audio e foram reescaladas" % invadidas)
    if inventadas:
        print("%d palavras caiam dentro de silencio e foram descartadas como alucinacao" % inventadas)
    if encaixadas:
        print("%d bordas de palavra encaixadas na borda de silencio mais proxima" % encaixadas)
    if aparadas:
        print("%d palavras invadiam silencio e foram aparadas" % aparadas)
    print("escrito em %s" % analise)


if __name__ == "__main__":
    main()
