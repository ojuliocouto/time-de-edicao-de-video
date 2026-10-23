# plano.json: o estado da edição

Todo o trabalho vive neste arquivo. Os MP4 são descartáveis: apagar todos e
rodar o render de novo devolve exatamente os mesmos arquivos.

## A regra que sustenta tudo

**Todo tempo dentro do plano.json se refere ao vídeo ORIGINAL, nunca a um
arquivo intermediário.**

Um insert não é "aos 8s do vídeo já cortado". É "aos 19,4s do original". O
`render.py` calcula sozinho onde isso cai depois dos cortes e da velocidade.

Por que isso importa na prática: reverter um corte da etapa 1 depois que os
inserts já estão montados custa uma linha. Os inserts e os zooms se
reposicionam sozinhos, porque nunca dependeram do arquivo intermediário. No
modelo comum, onde cada etapa exporta um MP4 que alimenta a próxima, o mesmo
pedido jogaria fora todo o trabalho de insert.

## Esquema

```json
{
  "fonte": "/caminho/absoluto/do/original.mp4",
  "meta": { "duracao": 84.32, "fps": 30.0, "largura": 1080, "altura": 1920 },
  "etapa_atual": "corte",
  "aprovado_ate": null,

  "corte": {
    "parametros": {
      "respiro": 0.15,
      "pausa_dramatica": 0.6,
      "cortar": ["gagueira", "comeco_falso", "hesitacao"],
      "corte_agressivo": false
    },
    "manter": [[0.0, 2.075], [3.725, 7.3]],
    "removidos": [
      { "de": 2.075, "ate": 3.725, "tipo": "pausa",
        "motivo": "pausa reduzida para 0.15s" },
      { "de": 12.40, "ate": 13.12, "tipo": "comeco_falso",
        "texto": "então o que acontece é",
        "motivo": "frase abandonada e refeita em seguida" }
    ]
  },

  "velocidade": { "modo": "uniforme", "fator": 1.3 },
  "zoom": [
    { "de": 15.90, "ate": 23.10, "tipo": "lento", "z": 1.12,
      "motivo": "take de 9s sem insert; o lento evita a imagem estagnar" }
  ],
  "inserts": [
    { "de": 6.20, "ate": 10.20,
      "arquivo": "inserts/tela-do-painel.mp4",
      "formato": "tela_cheia",
      "origem_ini": 0.0,
      "motivo": "ela fala do painel; mostrar a tela evita explicar por palavra" }
  ],
  "audio": null,
  "lettering": null
}
```

## Campo a campo

| Campo | O que é |
|---|---|
| `fonte` | caminho absoluto do original. o render lê daqui, sempre |
| `meta` | medido pelo ffprobe em `analisar.py`. não editar à mão |
| `etapa_atual` | onde o trabalho está |
| `aprovado_ate` | último portão aprovado pela pessoa. `null` = nenhum |
| `corte.manter` | **derivado**, nunca editado à mão. o render lê daqui |
| `corte.removidos` | a fonte de verdade. mexer aqui recalcula `manter` |
| `velocidade.fator` | 1.3 por padrão, uniforme no vídeo inteiro |
| `inserts` | lista; cada item tem seu proprio formato e janela |
| `zoom` | lista; janelas em timecode do original, fora dos inserts |
| `audio` | efeitos sonoros, gerados a partir dos inserts e zooms |
| `lettering` | objeto, um por vídeo; ver `references/edicao-lettering.md` |
| `efeitos_video` | lista; efeito de imagem na filmagem base, janela em timecode do original. Hoje só `pb` (preto e branco). Escrito por `plano.py efeito` |

`manter` e `removidos` são duas visões do mesmo fato. `removidos` é o que se
edita, `manter` é o que o ffmpeg consome. Editar `manter` direto quebra a
correspondência e o próximo comando do `plano.py` sobrescreve a mudança.

## Parâmetros e seus padrões

| Parâmetro | Padrão | O que faz |
|---|---|---|
| `respiro` | 0.15 | silêncio máximo mantido entre falas |
| `pausa_dramatica` | 0.6 | silêncio mantido antes de uma virada de raciocínio |
| `corte_agressivo` | false | libera a trava de cortar mais de 60% do vídeo |
| `velocidade.fator` | 1.3 | uniforme; a pessoa decide no portão se sobe |

## Travas embutidas

Constantes no topo do `plano.py`, valem inclusive contra o agente:

| Trava | Valor | Por quê |
|---|---|---|
| `BLOCO_MINIMO` | 0.12s | bloco menor que isso é inaudível e pica o áudio |
| `BLOCO_CURTO` | 0.25s | vira alerta, não erro: cabe uma palavra curta |
| `TOL_PALAVRA` | 0.08s | invasão máxima tolerada dentro de uma palavra |
| `CORTE_MAXIMO` | 60% | acima disso é sintoma de transcrição falhada |

## Inserts

Um vídeo tem **vários inserts de formatos diferentes**, cada um ligado só na
sua janela. Por isso `inserts` é lista, e o formato vive em cada item, não no
plano.

| Campo | O que é |
|---|---|
| `de`, `ate` | janela do insert, em timecode do **original** |
| `arquivo` | caminho do apoio; relativo resolve a partir da pasta de trabalho |
| `formato` | um dos oito de `references/edicao-inserts.md` |
| `origem_ini` | de que ponto do arquivo de apoio começar a tocar |
| `motivo` | por que este insert existe; aparece no portão de aprovação |
| `altura_pessoa` | opcional, só nos formatos react |

O `render.py` projeta `de` e `ate` do tempo do original para o tempo do vídeo
final, já cortado e acelerado. É isso que faz o insert continuar no lugar certo
quando um corte da etapa 1 muda depois.

**O insert toca em velocidade normal**, mesmo com o vídeo a 1,3x. Ele é material
de apoio, não fala acelerada. Se o arquivo acabar antes do fim da janela, a
base volta a aparecer e o render avisa.

**Formatos que combinam apoio com a filmagem** (tela dividida, vazado, react)
usam a filmagem **já cortada e acelerada**, não a bruta. A máscara de recorte
passa pelos mesmos cortes e pela mesma aceleração, senão o recorte descola da
imagem.

**Meta de densidade: um insert a cada 10s de vídeo final.** Não é regra fechada.
`plano.py resumo` confere e, quando não bate, manda perguntar se deve procurar
insert num banco ou seguir assim.

## Zoom

| Campo | O que é |
|---|---|
| `de`, `ate` | janela do zoom, em timecode do **original** |
| `tipo` | `seco`, `suave` ou `lento` |
| `z` | fator; 1.12 por padrão, ou seja 12% |
| `motivo` | por que este zoom existe; aparece no plano de aprovação |

**Insert não recebe zoom.** `plano.py zoom` recusa a lista inteira se algum
zoom invadir a janela de um insert, e o render desenha o zoom antes do insert,
de forma que o insert venceria mesmo se passasse.

**Regra de cobertura: take de rosto com mais de 5s precisa de zoom.** Take de
rosto é o que sobra do vídeo final depois de tirar as janelas de insert.
`plano.py resumo` lista todos e marca os que passam de 5s sem zoom.

## Som

```json
"audio": {
  "efeitos": [
    { "em": 6.20, "nome": "whoosh-short", "volume": 0.052,
      "motivo": "entrada do insert tela_cheia" }
  ],
  "biblioteca": "<skill>/assets/sfx",
  "nivel_fala": -36.9,
  "abaixo_da_voz": 6.0
}
```

`em` em timecode do **original**, como todo o resto. O bloco inteiro é gerado
por `plano.py som` a partir dos inserts e dos zooms secos, não é escrito à mão.

`volume` sai do nível de fala do próprio vídeo, mirando 6 dB abaixo. Volume
fixo não serve: ver `references/edicao-som.md`.

## Lettering

```json
"lettering": { "estilo": "caixa", "linhas": ["...", "..."],
               "posicao": "abaixo", "de": 0.0, "dur": 3.5 }
```

É um **objeto, não lista**: um lettering por vídeo. `de` em timecode do
original. Detalhes em `references/edicao-lettering.md`. Cada um será desenhado junto
com a pessoa quando a etapa for construída, seguindo a mesma regra: tempo
ancorado no original.
