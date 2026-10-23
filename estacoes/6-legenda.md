# Etapa 6. Legenda cinematográfica (até o portão 6)

Todo comando começa com o prefixo abaixo, que acha a skill e escolhe o Python
(`python3` no Mac e no Linux, `python` no Windows, onde `python3` pode abrir a
Microsoft Store):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python;
```

A legenda vem por último porque preserva a edição que recebe e não mexe nela.
O que foi aprovado nos anúncios que deram origem à skill é sempre o **modo
trilho**: a legenda numa faixa fixa embaixo, com hierarquia de peso e escala
dentro dela, e saídas pontuais para a palavra grande atrás da cabeça de quem fala.

Leia antes do primeiro vídeo: `references/legenda-regras.md` (o modo trilho, o
mapa de planos, o teste de aptidão do recorte, as proibições),
`references/legenda-style-system.md` (inteiro),
`references/legenda-hyperframes-commands.md` e, com mais de três herois,
`references/legenda-dynamic-layout-recipes.md`.

## 6.1 Base e transcrição

A base é o montado aprovado no portão 5, já em resolução cheia (as camadas da
legenda são 1080x1920 e o `composite_overlay.py` recusa outro tamanho). Nada de
render novo aqui:

```bash
mkdir -p "<pasta>/legenda" "<pasta>/final" && cp "<pasta>/previews/montado.mp4" "<pasta>/legenda/montado.mp4"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/transcrever.py "<pasta>/legenda/montado.mp4" --json "<pasta>/legenda/palavras.json"
```

A transcrição é do montado, nunca remapeada do bruto.

**Rascunho das legendas**, com as frases já cortadas nas pausas, na pontuação e
em até 34 caracteres, sem os trechos onde a arte escreve a fala (`--sem`, no
tempo do vídeo; tire as janelas do `fabrica/janelas.json`):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/cues_de_palavras.py --pasta "<pasta>/legenda" --sem 0-5.02,46.6-95.7 --corrigir "Cloud=Claude"
```

Ele escreve as cues no `legenda.json` (cria ou troca só a lista de cues). O
julgamento continua seu: ênfase, zona por insert, heróis e recortes.

Só legendar um vídeo pronto (sem as etapas anteriores): copie o vídeo para
`<pasta>/legenda/montado.mp4` (1080x1920, sem legenda queimada) e siga daqui.

## 6.2 O mapa de planos (o que legendar)

Para cada trecho do vídeo, um `shot` no `legenda.json`, e cada insert numa de
três classes:

| classe | o que fazer |
|---|---|
| a arte **escreve a fala** | sem legenda (seria redundante) |
| a arte **tem espaço livre** | legenda só no que a arte não escreve, acima ou abaixo da janela da arte (em cima costuma ficar melhor), nunca por cima dela |
| **sem espaço** | sem legenda, motivo anotado em `sem_legenda` |

Regras que vieram de pedidos repetidos:
- **legendar o vídeo inteiro, inclusive os inserts**, menos as duas exceções acima;
- gravação de tela também leva legenda, por cima da tela, no meio, maior;
- no vazado (a pessoa embaixo, arte em cima), o trilho cai no rosto: suba a legenda
  para a faixa entre a arte e a cabeça, ou para o alto;
- inserts de fundo claro: tinta escura (`"tinta": "escura"`);
- abertura com texto fixo: sem legenda por cima;
- onde quem fala desenha no peito (um número, uma seta do CTA): legenda entre o queixo e o
  desenho.

Faixa livre de cada insert: meça na folha de contato do montado, não chute.

## 6.3 Texto

- Segue a fala **palavra por palavra**. O pedido reescreveu uma frase e
  divergiu do áudio ("100 vídeos" x "conteúdos")? Pergunte; num caso real, a
  escolha foi o áudio.
- A legenda traz a ideia completa ("qualquer trabalho operacional pode ser
  automatizado", não só "qualquer trabalho").
- Até ~34 caracteres por legenda a 62 px; mais que isso quebra linha: divida.
- Sigla nunca sozinha na segunda linha ("TIMES DE / I.A." ficou feio).
- Grafia e vocabulário da campanha (`fabrica/estilo.md`); nome errado na
  transcrição ("Cloud", "IA") corrigido em `correcoes`.
- `**palavra**` marca o passo de peso (Inter 800) dentro do trilho.
- Lettering em Anton (`"enfase": "letter"`) nos momentos de impacto curto ("VAMOS NESSA!").

## 6.4 Heróis atrás da cabeça

Pedido de todo vídeo: "faça também aquelas legendas que a palavra vai atrás
dele". Escolha pela nota de herói da `references/legenda-style-system.md`
(importância, prova, ênfase falada, legibilidade) e anote o motivo. Uns 7 por
minuto de fala no trilho; em criativo de 2 min ficaram entre 4 e 6.

- herói em Anton, caixa alta, preenchimento `vidro` (padrão), `solido` ou
  `acento` (a cor da marca, numa palavra de virada como "BOA NOTÍCIA");
- **atrás da cabeça é o padrão**: nos anúncios aprovados os heróis passaram atrás
  de quem fala mesmo com o cabelo cacheado e a parede escura. Só vai para a frente se,
  no quadro ampliado, o recorte não seguir o contorno real (borda reta, mancha,
  cabeça "inflada") ou se o cabelo esconder letras a ponto de não ler; aí
  primeiro suba ou diminua a palavra, e só então ponha na frente;
- **quem decide é o quadro ampliado, não o número do `matte_fitness.py`.** Com a
  Vision (Mac), ele reprova por contraste cabelo escuro em fundo escuro mesmo
  com a borda certa (aconteceu em 5 anúncios aprovados). Com o remove-background
  (Windows e Linux), leve o número a sério: ali a borda costuma inflar;
- palavra e posição: perto da cabeça, cruzando cabelo e contorno (10 a 22% de
  sobreposição), **nunca o rosto nem a boca**.

Cada herói com profundidade ganha um recorte com folga de ~0,2 s antes e depois
da palavra (`recortes` no `legenda.json`).

## 6.5 legenda.json

Formato completo no topo de `scripts/gerar_legenda.py`. Os números aprovados:
trilho com base em y = 1590; zona do peito com base em ~1180; topo em ~230;
apoio Inter 62 px peso 500 com passo 800; âncora 72 px peso 600. Pediu peso
maior ("Inter 800 na legenda toda")? `"estilo": {"apoio_peso": 800}`.

Peças sob medida (carimbo na cor da marca na abertura, tela escurecendo atrás
do recorte numa palavra de impacto) entram em `extra` (css, html de trás, html da frente,
tweens).

## 6.6 Gerar, conferir, montar

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/gerar_legenda.py --pasta "<pasta>/legenda"
cd "<pasta>/legenda" && npx --yes hyperframes snapshot --at 5,12,30
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/montar_legenda.py --pasta "<pasta>/legenda" --recortes --saida "<pasta>/final/<NOME>-legendado.mp4"
```

- O `gerar_legenda.py` recusa cue mal formada e avisa frase longa e sigla solta.
- `hyperframes check` em peça longa estoura o prazo: vale o snapshot.
- Recorte: no Mac é a Vision sobre o próprio montado. O `matte_fitness.py`
  reprova cabelo escuro em parede escura por contraste, mas a borda segue o
  cabelo: confira com `snapshot --zoom` no herói, não pelo número.
- Fora do Mac, o `--recortes` usa o remove-background (~1 quadro por segundo):
  5 heróis de ~1,6 s levam uns 4 min. Diga o tempo antes.
- O `montar_legenda.py` renderiza as camadas de trás e da frente com alfa e
  compõe com os recortes no tempo. É o único caminho que termina em peça longa
  com profundidade. Sai também a versão 720p.

Folha de contato do legendado para julgar ritmo (nunca defeito: miniatura
esconde a natureza da borda):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/folha_de_contato.py "<pasta>/final/<NOME>-legendado.mp4" -o "<pasta>/legenda/folha-legenda.png" --quadros 24
```

## 6.7 Portão 6

Mande o 720p com a nota curta: quais palavras viraram herói e por quê, onde a
legenda sobe nos inserts, o que ficou sem legenda e por quê. Texto, cor,
posição e herói são ajustes baratos: mude o `legenda.json` e rode o
`montar_legenda.py` de novo (sem `--recortes` se os recortes não mudaram).
