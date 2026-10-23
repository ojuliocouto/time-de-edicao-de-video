# Lettering

Headline fixa nos primeiros segundos. **Etapa opcional e última na ordem:** só
entra se a pessoa pedir, ou se aceitar quando perguntado ao fim da sonorização.

**Quem escreve o texto é ela.** A skill não propõe headline. Quando ela quiser
lettering, ela manda o texto e escolhe o estilo no cardápio abaixo.

## Por que o texto não é desenhado pelo ffmpeg

Muita build do ffmpeg (a do Mac dela, por exemplo) vem **sem `libfreetype` e
sem `libass`**, então o filtro `drawtext` nem existe. O lettering é desenhado
em `scripts/lettering.py`, com Pillow, e sai igual no Mac, no Windows e no
Linux. A fonte é a Arial Bold (Liberation Sans no Linux, mesmas medidas); sem
nenhuma das duas, a Inter da skill em peso 700. O `drawtext` também não serviria:
não faz contorno decente, não controla espaçamento entre letras e não quebra
linha sozinho.

## Sequência de quadros, não imagem única

O lettering é gerado como **sequência de PNG transparentes**, um por quadro, e o
ffmpeg só sobrepõe.

Isso é obrigatório, não preferência: as animações medidas nas referências mudam
o **tamanho** do lettering ao longo do tempo, e o ffmpeg não redimensiona ao
longo do tempo. É a mesma limitação que apareceu no zoom.

Custo medido: 105 quadros para 3,5s, gerados em 2,5 segundos, ocupando 6 MB
temporários em `analise/lettering/`.

## Regras comuns aos dois estilos

**Duração: 3,5 segundos fixos.** Decisão dela. Não é a duração de cada
referência, que era 2,7s numa e 4,7s na outra.

**Três alturas**, iguais nos dois estilos, pelo centro do bloco:

| posição | altura do centro | quando |
|---|---|---|
| `meio` | 50% | quando o rosto não está no meio |
| `padrao` | 62,4% no `caixa`, 54% no `destaque` | o que as referências usam |
| `abaixo` | 78% | **quando o texto tamparia o rosto** |

A posição `abaixo` é a mais importante na prática: nas três alturas altas o
texto encobria o rosto da pessoa no material de teste.

## Estilo `caixa`

Texto sobre caixa de cantos arredondados.

**Referência:** post de `wendellcarvalho`, lettering de 0 a 2,65s.

**Medições:** caixa de 1016 x 216 num quadro de 1080, ou seja, 32 de margem de
cada lado, centralizada. Cantos de raio 40. Fundo branco puro (255,255,255) e
texto preto puro (0,0,0), confirmados por amostragem. Duas linhas com 45px de
altura de maiúscula, espaçadas em 84, o que dá corpo de fonte 63.

**A largura da caixa é fixa**, não acompanha o texto: na referência o texto era
bem mais estreito que a caixa.

**Cor do fundo e do texto são trocáveis** (`cor_fundo`, `cor_texto`), como ela
pediu. O padrão é o tradicional preto sobre branco.

**Animação:** entra pronta, sem movimento. **Sai encolhendo em direção ao
centro** em 0,13s. Medido na referência: fica parada até 2,62s e a largura cai
1014 → 840 → 584 → some. Verificado no render: 1012 → 960 → 448 → 0.

Este estilo **não leva elemento ao lado**; o comando recusa se vier um.

## Estilo `destaque`

Texto com brilho, alinhado à esquerda, com um elemento opcional ao lado.

**Referência:** reel de `nicholas.puru`, lettering de 0 a ~4,7s.

**Medições:** duas linhas, a primeira branca (250,250,254) e a segunda ciano
(105,226,254). Altura de maiúscula 61 e 57px, espaçamento 74, corpo ~84.
Elemento quadrado de 143x142 à direita, com folga de 25px, e **o conjunto de
texto mais elemento centralizado no quadro**: o centro do bloco deu 539,5
contra 540 do quadro.

**Aceita qualquer número de linhas.** A referência tinha duas, mas isso é do
exemplo e não do estilo. A **última** linha sai na cor de destaque e as
anteriores na cor principal; `cores` permite definir linha a linha.

**O corpo da fonte encolhe sozinho** até o conjunto caber em 940px de largura.
Com o texto do teste, em português e mais longo que o da referência, ele caiu de
84 para 54.

**O elemento acompanha a altura do bloco de texto.** Com três linhas o bloco
fica mais alto e o elemento cresce junto. Se incomodar, é limitar aqui.

**Animação:** **entra deslizando 46px da esquerda em 0,9s, desacelerando.**
Medido na referência: x vai de 56 a 102 e assenta. A primeira análise mediu só a
**largura** e concluiu que era estático, porque deslocamento não muda largura.
Movimento se mede pela posição.

**Sai deslizando para a direita com desvanecimento em 0,25s. Este é o único
parâmetro ASSUMIDO**, adotado simétrico ao de entrada; não foi medido na
referência.

## Formato no plano.json

```json
"lettering": {
  "estilo": "caixa",
  "linhas": ["E se você sumisse", "durante 6 meses?"],
  "posicao": "abaixo",
  "de": 0.0,
  "dur": 3.5,
  "cor_fundo": "FFFFFF",
  "cor_texto": "000000",
  "elemento": "elemento.png"
}
```

### O elemento quase sempre é um emoji

`elemento` espera um **arquivo**, mas o pedido natural da pessoa é "coloca um
💩 do lado". O `emoji.py` baixa uma vez o desenho do Noto Emoji (Google, Apache
2.0) e guarda no cache da skill, igual nos três sistemas:

```bash
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/emoji.py "💩" 420 "<pasta>/elemento.png"
```

Sai um PNG com fundo transparente, **aparado na tinta do desenho**. Isso não é
detalhe: o lettering desenha o elemento na altura do bloco de texto, então
qualquer transparência sobrando em volta vira encolhimento do emoji.

A primeira versão media com `NSAttributedString.size()`, que devolve a caixa da
linha da fonte e não a tinta. A caixa do elemento saía do tamanho certo, mas o
desenho ocupava só parte dela, então o emoji aparecia pequeno dentro do próprio
espaço. Aparar recuperou cerca de **20% de tinta visível** no mesmo bloco de
109px, medido em vídeo real. A versão atual desenha grande, varre o alfa
procurando o menor retângulo com pixel visível e reescala a partir dali.

O lado pedido é o do maior eixo; o outro sai proporcional. 420px atende com
folga, já que o elemento é redimensionado de novo na composição.

`de` em timecode do original, como todo o resto. Um lettering por vídeo, então
o campo é um objeto e não uma lista.

`plano.py lettering` recusa estilo desconhecido, posição desconhecida, linhas
vazias, elemento inexistente, elemento no estilo `caixa` e duração curta demais
para dar tempo de ler.


## Contraste: a altura certa depende do que está atrás

As três alturas foram pensadas para não tapar o rosto, mas isso é só metade da
escolha. No estilo `destaque` a **primeira linha é branca**, e num fundo claro
ela some. Em vídeo real, na altura `abaixo`, o fundo era a camiseta clara do
apresentador: a luminância média da faixa deu **189 de 255** e a primeira linha
ficou quase invisível. Ninguém percebeu na entrega.

O `plano.py lettering` agora mede a faixa no bruto, no timecode do lettering, e
avisa acima de 140. O aviso não impede nada: ou se troca a posição, ou se passa
cor escura no campo `cores`, que o estilo `destaque` aceita:

```json
{ "estilo": "destaque", "linhas": ["o Claude é", "péssimo para imagens"],
  "posicao": "abaixo", "cores": ["1A1A1A", "0A84FF"] }
```

A última cor da lista é sempre a da última linha, a de destaque.
