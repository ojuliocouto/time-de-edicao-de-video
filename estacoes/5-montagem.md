# Etapa 5. Montagem: inserts, zoom, whoosh e batida (até o portão 5)

Todo comando começa com o prefixo abaixo, que acha a skill e escolhe o Python
(`python3` no Mac e no Linux, `python` no Windows, onde `python3` pode abrir a
Microsoft Store):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python;
```

`<bruto>` é o `bruto-montado/montado.mp4` da etapa 0. Render, máscara e mixagem
vão com `timeout: 600000` na chamada do Bash.

A ordem importa: a máscara vem antes do `plano.py inserts` (ele mede a silhueta
nela), e o `plano.py som` vem depois do zoom (ele tira uma foto do plano: o que
entrar depois fica sem som).

## 5.1 Lista de inserts

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/montar_lista.py --pasta "<pasta>"
```

Converte as janelas do `fabrica/janelas.json` (tempo do final) para o original,
com a mesma conta do render (converter na mão foi onde mais se errou), e avisa:
rosto voltando por menos de 1 s, arquivo curto para a janela, arquivo que vai
aparecer só pela metade. Nos formatos com recorte, imprime a linha pronta da
máscara com as `--janelas` certas.

Caminho de arquivo no `janelas.json`: absoluto. No Windows, no formato
`C:/Users/...` (o Python do Windows não entende `/c/Users/...` do Git Bash).

## 5.2 Máscara da pessoa (só se algum formato pedir)

`vazado_maior`, `vazado_pequeno` e `react` precisam. Use a linha que o
`montar_lista.py` imprimiu:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/mascara.py "<bruto>" -o "<pasta>/analise/matte.mp4" --janelas <a-b,c-d> --estimar
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/mascara.py "<bruto>" -o "<pasta>/analise/matte.mp4" --janelas <a-b,c-d>
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/insert.py --medir --matte "<pasta>/analise/matte.mp4"
```

No Mac a Vision faz 10 quadros por segundo. No Windows e no Linux é o
remove-background do HyperFrames, ~1 quadro por segundo: **diga à pessoa o tempo
que o `--estimar` mostrou antes de começar**. Passou de 10 min: peça que ela
rode a linha exata no próprio terminal e acompanhe o arquivo de saída, porque a
máscara é um arquivo só e não se emenda em pedaços. A máscara sai com o tamanho, o fps e a
duração do bruto, em blocos de 40 s (a Vision parava no meio de arquivo longo
sem erro). O `render.py` confere e recusa máscara que não bate.

`insert.py --medir` com `recorte_amputado` no `react`: **pare e pergunte** se
a pessoa quer recortado assim ou em miniatura.

## 5.3 Inserts no plano

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/plano.py inserts --pasta "<pasta>" --arquivo "<pasta>/lista-inserts.json" --substituir
```

Recusa formato desconhecido, arquivo inexistente, sobreposição e janela maior
que o arquivo. Nos formatos com recorte, mede se o painel come o pé da arte e
calcula o `"subir"`: **pergunte** entre subir a arte e trocar o formato. Os 8
formatos, a geometria e as travas: `references/edicao-inserts.md`.

Dois inserts quase grudados não deixam mais o quadro do rosto entre eles: o
render cobre essa emenda sozinho. Mesmo assim, olhe a emenda.

## 5.4 Troca de vídeo no CTA (anúncio de dois vídeos)

Na emenda do corpo do anúncio com o CTA: whoosh na entrada do vídeo novo, efeito
de montagem (clarão editorial) e, quando a pessoa pedir, tela escura com o
lettering central da fala até a frase seguinte ("até ele falar 'não é só um
curso'"). É um insert de tela cheia como os outros, feito na etapa 4, com a
filmagem do CTA dentro dele escurecida. Cor seletiva no amarelo estragou a
barba: não use.

## 5.5 Zoom

O zoom é livre na fase final: você decide onde, sem perguntar ponto a
ponto, e lista no resumo. Regras (`references/edicao-zoom.md`):
- take de rosto acima de 5 s precisa de zoom (o `resumo` marca os que faltam);
- insert não recebe zoom (o comando recusa);
- `seco` em número, preço e dado; `suave` em CTA e fechamento; `lento` em take
  longo sem nada acontecendo; intensidade 12%;
- os tempos saem da coluna "no original" do `resumo`.

A pessoa pediu "só o whoosh, o resto não precisa"? Pule o zoom e a
batida nesse vídeo.

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/plano.py resumo --pasta "<pasta>"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/plano.py zoom --pasta "<pasta>" --arquivo "<pasta>/lista-zoom.json"
```

## 5.6 Whoosh em toda entrada de insert

Padrão nos criativos (pedido em todos os anúncios da série que deu origem à skill). **Sempre depois do
zoom, e de novo depois de qualquer mudança de insert ou de zoom:**

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/plano.py som --pasta "<pasta>"
```

**Um render só, em resolução cheia.** Ele serve para o portão 5 (a versão 720p
sai dele em segundos) e é a base da legenda: renderizar preview e depois o
cheio dobrava o tempo (numa validação: 3 renders de 15 min). Na chamada do
Bash, `run_in_background: true` e espere a notificação de que terminou (o
limite de 10 min da chamada não segura um render longo; nunca `nohup` nem `&`):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY -u $TEV/scripts/render.py --pasta "<pasta>" --ate audio --saida "<pasta>/previews/montado-sem-batida.mp4"
```

Whoosh na entrada e na saída de cada insert e click em cada zoom seco. O volume
sai do nível da fala do vídeo (6 dB abaixo), não é fixo. O comando avisa quando
o trecho fica metralhado. Subida longa (`--riser`) só se a pessoa pedir e só se o
primeiro take for longo. Detalhes: `references/edicao-som.md`.

Leva de 5 a 15 minutos num vídeo de 2 a 3 min com 20 inserts. Ajuste pequeno
(um insert trocado) pede o render inteiro de novo: junte os ajustes pedidos e
renderize uma vez. Confira as emendas e a sincronia: folha de contato em volta de
cada borda de insert e, nos inserts que escrevem a fala, a palavra entrando
quando é dita.

## 5.7 Batida de fundo

Padrão nos criativos: batida animada bem baixa no vídeo todo, com virada na
frase da oportunidade ("E pra isso eu tenho uma boa notícia", "Bom, se você se
interessou", "Vem aí"). O segundo da virada é do vídeo FINAL (ache na
transcrição do preview).

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/batida.py --video "<pasta>/previews/montado-sem-batida.mp4" --virada <segundo do final> -o "<pasta>/previews/montado.mp4"
```

104 BPM, ~21 dB abaixo da voz, medido no próprio vídeo. A primeira versão, 10 dB
abaixo, foi reprovada: "diminui drasticamente a música de fundo, deixa bem
baixinha mesmo". Nada de denoise na voz.

**Sem batida** (a pessoa dispensou): `cp "<pasta>/previews/montado-sem-batida.mp4" "<pasta>/previews/montado.mp4"`.
Daqui em diante o montado é sempre `previews/montado.mp4`, em resolução cheia.
A versão para mandar no chat:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/entrega.py "<pasta>/previews/montado.mp4"
```

(sai `previews/montado-720p.mp4`; sem `--drive` ele só confere e gera a leve).

## 5.8 Conferir antes de mandar

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/verificar.py --pasta "<pasta>" "<pasta>/previews/montado.mp4"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/auditar.py --pasta "<pasta>"
```

Depois despache o **revisor final** (`agentes/revisor-final.md`) com o caminho
do montado, o `PLANO.md` e o `fabrica/janelas.json`: ele assiste como a pessoa
assistiria e devolve uma lista. Corrija o que for defeito antes de mandar.

## 5.9 Portão 5

Mande o montado (`previews/montado-720p.mp4`) com o resumo: inserts na ordem,
zooms, onde a batida vira, e o que precisou de decisão sua. Ajuste: mexe no
plano, roda o `som` de novo se mudou insert ou zoom, e re-renderiza.

Lettering da edição (caixa ou destaque, 3,5 s) só quando a pessoa pedir e com o
texto dela: `references/edicao-lettering.md`. Na prática dos anúncios, texto na tela saiu
como insert ou como legenda, não como lettering.
