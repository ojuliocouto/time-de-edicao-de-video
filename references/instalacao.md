# Instalação no Mac, no Windows e no Linux

O `preflight.py` mostra o comando exato de cada item que faltar no sistema em
que está rodando. Este arquivo explica a ordem e as armadilhas. Instale um item
por vez, com a aprovação da pessoa, e rode o pré-flight de novo no fim.

## O que a skill usa

| Item | Para quê | Obrigatório |
|---|---|---|
| Python 3.9+ | todos os scripts (só biblioteca padrão) | sim |
| ffmpeg e ffprobe, com libx264 e libvpx-vp9 | corte, render, máscara, legenda com alfa | sim |
| Node.js 18+ (npx, npm) | HyperFrames, captura de página | sim |
| HyperFrames + o Chrome dele | inserts e legenda | sim |
| um motor de transcrição | corte, partituras, legenda | sim |
| Pillow | lettering e emoji da etapa de lettering | não |
| swiftc (Mac) | recorte da pessoa pela Vision, 10x mais rápido | não |
| rclone com remote `gdrive` | subir no Drive | não |
| yt-dlp | baixar reels, posts e vídeos de referência | não |

Motor de transcrição, em ordem de preferência: **mlx-whisper** (só Mac com chip
Apple), **faster-whisper** (Mac, Windows e Linux) e **whisper.cpp** com o modelo
`ggml-large-v3-turbo.bin` (reserva). Os dois primeiros ficam num venv em
`~/.venv-whisper`, porque o Python do sistema (Homebrew, distro) recusa
`pip install` direto. A skill acha o venv sozinha.

## Mac

```bash
brew install python@3.12 ffmpeg node rclone yt-dlp
python3 -m venv ~/.venv-whisper
~/.venv-whisper/bin/python -m pip install mlx-whisper faster-whisper pillow
npx --yes hyperframes --version
npx --yes hyperframes browser ensure
xcode-select --install
```

`xcode-select` abre uma janela do sistema: a pessoa clica. Em Mac com Intel,
tire o `mlx-whisper` do pip.

## Windows

O Claude Code no Windows roda os comandos no Git Bash. Use `python`, não
`python3`.

```bash
winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
```

**Feche e abra o Claude** depois dos `winget`: o PATH novo só vale para
programas abertos depois. Instale os três de uma vez e reabra uma vez só.

```bash
winget install -e --id Rclone.Rclone --accept-source-agreements --accept-package-agreements
winget install -e --id yt-dlp.yt-dlp --accept-source-agreements --accept-package-agreements
python -m venv ~/.venv-whisper
~/.venv-whisper/Scripts/python.exe -m pip install faster-whisper pillow
npx --yes hyperframes --version
npx --yes hyperframes browser ensure
```

Armadilhas:
- `python` abre a Microsoft Store: é o atalho falso do Windows. Configurações >
  Aplicativos > Configurações avançadas de aplicativos > Aliases de execução de
  aplicativo: desligue os dois "Instalador de aplicativo" (python.exe e python3.exe).
- `winget` não existe: Windows 10 antigo; atualize o "Instalador de Aplicativo"
  pela Microsoft Store.
- O `winget` às vezes abre a janela de permissão do Windows: a pessoa clica em Sim.
- Recorte da pessoa: sem Mac, é o remove-background do HyperFrames, ~1 quadro
  por segundo na CPU (5 heróis de legenda, ~4 min; máscara de 20 s de insert, ~10 min). Use sempre `--janelas`. Com placa NVIDIA, o próprio
  remove-background aceita `--device cuda`.
- Pouca memória (8 GB): render do HyperFrames com `--workers 1` e programas fechados.
- Antivírus segurando executável recém-baixado: primeiro suspeito quando algo
  falha sem mensagem.

## Linux (Ubuntu, Debian e derivados)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip ffmpeg rclone yt-dlp
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs
python3 -m venv ~/.venv-whisper
~/.venv-whisper/bin/python -m pip install faster-whisper pillow
npx --yes hyperframes --version
npx --yes hyperframes browser ensure
```

O Node da distro costuma ser velho demais para o HyperFrames: use o NodeSource
(acima) ou o nvm. Fedora: `dnf` no lugar de `apt` (`ffmpeg` vem do RPM Fusion).
O Chrome do HyperFrames pode pedir bibliotecas do sistema; o `browser ensure`
diz quais. Fonte do lettering: `sudo apt install -y fonts-liberation`
(opcional; sem ela o lettering usa a Inter da skill).

## Primeira transcrição

O faster-whisper baixa o modelo `large-v3-turbo` (~1,6 GB) na primeira vez, do
Hugging Face. Avise que demora. Em máquina fraca, o modelo `small` é bem mais
rápido e erra mais nome próprio: `FASTER_WHISPER_MODELO=small`.

## Drive

`rclone config`, interativo, abre o navegador para o login no Google. A pessoa
roda. O remote tem que se chamar `gdrive`.
