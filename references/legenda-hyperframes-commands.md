# Comandos e armadilhas

Flags verificadas nesta máquina. Cada armadilha aqui já custou uma rodada perdida.

## Transcrição

```bash
npx hyperframes transcribe VIDEO.mp4 -m large-v3 -l pt --timeout 900000
```

**Armadilha:** o padrão é `small.en`, um modelo só de inglês. Rodado em áudio em português ele não erra, ele **inventa**: devolve frases plausíveis em inglês que não têm relação com a fala, e nada indica o problema. `large-v3` é o único multilíngue da lista. Primeira execução baixa ~3 GB.

Saída: `transcript.json` **ao lado do arquivo de entrada**, não na raiz do projeto. Verificado: `transcribe sub/clipe.mp4` grava em `sub/transcript.json`. Duas transcrições de arquivos diferentes na mesma pasta sobrescrevem uma à outra sem aviso; renomeie a primeira antes de rodar a segunda.

Formato: array de `{text, start, end}`, uma entrada por palavra.

**Palavra errada é diferente de tempo errado.** O modelo troca nome próprio por palavra comum de som parecido, com confiança alta e sem sinal nenhum: `Claude` vira `cloud`, `IA` vira `ar`. Releia a transcrição procurando nome de produto, marca, pessoa e sigla, e corrija antes de desenhar. Registre cada correção em `transcriptCorrections` no plano, marcando se foi confirmada por áudio ou apenas deduzida do sentido da frase.

## Recorte do sujeito

Use `scripts/make_cutout.py`, que já aplica o controle de custo. Chamada direta, quando precisar:

```bash
npx hyperframes remove-background TRECHO.mp4 -o recorte.webm --quality best
```

- Roda a **~1,2 quadros por segundo** (Apple Silicon, CoreML). CoreML já é escolhido sozinho; `--info` confirma. Não existe acelerador a ligar.
- Primeira execução baixa ~175 MB, e o servidor é lento.
- Saída `.webm` é VP9 com `alpha_mode=1`. O `pix_fmt` aparece como `yuv420p` mesmo tendo alpha, então não use isso como teste.

## Ler o alpha de um WebM

```bash
ffmpeg -ss 14 -c:v libvpx-vp9 -i recorte.webm -frames:v 1 \
  -vf "alphaextract,scale=270:338" -f rawvideo -pix_fmt gray -
```

**Armadilha:** sem `-c:v libvpx-vp9` **antes** do `-i`, o `alphaextract` falha com `Requested planes not available`. O decodificador padrão descarta o canal alpha. Vale para qualquer ferramenta que leia esses arquivos, inclusive `scripts/subject_envelope.py`.

## Render

```bash
npx hyperframes render -o saida.mp4 -q high --crf 18
npx hyperframes render -c OUTRA.html -o saida.mp4 -q high --crf 18
```

- **Armadilha:** sem `-q high --crf 18` o padrão sai em ~120 kbps, inutilizável.
- Padrão de taxa de quadros é **30, independente da origem**. Decida isso antes de gerar qualquer recorte.
- **Origem mais lenta que 30 (24 ou 25 fps, o caso comum de câmera e PAL):** fixe o render na taxa da origem, não o contrário. De 25 para 30 não existe descarte de quadro possível e interpolar é proibido. Use `-f 25` no render, ou `data-fps="25"` no elemento raiz da composição, que é o que o `render` lê por padrão.
- `render` aceita `-c`; `check` e `snapshot` **não aceitam**, sempre olham o `index.html`.
- Referência de tempo medida: 15 s a 1080x1350 em `-q high` = **82 s**.

## Render longo trava com recorte do sujeito

**Verificado em 94 s / 2347 quadros, com 4 recortes de alpha na composição:** o render MP4 completo **trava** na captura, sempre num quadro em que um recorte está ativo (`Sequential drawElement capture stalled`, sem erro de compilação). Aconteceu duas vezes, em pontos diferentes. `--workers 3` avança muito mais (2296 de 2347) mas também para no último recorte.

Não é o número de vídeos com alpha em si: uma composição de teste com 7 s e dois recortes renderizou normal. O gatilho é a combinação de duração longa com recorte.

**Solução verificada, e é a mais rápida também:** tire os recortes da composição e componha fora.

1. Renderize duas camadas de tipografia com alpha, sem vídeo base e sem recorte: uma só com `#cc-layer-back`, outra só com `#cc-layer-front` (esconda a outra com `display:none`). Em 94 s isso levou 50 s e 79 s, sem travar.
2. Junte tudo com `scripts/composite_overlay.py`, na ordem: origem, tipografia de trás, recortes, tipografia da frente. Um recorte de trecho entra como `arquivo.webm@INICIO` e o script cuida do `-itsoffset` e da janela `enable` sozinho, lendo a duração do arquivo.

```bash
python3 scripts/composite_overlay.py bruto.mp4 \
  tras.webm recorte-a.webm@7.55 recorte-b.webm@27.87 frente.webm -o final.mp4
```

Chamada equivalente à mão, se precisar ajustar algo fora do script:

```bash
ffmpeg -y -i bruto.mp4 \
  -c:v libvpx-vp9 -i tras.webm \
  -itsoffset 7.55 -c:v libvpx-vp9 -i recorte-a.webm \
  -c:v libvpx-vp9 -i frente.webm \
  -filter_complex "[0:v][1:v]overlay=0:0:eof_action=pass[a];\
[a][2:v]overlay=0:0:eof_action=pass:enable='between(t,7.55,10.71)'[b];\
[b][3:v]overlay=0:0:eof_action=pass[v]" \
  -map "[v]" -map 0:a -c:a aac -b:a 128k \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -movflags +faststart final.mp4
```

Tempo total medido em 94 s: 50 s + 79 s de camadas + 149 s de composição = **~4,6 min**, contra um render completo que não termina.

## Render com alpha

```bash
npx hyperframes render -c .work/camada.html -o .work/camada.webm --format webm --quiet
```

Exige uma composição própria, com `background: transparent` no `html, body` e **sem o vídeo base**. Com o vídeo base o arquivo sai 100% opaco e não serve de camada.

**Guarde essas composições fora da raiz do projeto**, em `.work/` por exemplo. Dois arquivos com `data-composition-id` no mesmo nível disparam `multiple_root_compositions`, que é **erro** e derruba o `check` inteiro, inclusive o do `index.html` que você quer validar. Verificado.

```bash
npx hyperframes render -c .work/camada-tras.html -o .work/camada-tras.webm --format webm --workers 3
```

**Armadilha grave:** uma composição que contém um vídeo com alpha (o recorte do sujeito) **trava** no render com alpha, sem erro de compilação, parando em algum quadro e estourando o tempo limite. Verificado nos dois formatos, `webm` e `mov`. Para profundidade, tire o recorte da composição e componha em camadas.

Referência de tempo medida: 15 s de tipografia pura = **17 a 22 s** por camada.

## Composição em camadas

Use `scripts/composite_overlay.py`. Ordem de baixo para cima:

```bash
python3 scripts/composite_overlay.py bruto.mp4 \
  camada-tras.webm recorte.webm camada-frente.webm -o final.mp4
```

Resultado verificado como visualmente idêntico ao render completo, profundidade incluída. Tempo medido em 15 s: 17 s + 18 s de camadas + 36 s de composição = **71 s**, contra 82 s do render completo. O ganho é pequeno.

## Converter altura de letra em `top` de CSS

Posicionar um herói pela sobreposição exige saber onde a base das maiúsculas cai, e o CSS só aceita `top`. Medido na Anton, que é a display que a skill embarca:

| | valor |
|---|---|
| altura de maiúscula | 0,727 em |
| ascendente | 0,80 em |
| caixa de linha da fonte | ~1,55 em |

Com `line-height: 0.92`, para um corpo `S` e um `top` `T`:

- topo das maiúsculas = `T + 0,033·S`
- base das maiúsculas = `T + 0,76·S`

Para pôr a base num `y` alvo: `T = y − 0,76·S`.

**Isso posiciona, não mede.** A fração coberta é área e não altura, então depois de posicionar rode `scripts/occlusion.py`. Estimativa na mão erra por 2 a 8 vezes.

## Verificação

```bash
npx hyperframes check --at 1.2,3.4,6.4,12.4
npx hyperframes snapshot --at 6.4,14.4 --no-end -o .work/snaps
npx hyperframes snapshot --zoom "#cc-010" --zoom-scale 3
```

`snapshot` também escreve um `contact-sheet.jpg`, que é a forma mais barata de julgar o conjunto.

**Armadilha do `check`:** ele mede a caixa de fonte inteira, não a tinta visível. A Anton ocupa ~1,55em, ou seja, ~46 px acima das maiúsculas em corpo 150. Qualquer lockup de apoio mais herói acusa `content_overlap` mesmo com as letras a 20 px de distância. Confirme no snapshot antes de mexer no layout; se as letras estiverem separadas, use `data-layout-allow-overlap` no span do texto, não no clip que o envolve. Mesma lógica para `data-layout-allow-occlusion` no texto que fica atrás do sujeito.

## Quando uma correção parece não ter funcionado

Verificado nesta máquina: o `.transcode-cache/` **não** serve mídia velha. Substituindo um arquivo pelo mesmo nome com conteúdo diferente, o próximo `snapshot` já mostra o novo, sem limpar nada. Não perca tempo culpando o cache.

O erro a evitar é outro, e é de diagnóstico: ver o defeito intacto depois de uma correção e **inventar uma explicação para o pipeline** em vez de medir. A ordem certa é sempre a mesma:

1. Confira o artefato direto com `ffmpeg` ou `ffprobe`, fora do HyperFrames. O arquivo em disco é a verdade.
2. Se o arquivo está certo e o quadro está errado, aí sim o problema é a composição.
3. Use `snapshot --zoom` na região exata antes de concluir qualquer coisa. Contact sheet em miniatura esconde a natureza do defeito: uma borda reta e uma silhueta de cabelo parecem a mesma mancha em 300 px de largura.

## Preview

```bash
npx hyperframes preview --background
npx hyperframes preview --status
npx hyperframes preview --stop
```

O preview injeta atributos `data-hf-id` nos elementos do arquivo em disco. Edições por busca e substituição de texto param de bater depois disso: use o `id` como âncora, não a linha inteira.
