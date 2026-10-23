# Etapa 0. Preparo

Todo comando começa com o prefixo abaixo, que acha a skill e escolhe o Python
(`python3` no Mac e no Linux, `python` no Windows, onde `python3` pode abrir a
Microsoft Store):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python;
```

## 0.1 Pré-flight

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/preflight.py
```

`[FALTA]` trava a etapa; `[opcional]` não. Para o que faltar: mostre a lista
com o comando de cada item, peça aprovação e instale um por vez, na ordem de
`references/instalacao.md`. O que pede senha ou janela do sistema (sudo,
xcode-select, controle de conta do Windows), a pessoa roda. No Windows, quem
instala pelo `winget` precisa fechar e abrir o Claude antes de conferir de novo.

## 0.2 O que pedir à pessoa (e o que ela costuma mandar sem pedir)

| Item | Onde costuma estar |
|---|---|
| bruto | uma pasta de downloads ou do projeto (ex.: `~/Videos/meu-anuncio/bruto.mp4`) |
| roteiro | um documento de texto (Google Docs, Word, bloco de notas). Guarde o texto em `script.txt` na pasta do vídeo; documento com abas ou sem acesso: peça que a pessoa cole o texto |
| objetivo | captação de leads, aquecimento, vendas: muda o julgamento do corte e do CTA |
| pedidos de insert | "insert N: quando ele fala '...' coloca X em moldura" |
| referências de estética | links de vídeos de motion, bancos de referência |
| destino no Drive | só na entrega; pergunte lá |

**Material já editado não é bruto.** Num anúncio aprovado, o arquivo tinha 5 edições antigas
queimadas: cada uma foi medida quadro a quadro (`MONTAGEM.md`) e
coberta por insert novo. Pergunte se o arquivo é bruto quando houver dúvida.

**Legenda queimada no material** impede a legenda cinematográfica. Peça o
arquivo sem legenda antes de começar.

## 0.3 Pasta do vídeo

```
~/Videos/<cliente-ou-contexto>/<video>/
  bruto-montado/     só quando há emenda de dois vídeos (MONTAGEM.md, trechos.json)
  analise/           palavras, silêncios, transcrição, máscara
  plano.json         a edição inteira, em tempo do ORIGINAL
  previews/          os renders de cada portão (720p)
  PLANO.md           o plano de inserts (portão 2)
  fabrica/           estilo.md, janelas.json, partituras, inserts/, renders/, banco/
  base/              o corte + 1,3x em resolução cheia (a fabrica tira tudo dele)
  legenda/           legenda.json, composição, .work/
  final/             o legendado em 1080 e a versão leve em 720p
  DECISOES.md        o que você decidiu quando a pessoa liberou seguir sem aprovação
```

Exemplo: `~/Videos/meu-anuncio/`. Ao repetir um processo já feito ("o mesmo do
anúncio anterior"), **abra a pasta irmã e copie o que a pessoa decidiu lá**
(CTA, estética, trilho, inserts reaproveitáveis), em vez de redecidir.

## 0.4 Bruto padronizado (sempre, mesmo com um vídeo só)

O render recusa tudo que não seja 1080x1920, e a voz tem que estar em -24 LUFS.
Confira e padronize **antes** da análise (bruto 4K ou `.mov` com rotação só
falharia na etapa 1, depois dos cortes):

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate:stream_side_data=rotation -of default=nw=1 "<bruto>"
```

Vídeo único: `trechos.json` com um trecho só.

```json
[{"arquivo": "~/Videos/meu-anuncio/bruto.mp4", "de": 0.0, "ate": null, "fala": "vídeo inteiro"}]
```

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/montar_bruto.py --pasta "<pasta>" --trechos "<pasta>/trechos.json"
```

Sai `bruto-montado/montado.mp4` (1080x1920, voz em -24 LUFS, fps do original)
e o `MONTAGEM.md`. **O montado é o "bruto" de todas as etapas seguintes.**

## 0.5 Anúncio feito de dois vídeos (o corpo de um + o CTA de outro)

A pessoa manda os pontos de corte assim: "do início até '...antes do dia da
abertura,' (~197,6 s)" e "do vídeo do CTA, de 'Nossa oferta...' até
'Vamos nessa!'". Esses tempos vêm de transcrição que deriva.

1. Confira cada ponto de emenda com transcrição isolada e com os silêncios:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/transcrever.py "<arquivo>" --de 190 --ate 200 --isolado
ffmpeg -nostdin -hide_banner -ss 190 -t 10 -i "<arquivo>" -af silencedetect=n=-40dB:d=0.1 -f null - 2>&1 | grep silence
```

   Com `-ss` antes do `-i`, os tempos do `silencedetect` saem relativos ao
   trecho (0,676 é 190,676): some o início. Corte no meio do silêncio, nunca em
   cima da última palavra. Take repetido
   que a pessoa listou ("gravou DUAS vezes, usar só o segundo"): confirme qual é o
   mais limpo ouvindo a transcrição isolada dos dois.

2. Escreva `trechos.json` (`"ate": null` vai até o fim do arquivo) e monte:

```json
[{"arquivo": "~/Videos/meu-anuncio/bruto.mp4", "de": 0.0, "ate": 197.6667,
  "fala": "do início até '...antes do dia da abertura,'"},
 {"arquivo": "~/Videos/meu-anuncio/cta.mp4", "de": 130.70, "ate": null,
  "fala": "'Nossa oferta é diferente...' até 'Vamos nessa!'"}]
```

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/montar_bruto.py --pasta "<pasta>" --trechos "<pasta>/trechos.json" --estimar
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/montar_bruto.py --pasta "<pasta>" --trechos "<pasta>/trechos.json"
```

   Sai `bruto-montado/montado.mp4` e o `MONTAGEM.md` com o offset de cada
   trecho. O montado é o "bruto" das etapas seguintes.

3. **O CTA entra com a imagem**, não só o áudio sobre a imagem anterior: num
   anúncio aprovado, só o áudio foi reprovado como "meio nada a ver". A troca de vídeo (cabelo diferente,
   enquadramento diferente) ganha whoosh e efeito de montagem na etapa 5, e às
   vezes uma tela escura com o lettering da fala até a frase seguinte.

4. O mesmo trecho de CTA já foi usado em outro anúncio? Os inserts de lá servem
   aqui, deslocados pelo offset (o `MONTAGEM.md` dos dois diz quanto). Insert
   com a filmagem do apresentador embutida precisa de re-render para a boca bater.

5. Áudio: os dois trechos vão para -24 LUFS por ganho fixo. **Sem denoise e
   sem compressor**: nas vezes em que trataram o áudio ele piorou. Vale pôr
   no roteiro de gravação o aviso em caixa alta de gravar o CTA no mesmo
   microfone e ambiente.

Vídeo de depoimento de outra pessoa (um aluno, num anúncio aprovado): o
apresentador termina a frase sobre o aluno e só então entra o vídeo do aluno,
com a voz dele. É um terceiro trecho no `trechos.json`.
