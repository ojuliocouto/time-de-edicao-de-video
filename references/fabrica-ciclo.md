# O ciclo de fabricação

Seis passos, iguais nos três modos, mais o plano da série antes de todos eles
quando o pedido tem mais de uma arte.

## 1. Trava o estilo

Uma vez por projeto. Se `estilo.md` existe, leia e obedeça. Se não existe, monte
a partir do que a pessoa der, nesta ordem:

1. um manual de marca ou arquivo de estilo que ela já tenha
2. imagens de referência que ela mandar, das quais você extrai paleta,
   tipografia e regras de composição
3. uma escolha sua, justificada em uma frase, entre os presets do HyperFrames

O arquivo trava, no mínimo:

- cor de fundo e cor de texto
- **uma cor de acento só**
- as famílias tipográficas com o papel de cada uma
- a margem de segurança

Esse passo é o que faz oito artes parecerem da mesma família em vez de oito
coisas soltas. A tipografia padrão é Anton mais Inter; ver a seção de tipografia
em `references/fabrica-regras.md`.

## 1b. Planeja a série

Só quando o pedido tem mais de uma arte, o que é o caso normal dos modos roteiro
e áudio.

Escreva o `PLANO.md`, mostre a tabela e **espere aprovação antes de construir**.
O formato e os cinco pisos estão em `fabrica-plano.md`.

O plano decide o que não dá para consertar depois: qual o plano de cada insert,
onde estão os cortes, qual carrega material real, qual dispositivo usa e onde
muda o registro. Verificar isso no fim significa descobrir na sétima peça que a
série é chapada e refazer seis.

## 2. Consegue o material

Ordem obrigatória, por arte:

1. **arquivo do banco do projeto**: já está lá, usa
2. **arquivo que a pessoa mandar**: peça quando souber o que precisa
3. **busca na internet**: procure, **mostre o que achou e espere o ok**. Nunca
   baixe e use sem mostrar
4. **constrói**: tipografia, ícone, diagrama, forma

Só chegue no 4 quando os três primeiros não deram, e **avise que caiu na
construção**, para a pessoa poder mandar um arquivo e pedir para refazer.

Registre origem e link de tudo que entra no banco, em `banco/registro.md`. Isso
é o que torna a pergunta de direito de uso respondível depois, quando a peça
virar anúncio de cliente.

**Ao gerar imagem, peça a composição, não só o assunto.** Descreva onde o texto
vai morar e peça aquela zona vazia. Um prompt que pede "os dois terços inferiores
com a ação e o terço superior quase vazio" resolve a legibilidade na geração, e
você nunca precisa de caixa ou sombra atrás da tipografia.

Arquivo real ganha de arquivo gerado quando os dois existem: acervo aberto tem a
textura e a imperfeição que a geração ainda inventa, e não custa nada.

**Regra dura contra take genérico:** quando o roteiro cita uma coisa que existe
no mundo, a arte mostra aquela coisa, não um substituto que finge ser. Falou de
uma ferramenta, entra a ferramenta. Falou de uma página que a pessoa fez, entra
o print da página dela.

## 3. Consegue a peça

**Rode a busca e cole o resultado**, sempre:

```bash
npx hyperframes catalog --query "<o efeito em uma frase>"
```

A busca semântica faz um download único de 33 MB, já autorizado: use sempre
`--on-device --yes`.

Depois aplique a regra de repintar antes de desenhar (`references/fabrica-regras.md`, regra 3).

Peça desenhada do zero nasce dentro do projeto, porque nasce amarrada naquele
estilo. Se a mesma peça for pedida num segundo projeto, aí sim ela é
generalizada, sai o que era estilo, fica o que era forma, e sobe para
`primitivas.js` da skill. Nunca antes do segundo pedido.

## 4. Acaba

Só se o `estilo.md` do projeto pedir acabamento. Grão, vinheta, sombra de
contato, textura de papel. É o passo que separa peça de vídeo de print de página
web, e as peças já estão no catálogo:

```bash
npx hyperframes add grain-overlay
npx hyperframes add vignette
```

**A vinheta vai abaixo do conteúdo, o grão vai acima.** Invertido, o `check`
reprova todos os textos da composição. Os detalhes, os valores medidos e as
quatro armadilhas do acabamento estão em `fabrica-acabamento.md`. **Leia antes de colar
o primeiro snippet**, porque três das quatro custam um render cada.

Interface de produto e print de tela **pioram** com grão. Nesse caso escreva no
`estilo.md` que o projeto dispensa, e por quê.

## 5. Confere

```bash
npx hyperframes lint .
npx hyperframes check .
npx hyperframes snapshot --at <tempos>
```

E as duas medições que o `check` não faz:

```bash
python3 <skill>/scripts/medir_ritmo.py renders/<insert>.mp4
python3 <skill>/scripts/medir_quadro.py renders/<insert>.mp4 --em <tempo>
python3 <skill>/scripts/verificar_acentos.py inserts/ --recursivo
```

**O de acentos roda ANTES de renderizar**, porque o conserto é no HTML e cada
render custa. Ele lê só o `<body>`, ignora `<script>`, `<style>` e o `<title>`,
e separa palavra que sempre leva acento de palavra ambígua, que vira aviso.

O `medir_ritmo.py` é o que pega tela morta, que é o defeito mais provável e o
mais invisível: nenhum dos quatro verificadores do HyperFrames reclama de um
quadro parado. Os limites saem das referências que a pessoa escolheu, ver
`fabrica-numeros.md`.

Prints de prova em pelo menos três momentos: a abertura, o movimento principal e
a sustentação final. **Olhe os prints.** Gerar sem olhar não conta.

Erro é consertado antes de seguir. Nunca encurte a duração pedida para esconder
defeito.

Antes de marcar qualquer atributo de exceção, leia `fabrica-armadilhas.md`.

## 6. Renderiza

Só depois da checagem passar.

```bash
npx hyperframes render . -q high --fps 30 --workers 2 -o ./renders/<nome>.mp4
```

Verifique que o arquivo existe, não está vazio e tem a duração pedida. Escreva a
linha no `MANIFESTO.md`.

## O laço de revisão

Uma arte quase nunca sai certa de primeira, e tentar acertar de primeira é o
jeito lento de fazer.

1. monta a v1 e renderiza
2. tira os prints
3. marca **no print** o que está errado, com palavras, não com adjetivos
4. corrige só aquilo e refaz

Cada volta custa segundos de render, então três ou quatro voltas saem mais
rápido que uma tentativa de acerto perfeito. O revelador móvel levou quatro.
