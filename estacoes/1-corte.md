# Etapa 1. Corte e 1,3x (até o portão 1)

Todo comando começa com o prefixo abaixo, que acha a skill e escolhe o Python
(`python3` no Mac e no Linux, `python` no Windows, onde `python3` pode abrir a
Microsoft Store):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python;
```

`<bruto>` é o `bruto-montado/montado.mp4` da etapa 0 (1080x1920, voz em -24 LUFS).

**O que sustenta tudo:** a edição inteira vive no `plano.json`, sempre em tempo
do ORIGINAL. O render parte do original e aplica o plano numa passada só. Por
isso ajuste é barato (reverter um corte com os inserts montados é uma linha) e
a imagem não degrada. Esquema: `references/edicao-plano-json.md`.

## 1.1 Medir

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY -u $TEV/scripts/analisar.py "<bruto>" --pasta "<pasta>" --contexto "Claude, IA, skill, nome de quem fala, nomes do roteiro"
```

Use `timeout: 600000` na chamada (vídeo de 3 min leva de 1 a 5 min; sem GPU,
até o tempo do vídeo). Sai `analise/palavras.json`, `silencios.json` e `transcricao.txt`. O motor de
transcrição é o melhor instalado (mlx no Mac, faster-whisper nos três,
whisper.cpp de reserva); a linha "motor de transcricao" diz qual.

Avisou que retranscreveu trecho isolado? **Leia a transcrição ali.** O
transcritor entra em loop e come fala real.

## 1.2 Pausas e velocidade

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/plano.py criar --pasta "<pasta>" --fonte "<bruto>"
```

Pausa acima de 0,15 s sai (até 0,6 s fica antes de virada de raciocínio, onde é
ritmo). Velocidade 1,3x uniforme no vídeo inteiro. Jump cut aparecendo é
aceito.

**Velocidade diferente num trecho** (já pediram 1x só na abertura de um
anúncio): a skill só faz velocidade uniforme. Avise, e se a pessoa confirmar,
emende o trecho em 1x no render do plano depois (ver `references/licoes.md`,
"Velocidade por trecho"). Tudo depois do trecho anda no tempo: refaça o que depende dele.

## 1.3 Julgar a fala

Leia `analise/transcricao.txt` **inteira** e o roteiro. Regras, exemplos e
armadilhas em `references/edicao-corte.md` (o "é" que é verbo, a repetição que é
ênfase). Ler antes de marcar.

- **Sai:** gagueira, começo falso, hesitação sonora, retomada. Da retomada fica
  a **última tentativa completa**, salvo pedido da pessoa (num anúncio aprovado
  ficou a 2ª tomada, porque nela quem fala olha para baixo escrevendo o "5").
- **Fica:** vício de linguagem isolado ("tipo", "né", "então"). Decisão de quem pede o vídeo.
- **Escorregão de fala** que não dá para cortar sem perder sentido ("o que
  confere audita o carregamento"): fica, e você avisa.
- Trecho de demonstração que não se sustenta sem a tela (ele pedindo algo ao
  Claude por voz): só sai se a pessoa pedir.

O roteiro ajuda a achar retomada, mas **a fala vence o roteiro**. Divergência
importante (ele trocou uma palavra, esqueceu um pedaço): avise.

## 1.4 A regra dura: cada corte de fala conferido

Em 6 de 14 vídeos de uma série a transcrição longa errou: inventou começo falso
que não existia, juntou retomada numa palavra só, derivou de 0,5 s a 9 s. Dois
cortes marcados pelo `palavras.json` estavam 2 s deslocados (um comeu
"exclusiva desse evento") e só apareceu depois de ir para a pessoa.

Para cada corte de fala que você marcou:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/transcrever.py "<bruto>" --de <ini-2> --ate <fim+2> --isolado
```

- a fala isolada confirma que a repetição existe e onde ela começa e termina;
- a borda do corte cai dentro de um silêncio de `analise/silencios.json`;
- `SUSPEITA: 'fez' dura 1,6s` é retomada fundida numa palavra só: escute.

Com 3 cortes ou mais, despache o **conferente de corte**
(`agentes/conferente-de-corte.md`) com a lista; ele devolve cada corte
confirmado ou corrigido.

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/plano.py aplicar --pasta "<pasta>" --remocoes "<pasta>/remocoes.json"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/plano.py resumo --pasta "<pasta>"
```

`remocoes.json`: objetos com `de`, `ate`, `tipo`, `texto`, `motivo`. O `aplicar`
**soma** ao plano e recusa tudo se um corte cair dentro de palavra, deixar bloco
menor que 0,12 s ou passar de 60%. Corrija os tempos; não contorne. Desfazer:
`plano.py restaurar --indice N`.

## 1.5 Render e conferência

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY -u $TEV/scripts/render.py --pasta "<pasta>" --ate velocidade --preview
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/verificar.py --pasta "<pasta>" "<pasta>/previews/02-velocidade.mp4"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/auditar.py --pasta "<pasta>"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/transcrever.py "<pasta>/previews/02-velocidade.mp4" --json "<pasta>/analise/preview-palavras.json"
```

- `verificar.py` olha o arquivo (duração, blocos curtos, áudio). Falhou: não mande.
- `auditar.py` olha o conteúdo (abertura truncada, emenda, compressão) e separa
  o que o corte causou do que já vinha do bruto. **Defeito do bruto: avisar,
  não consertar.** Ele devolve código 1 em achado só informativo: não encadeie
  com `&&`. Leia `references/edicao-auditoria.md` antes da primeira entrega.
- A transcrição do preview prova que nenhuma palavra sumiu e que as retomadas
  saíram. Compare com o roteiro.

Bloco curto que o `verificar.py` acusa costuma ser respiração a -50 dB entre
pausas: sai com `aplicar`, tipo `hesitacao`.

## 1.6 Portão 1

Mande o MP4 (`SendUserFile`; sem ele, o caminho absoluto) com o resumo,
**escrito na mensagem**:

- duração antes e depois (ex.: 2min10 → 1min20 em 1,3x);
- cada corte de fala, com a frase e o motivo;
- o que o `auditar.py` mandou avisar;
- pergunta: algum corte errado, 1,3x está boa, e **já há pedidos de
  insert, referências de estética ou material?**

Aprovado: `plano.py aprovar --pasta "<pasta>" --etapa velocidade`.

**Ajuste depois do portão não refaz análise:** `restaurar --indice N`,
`aplicar` com o corte novo, `inserts --substituir`. A pessoa fala em tempo do vídeo
que viu ("em 1:09 tem uma duplicidade"): converta com

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/tempo.py --pasta "<pasta>" fin 1:09 1:23
```

e confira com transcrição isolada no original. Corte que inclui pausa já
encurtada tira do final menos que (fim - início) / 1,3: nunca desloque inserts
ou legenda pela conta de cabeça; meça entre os dois `plano.json`.
