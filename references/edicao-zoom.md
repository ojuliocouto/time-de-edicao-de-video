# Zoom

O zoom existe para o vídeo não parecer parado quando não há insert. Ele é
sempre sobre a imagem da pessoa, nunca sobre insert.

## Regras

**Take de rosto com mais de 5 segundos precisa de zoom.** Take de rosto é o que
sobra do vídeo final depois de tirar as janelas de insert. Regra dela, e é
verificável: `plano.py resumo` lista todos os takes e marca os que passam de 5s
sem zoom.

**Insert não recebe zoom.** `plano.py zoom` recusa a lista inteira se algum zoom
invadir a janela de um insert. Além disso o render desenha o zoom antes do
insert, então o insert venceria mesmo se algo passasse.

**Intensidade: 12%.** Calibrado com ela vendo três estilos renderizados sobre
material real.

**Zoom liberado.** O zoom é livre na fase final: o
agente decide onde, sem pedir aprovação ponto a ponto, e lista no resumo do
montado (momento, tipo e motivo). Antes disso a lista ia para aprovação antes do
render; se ela voltar a pedir, volta a ser assim.

## Os três tipos, e quando usar cada um

O tipo é escolha do agente, momento a momento. Ela definiu assim.

| tipo | comportamento | quando usar |
|---|---|---|
| `seco` | pula para o zoom e volta, sem transição | número, preço, dado concreto |
| `suave` | entra e sai em 12 quadros | chamada para ação e fechamento |
| `lento` | cresce do início ao fim da janela | take longo sem nada acontecendo |

O `seco` combina com o jump cut aparecendo que ela escolheu na etapa 1: marca o
momento em vez de suavizar.

Prioridade dentro de cada take: número, preço e dado; frase de virada e CTA;
trecho longo sem nada acontecendo.

## Por que a imagem é ampliada 2x antes do zoom

O `zoompan` do ffmpeg calcula a janela de recorte em **pixel inteiro**, e por
isso a imagem treme durante o movimento.

Isso foi medido isolando o efeito: aplicando o zoom sobre um **quadro parado**,
qualquer diferença entre quadros só pode vir do zoom.

| entrada | irregularidade entre quadros |
|---|---|
| direto, 1x | 0,083 |
| ampliada 2x antes | 0,041 |
| ampliada 4x antes | 0,037 |

Ampliar 2x **corta o tremor pela metade**. Ampliar 4x quase não melhora mais e
quadruplica o custo, então 2x é o ponto de equilíbrio.

Sobre o material em movimento a medição não separa o tremor do zoom do movimento
da própria pessoa: os dois dão o mesmo número. Por isso o teste do quadro parado.

## Por que não é `crop` com expressão

Seria o caminho mais direto, mas o `crop` deste ffmpeg avalia `w` e `h` uma vez
só, no início; só `x` e `y` mudam por quadro. Uma janela que encolhe faria o
tamanho do quadro variar, e o codificador recusa. O `zoompan` existe exatamente
para isso.

## Formato no plano.json

```json
{ "de": 15.90, "ate": 23.10, "tipo": "lento", "z": 1.12,
  "motivo": "take de 9s sem insert; o lento evita a imagem estagnar" }
```

Tempos em timecode do **original**, como todo o resto do plano.
