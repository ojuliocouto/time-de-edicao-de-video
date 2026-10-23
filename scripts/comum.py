"""O que muda de um sistema para outro mora aqui, e so aqui.

Todo script da skill importa este modulo logo no comeco. Ele resolve tres
coisas que quebravam fora do Mac sem aviso nenhum:

1. Acento na saida. No Windows o Python escreve no terminal em cp1252, e uma
   seta ou um emoji derruba o script com UnicodeEncodeError no meio do render.
   Aqui a saida vira UTF-8 assim que o modulo e importado.
2. Programa que nao e .exe. No Windows o `npx` e um `npx.cmd`, e o
   subprocess sem shell nao acha `.cmd` pelo nome curto. `exe()` devolve o
   caminho inteiro, que funciona nos tres sistemas.
3. Pasta de cache e venv. `/tmp` nao existe no Windows e o python de um venv
   fica em `Scripts\\python.exe`, nao em `bin/python`.

Leitura e escrita de texto sempre com encoding="utf-8": o padrao do Windows e
cp1252 e grava "TransiÃ§Ã£o" no lugar de "Transicao" acentuado.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
ASSETS = SKILL / "assets"
FONTES = ASSETS / "fonts"
SFX = ASSETS / "sfx"

if sys.platform == "darwin":
    SISTEMA = "mac"
elif os.name == "nt":
    SISTEMA = "windows"
else:
    SISTEMA = "linux"


def utf8():
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


utf8()


def exe(nome):
    """Caminho completo do programa, ou o proprio nome se nao achar.

    Devolver o nome (em vez de falhar aqui) deixa o erro acontecer no
    subprocess, com a mensagem de quem chamou."""
    for candidato in (nome, nome + ".cmd", nome + ".exe", nome + ".bat"):
        achado = shutil.which(candidato)
        if achado:
            return achado
    return nome


def tem(nome):
    return any(shutil.which(c) for c in (nome, nome + ".cmd", nome + ".exe"))


def exigir(*nomes):
    faltam = [n for n in nomes if not tem(n)]
    if faltam:
        sys.exit("faltando: %s. Rode o preflight.py da skill para ver como instalar."
                 % ", ".join(faltam))


def rodar(cmd, checar=True, **kw):
    """subprocess.run com o primeiro item resolvido por exe() e texto em UTF-8."""
    cmd = [str(c) for c in cmd]
    cmd[0] = exe(cmd[0])
    kw.setdefault("capture_output", True)
    # ffmpeg le o teclado se o stdin estiver aberto: dentro de agente, sem
    # ninguem para responder, o comando fica parado para sempre (1h44 na
    # validacao). Sem stdin explicito, ele recebe o vazio.
    if "input" not in kw and "stdin" not in kw:
        kw["stdin"] = subprocess.DEVNULL
    if kw.get("capture_output") or kw.get("stdout") is not None:
        kw.setdefault("text", True)
    if kw.get("text"):
        kw.setdefault("encoding", "utf-8")
        kw.setdefault("errors", "replace")
    r = subprocess.run(cmd, **kw)
    if checar and r.returncode != 0:
        detalhe = (r.stderr or "")[-1500:] if isinstance(r.stderr, str) else ""
        sys.exit("falhou: %s\n%s" % (" ".join(os.path.basename(c) for c in cmd[:3]), detalhe))
    return r


def popen(cmd, **kw):
    cmd = [str(c) for c in cmd]
    cmd[0] = exe(cmd[0])
    kw.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.Popen(cmd, **kw)


def cache(*partes):
    """Pasta de cache da skill, criada se faltar. Nunca /tmp."""
    if SISTEMA == "windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif SISTEMA == "mac":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    p = base / "time-de-edicao-de-video"
    for parte in partes:
        p = p / parte
    p.mkdir(parents=True, exist_ok=True)
    return p


def python_do_venv(pasta):
    pasta = Path(pasta).expanduser()
    if SISTEMA == "windows":
        return pasta / "Scripts" / "python.exe"
    return pasta / "bin" / "python"


VENVS = [Path.home() / ".venv-whisper", Path.home() / ".venvs" / "mlx-whisper",
         Path.home() / "Claude" / ".venv-whisper"]


def python_com(modulo):
    """Um Python que importa `modulo`: o atual ou o de um venv conhecido.

    O preflight instala Pillow e o faster-whisper no ~/.venv-whisper, porque o
    Python do sistema (Homebrew no Mac, distro no Linux) recusa pip install."""
    candidatos = [sys.executable] + [str(python_do_venv(v)) for v in VENVS]
    for py in dict.fromkeys(candidatos):
        if py != sys.executable and not Path(py).exists():
            continue
        r = subprocess.run([py, "-c", "import " + modulo], capture_output=True, stdin=subprocess.DEVNULL)
        if r.returncode == 0:
            return py
    return None


def reexecutar_com(modulo):
    """Chamado quando o import falha: roda o mesmo script num Python que tenha
    o modulo e sai com o codigo dele. Se nenhum tiver, para com o comando."""
    py = python_com(modulo)
    if py and py != sys.executable:
        r = subprocess.run([py, sys.argv[0]] + sys.argv[1:], stdin=subprocess.DEVNULL)
        sys.exit(r.returncode)
    sys.exit("falta o modulo %s. Rode o preflight.py da skill: ele mostra o comando." % modulo)


def ler_texto(caminho):
    return Path(caminho).expanduser().read_text(encoding="utf-8")


def gravar_texto(caminho, texto):
    p = Path(caminho).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")
    return p


def ler_json(caminho):
    return json.loads(ler_texto(caminho))


def gravar_json(caminho, dado, indent=1):
    return gravar_texto(caminho, json.dumps(dado, indent=indent, ensure_ascii=False))


def sondar(video):
    """largura, altura, fps (float e texto), duracao e se tem audio."""
    r = rodar(["ffprobe", "-v", "error",
               "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
               "-of", "json", str(video)])
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    if v is None:
        sys.exit("o arquivo nao tem trilha de video: %s" % video)
    num, den = v["r_frame_rate"].split("/")
    return {"w": int(v["width"]), "h": int(v["height"]),
            "fps": float(num) / float(den), "fps_txt": v["r_frame_rate"],
            "dur": float(d["format"]["duration"]),
            "audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


_OPCAO_SCRIPT = None


def opcao_script_filtro():
    """'-filter_complex_script' esta obsoleto desde o ffmpeg 7 e pode sumir; o
    substituto '-/filter_complex' nao existe no 4.x e no 6.x que o Ubuntu traz.
    Escolhe pela versao instalada."""
    global _OPCAO_SCRIPT
    if _OPCAO_SCRIPT is None:
        r = rodar(["ffmpeg", "-hide_banner", "-version"], checar=False)
        import re
        m = re.search(r"ffmpeg version n?(\d+)\.", r.stdout or "")
        _OPCAO_SCRIPT = "-/filter_complex" if m and int(m.group(1)) >= 7 else "-filter_complex_script"
    return _OPCAO_SCRIPT


def contar_quadros(video):
    r = rodar(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0",
               "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(video)])
    try:
        return int(r.stdout.strip().split(",")[0])
    except ValueError:
        return 0
