# Troubleshooting e instalação

## Troubleshooting

### A transcrição voltou vazia
O modelo de teste que vem com o brew é falso e sempre devolve vazio. Conferir
que `--modelo` aponta para `ggml-large-v3-turbo.bin`. Se o caminho estiver
certo, ouvir o `analise/audio.wav`: provavelmente o vídeo não tem áudio.

### A transcrição está lenta demais
Alternativa: trocar o whisper.cpp pelo `mlx-whisper`, que roda na GPU do Mac e
é bem mais rápido. Passar `--modelo mlx-community/whisper-large-v3-turbo` não
funciona direto; exige adaptar `transcrever()` em `analisar.py`. Só vale se a
demora estiver atrapalhando de verdade.

### O corte ficou picotado
Blocos curtos empilhados. Rodar `plano.py validar` e olhar os alertas. Causa
mais comum: transcrição imprecisa gerando marcações de fala erradas. Aumentar
`--respiro` reduz o problema.

### O plano corta mais de 60% e a trava disparou
Quase sempre é transcrição falhada, não vídeo ruim. Conferir
`analise/transcricao.txt` antes de qualquer coisa. Se o corte for mesmo de
propósito, marcar `corte_agressivo: true` nos parâmetros do plano.

### O ffmpeg falhou com filtro muito longo
Não deveria: o grafo vai em arquivo, não na linha de comando. Se acontecer,
conferir `analise/filtro.txt`.

### O vídeo do insert saiu com dimensão errada ou com a camada trocada
Quase sempre é quoting de shell. **Ao montar filtro de ffmpeg em comando
digitado, usar sempre `${VAR}` e nunca `$VAR`.** O zsh interpreta `$A[mini]`
como índice de array e devolve vazio: o ffmpeg monta um grafo diferente, não
reclama de nada e entrega um vídeo errado. Os scripts da skill declaram bash no
topo e escapam disso.

### A detecção de silêncio parece absurda
O limiar sai do próprio áudio e é reportado no início do `analisar.py`. Se o
material tem música de fundo ou foi gravado em ambiente ruidoso, a proposta
automática pode errar. Forçar com `--limiar -48`, por exemplo, e conferir a
proporção de silêncio no relatório: num vídeo falado do começo ao fim, algo
entre 15% e 30% é plausível.

### O preview parece borrado ou quebrado em blocos
Rodar `auditar.py` antes de mexer na qualidade do encode: quase sempre o defeito
está no arquivo de origem. Ver `references/edicao-auditoria.md`.

### O áudio saiu com estalo nos cortes
Corte caindo em ponto de energia alta. Ajustar o tempo daquele corte
específico em alguns centésimos com `restaurar` e reaplicar.

---

## Instalação

Está em `references/instalacao.md`, por sistema. O `preflight.py` mostra o
comando exato do que faltar.

---



## O plano perdeu inserts, zoom, som e lettering de uma vez

Alguém rodou `plano.py criar` numa pasta que já tinha avançado. O `criar` monta
o plano do zero, então tudo que veio depois do corte ia junto. Num teste real
sumiram **7 inserts, 6 zooms, 13 efeitos e o lettering** sem uma linha de aviso.

Hoje o comando **recusa** quando encontra trabalho posterior e lista o que
seria perdido. Para mudar o corte sem perder o resto, o caminho é `restaurar`
ou `aplicar`. O `--recomecar` existe só para quando a intenção for jogar fora.

## O recorte da pessoa aparece deslocado ou esticado

A máscara foi gerada com tamanho ou fps diferentes do bruto. O comando da fase
5.2 já teve `1080x1920` e `-r 30` cravados, o que quebra em qualquer bruto fora
desse padrão: a 25 fps a máscara dura 75s em vez de 90, e o recorte vai
descolando ao longo do vídeo sem nada acusar.

O `render.py` confere duração **e** dimensão e recusa antes de renderizar. A
correção é gerar de novo com largura, altura e fps tirados do próprio bruto,
como está no comando da fase 5.2.


## Quanto tempo cada render demora

Medido num Reels de 66s finais, 1080x1920, com 7 inserts e 6 zooms:

| até | tempo |
|---|---|
| `velocidade` | ~10s |
| `inserts` | ~11 min |
| `zoom` | ~12 min |
| `audio` | ~10 min |
| `lettering` | ~11 min |
| final em qualidade cheia | ~9 min |

**O que domina o custo é o formato, não a quantidade.** O mesmo vídeo de 76s
finais foi medido nas duas pontas:

| inserts | com vazado? | tempo |
|---|---|---|
| 9 | nenhum | ~13 min |
| 14 | dois `vazado_pequeno` | **~24 min** |

Cinco inserts a mais quase dobraram o render, e a diferença está nos dois
vazados: eles obrigam a processar a máscara do vídeo inteiro, com erosão, blur e
`tmix` de três quadros por frame. `react` e `react_miniatura` custam o mesmo.
**Ao estimar, contar os vazados antes de contar os inserts.**

**Não estimar pelo ritmo dos primeiros minutos.** O começo do arquivo costuma ser
o trecho mais denso, e uma projeção feita ali deu 80 min para um render que levou
24. Se for estimar, medir depois da metade.

**Rodar com `python3 -u`**, senão a saída fica presa no buffer e parece
travado. Encadear o render com `verificar.py` num `&&` faz parecer que tudo é
instantâneo, e não é.

## Aviso de bloco curto depois que o plano avançou

O `aplicar` avisa quando sobra um bloco de fala muito curto. A correção óbvia
seria aumentar o `--respiro`, mas ele é flag do `criar`, e o `criar` recusa
rodar numa pasta que já avançou.

**Não é impasse: bloco curto é aviso, não defeito.** Ele existe para a pessoa
conferir se a emenda ficou seca demais naquele ponto. Confira no preview. Se
incomodar de verdade, o caminho é `plano.py restaurar --indice N` no corte que
criou o bloco, não refazer o plano. `criar --recomecar` só quando a intenção for
mesmo jogar tudo fora e remarcar do zero.


## O transcritor entrou em loop e comeu um trecho inteiro

O whisper as vezes para de acompanhar a fala e passa a repetir a ultima frase,
esticando cada palavra por segundos. Em material real ele comeu **32s de um
anuncio de 121s**, justamente a oferta e o CTA, e repetiu "nao e a falta de
ideias" ate o fim. Nada acusava: o JSON tinha palavras, tempos e texto plausivel,
e cortar em cima disso destruiria o video.

A assinatura e **palavra curta durando segundos num trecho onde o audio TEM
fala**. Se o audio estivesse mudo seria alucinacao, que o `descartar_alucinacao`
ja trata; aqui e o contrario, tem fala e falta texto. O `analisar.py` detecta,
retranscreve o trecho isolado e costura, avisando na saida.

**Duas armadilhas do reparo, ambas custaram uma rodada cada:**

O whisper.cpp **arredonda o clipe para multiplo de 30s**: um trecho de 38,9s
volta com palavras ate 60s. Sem corrigir a cauda ANTES de somar o deslocamento,
a janela de troca descarta metade do texto recuperado.

Quando ele repete a ultima frase ao fechar o bloco, a copia sai com tempos EM
CIMA da primeira, e depois de ordenar as duas viram sopa. O descarte por
sobreposicao so vale para **copia literal**: uma versao que descartava por
sobreposicao de tempo sozinha comeu fala legitima, porque em fala rapida as
palavras se encostam.

**Limite conhecido:** a emenda ainda perde uma oracao curta na borda esquerda e
pode deixar a ultima frase duplicada. **Sempre conferir a transcricao no trecho
avisado antes de marcar corte de fala ali.**
