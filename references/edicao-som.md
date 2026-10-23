# Sonorização

**Padrão atual:** nos criativos, whoosh em toda entrada de insert e
batida de fundo bem baixa são o padrão (pedido em todos os anúncios da série de origem).
A batida é do `scripts/batida.py`, separada deste nível automático. Continua
fora: impacto grave, riser sem pedido e efeito ilustrando o conteúdo do insert.

**O nível automático** é o que o `plano.py som` faz: whoosh na entrada e na
saída de cada insert, click em cada zoom seco. Rode depois do zoom: o comando
tira uma foto do plano, e o que entrar depois fica sem som.

## O que entra

| onde | efeito | por quê |
|---|---|---|
| entrada de cada insert | `whoosh-short` (0,57s) | marca a troca de imagem |
| saída de cada insert | `whoosh-short` | marca a volta |
| cada zoom `seco` | `click-soft` (0,37s) | acompanha o impacto do zoom |

Zoom `suave` e `lento` não recebem efeito: eles não têm um instante de impacto.

**Nada a julgar aqui.** Os tempos já estão todos no `plano.json`, então a lista
é gerada, não decidida:

```bash
python3 scripts/plano.py som --pasta "<pasta>"
```

## Densidade

No material de teste deu **8 efeitos em 45s, um a cada 5,6 segundos**. É a
faixa que faz parecer edição cuidada sem virar barulho.

Para comparação, o que foi descartado: efeito em todo corte seco daria 21
efeitos no mesmo vídeo, um a cada 2 segundos.

Dois efeitos a menos de 0,15s um do outro viram um só, senão soam como borrão.

## A biblioteca

`assets/sfx/` desta skill: whoosh, whoosh-short, click, click-soft, pop e
riser, copiados da biblioteca da `media-use` (Pixabay, uso comercial livre,
créditos em `assets/sfx/CREDITS.md`). **Local, offline e sem custo**, nos três
sistemas.

Disponíveis: `whoosh`, `whoosh-short`, `whoosh-cinematic`, `click`,
`click-soft`, `pop`, `ping`, `chime`, `notification`, `sparkle`, `typing`,
`key-press`, `riser` (10s), `impact-bass-1`, `impact-bass-2`, `error`,
`glitch-1/2/3`.

## O volume NÃO é fixo

A biblioteca sugere volume 0,35, e isso **está errado para material gravado
baixo**. Medido no vídeo de teste: a fala vive em -36,9 dBFS e o whoosh a 0,35
media **-26 dBFS, onze dB ACIMA da voz**. Soaria como susto.

O nível passa a sair do próprio vídeo:

```
alvo   = nivel_de_fala - 6 dB
volume = 10 ^ ((alvo - nivel_do_efeito) / 20)
```

O nível de fala é o percentil 85 de janelas de 20ms de `analise/audio.wav`. No
material de teste isso baixou o whoosh de 0,35 para **0,052**, quase sete vezes.
Verificado depois de renderizar: o efeito mede -42,8 contra fala em -36,9, ou
seja, 5,9 dB abaixo.

**Limite conhecido:** para efeito muito curto, como o `click-soft` de 0,37s, a
medição do percentil 85 superestima o nível do arquivo e o ganho aplicado
subestima. Ele sai uns 6 dB mais baixo que o alvo. Para um click discreto isso
não incomoda, mas se um dia um efeito curto sumir na mixagem, é aqui.

## Subida de abertura (opcional, e só opcional)

```bash
python3 scripts/plano.py som --pasta "<pasta>" --riser
```

Acrescenta a subida longa no começo do vídeo. **Nunca padrão.** Decisão dela:
funciona justamente porque é rara; usada sempre, perde o efeito.

**Ela vai sobre o PRIMEIRO TAKE do vídeo, não amarrada ao primeiro insert.**
Decisão dela, e a distinção importa: num vídeo cujo primeiro insert só apareça
aos 30 segundos, ancorar no insert jogaria a subida para o meio do vídeo. Ela é
elemento de abertura e tem que existir de qualquer jeito.

O posicionamento é **de trás para frente**: o pico do arquivo cai no fim do
primeiro take, que é o momento natural de virada. Se o take for longo, o pico é
limitado a **12 segundos do vídeo final** para não sair da abertura. Se isso
jogaria o início antes do zero, a subida entra cortada pelo campo `origem_ini`.

Não entra quando o primeiro take é curto demais para caber 1,5s de subida
audível, e o comando explica por quê em vez de falhar calado.

Toda a conta é feita no tempo **final**, que é o que a pessoa assiste, e o
resultado volta para timecode do original, como o resto do plano.

**Verificado no material de teste:** primeiro take de 0 a 4,4s, a subida entra
em 1,26s e cresce de inaudível até **-39,6 dBFS no pico em 4,4s**, que é a
troca. A voz vive em -36,9, então o pico fica 3 dB abaixo dela.

### Não confiar na descrição da biblioteca

O manifesto descreve o `riser` como "10s de build, pico no fim". **O arquivo
não é isso.** Medindo o envelope:

| tempo | nível |
|---|---|
| 0,0s | -80 dBFS |
| 1,5s | -31 |
| 3,0s | **-8,2, o pico** |
| 4,5s | -58 |
| 5,5s em diante | silêncio, até -126 |

O conteúdo audível dura 4,5s e o pico fica no começo. Posicionando pelo que o
manifesto dizia, a subida inteira era cortada fora e sobrava só o rabo mudo: o
efeito media -74 dBFS e simplesmente não se ouvia.

Por isso o pico é **medido no arquivo**, por `pico_do_efeito()`, e não lido do
manifesto. Depois da correção o envelope cresce de nada até -41,6 dBFS no pico,
5 dB abaixo da voz.

O nível dela também sai de outro lugar: o percentil 99,5 em vez do 85, porque
metade do arquivo é silêncio e o percentil 85 puxa a medida para baixo. E ela
mira 4 dB abaixo da voz, não 6, porque é contínua e precisa ser ouvida durante
o build.

## Na mixagem

Cada efeito vira uma trilha atrasada com `adelay` até o seu instante e entra num
`amix`.

**`normalize=0` é essencial.** Sem isso o `amix` divide o volume de todas as
trilhas pelo número de entradas, e a voz afundaria a cada efeito.


## Quando o riser NÃO cabe

O riser precisa de um primeiro take longo o bastante para a subida acontecer.
Num teste real o primeiro take de rosto durava **1,63s** antes do insert entrar,
e a subida ficaria espremida a ponto de virar um estalo. Nesse caso o certo é
não usar e dizer por quê, não encurtar a subida.

## Insert curto em sequência vira metralhadora

Três inserts de imagem seguidos, ocupando 5s no total, geram **cinco efeitos**
nesse trecho: entrada e saída de cada um, menos os que a fusão de 0,15s junta.
Tecnicamente correto e chato de ouvir. Quando acontecer, **avisar e oferecer**
deixar um único whoosh na entrada do primeiro e outro na saída do último. Não
mudar sozinho: é gosto, não defeito.
