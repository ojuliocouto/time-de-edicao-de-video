# Os números

Cada número aqui tem, na mesma linha, **como foi obtido**. Número sem método é
opinião com cara de dado, e foi assim que o guia VOX escreveu a tabela dele:
"duração validada", sem dizer validada contra o quê.

Duas fontes:

- **medido**: saiu de render nosso, com script que está em `scripts/`
- **herdado**: veio do guia VOX, ainda não validado aqui. Marcado como tal.

---

## 1. Ritmo: o número que mais importa

**A tela tem que estar se mexendo em pelo menos 55% da duração, e a maior parada
não passa de 0,8 s** (ou 2% da duração, o que for maior, para peça longa).

Método: rodei `scripts/medir_ritmo.py` nas **referências de motion que a pessoa
escolheu** e em inserts nossos já entregues.

| | referências dela | nossos inserts |
| --- | --- | --- |
| em movimento | 59% a 100% (mediana 90%) | 54% a 76% (mediana 68%) |
| maior parada | 0,00s a 1,50s (mediana 0,33s) | 0,40s a 2,03s |

Com esses limites o verificador **aprova as sete referências de motion dela e
reprova dois dos nossos quatro inserts reais.** Discrimina, então serve.

Este é o número que explica "achei simples". Não era a paleta e não era a
composição: a nossa tela fica parada bem mais tempo que a das referências que
ela escolheu, e as paradas são o dobro ou o triplo mais longas.

```bash
python3 <skill>/scripts/medir_ritmo.py renders/<insert>.mp4
```

### O borrão não é enfeite, é o que impede a medida de mentir

O `grain-overlay`, que é acabamento legítimo, anima por `@keyframes` de CSS e
muda pixel em **todo** quadro. Sem tratamento, ele infla a medida: a mesma
composição deu **83% com grão e 59% sem**.

Por isso o script passa um `boxblur=6` antes de comparar os quadros. Com o
borrão as duas medições coincidem em 22%. Foi o borrão que forçou recalibrar
todos os limites acima, e é por isso que eles são mais baixos do que a primeira
versão deste arquivo dizia.

**Nunca rode com `--borrao 0` numa peça com grão.**

### Deriva lenta de câmera não conta como movimento

Coloquei uma escala de 5% ao longo de 6 s achando que sustentaria o quadro
durante os holds. Medido: **não registra**, porque dá 0,33 px por quadro na
borda. A composição deu 22%.

Trocando a deriva única por **quatro pernas encadeadas** de câmera, cada uma com
começo e fim, a mesma composição foi para **59%** e passou. É o que o
`aproxima` e o `trocaCena` do `primitivas.js` já faziam certo.

### O hold de leitura não é tela parada

O guia VOX pede hold mínimo de 1 segundo para dar tempo de ler. As referências
dela têm paradas bem menores. Os dois estão certos porque medem coisas
diferentes: nas referências o texto **fica** o tempo de leitura enquanto a
câmera continua trabalhando por baixo.

**Segure o texto o tempo de ler, e nunca congele o quadro para isso.**

Tempo de leitura, do padrão de legenda: **13 caracteres por segundo**, com piso
de 1 segundo. Uma frase de 26 caracteres pede 2 segundos no ar.

---

## 2. Stagger: o nosso estava quebrado

**Mínimo de 3 frames entre elementos. A 30 fps, isso é 0,10 s.**

Método: aritmética, não gosto. O `umViraMuitos` do `primitivas.js` usava
`each: 0.03`, que a 30 fps dá **0,9 frame**. Abaixo de um frame o stagger não
existe: os elementos entram todos no mesmo quadro renderizado.

| | stagger | em frames a 30 fps |
| --- | --- | --- |
| nosso `umViraMuitos`, antes | 0,03 s | **0,9** |
| nosso `palavrasSubindo` | 0,10 s | 3,0 |
| guia VOX | 0,10 a 0,20 s | 3 a 6 |

O de palavra já estava certo. O de grade estava três vezes abaixo do piso do que
é fisicamente visível. Corrigido para 0,10 s.

Este é o único número em que o guia é **objetivamente melhor** que o nosso, e dá
para provar sem opinião nenhuma.

---

## 3. Deslocamento por frame: o limite do strobe

**Um elemento não pode andar, entre dois quadros, mais do que o próprio tamanho
no eixo do movimento. Confortável é metade disso.**

Método: montei uma régua com cinco barras de 120 px viajando os mesmos 300 px em
durações diferentes, renderizei a 30 fps e medi o centroide de cada barra quadro
a quadro (`medicao-numeros/medir.py`).

| duração | pico medido | contra a barra de 120 px | sobreposição entre quadros |
| --- | --- | --- | --- |
| 4 frames | 205 px/f | 1,7× o tamanho | **nenhuma** |
| 6 frames | 155 px/f | 1,3× | **nenhuma** |
| 10 frames | 103 px/f | 0,86× | 14% |
| 16 frames | 68 px/f | 0,57× | 43% |
| 24 frames | 47 px/f | 0,39× | 61% |

Quando o deslocamento passa do tamanho do elemento, as posições em quadros
consecutivos **não se tocam**, e o olho vê dois objetos em vez de um se movendo.
Não há motion blur de shutter no HyperFrames para disfarçar isso.

Com `power3.out`, o pico está no **primeiro** frame da rajada e vale
`viagem × (1 − (1 − 1/N)³)`. Para achar a duração mínima de uma viagem `D` com
um elemento de tamanho `S`:

```
N mínimo = 1 / (1 − (1 − S/D)^(1/3))
```

Na prática: **viagem longa exige rajada longa.** Uma palavra de 60 px de altura
subindo 26 px cabe em 6 frames. A mesma palavra atravessando 400 px precisa de
uns 20.

---

## 4. Rajada de entrada: aqui eu não tenho prova

| | rajada de entrada |
| --- | --- |
| nossas primitivas | 12 a 13 frames (0,40 a 0,44 s) |
| guia VOX | 16 a 18 frames (0,53 a 0,60 s) |

**Não medi nada que diga que 16 é melhor que 12.** A única coisa que restringe a
duração com evidência é a regra 3 acima. Fica registrado como divergência aberta,
não como correção.

O que **não** é opinião: se a rajada encurtar a ponto de estourar o limite de
deslocamento, ela está errada, independente do gosto.

---

## 5. Composição: medimos e não era o nosso problema

O guia VOX gasta uma seção inteira em composição, com números fortes: 30 a 40%
de fundo puro, uma banda inteira intocada, no máximo cinco a seis elementos, uma
âncora ocupando 30 a 40% da largura.

Rodei `scripts/medir_quadro.py` nas onze referências dela e em seis inserts
nossos:

| | referências dela | nossos inserts | discrimina? |
| --- | --- | --- | --- |
| respiro | 57% a 99% (mediana 91%) | 70% a 97% (mediana 90%) | **não** |
| maior banda limpa | 1% a 48% (mediana 26%) | 18% a 33% (mediana 29%) | **não** |
| âncora | 35% a 100% (mediana 66%) | 38% a 91% (mediana 83%) | **não** |
| elementos | 1 a 6 (mediana 2) | 1 a 7 (mediana 3,5) | fraco |

Três das quatro medidas dão praticamente igual nos dois grupos. O piso de 30% de
respiro nunca chega perto de reprovar num quadro vertical: 90% de fundo é o
normal aqui.

**Conclusão honesta: composição nunca foi a nossa fraqueza, ritmo era.** O
`medir_quadro.py` reporta as três como informação e só reprova por número de
elementos.

O único que sobrevive:

**Máximo de 6 elementos por quadro.** Bate com o guia VOX e com o teto das
referências dela, que chegaram a 6 e não passaram. Um insert nosso deu 7.

Atenção ao contar: sem juntar letras vizinhas, o mesmo quadro dá **30**
"elementos" que são letras e linhas. O script dilata a máscara antes de agrupar,
com `--juntar`.

---

## 6. Herdados do guia VOX, ainda não validados aqui

Use, mas sabendo que não passaram por medição nossa:

| Número | Para |
| --- | --- |
| acento em no máximo 3 pontos, formando triângulo | leitura do quadro |
| traço de markup em 10 a 16 frames | grifo, círculo, sublinhado |
| uma ação dominante por vez | escalonamento de entradas |
| plano novo a cada 1 a 5 segundos | corte |
| profundidades não lineares: 0,12 · 0,40 · 0,55 · 1,25 | parallax de 4 planos |
| overscan das camadas 116% | parallax |
| rotação máxima de câmera 0,3° | parallax |

Os três últimos são de uma técnica que a gente ainda não montou. Quando montar,
medir e mover para a parte de cima deste arquivo.
