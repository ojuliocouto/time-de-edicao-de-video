# Regras da fabricação de insert

Vindas da antiga skill `fabrica-de-insert`, que esta absorveu. Valem para você
e para todo fabricante. Os scripts citados ficam em
`~/.claude/skills/time-de-edicao-de-video/scripts/`; os modos "pedido",
"roteiro" e "áudio" dela viraram as etapas 2 a 4 desta skill.

## As regras que não se negociam

**1. A busca no catálogo é obrigatória e o resultado vai colado na conversa**,
mesmo quando a decisão final for desenhar do zero.

```bash
npx hyperframes catalog --query "<the effect in one English sentence>" --on-device --yes
```

O `--on-device --yes` autoriza um download único de 33 MB do modelo de busca,
que fica na máquina. Sem ele a busca cai no casamento de palavra e presta menos.

### A QUERY VAI EM INGLÊS. SEMPRE.

Esta skill é em português, o catálogo não. O modelo de busca é treinado em
inglês e **devolve lixo em português**, sem avisar que está devolvendo lixo.
Medido:

| Query | Cinco primeiros |
| --- | --- |
| `"comparacao lado a lado de dois lados identicos"` | lower third de podcast, máscara de visão computacional, letras descendo, **mapa da Espanha** |
| `"side by side comparison of two identical panels"` | `comparison-split`, `mk-clone-wall-transition`, `type-match-cut`, `before-after-wipe` |

Mesma intenção. Um devolve ruído, o outro devolve exatamente as peças de
comparação que existem.

Sintoma de que você escreveu em português: **`spain-map` no resultado.** Ele
apareceu em cinco de seis buscas em português e em nenhuma em inglês, porque o
modelo reage à semelhança da língua e não ao conteúdo. Viu `spain-map` num
pedido que não é mapa, reescreva em inglês e rode de novo.

Sem a busca, "não existe pronto" vira palavra, e palavra não se audita. E vale
também antes de sair procurando tutorial fora: na primeira caçada aos quatro
efeitos que faltavam, **os quatro já estavam no catálogo**.

**2. Coisa real antes de coisa genérica.** Quando o roteiro cita algo que existe
no mundo, a arte mostra aquilo, não um substituto que finge ser. Ordem de busca
do material, por arte:

1. arquivo do banco do projeto
2. arquivo que a pessoa mandar
3. busca na internet , **mostre o que achou e espere o ok antes de usar**
4. constrói do zero, e **avisa que caiu na construção**

Todo arquivo que entra no banco fica registrado em `banco/registro.md` com
origem e link.

**Ao gerar imagem, peça a composição, não só o assunto.** O prompt reserva a
zona vazia onde o texto vai morar. Isso resolve legibilidade no momento da
geração, e evita ter que salvar depois com caixa ou sombra atrás da tipografia:

> vertical 9:16, [CENA]: os **dois terços inferiores** têm a ação; o **terço
> superior** é quase vazio, deixando espaço negativo generoso. Sem texto.

Arquivo real ganha de arquivo gerado quando os dois existem. Acervo aberto tem a
textura e a imperfeição que a geração ainda inventa, e é de graça.

**3. Repinta antes de desenhar.**

- achou peça que serve → instala e repinta segundo o `estilo.md`
- achou peça parecida que briga com o estilo → repinta assim mesmo na primeira
  vez; se a mesma arte for pedida de novo e brigar de novo, aí desenha
- não achou nada → desenha do zero

Peça descartada por brigar com o estilo tem o motivo escrito.

**4. Nunca encurta a duração pedida para esconder defeito.**

**5. A série se planeja antes da primeira arte.** O `PLANO.md` decide, para o
conjunto: o **plano** de cada insert e onde estão os cortes, qual carrega
**material real** e qual é grafismo, qual **dispositivo** usa, e onde muda o
**registro**. Cinco pisos, e a tabela reprova antes de existir arte:

| Piso | Regra |
| --- | --- |
| corte | metade da série tem troca de plano interna |
| material real | um terço da série carrega coisa real |
| dispositivo | não repete em sequência, nem passa de um terço da série |
| plano | o tamanho de plano varia ao longo da série |
| registro | pelo menos uma virada |

Medido em doze inserts entregues em dois anúncios: **dez nunca cortam**, tudo
numa tela só, contra referências que cortam de 3 a 10 vezes. O plano antigo pedia
só campos por peça, então saíam peças independentes e parecidas. **O formato do
plano produzia o defeito.** Método em `references/fabrica-plano.md`.

E a regra 2 ganha o dente da regra 1: **a busca por material real vai colada na
conversa.** "Não achei nada real" é resultado mostrado, não pulo silencioso. Sem
isso ela apodrece: em doze inserts, nunca disparou.

```bash
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/medir_serie.py renders/
```

**6. O quadro não pode morrer.** Medido nas referências que ela escolheu, a tela
se mexe em 75% a 100% da duração, com parada máxima de 0,6 s. Nos nossos inserts
entregues, 55% a 85%, com paradas de até 2,6 s. **Era esse o "achei simples".**

```bash
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/medir_ritmo.py renders/<insert>.mp4
```

Reprovou, o conserto quase nunca é acelerar as tweens: é **continuar entrando
coisa**. Deriva lenta de câmera não resolve, foi medido e não registra. Câmera em
pernas encadeadas resolve. Números e método em `references/fabrica-numeros.md`.

## O catálogo em três camadas

| Camada | O que é | Por que guardar |
| --- | --- | --- |
| **Primitiva** | o átomo de movimento | para **reusar** |
| **Efeito** | primitiva ou combinação com intenção narrativa | para **buscar** por intenção |
| **Cena** | a montagem completa | para **lembrar** de uma combinação que funcionou |

`assets/primitivas.js` traz 18 funções prontas, cada uma com a origem no comentário.
O `novo_projeto.py` já copia para a fábrica e para cada insert. Cresça a partir dele.

Duas dependem de DOM próprio e não funcionam soltas: a câmera exige um elemento
`#mundo` envolvendo as cenas, e `rolaPagina` exige um contentor com overflow
hidden. Está escrito no cabeçalho do arquivo.

`assets/cenas/` traz as combinações que já funcionaram. Leia antes de montar algo do
zero: a chance de já existir uma cena parecida é alta.

Uma arte é **conteúdo × efeito**. Dez conteúdos e onze efeitos dão mais de cem
combinações sem precisar de catálogo gigante. Ver `references/fabrica-catalogo.md`.

## Ao ler um tutorial

**Extraia as primitivas, não a cena.** Liste todas que o tutorial ensina, uma
linha por mecanismo, inclusive as que não vai usar agora. Resumir a cena em vez
de listar as primitivas é o erro que faz um tutorial de quinze mecanismos render
seis.

Depois guarde a cena também, porque ela carrega a decisão de qual combinação, em
que ordem e com que tempo, e isso não sobrevive na lista de primitivas.

Tutorial ganha de referência visual sempre que os dois existirem: a referência
mostra o resultado, o tutorial mostra o mecanismo.

## Tipografia padrão

**Anton** para as palavras herói, **Inter** para o apoio. Os dois arquivos estão
em `assets/fonts/`. Copie para o projeto e embarque por `@font-face`, nunca
baixe. Só troque quando a marca exigir, e escreva o porquê no `estilo.md`.

Duas armadilhas da Anton estão em `references/fabrica-armadilhas.md`, junto com as do
verificador. **Leia antes do primeiro `check`.**

## Scripts

Nove, todos em Python 3 puro. Os de medição usam `ffmpeg`; o de transcrição
precisa de um backend de whisper e diz qual instalar se faltar; o de acentos não
precisa de nada.

```bash
# monta a pasta do projeto: estrutura, fontes, primitivas.js e estilo.md em branco
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/novo_projeto.py ~/Claude/cliente/projeto --nome "Projeto X"

# captura uma pagina em alta, para entrar no insert como material real.
# altura grande = pagina inteira, que e o que a primitiva rolaPagina desloca
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/capturar_pagina.py https://exemplo.com -o banco/pag.png --altura 3400

# folha de contato de um video: para ler o movimento de uma referencia,
# ou para conferir um insert rendido sem assistir quadro a quadro
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/folha_de_contato.py referencia.mp4 -o /tmp/folha.png --quadros 8

# REGRA 5: a tela morreu? limites calibrados nas referencias dela
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/medir_ritmo.py renders/insert.mp4

# composicao em numero: respiro, banda limpa, quantos elementos
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/medir_quadro.py renders/insert.mp4 --em 2.5

# REGRA 5: a serie inteira ficou chapada? confere contra o PLANO.md
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/medir_serie.py renders/

# MODO AUDIO: partitura palavra a palavra, com janela opcional
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/transcrever.py fala.m4a --trecho "a frase que ela quer cobrir"

# e quando a narracao OFICIAL chegar: desloca os disparos, preserva os gestos
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/retimar.py inserts/<nome>/index.html --inicio 0 \
  --de 0,3.32,5.96,10.22 --para 0,3.10,5.61,9.74 --aplicar

# o portugues da TELA: acento que faltou. O check do HyperFrames nao ve isso.
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/verificar_acentos.py inserts/ --recursivo
```

O `capturar_pagina.py` usa o Chrome que o HyperFrames já baixou. Se ele
reclamar que não achou, rode um `npx hyperframes check` uma vez.

## Criar cada insert

```bash
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/novo_projeto.py <video>/fabrica --insert <nome>
```

Roda o `hyperframes init` com as três flags que não são opcionais
(`--non-interactive`, senão trava o agente; `HYPERFRAMES_SKIP_SKILLS=1`, senão
bate no GitHub; `--resolution portrait`, senão sai deitado) e copia para dentro
do insert as fontes, o `gsap.min.js`, o `base.css` e o `primitivas.js`. **As
fontes precisam existir em dois níveis**, porque o `@font-face` resolve relativo
ao `index.html` de cada insert: sem a segunda cópia a Anton não carrega e o
render sai com a substituta, sem avisar.

Mídia do insert vai em `inserts/<nome>/assets/midia/`. O `banco/` da fábrica é
o arquivo do projeto; `assets/midia/` é o que aquela composição usa.

## Estrutura de um projeto

```
<projeto>/
  estilo.md            paleta, fontes, regras de layout
  primitivas.js        copiado pelo novo_projeto.py, cresce com o projeto
  assets/fonts/        Anton e Inter, copiadas da skill
  banco/               imagens, prints, logos, gravacoes de tela
  banco/registro.md    de onde veio cada arquivo
  inserts/<nome>/      um projeto hyperframes por arte
  renders/             os arquivos finais
  MANIFESTO.md         nome, duracao, trecho coberto, material usado
```

O `MANIFESTO.md` é a ponte futura para a skill de edição, sem que as duas
precisem se conhecer.

## Quando algo dá errado

| Sintoma | Causa provável | O que fazer em vez disso |
| --- | --- | --- |
| `check` reprova mas o print está certo | efeito legítimo brigando com o verificador | marque o atributo de exceção **no elemento mais estreito**, nunca no wrapper de cena |
| elemento some do vídeo inteiro e o `check` passa | `autoAlpha` numa morte dura | troque por `visibility` pura, e dê um `visible` explícito no tempo zero |
| texto não troca quando arrasto a timeline pra trás | `tl.call` | duas cópias empilhadas trocadas por opacidade: a primitiva `trocaJanela` |
| edição por script não pega | preview do Studio injetando ids | pare o preview antes de editar em lote |
| render falha ou trava | pouca RAM | `--workers 2` |
| peça do catálogo não encaixa no formato | container query horizontal em quadro vertical, por exemplo | descarte, escreva o motivo, e monte com as primitivas |
| busca do catálogo só devolve ruído, e `spain-map` aparece | query escrita em português | reescreva a query em inglês e rode de novo |
| grifo deixa o texto ilegível por um instante | texto claro sobre acento claro no meio da tween | duas cópias recortadas pela mesma variável, ver `fabrica-armadilhas.md` |
| a fonte some ou troca sozinha no render | `@font-face` apontando pra caminho errado | as fontes têm que estar em `assets/fonts/` do projeto, copiadas, nunca baixadas |
| `check` acusa `text_occluded` em **todos** os textos | vinheta de tela cheia acima do conteúdo | vinheta **abaixo** do conteúdo, grão acima. Atributo de exceção no oclusor não resolve |
| mexi no valor da peça do catálogo e nada mudou | o tween veio dentro de um comentário HTML | confira se o código está mesmo dentro do `<script>` |
| vinheta virou um halo escuro | os padrões da peça são para composição escura | trave `--vignette-color` em alfa baixa e `--vignette-size` alto, no CSS |
| texto passa no contraste no começo e reprova no fim | a câmera empurrou o texto pra borda escurecida pela vinheta | confira o contraste **no fim** do movimento de câmera |
| `medir_ritmo.py` reprova mesmo com câmera se mexendo | deriva lenta única, que não registra | câmera em pernas encadeadas, cada uma com começo e fim |
| a arte saiu com "voce", "operacao", "conteudo" na tela | você digitou o HTML sem acento e nenhum verificador reclamou | `verificar_acentos.py` antes de renderizar |

Cada linha tem o detalhe completo em `references/fabrica-armadilhas.md`.

**A regra que resume todas:** o `check` passar não quer dizer que está certo.
Olhe o print.

## Critérios de pronto

Os quatro primeiros são de processo. Os cinco últimos são de **resultado**, e
faltavam: dava para cumprir a lista inteira e entregar coisa crua.

1. `hyperframes check` passa sem erro
2. os prints de prova foram gerados **e olhados**
3. o material usado está registrado com origem
4. a duração do arquivo bate com a pedida
5. **`medir_ritmo.py` passa** , a tela não morre no meio
6. **o acabamento foi decidido**, usado ou dispensado com motivo no `estilo.md`
7. **no máximo 6 elementos por quadro**, conferido com `medir_quadro.py`
8. **`verificar_acentos.py` passa** , nenhuma palavra de tela sem acento
9. **a série bate com o `PLANO.md` aprovado**, conferido com `medir_serie.py`

## Decisões já tomadas

Não reabra sem motivo novo: After Effects por MCP (fora: assinatura, AE aberto),
Lottie (na gaveta: só ilustração desenhada), Higgsfield (fonte de matéria-prima,
não motor de motion), Remotion (fora: resolve o mesmo problema do HyperFrames e
custaria as 373 peças do catálogo e os verificadores).
