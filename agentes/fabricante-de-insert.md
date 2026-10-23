# Brief do fabricante de insert (molde)

O orquestrador copia este arquivo para `<pasta>/fabrica/BRIEF-AGENTES.md`,
preenche a seção **O projeto** e despacha um subagente por grupo de inserts com:

> Leia `<pasta>/fabrica/BRIEF-AGENTES.md` inteiro e construa os inserts
> `<nomes>`. Não mande nada para a pessoa que pediu o vídeo.

Tudo abaixo de "Regras de produção" vale para qualquer projeto e não se edita.

---

## O projeto  ← o orquestrador preenche

- **O anúncio em duas frases:** <tema, para quem, o que quem fala diz>
- **Pasta da fábrica:** `<pasta>/fabrica/`
- **Estilo:** `fabrica/estilo.md` (obrigatório ler). Referências da pessoa:
  `fabrica/referencias/` (vídeos de referência, folhas de contato, PESQUISA.md).
- **Pilotos aprovados (copie o jeito deles):**
  `fabrica/inserts/<piloto-1>/index.html` e `fabrica/inserts/<piloto-2>/index.html`.
  O que eles fazem que os outros devem repetir: <ex.: o apresentador encolhendo da
  tela cheia para um cartão com clipPath, cursor que mira o alvo, contorno
  laranja desenhado com strokeDashoffset>.
- **Reprovado (não fazer):** <ex.: mesa verde, janela de Windows 95, serifada creme>.
- **Material no banco** (origem em `banco/registro.md`): <prints, gravações,
  logos, slides, filmagem f<nome>.mp4 de quem fala>.
- **Grafia da campanha:** <ex.: "IA" sem pontos; taste-skill, Claude, ChatGPT>.
- **Seus inserts:** a linha de cada um em `<pasta>/PLANO.md` e em `<pasta>/fabrica/partituras.txt`.

## Regras de produção

### Antes de construir

1. Leia, da skill `~/.claude/skills/time-de-edicao-de-video/`:
   `references/fabrica-regras.md` (primeiro), `references/fabrica-ciclo.md`,
   `references/fabrica-armadilhas.md`,
   `references/fabrica-numeros.md`, `references/fabrica-acabamento.md`,
   `references/fabrica-catalogo.md` e `assets/cenas/README.md`.
2. Leia `<pasta>/fabrica/estilo.md`, a linha do seu insert em `<pasta>/PLANO.md` e a dele no
   `partituras.txt` (`nome|duração|janela|palavra@segundo`).
3. Abra os pilotos aprovados e as referências. Se precisar de mais detalhe de
   uma referência: `TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/folha_de_contato.py <video> -o <png> --quadros 16`.

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

**Orçamento de tempo:** cerca de 20 minutos por insert, do init ao render. Uma
volta de revisão em cima do snapshot, não três. Passou de 30 minutos num
insert, entregue o que tem e liste no relatório o que ficou abaixo do ideal: o
orquestrador decide se vale outra volta.

### Construir

- Criar o insert (no Windows, `python` no lugar de `python3`):
  `TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/novo_projeto.py <pasta>/fabrica --insert <nome>`.
  Ele roda o init com as três flags, copia fontes, gsap, base.css e
  primitivas.js para dentro do insert e apaga o AGENTS.md. **Nunca use
  `--recomecar`.**
- 30 fps, `data-duration` com duas casas, igual à duração da partitura. Tamanho
  pelo formato do insert no `janelas.json`: `tela_cheia`, `moldura`, vazados e
  react em **1080x1920**; `dividida_foco_original` em **1080x716** e
  `dividida_foco_insert` em **1080x1200** (o render corta o que passar disso:
  uma arte 1080x1920 numa dividida perdia 63% da altura). Tela dividida feita
  DENTRO da arte (material em cima, filmagem embaixo) é `tela_cheia`.
- **Cada elemento entra no tempo da palavra dita** (partitura). A transcrição
  escreve errado ("TextSkill", "Cloud", "IA"): na tela, a grafia da campanha.
- **Busca no catálogo em inglês antes de desenhar**, e cite o resultado no
  relatório: `npx hyperframes catalog --query "<efeito em inglês>" --on-device --yes`.
  `spain-map` no resultado é sintoma de query em português.
- **Primeiro quadro já cheio. A tela nunca para.** Câmera em pernas
  encadeadas, palavra entrando, cursor, cartão respirando. Deriva lenta única
  não conta.
- No máximo 6 elementos por quadro. Pouca palavra, grande, legível no tempo de
  tela. Nunca sigla sozinha numa linha.
- **Material real legível no tamanho em que aparece.** Print pequeno em cartão
  ficou "muito ruim": aí vale vetor desenhado. Post de terceiro: usuário oculto.
- **Rosto do apresentador:** use a filmagem `banco/filmagem/f<nome>.mp4`, que começa
  exatamente no início da sua janela, com
  `data-start="0" data-duration="<duração>" data-media-start="0" muted playsinline`,
  sem acelerar, cortar ou deslocar (senão a boca não bate). Quadro congelado e
  olho arregalado foram reprovados.
- Toda mídia nova num `<video>`: recodificada com `-g 30 -keyint_min 30`
  (senão "sparse keyframes" e o vídeo congela). Imagem de vídeo HDR: JPG ou
  bt709. Fonte "Helvetica Neue" no CSS sai em Inter: declare `@font-face` local.
- Insert de tela cheia sem o apresentador: nada essencial abaixo de y 1540 (a legenda
  vai ali depois), salvo quando a arte escreve a fala.
- Não invente número, preço ou data.

### Conferir (todos obrigatórios, nesta ordem)

Caminhos sempre absolutos: a pasta de trabalho volta ao início a cada chamada.
Render e check com `timeout: 600000` na chamada do Bash.

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/verificar_acentos.py "<pasta>/fabrica/inserts/<nome>" --recursivo
cd "<pasta>/fabrica/inserts/<nome>" && npx hyperframes check .
cd "<pasta>/fabrica/inserts/<nome>" && npx hyperframes snapshot --at <5 tempos>
```

Olhe os snapshots. Compare com os pilotos: mesma família, sem ser igual. Pelo
menos uma volta de revisão em cima do print.

### Renderizar, em primeiro plano

```bash
cd "<pasta>/fabrica/inserts/<nome>" && npx hyperframes render . -q high --fps 30 --workers 2 -o "<pasta>/fabrica/renders/<nome>.mp4"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/medir_ritmo.py "<pasta>/fabrica/renders/<nome>.mp4"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/medir_quadro.py "<pasta>/fabrica/renders/<nome>.mp4" --em <t>
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/folha_de_contato.py "<pasta>/fabrica/renders/<nome>.mp4" -o "<pasta>/fabrica/renders/folha-<nome>.png" --quadros 12
```

Duração conferida com ffprobe (±1 quadro). `medir_ritmo.py` reprovou: o
conserto quase nunca é acelerar as tweens, é continuar entrando coisa.

### Não fazer

- Não mande nada para a pessoa que pediu o vídeo e não fale com ela.
- Não mexa em `<pasta>/plano.json`, `<pasta>/PLANO.md`, `estilo.md`, `base.css`,
  `janelas.json`, `partituras.txt`, nos pilotos nem nos inserts dos outros agentes.
- Não rode render em segundo plano.

Acrescente a linha de cada insert seu no `MANIFESTO.md` (arquivo, duração,
janela, material). Material novo: uma linha em `banco/registro.md` com a origem.

## Relatório final (curto)

Para cada insert: caminho do render, duração medida, resultado do
`medir_ritmo.py`, o que a busca no catálogo trouxe e a decisão, o conceito em
duas frases, o material real usado (e de onde veio), o caminho da folha de
contato que você olhou, e o que ficou abaixo do ideal.
