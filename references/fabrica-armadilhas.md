# Armadilhas

Cada uma destas custou uma volta de retrabalho. Leia antes do primeiro `check`.

## O verificador reprova efeito legítimo

O `check` reprovou o revelador móvel **85 vezes** na primeira tentativa. Ele
achou que as palavras apagadas eram texto ilegível e que as camadas sobrepostas
eram erro de layout. Não eram: eram o efeito.

**O procedimento é sempre o mesmo:** tire o print antes de mexer no layout.
Confirme com os olhos se o que o verificador viu é o efeito ou um defeito de
verdade. Só então marque.

Marcar é decisão, não atalho, e vai **no elemento mais estreito possível**,
nunca no wrapper de cena.

| Atributo | Para |
| --- | --- |
| `data-layout-ignore` | decorativo que não deve ser auditado |
| `data-layout-allow-overlap` | camadas de texto sobrepostas de propósito |
| `data-layout-allow-overflow` | algo que sai do quadro de propósito |
| `data-layout-allow-occlusion` | algo que cobre texto de propósito |

## Anton: a caixa de linha de 1,55em

A Anton ocupa cerca de 1,55em de caixa, ou seja, uns 46 px acima das maiúsculas
em corpo 150. O `check` mede a caixa da fonte, não a tinta visível, então
qualquer empilhamento acusa `content_overlap` mesmo com as letras a 20 px de
distância.

**Mas nem toda acusação é falsa.** No teste B ele acusou cinco e **duas eram
verdadeiras**: a entrelinha estava apertada e o acento do Ú invadia a linha de
cima. Print primeiro, sempre.

Entrelinha segura para a Anton em display: **1,12 a 1,16**. Abaixo disso ela
encosta.

## Anton: é condensada

Ao substituir uma display larga (Archivo Black, por exemplo), **suba o corpo em
torno de 25% e solte o tracking para perto de zero**. Manter o mesmo corpo e o
tracking negativo faz o peso visual despencar.

## Rotação em 3D sai do eixo se a âncora estiver errada

Com `left: 50%; top: 50%` e `translate(-50%,-50%)` no fim da cadeia, a rotação
gira em torno de um ponto deslocado, não do centro real do plano. Quanto maior o
giro, mais a peça sai do centro: uma palavra com 50 graus ficou 110 px fora.

**Correção:** `transform-origin: 0 0` no elemento. Aí a cadeia
`translate3d(...) rotateY(...) translate(-50%,-50%)` gira em torno do centro de
verdade.

## Separar camadas só em Z quase não rende

Sob perspectiva, afastar painéis empilhados apenas no eixo Z produz uma diferença
de escala pequena demais: parece um painel só com as bordas aparecendo.

**Correção:** separe em X e Y também, em leque, centralizado no índice do meio.

## Valor por função em variável de CSS não é confiável

`{ "--pz": (i) => ... }` não se comporta como em propriedade normal. Quando o
alvo depende do índice, **percorra os elementos e escreva uma tween por
elemento**, com o tempo escalonado na mão.

## Varredura de gradiente por dentro das letras não pinta

`background-clip: text` mais tween de `background-position` anima a propriedade
corretamente (dá para conferir medindo no DOM) mas **não pinta no render**.
Amostrei os pixels do frame para confirmar.

**Alternativa que funciona:** cópias empilhadas por palavra com envoltória de
opacidade, ou o `yt-feather-highlight` do catálogo.

Observação: animar variável de CSS **funciona** neste motor. O `spotlight-card`
do catálogo faz isso. O problema acima é específico do `background-position`.

## O grifo apaga o próprio texto, e o `check` não vê

A mais provável de todas, porque o `grifo` é a primitiva mais usada e está em
quase toda cena. Em projeto de fundo escuro ela **sempre** cria o problema.

A barra de acento abre por trás da palavra. Enquanto ela passa, metade da
palavra está sobre o fundo e metade sobre o acento. Se o texto tiver uma cor só,
uma das metades fica ilegível. Trocar a cor por tween no meio do caminho cria um
instante de escuro sobre escuro: **contraste 1:1, texto invisível.**

E o pior: as duas formas documentadas de rodar a checagem **passam limpas**.

```
npx hyperframes check .                    → 0 erros, contraste 32/32 passa
npx hyperframes check . --at-transitions   → 0 erros, contraste 23/23 passa
npx hyperframes check . --at 5.25,5.3,5.35,5.4
  ✗ #g1 2.75:1 (need 3:1, t=5.25s)
  ✗ #g1 1:1    (need 3:1, t=5.35s)
```

As nove amostras padrão caem nos extremos das tweens, onde está tudo certo. O
defeito mora no meio. E o mesmo defeito, na mesma construção, foi pego pelo
`check` padrão em outra composição: **o que decide não é o defeito, é a sorte de
onde as amostras caem.**

### A correção

Duas cópias da palavra, recortadas pela **mesma** variável que abre a barra. E o
detalhe que muda tudo: **a barra é o fundo da própria cópia escura**, não um
elemento separado. Assim o mesmo `clip-path` corta texto e barra juntos e nunca
existe um pixel de acento sem o texto escuro certo em cima.

```html
<span class="grifo" id="g1"
      data-layout-allow-overlap="true" data-layout-allow-occlusion="true">
  <span class="g-clara">palavra</span><span class="g-escura">palavra</span>
</span>
```

```css
.grifo { position: relative; display: inline-block; padding: 10px 16px; }
.grifo > span { display: block; white-space: nowrap; }
.grifo .g-clara {           /* a metade ainda FORA do acento */
  color: var(--tinta);
  clip-path: inset(0 0 0 calc(var(--w, 0) * 100%));
}
.grifo .g-escura {          /* a metade JA sobre o acento */
  position: absolute; inset: 0; padding: 10px 16px;
  color: var(--fundo); background: var(--acento);
  clip-path: inset(0 calc(100% - var(--w, 0) * 100%) 0 0);
}
```

**O pai não pode ter texto próprio.** O verificador de contraste lê o nó de texto
direto do pai e ignora o `clip-path` dos filhos.

**Os dois atributos andam em par.** Só `data-layout-allow-overlap` não resolve:
ele muda o diagnóstico de `content_overlap` (aviso) para `text_occluded` (erro),
e o `check` reprova. Precisa dos dois juntos.

### O verificador NÃO consegue provar esta correção. Só o print prova.

Isto é o mais importante desta seção, e eu escrevi errado na primeira versão.

O verificador de contraste amostra o **centro da caixa** de cada cópia e ignora o
`clip-path`, então lê a metade que está recortada fora. Medido na correção
correta, com o render visualmente perfeito em todo quadro:

```
npx hyperframes check . --at 1.1,1.2,1.3,1.4,1.5
  ✗ span:nth-of-type(2) 1:1    (need 3:1, t=1.1s)
  ✗ span:nth-of-type(1) 1.89:1 (need 3:1, t=1.2s)
```

**1:1 é o mesmo número do defeito que esta correção conserta.** Não dá para
distinguir o conserto do bug pelo relatório.

Então o procedimento é:

1. implemente as duas cópias
2. `npx hyperframes snapshot --at <cinco tempos dentro da tween>`
3. **olhe os cinco prints.** Cada um tem que estar legível: claro sobre fundo de
   um lado, escuro sobre acento do outro
4. só depois marque os dois atributos de exceção

Amostrar com `--at` no meio da tween serve para achar o defeito na versão
ingênua. **Não serve para aprovar a correção.**

## O `check` não vê tela vazia

Um handoff mal encaixado deixa um buraco: a frase morre em 2,74 e a próxima
coisa nasce em 2,78. No meio, **quadro totalmente preto**.

Os quatro verificadores passam limpos. Não existe regra que reclame de quadro
sem conteúdo, porque tecnicamente não há erro: não tem sobreposição, não tem
texto ilegível, não tem overflow.

Num insert que substitui um rosto falando, um quadro preto no meio é grave.

**Como pegar:** amostre exatamente na fronteira entre duas batidas, não no meio
de cada uma. Se a saída de uma termina em `t` e a entrada da outra começa em `t`,
tire print em `t`.

**Como evitar:** sobreponha as duas em pelo menos 0,15 s. A saída de uma começa
antes de a entrada da outra terminar.

## autoAlpha na morte dura apaga o elemento desde o quadro zero

A mais cara de todas até agora: apagou metade de um insert e **o `check`
passou limpo**. Só apareceu no print.

O `check` pede um `tl.set` de morte dura depois de toda saída que termina numa
fronteira de clipe. A tentação é escrever `tl.set(alvo, { autoAlpha: 0 })`.

**`autoAlpha` mexe em opacidade E em visibilidade.** Se a entrada daquele
elemento anima só `opacity`, o `visibility: hidden` que o `set` deixou nunca é
desfeito: a opacidade anima bonito num elemento invisível.

Duas saídas:

- use **`visibility` pura** na morte dura, e dê a cada elemento um
  `tl.set(alvo, { visibility: "visible" }, 0)` no tempo zero, para o seek para
  trás ter estado explícito;
- ou use `autoAlpha` **dos dois lados**, entrada e saída, sem misturar.

E a lição maior: **o `check` não vê isso.** Só o print vê.

## `tl.call` não é confiável em seek para trás

Trocar texto com `tl.call(() => el.textContent = "...")` funciona tocando para
frente e falha quando a linha do tempo é arrastada para trás, porque o callback
não tem estado reverso.

**Correção:** duas cópias empilhadas do texto, trocadas por opacidade. É a
primitiva `trocaJanela` em `primitivas.js`.

## O preview do Studio escreve no seu arquivo

Enquanto `hyperframes preview` roda, ele injeta `data-hf-id` em cada elemento do
`index.html`. Isso derruba edição em lote feita por script.

**Pare o preview antes de editar em lote.**

## Duas tweens de câmera se pisando

Quando uma perna de aproximação e uma troca de cena se sobrepõem, o `check`
acusa `overlapping_gsap_tweens`. Encerre cada perna antes de a próxima começar.

## Memória

Numa máquina com pouca RAM livre, use `--workers 2`. Cada worker sobe um Chrome
de uns 256 MB.

## Quando alguma coisa treme, desmonte antes de investigar

Vem do guia MOTION VOX STYLE e é melhor que o que a gente fazia, que era pensar.

Monte a versão crua: sem borrão, sem sombra, sem grão, sem vinheta, sem
acabamento nenhum. **Estável?** Devolva um acabamento por vez, renderizando entre
cada um. O culpado aparece sozinho.

Custa três ou quatro renders de segundos. Raciocinar sobre qual das seis coisas
está errada custa muito mais, e costuma errar.

As três causas mais comuns, na ordem:

1. movimento aleatório por camada, quando deveria ser um só movimento de câmera
2. dois planos na mesma profundidade, que deviam estar separados
3. um arquivo em resolução menor que a composição

Esta seção existe porque as catorze armadilhas acima foram achadas uma a uma, na
dor. Várias teriam caído em minutos com este protocolo.

## A vinheta reprova todo texto da composição

Um overlay de tela cheia com alfa alta faz o `check` acusar `text_occluded` em
**todos** os textos. E os dois atributos de exceção no oclusor não resolvem: a
regra dispara no texto.

**Correção:** vinheta abaixo do conteúdo, grão acima. Detalhe medido em
`fabrica-acabamento.md`.

## O tween que vem no snippet do catálogo pode estar comentado

O `vignette` traz o bloco de integração com a timeline **dentro de um comentário
HTML**. Editar os valores ali não muda nada. Confira se o código que você está
ajustando está de fato dentro do `<script>`.

## Deriva lenta de câmera não conta como movimento

Uma escala de 5% ao longo de 6 s parece "a câmera nunca para". Medido, **não
registra**: dá 0,33 px por quadro na borda e o `medir_ritmo.py` lê a tela como
parada.

O que sustenta o quadro é câmera **em pernas encadeadas**, cada perna com começo
e fim, como o `aproxima` e o `trocaCena` já fazem. A mesma composição foi de 22%
para 59% de movimento só trocando a deriva única por quatro pernas.

## Nenhum verificador do HyperFrames vê português errado

Sete inserts de um anúncio foram entregues com **"voce", "operacao", "Conteudo",
"Prospeccao", "alguem" e "sab"** na tela. O `lint` passou, o `check` passou, o
contraste passou, o ritmo passou. Nada disso é erro de layout, então nada
reclamou.

A causa é banal: escrevendo HTML direto no terminal, sem acento sai mais rápido,
e o texto que vira arte é o mesmo texto que você digitou.

```bash
python3 <skill>/scripts/verificar_acentos.py inserts/ --recursivo
```

**Rode antes de renderizar.** O conserto é no HTML, e cada render custa.

O script lê só o `<body>` (o `<title>` costuma ser o nome do arquivo em
kebab-case e daria falso positivo em toda palavra), ignora `<script>` e
`<style>`, e separa dois tipos: palavra que **sempre** leva acento, que reprova,
e palavra ambígua como `esta`, `pais` e `pratica`, que só avisa com `--avisos`.

## `fromTo` aplica o estado inicial na montagem, não na hora do tween

Custou dois defeitos visíveis de uma vez, e os quatro verificadores passaram
limpos nos dois.

O GSAP renderiza o `from` de um `fromTo` **no momento em que a timeline é
montada**, não quando o tween começa. Se o estado inicial for visível, ele vaza
para **todo o trecho anterior**.

```js
// um anel de choque que deveria aparecer so em 1,18s
tl.fromTo("#onda", { scale: 0.94, opacity: 0.95 },
  { scale: 2.5, opacity: 0, duration: 0.62 }, 1.18);
```

Resultado: o anel fica **na tela desde o quadro zero**, em opacidade 0,95, e só
começa a animar em 1,18. O CSS tinha `opacity: 0` e não adiantou nada.

O segundo caso foi mais sutil: um gradiente de sombra com
`fromTo(el, { xPercent: -26 }, ..., 1.52)` deixou a sombra deslocada para a
esquerda durante o primeiro segundo e meio, o que desenhou uma **faixa escura
com borda dura** na face de um cartão claro. Parecia erro de desenho, era
tempo.

**Correção:** `immediateRender: false` no `fromTo`.

```js
tl.fromTo("#onda", { scale: 0.94, opacity: 0.95 },
  { scale: 2.5, opacity: 0, duration: 0.62, immediateRender: false }, 1.18);
```

**Quando isso morde:** só quando o `from` é visível. Um `fromTo` que parte de
`opacity: 0` não tem esse problema, e é por isso que a maioria das entradas
funciona sem pensar no assunto. O sintoma é sempre o mesmo: **uma coisa que
deveria entrar no meio já está lá desde o começo**, parada.
