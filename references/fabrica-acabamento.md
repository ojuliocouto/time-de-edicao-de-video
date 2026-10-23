# Acabamento

O passo que faltava. Sem ele o insert fica tecnicamente correto e **parece print
de página web**, não peça de vídeo.

A ideia vem do guia MOTION VOX STYLE: "nada é vetor limpo". Cada peça ganha
sombra de contato, a tipografia ganha textura, o quadro inteiro leva grão fino e
uma vinheta suave. É esse acabamento que faz a arte parecer fotografada em cima
de uma mesa em vez de montada numa tela.

O incômodo: **as peças já eram nossas.** Estão no catálogo do HyperFrames desde
sempre e a skill nunca mandou ninguém procurá-las, porque a lista de pronto
terminava em "o check passou".

## As peças

```bash
npx hyperframes add grain-overlay
npx hyperframes add vignette
```

Outras que servem, dependendo do estilo do projeto:

| Peça | Para |
| --- | --- |
| `grain-overlay` | grão de filme animado sobre tudo |
| `vignette` | escurecimento suave das bordas |
| `freeze-frame-dressing` | papel, fita e recorte, para colagem |
| `organic-light-leak-overlay` | vazamento de luz, memória, transição motivada |
| `ink-bleed-reveal` | tinta abrindo no papel |
| `yt-lcd-background` | fundo de papel texturizado com grade |
| `halftone-dissolve` | transição por retícula de jornal |

## A ordem das camadas, que não é óbvia

**A vinheta vai ABAIXO do conteúdo. O grão vai ACIMA.**

Isso não é gosto, é o que faz o `check` passar. Testado:

- vinheta acima do conteúdo → `text_occluded` em **todos** os textos da
  composição, porque a vinheta é um elemento opaco cobrindo texto
- vinheta abaixo do conteúdo, grão acima → **0 erros**

O grão não dispara oclusão porque é textura semitransparente. A vinheta dispara
porque o gradiente chega a alfa alta na borda.

```css
#hf-vignette { z-index: 1; }    /* abaixo */
#mundo       { z-index: 2; }    /* o conteudo */
#grain-overlay { z-index: 100; } /* acima */
```

### Não tente resolver com atributo de exceção

Testei os dois no oclusor e **nenhum funciona**: `data-layout-ignore` e
`data-layout-allow-occlusion` no `#hf-vignette` não silenciam nada, porque a
regra dispara no **texto**, não no oclusor. O waiver sancionado é
`data-layout-allow-occlusion` em cada elemento de texto, o que desliga a checagem
de oclusão da composição inteira. Não vale a pena: mude a ordem das camadas.

## Os padrões do componente são para composição escura

O `vignette` vem com `--vignette-color: rgba(0, 0, 0, 0.7)` e
`--vignette-size: 45%`. Num fundo claro isso **não é acabamento, é um halo**:
medido, o canto do quadro foi de `#f4f2ee` para `#5c5d5b`.

Trave os três no CSS, e não no exemplo de timeline:

```css
#hf-vignette {
  --vignette-color: rgba(24, 20, 12, 0.16);   /* fundo claro */
  --vignette-size: 62%;
  --vignette-shape: ellipse;
}
```

Com esses valores o canto vai para `#d1d1cb`, que é presença sem halo.

### A armadilha que me pegou: o tween vem comentado

O snippet do `vignette` traz um bloco chamado "Timeline integration example"
**dentro de um comentário HTML**. Ele não roda. Se você editar os valores ali
achando que está mexendo na peça, não muda nada, e a vinheta continua no padrão
escuro. Eu editei o comentário duas vezes antes de perceber.

## A vinheta briga com a câmera

Vinheta escurece a borda. Câmera que aproxima empurra o texto **para** a borda.
Junte os dois e um texto que passava no contraste no começo reprova no fim.

Medido: um kicker em `#6b6558` passou em t=0 e caiu para 2,79:1 em t=4,3s,
conforme a câmera avançava. Corrigido escurecendo para `#4f4a3f`.

**Confira o contraste no fim do movimento de câmera, não só no começo.**

## O grão custa arquivo

Mesma composição, 6 s, qualidade alta:

| | tamanho |
| --- | --- |
| sem grão | 1,6 MB |
| com grão | 11,5 MB |

Sete vezes. Ruído é caro de comprimir. Não é problema para um insert de poucos
segundos, mas conte com isso antes de rodar uma bateria.

## O grão engana o verificador de ritmo

O `grain-overlay` anima por `@keyframes` de CSS em relógio de parede, não pela
timeline. Consequência: **muda pixel em todo quadro**, e infla a medida de
movimento. A mesma composição deu 83% com grão e 59% sem.

O `scripts/medir_ritmo.py` já borra o quadro antes de comparar exatamente por
isso, e com o borrão as duas medições coincidem. **Não rode a medição de ritmo
com `--borrao 0` numa peça com grão.**

Segunda consequência: como é relógio de parede, o grão **não é determinístico**
entre renders. Dois renders da mesma composição têm grão diferente. Para o grão
tanto faz, mas não use `@keyframes` de CSS para nada que precise bater.

## Quando não usar

Acabamento é decisão de `estilo.md`, não obrigação. Interface de produto,
dashboard e print de tela **pioram** com grão: a peça inteira existe para parecer
uma tela real, e grão em cima entrega que não é.

Escreva no `estilo.md` se o projeto usa acabamento e qual.
