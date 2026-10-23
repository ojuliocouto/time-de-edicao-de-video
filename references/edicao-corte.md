# Julgamento de corte: o que sai da fala e o que fica

Este arquivo cobre a parte da etapa 1 que nenhuma ferramenta faz. Pausa é
detecção acústica e o `silencedetect` resolve sozinho. Gagueira, começo falso
e hesitação são interpretação: dependem do sentido da frase, não do volume do
áudio. É o agente que lê e decide.

## O corte de pausa, que a maquina faz sozinha

Todo silencio acima de **0,15s** e cortado, deixando 0,15s no lugar, metade de
cada lado. Isso sai do `silencedetect` e nao precisa de julgamento.

### Pausa dramatica protegida

Uma pausa longa antes de uma **virada de raciocinio** nao e ruido, e ritmo.
Nesses casos preserva-se **ate 0,6s** em vez de reduzir para 0,15s. E o que
separa corte seco de corte atropelado.

A protecao dispara em dois casos:

- a frase **antes** da pausa termina em pergunta, ou seja, pergunta retorica
  pendurada;
- a fala **logo depois** da pausa comeca com um marcador de virada: "e sabe",
  "so que", "mas", "acontece que", "o resultado", "e por isso", "presta
  atencao", "olha so", "o problema e", "a verdade e", entre outros. A lista
  fica em `MARCADORES_VIRADA`, no `plano.py`.

**So as primeiras quatro palavras depois da pausa contam.** Uma primeira versao
varria mais texto e uma expressao distante marcava como dramatica uma pausa que
nao tinha nada a ver: no material de teste, uma pausa curta foi protegida porque
"e sabe" aparecia cinco palavras adiante.

### Limite conhecido

A protecao e por marcador, entao ela erra nos dois sentidos. Suspense construido
sem marcador nenhum, do tipo "uma condicao quase... desleal", nao e reconhecido e
a pausa vai ser cortada. Quando isso importar, o caminho e devolver aquele corte
especifico com `plano.py restaurar --indice N`.

## O teste que vale para tudo

Antes de marcar qualquer corte, leia a frase inteira sem o trecho. Se ela
continuar dizendo a mesma coisa, corta. Se mudar de sentido, ficar ambígua ou
perder a ênfase, não corta.

Na dúvida, não corta. Um vídeo com uma gagueira a mais é aceitável. Um vídeo
com uma frase quebrada não é, e a pessoa vai ter que reprovar o portão inteiro
por causa de um corte.

## Os três tipos

### gagueira

Repetição involuntária de sílaba ou palavra, sem intenção.

    "o, o, o procedimento"        -> corta as duas primeiras, mantém "o procedimento"
    "eu vou, eu vou falar"        -> corta a primeira tentativa
    "pro-, procedimento"          -> corta a sílaba solta

Mantém sempre a **última** repetição, que é a que engata na frase.

Não confunda com repetição de ênfase, que é intencional e fica:

    "é muito, muito importante"   -> FICA, a repetição é o argumento
    "não, não faça isso"          -> FICA, a repetição é a força da frase

O que separa os dois: a gagueira repete uma palavra que sozinha não significa
nada (artigo, pronome, sílaba). A ênfase repete uma palavra com peso.

### comeco_falso

A frase começa, morre e é refeita de outro jeito. Corta a primeira tentativa
inteira, da primeira palavra até a última antes do recomeço.

    "então o que acontece é... na verdade o que acontece é que muita gente erra"
     ^--------------------^ corta isto inteiro

    "o paciente ele... a maioria dos pacientes chega achando que"
     ^--------------^ corta isto inteiro

Cuidado com o limite do corte. Ele vai até o fim da tentativa abandonada, não
até o meio dela. Cortar pela metade deixa um pedaço de frase órfã, que soa
pior que o começo falso original.

Não é começo falso quando a primeira parte carrega informação que a segunda
não repete:

    "isso custa caro... e não é só o dinheiro, é o tempo também"
     -> FICA. a segunda parte se apoia na primeira, não a substitui.

### hesitacao

Som de segurar o pensamento, sem conteúdo.

    "é...", "eh", "hmm", "aaah", "uhum" no meio da frase

Sai sem perda nenhuma. É o corte mais seguro dos três.

Atenção a uma armadilha do português: "é" também é o verbo ser. O whisper
transcreve os dois igual.

    "a resposta é... é simples"    -> o primeiro "é" é hesitação, o segundo é verbo
    "é, eu concordo"               -> hesitação
    "é caro"                       -> verbo, FICA

Use a duração para desempatar. Hesitação costuma se estender bem mais que a
mesma palavra usada como verbo, e quase sempre tem silêncio grudado nela.

## Vício de linguagem: a regra é não cortar

"tipo", "né", "então", "assim" usados como muleta **ficam**. Foi decisão
explícita da pessoa. Cortar isso rouba a personalidade da fala e é o que faz
vídeo editado soar como locução de robô.

A única exceção é quando a muleta faz parte de um começo falso ou de uma
hesitação. Aí ela sai junto, porque o corte é do trecho inteiro:

    "então... então o que eu quero dizer é"
     ^--------^ isto é gagueira com "então", corta

## Como entregar as marcações

Escreva um JSON com uma lista e passe para `plano.py aplicar`:

```json
[
  { "de": 12.40, "ate": 13.12, "tipo": "comeco_falso",
    "texto": "então o que acontece é",
    "motivo": "frase abandonada, refeita em 13.12 como 'na verdade o que acontece é'" },
  { "de": 4.02, "ate": 4.31, "tipo": "gagueira",
    "texto": "eu vou",
    "motivo": "repetição, a segunda tentativa fica" }
]
```

O `motivo` não é enfeite. Ele aparece no relatório do portão de aprovação e é
o que permite a pessoa discordar de um corte específico sem assistir o vídeo
inteiro procurando o que mudou.

Tire os tempos de `analise/palavras.json`, que tem início e fim de cada
palavra. O `de` é o `ini` da primeira palavra que sai. O `ate` é o `fim` da
última.

## O que o script recusa

`plano.py` valida cada marcação antes de aceitar e **recusa a aplicação
inteira** se qualquer uma falhar, sem salvar nada:

- Corte que cai fundo dentro de uma palavra. Encostar na borda ele resolve
  sozinho; invadir mais de 0,08s ele recusa, porque corta um fonema no meio.
- Corte que deixaria um bloco de fala com menos de 0,12s.
- Conjunto de cortes que remove mais de 60% do vídeo.

Se recusar, o motivo aparece na mensagem. Conserte os tempos e rode de novo.
