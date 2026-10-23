#!/usr/bin/env python3
"""Pre-flight do time de edicao: confere a maquina antes de qualquer etapa.

    python preflight.py              quadro completo (Mac, Windows ou Linux)
    python preflight.py --rapido     pula o que usa a rede (HyperFrames)
    python preflight.py --json       para o agente ler

So confere. Para cada item que falta mostra o comando que instala NAQUELE
sistema; quem roda e o agente, com a aprovacao da pessoa, um item por vez.
Sai com 0 quando todo item obrigatorio esta pronto e com 1 quando falta algum.
Item opcional (lettering, Drive, Vision, skills do HyperFrames) nunca muda o
codigo de saida.

Python: no Mac e no Linux e `python3`; no Windows e `python` (ou `py -3`). Se
`python` abrir a Microsoft Store, e o atalho falso do Windows: Configuracoes >
Aplicativos > Configuracoes avancadas > Aliases de execucao, desligar os dois.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REABRIR = "depois feche e abra o Claude para o PATH valer"
VENV = Path.home() / ".venv-whisper"


class Ambiente:
    """Tudo que o pre-flight le da maquina passa por aqui; o teste troca."""

    def __init__(self, sistema=None, home=None, path=None, maquina=None, versao=None):
        if sistema is None:
            sistema = "mac" if sys.platform == "darwin" else "windows" if os.name == "nt" else "linux"
        self.sistema = sistema
        self.home = Path(home) if home else Path.home()
        self.path = os.environ.get("PATH", "") if path is None else path
        self.maquina = maquina or platform.machine().lower()
        self.versao = versao or sys.version_info[:2]

    def which(self, nome):
        for c in (nome, nome + ".cmd", nome + ".exe"):
            achado = shutil.which(c, path=self.path)
            if achado:
                return achado
        return None

    def rodar(self, cmd, espera=30):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=espera,
                               encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
            return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
        except (OSError, subprocess.SubprocessError) as e:
            return 1, str(e)

    def venv_python(self):
        v = self.home / ".venv-whisper"
        return v / ("Scripts/python.exe" if self.sistema == "windows" else "bin/python")

    def importa(self, py, modulo):
        if not Path(py).exists() and py != sys.executable:
            return False
        code, _ = self.rodar([str(py), "-c", "import " + modulo], 60)
        return code == 0


def instalar(amb, item):
    """Comando de instalacao por sistema."""
    s = amb.sistema
    pip_venv = ('"%s" -m pip install' % amb.venv_python())
    criar_venv = {"mac": "python3 -m venv ~/.venv-whisper",
                  "linux": "python3 -m venv ~/.venv-whisper",
                  "windows": "python -m venv ~/.venv-whisper"}[s]
    tabela = {
        "python": {"mac": "brew install python@3.12",
                   "windows": "winget install -e --id Python.Python.3.12 --accept-source-agreements "
                              "--accept-package-agreements (%s)" % REABRIR,
                   "linux": "sudo apt install -y python3 python3-venv python3-pip  (ou dnf/pacman)"},
        "ffmpeg": {"mac": "brew install ffmpeg",
                   "windows": "winget install -e --id Gyan.FFmpeg --accept-source-agreements "
                              "--accept-package-agreements (%s)" % REABRIR,
                   "linux": "sudo apt install -y ffmpeg"},
        "node": {"mac": "brew install node",
                 "windows": "winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements "
                            "--accept-package-agreements (%s)" % REABRIR,
                 "linux": "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && "
                          "sudo apt install -y nodejs   (a versao da distro costuma ser velha demais)"},
        "hyperframes": {k: "npx --yes hyperframes --version   (baixa na primeira vez)" for k in ("mac", "windows", "linux")},
        "chrome": {k: "npx --yes hyperframes browser ensure" for k in ("mac", "windows", "linux")},
        "transcricao": {"mac": "%s && %s mlx-whisper faster-whisper pillow" % (criar_venv, pip_venv)
                        if amb.maquina in ("arm64", "aarch64") else
                        "%s && %s faster-whisper pillow" % (criar_venv, pip_venv),
                        "windows": "%s && %s faster-whisper pillow" % (criar_venv, pip_venv),
                        "linux": "%s && %s faster-whisper pillow" % (criar_venv, pip_venv)},
        "pillow": {k: "%s pillow   (cria o venv antes, se faltar: %s)" % (pip_venv, criar_venv)
                   for k in ("mac", "windows", "linux")},
        "yt-dlp": {"mac": "brew install yt-dlp",
                   "windows": "winget install -e --id yt-dlp.yt-dlp (%s)" % REABRIR,
                   "linux": "python3 -m pip install --user yt-dlp   (ou sudo apt install -y yt-dlp)"},
        "swiftc": {"mac": "xcode-select --install   (abre uma janela do sistema: a pessoa clica)"},
        "rclone": {"mac": "brew install rclone && rclone config   (remote com o nome gdrive)",
                   "windows": "winget install -e --id Rclone.Rclone && rclone config   (remote gdrive; %s)" % REABRIR,
                   "linux": "sudo apt install -y rclone && rclone config   (remote com o nome gdrive)"},
        "skills-hyperframes": {k: "npx --yes hyperframes skills" for k in ("mac", "windows", "linux")},
    }
    return tabela.get(item, {}).get(s, "")


def item(nome, ok, chave, amb, detalhe="", obrigatorio=True, etapa="base"):
    return {"etapa": etapa, "nome": nome, "ok": bool(ok), "obrigatorio": obrigatorio,
            "detalhe": detalhe, "instalar": "" if ok else instalar(amb, chave)}


def conferir(amb, rapido=False):
    out = []
    out.append(item("Python 3.9 ou mais novo", amb.versao >= (3, 9), "python", amb,
                    "%d.%d" % amb.versao))
    ff = amb.which("ffmpeg")
    out.append(item("ffmpeg e ffprobe", ff and amb.which("ffprobe"), "ffmpeg", amb))
    if ff:
        _, enc = amb.rodar([ff, "-hide_banner", "-encoders"])
        out.append(item("ffmpeg com libx264 e libvpx-vp9", "libx264" in enc and "libvpx-vp9" in enc,
                        "ffmpeg", amb, "o render e a legenda com alfa dependem dos dois"))
    node = amb.which("node")
    versao_node = ""
    if node:
        _, v = amb.rodar([node, "--version"])
        versao_node = v.strip()
    try:
        maior = int(versao_node.lstrip("v").split(".")[0]) if versao_node else 0
    except ValueError:
        maior = 0
    out.append(item("Node.js 18+ (npx, npm)", node and maior >= 18 and amb.which("npx") and amb.which("npm"),
                    "node", amb, versao_node))

    # etapa: inserts e legenda (HyperFrames)
    if not rapido and amb.which("npx"):
        code, txt = amb.rodar([amb.which("npx"), "--yes", "hyperframes", "--version"], 180)
        out.append(item("HyperFrames", code == 0, "hyperframes", amb, txt.splitlines()[-1] if txt else "",
                        etapa="inserts e legenda"))
    elif rapido:
        out.append(item("HyperFrames (nao conferido: --rapido)", True, "hyperframes", amb, "",
                        obrigatorio=False, etapa="inserts e legenda"))
    else:
        out.append(item("HyperFrames", False, "node", amb, "precisa do Node primeiro", etapa="inserts e legenda"))
    tem_chrome, onde = False, ""
    for cache in (amb.home / ".cache" / "hyperframes", amb.home / ".cache" / "puppeteer"):
        if cache.exists() and any(p.name.startswith(("chrome", "Google Chrome")) for p in cache.rglob("*")
                                  if p.is_file()):
            tem_chrome, onde = True, str(cache)
            break
    out.append(item("Chrome do HyperFrames", tem_chrome, "chrome", amb, onde, etapa="inserts e legenda"))
    # so a "hyperframes": nas versoes novas a hyperframes-core foi incorporada a ela
    faltam_hf = [s for s in ("hyperframes",)
                 if not (amb.home / ".claude" / "skills" / s / "SKILL.md").exists()]
    out.append(item("skills do HyperFrames (referencia)", not faltam_hf, "skills-hyperframes", amb,
                    ("faltam: " + ", ".join(faltam_hf)) if faltam_hf else "", obrigatorio=False,
                    etapa="inserts e legenda"))

    # etapa: transcricao (corte, partitura, legenda)
    venv = amb.venv_python()
    candidatos = [sys.executable, str(venv), str(amb.home / ".venvs" / "mlx-whisper" / "bin" / "python")]
    motores = []
    for py in candidatos:
        if amb.sistema == "mac" and amb.importa(py, "mlx_whisper"):
            motores.append("mlx-whisper")
            break
    for py in candidatos:
        if amb.importa(py, "faster_whisper"):
            motores.append("faster-whisper")
            break
    modelo_cpp = amb.home / ".cache" / "whisper-cpp" / "ggml-large-v3-turbo.bin"
    if amb.which("whisper-cli") and modelo_cpp.exists():
        motores.append("whisper.cpp")
    out.append(item("motor de transcricao", motores, "transcricao", amb,
                    ", ".join(motores) if motores else "nenhum", etapa="transcricao"))
    tem_pil = any(amb.importa(py, "PIL") for py in candidatos)
    out.append(item("Pillow (lettering e emoji)", tem_pil, "pillow", amb, "", obrigatorio=False,
                    etapa="lettering"))

    # etapa: recorte da pessoa
    if amb.sistema == "mac":
        out.append(item("swiftc (Vision: recorte 10x mais rapido)", amb.which("swiftc"), "swiftc", amb,
                        "sem ele o recorte usa o HyperFrames, mais lento", obrigatorio=False,
                        etapa="recorte da pessoa"))
    else:
        out.append(item("recorte pelo HyperFrames", True, "", amb,
                        "fora do Mac o recorte e o remove-background: ~1 quadro/s, use --janelas",
                        obrigatorio=False, etapa="recorte da pessoa"))

    out.append(item("yt-dlp (baixar reels, posts e videos de referencia)", amb.which("yt-dlp"), "yt-dlp", amb, "",
                    obrigatorio=False, etapa="material dos inserts"))

    # etapa: entrega
    rc = amb.which("rclone")
    remoto = False
    if rc:
        _, txt = amb.rodar([rc, "listremotes"])
        remoto = "gdrive:" in txt
    out.append(item("rclone com o remote gdrive (Drive)", rc and remoto, "rclone", amb, "",
                    obrigatorio=False, etapa="entrega"))
    return out


def quadro(itens, amb):
    linhas = ["", "TIME DE EDICAO DE VIDEO: pre-flight (%s, %s)" % (amb.sistema, amb.maquina), ""]
    etapa = None
    for i in itens:
        if i["etapa"] != etapa:
            etapa = i["etapa"]
            linhas.append("[%s]" % etapa)
        marca = "ok" if i["ok"] else ("FALTA" if i["obrigatorio"] else "opcional")
        linhas.append("  [%-8s] %s%s" % (marca, i["nome"], ("  (%s)" % i["detalhe"]) if i["detalhe"] else ""))
        if not i["ok"] and i["instalar"]:
            linhas.append("             instalar: %s" % i["instalar"])
    faltam = sum(1 for i in itens if not i["ok"] and i["obrigatorio"])
    linhas += ["", "Tudo pronto." if not faltam else "Falta(m) %d item(ns) obrigatorio(s)." % faltam]
    return "\n".join(linhas)


def main(argv=None):
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Pre-flight do time de edicao de video.")
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    amb = Ambiente()
    itens = conferir(amb, a.rapido)
    if a.json:
        print(json.dumps({"sistema": amb.sistema, "itens": itens}, ensure_ascii=False, indent=1))
    else:
        print(quadro(itens, amb))
    return 0 if all(i["ok"] or not i["obrigatorio"] for i in itens) else 1


if __name__ == "__main__":
    sys.exit(main())
