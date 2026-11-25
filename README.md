# Video Editing Team (`time-de-edicao-de-video`)

A [Claude Code](https://claude.com/claude-code) skill that turns raw talking-head footage into a finished vertical video ad: cut, sped up, with inserts, sound design and cinematic captions. It runs as a small production team of subagents coordinated by Claude, and it stops at an approval gate after every stage so a human signs off before anything moves on.

Everything runs on your own machine with ffmpeg, HyperFrames and a local speech-to-text engine. It works on macOS, Windows and Linux, and the test suite runs on all three on every push.

> **Language note:** the skill itself (instructions, stage manuals, script messages) is written in Brazilian Portuguese, and Claude talks to you in Portuguese while it runs. This README is in English so anyone can evaluate and install it.

## What it is

- A workflow skill for Claude Code. You give Claude the raw footage and the script, and Claude runs the whole edit through 8 stages.
- A set of Python scripts (standard library only) that do the deterministic work: analysis, cut plan, render, audits, captions and delivery checks.
- A production process tuned on a real series of video ads, with every rule traced back to a real rejection (see `references/licoes.md`).

## What it is not

- It is not a video editor with a UI. You talk to Claude; Claude edits.
- It is not for videos built from scratch in HTML or animation. For that, use HyperFrames directly.
- It is not a cloud service. No footage leaves your machine, except an optional upload to a Google Drive folder that you choose.
- It does not invent facts. Numbers, prices and dates on screen must come from a source.

## How it works

```
0 Prep -> 1 Cut and 1.3x -> [G1] -> 2 Insert plan -> [G2] -> 3 Style and pilots -> [G3]
  -> 4 Insert production -> [G4] -> 5 Assembly (zoom, whoosh, beat) -> [G5] -> 6 Captions -> [G6] -> 7 Delivery
```

`[Gn]` is an approval gate. Claude stops, sends you the preview and waits for "approved". You can relax this ("build the plan and keep going without my approval"); Claude then records each decision it took for you in `DECISOES.md`.

| Stage | What happens |
|---|---|
| 0. Prep | Normalizes the raw footage to 1080x1920 and the voice to -24 LUFS with a fixed gain (no denoise, no compressor). Can splice two takes, such as the body of one video and the call to action of another. |
| 1. Cut and 1.3x | Removes pauses above 0.15 s, applies a uniform 1.3x speed-up and fixes stutters and false starts. Every speech cut is checked by an isolated transcription of that segment. |
| 2. Insert plan | Writes `PLANO.md` and `fabrica/janelas.json`: where each insert goes, in final-video time. Your requests go in as you wrote them. |
| 3. Style and pilots | Locks palette, typography and accent in `estilo.md`, then renders 2 pilot inserts for you to approve the look. |
| 4. Insert production | 4 to 6 "insert maker" subagents build the inserts in parallel, 2 to 4 each. Claude checks every render before you see it. |
| 5. Assembly | Places the inserts, adds zoom on long face shots, a whoosh on every insert entry and a low background beat, then renders once at full resolution. |
| 6. Captions | Cinematic captions over the whole video, with selected words placed behind the speaker's head using a person cutout. |
| 7. Delivery | Final checks, a light version for sharing, and an optional upload to the Drive folder you name. |

### The team

| Role | Job | File |
|---|---|---|
| Claude (orchestrator) | Talks to you, decides, assembles, checks, delivers | `SKILL.md` |
| Stage manuals | Step-by-step commands for each stage | `estacoes/` |
| Insert maker (subagent) | Builds 2 to 4 inserts, in parallel with the others | `agentes/fabricante-de-insert.md` |
| Cut checker (subagent) | Verifies each speech cut against an isolated transcription | `agentes/conferente-de-corte.md` |
| Final reviewer (subagent) | Watches the assembled video as the viewer would and reports problems | `agentes/revisor-final.md` |

Subagents never talk to you. Claude reviews their output before sending anything.

### Partial jobs

Stage 0 always runs. After it, you can jump in:

| Request | Minimum input | Stages |
|---|---|---|
| Cut and speed up only | the raw footage | 0, 1 and 7 |
| Inserts only | the final video and `fabrica/janelas.json` | 3 and 4 |
| Captions only | the finished video, without burned-in captions, at 1080x1920 | 6 and 7 |

## Prerequisites

| Item | Used for | Required |
|---|---|---|
| [Claude Code](https://claude.com/claude-code) | runs the skill | yes |
| Python 3.9+ | all scripts (standard library only) | yes |
| ffmpeg and ffprobe, with libx264 and libvpx-vp9 | cutting, rendering, masks, captions with alpha | yes |
| Node.js 18+ (npx, npm) | HyperFrames and page capture | yes |
| [HyperFrames](https://github.com/heygen-com/hyperframes) and its bundled Chrome | inserts and captions | yes |
| A transcription engine | cuts, insert timing, captions | yes |
| Pillow | lettering and emoji | no |
| swiftc (macOS) | person cutout via Apple Vision, about 10x faster | no |
| rclone with a remote named `gdrive` | upload to Google Drive | no |
| yt-dlp | download reference reels, posts and videos | no |

Transcription engine, in order of preference: **mlx-whisper** (Apple silicon only), **faster-whisper** (macOS, Windows and Linux) and **whisper.cpp** with `ggml-large-v3-turbo.bin` as a fallback. The Python engines live in a virtual environment at `~/.venv-whisper`; the skill finds it automatically.

No API keys and no paid services are required. The first transcription downloads the `large-v3-turbo` model (about 1.6 GB) from Hugging Face.

## Installation

### Option 1: let Claude do it

Paste this into Claude Code:

```
Download the repository https://github.com/ojuliocouto/time-de-edicao-de-video and install the skill globally in ~/.claude/skills/time-de-edicao-de-video
```

Then:

```
Run the video editing team pre-flight and install whatever is missing
```

The pre-flight shows the exact install command for each missing item on your operating system. Claude installs them one at a time, with your approval.

### Option 2: manual

```bash
git clone https://github.com/ojuliocouto/time-de-edicao-de-video ~/.claude/skills/time-de-edicao-de-video
```

Then check your machine:

```bash
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/preflight.py
```

On Windows, use `python` instead of `python3`. The pre-flight exits with 0 when every required item is ready and with 1 when something is missing.

Full per-system instructions and known pitfalls (Windows Store Python alias, PATH refresh after `winget`, old Node on Linux distros) are in [`references/instalacao.md`](references/instalacao.md).

### macOS quick setup

```bash
brew install python@3.12 ffmpeg node rclone yt-dlp
python3 -m venv ~/.venv-whisper
~/.venv-whisper/bin/python -m pip install mlx-whisper faster-whisper pillow
npx --yes hyperframes --version
npx --yes hyperframes browser ensure
xcode-select --install
```

On Intel Macs, remove `mlx-whisper` from the pip command.

### Windows quick setup (Git Bash)

```bash
winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
```

Close and reopen Claude Code so the new PATH takes effect, then:

```bash
python -m venv ~/.venv-whisper
~/.venv-whisper/Scripts/python.exe -m pip install faster-whisper pillow
npx --yes hyperframes --version
npx --yes hyperframes browser ensure
```

### Linux quick setup (Ubuntu, Debian)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip ffmpeg rclone yt-dlp
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs
python3 -m venv ~/.venv-whisper
~/.venv-whisper/bin/python -m pip install faster-whisper pillow
npx --yes hyperframes --version
npx --yes hyperframes browser ensure
```

### Google Drive (optional)

Run `rclone config` and create a remote named `gdrive`. The login opens in your browser. The skill never creates Drive folders: it only uploads to the folder you name.

## Usage

In Claude Code, from any folder:

```
Edit this video with the video editing team: ~/Videos/my-ad/raw.mp4, the script is in ~/Videos/my-ad/script.txt
```

Claude creates one working folder per video, runs the pre-flight once per session, and starts at stage 0. Reply at each gate with "approved" or with numbered changes ("1. ok, 2. swap insert 3 for a screenshot").

## Repository layout

| Path | Contents |
|---|---|
| `SKILL.md` | Entry point: process, gates, team and the non-negotiable rules |
| `estacoes/` | One manual per stage, `0-preparo.md` to `7-entrega.md` |
| `agentes/` | Briefs for the three subagents |
| `scripts/` | Python scripts for every stage; `comum.py` holds the OS-specific parts |
| `assets/` | Fonts (Anton, Inter), GSAP, scene templates and sound effects |
| `references/` | Detailed references for cutting, inserts and captions, plus lessons learned and installation |
| `tests/` | Test runner and a synthetic voice sample |
| `.github/workflows/` | CI that installs everything and runs the tests on Ubuntu, Windows and macOS |

## Tests

```bash
python3 tests/rodar.py --rapido    # static, unit and integration tests, no render
python3 tests/rodar.py             # everything except speech, HyperFrames and Chrome
python3 tests/rodar.py --completo  # full suite, with speech, HyperFrames and Chrome
```

Run the tests after any change to the skill. The GitHub Actions workflow runs the full suite on Ubuntu, Windows and macOS on every push, using the same install steps as `references/instalacao.md`.

## Security and privacy

- All processing is local. Footage, transcripts and renders stay in the per-video folder you choose.
- Network access happens only for: installing dependencies, the one-time transcription model download from Hugging Face, HyperFrames' bundled Chrome, page captures and reference downloads you ask for, and the optional rclone upload to Google Drive.
- The repository contains no API keys, tokens or credentials, and the skill needs none. The Drive login is handled by rclone in your browser.
- The test audio (`tests/assets/fala.m4a`) is synthetic speech generated with espeak-ng. It contains no real person's voice.
- The skill refuses to work around its own safety checks. When a script refuses, the message says which known failure it is preventing.

## License

This repository does not include a project-wide license yet. Bundled third-party components keep their own licenses:

| Component | License | File |
|---|---|---|
| Caption engine, adapted from Audrey's open skill | MIT | `references/legenda-LICENSE.txt` |
| Inter font | SIL Open Font License 1.1 | `assets/fonts/Inter-LICENSE.txt` |
| Anton font | SIL Open Font License 1.1 | `assets/fonts/Anton-OFL.txt` |
| Sound effects | Pixabay Content License | `assets/sfx/CREDITS.md` |
| GSAP 3.13.0 | GSAP Standard License (free) | header of `assets/gsap.min.js` |

## Credits

The caption stage is adapted from the open cinematic caption skill by audrey-560, under the MIT License. Video composition and rendering use [HyperFrames](https://github.com/heygen-com/hyperframes) by HeyGen.
