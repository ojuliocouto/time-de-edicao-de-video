# Etapa 2. Plano de inserts (até o portão 2)

Todo comando começa com o prefixo abaixo, que acha a skill e escolhe o Python
(`python3` no Mac e no Linux, `python` no Windows, onde `python3` pode abrir a
Microsoft Store):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python;
```

O plano decide a série inteira antes da primeira arte: o que cada insert
mostra, em que formato, com que material e com que mecanismo. Medido em doze
inserts entregues antes desta regra: dez nunca cortavam e todos se pareciam.
**O formato do plano produzia o defeito.** Método completo:
`references/fabrica-plano.md`.

## 2.1 Antes de escrever

1. **Transcrição do vídeo final** (o preview aprovado), que é o relógio do plano:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/transcrever.py "<pasta>/previews/02-velocidade.mp4" --json "<pasta>/analise/preview-palavras.json"
```

2. **Folha de contato** do preview, um quadro a cada ~2 s em grade de 8 colunas
   (`--quadros` = duração ÷ 2), para ver o que a câmera mostra:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/folha_de_contato.py "<pasta>/previews/02-velocidade.mp4" -o "<pasta>/analise/folha.png" --quadros 80 --colunas 8
```

3. Marque três coisas no tempo do final:
   - **onde quem fala aponta** ("esse cara aqui", "isso aqui"): o insert mostra
     exatamente aquilo, com material real buscado na internet;
   - **onde quem fala desenha ou risca na tela** (um número, uma seta, uma
     palavra escrita à mão): proteja, nenhum motion por cima;
   - **o que já vem queimado no arquivo** (caixinha do Instagram, edição
     antiga): cubra ou mantenha, pergunte.

## 2.2 Os pedidos da pessoa

O pedido costuma vir assim: *"insert 3: quando ele fala 'transformaria num time
que edita vídeos 100% com IA' inserir em tela cheia essas palavras sendo
escritas e circula o 100% com IA."* Entra **como foi escrito**: o formato, o
texto e o momento são de quem pediu. Quando vier "me dá a ideia", você propõe.

Material que chega por link (galeria de imagens, Drive, rede social):
- galeria ou página com o vídeo: baixe o vídeo da página;
- reels e posts: `yt-dlp` sem login; thumb do YouTube em
  `https://i.ytimg.com/vi/<id>/maxresdefault.jpg`;
- vídeo de referência de motion: baixe para `fabrica/referencias/`.

## 2.3 As regras do que propor

Cada linha tem a reprovação de origem em `references/licoes.md`.

**Densidade.** Meta de um insert a cada 10 s do vídeo final; o pedido costuma
ser "bastante inserts". Trecho longo de rosto sem nada: proponha, e pergunte se
deve ficar no rosto.

**Abertura.** O gancho inteiro na tela antes de 1 s e a tela nunca para
(número contando, texto digitado com cursor, algo sempre se mexendo). Duas
aberturas aprovadas:
- vídeo escurecido (camada preta a ~58%) com a frase de gancho centralizada e
  o trecho de destaque grande na cor da marca;
- quando quem fala aponta para uma tela: texto menor no terço de baixo e a filmagem
  quase sem escurecer, e o insert dura **só a frase do gancho**.
Texto fixo de abertura ("COMUNICADO IMPORTANTE", "NÃO FAZ SENTIDO..."): gere 3
a 6 opções de design em PNG e deixe a pessoa escolher. **Nunca** slam tipográfico
(palavras gigantes batendo, flash, glitch): reprovado mesmo quando o pedido foi
"efeito duro e chamativo". A abertura com o rosto de quem fala é uma opção válida.

**Material real antes de grafismo.**
- Fala sobre o que dizem na internet: prints e thumbs reais pipocando, usuário
  oculto (nome, foto, @). Quando a pessoa preferir não arriscar, posts fictícios com
  usuário inventado.
- Fala sobre produto, página, notícia, repositório: print ou gravação real
  (`capturar_pagina.py`). Notícia: "só pega os prints e joga na tela", sem
  rajada, com tempo para escanear; empilhados dão ideia de volume.
- Prova social: o vídeo ou print real do aluno; mensagem do grupo só com
  autorização.
- Material real só entra se ficar **legível no tamanho em que aparece**: print
  pequeno dentro de cartão ficou "muito ruim"; ali vale vetor desenhado.
- Simulação que parece falsa (chat do Claude feito em motion) foi "meio
  mentiroso": use a gravação real.

**Formatos** (`references/edicao-inserts.md`, os 8 nomes exatos):
- `moldura` é a preferida para vídeo e arte explicativa;
- `tela_cheia` para texto de impacto sobre fundo escuro;
- para quem fala aparecer junto: `vazado_pequeno` (o mais usado), `react_miniatura`
  ou `dividida_foco_original`. `dividida_foco_insert` cortou a cabeça do
  apresentador num enquadramento fechado: confira antes;
- **não faça todos no mesmo formato** (reprovação real: "não precisa fazer
  todos em tela dividida");
- gravação de tela vertical sem contexto: moldura horizontal com a tela inteira
  e o espaço livre para uma legenda de impacto.

**Leitura.** Informação que cabe no tempo de tela; pouco texto, grande. Muito
texto: versão reduzida ou mais tempo. Sigla nunca sozinha numa linha.

**Emendas.** Rosto voltando por menos de 1 s entre dois inserts parece falha:
encoste os dois (estique um ou antecipe o outro) e avise.

**Rosto dentro de arte.** Trecho curto do próprio bruto em movimento, de
preferência sorrindo (folha de contato a cada 2 s acha o sorriso). Nunca quadro
congelado, nunca olho arregalado.

**Reaproveitamento.** Mesmo áudio de CTA em outro anúncio: os inserts de lá
servem (botão, data, grupo). Pergunte; costuma ser aprovado.

**Números e nomes.** Nunca invente número, preço ou data. Número oficial só com
fonte. Grafia da campanha no `estilo.md` (ex.: "IA" sem pontos).

## 2.4 O que escrever

`PLANO.md`, numerado **na ordem em que aparece no vídeo**:

| nº | janela (final) | frase | formato | o que mostra | material | dispositivo e fundo |
|---|---|---|---|---|---|---|
| 01 | 0,00 a 5,02 | "como eu tiro a cara de IA..." | tela_cheia | filmagem escurecida + gancho | filmagem | texto palavra a palavra, escuro |

Mais: os cinco pisos da série (`references/fabrica-plano.md`), o resumo do
estilo e as **decisões em aberto numeradas**.

`fabrica/janelas.json`, a fonte única das janelas (tempo do FINAL), que a
fabricação, a montagem e o `com_voz.py` leem:

```json
[{"nome": "01-abertura", "de": 0.00, "ate": 5.02, "formato": "tela_cheia", "filmagem": true, "motivo": "gancho"},
 {"nome": "16-botao", "arquivo": "/caminho/outro-anuncio/fabrica/renders/16-botao.mp4",
  "de_orig": 211.99, "ate_orig": 221.43, "formato": "vazado_pequeno", "origem_ini": 0.62}]
```

`"filmagem": true` quando a arte usa a filmagem de quem fala dentro dela. Insert
reaproveitado de outro projeto entra com `arquivo` (caminho absoluto; no Windows
no formato `C:/Users/...`) e tempo do ORIGINAL.

## 2.5 Portão 2

Mande o plano **escrito na mensagem**, não só o arquivo: a tabela resumida e as
decisões numeradas, para a resposta vir como "1. ok, 2. pode reaproveitar...".
Nada é produzido antes do "aprovado".

A pessoa liberou seguir sem aprovação ("faz o plano e mete marcha")? Siga, e
registre em `DECISOES.md` cada decisão que ela teria tomado, com o motivo.
