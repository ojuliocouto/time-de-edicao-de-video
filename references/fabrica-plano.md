# O plano da série

Escrito **antes de qualquer arte**, em `PLANO.md` na raiz do projeto, e aprovado
inteiro de uma vez.

## Por que este arquivo existe

A skill já tinha um passo de planejamento. Ele pedia, por arte: o trecho, o que
mostra, a duração e de onde vem o material. **Todos os campos eram por peça, e
nenhum era da série.** O plano era uma lista de itens independentes, então saíam
itens independentes e parecidos.

Medido em doze inserts entregues em dois anúncios:

| | detalhe de textura | trocas de plano |
| --- | --- | --- |
| referências que a pessoa escolheu (6) | 3,2% a 13,6% | **0, 0, 3, 6, 8, 10** |
| reel de exemplo A (5) | 2,9% a 15,0% | **1, 0, 0, 0, 0** |
| reel de exemplo B (7) | 2,4% a 5,0% | **0, 0, 0, 0, 0, 0, 0** |

Dez de doze inserts nunca cortam. Tudo numa tela só, do primeiro ao último
quadro. E o registro de material do reel B mostra o resto: em sete artes, o único
material real foi um mascote de conversa antiga e um SVG de logo.

**Não foi falta de criatividade. O formato do plano produzia o defeito.**

## Verificador ou planejador

| | Serve quando |
| --- | --- |
| **Verificador** | o defeito só aparece no resultado e o conserto é barato |
| **Planejador** | o defeito já está decidido no plano e o conserto é reconstruir |

Tela morta é o primeiro caso: dá para medir e refazer em segundos de render.
Série chapada é o segundo: quando você escreve "três linhas com X", a chatice já
está travada, e descobrir na sétima peça significa refazer seis.

## O formato

Uma linha por insert. As quatro colunas do meio são as que não existiam.

| # | Janela | Trecho | **Plano** | **Material** | **Dispositivo** | **Registro** |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2,98 a 5,60s | ... | geral → fechado | grafismo | acúmulo | escuro denso |

- **Plano**: fechado, médio ou geral, e onde estão os cortes internos
- **Material**: o arquivo real que entra, ou a palavra `grafismo` quando não há
- **Dispositivo**: o mecanismo, tirado do conjunto fechado do projeto
- **Registro**: claro ou escuro, denso ou vazio

## Os cinco pisos

O plano reprova na tabela, antes de existir arte. Consertar é editar uma linha.

**1. Corte.** Pelo menos **metade** dos inserts tem troca de plano interna.
Calibrado nas referências: quatro das seis cortam de 3 a 10 vezes.

**2. Material real.** Pelo menos **um terço** dos inserts carrega coisa real,
não grafismo construído. Isto não é medida nova, é a regra 2 ganhando piso: ela
existia e apodrecia em silêncio porque ninguém contava.

**3. Dispositivo não repete em sequência**, e nenhum aparece em mais de um terço
da série. O dispositivo sai de um **conjunto fechado** definido no `estilo.md` do
projeto: vocabulário fechado dá família, rotação dentro dele dá variedade. As
duas coisas juntas, não uma contra a outra.

**4. Tamanho de plano não é o mesmo em toda a série.**

**5. Pelo menos uma virada de registro** ao longo da série.

Piso 1 é medido. Os pisos 2 a 5 são decisão de direção, e estão escritos aqui
para não dependerem de eu lembrar.

## O que teria acontecido no reel de exemplo A

O plano que eu deveria ter escrito, antes de construir:

| # | Plano | Material | Dispositivo |
| --- | --- | --- | --- |
| 1 | geral → fechado | grafismo | acúmulo |
| 2 | fechado | grafismo | diagrama |
| 3 | fechado | grafismo | lista |
| 4 | fechado | grafismo | risca-e-troca |
| 5 | fechado | grafismo | botão |

Quatro linhas iguais na coluna do meio, cinco quase iguais na primeira. **O
problema é visível numa tabela de cinco linhas**, e custaria minutos consertar
ali. Custou uma hora de construção para aparecer só no fim.

## Depois de aprovado

O plano vira contrato. O `scripts/medir_serie.py` confere se o render bate com
ele: se a linha diz corte e material real, e o arquivo não tem nenhum dos dois,
quem escorregou foi a execução, não o plano.

O verificador aqui é guarda contra deriva, não instrumento de descoberta. Com o
plano certo, ele passa.
