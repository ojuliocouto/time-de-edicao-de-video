# O catálogo

Uma arte é **conteúdo × efeito**. Dez conteúdos e onze efeitos dão mais de cem
combinações sem precisar de um catálogo gigante.

## Eixo do conteúdo: o que está na arte

| Tipo | Para quando o roteiro tem | De onde partir |
| --- | --- | --- |
| Palavra | uma frase ou nome que precisa pesar | **blueprint** `titlecard-reveal`, `kinetic-type-beats` |
| Número | dado, preço, porcentagem, contagem | `mk-progress-stat`, `apple-money-count`, `number-wheel` |
| Tela de produto | uma interface, um site, um app | `browser-device-stage`, `device-frame-stage`, `multi-device-splay` |
| Passo a passo | uma sequência de etapas | `hw-pipeline`, `flowchart-vertical`, `mk-specs-list` |
| Terminal | código, comando, log | `terminal-simulator`, `code-snippet-*` |
| Objeto em cena | uma imagem real que precisa se mexer | **regra** de keyframes de câmera sobre a imagem |
| Ligação | coisas que se conectam ou convergem | `constellation-hub`, `arc-motion-path`, `avatar-cloud` |
| Destaque em print | um print real que precisa de marcação | `vox-annotate`, `marker-highlight`, e a família `hw-*` inteira: `hw-callout-circle`, `hw-underline`, `hw-arrow`, `hw-box-label` |
| Acúmulo | excesso, bagunça, "muita gente faz assim" | `overwhelm-surround`, `notification-cascade` |
| Comparação | antes e depois, um contra o outro | `comparison-split`, `before-after-wipe`, `split-tilt-cards` |

### Nem tudo nessa coluna se instala

São **três origens diferentes** e confundir uma com a outra é erro garantido:

| Origem | Como se usa | Como reconhecer |
| --- | --- | --- |
| **Componente ou bloco** | `npx hyperframes add <nome>` e repinta | aparece em `npx hyperframes catalog` |
| **Blueprint** | você **lê** e implementa; não instala | mora em `hyperframes-animation/blueprints/` |
| **Regra** | você **lê** e implementa; não instala | mora em `hyperframes-animation/rules/` |

Marcados acima com **blueprint** e **regra**. `titlecard-reveal`,
`kinetic-type-beats` e `card-morph-anchor` **não são instaláveis**: rodar
`hyperframes add` neles dá erro.

Na dúvida, o comando resolve:

```bash
npx hyperframes catalog | grep "^<nome> "     # achou = instalavel
find ~/.claude/skills/hyperframes-animation -name "<nome>.md"   # achou = blueprint ou regra
```

## Eixo do efeito: como ela se mexe

Os treze têm primitiva em `primitivas.js`. Nenhum buraco conhecido.

| # | Efeito | Primitiva | Origem |
| --- | --- | --- | --- |
| 1 | Peso misto na frase | `grifo` | BeTheCut |
| 2 | Escrita progressiva | `palavrasSubindo`, `palavrasDeslizando` | BeTheCut |
| 3 | Troca no mesmo lugar | `trocaNoLugar` | catálogo, `kinetic-type-swap` |
| 4 | Objeto flutuando | `cardSubindo` | BeTheCut |
| 5 | Um vira muitos | `umViraMuitos` | catálogo, `stagger-lattice` |
| 6 | Camadas separando | `camadasSeparando` | catálogo, `camera-rig-depth-stack` |
| 7 | Trajetória | `linhaComPonto` | BeTheCut |
| 8 | Giro que transforma | `giroQueTransforma` | **regra** `card-morph-anchor`, não instalável |
| 9 | Emissão | `brilho` | BeTheCut |
| 10 | Convergência | anéis contra-girando | BeTheCut |
| 11 | Revelador móvel | ver `cenas/revelador-movel.html` | construído do zero |
| 12 | Palavra que carimba | `carimba` | guia MOTION VOX STYLE |
| 13 | Lista que envelhece | `listaEnvelhece` | guia MOTION VOX STYLE |

Os dois últimos entraram depois. **Carimbar não é o mesmo que entrar subindo:**
o `palavrasSubindo` traz a palavra de fora do quadro, o `carimba` pousa em cima
da posição que ela já ocupa. Serve para a palavra que precisa pesar sozinha.

**A lista que envelhece resolve de graça o buraco de tela vazia:** o item novo
entra e o anterior é rebaixado, não removido. Nunca existe um instante em que a
coisa velha já saiu e a nova ainda não chegou.

Paleta **não entra aqui**. Cor é decisão de projeto: as referências que geraram
esta lista têm fundo preto, branco, lilás, cinza, vermelho e bege, sem padrão.

**Colagem** (recorte em preto e branco, forma chapada, papel texturizado) não é
efeito, é tratamento visual, e vai para o `estilo.md`.

## Eixo da câmera

`aproxima` e `trocaCena` fazem a câmera 2D em pernas encadeadas: aproximação
lenta, aproximação rápida, e a saída que sobe a cena inteira. Cada perna tem que
terminar antes de a próxima começar.

Para voo em 3D de verdade, com pouso resolvido por trigonometria em vez de pose
chutada, ver `cenas/voo-3d-tipografia.html`.

## As cenas guardadas

| Cena | Arquivo | O que combina |
| --- | --- | --- |
| **Revelador móvel** | `cenas/revelador-movel.html` | máscara suave móvel, palavra achada, frase que se monta |
| **Voo 3D por tipografia** | `cenas/voo-3d-tipografia.html` | planos em ângulo reto, câmera pousando, foco entrando e saindo |
| **Motion limpo de SaaS** | `cenas/motion-limpo-saas.html` | quatro cenas: dor, órbita de apps, medidor caindo, solução |
| **Quatro efeitos** | `cenas/quatro-efeitos.html` | uma cena por efeito: troca, espalha, separa, transforma |

Leia antes de montar algo do zero. A chance de já existir uma cena parecida é
alta, e a cena carrega a decisão de ordem e ritmo que a lista de primitivas não
carrega.

## Acabamento não é efeito

`grain-overlay`, `vignette`, `freeze-frame-dressing`, `organic-light-leak-overlay`
e `ink-bleed-reveal` não entram em nenhum dos dois eixos: são tratamento, e o
tratamento é decisão de `estilo.md`. Ver `fabrica-acabamento.md`.
