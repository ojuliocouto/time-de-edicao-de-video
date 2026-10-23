# Formatos de insert

Cada formato é uma receita fechada: geometria, tratamento de áudio e
transição. Todos compartilham os mesmos campos no `plano.json` e todos têm
tempo ancorado no vídeo original.

Este arquivo é construído um formato por vez, a partir de vídeo de referência
medido em pixel, não descrito de memória.

## De onde vêm os arquivos de apoio

Três modos, definidos pela pessoa. **Um mesmo vídeo mistura formatos
diferentes**, então cada insert traz o seu.

**1. Roteiro pontuado (o mais comum).** Ela manda o script já marcando onde
entra cada insert, qual o formato de cada um e o link do arquivo. Aqui não há
decisão a tomar: é transcrever para `lista-inserts.json` e aplicar.

**2. Arquivos com formato sugerido.** Ela manda vários links, dizendo o formato
de cada um, e **o agente decide em que momento cada um entra**. A decisão sai da
transcrição: onde a fala pede apoio visual, onde há trecho longo sem respiro,
onde mostrar economiza explicação.

**3. Banco de inserts (raro).** Ela manda o link de um banco e o agente procura
lá dentro o que serve.

**Meta de densidade: pelo menos um insert a cada 10 segundos de vídeo final.**
Não é regra fechada, é alvo. `plano.py resumo` confere sozinho. Quando não
bater, **perguntar** se ela quer que se procure insert num banco específico ou
se segue assim. Não decidir sozinho.

Os arquivos chegam como **link**, então baixar é parte do trabalho. Baixar
arquivo pede autorização dela antes.

---

## Campos comuns a todo insert

```json
{ "de": 12.40, "ate": 18.90,
  "arquivo": "inserts/tela-do-claude.mp4",
  "formato": "tela_cheia",
  "origem_ini": 0.0,
  "motivo": "ela fala do painel; mostrar a tela evita explicar por palavra" }
```

| Campo | O que é |
|---|---|
| `de`, `ate` | quando o insert aparece, em timecode do **original** |
| `arquivo` | caminho do vídeo ou imagem de apoio |
| `formato` | qual receita abaixo aplicar |
| `origem_ini` | de que ponto do arquivo de insert começar a tocar |
| `motivo` | por que este insert existe; aparece no portão de aprovação |

**Regra de áudio, válida para todos até segunda ordem:** o arquivo de insert
entra **sempre mudo**. Só o áudio original continua tocando. Decisão explícita
da pessoa.

**Regra de transição, válida para todos até segunda ordem:** corte seco na
entrada e na saída, sem fade e sem animação. Medido no material de referência
e coerente com o jump cut assumido na etapa 1.

---

## 1. `tela_cheia`

O insert substitui a imagem inteira. A pessoa some da tela e só a voz dela
continua.

**Referência:** reel de `nicholas.puru`, insert entrando em 2,10s.

**Medições feitas no arquivo:**

- Ocupa os 1080x1920 inteiros. A coluna de pixels da borda esquerda tem cor
  constante em toda a altura e **não é preta**, o que descarta tarja, moldura
  e margem.
- Entrada em corte seco. O brilho médio do quadro cai de 128 para 33 entre
  2,00s e 2,10s, ou seja, em três quadros no máximo. Uma transição deixaria
  valores intermediários; não deixou nenhum.
- Sem borda, sem canto arredondado, sem sombra.

**Geometria:** ocupa tudo. Não há o que posicionar.

**Fonte esperada:** arquivo já vertical 9:16. Este formato **não** foi pensado
para print de computador deitado nem foto quadrada; para esses existe outro
formato. Se o arquivo chegar com proporção muito diferente de 9:16, avisar a
pessoa e propor o outro formato em vez de forçar o enquadramento.

**Receita ffmpeg:**

```
[1:v]scale=1080:1920:force_original_aspect_ratio=increase,
     crop=1080:1920,setpts=PTS-STARTPTS+DE/TB[ins];
[base][ins]overlay=enable='between(t,DE,ATE)'[saida]
```

`force_original_aspect_ratio=increase` seguido de `crop` absorve diferença
pequena de proporção sem deformar a imagem. Diferença grande é recusada antes,
pela regra da fonte esperada.

**Áudio:** o arquivo de insert não é mapeado. Nada a fazer.

---

## 2. `moldura`  (a moldura arredondada)

O insert aparece dentro de uma caixa de cantos arredondados, centralizada,
sobre fundo preto chapado. A imagem original some.

**Referência:** reel de `thevibefounder`, moldura em 2,0s, fonte horizontal.

**Medições feitas no arquivo:**

- Caixa de 1003x763 num quadro de 1080x1920. Largura = 92,9% do quadro, com
  39px de margem de cada lado. Centro exatamente em x=540.
- Proporção da caixa: 1,315. Ou seja, a caixa **segue a proporção da fonte**;
  ela não tem forma própria.
- Raio do canto: **84px**. Medido pelo recuo da borda esquerda linha a linha
  ao longo do arco (recuo 48 em dy=8, 28 em dy=20, 7 em dy=44, zero em dy=76)
  e ajustado à curva de um arco.
- **Sem borda.** A passagem do preto para o conteúdo acontece em 3 a 4 pixels,
  que é só antisserrilhado. Um contorno deixaria um anel de valores altos.
- **Fundo preto puro.** Cinco pontos fora da moldura deram 0,0,0 exato. Vídeo
  comprimido nunca dá preto exato em área grande, então é cor chapada.

**Geometria:** a caixa é a fonte encaixada dentro de uma área de
**1003 x 1498** (92,9% da largura por 78% da altura), preservando proporção,
centralizada no quadro.

Essa regra única cobre as duas orientações, e é o que a pessoa pediu ao notar
que a moldura muda conforme a fonte:

| Fonte | Caixa resultante | Quem limita |
|---|---|---|
| 4:3 horizontal | 1003 x 752 | a largura |
| 16:9 horizontal | 1003 x 564 | a largura |
| 1:1 quadrada | 1003 x 1003 | a largura |
| 9:16 vertical | 842 x 1498 | a altura |

Sem a trava de altura, um insert 9:16 viraria uma caixa de 1783px de altura,
quase a tela inteira, e a moldura deixaria de existir.

**Receita ffmpeg:**

```
[insert]scale=1003:1498:force_original_aspect_ratio=decrease,
        scale=trunc(iw/2)*2:trunc(ih/2)*2,format=rgba,
        geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':
            a='clip(255*(84-sqrt(pow(max(max(84-X,X-(W-1-84)),0),2)
                              +pow(max(max(84-Y,Y-(H-1-84)),0),2))+0.5),0,255)'[cx];
[preto][cx]overlay=(W-w)/2:(H-h)/2
```

`force_original_aspect_ratio=decrease` é o que implementa a tabela acima sem
nenhum condicional: encaixa dentro da área e deixa a proporção escolher quem
limita.

O `geq` desenha o canto arredondado na transparência, porque o ffmpeg não tem
filtro de canto arredondado. O `+0.5` dentro do `clip` cria um pixel de
antisserrilhado na curva; sem ele o canto sai serrilhado.

O fundo é `color=black:s=1080x1920`, não a imagem original.

**Verificação:** o render de teste reproduziu a referência com precisão. Recuo
do canto medido no render contra medido na referência: 48 contra 48, 29 contra
28, 10 contra 7, zero contra zero. Largura 1003 exata nos dois.

**Transição, medida neste reel (não assumida da regra geral):** corte seco na
entrada e na saída. A moldura aparece entre 0,97s e 1,00s, um quadro a 30 fps,
e some do mesmo jeito: em 2,10s a caixa tem 381px de altura e no quadro
seguinte já tem 960, que é tela cheia. Nenhum tamanho intermediário em nenhuma
das duas pontas, e o tamanho da caixa fica constante enquanto ela está no ar.
Portanto **sem animação de escala**.

**Áudio:** insert mudo, como todos.

**Assumido, não medido:** o raio de 84px vale também para a variante vertical.
A referência só mostra o caso horizontal. Risco baixo: raio constante é o que
mantém a identidade visual entre um insert e outro.

---

## 3. `dividida_foco_original`

Tela dividida na horizontal: insert numa faixa menor em cima, filmagem
original numa faixa maior embaixo. As duas preenchem a largura inteira.

**Referência:** reel de `wendellcarvalho`, formato no ar de 0:00 a 0:07.

**Medições feitas no arquivo:**

- **Costura em y=717**, constante em t=2,0s, t=5,0s e t=6,5s.
  Achada pelos valores crus de duas colunas nas pontas do quadro: na coluna 60
  as linhas 690 a 716 têm valor constante 81,83,87 e a linha 717 salta para
  113,117,121, chegando a 143,147,151 na 718. A coluna 1020 salta nas mesmas
  linhas.
- Faixa de cima 1080x717 (37,3% da altura), faixa de baixo 1080x1203 (62,7%).
- **Sem moldura, sem linha divisória, sem espaço entre as partes.** A passagem
  ocupa uma única linha de mistura, que é só antisserrilhado de escala.
- **Sem margem em volta.** As duas faixas ocupam o quadro inteiro.

**Cuidado ao medir este formato:** o reel tem um balão de headline atravessando
a divisa, e ele produz as bordas horizontais mais fortes do quadro inteiro. Um
detector de borda ingênuo aponta o balão, não a costura. Foi preciso ler os
valores crus de colunas nas pontas, longe do balão. O balão e o card de notícia
são lettering, não fazem parte deste formato.

**Geometria implementada:** 716 em cima e 1204 embaixo, somando 1920.

Números pares de propósito: o H.264 com `yuv420p` exige altura par em cada
camada. Com 717 e 1203 o ffmpeg arredonda sozinho e **entrega um arquivo de
1080x716, ou seja, só a faixa de cima**, sem reclamar de nada. O sintoma seria
um vídeo entregue sem metade do conteúdo. Fica a um pixel da referência.

**Enquadramento das duas faixas:** cada fonte é ampliada até cobrir a faixa
inteira e o excedente é cortado pelo miolo, descartando igual dos dois lados.
Nada de faixa preta, nada de fundo borrado. Decisão da pessoa, e é também o
que a referência faz.

**Receita ffmpeg:**

```
[insert]scale=1080:716:force_original_aspect_ratio=increase,
        crop=1080:716,setsar=1[topo];
[orig]  scale=1080:1204:force_original_aspect_ratio=increase,
        crop=1080:1204,setsar=1[base];
[topo][base]vstack=inputs=2
```

O `setsar=1` não é enfeite. Sem ele o `scale` preserva a proporção de exibição
da fonte e devolve pixel não quadrado: o arquivo sai marcado como 716:1273 em
vez de 9:16. Alguns players corrigem isso e outros não, então o mesmo vídeo
estica diferente dependendo de onde é assistido.

**Verificação:** costura do render medida em y=716 pelo mesmo método usado na
referência, contra 717 medido nela. Saída 1080x1920 com pixel quadrado 1:1.

**Áudio:** insert mudo, como todos. Só o áudio original toca.

---

## 4. `dividida_foco_insert`

O espelho do formato 3. Insert numa faixa grande em cima, filmagem original
numa faixa pequena embaixo. Serve quando o material de apoio é o assunto e a
pessoa está só narrando.

**Referência:** reel de `vaibhavsisinty`, formato no ar desde o início.

**Medições feitas no arquivo:**

- **Fronteira em y=1198.** Faixa do insert 62,4% da altura, faixa do original
  37,6%. É praticamente o espelho do formato 3 (37,3% / 62,7%): os dois usam a
  mesma divisão, invertida.
- **Sem faixa preta entre as partes.** As duas se encostam.
- Sem moldura, sem linha, sem margem em volta.

**Como a fronteira foi encontrada, porque o caminho direto não funciona:** a
referência tem uma sombra que escurece o pé do insert até o preto absoluto. Na
coluna central o brilho desce em rampa de 111 até 0 ao longo de mais de cem
linhas, o que apaga qualquer borda detectável. Um detector de borda não acha
nada ali, e a olho parece existir um vão preto entre as duas partes.

A saída foi medir **croma** em vez de brilho, isto é, o quanto os canais R, G e
B diferem entre si. No instante 12s o insert é uma interface cinza, com croma
zero, e a filmagem é colorida. O croma é 0 até a linha 1194 e sobe a partir da
1195 até o valor cheio na 1200. Não há vão nenhum: o que parecia vão era a
sombra.

Esse truque só funcionou porque o insert daquele trecho era cinza. Em outro
material seria preciso outro discriminador.

**A sombra não faz parte do formato.** Decisão da pessoa. As duas partes se
encostam com borda dura. Isso é uma diferença visível em relação à referência,
onde a passagem é suave. Se um dia a borda dura incomodar, dá para acrescentar
um degradê de escurecimento no pé do insert.

**Geometria implementada:** 1200 em cima e 720 embaixo, somando 1920. Dois
pixels da referência, e as duas alturas são pares, como o H.264 exige.

**Enquadramento:** igual ao formato 3. Cada fonte é ampliada até cobrir sua
faixa e o excedente sai pelo miolo, descartando igual dos dois lados.

**Receita ffmpeg:** a mesma do formato 3, com os dois números trocados.

```
[insert]scale=1080:1200:force_original_aspect_ratio=increase,
        crop=1080:1200,setsar=1[topo];
[orig]  scale=1080:720:force_original_aspect_ratio=increase,
        crop=1080:720,setsar=1[base];
[topo][base]vstack=inputs=2
```

**Verificação:** costura do render medida em y=1200, contra ~1198 na
referência. Saída 1080x1920 com pixel quadrado.

**Áudio:** insert mudo, como todos.

---

## 5 e 6. `vazado_maior` e `vazado_pequeno`

Insert preenchendo o quadro inteiro, filmagem original num painel de cantos
superiores arredondados no rodapé, e a **pessoa recortada do próprio fundo**
transbordando por cima da borda do painel, sobre o insert.

Mesma receita, dois conjuntos de números. Ambos aprovados sobre material real.

**Referência da geometria:** post de `nick_saraev`.

| | `vazado_maior` | `vazado_pequeno` |
|---|---|---|
| Escala da filmagem | 100% | 70% |
| Painel | 1080 x 480, largura cheia | 756 x 480, centralizado |
| Raio do canto superior | 180 | 126 |
| Margem lateral | nenhuma | 162 de cada lado |

Os dois vazam pela base do quadro, então só os cantos de cima são arredondados.

**O painel tem 480 de altura, não os 683 medidos na referência.** A pessoa pediu
o original ocupando menos espaço depois de ver a primeira versão.

### As três camadas, nesta ordem

1. insert em tela cheia
2. painel com a filmagem, recortado no retângulo de cantos arredondados
3. a mesma filmagem **com o fundo removido**, sem recorte, por cima

A camada 3 só aparece acima da borda do painel. As duas precisam estar na mesma
escala e no mesmo deslocamento, senão aparece um degrau no pescoço.

### Posicionamento: proporcional à cabeça, e a cabeça é medida

O transbordo é `0,38 x altura da cabeça`, e a altura da cabeça sai da máscara,
não de estimativa.

**Como o fim da cabeça é encontrado:** a silhueta abre no cabelo, estrangula no
pescoço e abre de novo nos ombros. No material de teste a largura vai de 96 no
topo do cabelo a 774 na altura mais larga, cai para 526 em y=1063 e volta a
1078 nos ombros. **Esse mínimo local é o pescoço.**

Sem isso, a única medida disponível seria a silhueta inteira, que vai até o pé
do quadro: usá-la dá transbordo de 481 em vez de 265, quase o dobro.

```
altura_cabeça = pescoço - topo_da_silhueta
vazamento     = 0,38 * altura_cabeça * escala
y0            = topo_do_painel - vazamento - topo_da_silhueta * escala
```

A fração de 0,38 está calibrada para reproduzir o render aprovado: dá 265 no
`vazado_maior` e 185 no `vazado_pequeno`.

### Limite conhecido: o formato pede plano médio

Se a cabeça for mais alta que o painel, não existe posição que caiba o rosto
inteiro. O `vazado_pequeno` contorna sozinho, porque a 70% a cabeça encolhe.
**Em gravação de close fechado, preferir o `vazado_pequeno`.**

---

## 7. `react` e 8. `react_miniatura`

Insert numa faixa grande no topo, fundo preto embaixo, e a pessoa embaixo,
deslocada para a direita. Duas formas de mostrar a pessoa: recortada do fundo,
ou dentro de uma miniatura arredondada.

**Referência:** reel de `vaibhavsisinty`, mesmo criador do formato 4.

| | valor | fração do quadro |
|---|---|---|
| Faixa do insert | 1080 x 1200, topo, sem arredondamento | 62,5% da altura |
| Fundo abaixo | preto chapado | |
| Altura da pessoa | 800px | 41,7% da altura |
| Centro horizontal | x = 793 | 73,4% da largura |
| Folga insert -> cabeça | 74/646 da altura da pessoa | |

**Altura da faixa do insert: 1200px.** Não pôde ser medida direto porque tem a
mesma rampa de escurecimento do formato 4: o valor cai a zero entre 1150 e 1255
dependendo do quadro. A conclusão vem do formato 4, do mesmo criador, onde a
fronteira foi medida em 1198 por croma.

**Altura da pessoa: 800px.** Medida original da referência era 646; a pessoa
pediu maior depois de ver.

### A decisão entre recortado e miniatura é DELA, não da skill

**Vale só aqui, no `react`.** Nos dois vazados o aviso não se aplica: lá só a
cabeça aparece acima do painel e o ombro encostado na borda fica dentro dele,
onde a imagem é a filmagem crua e nada é recortado. Perguntar no vazado por
causa de `recorte_amputado` é ruído, e ela apontou isso em teste real.

No `react` a pessoa aparece inteira sobre o fundo. Quando ela encosta na borda
do quadro original, o recorte sai com uma linha reta cortando o corpo, com cara
de membro amputado.

Isso é medido, não avaliado no olho: `ocupacao_lateral` é a fração da coluna de
borda do quadro coberta pela silhueta. No material de teste deu **31% na
esquerda e 27% na direita**, e o recorte saiu com a camiseta cortada em linha
reta. Acima de **15%** o problema aparece.

```bash
python3 scripts/insert.py --medir --matte matte.mp4
```

**Quando a medição acusar, PERGUNTE.** Decisão explícita da pessoa: ela quer
saber que o recorte vai sair cortado e escolher se aceita assim mesmo ou se
prefere a miniatura. **Não escolher por ela.** A medição serve para fazer a
pergunta na hora certa, não para decidir sozinho.

Quando a medição não acusar, o recorte serve e não precisa perguntar.

**Miniatura:** retângulo de 450x800 com os quatro cantos arredondados em raio
40, centro em x=793, margem de 56 da base. Mostra a filmagem crua, sem recorte,
então não depende de máscara nenhuma.

---

## Tratamento da borda do recorte

Vale para todos os formatos com recorte. Foi a parte que mais deu trabalho.

```
erosion x N, scale=460:-2:flags=area, scale=<tamanho>:flags=bicubic,
gblur=sigma=S, tmix=frames=3
```

### Por que reamostrar a máscara para 460

Esta é a peça mais importante e foi descoberta por comparação, não por teoria.

O `react` ficou visivelmente melhor que os vazados **usando exatamente a mesma
máscara e o mesmo tratamento**. A diferença era escala: no react a pessoa entra
a 42%, então a máscara de 1080 é reduzida para 458, e a redução faz média entre
pixels vizinhos, criando transição suave onde a máscara tinha degrau. Nos
vazados a pessoa entra a 100% e o degrau aparece em tamanho real.

A solução é imitar isso sem encolher a pessoa: **reduzir a máscara para 460 de
largura e trazer de volta ao tamanho de exibição.** Isso apaga o degrau de alta
frequência e mantém a pessoa cheia.

### Erosão proporcional

Erosão é operação de 1 pixel fixo. Duas erosões numa máscara de 458 comem 0,44%
da largura; as mesmas duas em 1080 comem 0,19%. Sem perceber, o react estava
recebendo erosão proporcionalmente duas vezes e meia mais forte que o
`vazado_maior`. Agora o número de passes é `4,7 x escala`: 5 em escala cheia,
3 a 70%, 2 a 42%.

### Não endurecer a máscara

Uma primeira versão aplicava `lut=y='clip((val-100)*3.6,0,255)'` para resolver
mão semitransparente. Isso resolve a mão e **destrói o cabelo**, que é
justamente a região de transparência parcial.

### Medições que motivaram tudo isso

Na máscara crua, na região do cabelo: só **3,7% dos pixels têm meio-tom**, e de
um quadro para o outro **1,6% dos pixels mudam drasticamente**, o que parado
não se vê e em movimento vira chiado. O `tmix` resolve o chiado.

### Caminhos testados e descartados

- **Filtro `guided`**, o refinamento clássico para cabelo: destruiu a máscara.
  Ele ajusta o alfa seguindo a intensidade da guia, e com cabelo escuro sobre
  parede escura puxa tudo para transparente.
- **Ampliar o quadro inteiro 2x antes de segmentar**: o detector passa a
  incluir região escura do fundo como parte do assunto.
- **Segmentar só a faixa acima do painel, ampliada**: mesmo defeito.

Só o recorte apertado na cabeça melhorou o contorno, e pouco. Fica registrado
como próximo passo se um dia valer a complexidade de seguir a cabeça.

### Teto: o material manda mais que o algoritmo

No bruto de teste **o cabelo já estava desfocado na origem**, com fundo escuro
contra cabelo escuro. Nenhuma ferramenta inventa detalhe que a câmera não
registrou. Gravação com foco no rosto e separação de luminância entre cabelo e
fundo muda o resultado mais que qualquer ajuste de filtro.

---

## O recorte da pessoa

`scripts/mascara.py`, nos três sistemas. No Mac usa a Vision (o
`segvideo.swift`, compilado sozinho no cache da skill); no Windows e no Linux, o
`remove-background` do HyperFrames, bem mais lento, e por isso com `--janelas`.

```bash
python3 scripts/mascara.py entrada.mp4 -o analise/matte.mp4
python3 scripts/mascara.py entrada.mp4 -o analise/matte.mp4 --janelas 12.4-19.8,61-66
```

**API: `VNGenerateForegroundInstanceMaskRequest`**, a mesma do "copiar assunto"
do Preview. Nativa do macOS, sem baixar modelo.

Escolhida contra `VNGeneratePersonSegmentationRequest` depois de comparar as
duas na mesma imagem, e ganha nos dois eixos: a de pessoa devolve máscara em
1512x2016 para imagem 1080x1920, em proporção errada e menor que o vídeo, e
esticada deixa halo em volta do cabelo; a de assunto devolve na resolução real.
E roda a 0,10s por quadro contra 0,45s, quatro vezes mais rápida.

A de pessoa fica como reserva por quadro.

---

## Os oito nomes exatos

O que vai no campo `formato` é a string da esquerda. Nenhuma outra grafia é
aceita, e o `plano.py` recusa a lista inteira se errar:

| string | é o quê |
|---|---|
| `tela_cheia` | o insert ocupa o quadro todo |
| `moldura` | insert dentro de moldura arredondada, fundo preto |
| `dividida_foco_original` | tela dividida, mais espaço para a filmagem |
| `dividida_foco_insert` | tela dividida, mais espaço para o insert |
| `vazado_maior` | insert atrás, pessoa recortada por cima, painel maior |
| `vazado_pequeno` | o mesmo, com o painel menor |
| `react` | pessoa recortada inteira sobre o insert |
| `react_miniatura` | igual, mas a pessoa entra em miniatura arredondada |

## Como montar

```bash
# mede a silhueta e diz se o recorte vai sair amputado
python3 scripts/insert.py --medir --matte matte.mp4

# monta
python3 scripts/insert.py --formato vazado_maior \
  --original bruto.mp4 --insert apoio.mp4 --matte matte.mp4 \
  --saida saida.mp4 --dur 9.8
```

Formatos sem `--matte`: `tela_cheia`, `moldura`, `dividida_foco_original`,
`dividida_foco_insert`, `react_miniatura`.

**Armadilha do shell, custou um vídeo errado:** ao montar filtro de ffmpeg em
linha de comando, sempre usar `${VAR}` e não `$VAR`. O zsh interpreta
`$A[mini]` como índice de array e devolve **vazio**, o que faz o ffmpeg montar
um grafo diferente sem reclamar de nada e entregar um vídeo errado. Os scripts
da skill declaram bash no topo e escapam disso, mas comando digitado direto no
terminal não.

O `insert.py` confere a dimensão da saída e falha se não for 1080x1920, que é a
rede de segurança para esse tipo de erro silencioso.

---

<!-- Próximos formatos entram aqui, um por vez, medidos da mesma forma. -->


## O formato pode comer o fecho da arte

Nos vazados e no react o quadro do insert **não aparece inteiro**: o painel come
os últimos 480 pixels e a cabeça recortada ainda vaza acima dele. No
`vazado_pequeno` medido em material real, a zona tapada começa em **y=1275** de
1920. No `vazado_maior`, em 1205. No `react`, em 1120.

Isso derrubou duas artes num anúncio real. Uma terminava numa caixa escrita "A
MESMA HISTÓRIA", que era o fecho do raciocínio, e a outra listava três itens
sendo que o terceiro era o mais forte: os dois sumiram atrás do painel, e o
insert virou meia frase.

**O `plano.py inserts` mede a arte e avisa.** Ele lê a altura do último conteúdo
do arquivo em cinco instantes, tomando o fundo da primeira linha do quadro em
vez de assumir preto, e compara com a zona tapada do formato.

**Quando avisar, PARE E PERGUNTE.** São duas saídas e a escolha é dela:

- **trocar o formato** por um que mostre o quadro inteiro (`moldura`,
  `tela_cheia`, `dividida_foco_insert`);
- **subir a arte**, com o campo `"subir": <pixels>` no insert. O comando já diz
  quantos pixels resolvem. O render corta esse tanto do topo e completa embaixo
  com preto, e como a folga de cima costuma ser margem vazia, não se perde nada.

```json
{ "de": 60.117, "ate": 66.860, "arquivo": "inserts/n2.mp4",
  "formato": "vazado_pequeno", "subir": 199, "motivo": "..." }
```

**Não decidir sozinho.** O que fica tapado é quase sempre o fecho, que é
justamente o que a arte existe para dizer.


## Rosto que volta por meio segundo entre dois inserts

**Grudar um insert no outro não é problema nenhum.** Decisão explícita dela.
Voltar para o rosto por menos de 1,5s entre dois inserts não lê como corte, lê
como falha: parece que o vídeo engasgou.

Num anúncio real isso aconteceu quatro vezes, com buracos de 0,92s, 0,77s, 0,18s
e 0,10s. O de 0,10s é um piscar de três quadros, e nem se percebe o que era.

O `plano.py inserts` mede o vão **em tempo final**, não em timecode do original,
porque é assim que a pessoa vê, e avisa abaixo de 1,5s. Para cada buraco ele diz
qual dos dois arquivos é longo o bastante para fechar:

- se o de trás estica, aumentar o `ate` dele até o `de` do próximo;
- se não, puxar o `de` do próximo para trás até o `ate` do anterior;
- se nenhum dos dois cobre, **avisar**: aí é trocar o arquivo por um mais longo
  ou aceitar o corte.

O aviso não é recusa. Um take de rosto longo entre inserts é legítimo e não
dispara nada; o que ele persegue é o piscar involuntário nascido de janelas
ajustadas pela fala.


## Enquadrar o rosto nas divididas

Nas divididas a faixa da filmagem e mais baixa que a pessoa, entao o corte
central pode cortar a testa ou o queixo. O campo `enquadrar` desloca esse corte
na vertical, em pixels: **negativo sobe** (mostra mais do topo da cabeca),
positivo desce.

```json
{ "de": 87.1, "ate": 93.0, "arquivo": "inserts/dash.mp4",
  "formato": "dividida_foco_insert", "enquadrar": -170,
  "motivo": "meio termo, sem cortar testa nem queixo" }
```

Medido em material real: no `dividida_foco_insert` o corte central cai em
y=600 do quadro de 1920 e come 266px da cabeca. Com `-170` a cabeca aparece
quase inteira e o queixo sobra com folga. **Meca antes de chutar**: extraia um
frame do original, recorte `crop=1080:720:0:<y>` em tamanho real e olhe.

O valor e limitado ao que existe de imagem, entao um exagero encosta na borda
em vez de deixar faixa preta.

## A trava de material usa a projecao, nao a regra de tres

A validacao de "o arquivo cobre a janela?" projeta os dois extremos pelo mesmo
caminho do render. A conta simples `(ate-de)/fator` **superestima**, porque
ignora os silencios cortados DENTRO da janela: num take real de 11,4s com 4,1s
de pausa cortada ela pedia 7,86s de arte quando o render consome 5,02s, e
recusava uma arte que servia.
