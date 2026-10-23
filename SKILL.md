---
name: time-de-edicao-de-video
description: "Time de edição de vídeo de ponta a ponta: da filmagem bruta (ou de dois vídeos emendados) ao criativo pronto e legendado. Corte seco e 1,3x, plano de inserts aprovado, inserts fabricados por subagentes em paralelo, montagem com whoosh, zoom e batida, legenda cinematográfica com palavra atrás da pessoa e entrega no Drive, com portão de aprovação entre as etapas. Mac, Windows e Linux."
triggers:
  - time de edição de vídeo
  - time de edicao de video
  - editar esse vídeo
  - editar criativo
  - editar anúncio
  - edição completa do vídeo
  - /time-de-edicao-de-video
category: workflow
version: 1.0.0
---

# Time de edição de vídeo

## Quando usar

Vídeo gravado em câmera (ou o avatar de quem fala) que precisa virar criativo
pronto: corte, inserts, som, legenda e entrega. **Não serve** para vídeo feito
do zero em HTML ou animação (isso é `hyperframes`).

Só um pedaço? A etapa 0 sempre roda; depois, entre direto:

| Pedido | Entrada mínima | Etapas |
|---|---|---|
| só cortar e acelerar | o bruto | 0, 1 e 7 |
| só fabricar inserts | o vídeo final (copie para `base/final-sem-insert.mp4`) e o `fabrica/janelas.json` | 3 e 4 |
| só legendar | o vídeo pronto, sem legenda queimada, em 1080x1920 (copie para `legenda/montado.mp4`) | 6 e 7 |

Uma skill só para o processo inteiro que antes passava por três: `editar-video`
(corte, inserts, zoom, som), `fabrica-de-insert` (as artes) e
`cinematic-caption` (a legenda). Tudo que elas faziam está aqui, mais o que foi
reinventado dentro de cada projeto e virou ferramenta.

O processo abaixo foi aprovado com "ficou perfeito" numa série de anúncios
reais, do primeiro ao último. **Siga na ordem. Não pule portão.**

## Antes de tudo

1. **Sempre em português**, inclusive aviso de render e mensagem curta. Resposta
   em inglês já gerou reclamação duas vezes no mesmo dia.
2. **Comandos:** variável de shell não sobrevive entre uma chamada e outra, então
   todo comando da skill começa com este prefixo, que acha a skill e escolhe o
   Python (`python` no Windows, onde `python3` pode abrir a Microsoft Store):
   `TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python;` (funciona no Mac, no Linux e no Git Bash do Windows).
3. **Pré-flight**, uma vez por sessão: `TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/preflight.py`.
   Faltou item obrigatório: mostre a lista com o comando de cada um, peça
   aprovação, instale um por vez (`references/instalacao.md`) e rode de novo.
4. **Pasta do vídeo:** uma pasta própria por vídeo (ex.: `~/Videos/meu-anuncio/`).
   Reaproveite a do cliente se existir; cliente incerto, pergunte. Nada de
   material dentro de `~/.claude/skills/`.
5. **Leia `references/licoes.md` antes do primeiro vídeo da sessão.**
   É o mapeamento do que foi aprovado, do que foi reprovado e por quê.
6. **Mandar arquivo para a pessoa:** `SendUserFile` quando existir; sem ele, o
   caminho absoluto do arquivo na mensagem.

## O time

| Quem | Faz | Onde está |
|---|---|---|
| Você (orquestrador) | conversa com a pessoa, decide, monta, confere, entrega | este arquivo |
| Estações (manuais de cada etapa) | o passo a passo e os comandos de cada etapa | `estacoes/` |
| Fabricante de insert (subagente) | constrói 2 a 4 inserts, em paralelo com os outros | `agentes/fabricante-de-insert.md` |
| Conferente de corte (subagente) | confere cada corte de fala por transcrição isolada | `agentes/conferente-de-corte.md` |
| Revisor final (subagente) | assiste ao montado como a pessoa assistiria e acha o que ela acharia | `agentes/revisor-final.md` |

Você nunca manda para a pessoa nada que um subagente produziu sem olhar antes.
O subagente não fala com ela.

## O processo

```
0 Preparo ─▶ 1 Corte e 1,3x ─▶ [P1] ─▶ 2 Plano de inserts ─▶ [P2] ─▶ 3 Pilotos ─▶ [P3]
  ─▶ 4 Fabricação ─▶ [P4] ─▶ 5 Montagem (zoom, whoosh, batida) ─▶ [P5] ─▶ 6 Legenda ─▶ [P6] ─▶ 7 Entrega
```

`[Pn]` é portão: **para, manda, espera o "aprovado".** A pessoa pode encurtar
("pode montar o plano e já fazer em sequência sem minha aprovação"): aí você
segue, e registra cada decisão que ela teria tomado em `DECISOES.md` na pasta.
Ela também pode pedir o contrário: "faça 2 inserts primeiro e só siga com o meu
ok". O que veio no pedido vale mais do que o padrão abaixo.

### Etapa 0. Preparo → `estacoes/0-preparo.md`

Bruto, roteiro e objetivo do vídeo. **Todo bruto passa pelo
`montar_bruto.py`**, mesmo um vídeo só: sai em 1080x1920 (o render recusa outra
resolução) e com a voz em -24 LUFS por ganho fixo, **sem denoise**. Se o anúncio
nasce de dois vídeos (o corpo de um com o CTA de outro), o mesmo script
emenda os trechos, com vídeo **e** imagem do CTA. Os tempos que a pessoa passa
vêm de transcrição que deriva: confira cada ponto de emenda antes.

### Etapa 1. Corte e 1,3x → `estacoes/1-corte.md`

`analisar.py` → `plano.py criar` (pausa acima de 0,15 s sai, 1,3x uniforme) →
você julga gagueira, começo falso e retomada (`references/edicao-corte.md`) →
**cada corte de fala conferido por transcrição isolada e pelos silêncios**
(subagente conferente) → render → `verificar.py` + `auditar.py` → transcrição
do preview para provar que nenhuma palavra sumiu.

**[P1]** Manda o preview com o resumo (quanto encolheu, cada corte de fala e o
motivo, o que o `auditar.py` mandou avisar). Pergunta se já há pedidos de
insert, referências de estética e material. Costumam chegar logo depois do
"aprovado o corte".

### Etapa 2. Plano de inserts → `estacoes/2-plano-de-inserts.md`

`PLANO.md` + `fabrica/janelas.json` (a fonte única das janelas, em tempo do
vídeo final). Os pedidos da pessoa entram como ela escreveu; o resto você
propõe. Antes de propor: onde quem fala aponta ("esse cara aqui"), onde desenha
ou risca na tela (proteger), o que já vem queimado no arquivo (cobrir).

**[P2]** Mande o plano **escrito na mensagem** (tabela curta + decisões em
aberto numeradas), para a resposta vir como "1. ok, 2. troca por...". Nada é
produzido antes do "aprovado".

### Etapa 3. Estilo e pilotos → `estacoes/3-estilo-e-pilotos.md`

`estilo.md` trava só paleta, tipografia e acento. Fundo, efeito e mecanismo
variam a cada insert. Leia as referências de verdade (vídeo de referência,
folha de contato). Faça **2 pilotos**, mande cada um com a voz do trecho.

**[P3]** A pessoa aprova a estética nos pilotos. Reprovou ("não gostei da
estética")? Refaz os pilotos, não a série.

### Etapa 4. Fabricação → `estacoes/4-fabricacao.md`

`preparar_fabrica.py` (base, filmagem por insert, partituras) → `BRIEF-AGENTES.md`
→ **4 a 6 fabricantes em paralelo**, 2 a 4 inserts cada. Você confere cada render
(folha de contato, `medir_ritmo.py`, acentos) e manda **cada insert separado**,
com a voz, na ordem do vídeo: a frase do trecho e o vídeo embaixo. A pessoa
conta os inserts pela ordem em que recebeu.

**[P4]** A pessoa aprova os inserts ("Aprovados, pode montar") ou pede mudança
pelo número ("o insert 2 em 0:03..."). Nada entra no vídeo antes do ok.

### Etapa 5. Montagem → `estacoes/5-montagem.md`

`montar_lista.py` → máscara, se algum formato pede recorte → `plano.py inserts`
→ zoom nos takes de rosto acima de 5 s (liberado: você decide onde, sem pedir
ponto a ponto) → whoosh em toda entrada de insert (`plano.py som`, sempre
**depois** do zoom e de novo a cada mudança de insert ou zoom) → **um** render
em resolução cheia (o 720p sai dele; a legenda usa o mesmo) →
batida bem baixa com virada na hora da oportunidade (`batida.py`) →
`verificar.py` + `auditar.py` + emendas olhadas quadro a quadro → revisor final.

**[P5]** Manda o montado (720p no chat). Ajuste é no plano e re-render, nunca
refazendo análise.

### Etapa 6. Legenda → `estacoes/6-legenda.md`

Sobre o mesmo montado em resolução cheia do portão 5, sem render novo.
Modo trilho, motor `gerar_legenda.py` + `montar_legenda.py`. Legenda no vídeo
**inteiro, inclusive nos inserts**, menos onde a arte já escreve a fala ou não
há espaço. Palavras atrás da cabeça de quem fala (pedido de todas as vezes) com
recorte da pessoa. Folha de contato e preview antes do final.

**[P6]** Manda o legendado em 720p. Iteração de texto, posição e herói é barata.

### Etapa 7. Entrega → `estacoes/7-entrega.md`

Só depois do "aprovado". `entrega.py` confere e gera a versão leve; o Drive só
na pasta que A PESSOA indicar, com o nome no padrão da pasta
(`ADxx-tema-LEGENDADO.mp4`), tamanho conferido igual ao local. Informe
resolução, fps, duração e tamanho.

## Regras que não se negociam

Cada uma custou uma reprovação real. Origem em `references/licoes.md`.

**Corte e áudio**
1. Nenhum corte de fala sai sem transcrição **isolada** do trecho e borda
   conferida contra `silencios.json`. A transcrição longa alucinou começos
   falsos, comeu frases e derivou de 0,5 s a 9 s em 6 dos 14 vídeos.
2. Palavra curta esticada (mais de 0,9 s) é retomada fundida. Escute.
3. Vício de linguagem ("tipo", "né", "então") **fica**. Retomada: fica a última
   tentativa completa, salvo pedido da pessoa.
4. **Nunca denoise, nunca compressor.** Voz em -24 LUFS por ganho fixo, feito
   na etapa 0 pelo `montar_bruto.py`.
5. Tempo que a pessoa fala ("em 1:09") é do vídeo final: converta com `tempo.py`.

**Inserts**
6. Nada é produzido antes do PLANO aprovado (salvo ordem explícita da pessoa).
7. Abertura: o gancho inteiro na tela antes de 1 s e **a tela nunca para**.
   Sem slam tipográfico (palavras gigantes batendo, flash, glitch): reprovado.
8. Fala que cita algo real pede **material real**: print, página, gravação,
   post. Grafismo genérico ali foi "animação barata". Post de terceiro, usuário
   oculto; ou fictício, quando a pessoa pedir.
9. Quando quem fala aponta e diz "esse cara aqui", o insert mostra exatamente aquilo.
10. Rosto do apresentador dentro de arte: trecho em movimento, de preferência
    sorrindo. **Nunca quadro congelado, nunca olho arregalado.**
11. Informação que cabe no tempo de tela. Muito texto: versão reduzida ou mais tempo.
12. Rosto voltando por menos de 1 s entre dois inserts parece falha: encoste.
13. Não cobrir o que quem fala desenha ou risca na tela, nem o momento que a
    pessoa quer ver.
14. Série variada: mesma paleta, fundo e mecanismo diferentes. Nem todos no
    mesmo formato (nem todos divididos). Moldura arredondada é a preferida para
    vídeo e arte explicativa; tela cheia para texto de impacto.
15. Print sem efeito exagerado: "só pega os prints e joga na tela", com tempo
    para escanear. Tire data que envelhece (cabeçalho de três anos atrás).
16. Nunca inventar número, preço ou data. Número só com fonte.

**Legenda**
17. Nunca karaokê palavra a palavra, nunca placa ou véu de largura total.
18. Legenda segue a fala palavra por palavra e traz a ideia completa. Sigla
    nunca sozinha na segunda linha. Vocabulário da campanha (`estilo.md`).
19. Legenda não fica em cima da arte: acima ou abaixo da janela do insert, e
    nunca na boca de quem fala.

**Operação**
20. Todo preview passa por `verificar.py` e `auditar.py` antes de ir para a
    pessoa. O que o `auditar.py` aponta como defeito do bruto: **avisar, não
    consertar**.
21a. **Comando que espera resposta trava o agente para sempre.** Numa validação
    um fabricante ficou 1h44 parado num comando que pedia confirmação. Em
    todo comando que você mesmo escrever:
    - `ffmpeg -nostdin` sempre (sem isso o ffmpeg lê o teclado e para);
    - nunca `rm pasta/*` (o zsh do Mac pergunta "tem certeza?"): use
      `find pasta -type f -delete` ou `rm -rf pasta && mkdir pasta`;
    - laço com qualquer programa: termine com `< /dev/null`;
    - toda chamada do Bash com `timeout` explícito: 120000 para comando comum,
      600000 só para render, máscara e transcrição. Passou do tempo, é sinal de
      travado: mate e descubra o porquê, não espere.
21. Comando longo: até 10 min, em primeiro plano com `timeout: 600000`. Render
    do montado e máscara longa passam disso: `run_in_background: true` na
    chamada do Bash e espere a notificação (nunca `nohup` nem `&`, que o
    HyperFrames cancela quando a chamada termina). Se a sessão cair, refaça o
    render: ele parte do plano e é sempre refazível.
22. Nunca criar pasta no Drive. Pergunte a pasta; destino já fixado pela pessoa
    para aquela série vale.
23. Ajuste é no `plano.json` e re-render. Nunca editar `corte.manter` à mão,
    nunca rodar `plano.py criar` de novo numa pasta que avançou, nunca empilhar
    render sobre render.

## Quando algo dá errado

Se falhar, não improvise fora da skill: rode o `preflight.py` e siga o
troubleshooting da etapa. Recusa de um script **não se contorna**: cada trava é um jeito conhecido de
estragar o vídeo, e a mensagem diz qual. Sintomas e saídas:
`references/edicao-problemas.md` (corte, render, máscara),
`references/fabrica-armadilhas.md` (HyperFrames, fontes, verificador),
`references/legenda-hyperframes-commands.md` (camadas, alfa, recorte).

| Sintoma | Saída |
|---|---|
| sessão caiu no meio da fabricação | `MANIFESTO.md` diz o que já está pronto; retome dali, não refaça |
| render de camada cancelado sem erro | estava em segundo plano: rode em primeiro plano |
| máscara com menos quadros que o vídeo | `mascara.py` já roda em blocos; se ainda acontecer, `--janelas` menores |
| "sparse keyframes" e vídeo congelado no insert | mídia sem keyframe: `-g 30 -keyint_min 30` (o `preparar_fabrica.py` já faz) |
| fonte trocada sozinha no render | "Helvetica Neue" no CSS sai em Inter: declare `@font-face` com arquivo local |
| "HDR image decode failed" | PNG tirado de vídeo HDR: remarque bt709 ou use JPG |
| página em branco no print | página feita em JS: `capturar_pagina.py` sem `--rapido` |
| recorte da pessoa lento (Windows, Linux) | é o remove-background do HyperFrames: `--janelas` só com os trechos usados |

## Arquivos da skill

`scripts/`: todos em Python, rodam nos três sistemas (`comum.py` concentra o
que muda entre eles). `assets/`: fontes Anton e Inter, `gsap.min.js`,
`primitivas.js`, `cenas/` e os efeitos sonoros. `references/`: as referências
das três skills de origem (prefixo `edicao-`, `fabrica-`, `legenda-`), mais
`licoes.md` e `instalacao.md`. `tests/`: `python3 $TEV/tests/rodar.py`
depois de qualquer mudança na skill.
