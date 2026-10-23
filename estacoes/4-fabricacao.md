# Etapa 4. Fabricação dos inserts

Todo comando começa com o prefixo abaixo, que acha a skill e escolhe o Python
(`python3` no Mac e no Linux, `python` no Windows, onde `python3` pode abrir a
Microsoft Store):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python;
```

Um insert é a arte que entra no lugar do rosto (ou junto dele) enquanto a
pessoa fala. Cada um é um projeto HyperFrames em `fabrica/inserts/<nome>/`, renderizado
em `fabrica/renders/<nome>.mp4`, 1080x1920, 30 fps, mudo.

## 4.1 Preparar

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/preparar_fabrica.py --pasta "<pasta>"
```

Deixa pronto, lendo `fabrica/janelas.json`:
- `base/final-sem-insert.mp4`: o corte + 1,3x em resolução cheia;
- `fabrica/banco/filmagem/f<nome>.mp4` para cada janela com `"filmagem": true`:
  o trecho exato, mudo, com keyframe a cada 30 quadros;
- `fabrica/partituras.txt`: `nome|duração|janela|palavra@segundo`, com o tempo
  relativo ao início do insert, transcrito do vídeo **final** (do bruto, dois
  inserts de um anúncio saíram 0,8 s atrasados).

Mudou o corte depois? `--refazer-base`.

## 4.2 O brief

Copie `agentes/fabricante-de-insert.md` para `fabrica/BRIEF-AGENTES.md` e
preencha a parte do projeto: o anúncio em duas frases, onde está o estilo, os
pilotos aprovados (caminho do `index.html` de cada um) e o que eles fazem que
os outros devem copiar, o que foi reprovado, o material do banco, e a linha do
PLANO de cada insert. É o único contexto que o agente tem.

## 4.3 Despachar

Subagentes em paralelo, **todos na mesma mensagem**, com **1 ou 2 inserts
cada** (até 8 agentes): a série sai no tempo do insert mais lento, não na soma.
Numa validação, dois agentes com 2 inserts cada levaram 13 min e 2 h; o
de 2 h estava travado num comando. Agrupe no mesmo agente só os inserts que
dependem um do outro. O prompt de cada um:

> Leia `<pasta>/fabrica/BRIEF-AGENTES.md` inteiro e construa os inserts
> `<nomes>`. Não mande nada para a pessoa que pediu o vídeo.

Inserts que dependem um do outro (o segundo abre com o fim do primeiro) vão
para o mesmo agente. Você não refaz o que delegou; espera o relatório.

Se a sessão cair no meio: o `MANIFESTO.md` lista o que ficou pronto. Retome só
o que falta (num mesmo dia, os agentes em segundo plano morreram duas vezes
com a queda da sessão; o que estava em `renders/` foi aproveitado).

## 4.4 Conferir cada insert antes de mandar

Para cada render que voltou:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/folha_de_contato.py "<pasta>/fabrica/renders/<nome>.mp4" -o "<pasta>/fabrica/renders/folha-<nome>.png" --quadros 12
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/medir_ritmo.py "<pasta>/fabrica/renders/<nome>.mp4"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/verificar_acentos.py "<pasta>/fabrica/inserts/<nome>" --recursivo
```

Olhe a folha. Pergunte a si mesmo o que a pessoa perguntaria:
- dá para ler no tempo de tela?
- a primeira tela já está cheia e a tela nunca para?
- o rosto de quem fala, se aparece, está em movimento e com olhar normal?
- o material real está legível no tamanho em que aparece?
- cada palavra entra quando é dita (compare com a partitura)?
- parece com os pilotos aprovados, sem ser igual aos outros inserts?

Defeito: devolva ao agente com o que mudar, ou conserte você. Depois:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/com_voz.py --pasta "<pasta>" --todos
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/medir_serie.py "<pasta>/fabrica/renders/"
```

## 4.5 Mandar para a pessoa

Cada insert separado, na ordem do vídeo, um embaixo do outro: a frase do trecho
e o vídeo com voz logo abaixo. A pessoa conta pela ordem em que recebeu ("o
insert 2" era o 03 do plano): numere pela ordem de envio e diga o nome do arquivo.

Pedido de mudança num insert: ajuste em `fabrica/inserts/<nome>/index.html` e
renderize de novo para `fabrica/renders/`. A narração mudou de tempo? O
`retimar.py` desloca os disparos e preserva a duração de cada gesto:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/retimar.py "<pasta>/fabrica/inserts/<nome>/index.html" --inicio 0 --de 0,3.32,5.96 --para 0,3.10,5.61 --aplicar
```

Tabela em HTML que o `retimar.py` não alcança: retime o próprio MP4 por trechos
(`setpts`), como já foi feito num insert de tabela.

## 4.6 Portão 4

Nada entra no vídeo antes do ok da pessoa nos inserts. Respostas comuns:
"Aprovados, pode montar os inserts no vídeo e me mandar o preview" (siga para a
etapa 5), ou o número e a mudança ("no insert 2 em 0:03 tem um frame do
apresentador com o olho esbugalhado, muda isso"). A pessoa pode liberar antes
("vai montando"):
aí siga e anote em `DECISOES.md`.

## 4.7 O que os agentes não podem esquecer (também está no brief)

As regras completas da fabricação (catálogo em três camadas, material real,
os cinco pisos da série, critérios de pronto): `references/fabrica-regras.md`.


- `novo_projeto.py <fabrica> --insert <nome>` cria o insert com as três flags do
  init e copia fontes, gsap e base.css para dentro dele. Nunca `--recomecar`.
- Busca no catálogo **em inglês**, resultado citado, antes de desenhar:
  `npx hyperframes catalog --query "<efeito em inglês>" --on-device --yes`
  (`spain-map` no resultado é sintoma de query em português).
- Primeiro quadro cheio; a tela nunca para (câmera em pernas encadeadas, não
  deriva lenta); no máximo 6 elementos por quadro.
- Mídia em `<video>` dentro do insert com `-g 30 -keyint_min 30`.
- Filmagem embutida entra sem acelerar, cortar nem deslocar.
- `hyperframes check` sem erro, snapshot olhado, render **em primeiro plano**:
  `npx hyperframes render . -q high --fps 30 --workers 2 -o ../../renders/<nome>.mp4`.
- Material novo em `banco/registro.md`; linha no `MANIFESTO.md`.
- Armadilhas do HyperFrames: `references/fabrica-armadilhas.md`.
