#!/usr/bin/env python3
"""Testes da skill. Rodar depois de QUALQUER mudanca nela.

    python3 ~/.claude/skills/time-de-edicao-de-video/tests/rodar.py          tudo
    python3 ~/.claude/skills/time-de-edicao-de-video/tests/rodar.py --rapido  sem render
    python3 ~/.claude/skills/time-de-edicao-de-video/tests/rodar.py --completo  com fala, HyperFrames e Chrome

Tres camadas:
1. estatico: todo script compila, importa o comum.py e nao usa nada que quebra
   fora do Mac (arquivo de texto sem encoding, /tmp, npx sem exe(), shell=True,
   python3 cravado, caminho de Homebrew);
2. unidade: tempo final <-> original, preflight simulando Windows e Linux,
   validacao do legenda.json;
3. integracao: um video sintetico (ffmpeg lavfi) passa por plano, inserts,
   render, verificar, batida, montar_lista e gerar_legenda. Roda igual nos tres
   sistemas, sem rede e sem transcricao.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
PY = sys.executable
falhas = []


def ok(cond, nome, detalhe=""):
    print(("  ok    " if cond else "  FALHA ") + nome + (("  (" + detalhe + ")") if detalhe and not cond else ""))
    if not cond:
        falhas.append(nome)


def rodar(args, **kw):
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("errors", "replace")
    return subprocess.run([PY, "-u"] + [str(a) for a in args], **kw)


# ------------------------------------------------------------------ estatico

def estatico():
    print("[estatico]")
    for p in sorted(SCRIPTS.glob("*.py")):
        src = p.read_text(encoding="utf-8")
        try:
            arvore = ast.parse(src)
        except SyntaxError as e:
            ok(False, "%s compila" % p.name, str(e))
            continue
        if p.name not in ("comum.py", "preflight.py"):
            ok("import comum" in src, "%s importa o comum.py" % p.name)
        problemas = []
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call):
                f = no.func
                kws = {k.arg for k in no.keywords}
                if isinstance(f, ast.Attribute) and f.attr in ("read_text", "write_text") and "encoding" not in kws:
                    problemas.append("linha %d: %s sem encoding" % (no.lineno, f.attr))
                if isinstance(f, ast.Name) and f.id == "open" and "encoding" not in kws:
                    modo = no.args[1].value if len(no.args) > 1 and isinstance(no.args[1], ast.Constant) else ""
                    for k in no.keywords:
                        if k.arg == "mode" and isinstance(k.value, ast.Constant):
                            modo = k.value.value
                    if "b" not in str(modo):
                        problemas.append("linha %d: open() de texto sem encoding" % no.lineno)
                if isinstance(f, ast.Attribute) and f.attr in ("run", "Popen", "check_output") and \
                        isinstance(f.value, ast.Name) and f.value.id == "subprocess" and \
                        not ({"stdin", "input"} & kws) and not any(k.arg is None for k in no.keywords):
                    problemas.append("linha %d: subprocess sem stdin fechado (trava esperando teclado)" % no.lineno)
                if any(k.arg == "shell" for k in no.keywords):
                    problemas.append("linha %d: shell=True" % no.lineno)
                if isinstance(f, ast.Attribute) and f.attr in ("run", "Popen", "check_output") and \
                        any(k.arg in ("text", "universal_newlines") for k in no.keywords) and "encoding" not in kws:
                    problemas.append("linha %d: subprocess de texto sem encoding" % no.lineno)
            if isinstance(no, ast.List) and no.elts and isinstance(no.elts[0], ast.Constant) and \
                    no.elts[0].value in ("npx", "whisper-cli", "python3", "python", "swiftc"):
                # dentro de comum.rodar/popen o primeiro item passa por exe(): permitido
                problemas.append("linha %d: comando '%s' cru numa lista" % (no.lineno, no.elts[0].value))
        for m in re.finditer(r"[\"'](/tmp/|/opt/homebrew|/usr/local/bin)", src):
            problemas.append("caminho de um sistema so: %s" % m.group(1))
        # comum.rodar e comum.popen resolvem o primeiro item com exe(): libera as listas deles
        liberadas = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) and \
                    no.func.attr in ("rodar", "popen") and no.args and isinstance(no.args[0], ast.List):
                liberadas.add(no.args[0].lineno)
        problemas = [x for x in problemas if not (x.startswith("linha") and "cru numa lista" in x and
                                                  int(x.split()[1].rstrip(":")) in liberadas)]
        ok(not problemas, "%s portavel" % p.name, "; ".join(problemas[:4]))


    import re as _re
    for doc in list((RAIZ / "estacoes").glob("*.md")) + list((RAIZ / "agentes").glob("*.md")) + [RAIZ / "SKILL.md"]:
        txt = doc.read_text(encoding="utf-8")
        ruins = [l for l in txt.splitlines() if _re.search(r"(^|[;&|] *)ffmpeg (?!-nostdin)", l)]
        rmstar = [l for l in txt.splitlines() if _re.search(r"\brm (-\w+ )*\S*/\*", l) and "nunca" not in l]
        ok(not ruins and not rmstar, "%s: comandos que nao travam esperando resposta" % doc.name,
           "; ".join((ruins + rmstar)[:2]))


# ------------------------------------------------------------------ unidade

def unidade():
    print("[unidade]")
    sys.path.insert(0, str(SCRIPTS))
    import tempo
    with tempfile.TemporaryDirectory() as tmp:
        plano = {"corte": {"manter": [[0.0, 2.0], [3.0, 6.0], [8.0, 9.0]]}, "velocidade": {"fator": 1.3}}
        Path(tmp, "plano.json").write_text(json.dumps(plano), encoding="utf-8")
        t = tempo.Tempo(tmp)
        ok(abs(t.final(4.0) - 3.0 / 1.3) < 1e-9, "tempo: original -> final")
        ok(abs(t.orig(t.final(5.5)) - 5.5) < 1e-9, "tempo: ida e volta")
        ok(abs(t.final(2.5) - 2.0 / 1.3) < 1e-9, "tempo: trecho cortado vai para o proximo bloco")
        ok(abs(t.duracao_final() - 6.0 / 1.3) < 1e-9, "tempo: duracao final")
        ok(abs(tempo.segundos("1:09") - 69.0) < 1e-9, "tempo: minuto:segundo")

    import preflight
    for sistema, espera in (("windows", "winget"), ("linux", "apt"), ("mac", "brew")):
        with tempfile.TemporaryDirectory() as casa:
            amb = preflight.Ambiente(sistema=sistema, home=casa, path="", maquina="x86_64")
            itens = preflight.conferir(amb, rapido=True)
            texto = preflight.quadro(itens, amb)
            ok(espera in texto, "preflight %s mostra comandos com %s" % (sistema, espera))
            ok(any(not i["ok"] and i["obrigatorio"] for i in itens), "preflight %s acusa o que falta" % sistema)
            if sistema == "windows":
                ok("Scripts" in texto and "python -m venv" in texto, "preflight windows usa Scripts/ e python")

    import gerar_legenda as gl
    spec = {"cues": [{"id": "a", "de": 0, "ate": 1, "texto": "x"}, {"id": "a", "de": 1, "ate": 0.5, "texto": "y"},
                     {"id": "h", "de": 1, "ate": 2, "texto": "HEROI", "enfase": "hero"},
                     {"id": "z", "de": 2, "ate": 3, "texto": "frase que passa de trinta e quatro letras", "zona": "rail"}]}
    erros, avisos = gl.validar(spec)
    ok(any("repetido" in e for e in erros), "legenda: recusa id repetido")
    ok(any("ate <= de" in e for e in erros), "legenda: recusa fim antes do comeco")
    ok(any("herois" in e for e in erros), "legenda: recusa heroi sem posicao")
    ok(any("caracteres" in x for x in avisos), "legenda: avisa frase longa")

    import mascara
    js = mascara.ler_janelas("5-8,7-10,20-21", 30.0)
    ok(js[0] == (0.0, 1.0) and len(js) == 3, "mascara: janelas juntam e incluem o 1o segundo", str(js))


# ------------------------------------------------------------------ integracao

def ffmpeg(*args):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + [str(a) for a in args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:])


def integracao():
    print("[integracao]")
    if not shutil.which("ffmpeg"):
        ok(False, "ffmpeg instalado")
        return
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        bruto = tmp / "bruto.mp4"
        # 8 s: tom de 1 s, silencio de 1 s, alternando. 1080x1920 a 30 fps.
        ffmpeg("-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=8",
               "-f", "lavfi", "-i", "sine=f=220:d=8:sample_rate=48000",
               "-filter_complex", "[1:a]volume='if(lt(mod(t,2),1),1,0)':eval=frame[a]",
               "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", bruto)
        pasta = tmp / "video"
        (pasta / "analise").mkdir(parents=True)
        (pasta / "analise" / "meta.json").write_text(json.dumps(
            {"duracao": 8.0, "fps": 30.0, "largura": 1080, "altura": 1920, "limiar_silencio": -40}), encoding="utf-8")
        palavras = [{"i": k, "texto": "fala%d" % k, "ini": 2.0 * k + 0.05, "fim": 2.0 * k + 0.95} for k in range(4)]
        (pasta / "analise" / "palavras.json").write_text(json.dumps(palavras), encoding="utf-8")
        sil = [{"ini": 2.0 * k + 1.0, "fim": 2.0 * k + 2.0, "dur": 1.0} for k in range(4)]
        (pasta / "analise" / "silencios.json").write_text(json.dumps(sil), encoding="utf-8")
        ffmpeg("-i", bruto, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", pasta / "analise" / "audio.wav")

        r = rodar([SCRIPTS / "plano.py", "criar", "--pasta", pasta, "--fonte", bruto])
        ok(r.returncode == 0 and (pasta / "plano.json").exists(), "plano.py criar", r.stdout[-300:] + r.stderr[-300:])
        r = rodar([SCRIPTS / "render.py", "--pasta", pasta, "--ate", "velocidade", "--preview"])
        prev = pasta / "previews" / "02-velocidade.mp4"
        ok(r.returncode == 0 and prev.exists(), "render.py velocidade", r.stderr[-400:])
        r = rodar([SCRIPTS / "verificar.py", "--pasta", pasta, prev])
        ok(r.returncode == 0, "verificar.py aprova o preview", r.stdout[-300:])

        # dois inserts grudados na mesma borda, pelo caminho da fabrica
        renders = pasta / "fabrica" / "renders"
        renders.mkdir(parents=True)
        for nome, cor in (("01-a", "red"), ("02-b", "blue")):
            ffmpeg("-f", "lavfi", "-i", "color=c=%s:s=1080x1920:r=30:d=4" % cor, "-c:v", "libx264",
                   "-pix_fmt", "yuv420p", renders / (nome + ".mp4"))
        sys.path.insert(0, str(SCRIPTS))
        import tempo
        t = tempo.Tempo(pasta)
        # vao menor que um quadro entre os dois, com um quadro da grade caindo
        # dentro dele: e o caso que deixava o rosto piscar 1 quadro (caso real)
        k = int(t.duracao_final() / 2 * 30)
        meio = k / 30.0
        # o 01 com a duracao EXATA da janela: e o caso em que o arquivo acaba
        # antes da borda e o rosto vaza (caso de uma validacao)
        ffmpeg("-f", "lavfi", "-i", "color=c=red:s=1080x1920:r=30:d=%.4f" % (meio - 0.010 - 0.3), "-c:v", "libx264",
               "-pix_fmt", "yuv420p", renders / "01-a.mp4")
        janelas = [{"nome": "01-a", "de": 0.3, "ate": round(meio - 0.010, 4), "formato": "tela_cheia"},
                   {"nome": "02-b", "de": round(meio + 0.015, 4), "ate": round(t.duracao_final() - 0.2, 3),
                    "formato": "tela_cheia"}]
        (pasta / "fabrica" / "janelas.json").write_text(json.dumps(janelas), encoding="utf-8")
        r = rodar([SCRIPTS / "montar_lista.py", "--pasta", pasta])
        ok(r.returncode == 0 and (pasta / "lista-inserts.json").exists(), "montar_lista.py", r.stderr[-300:])
        r = rodar([SCRIPTS / "plano.py", "inserts", "--pasta", pasta, "--arquivo", pasta / "lista-inserts.json",
                   "--substituir"])
        ok(r.returncode == 0, "plano.py inserts aceita a lista", r.stdout[-400:])
        r = rodar([SCRIPTS / "render.py", "--pasta", pasta, "--ate", "inserts", "--preview"])
        ins = pasta / "previews" / "03-inserts.mp4"
        ok(r.returncode == 0 and ins.exists(), "render.py inserts", r.stderr[-400:])
        if ins.exists():
            # na emenda nao pode aparecer o testsrc (rosto): o quadro da borda e vermelho ou azul
            quadro = tmp / "emenda.rgb"
            ffmpeg("-i", ins, "-vf", "select='between(n,%d,%d)',crop=8:8:536:960,scale=1:1" % (k - 3, k + 3),
                   "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", quadro)
            px = quadro.read_bytes()
            cores = [tuple(px[i:i + 3]) for i in range(0, len(px), 3)]
            puras = [c for c in cores if (c[0] > 150 and c[1] < 90 and c[2] < 90) or (c[2] > 150 and c[0] < 90 and c[1] < 90)]
            ok(len(cores) == 7 and len(puras) == 7, "emenda de inserts quase grudados sem quadro do rosto",
               "quadros %s" % cores)

        r = rodar([SCRIPTS / "batida.py", "--video", ins if ins.exists() else prev, "--virada", "2",
                   "-o", tmp / "com-batida.mp4"])
        ok(r.returncode == 0 and (tmp / "com-batida.mp4").exists(), "batida.py gera e mixa", r.stderr[-300:])

        leg = pasta / "legenda"
        leg.mkdir()
        shutil.copy2(prev, leg / "montado.mp4")
        (leg / "legenda.json").write_text(json.dumps({
            "video": "montado.mp4", "zonas": {"peito": {"base": 1180}},
            "shots": [{"id": "s0", "de": 0, "ate": 6, "tipo": "talking-head", "profundidade": True}],
            "cues": [{"id": "c1", "de": 0.2, "ate": 1.4, "texto": "Uma **legenda** de teste", "enfase": "support"},
                     {"id": "c1h", "de": 1.0, "ate": 2.0, "texto": "TESTE", "enfase": "hero"},
                     {"id": "c2", "de": 2.0, "ate": 3.0, "texto": "Ação já é ótima", "enfase": "anchor", "zona": "peito",
                      "tinta": "escura"}],
            "herois": {"c1h": {"motivo": "teste", "tamanho": 200, "base": 300, "recorte": "cc-a"}},
            "recortes": {"cc-a": {"inicio": 0.8, "duracao": 1.4}}}, ensure_ascii=False), encoding="utf-8")
        r = rodar([SCRIPTS / "gerar_legenda.py", "--pasta", leg])
        idx = leg / "index.html"
        ok(r.returncode == 0 and idx.exists() and (leg / ".work" / "tras.html").exists(), "gerar_legenda.py",
           r.stdout[-300:] + r.stderr[-300:])
        if idx.exists():
            h = idx.read_text(encoding="utf-8")
            ok("Ação já é ótima" in h and "cc-tinta-escura" in h, "gerar_legenda.py preserva acento e tinta")
            plano = json.loads((leg / "cinematic-caption-plan.json").read_text(encoding="utf-8"))
            ok(plano["mode"] == "rail" and len(plano["cues"]) == 3, "gerar_legenda.py escreve o plano")


# ------------------------------------------------------------------ completo
# O caminho inteiro com fala de verdade (voz sintetica em portugues, com uma
# retomada no comeco), usando o que a skill instala: motor de transcricao,
# HyperFrames, Chrome, Pillow, puppeteer. E o teste que roda no GitHub
# Actions em Windows, Linux e Mac.

def palavras_de(arq):
    return json.loads(Path(arq).read_text(encoding="utf-8"))


def simples(t):
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if c.isalnum())


def completo():
    print("[completo]")
    fala = RAIZ / "tests" / "assets" / "fala.m4a"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        bruto = tmp / "bruto.mov"
        ffmpeg("-f", "lavfi", "-i", "testsrc2=s=720x1280:r=25:d=14", "-i", fala, "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", bruto)

        r = rodar([SCRIPTS / "transcrever.py", "--listar-motores", fala])
        ok(r.returncode == 0 and r.stdout.strip(), "transcrever: algum motor instalado", r.stdout + r.stderr[-300:])
        print("        motores: " + " | ".join(r.stdout.split()[::2]))

        r = rodar([SCRIPTS / "transcrever.py", fala, "--de", "0", "--ate", "2.6", "--isolado"])
        ok(r.returncode == 0 and "hoje" in simples(r.stdout), "transcrever: trecho isolado", r.stdout[-300:] + r.stderr[-300:])

        pasta = tmp / "video com acento é"
        pasta.mkdir()
        (pasta / "trechos.json").write_text(json.dumps([{"arquivo": str(bruto), "de": 0, "ate": None,
                                                         "fala": "tudo"}]), encoding="utf-8")
        r = rodar([SCRIPTS / "montar_bruto.py", "--pasta", pasta, "--trechos", pasta / "trechos.json"])
        mont = pasta / "bruto-montado" / "montado.mp4"
        ok(r.returncode == 0 and mont.exists(), "montar_bruto: padroniza 720p a 25 fps", r.stderr[-400:])
        if not mont.exists():
            return
        sys.path.insert(0, str(SCRIPTS))
        import comum
        m = comum.sondar(mont)
        ok((m["w"], m["h"]) == (1080, 1920), "montar_bruto: sai 1080x1920", str(m))

        r = rodar([SCRIPTS / "analisar.py", mont, "--pasta", pasta], timeout=1800)
        ok(r.returncode == 0 and (pasta / "analise" / "palavras.json").exists(), "analisar.py com fala real",
           r.stdout[-300:] + r.stderr[-400:])
        if r.returncode != 0:
            return
        ws = palavras_de(pasta / "analise" / "palavras.json")
        hojes = [w for w in ws if simples(w["texto"]) == "hoje"]
        ok(len(hojes) == 2, "analisar.py acha a retomada ('hoje' duas vezes)", " ".join(w["texto"] for w in ws))

        r = rodar([SCRIPTS / "plano.py", "criar", "--pasta", pasta, "--fonte", mont])
        ok(r.returncode == 0, "plano.py criar com fala real", r.stdout[-300:])
        if len(hojes) == 2:
            rem = [{"de": hojes[0]["ini"], "ate": round(hojes[1]["ini"] - 0.03, 3), "tipo": "comeco_falso",
                    "texto": "Hoje eu vou te mostrar.", "motivo": "retomada: fica a segunda"}]
            (pasta / "remocoes.json").write_text(json.dumps(rem, ensure_ascii=False), encoding="utf-8")
            r = rodar([SCRIPTS / "plano.py", "aplicar", "--pasta", pasta, "--remocoes", pasta / "remocoes.json"])
            ok(r.returncode == 0, "plano.py aplicar corta a retomada", r.stdout[-400:])
        r = rodar([SCRIPTS / "render.py", "--pasta", pasta, "--ate", "velocidade", "--preview"], timeout=1800)
        prev = pasta / "previews" / "02-velocidade.mp4"
        ok(r.returncode == 0 and prev.exists(), "render.py com fala real", r.stderr[-400:])
        r = rodar([SCRIPTS / "verificar.py", "--pasta", pasta, prev])
        ok(r.returncode == 0, "verificar.py", r.stdout[-300:])
        r = rodar([SCRIPTS / "auditar.py", "--pasta", pasta])
        ok(r.returncode in (0, 1) and "Traceback" not in r.stderr, "auditar.py roda", r.stderr[-300:])
        r = rodar([SCRIPTS / "transcrever.py", prev, "--json", tmp / "prev.json"])
        if r.returncode == 0:
            pv = palavras_de(tmp / "prev.json")
            n = sum(1 for w in pv if simples(w["p"]) == "hoje")
            ok(n == 1 and any(simples(w["p"]).startswith("legenda") for w in pv),
               "preview transcrito: a retomada saiu e nada sumiu", " ".join(w["p"] for w in pv))
        else:
            ok(False, "transcrever.py no preview", r.stderr[-300:])

        # lettering + emoji (Pillow, rede para o Noto)
        r = rodar([SCRIPTS / "emoji.py", "😀", "300", tmp / "emoji.png"], timeout=300)
        ok(r.returncode == 0 and (tmp / "emoji.png").exists(), "emoji.py", r.stdout[-200:] + r.stderr[-300:])
        lt = {"estilo": "destaque", "linhas": ["teste de", "lettering ação"], "posicao": "abaixo", "de": 3.0}
        if (tmp / "emoji.png").exists():
            lt["elemento"] = str(tmp / "emoji.png")
        (tmp / "lt.json").write_text(json.dumps(lt, ensure_ascii=False), encoding="utf-8")
        r = rodar([SCRIPTS / "plano.py", "lettering", "--pasta", pasta, "--arquivo", tmp / "lt.json"])
        ok(r.returncode == 0, "plano.py lettering", r.stdout[-300:] + r.stderr[-300:])
        r = rodar([SCRIPTS / "render.py", "--pasta", pasta, "--ate", "lettering", "--preview"], timeout=1800)
        ok(r.returncode == 0 and (pasta / "previews" / "06-lettering.mp4").exists(), "render.py com lettering",
           r.stdout[-300:] + r.stderr[-400:])

        # mascara pelo HyperFrames (o motor do Windows e do Linux)
        r = rodar([SCRIPTS / "mascara.py", prev, "--recortes", "cc-a@1.0+0.6", "--pasta", tmp / "work",
                   "--motor", "hyperframes"], timeout=1800)
        rec = tmp / "work" / "cc-a-recorte.webm"
        ok(r.returncode == 0 and rec.exists(), "mascara.py pelo HyperFrames", r.stdout[-300:] + r.stderr[-500:])
        r = rodar([SCRIPTS / "mascara.py", prev, "-o", tmp / "matte.mp4", "--janelas", "1-1.5", "--motor", "hyperframes"],
                  timeout=1800)
        ok(r.returncode == 0 and "mesmo numero" not in r.stdout, "mascara.py do video inteiro com janelas",
           r.stdout[-300:] + r.stderr[-300:])

        # legenda com heroi atras e camadas
        leg = pasta / "legenda"
        (leg / ".work").mkdir(parents=True)
        ffmpeg("-i", prev, "-vf", "scale=1080:1920", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy",
               leg / "montado.mp4")
        if rec.exists():
            shutil.copy2(rec, leg / ".work" / "cc-a-recorte.webm")
            rec_ok = comum.sondar(leg / ".work" / "cc-a-recorte.webm")
            if (rec_ok["w"], rec_ok["h"]) != (1080, 1920):
                ffmpeg("-c:v", "libvpx-vp9", "-i", rec, "-vf", "scale=1080:1920", "-c:v", "libvpx-vp9",
                       "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", leg / ".work" / "cc-a-recorte.webm")
        (leg / "legenda.json").write_text(json.dumps({
            "video": "montado.mp4", "zonas": {"peito": {"base": 1180}},
            "shots": [{"id": "s0", "de": 0, "ate": 30, "tipo": "talking-head", "profundidade": True}],
            "cues": [{"id": "c1", "de": 0.1, "ate": 1.6, "texto": "Hoje eu vou te **mostrar**"},
                     {"id": "c1h", "de": 1.0, "ate": 1.6, "texto": "CLAUDE", "enfase": "hero"},
                     {"id": "c2", "de": 1.7, "ate": 3.2, "texto": "uma skill de **verdade**", "enfase": "anchor",
                      "zona": "peito"},
                     {"id": "c3", "de": 3.3, "ate": 4.0, "texto": "VAMOS NESSA!", "enfase": "letter"}],
            "herois": {"c1h": {"motivo": "teste", "tamanho": 200, "base": 330, "recorte": "cc-a"}},
            "recortes": {"cc-a": {"inicio": 1.0, "duracao": 0.6}}}, ensure_ascii=False), encoding="utf-8")
        final = pasta / "final" / "teste-legendado.mp4"
        r = rodar([SCRIPTS / "montar_legenda.py", "--pasta", leg, "--saida", final, "--workers", "1"], timeout=3000)
        ok(r.returncode == 0 and final.exists(), "montar_legenda.py (camadas HyperFrames + composicao)",
           r.stdout[-500:] + r.stderr[-800:])
        if final.exists():
            r = rodar([SCRIPTS / "entrega.py", final])
            ok(r.returncode == 0 and "1080x1920" in r.stdout, "entrega.py confere e gera a versao leve", r.stdout[-300:])
            r = rodar([SCRIPTS / "batida.py", "--video", final, "--virada", "2", "-o", tmp / "batida.mp4"])
            ok(r.returncode == 0, "batida.py sobre o legendado", r.stderr[-300:])

        # captura de pagina local (puppeteer-core + Chrome do HyperFrames)
        html = tmp / "pagina.html"
        html.write_text("<html><body style='background:#f2f2f2;font:40px sans-serif'><h1>Página de teste ação</h1>"
                        + "<p>linha</p>" * 80 + "</body></html>", encoding="utf-8")
        r = rodar([SCRIPTS / "capturar_pagina.py", html.resolve().as_uri(), "-o", tmp / "pag.png", "--espera", "500"],
                  timeout=900)
        ok(r.returncode == 0 and (tmp / "pag.png").exists(), "capturar_pagina.py (print completo)",
           r.stdout[-300:] + r.stderr[-500:])
        r = rodar([SCRIPTS / "capturar_pagina.py", html.resolve().as_uri(), "--gravar", tmp / "pag.mp4",
                   "--segundos", "1", "--chaves", "0:0,1:600", "--espera", "300"], timeout=900)
        ok(r.returncode == 0 and (tmp / "pag.mp4").exists(), "capturar_pagina.py (gravacao da rolagem)",
           r.stdout[-300:] + r.stderr[-500:])

        # fabrica: projeto e um insert de verdade pelo init do HyperFrames
        fab = pasta / "fabrica"
        r = rodar([SCRIPTS / "novo_projeto.py", fab, "--nome", "teste"], timeout=300)
        ok(r.returncode == 0 and (pasta / "PLANO.md").exists() and (fab / "base.css").exists(),
           "novo_projeto.py cria a fabrica", r.stdout[-300:] + r.stderr[-300:])
        r = rodar([SCRIPTS / "novo_projeto.py", fab, "--insert", "01-teste"], timeout=600)
        ins = fab / "inserts" / "01-teste"
        ok(r.returncode == 0 and (ins / "index.html").exists() and (ins / "assets" / "fonts" / "Inter-Variable.ttf").exists(),
           "novo_projeto.py --insert (init do HyperFrames)", r.stdout[-300:] + r.stderr[-500:])
        r = rodar([SCRIPTS / "preflight.py", "--rapido"], timeout=600)
        ok("Traceback" not in r.stderr, "preflight.py roda", r.stderr[-300:])
        print(r.stdout)


def main():
    rapido = "--rapido" in sys.argv
    estatico()
    unidade()
    if not rapido:
        integracao()
    if "--completo" in sys.argv:
        completo()
    print("")
    if falhas:
        print("%d FALHA(S): %s" % (len(falhas), ", ".join(falhas)))
        return 1
    print("tudo ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
