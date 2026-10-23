# Etapa 7. Entrega

Todo comando começa com o prefixo abaixo, que acha a skill e escolhe o Python
(`python3` no Mac e no Linux, `python` no Windows, onde `python3` pode abrir a
Microsoft Store):

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python;
```

Só depois do "aprovado" da pessoa na legenda (portão 6).

## 7.1 Arquivo final

O legendado em resolução cheia já saiu da etapa 6
(`final/<NOME>-legendado.mp4`). Só refaça se algo mudou depois do portão 6:
corte, insert ou zoom mudou → render cheio, batida e `montar_legenda.py` de novo
(etapa 6.1 e 6.6); só texto da legenda mudou → só o `montar_legenda.py`.

## 7.2 Conferir e versão leve

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/entrega.py "<pasta>/final/<NOME>-legendado.mp4"
```

Recusa o que não é 1080x1920 ou está sem áudio, gera a versão 720p e imprime a
linha da entrega. Mande no chat a 720p; a pessoa leva o 1080 do Drive.

## 7.3 Drive

**Pergunte a pasta** (e se vai numa subpasta existente). Mesmo com destino já
usado no projeto, confirme numa frase ("subo na pasta dos criativos, como os
outros?"). Nunca crie pasta. O destino é o ID da pasta do Drive que a pessoa
indicar (a parte final do link da pasta).

Nome no padrão da pasta: `ADxx-tema-LEGENDADO.mp4` (ex.:
`AD-cara-de-ia-LEGENDADO.mp4`). Peça com mais de um arquivo
vai numa subpasta com o nome da peça (perguntando).

```bash
TEV=~/.claude/skills/time-de-edicao-de-video; PY=python3; [ "$OS" = Windows_NT ] && PY=python; $PY $TEV/scripts/entrega.py "<pasta>/final/<NOME>-legendado.mp4" --drive <id-da-pasta> --nome "<ADxx-tema-LEGENDADO.mp4>"
```

O script confere o tamanho no Drive contra o local. Para mandar por mensagem,
`--leve-no-drive` sobe também a 720p (a leve carrega melhor em link de mensagem).
Pegue o link com `rclone link "gdrive:<nome>" --drive-root-folder-id <id>`.

## 7.4 A mensagem de entrega

Na mensagem, em português:
- o link (ou o caminho) do arquivo e da versão leve;
- resolução, fps, duração e tamanho, e a frase de que vídeo curto em H.264 pesa
  pouco sem perder qualidade (já perguntaram "essa qualidade tá certa? só 46 MB");
- o que ficou de fora (zoom, batida, whoosh, se a pessoa dispensou) e o que ficou
  pendente (autorização de depoimento, material que ela vai mandar).

## 7.5 Fechar

- Registre o projeto na memória: pasta, o que a pessoa pediu de diferente, o que
  reprovou e o motivo, onde foi entregue. É disso que o próximo vídeo se
  alimenta.
- Não apague nada da pasta do vídeo: ajuste pedido depois da entrega reaproveita
  plano, inserts e legenda.
