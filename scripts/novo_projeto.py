#!/usr/bin/env python3
"""Monta a fabrica de inserts de um video, e cada insert novo dentro dela.

    # uma vez por video: estrutura, fontes, primitivas.js, estilo.md, base.css e o
    # modelo do PLANO.md na pasta do video (um nivel acima da fabrica), se faltar
    python novo_projeto.py <video>/fabrica --nome "meu anuncio"

    # um insert novo: init do HyperFrames com as tres flags, fontes, gsap,
    # base.css e primitivas copiados para dentro dele, AGENTS.md apagado
    python novo_projeto.py <video>/fabrica --insert 02-taste-skill

Nunca escreve por cima de estilo.md, PLANO.md, registro.md nem MANIFESTO.md
que ja existam. O --forcar antigo fazia isso e apagou o estilo e o plano
aprovados de um anuncio no meio da serie. Recomecar do zero de proposito
pede --recomecar.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import os
import shutil
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASTAS = ["banco", "inserts", "renders", "assets/fonts"]

ESTILO = """# estilo.md, {nome}

Estilo travado em ____ .

## Como foi escolhido

<!-- Uma das tres, e apague as outras duas:
     1. manual de marca que o cliente ja tinha, em <caminho>
     2. imagens de referencia que a pessoa mandou, em banco/referencias/
     3. escolha da skill. Nesse caso escreva a justificativa em UMA frase. -->

## Paleta

| Token | Valor | Papel |
| --- | --- | --- |
| `--fundo` | | fundo, sempre |
| `--tinta` | | texto principal |
| `--suave` | | apoio, legenda, rodape |
| `--acento` | | **um so** |
| `--painel` | | superficie de card |
| `--borda` | | contorno e linha morta |

## Tipografia

- **Anton** para palavra heroi. Entrelinha 1,12 a 1,16, tracking perto de zero.
- **Inter** para apoio. Peso 500 a 600, tracking aberto em caixa alta.

Trocar so se a marca exigir, e escrever o porque aqui.

## Layout

- Formato padrao: vertical 1080x1920, 30 fps.
- Margem de seguranca: 110 px de cada lado.
- Um assunto por tela.
- **Maximo de 6 elementos por quadro.** Conferir com `medir_quadro.py`.
- Uma ancora manda, o resto obedece.

## Movimento

Os numeros abaixo sao medidos, nao chutados. Metodo em `references/fabrica-numeros.md`.

- Desaceleracao forte no fim. O movimento nao termina, bate.
- Camera em **pernas encadeadas**, cada uma terminando antes da proxima comecar.
  Deriva lenta unica nao conta como movimento: foi medida e nao registra.
- **Stagger minimo de 3 frames** (0,10 s a 30 fps). Abaixo disso nao existe
  stagger: os elementos entram todos no mesmo quadro renderizado.
- **Deslocamento maximo por frame = o tamanho do proprio elemento** no eixo do
  movimento. Passou disso, as posicoes em quadros consecutivos nao se tocam e o
  olho ve dois objetos. Confortavel e metade.
- **Hold de leitura:** 13 caracteres por segundo, piso de 1 s. Segure o texto o
  tempo de ler, mas nunca congele o quadro para isso.
- **A tela nao morre:** movimento em pelo menos 55% da duracao, parada maxima de
  0,8 s. Conferir com `medir_ritmo.py` antes de dar por pronto.

## Tratamento

<!-- colagem, textura, recorte fotografico: usa ou nao usa, e por que -->

## Acabamento

<!-- Decisao obrigatoria: usa ou dispensa, e por que. Ver references/fabrica-acabamento.md

     Se USA, escreva os valores travados aqui:
       grao ....... grain-overlay, opacidade ____
       vinheta .... vignette, --vignette-color ____ , --vignette-size ____
       ordem ...... vinheta ABAIXO do conteudo, grao ACIMA (invertido, o check
                    reprova todo texto da composicao)

     Se DISPENSA, escreva o motivo. Interface de produto e print de tela pioram
     com grao: a peca existe pra parecer tela real, e o grao entrega que nao e. -->
"""

PLANO = """# Plano da serie, {nome}

Escrito ANTES da primeira arte. Mostrar a tabela e esperar aprovacao.
Formato e pisos em references/fabrica-plano.md.

| # | Janela | Trecho | Plano | Material | Dispositivo | Registro |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## Conferencia dos cinco pisos

Preencher com o numero real, nao com "ok".

- [ ] **corte** ....... ___ de ___ inserts tem troca de plano  (minimo: metade)
- [ ] **material real** ___ de ___ carregam coisa real         (minimo: um terco)
- [ ] **dispositivo** . nenhum repete em sequencia, nenhum passa de um terco
- [ ] **plano** ....... o tamanho de plano varia ao longo da serie
- [ ] **registro** .... existe ao menos uma virada

## Conjunto fechado de dispositivos deste projeto

<!-- Liste aqui os mecanismos que esta serie usa, e so use estes. Vocabulario
     fechado da familia; rotacao dentro dele da variedade. -->

## O que NAO vai virar insert

<!-- Trecho da fala que fica no rosto de proposito, e por que. -->
"""


REGISTRO = """# Registro de material

De onde veio cada arquivo do banco, e em que condicao de uso.

| Arquivo | Origem | Licenca / condicao | Usado em |
| --- | --- | --- | --- |
"""

MANIFESTO = """# Manifesto de inserts, {nome}

| Arquivo | Duracao | Trecho que cobre | Material usado |
| --- | --- | --- | --- |
"""


BASE_CSS = """/* tokens do estilo.md: preencha com a paleta e a fonte travadas */
@font-face { font-family: "Inter"; src: url("fonts/Inter-Variable.ttf") format("truetype"); font-weight: 100 900; }
@font-face { font-family: "Anton"; src: url("fonts/Anton-Regular.ttf") format("truetype"); }
:root {
  --fundo: #0b0b0b;
  --tinta: #ffffff;
  --cinza: #838383;   /* contraste minimo 3:1 no check */
  --acento: #F94E03;
}
"""


def copiar_fontes(fontes, destino_fontes):
    """Copia as fontes e devolve os nomes copiados."""
    os.makedirs(destino_fontes, exist_ok=True)
    nomes = []
    for f in sorted(os.listdir(fontes)):
        if f.endswith((".ttf", ".otf", ".woff2")):
            shutil.copy2(os.path.join(fontes, f), os.path.join(destino_fontes, f))
            nomes.append(f)
    return nomes


def main():
    ap = argparse.ArgumentParser(description="Monta a pasta de um projeto de inserts.")
    ap.add_argument("destino", help="caminho da pasta do projeto")
    ap.add_argument("--nome", default=None, help="nome legivel do projeto")
    ap.add_argument("--insert", default=None, help="cria um insert novo com este nome")
    ap.add_argument("--recomecar", action="store_true",
                    help="APAGA estilo.md, PLANO.md, registro.md e MANIFESTO.md e escreve em branco")
    ap.add_argument("--forcar", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.forcar:
        print("o --forcar nao existe mais: ele apagava o estilo.md e o PLANO.md aprovados.\n"
              "para criar um insert use --insert <nome>; para recomecar do zero, --recomecar.")
        return 2

    destino = os.path.abspath(os.path.expanduser(a.destino))
    nome = a.nome or os.path.basename(destino.rstrip("/"))

    fontes = os.path.join(SKILL, "assets", "fonts")
    primitivas = os.path.join(SKILL, "assets", "primitivas.js")
    for caminho, oque in ((fontes, "as fontes"), (primitivas, "o primitivas.js")):
        if not os.path.exists(caminho):
            print(f"erro: nao achei {oque} em {caminho}", file=sys.stderr)
            print("       a skill parece incompleta; rode o git pull no repo de skills.", file=sys.stderr)
            return 1

    for p in PASTAS:
        os.makedirs(os.path.join(destino, p), exist_ok=True)

    copiados = copiar_fontes(fontes, os.path.join(destino, "assets", "fonts"))
    if not os.path.exists(os.path.join(destino, "primitivas.js")):
        shutil.copy2(primitivas, os.path.join(destino, "primitivas.js"))
    os.makedirs(os.path.join(destino, "assets", "js"), exist_ok=True)
    shutil.copy2(os.path.join(SKILL, "assets", "gsap.min.js"), os.path.join(destino, "assets", "js", "gsap.min.js"))

    if a.insert:
        return novo_insert(destino, a.insert, fontes)

    # As fontes precisam existir em DOIS niveis. O @font-face de cada insert
    # resolve relativo ao index.html dele, nao a raiz do projeto. Sem a segunda
    # copia a fonte nao carrega e o render sai com a substituta, silenciosamente.
    inserts = os.path.join(destino, "inserts")
    ja_existentes = [
        d for d in sorted(os.listdir(inserts))
        if os.path.isdir(os.path.join(inserts, d))
    ] if os.path.isdir(inserts) else []
    for d in ja_existentes:
        copiar_fontes(fontes, os.path.join(inserts, d, "assets", "fonts"))

    escritos, pulados = [], []
    for arquivo, conteudo in (
        ("estilo.md", ESTILO.format(nome=nome)),
        (os.path.join("..", "PLANO.md"), PLANO.format(nome=nome)),
        ("base.css", BASE_CSS),
        (os.path.join("banco", "registro.md"), REGISTRO),
        ("MANIFESTO.md", MANIFESTO.format(nome=nome)),
    ):
        alvo = os.path.join(destino, arquivo)
        if os.path.exists(alvo) and not a.recomecar:
            pulados.append(arquivo)
            continue
        with open(alvo, "w", encoding="utf-8") as fh:
            fh.write(conteudo)
        escritos.append(arquivo)

    print(f"projeto em {destino}")
    print(f"  pastas ....... {', '.join(PASTAS)}")
    print(f"  fontes ....... {', '.join(copiados) if copiados else 'NENHUMA'}")
    if ja_existentes:
        print(f"  fontes tambem em inserts/: {', '.join(ja_existentes)}")
    print("  primitivas ... primitivas.js")
    print(f"  escritos ..... {', '.join(escritos) if escritos else 'nenhum'}")
    if pulados:
        print(f"  preservados .. {', '.join(pulados)}  (ja existiam; nada foi apagado)")
    print()
    print("proximo passo: preencher o estilo.md, depois o PLANO.md.")
    print("             a primeira arte so comeca com o PLANO.md aprovado.")
    print()
    print("Cada insert: python novo_projeto.py <fabrica> --insert <nome>")
    return 0


def novo_insert(destino, nome, fontes):
    """init do HyperFrames com as tres flags que nao sao opcionais:
    --non-interactive (senao pergunta e trava o agente), HYPERFRAMES_SKIP_SKILLS=1
    (senao bate no GitHub a cada init) e --resolution portrait (senao sai deitado).
    Depois copia para DENTRO do insert o que o @font-face e o <script> procuram
    relativo ao index.html dele: sem a segunda copia a fonte troca no render sem
    aviso."""
    pasta = os.path.join(destino, "inserts", nome)
    if os.path.exists(os.path.join(pasta, "index.html")):
        print(f"o insert {nome} ja existe: nada foi tocado ({pasta})")
        return 0
    env = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1")
    r = comum.rodar(["npx", "--yes", "hyperframes", "init", os.path.join("inserts", nome), "-e", "blank",
                     "--resolution", "portrait", "--non-interactive"], checar=False, cwd=destino, env=env)
    if r.returncode != 0 or not os.path.exists(os.path.join(pasta, "index.html")):
        print("o init do HyperFrames falhou:\n" + (r.stderr or r.stdout or "")[-1200:], file=sys.stderr)
        return 1
    copiar_fontes(fontes, os.path.join(pasta, "assets", "fonts"))
    os.makedirs(os.path.join(pasta, "assets", "js"), exist_ok=True)
    os.makedirs(os.path.join(pasta, "assets", "midia"), exist_ok=True)
    shutil.copy2(os.path.join(SKILL, "assets", "gsap.min.js"), os.path.join(pasta, "assets", "js", "gsap.min.js"))
    for extra in ("base.css", "primitivas.js"):
        if os.path.exists(os.path.join(destino, extra)):
            shutil.copy2(os.path.join(destino, extra), os.path.join(pasta, "assets", extra))
    for extra in ("AGENTS.md", "CLAUDE.md"):   # regras do init brigam com as da skill
        if os.path.exists(os.path.join(pasta, extra)):
            os.remove(os.path.join(pasta, extra))
    idx = os.path.join(pasta, "index.html")
    html = open(idx, encoding="utf-8").read()
    import re
    html = re.sub(r'<script src="https?://[^"]*gsap[^"]*"></script>', '<script src="assets/js/gsap.min.js"></script>', html)
    html = html.replace('<html lang="en"', '<html lang="pt-BR"')
    if "window.__timelines" not in html and "</body>" in html:
        html = html.replace("</body>", "<script>window.__timelines = window.__timelines || {};</script>\n</body>", 1)
    open(idx, "w", encoding="utf-8").write(html)
    print(f"insert {nome} pronto em {pasta}")
    print("  fontes, gsap.min.js e (se houver) base.css e primitivas.js em assets/")
    print("  midia do insert vai em assets/midia/; registre a origem em banco/registro.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
