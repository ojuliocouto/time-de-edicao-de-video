#!/usr/bin/env python3
"""plano.py - cria, valida e ajusta o plano.json, que e o estado da edicao.

Regra central: todo tempo dentro do plano.json se refere ao VIDEO ORIGINAL,
nunca a um arquivo intermediario. E isso que permite reverter um corte da
etapa 1 depois que os inserts ja estao montados sem refazer nada.

Subcomandos:
    criar       monta o plano inicial cortando as pausas
    aplicar     junta as remocoes julgadas pelo agente (gagueira etc.)
    restaurar   devolve um corte especifico
    velocidade  muda o fator de velocidade
    validar     roda as regras de seguranca
    resumo      relatorio legivel do que vai ser cortado
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

RESPIRO = 0.15          # silencio maximo mantido entre falas
PAUSA_DRAMATICA = 0.60  # silencio mantido antes de uma virada de raciocinio
VELOCIDADE = 1.3        # fator uniforme aplicado ao video inteiro
BLOCO_MINIMO = 0.12     # abaixo disso o bloco e inaudivel e vira audio picotado
BLOCO_CURTO = 0.25      # entre minimo e isto vira alerta, nao erro
TOL_PALAVRA = 0.08      # quanto um corte pode invadir uma palavra antes de ser recusado
CORTE_MAXIMO = 0.60     # cortar mais que isto sem pedido explicito e sintoma de erro
META_INSERT = 10.0      # meta: pelo menos um insert a cada 10s de video final
TAKE_SEM_ZOOM = 5.0     # take de rosto acima disso tem que receber zoom
ZOOM_PADRAO = 1.12      # 12%, calibrado com ela sobre material real
TIPOS_ZOOM = ("seco", "suave", "lento")

ESTILOS_LETTERING = ("caixa", "destaque")
LETTERING_DUR = 3.5   # decisao dela: fixo nos dois estilos, nao a duracao de cada referencia
POSICOES_LETTERING = ("padrao", "meio", "abaixo")

BIBLIOTECA_SFX = comum.SFX   # whoosh, click e riser vem com a skill (Pixabay, uso livre)
SFX_INSERT = "whoosh-short"   # 0,57s
SFX_ZOOM = "click-soft"       # 0,37s
ABAIXO_DA_VOZ = 6.0           # dB que o efeito fica abaixo do nivel de fala
JUNTOS = 0.15                 # dois efeitos a menos disso viram um so
METRALHADORA_EFEITOS = 4      # a partir de quantos efeitos juntos o trecho soa metralhado
METRALHADORA_JANELA = 6.0     # dentro de quantos segundos do original
SFX_RISER = "riser"           # o pico e MEDIDO, nao lido do manifesto
RISER_ABAIXO = 4.0            # a subida e continua sob a fala, mas precisa ser ouvida
RISER_JANELA = 12.0           # ela e de ABERTURA: o pico nunca cai depois disso

FORMATOS = ("tela_cheia", "moldura", "dividida_foco_original", "dividida_foco_insert",
            "vazado_maior", "vazado_pequeno", "react", "react_miniatura")

TIPOS = ("pausa", "gagueira", "comeco_falso", "hesitacao", "trecho")

MARCADORES_VIRADA = (
    "e sabe", "sabe qual", "so que", "mas ", "so que", "e adivinha", "e ai",
    "acontece que", "o resultado", "e por isso", "agora presta", "presta atencao",
    "olha so", "repara", "e ai que", "e o pior", "o problema e", "a verdade e",
)


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def carregar(pasta):
    p = Path(pasta).expanduser() / "plano.json"
    if not p.exists():
        sys.exit("plano.json nao existe em %s. rode 'criar' primeiro." % pasta)
    return json.loads(p.read_text(encoding="utf-8")), p


def salvar(plano, caminho):
    caminho.write_text(json.dumps(plano, indent=1, ensure_ascii=False), encoding="utf-8")


def ler_analise(pasta):
    a = Path(pasta).expanduser() / "analise"
    faltando = [n for n in ("meta.json", "palavras.json", "silencios.json")
                if not (a / n).exists()]
    if faltando:
        sys.exit("faltam arquivos de analise (%s). rode analisar.py primeiro."
                 % ", ".join(faltando))
    return (json.loads((a / "meta.json").read_text(encoding="utf-8")),
            json.loads((a / "palavras.json").read_text(encoding="utf-8")),
            json.loads((a / "silencios.json").read_text(encoding="utf-8")))


# ---------------------------------------------------------------- pausas

def protegida(silencio, palavras):
    """Uma pausa longa antes de uma virada de raciocinio e ritmo, nao ruido.
    Tambem protege a pausa que vem logo depois de uma pergunta retorica."""
    antes = [p["texto"] for p in palavras if p["fim"] <= silencio["ini"]][-3:]
    if antes and "?" in " ".join(antes):
        return True
    # so as primeiras palavras depois da pausa contam. varrer mais que isso
    # faz uma expressao distante marcar uma pausa que nao tem nada a ver.
    depois = [p["texto"] for p in palavras if p["ini"] >= silencio["fim"]][:4]
    frase = sem_acento(" ".join(depois))
    return any(frase.startswith(m) for m in MARCADORES_VIRADA)


def cortes_de_pausa(silencios, palavras, meta, respiro, dramatica):
    fim_video = meta["duracao"]
    fala_ini = palavras[0]["ini"]
    fala_fim = palavras[-1]["fim"]
    cortes = []

    for s in silencios:
        if s["ini"] <= 0.05:                       # silencio de abertura
            alvo = max(0.0, min(fala_ini, s["fim"]) - respiro)
            if alvo > 0.05:
                cortes.append({"de": 0.0, "ate": round(alvo, 3),
                               "tipo": "pausa", "motivo": "silencio de abertura"})
            continue
        if s["fim"] >= fim_video - 0.05:           # silencio de encerramento
            alvo = max(fala_fim + respiro, s["ini"])
            if fim_video - alvo > 0.05:
                cortes.append({"de": round(alvo, 3), "ate": round(fim_video, 3),
                               "tipo": "pausa", "motivo": "silencio de encerramento"})
            continue

        manter = dramatica if protegida(s, palavras) else respiro
        if s["dur"] <= manter + 0.02:
            continue
        # o que sobra e 'manter', metade de cada lado. o miolo vai embora.
        metade = manter / 2.0
        cortes.append({
            "de": round(s["ini"] + metade, 3),
            "ate": round(s["fim"] - metade, 3),
            "tipo": "pausa",
            "motivo": ("pausa dramatica reduzida para %.2fs" % manter
                       if manter == dramatica else "pausa reduzida para %.2fs" % manter),
        })
    return cortes


# ---------------------------------------------- fronteira de palavra

def ajustar_fronteira(t, palavras, silencios=None):
    """Corte nunca cai no meio de uma palavra. Encosta na borda mais proxima
    quando a invasao e pequena; recusa quando e funda.

    Silencio detectado tem precedencia sobre span de palavra: o silencedetect e
    exato e o whisper e aproximado. Um corte dentro de um silencio detectado e
    sempre legitimo, mesmo que o span da palavra diga o contrario."""
    if silencios:
        for s in silencios:
            if s["ini"] - 0.02 <= t <= s["fim"] + 0.02:
                return t, None
    for p in palavras:
        if p["ini"] < t < p["fim"]:
            d_ini, d_fim = t - p["ini"], p["fim"] - t
            if min(d_ini, d_fim) > TOL_PALAVRA:
                return None, ("corte em %.3fs cai dentro da palavra '%s' (%.3f-%.3f)"
                              % (t, p["texto"], p["ini"], p["fim"]))
            return (p["ini"] if d_ini < d_fim else p["fim"]), None
    return t, None


def normalizar(cortes, palavras, silencios=None):
    limpos, erros = [], []
    for c in cortes:
        de, e1 = ajustar_fronteira(c["de"], palavras, silencios)
        ate, e2 = ajustar_fronteira(c["ate"], palavras, silencios)
        if e1 or e2:
            erros.append(e1 or e2)
            continue
        if ate - de < 0.02:
            continue
        d = dict(c)
        d["de"], d["ate"] = round(de, 3), round(ate, 3)
        limpos.append(d)
    limpos.sort(key=lambda x: x["de"])

    # funde cortes que se encostam ou se sobrepoem
    fundidos = []
    for c in limpos:
        if fundidos and c["de"] <= fundidos[-1]["ate"] + 0.001:
            if c["ate"] > fundidos[-1]["ate"]:
                fundidos[-1]["ate"] = c["ate"]
            # ao fundir, o tipo que REMOVE FALA vence o de pausa, senao o corte
            # deliberado some da lista de revisao so por encostar num silencio.
            if fundidos[-1]["tipo"] == "pausa" and c["tipo"] != "pausa":
                fundidos[-1]["tipo"] = c["tipo"]
                for campo in ("texto", "motivo"):
                    if c.get(campo):
                        fundidos[-1][campo] = c[campo]
        else:
            fundidos.append(c)
    return fundidos, erros


def calcular_manter(cortes, duracao):
    """Deriva os blocos mantidos a partir dos cortes. Blocos curtos demais
    somem: empilhados eles produzem aquele audio picotado de corte automatico."""
    blocos, cursor, descartados = [], 0.0, []
    for c in sorted(cortes, key=lambda x: x["de"]):
        if c["de"] > cursor:
            blocos.append([round(cursor, 3), round(c["de"], 3)])
        cursor = max(cursor, c["ate"])
    if cursor < duracao:
        blocos.append([round(cursor, 3), round(duracao, 3)])

    bons = []
    for b in blocos:
        if b[1] - b[0] < BLOCO_MINIMO:
            descartados.append(b)
        else:
            bons.append(b)
    return bons, descartados


def recalcular(plano, palavras, silencios=None):
    cortes, erros = normalizar(plano["corte"]["removidos"], palavras, silencios)
    plano["corte"]["removidos"] = cortes
    manter, descartados = calcular_manter(cortes, plano["meta"]["duracao"])
    plano["corte"]["manter"] = manter
    return erros, descartados


# ---------------------------------------------------------------- validar

def validar(plano, palavras, silencios=None):
    erros, alertas = [], []
    dur = plano["meta"]["duracao"]
    manter = plano["corte"]["manter"]

    if not manter:
        erros.append("nenhum bloco sobrou. o plano cortaria o video inteiro.")
        return erros, alertas

    restante = sum(b[1] - b[0] for b in manter)
    cortado = 1.0 - (restante / dur)
    if cortado > CORTE_MAXIMO and not plano["corte"]["parametros"].get("corte_agressivo"):
        erros.append("o plano corta %.0f%% do video. acima de %.0f%% costuma ser "
                     "transcricao falhada ou parametro errado. investigue antes de "
                     "renderizar, ou marque corte_agressivo se for de proposito."
                     % (cortado * 100, CORTE_MAXIMO * 100))

    for b in manter:
        d = b[1] - b[0]
        if d < BLOCO_MINIMO:
            erros.append("bloco de %.3fs em %.2fs e curto demais, gera audio picotado" % (d, b[0]))
        elif d < BLOCO_CURTO:
            alertas.append("bloco curto de %.3fs em %.2fs, confira se nao picotou" % (d, b[0]))

    for c in plano["corte"]["removidos"]:
        if c["tipo"] not in TIPOS:
            erros.append("tipo de corte desconhecido: %s" % c["tipo"])
        for t in (c["de"], c["ate"]):
            _, e = ajustar_fronteira(t, palavras, silencios)
            if e:
                erros.append(e)

    fator = plano.get("velocidade", {}).get("fator", 1.0)
    if not 0.5 <= fator <= 3.0:
        erros.append("fator de velocidade fora de faixa util: %s" % fator)
    return erros, alertas


# --------------------------------------------------------------- resumo

def texto_em(palavras, de, ate):
    ps = [p["texto"] for p in palavras if p["ini"] >= de - 0.01 and p["fim"] <= ate + 0.01]
    return " ".join(ps)


def resumo(plano, palavras):
    dur = plano["meta"]["duracao"]
    manter = plano["corte"]["manter"]
    restante = sum(b[1] - b[0] for b in manter)
    fator = plano.get("velocidade", {}).get("fator", 1.0)

    por_tipo = {}
    for c in plano["corte"]["removidos"]:
        d = por_tipo.setdefault(c["tipo"], [0, 0.0])
        d[0] += 1
        d[1] += c["ate"] - c["de"]

    linhas = ["ORIGINAL      %6.2fs" % dur]
    for t in TIPOS:
        if t in por_tipo:
            n, s = por_tipo[t]
            linhas.append("  - %-13s %2d cortes, %5.2fs" % (t, n, s))
    linhas.append("APOS CORTE    %6.2fs  (%.0f%% do original)" % (restante, 100 * restante / dur))
    linhas.append("APOS %.2fx     %6.2fs" % (fator, restante / fator))
    linhas.append("")
    linhas.append("blocos mantidos: %d" % len(manter))
    linhas.append("")
    linhas.append("CORTES QUE REMOVEM FALA (revise estes):")
    achou = False
    for i, c in enumerate(plano["corte"]["removidos"]):
        if c["tipo"] == "pausa":
            continue
        achou = True
        linhas.append("  [%d] %7.3f-%7.3f  %-13s \"%s\"" %
                      (i, c["de"], c["ate"], c["tipo"],
                       c.get("texto") or texto_em(palavras, c["de"], c["ate"])))
        if c.get("motivo"):
            linhas.append("       motivo: %s" % c["motivo"])
    if not achou:
        linhas.append("  nenhum. so pausas foram cortadas ate agora.")

    ins = plano.get("inserts") or []
    if ins:
        linhas.append("")
        linhas.append("INSERTS:")
        for k, i in enumerate(sorted(ins, key=lambda x: x["de"])):
            linhas.append("  [%d] %7.3f-%7.3f  %-22s %s" %
                          (k, i["de"], i["ate"], i["formato"],
                           Path(i["arquivo"]).name))
            if i.get("motivo"):
                linhas.append("       motivo: %s" % i["motivo"])
    zs = plano.get("zoom") or []
    if zs:
        linhas.append("")
        linhas.append("ZOOMS:")
        for k, z in enumerate(sorted(zs, key=lambda x: x["de"])):
            linhas.append("  [%d] %7.3f-%7.3f  %-6s %.0f%%  %s" %
                          (k, z["de"], z["ate"], z["tipo"],
                           100 * (z.get("z", 1.12) - 1), z.get("motivo", "")))

    takes = takes_de_rosto(plano)
    faltando = [t for t in takes if t["precisa"]]
    if takes:
        linhas.append("")
        linhas.append("TAKES DE ROSTO (o que sobra do final depois de tirar os inserts)")
        linhas.append("  A COLUNA 'no original' E A QUE VAI NA LISTA DE ZOOM.")
        linhas.append("  %-16s %-18s %s" % ("no video final", "no original", ""))
        for t in takes:
            marca = ""
            if t["precisa"]:
                marca = "  <-- acima de %.0fs SEM ZOOM" % TAKE_SEM_ZOOM
            elif t["tem_zoom"]:
                marca = "  (com zoom)"
            linhas.append("  %6.2f-%6.2f    %7.2f-%7.2f   %5.2fs%s"
                          % (t["de"], t["ate"], t["de_orig"], t["ate_orig"],
                             t["dur"], marca))
        if faltando:
            linhas.append("  %d take(s) de rosto passam de %.0fs sem zoom. A imagem estagna ali."
                          % (len(faltando), TAKE_SEM_ZOOM))

    lt = plano.get("lettering")
    if lt:
        linhas.append("")
        linhas.append("LETTERING: %s, de %.2fs por %.2fs" %
                      (lt.get("estilo"), lt.get("de", 0), lt.get("dur", 0)))
        for l in lt.get("linhas", []):
            linhas.append("  %s" % l)

    som = (plano.get("audio") or {}).get("efeitos") or []
    if som:
        linhas.append("")
        linhas.append("SOM: %d efeitos" % len(som))

    d = densidade(plano)
    linhas.append("")
    linhas.append("densidade: %d inserts em %.1fs de video final | meta %d (1 a cada %.0fs)"
                  % (d["inserts"], d["duracao_final"], d["meta"], META_INSERT))
    if not d["bate"]:
        if d["inserts"]:
            linhas.append("  a meta nao bateu. PERGUNTE se ela quer procurar insert num banco")
            linhas.append("  ou se segue assim. Nao decida sozinho.")
    return "\n".join(linhas)


# ------------------------------------------------------------ comandos

def trabalho_posterior(plano):
    """Lista o que existe no plano DEPOIS da etapa de corte, em texto legivel.

    Serve para o 'criar' saber que nao esta diante de um plano em branco."""
    fora = []
    n = len(plano.get("inserts") or [])
    if n:
        fora.append("%d insert(s)" % n)
    n = len(plano.get("zoom") or [])
    if n:
        fora.append("%d zoom(s)" % n)
    n = len(((plano.get("audio") or {}) or {}).get("efeitos") or [])
    if n:
        fora.append("%d efeito(s) de som" % n)
    if plano.get("lettering"):
        fora.append("o lettering")
    return fora


def cmd_criar(args):
    pasta = Path(args.pasta).expanduser()

    # O 'criar' monta o plano do ZERO. Rodar de novo numa pasta que ja avancou
    # apaga insert, zoom, som e lettering sem deixar rastro: num teste real
    # sumiram 7 inserts, 6 zooms, 13 efeitos e o lettering de uma vez so. Como a
    # skill inteira existe para ajuste custar barato, isto vira uma recusa.
    antigo = pasta / "plano.json"
    if antigo.exists() and not args.recomecar:
        try:
            fora = trabalho_posterior(json.loads(antigo.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            fora = []
        if fora:
            sys.exit(
                "RECUSADO: ja existe plano nesta pasta com %s.\n"
                "'criar' monta o plano do zero e isso tudo seria apagado.\n\n"
                "Para mudar o corte sem perder o resto, use 'restaurar' ou "
                "'aplicar'.\nPara jogar fora de proposito e recomecar: "
                "--recomecar" % ", ".join(fora))

    meta, palavras, silencios = ler_analise(pasta)
    cortes = cortes_de_pausa(silencios, palavras, meta, args.respiro, args.dramatica)

    plano = {
        "fonte": str(Path(args.fonte).expanduser().resolve()) if args.fonte else None,
        "meta": meta,
        "etapa_atual": "corte",
        "aprovado_ate": None,
        "corte": {
            "parametros": {
                "respiro": args.respiro,
                "pausa_dramatica": args.dramatica,
                "cortar": ["gagueira", "comeco_falso", "hesitacao"],
            },
            "manter": [],
            "removidos": cortes,
        },
        "velocidade": {"modo": "uniforme", "fator": args.velocidade},
        "inserts": [],
        "zoom": [],
        "audio": None,
        "lettering": None,
    }
    erros_f, descartados = recalcular(plano, palavras, silencios)
    salvar(plano, pasta / "plano.json")

    print(resumo(plano, palavras))
    for e in erros_f:
        print("RECUSADO: %s" % e)
    for b in descartados:
        print("bloco de %.3fs em %.2fs descartado por ser curto demais" % (b[1] - b[0], b[0]))
    print("\nplano escrito em %s" % (pasta / "plano.json"))
    print("proximo passo: ler analise/transcricao.txt e marcar gagueira, "
          "comeco falso e hesitacao com 'aplicar'.")


def cmd_aplicar(args):
    plano, caminho = carregar(args.pasta)
    _, palavras, silencios = ler_analise(args.pasta)
    novos = json.loads(Path(args.remocoes).expanduser().read_text(encoding="utf-8"))
    if not isinstance(novos, list):
        sys.exit("o arquivo de remocoes tem que ser uma lista de objetos")

    for n in novos:
        for campo in ("de", "ate", "tipo"):
            if campo not in n:
                sys.exit("remocao sem campo '%s': %s" % (campo, n))
        if n["tipo"] not in TIPOS:
            sys.exit("tipo invalido '%s'. use um de: %s" % (n["tipo"], ", ".join(TIPOS)))
        n["de"], n["ate"] = float(n["de"]), float(n["ate"])

    plano["corte"]["removidos"].extend(novos)
    erros_f, descartados = recalcular(plano, palavras, silencios)
    erros, alertas = validar(plano, palavras, silencios)

    # erros_f sao cortes recusados pela regra de fronteira de palavra. eles ja
    # foram descartados, mas descartar em silencio faria quem pediu achar que
    # o corte entrou. entao a aplicacao inteira falha e nada e salvo.
    if erros or erros_f:
        print("PLANO RECUSADO, nada foi salvo:")
        for e in erros + erros_f:
            print("  %s" % e)
        sys.exit(1)
    salvar(plano, caminho)
    print(resumo(plano, palavras))
    for a in alertas:
        print("alerta: %s" % a)
    for b in descartados:
        print("bloco de %.3fs em %.2fs descartado por ser curto demais" % (b[1] - b[0], b[0]))


def cmd_restaurar(args):
    plano, caminho = carregar(args.pasta)
    _, palavras, silencios = ler_analise(args.pasta)
    rem = plano["corte"]["removidos"]
    if not 0 <= args.indice < len(rem):
        sys.exit("indice fora da lista (0 a %d)" % (len(rem) - 1))
    fora = rem.pop(args.indice)
    recalcular(plano, palavras, silencios)
    salvar(plano, caminho)
    print("devolvido: %.3f-%.3f (%s)" % (fora["de"], fora["ate"], fora["tipo"]))
    print(resumo(plano, palavras))


def cmd_velocidade(args):
    plano, caminho = carregar(args.pasta)
    _, palavras, silencios = ler_analise(args.pasta)
    plano["velocidade"] = {"modo": "uniforme", "fator": args.fator}
    erros, _ = validar(plano, palavras, silencios)
    if erros:
        sys.exit("\n".join(erros))
    salvar(plano, caminho)
    print(resumo(plano, palavras))


ETAPAS_APROVAVEIS = ("velocidade", "inserts", "zoom", "audio", "lettering")



EFEITOS_VIDEO = ("pb",)


def cmd_efeito(args):
    """Efeito de imagem sobre a filmagem base, em timecode do ORIGINAL.
    Hoje so 'pb' (preto e branco). Insert nao recebe o efeito: ele e
    aplicado na base antes dos overlays, entao tela_cheia cobre e as
    divididas mostram a faixa da filmagem ja tratada."""
    plano, caminho = carregar(args.pasta)
    if args.limpar and args.tipo is None:
        # so apagar, sem por nada no lugar
        plano["efeitos_video"] = []
        salvar(plano, caminho)
        print("efeitos de video: nenhum (lista limpa)")
        return
    if args.tipo is None or args.de is None or args.ate is None:
        sys.exit("faltou --tipo, --de ou --ate. Para so apagar, use --limpar sozinho.")
    if args.tipo not in EFEITOS_VIDEO:
        sys.exit("efeito desconhecido: %s. use um de: %s"
                 % (args.tipo, ", ".join(EFEITOS_VIDEO)))
    if args.ate <= args.de:
        sys.exit("janela invalida: ate (%s) tem que ser maior que de (%s)"
                 % (args.ate, args.de))
    lista = plano.get("efeitos_video") or []
    if args.limpar:
        lista = []
    lista.append({"de": args.de, "ate": args.ate, "tipo": args.tipo,
                  "motivo": args.motivo or ""})
    plano["efeitos_video"] = lista
    salvar(plano, caminho)
    for e in lista:
        print("efeito %s: %.2fs a %.2fs (original)  %s"
              % (e["tipo"], e["de"], e["ate"], e.get("motivo", "")))


def cmd_aprovar(args):
    """Registra ate onde a PESSOA aprovou. Nao e enfeite: e o que separa
    'ja passou pelo olho dela' de 'o agente achou que estava bom'. Sem isto
    gravado, uma conversa retomada nao sabe qual portao ja caiu."""
    plano, caminho = carregar(args.pasta)
    if args.etapa not in ETAPAS_APROVAVEIS:
        sys.exit("etapa desconhecida: %s. use uma de: %s"
                 % (args.etapa, ", ".join(ETAPAS_APROVAVEIS)))
    plano["aprovado_ate"] = args.etapa
    salvar(plano, caminho)
    print("aprovado ate: %s" % args.etapa)


def cmd_validar(args):
    plano, _ = carregar(args.pasta)
    _, palavras, silencios = ler_analise(args.pasta)
    erros, alertas = validar(plano, palavras, silencios)
    for a in alertas:
        print("alerta: %s" % a)
    if erros:
        print("REPROVADO:")
        for e in erros:
            print("  %s" % e)
        sys.exit(1)
    print("plano valido: %d blocos, %d cortes" %
          (len(plano["corte"]["manter"]), len(plano["corte"]["removidos"])))


def densidade(plano):
    """A meta e um insert a cada 10s de video final. Nao e regra fechada: quando
    nao bater, PERGUNTAR se a pessoa quer que se procure insert num banco ou se
    segue assim. Nao decidir sozinho."""
    manter = plano["corte"]["manter"]
    fator = plano.get("velocidade", {}).get("fator", 1.0)
    final = sum(b[1] - b[0] for b in manter) / fator
    n = len(plano.get("inserts") or [])
    alvo = max(1, int(final / META_INSERT))
    return {"duracao_final": round(final, 2), "inserts": n, "meta": alvo,
            "bate": n >= alvo}


# fracao da altura, contada do TOPO, onde cada posicao do lettering cai.
# Espelha o 'fracao' do lettering.py.
FAIXA_LETTERING = {"meio": 0.50, "padrao": 0.624, "abaixo": 0.78}
FAIXA_ALTURA = 220          # altura da faixa medida, em pixel
CLARO_DEMAIS = 140          # luminancia media a partir da qual texto branco some


def fundo_claro_em(plano, posicao, t_original):
    """Luminancia media da faixa onde o lettering vai cair, ou None quando esta
    escura o bastante ou nao deu para medir. Mede no BRUTO, no timecode do
    original, que e onde o campo 'de' do lettering vive."""
    fonte = plano.get("fonte")
    if not fonte or not Path(fonte).exists():
        return None
    L, A = plano["meta"]["largura"], plano["meta"]["altura"]
    y = int(A * FAIXA_LETTERING.get(posicao, 0.624)) - FAIXA_ALTURA // 2
    y = max(0, min(A - FAIXA_ALTURA, y))
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", "%.3f" % max(0.0, t_original), "-i", str(fonte),
         "-frames:v", "1", "-vf", "crop=%d:%d:0:%d,format=gray" % (L, FAIXA_ALTURA, y),
         "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, stdin=subprocess.DEVNULL)
    d = r.stdout
    if len(d) < L * FAIXA_ALTURA:
        return None
    media = sum(d[:L * FAIXA_ALTURA]) / float(L * FAIXA_ALTURA)
    return int(media) if media >= CLARO_DEMAIS else None


PISCA = 1.5             # segundos de rosto entre dois inserts que nao valem o corte
MARGEM_TAPADA = 30      # folga em pixel antes de reclamar
AMOSTRAS_CONTEUDO = 5   # quantos instantes do insert medir


def base_do_conteudo(arq, dur):
    """Ultimo y com conteudo no insert, medindo varios instantes.

    O fundo e lido da PRIMEIRA LINHA do quadro, nao assumido preto: arte clara
    sobre fundo branco e tao comum quanto arte sobre fundo escuro, e um limiar
    fixo so acertaria metade dos casos."""
    w, h = 270, 480
    fundo_max = 0
    for k in range(AMOSTRAS_CONTEUDO):
        t = dur * (k + 1) / float(AMOSTRAS_CONTEUDO + 1) if dur > 0.2 else 0.0
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", str(arq),
                            "-frames:v", "1", "-vf", "format=gray,scale=%d:%d" % (w, h),
                            "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, stdin=subprocess.DEVNULL)
        d = r.stdout
        if len(d) < w * h:
            continue
        topo = sorted(d[:w])
        fundo = topo[len(topo) // 2]
        linhas = [y for y in range(h)
                  if max(abs(px - fundo) for px in d[y * w:(y + 1) * w]) > 25]
        if linhas:
            fundo_max = max(fundo_max, linhas[-1] * 1920 // h)
    return fundo_max or None


def duracao_de(caminho):
    """Duracao de um arquivo de midia, ou None se nao for possivel medir.
    Imagem parada volta 0 ou None, e quem chama trata como imagem."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(caminho)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def takes_de_rosto(plano):
    """Trechos em que o especialista aparece de frente para a camera, ou seja,
    o que sobra do video final depois de tirar as janelas de insert.

    Regra dela: take de rosto acima de 5s precisa de zoom, senao a imagem
    estagna. Insert nao recebe zoom."""
    manter = plano["corte"]["manter"]
    fator = plano.get("velocidade", {}).get("fator", 1.0)
    final = sum(b[1] - b[0] for b in manter) / fator

    def proj(t):
        acc = 0.0
        for a, b in manter:
            if t < a:
                return acc / fator
            if t <= b:
                return (acc + (t - a)) / fator
            acc += b - a
        return acc / fator

    ocupado = sorted((proj(i["de"]), proj(i["ate"])) for i in (plano.get("inserts") or []))
    takes, cursor = [], 0.0
    for a, b in ocupado:
        if a - cursor > 0.05:
            takes.append((round(cursor, 2), round(a, 2)))
        cursor = max(cursor, b)
    if final - cursor > 0.05:
        takes.append((round(cursor, 2), round(final, 2)))

    def desproj(tf):
        """Caminho de volta: tempo do video FINAL para timecode do ORIGINAL.

        Existe porque a etapa de zoom pede 'de' e 'ate' no timecode do original,
        enquanto os takes so podiam ser calculados no tempo final. Sem isto a
        conversao era feita na mao, take por take, e nenhuma trava pegava o erro:
        o zoom simplesmente caia no lugar errado."""
        restante = tf * fator
        for a, b in manter:
            if restante <= b - a:
                return round(a + restante, 3)
            restante -= b - a
        return round(manter[-1][1], 3) if manter else 0.0

    zooms = [(proj(z["de"]), proj(z["ate"])) for z in (plano.get("zoom") or [])]
    saida = []
    for a, b in takes:
        tem = any(za < b - 0.05 and zb > a + 0.05 for za, zb in zooms)
        saida.append({"de": a, "ate": b, "dur": round(b - a, 2), "tem_zoom": tem,
                      "de_orig": desproj(a), "ate_orig": desproj(b),
                      "precisa": (b - a) > TAKE_SEM_ZOOM and not tem})
    return saida


def nivel_dbfs(caminho, percentil=0.85):
    """Nivel de um audio em dBFS, no percentil pedido de janelas de 20ms.

    Serve tanto para a fala do video quanto para o efeito. Decodifica com o
    ffmpeg para wav 16k mono e mede em Python."""
    import array as _a, math as _m, subprocess as _s, wave as _w, tempfile, os
    tmp = tempfile.mktemp(suffix=".wav")
    r = _s.run(["ffmpeg", "-v", "error", "-y", "-i", str(caminho),
                "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp],
               capture_output=True)
    if r.returncode != 0 or not os.path.exists(tmp):
        return None
    try:
        w = _w.open(tmp, "rb")
        a = _a.array("h"); a.frombytes(w.readframes(w.getnframes())); w.close()
    finally:
        os.unlink(tmp)
    n = 320
    v = []
    for i in range(0, len(a) - n, n):
        s = sum(x * x for x in a[i:i + n]) / n
        v.append(20 * _m.log10(_m.sqrt(s) / 32768.0) if s > 0 else -99.0)
    if not v:
        return None
    v.sort()
    return round(v[int(len(v) * percentil)], 1)


def gerar_som(plano):
    """Monta a lista de efeitos a partir do que ja esta no plano: entrada e
    saida de cada insert, e cada zoom seco.

    Decisao dela: so o nivel automatico. Sem musica de fundo, sem impacto, sem
    riser. Nao ha o que julgar aqui, os tempos ja estao todos decididos."""
    efeitos = []
    for i in sorted(plano.get("inserts") or [], key=lambda x: x["de"]):
        if i["de"] > 0.15:   # insert que abre o video nao ganha whoosh no quadro 0
            efeitos.append({"em": round(i["de"], 3), "nome": SFX_INSERT,
                            "motivo": "entrada do insert %s" % i["formato"]})
        efeitos.append({"em": round(i["ate"], 3), "nome": SFX_INSERT,
                        "motivo": "saida do insert %s" % i["formato"]})
    for z in sorted(plano.get("zoom") or [], key=lambda x: x["de"]):
        if z["tipo"] == "seco":
            efeitos.append({"em": round(z["de"], 3), "nome": SFX_ZOOM,
                            "motivo": "zoom seco"})
    efeitos.sort(key=lambda e: e["em"])

    # dois efeitos colados soam como um borrao: fica o primeiro
    limpos, juntados = [], 0
    for e in efeitos:
        if limpos and e["em"] - limpos[-1]["em"] < JUNTOS:
            juntados += 1
            continue
        limpos.append(e)
    return limpos, juntados


def pico_do_efeito(caminho, passo=0.1):
    """Instante de maior energia dentro do arquivo, e onde o audivel acaba.

    **Nao confiar na descricao da biblioteca.** O manifesto diz que o riser tem
    'pico no fim' de 10s; medindo, ele cresce ate -8,2 dBFS aos 3,0s e de 5,5s
    em diante e silencio absoluto, ate -126 dBFS. Posicionar pelo que o
    manifesto diz jogava fora a subida inteira e mantinha so o rabo mudo."""
    import array as _a, math as _m, subprocess as _s, wave as _w, tempfile, os
    tmp = tempfile.mktemp(suffix=".wav")
    r = _s.run(["ffmpeg", "-v", "error", "-y", "-i", str(caminho),
                "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp],
               capture_output=True)
    if r.returncode != 0 or not os.path.exists(tmp):
        return None, None
    try:
        w = _w.open(tmp, "rb")
        a = _a.array("h"); a.frombytes(w.readframes(w.getnframes())); sr = w.getframerate(); w.close()
    finally:
        os.unlink(tmp)
    n = int(passo * sr)
    env = []
    for i in range(0, max(1, len(a) - n), n):
        s = sum(x * x for x in a[i:i + n]) / n
        env.append((i / sr, 20 * _m.log10(_m.sqrt(s) / 32768.0) if s > 0 else -99.0))
    if not env:
        return None, None
    pico_t, pico_db = max(env, key=lambda e: e[1])
    fim = pico_t
    for tt, db in env:
        if tt > pico_t and db > pico_db - 40:
            fim = tt
    return round(pico_t, 2), round(fim + passo, 2)


def riser_de_abertura(plano):
    """A subida vai sobre o PRIMEIRO TAKE do video, o da pessoa falando, e nao
    amarrada ao primeiro insert.

    Decisao dela, e a distincao importa: se um video so tiver insert la pelos 30
    segundos, ancorar no insert jogaria a subida para o meio do video. Ela e
    elemento de abertura e tem que existir de qualquer jeito.

    O pico cai no fim do primeiro take, que e o momento natural de virada. Se
    esse take for longo, o pico e limitado a RISER_JANELA para nao sair da
    abertura. Tudo em tempo do video FINAL, que e o que a pessoa assiste; o
    resultado volta para timecode do original, como o resto do plano."""
    takes = takes_de_rosto(plano)
    if not takes:
        return None, "o video nao tem take de rosto para a subida acompanhar"
    primeiro = takes[0]
    alvo_final = min(primeiro["ate"], RISER_JANELA)
    if alvo_final < 1.5:
        return None, ("o primeiro take dura so %.1fs; nao cabe subida audivel nele"
                      % primeiro["dur"])

    pico_t, _ = pico_do_efeito(BIBLIOTECA_SFX / (SFX_RISER + ".mp3"))
    if pico_t is None:
        return None, "nao consegui medir o pico do arquivo da subida"

    ini_final = alvo_final - pico_t
    corte = 0.0
    if ini_final < 0:
        corte = -ini_final
        ini_final = 0.0
    if pico_t - corte < 1.5:
        return None, ("o primeiro take dura %.1fs e sobraria menos de 1,5s de subida "
                      "audivel" % primeiro["dur"])

    # de volta ao timecode do original
    manter = plano["corte"]["manter"]
    fator = plano.get("velocidade", {}).get("fator", 1.0)
    restante, orig = ini_final * fator, manter[-1][1]
    for a, b in manter:
        if restante <= b - a:
            orig = a + restante
            break
        restante -= b - a

    return {"em": round(orig, 3), "nome": SFX_RISER, "origem_ini": round(corte, 3),
            "abaixo_da_voz": RISER_ABAIXO,
            "motivo": "subida sobre o primeiro take (%.1fs a %.1fs do final), pico em %.1fs"
                      % (primeiro["de"], primeiro["ate"], alvo_final)}, None


def cmd_lettering(args):
    plano, caminho = carregar(args.pasta)
    _, palavras, _ = ler_analise(args.pasta)
    spec = json.loads(Path(args.arquivo).expanduser().read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        sys.exit("o arquivo tem que ser um objeto, nao uma lista: e um lettering so")

    erros = []
    est = spec.get("estilo")
    if est not in ESTILOS_LETTERING:
        erros.append("estilo '%s' desconhecido. use: %s" % (est, ", ".join(ESTILOS_LETTERING)))
    linhas = spec.get("linhas") or []
    if not linhas or not all(isinstance(l, str) and l.strip() for l in linhas):
        erros.append("'linhas' tem que ser uma lista de textos nao vazios")
    if est == "destaque" and len(linhas) > 2:
        erros.append("o estilo destaque foi medido com duas linhas; %d nao cabe" % len(linhas))
    pos = spec.get("posicao", "padrao")
    if pos not in POSICOES_LETTERING:
        erros.append("posicao '%s' desconhecida. use: %s" % (pos, ", ".join(POSICOES_LETTERING)))
    el = spec.get("elemento")
    if el:
        cam = Path(el)
        if not cam.is_absolute():
            cam = Path(args.pasta).expanduser() / cam
        if not cam.exists():
            erros.append("elemento nao encontrado: %s" % cam)
        else:
            spec["elemento"] = str(cam.resolve())
    if est == "caixa" and el:
        erros.append("o estilo caixa nao leva elemento ao lado; use destaque")

    # A altura escolhida cai sobre alguma coisa. No estilo destaque a primeira
    # linha e BRANCA, e num fundo claro (camiseta, parede branca, ceu) ela some.
    # Aconteceu em video real na altura 'abaixo' e ninguem percebeu na hora.
    if not erros and est == "destaque":
        aviso = fundo_claro_em(plano, pos, float(spec.get("de", 0.0)))
        if aviso is not None:
            print("ATENCAO: na altura '%s' o fundo esta claro (luminancia %d de 255)."
                  % (pos, aviso))
            print("A primeira linha do estilo 'destaque' e branca e vai sumir ali.")
            print("Opcoes: trocar a posicao, ou passar \"cores\" no json, por")
            print("exemplo \"cores\": [\"1A1A1A\", \"0A84FF\"] para texto escuro.")
            print("")

    spec["de"] = float(spec.get("de", 0.0))
    spec["dur"] = float(spec.get("dur", LETTERING_DUR))
    if spec["dur"] <= 0.3:
        erros.append("duracao de %.2fs e curta demais para dar tempo de ler" % spec["dur"])

    if erros:
        print("RECUSADO, nada foi salvo:")
        for e in erros:
            print("  %s" % e)
        sys.exit(1)

    plano["lettering"] = spec
    salvar(plano, caminho)
    print("lettering '%s', %d linha(s), de %.2fs por %.2fs, posicao %s%s"
          % (est, len(linhas), spec["de"], spec["dur"], pos,
             ", com elemento" if el else ""))
    for l in linhas:
        print("  %s" % l)


def cmd_som(args):
    plano, caminho = carregar(args.pasta)
    _, palavras, _ = ler_analise(args.pasta)
    if not BIBLIOTECA_SFX.exists():
        sys.exit("biblioteca de efeitos nao encontrada em %s\n"
                 "ela vem dentro da skill, em assets/sfx." % BIBLIOTECA_SFX)

    efeitos, juntados = gerar_som(plano)
    if args.riser:
        r, porque = riser_de_abertura(plano)
        if r is None:
            print("SUBIDA DE ABERTURA NAO ENTROU: %s" % porque)
        else:
            efeitos = sorted([r] + efeitos, key=lambda e: e["em"])
    faltando = [e["nome"] for e in efeitos
                if not (BIBLIOTECA_SFX / (e["nome"] + ".mp3")).exists()]
    if faltando:
        sys.exit("efeito nao existe na biblioteca: %s" % ", ".join(sorted(set(faltando))))

    if not efeitos:
        print("nada a sonorizar: o plano nao tem insert nem zoom seco.")
        return

    # Volume fixo nao serve. A biblioteca sugere 0,35, o que assume material
    # gravado alto. No video de teste a fala vive em -37 dBFS e o whoosh a 0,35
    # media -26: onze dB ACIMA da voz, o que soa como susto. O nivel do efeito
    # passa a sair do nivel de fala do proprio video.
    voz = nivel_dbfs(Path(args.pasta).expanduser() / "analise" / "audio.wav")
    if voz is None:
        sys.exit("nao consegui medir o nivel da fala em analise/audio.wav")
    alvo = voz - ABAIXO_DA_VOZ
    for e in efeitos:
        arqe = BIBLIOTECA_SFX / (e["nome"] + ".mp3")
        bruto = nivel_dbfs(arqe, 0.995 if e["nome"] == SFX_RISER else 0.85)
        if bruto is None:
            sys.exit("nao consegui medir o efeito %s" % e["nome"])
        a = voz - float(e.get("abaixo_da_voz", ABAIXO_DA_VOZ))
        e["volume"] = round(min(1.0, 10 ** ((a - bruto) / 20.0)), 4)
        e["nivel_alvo"] = round(a, 1)

    plano["audio"] = {"efeitos": efeitos, "biblioteca": str(BIBLIOTECA_SFX),
                      "nivel_fala": voz, "abaixo_da_voz": ABAIXO_DA_VOZ}
    salvar(plano, caminho)

    manter = plano["corte"]["manter"]
    final = sum(b[1] - b[0] for b in manter) / plano["velocidade"]["fator"]
    print("%d efeitos em %.1fs de video final, um a cada %.1fs"
          % (len(efeitos), final, final / len(efeitos)))
    print("fala em %.1f dBFS, efeitos mirando %.1f dBFS (%.0f dB abaixo)"
          % (voz, alvo, ABAIXO_DA_VOZ))
    if juntados:
        print("%d efeito(s) caiam a menos de %.2fs de outro e foram fundidos"
              % (juntados, JUNTOS))

    # Inserts curtos em sequencia geram entrada e saida de cada um e o trecho
    # vira metralhadora. Tecnicamente correto e chato de ouvir. Esta regra vivia
    # so na referencia, entao passou batido em dois videos seguidos: agora o
    # proprio comando levanta a mao.
    tempos = sorted(e["em"] for e in efeitos)
    pior, inicio = 0, 0.0
    for k, x in enumerate(tempos):
        j = k
        while j + 1 < len(tempos) and tempos[j + 1] - x <= METRALHADORA_JANELA:
            j += 1
        if j - k + 1 > pior:
            pior, inicio = j - k + 1, x
    if pior >= METRALHADORA_EFEITOS:
        print("")
        print("ATENCAO: %d efeitos em %.0fs, a partir de %.2fs do original."
              % (pior, METRALHADORA_JANELA, inicio))
        print("Isso costuma soar metralhado. AVISE a pessoa e OFERECA deixar so")
        print("um efeito na entrada do primeiro insert e outro na saida do")
        print("ultimo. Nao mude sozinho: e gosto, nao defeito.")

    print("")
    for e in efeitos:
        print("  %7.3f  %-12s vol %.3f  %s" % (e["em"], e["nome"], e["volume"], e["motivo"]))


def cmd_zoom(args):
    plano, caminho = carregar(args.pasta)
    _, palavras, _ = ler_analise(args.pasta)
    dur = plano["meta"]["duracao"]
    novos = json.loads(Path(args.arquivo).expanduser().read_text(encoding="utf-8"))
    if not isinstance(novos, list):
        sys.exit("o arquivo tem que ser uma lista de objetos")

    erros = []
    for k, z in enumerate(novos):
        for campo in ("de", "ate", "tipo"):
            if campo not in z:
                erros.append("zoom %d sem campo '%s'" % (k, campo))
        if erros:
            continue
        z["de"], z["ate"] = float(z["de"]), float(z["ate"])
        z["z"] = float(z.get("z", ZOOM_PADRAO))
        if z["tipo"] not in TIPOS_ZOOM:
            erros.append("zoom %d: tipo '%s' desconhecido. use: %s"
                         % (k, z["tipo"], ", ".join(TIPOS_ZOOM)))
        if z["ate"] <= z["de"]:
            erros.append("zoom %d: 'ate' nao e maior que 'de'" % k)
        if z["de"] < 0 or z["ate"] > dur + 0.01:
            erros.append("zoom %d: %.2f-%.2f cai fora do video de %.2fs"
                         % (k, z["de"], z["ate"], dur))
        if not 1.01 <= z["z"] <= 1.5:
            erros.append("zoom %d: fator %.2f fora da faixa util (1.01 a 1.5)" % (k, z["z"]))
        for i in (plano.get("inserts") or []):
            if z["de"] < i["ate"] - 0.01 and z["ate"] > i["de"] + 0.01:
                erros.append("zoom %d (%.2f-%.2f) invade o insert %s (%.2f-%.2f). "
                             "insert nao recebe zoom."
                             % (k, z["de"], z["ate"], i["formato"], i["de"], i["ate"]))

    todos = sorted((plano.get("zoom") or []) + novos, key=lambda x: x["de"])
    for a, b in zip(todos, todos[1:]):
        if b["de"] < a["ate"] - 0.01:
            erros.append("dois zooms se sobrepoem: %.2f-%.2f e %.2f-%.2f"
                         % (a["de"], a["ate"], b["de"], b["ate"]))
    if erros:
        print("RECUSADO, nada foi salvo:")
        for e in erros:
            print("  %s" % e)
        sys.exit(1)

    plano["zoom"] = todos
    salvar(plano, caminho)
    print(resumo(plano, palavras))


def cmd_inserts(args):
    plano, caminho = carregar(args.pasta)
    _, palavras, _ = ler_analise(args.pasta)
    dur = plano["meta"]["duracao"]
    novos = json.loads(Path(args.arquivo).expanduser().read_text(encoding="utf-8"))
    if not isinstance(novos, list):
        sys.exit("o arquivo tem que ser uma lista de objetos")

    erros = []
    for k, i in enumerate(novos):
        for campo in ("de", "ate", "arquivo", "formato"):
            if campo not in i:
                erros.append("insert %d sem campo '%s'" % (k, campo))
        if erros:
            continue
        i["de"], i["ate"] = float(i["de"]), float(i["ate"])
        if i["formato"] not in FORMATOS:
            erros.append("insert %d: formato '%s' desconhecido. use um de: %s"
                         % (k, i["formato"], ", ".join(FORMATOS)))
        if i["ate"] <= i["de"]:
            erros.append("insert %d: 'ate' nao e maior que 'de'" % k)
        if i["de"] < 0 or i["ate"] > dur + 0.01:
            erros.append("insert %d: %.2f-%.2f cai fora do video, que tem %.2fs"
                         % (k, i["de"], i["ate"], dur))
        arq = Path(i["arquivo"])
        if not arq.is_absolute():
            arq = Path(args.pasta).expanduser() / arq
        if not arq.exists():
            erros.append("insert %d: arquivo nao encontrado: %s" % (k, arq))
        else:
            i["arquivo"] = str(arq)

    # O insert precisa cobrir a janela inteira. Se acabar antes, o overlay usa
    # eof_action=pass e a filmagem volta a aparecer no meio da janela, sem erro
    # e sem aviso: some do preview e ninguem entende por que. Imagem parada nao
    # entra na conta, o render segura ela com -loop.
    fator = plano.get("velocidade", {}).get("fator", 1.0)
    manter_v = plano["corte"]["manter"]

    def _proj(t):
        """Mesma projecao que o render usa para posicionar o insert. Usar
        (ate-de)/fator no lugar disto SUPERESTIMA o material necessario, porque
        ignora os silencios cortados DENTRO da janela: num take real de 11,4s
        com 4,1s de pausa cortada, a conta simples pedia 7,86s de arte quando o
        render consome 5,02s, e a trava recusava uma arte que servia."""
        acc = 0.0
        for a, b in manter_v:
            if t < a:
                return acc / fator
            if t <= b:
                return (acc + (t - a)) / fator
            acc += b - a
        return acc / fator

    for k, i in enumerate(novos):
        if erros or "arquivo" not in i:
            break
        d = duracao_de(i["arquivo"])
        if d is None or d <= 0.05:          # imagem parada
            continue
        precisa = _proj(i["ate"]) - _proj(i["de"])
        disponivel = d - float(i.get("origem_ini", 0.0))
        if disponivel < precisa - 0.05:
            erros.append(
                "insert %d (%s): a janela precisa de %.2fs de material e o "
                "arquivo so oferece %.2fs a partir de %.2fs.\n"
                "    encurte a janela, baixe o 'origem_ini' ou troque o arquivo."
                % (k, Path(i["arquivo"]).name, precisa, max(0.0, disponivel),
                   float(i.get("origem_ini", 0.0))))

    # Formato que cobre parte do quadro pode comer o que a arte existe para
    # dizer. Isso NAO e recusa: e pergunta. Ela decide entre trocar o formato e
    # subir a arte com 'subir'.
    tapados = []
    if not erros:
        import insert as fmt
        mt = Path(args.pasta).expanduser() / "analise" / "matte.mp4"
        sil = fmt.medir_silhueta(str(mt)) if mt.exists() else None
        for k, i in enumerate(novos):
            z = fmt.zona_tapada(i["formato"], sil, i.get("altura_pessoa"))
            if z is None:
                continue
            d = duracao_de(i["arquivo"])
            if d is None:
                continue
            base_c = base_do_conteudo(i["arquivo"], d)
            if base_c and base_c > z - MARGEM_TAPADA + int(i.get("subir", 0)):
                tapados.append((k, Path(i["arquivo"]).name, i["formato"], base_c, z,
                                base_c - (z - MARGEM_TAPADA) + int(i.get("subir", 0))))

    base = [] if args.substituir else (plano.get("inserts") or [])
    todos = sorted(base + novos, key=lambda x: x["de"])
    for a, b in zip(todos, todos[1:]):
        if b["de"] < a["ate"] - 0.01:
            erros.append("dois inserts se sobrepoem: %.2f-%.2f e %.2f-%.2f"
                         % (a["de"], a["ate"], b["de"], b["ate"]))
    if erros:
        print("RECUSADO, nada foi salvo:")
        for e in erros:
            print("  %s" % e)
        sys.exit(1)

    plano["inserts"] = todos
    salvar(plano, caminho)
    print(resumo(plano, palavras))

    # Voltar para o rosto por menos de PISCA segundos entre dois inserts nao le
    # como corte, le como falha. Decisao dela: GRUDAR um insert no outro nao tem
    # problema nenhum, e melhor do que enfiar meio segundo de rosto no meio.
    fator = plano.get("velocidade", {}).get("fator", 1.0)
    manter = plano["corte"]["manter"]

    def pfinal(x):
        acc = 0.0
        for a, b in manter:
            if x < a:
                return acc / fator
            if x <= b:
                return (acc + (x - a)) / fator
            acc += b - a
        return acc / fator

    piscadas = []
    for a, b in zip(todos, todos[1:]):
        vao = pfinal(b["de"]) - pfinal(a["ate"])
        if 0.02 < vao < PISCA:
            da = duracao_de(a["arquivo"]) or 0
            db = duracao_de(b["arquivo"]) or 0
            cabe_a = da * fator >= (b["de"] - a["de"]) - 0.05
            cabe_b = db * fator >= (b["ate"] - a["ate"]) - 0.05
            piscadas.append((Path(a["arquivo"]).name, Path(b["arquivo"]).name,
                             vao, cabe_a, cabe_b))
    if piscadas:
        print("")
        print("=" * 68)
        print("ATENCAO: o rosto volta por menos de %.1fs entre dois inserts." % PISCA)
        for na, nb, vao, ca, cb in piscadas:
            print("  %.2fs de rosto entre %s e %s" % (vao, na, nb))
            if ca:
                print("      da para esticar o '%s' ate a entrada do proximo." % na)
            elif cb:
                print("      o '%s' nao estica, mas da para puxar o '%s' para tras." % (na, nb))
            else:
                print("      nenhum dos dois arquivos e longo o bastante para fechar.")
        print("")
        print("GRUDAR UM INSERT NO OUTRO NAO E PROBLEMA. Meio segundo de rosto no")
        print("meio de dois inserts nao le como corte, le como falha.")
        print("=" * 68)

    if tapados:
        print("")
        print("=" * 68)
        print("ATENCAO: o formato cobre parte da arte nestes inserts.")
        for k, nome, f, bc, z, subir in tapados:
            print("  insert %d (%s, %s): a arte desce ate y=%d e o formato tapa"
                  % (k, nome, f, bc))
            print("      a partir de y=%d. Sobra tapado o que estiver nos ultimos"
                  % z)
            print("      %d pixels da arte." % (bc - z))
            print("      Para nao tapar: \"subir\": %d nesse insert." % subir)
        print("")
        print("PARE E PERGUNTE: trocar o formato, ou seguir subindo a arte?")
        print("Nao decida sozinho. O que fica tapado costuma ser o fecho da arte,")
        print("que e justamente o que ela existe para dizer.")
        print("=" * 68)


def cmd_resumo(args):
    plano, _ = carregar(args.pasta)
    _, palavras, _ = ler_analise(args.pasta)
    print(resumo(plano, palavras))


def main():
    ap = argparse.ArgumentParser(description="Estado da edicao de video")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("criar", help="monta o plano inicial cortando as pausas")
    c.add_argument("--recomecar", action="store_true",
                   help="joga fora insert, zoom, som e lettering ja montados e "
                        "recomeca o plano do zero")
    c.add_argument("--pasta", required=True)
    c.add_argument("--fonte", default=None, help="caminho do video original")
    c.add_argument("--respiro", type=float, default=RESPIRO)
    c.add_argument("--dramatica", type=float, default=PAUSA_DRAMATICA)
    c.add_argument("--velocidade", type=float, default=VELOCIDADE)
    c.set_defaults(func=cmd_criar)

    a = sub.add_parser("aplicar", help="junta as remocoes julgadas pelo agente")
    a.add_argument("--pasta", required=True)
    a.add_argument("--remocoes", required=True, help="json com lista de cortes")
    a.set_defaults(func=cmd_aplicar)

    r = sub.add_parser("restaurar", help="devolve um corte especifico")
    r.add_argument("--pasta", required=True)
    r.add_argument("--indice", type=int, required=True)
    r.set_defaults(func=cmd_restaurar)

    v = sub.add_parser("velocidade", help="muda o fator de velocidade")
    v.add_argument("--pasta", required=True)
    v.add_argument("--fator", type=float, required=True)
    v.set_defaults(func=cmd_velocidade)

    ef = sub.add_parser("efeito", help="efeito de imagem na filmagem base (ex.: pb)")
    ef.add_argument("--pasta", required=True)
    ef.add_argument("--tipo", help="um de: " + ", ".join(EFEITOS_VIDEO))
    ef.add_argument("--de", type=float, help="timecode do ORIGINAL")
    ef.add_argument("--ate", type=float, help="timecode do ORIGINAL")
    ef.add_argument("--motivo", default="")
    ef.add_argument("--limpar", action="store_true",
                    help="descarta os efeitos anteriores; sozinho, so apaga")
    ef.set_defaults(func=cmd_efeito)

    ap_ = sub.add_parser("aprovar", help="registra ate qual etapa a pessoa aprovou")
    ap_.add_argument("--pasta", required=True)
    ap_.add_argument("--etapa", required=True,
                     help="uma de: " + ", ".join(ETAPAS_APROVAVEIS))
    ap_.set_defaults(func=cmd_aprovar)

    d = sub.add_parser("validar", help="roda as regras de seguranca")
    d.add_argument("--pasta", required=True)
    d.set_defaults(func=cmd_validar)

    i = sub.add_parser("inserts", help="junta a lista de inserts ao plano")
    i.add_argument("--pasta", required=True)
    i.add_argument("--arquivo", required=True, help="json com lista de inserts")
    i.add_argument("--substituir", action="store_true",
                   help="troca a lista inteira em vez de acrescentar; use para ajuste")
    i.set_defaults(func=cmd_inserts)

    z = sub.add_parser("zoom", help="junta a lista de zooms ao plano")
    z.add_argument("--pasta", required=True)
    z.add_argument("--arquivo", required=True, help="json com lista de zooms")
    z.set_defaults(func=cmd_zoom)

    m = sub.add_parser("som", help="gera os efeitos sonoros a partir do plano")
    m.add_argument("--pasta", required=True)
    m.add_argument("--riser", action="store_true",
                   help="acrescenta a subida longa de abertura; opcao, nunca padrao")
    m.set_defaults(func=cmd_som)

    lt = sub.add_parser("lettering", help="define o lettering de abertura")
    lt.add_argument("--pasta", required=True)
    lt.add_argument("--arquivo", required=True, help="json com a especificacao")
    lt.set_defaults(func=cmd_lettering)

    s = sub.add_parser("resumo", help="relatorio legivel")
    s.add_argument("--pasta", required=True)
    s.set_defaults(func=cmd_resumo)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
