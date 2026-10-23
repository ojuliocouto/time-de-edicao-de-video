# Brief do conferente de corte

Despachado na etapa 1 quando há 3 cortes de fala ou mais. Ele não decide o que
cortar: confere se cada corte que o orquestrador marcou existe de verdade no
áudio e se as bordas caem em silêncio.

Prompt do orquestrador (preencha os campos):

> Você é o conferente de corte do time de edição de vídeo. Leia
> `~/.claude/skills/time-de-edicao-de-video/agentes/conferente-de-corte.md` e
> siga. Vídeo: `<bruto>`. Pasta: `<pasta>`. Cortes a conferir: `<pasta>/remocoes.json`.
> Roteiro (se houver): `<pasta>/script.txt`. No Windows, use `python` no lugar
> de `python3`.

## Por que existe

A transcrição do vídeo inteiro errou em 6 de 14 vídeos de uma série: inventou
começo falso que não existia (repetiu "você só precisa construir os times"),
comeu frases inteiras, juntou retomada numa palavra só ("fez" de 1,6 s) e
derivou de 0,5 s a 9 s. Dois cortes de um anúncio estavam 2 s deslocados; um
comeu "exclusiva desse evento". Só apareceu depois de ir para a pessoa.

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

## O que fazer, para cada corte do remocoes.json

1. Transcreva isolado, com 2 s de folga em cada lado:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/transcrever.py "<bruto>" --de <de-2> --ate <ate+2> --isolado
```

2. Confirme três coisas:
   - **a repetição existe** no isolado (não é invenção da transcrição longa);
   - **o que fica** depois do corte forma a frase certa (compare com o roteiro;
     a fala vence o roteiro quando divergem);
   - **as bordas** (`de` e `ate`) caem dentro de um silêncio de
     `<pasta>/analise/silencios.json`, ou entre duas palavras do isolado.
3. `SUSPEITA` impressa pelo script (palavra curta com mais de 0,9 s): é
   retomada fundida. Transcreva uma janela menor em volta e ache onde ela está.

Procure também, no vídeo inteiro, **retomada que ninguém marcou**: palavra
esticada no `analise/palavras.json` (fim - início > 0,9 s em palavra curta) e
frase do roteiro que aparece duas vezes. Confira cada uma isolada.

## O que devolver

Uma tabela, um corte por linha:

| corte | de | até | situação | de corrigido | até corrigido | o que o isolado diz |
|---|---|---|---|---|---|---|
| 1 | 104,20 | 108,90 | confirmado | | | "Mas não é só isso que te... Mas não é só isso." |
| 2 | 131,10 | 133,40 | deslocado | 133,05 | 135,35 | a retomada começa 1,95 s depois |
| 3 | 59,20 | 61,00 | não existe | | | a fala é corrida, sem repetição |

E a lista de retomadas não marcadas, com tempo e o texto do isolado.

Não edite o `plano.json` nem o `remocoes.json`. Não fale com a pessoa que pediu o vídeo.
