# Lições de uma série real de anúncios

Mapeamento de 14 edições de anúncios em vídeo feitas com as três skills que
deram origem a esta (`editar-video`, `fabrica-de-insert` e `cinematic-caption`),
lidas nas mensagens de quem pediu e aprovou, nas pastas dos projetos e nas
anotações. Cada regra da skill aponta para cá.

## Os 14 vídeos

Anúncios verticais de 1 a 3 minutos, gravados em câmera por um apresentador:
alguns de corpo único, outros emendados (o corpo de um vídeo com o CTA de
outro), alguns com depoimento de aluno ou react a vídeo de terceiro. Todos
terminaram aprovados e entregues no Drive, um deles sem nenhum ajuste. O custo
está no caminho: rodadas de ajuste que as regras abaixo evitam.

## O processo aprovado (e que esta skill segue)

1. Corte + 1,3x, preview, portão.
2. `PLANO.md` de inserts: os que a pessoa dita mais os que você propõe,
   decisões em aberto numeradas, nada produzido antes do "aprovado".
3. Inserts fabricados (depois de um tempo, por 4 a 6 agentes em paralelo),
   mandados um por um com a voz.
4. Montado com whoosh, zoom e batida; ajustes da pessoa.
5. Legenda cinematográfica no vídeo inteiro, com palavras atrás de quem fala.
6. Drive em alta, com tamanho conferido; 720p para mensagem.

O fluxo foi aprovado com "ficou perfeito" nos três primeiros vídeos e repetido
sem mudança de estrutura em todos os seguintes.

## O que mais custou retrabalho, em ordem

### 1. Transcrição que mente (6 de 14 vídeos)

- Inventou dois começos falsos e perdeu o CTA e uma frase inteira.
- Dois cortes 2 s deslocados; um comeu "exclusiva desse evento". Só apareceu
  depois do portão.
- Derivou até 9 s a partir dos 85 s e inventou um "ou seja".
- Duplicou o fim de um vídeo; dois inserts saíram 0,8 s atrasados porque o
  tempo veio do bruto.
- Em quatro vídeos, o whisper.cpp derivou de 0,5 s a 2 s.
- A pessoa achou duas repetições que a transcrição tinha fundido numa palavra
  só esticada ("fez" de 1,6 s).

**Na skill:** motor de transcrição melhor primeiro (mlx, faster-whisper), corte
de fala só com transcrição isolada e silêncio, alerta automático de palavra
esticada, transcrição do preview depois do render, partituras feitas do vídeo
final, conferente de corte como subagente.

### 2. Inserts genéricos ou parecidos demais

- "animação barata": cartões abstratos onde a fala citava posts reais. Virou
  prints e thumbs reais, usuário oculto.
- "meio mentiroso": chat do Claude feito em motion. Virou a gravação real da
  ferramenta.
- "não é pra se limitar só nesse design": os pilotos copiavam uma referência;
  o pedido era paleta fixa e o resto variando.
- "não gostei da estética": a primeira estética inteira. Foi bom ter só dois
  pilotos prontos naquela hora.
- "não precisa fazer todos em tela dividida".
- Slam tipográfico na abertura: reprovado mesmo tendo sido pedido; a pessoa
  preferiu o trecho sem insert.
- Print pequeno em cartão: "muito ruim"; virou organograma desenhado em vetor.
- Um player "AO VIVO" reaproveitado de outro vídeo não serviu; o pedido era
  grafismo mostrando cada etapa sendo instalada.

**Na skill:** regras de material real e de série variada na etapa 2, pilotos
antes da série na etapa 3, molde de brief que carrega o que foi reprovado.

### 3. Leitura e ritmo dos inserts

- Dois inserts "entram com muita informação e não dá tempo de acompanhar".
- Abertura reprovada duas vezes: "fica uns segundos parado e isso é um problema
  na retenção", "o número demora a se mexer". Aprovada com o dado na tela no
  quadro zero, número contando e digitação com cursor.
- Abertura feita a partir de referência: "não tá igual à referência, eu quero
  idêntica"; depois "a palavra anterior ainda tá na tela quando aparece a
  próxima, fica bagunçado". Um par de palavras por vez.

### 4. O rosto de quem fala

- Quadro congelado do rosto dentro de insert: "imagem da cara dele esquisita
  estática". Virou 0,9 s do bruto com ele sorrindo.
- Olho esbugalhado em dois inserts do mesmo vídeo.
- `dividida_foco_insert` cortou a cabeça.
- A pessoa quis ver o apresentador escrevendo um número no quadro; o corte
  mudou de take para mostrar isso.

### 5. Abertura

Aprovadas: vídeo escurecido com a frase central e o destaque na cor da marca;
texto fixo escolhido entre opções em PNG (em três vídeos, incluindo um carimbo
na cor da marca); com quem fala apontando para uma tela, texto menor embaixo e
quase sem escurecer.

### 6. Áudio

- Denoise piorou o áudio nas vezes em que foi feito: proibido.
- Voz em -24 LUFS por ganho fixo (a versão em -14,5 ficou alta).
- Batida: a primeira, 10 dB abaixo da voz, "diminui drasticamente". Aprovada a
  ~21 dB abaixo, com virada na frase da oportunidade.
- CTA só com o áudio sobre outra imagem: "meio nada a ver". Entra com a imagem,
  com whoosh e efeito de montagem.
- Whoosh: pedido em todos os anúncios da série.

### 7. Legenda

- Pedido de todo vídeo: legenda no vídeo inteiro, inclusive nos inserts, menos
  onde a arte escreve a fala ou não há espaço; e as palavras atrás de quem fala.
- Legenda escondida no teto escuro, fora da tela gravada: a pessoa não viu. Vai
  por cima da tela, no meio.
- Legenda sobre a arte: proibido; acima ou abaixo da janela.
- "100 vídeos por dia" no pedido, "conteúdos" no áudio: a escolha foi o áudio.
- "TIMES DE / I.A." quebrou feio: sigla nunca sozinha na segunda linha.
- Peso maior (Inter 800) pedido num dos vídeos.
- Karaokê palavra a palavra: "nunca vamos usar". Placa de largura total:
  "grotesco".

### 8. Operação

- A sessão caiu duas vezes no mesmo dia durante máscara e render; processos em
  segundo plano e agentes morreram junto. Render de camada disparado em segundo
  plano foi cancelado sozinho. Primeiro plano ou aba do Terminal.
- `novo_projeto.py --forcar` apagou `estilo.md` e `PLANO.md` aprovados no meio
  de uma série. Consertado: não apaga mais.
- A Vision parou de entregar quadros no meio de arquivo longo (4768 de 10533)
  sem erro. Consertado: blocos de 40 s com número exato de quadros.
- Dois inserts grudados na mesma borda deixaram um quadro do rosto.
  Consertado no render.
- "Helvetica Neue" no CSS saiu em Inter sem aviso; PNG de vídeo HDR falhou;
  `.mov` vertical com rotação que o ffprobe não mostra.
- Corte que inclui pausa encurtada desloca menos que a conta de cabeça
  (2,90 s contra 3,22 s): `tempo.py` sempre.
- A pessoa fala em tempo do vídeo que viu ("em 1:09") e conta os inserts pela
  ordem em que recebeu.
- Drive: houve reclamação de pastas criadas sem pedir. Pergunte a pasta.
- Inglês na resposta: reclamação duas vezes no mesmo dia.

## Ferramentas que eram reinventadas em cada projeto e agora são da skill

| Antes (em cada pasta) | Agora |
|---|---|
| `fabrica/tempo.py`, `fin2orig.py` | `scripts/tempo.py` |
| `fabrica/janelas.py` + `scratch/montar_lista.py` | `fabrica/janelas.json` + `scripts/montar_lista.py` |
| `scratch/com_voz.sh` | `scripts/com_voz.py` |
| filmagem por insert e partituras feitos à mão | `scripts/preparar_fabrica.py` |
| `analise/gerar-matte.sh` + `encaixa.py` + `legenda/recortes.sh` | `scripts/mascara.py` |
| `audio/gerar_batida_v2.py` (numpy) | `scripts/batida.py` (Python puro, mede e mixa) |
| `legenda/gerar.py` copiado de vídeo em vídeo | `scripts/gerar_legenda.py` + `legenda.json` |
| `legenda/montar.sh` | `scripts/montar_legenda.py` |
| `bruto-montado/` e `MONTAGEM.md` à mão | `scripts/montar_bruto.py` |
| `fabrica/ferramentas/print.js` e `gravar.js` (caminhos do Mac) | `scripts/capturar_pagina.py` + `pagina.js` |
| `rclone` à mão e conferência de tamanho | `scripts/entrega.py` |

## Pontos de melhoria que ficaram de fora (para decidir depois)

- **Velocidade por trecho.** Já pediram 1x só na abertura de um vídeo; a skill
  só faz velocidade uniforme e o trecho foi emendado por fora. Se voltar a
  acontecer, vale implementar no `plano.json`.
- **Banco de inserts reaproveitáveis** (botão, data, grupo, cadeado) catalogado
  por campanha, em vez de achar na pasta irmã.
- **Insert aprovado vira cena** em `assets/cenas/`, para a próxima série partir
  dele.
