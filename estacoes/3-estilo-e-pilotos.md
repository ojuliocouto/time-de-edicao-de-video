# Etapa 3. Estilo e pilotos (até o portão 3)

Todo comando começa com o prefixo abaixo, que acha a skill e escolhe o Python
(`python3` no Mac e no Linux, `python` no Windows, onde `python3` pode abrir a
Microsoft Store):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python;
```

## 3.1 Montar a fábrica

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/novo_projeto.py "<pasta>/fabrica" --nome "<nome do vídeo>"
```

Cria `estilo.md`, `base.css` (os tokens do estilo, que vão para dentro de cada
insert), `banco/`, `inserts/`, `renders/`, fontes, `gsap.min.js` e
`primitivas.js`. O plano aprovado continua em `<pasta>/PLANO.md` (um nível
acima da fábrica); o script só escreve o modelo ali se ele ainda não existir. **Nunca apaga**
estilo, plano, registro ou manifesto que já existam (o antigo `--forcar` apagou
os de um anúncio no meio da série).

## 3.2 Ler as referências de verdade

A pessoa manda vídeos de referência de motion e pede "analise com calma, demore
o tempo que for". Ler o título da referência não é ler a referência.

1. Baixe o vídeo de cada referência para `fabrica/referencias/`: `yt-dlp -o
   "<pasta>/fabrica/referencias/ref1.%(ext)s" "<link da referência>"` (link
   curto também serve). Sem `yt-dlp` (o pré-flight mostra como instalar) ou se
   ele falhar, abra o link no navegador e pegue o `.mp4` do `<video>` da página.
2. Folha de contato densa de cada um e quadros grandes dos momentos-chave:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/folha_de_contato.py "<pasta>/fabrica/referencias/ref1.mp4" -o "<pasta>/fabrica/referencias/folha-ref1.png" --quadros 16
```

3. Escreva o que a referência faz, mecanismo por mecanismo (fundo, tipo,
   peso, entrada de cada elemento, câmera, transição), em
   `fabrica/referencias/PESQUISA.md`. Extraia primitivas, não a cena
   (`references/fabrica-catalogo.md`, "Ao ler um tutorial").

Quando a pessoa diz "idêntica à referência", é idêntica: mesma fonte, mesma
grade, mesmo zoom em degrau. Numa abertura real, a versão "inspirada" foi
reprovada duas vezes.

## 3.3 Travar o estilo

`fabrica/estilo.md` trava **só** paleta, tipografia, acento e grafia da
campanha. Fundo, efeito e mecanismo variam em cada insert: "não é pra se
limitar só nesse design... a ideia é ir variando e só mantendo as cores da id
visual e paleta". Texto cinético é um dispositivo entre vários, não a
base de todos.

Padrão que entra em todo `estilo.md`, salvo pedido diferente:
- base neutra (preto, branco, cinza) e detalhe na cor da marca (o padrão da
  skill é o laranja `#F94E03`; troque pela cor da sua marca);
- fonte parecida com a da legenda (Inter para apoio, Anton para impacto), salvo
  quando a referência pede outra; "Helvetica Neue" no CSS sai em Inter no
  render sem aviso: declare `@font-face` com arquivo local;
- grafia: "I.A." ou "IA" conforme a campanha;
  "conteúdos" no lugar de "vídeos" quando o sentido permite.

Leia `references/fabrica-ciclo.md` (o ciclo de seis passos) e
`references/fabrica-acabamento.md` antes de escrever o estilo.

## 3.4 Dois pilotos

Escolha dois inserts do plano que cubram mecanismos diferentes e construa você
mesmo, com o mesmo ciclo e as mesmas checagens da etapa 4, nesta ordem:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/preparar_fabrica.py --pasta "<pasta>"
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/novo_projeto.py "<pasta>/fabrica" --insert <piloto-1>
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/novo_projeto.py "<pasta>/fabrica" --insert <piloto-2>
```

Construa, confira e renderize cada um como manda `agentes/fabricante-de-insert.md`
("Construir", "Conferir", "Renderizar"). Depois, a versão com a voz:

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/com_voz.py --pasta "<pasta>" <piloto-1> <piloto-2>
```

Na conversa, um embaixo do outro: a frase do trecho e o vídeo logo abaixo.

## 3.5 Portão 3

- "ficou legal" com ressalva ("só não precisa fazer todos em tela dividida"):
  a ressalva vai para o `estilo.md` e para o brief dos agentes.
- "não gostei da estética": a versão vai para `fabrica/_versoes/v1-<nome>/`,
  você lê as referências novas e refaz **os pilotos**, não a série.
- Inserts que não agradam em lote: passe a fazer um por um, cada aprovado
  guardado fora do vídeo, e só monte quando todos estiverem aprovados.

Os pilotos aprovados viram o molde que os agentes copiam (etapa 4).
