# Auditoria antes da aprovação

`scripts/auditar.py` roda depois de montar o plano e **antes de mandar o vídeo
para aprovação**. Ele existe porque um vídeo pode passar em todas as checagens
técnicas e mesmo assim não fazer sentido.

```bash
python3 scripts/auditar.py --pasta "<pasta>"          # completo
python3 scripts/auditar.py --pasta "<pasta>" --sem-imagem   # só o sentido, mais rápido
```

Sai com código de erro quando há o que sinalizar, então serve em cadeia de
comandos.

## A regra que vale para as duas auditorias

**Separar o que o corte causou do que já vinha assim no bruto.**

Defeito de origem não se conserta cortando, e às vezes cortar piora. Num teste
real o vídeo começava em "e liberar um ingresso", no meio da frase. A pessoa
achou que a skill tinha cortado o começo. A medição mostrou o contrário: o
áudio do render bate com o do bruto desde a amostra zero, e o primeiro bloco
mantido ia de 0,0 a 5,635 segundos, intacto. O vídeo de origem começava assim.

Nesse caso a decisão dela foi explícita: **se o áudio começa estranho mas
cortar atrapalharia o sentido, mantém-se o áudio estranho.** A skill avisa, ela
decide.

Por isso todo achado diz de onde veio, e a instrução é sempre **avisar e
perguntar**, nunca consertar sozinho.

## 1. Auditoria de sentido

Reconstrói o texto que sobreviveu aos cortes e mostra, sempre, **como o vídeo
começa e como termina**, em texto. Só isso já pega a maioria dos problemas.

Além disso sinaliza:

**Abertura truncada.** Quando a primeira palavra é uma que não abre raciocínio:
"e", "mas", "então", "que", "porque", "aí", preposição solta. Diz se foi o corte
ou se já era do bruto, e no segundo caso manda perguntar.

**Encerramento truncado.** Quando a última palavra não fecha frase. Mesma
distinção de origem.

**Emendas.** Para cada corte que removeu fala, imprime as quatro palavras antes
e as quatro depois, juntas, para ler em voz alta. Corte de pausa não entra: só
gagueira, começo falso e hesitação, que são os que podem quebrar sentido.

## 2. Auditoria de imagem

Varre a filmagem procurando trecho com compressão destruída, que aparece como
imagem quebrada em blocos.

**Mede na resolução nativa.** Uma primeira versão reduzia a imagem antes de
medir, o que desalinha a grade de 8 pixels do H.264 e apaga justamente o sinal
procurado: dava 1,08 em todo lugar, inclusive no trecho quebrado.

**Limiar relativo, não absoluto.** A razão de blocagem depende de quanto a
imagem tem de detalhe. No material de teste a mediana era 1,36 e o pior trecho
dava 1,51, onze por cento acima. É pouco: **a detecção é fraca de propósito, ela
levanta suspeita para conferir no olho, não dá veredito.**

**Também reporta a taxa de bits do bruto.** Esse é o indicador mais confiável do
teto de qualidade. Abaixo de 6 Mbps em vertical 1080 costuma quebrar em cena
escura com ruído. O material de teste tinha 4,7 Mbps.

## O que isso não é

Não é controle de qualidade do encode da skill. Isso foi medido: em material com
blocagem de origem, preview em crf 28 e em crf 23 deram resultado **visualmente
idêntico**, com o arquivo mais que dobrando de tamanho à toa. Quando um preview
sai quebrado, a primeira pergunta é se o bruto já estava quebrado ali.


## O `auditar.py` sai com código 1 mesmo sem defeito da edição

Ele devolve 1 sempre que tem algo para avisar, **inclusive quando o defeito já
vinha do bruto** e nada há para consertar. Isso é de propósito: o código 1 diz
"tem coisa para a pessoa saber", não "a edição está errada".

Consequência prática: **não encadear com `&&`.** Rodar
`render.py && verificar.py && auditar.py` funciona, mas
`auditar.py && outra_coisa` derruba a sequência num aviso inofensivo.
