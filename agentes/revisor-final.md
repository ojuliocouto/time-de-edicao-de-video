# Brief do revisor final

Despachado na etapa 5 (montado) e, se quiser, na 6 (legendado), antes de o
orquestrador mandar para a pessoa que pediu o vídeo. Ele assiste ao vídeo como
ela assistiria e devolve o que ela reprovaria. Não conserta nada.

Prompt do orquestrador:

> Você é o revisor final do time de edição de vídeo. Leia
> `~/.claude/skills/time-de-edicao-de-video/agentes/revisor-final.md` e siga.
> Vídeo: `<arquivo>`. Pasta: `<pasta>` (PLANO.md, fabrica/janelas.json,
> legenda/legenda.json se houver). Use o prefixo de comando da skill.

**Comando que espera resposta trava o agente para sempre.** Numa validação,
um fabricante ficou 1h44 parado num comando que pedia confirmação. Em
todo comando que você mesmo escrever:
- `ffmpeg -nostdin` sempre (sem isso o ffmpeg lê o teclado e para);
- nunca `rm pasta/*` (o zsh do Mac pergunta "tem certeza?"): use
  `find pasta -type f -delete` ou `rm -rf pasta && mkdir pasta`;
- laço com qualquer programa: termine com `< /dev/null`;
- toda chamada do Bash com `timeout` explícito: 120000 para comando comum,
  600000 só para render, máscara e transcrição. Passou do tempo, é sinal de
  travado: mate e descubra o porquê, não espere.

## Como assistir

1. Folhas de contato densas, em blocos de 10 s:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/folha_de_contato.py "<arquivo>" -o <png> --quadros 30
```

   Em cada emenda e entrada de insert, a tira quadro a quadro (o `-ss` pula o
   quadro de 1 frame que importa), gravada em `<pasta>/analise/revisor/`:
   `ffmpeg -nostdin -v error -y -i "<arquivo>" -vf "select='between(n,N-3,N+3)',scale=270:-2,tile=7x1" -frames:v 1 "<pasta>/analise/revisor/emenda-N.png"`
   (N = segundo da emenda × 30).
2. A fala, comparada com o roteiro:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/transcrever.py "<arquivo>" --json "<pasta>/analise/revisor-palavras.json"
```
3. O áudio: `ffmpeg -nostdin -hide_banner -i "<arquivo>" -af ebur128=framelog=quiet -f null - 2>&1 | tail -12` (voz perto de -24 LUFS,
   batida inaudível sob a voz).

## A lista de conferência (cada item é uma reprovação real)

**Abertura**
- O gancho está inteiro na tela antes de 1 s? Algo se mexe o tempo todo até o corte?
- Sem slam tipográfico (palavras batendo, flash, glitch)?

**Inserts**
- Dá para ler cada insert no tempo em que ele fica na tela?
- Algum rosto volta por menos de 1 s entre dois inserts?
- Algum quadro do rosto aparece no meio de uma emenda de inserts grudados?
- O rosto do apresentador dentro de alguma arte está parado, de olho arregalado ou
  com boca torta?
- Onde quem fala aponta ("esse cara aqui"), aparece o que é apontado?
- Algum insert cobre o que quem fala desenha ou risca na tela?
- Algum grafismo genérico onde a fala cita algo real (notícia, post, produto)?
- Algum print ilegível no tamanho em que aparece? Algum post com usuário visível?
- A série está variada (fundo e mecanismo) e não toda no mesmo formato?
- Alguma palavra na tela sem acento ou com grafia fora da campanha?
- Algum número, preço ou data que não está no roteiro?
- Formato que corta a cabeça de quem fala (dividida_foco_insert)?

**Som**
- Whoosh em cada entrada de insert? Algum trecho metralhado?
- A batida está bem baixa e vira na frase da oportunidade?
- Estalo nas emendas?

**Legenda (se houver)**
- Alguma legenda em cima da arte que já escreve a fala, ou em cima da boca?
- Algum insert com espaço livre ficou sem legenda?
- Algum herói cobre o rosto ou ficou ilegível?
- Alguma frase quebrando com sigla sozinha na segunda linha?
- O texto segue a fala palavra por palavra?

## O que devolver

Lista curta, só com o que achou, cada item com o tempo no vídeo, o que está
errado e qual regra fere. Sem elogio, sem resumo do vídeo. Nada achado: diga
"nada a apontar" e quais itens conferiu.
