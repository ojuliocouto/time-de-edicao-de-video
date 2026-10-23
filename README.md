# Time de edição de vídeo

Skill do Claude Code que transforma a filmagem bruta de quem fala para a câmera num criativo vertical pronto, cortado, com inserts, som e legenda. Ela coordena um pequeno time de subagentes (fabricantes de insert, conferente de corte e revisor final) e para num portão de aprovação ao fim de cada etapa. Tudo roda na sua máquina, com ffmpeg, HyperFrames e transcrição local.

**As 8 etapas:** preparo, corte e 1,3x, plano de inserts, estilo e pilotos, fabricação dos inserts, montagem (zoom, whoosh e batida), legenda cinematográfica e entrega.

## Como instalar

Cole no Claude Code:

```
Baixe o repositório https://github.com/ojuliocouto/time-de-edicao-de-video e instale globalmente a skill na pasta ~/.claude/skills/time-de-edicao-de-video
```

Depois:

```
Roda o pre-flight do time de edição de vídeo e instala o que estiver faltando
```

Funciona em Mac, Windows e Linux, e os testes rodam nos três sistemas a cada mudança (GitHub Actions).

## Créditos

A legenda é adaptada da skill aberta de audrey-560, sob licença MIT (texto da licença em `references/legenda-LICENSE.txt`).
