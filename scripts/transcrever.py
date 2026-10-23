#!/usr/bin/env python3
"""Transcricao por palavra, o relogio de toda a skill.

Tres usos:

    # partitura de um insert: tempos relativos ao inicio da janela, com frame
    python transcrever.py base/final.mp4 --de 12.5 --ate 19.0 -o fabrica/inserts/x/partitura.md
    python transcrever.py base/final.mp4 --trecho "isso aqui e uma skill"

    # conferencia de corte: transcreve SO o trecho, isolado (a regra dura)
    python transcrever.py bruto.mp4 --de 104 --ate 112 --isolado

    # palavras em JSON, para outro script
    python transcrever.py preview.mp4 --json analise/preview-palavras.json

Motores, nesta ordem no modo auto:
  1. mlx-whisper (Mac com chip Apple): o mais rapido e o que melhor casou com
     os silencios numa serie de anuncios reais. Era a referencia de tempo deles.
  2. faster-whisper (Mac, Windows e Linux, CPU): mesmo modelo large-v3-turbo.
  3. whisper-cli do whisper.cpp: o mais sujeito a deriva (0,5 s a 9 s em
     material longo). Fica de reserva.

Medido em material real: transcricao longa DERIVA e INVENTA repeticao. Por isso
o --isolado corta o trecho antes de transcrever: num clipe curto o modelo nao
tem como se perder, e os tempos voltam somados ao inicio do trecho.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import json
import os
import sys
import tempfile
import unicodedata
from pathlib import Path

MODELO_MLX = "mlx-community/whisper-large-v3-turbo"
MODELO_FASTER = os.environ.get("FASTER_WHISPER_MODELO", "large-v3-turbo")
MODELO_CPP = Path(os.environ.get("WHISPER_MODELO",
                                 Path.home() / ".cache" / "whisper-cpp" / "ggml-large-v3-turbo.bin"))
PASTA_WHISPER_CPP = Path.home() / ".local" / "whisper-cpp"

VENVS = [
    Path.home() / ".venvs" / "mlx-whisper",
    Path.home() / ".venv-whisper",
    Path.home() / "Claude" / ".venv-whisper",
]

CODIGO = r'''
import json, sys
caminho, idioma, motor, modelo = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
if motor == "mlx":
    import mlx_whisper
    r = mlx_whisper.transcribe(caminho, path_or_hf_repo=modelo,
                               word_timestamps=True, language=idioma, verbose=False)
    ws = [{"p": w["word"].strip(), "t": w["start"], "f": w["end"]}
          for s in r["segments"] for w in s.get("words", [])]
else:
    # O audio vai como array, nao como caminho: o faster-whisper 1.2 decodifica
    # arquivo pelo PyAV, e o PyAV 16 quebrou essa chamada (metadata_errors).
    # O wav ja chega em 16 kHz mono, que e o que o modelo come.
    import wave
    import numpy as np
    from faster_whisper import WhisperModel
    with wave.open(caminho, "rb") as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    audio = pcm.astype(np.float32) / 32768.0
    m = WhisperModel(modelo, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(audio, language=idioma, word_timestamps=True,
                           vad_filter=False, condition_on_previous_text=False)
    ws = [{"p": w.word.strip(), "t": w.start, "f": w.end}
          for s in segs for w in (s.words or [])]
print("###JSON###" + json.dumps(ws, ensure_ascii=False))
'''


def _importa(py, modulo):
    try:
        r = comum.rodar([str(py), "-c", "import " + modulo], checar=False)
    except OSError:
        return False
    return r.returncode == 0


def pythons():
    vistos = []
    for v in VENVS + [comum.cache("venv-whisper")]:
        py = comum.python_do_venv(v)
        if py.exists():
            vistos.append(str(py))
    vistos.append(sys.executable)
    return list(dict.fromkeys(vistos))


def achar_whisper_cli():
    achado = comum.exe("whisper-cli")
    if achado != "whisper-cli":
        return achado
    for c in (PASTA_WHISPER_CPP / "whisper-cli.exe", PASTA_WHISPER_CPP / "Release" / "whisper-cli.exe",
              PASTA_WHISPER_CPP / "whisper-cli", PASTA_WHISPER_CPP / "build" / "bin" / "whisper-cli"):
        if c.exists():
            return str(c)
    return None


def motores_disponiveis():
    """[(motor, python_ou_binario)] na ordem de preferencia."""
    achados = []
    for py in pythons():
        if comum.SISTEMA == "mac" and _importa(py, "mlx_whisper"):
            achados.append(("mlx", py))
            break
    for py in pythons():
        if _importa(py, "faster_whisper"):
            achados.append(("faster", py))
            break
    cli = achar_whisper_cli()
    if cli and MODELO_CPP.exists():
        achados.append(("whispercpp", cli))
    return achados


def escolher(motor="auto"):
    disp = motores_disponiveis()
    if motor != "auto":
        disp = [d for d in disp if d[0] == motor]
    if not disp:
        sys.exit("nenhum motor de transcricao pronto%s.\n"
                 "rode o preflight.py da skill: ele mostra o comando de instalar\n"
                 "(faster-whisper roda nos tres sistemas; mlx-whisper so no Mac)."
                 % ("" if motor == "auto" else " para --motor " + motor))
    return disp[0]


def _wav(origem, destino, de=None, ate=None):
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if de is not None:
        cmd += ["-ss", "%.3f" % de]
    if ate is not None:
        cmd += ["-to", "%.3f" % ate] if de is None else ["-t", "%.3f" % (ate - de)]
    cmd += ["-i", str(origem), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(destino)]
    comum.rodar(cmd)


def _whispercpp(cli, wav, idioma, contexto=None):
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "saida"
        cmd = [cli, "-m", str(MODELO_CPP), "-f", str(wav), "-l", idioma, "-ml", "1", "-sow",
               "-oj", "-of", str(base), "-np", "-nt"]
        if contexto:
            cmd += ["--prompt", contexto]
        comum.rodar(cmd)
        bruto = json.loads(Path(str(base) + ".json").read_text(encoding="utf-8"))
    ws = []
    for seg in bruto.get("transcription", []):
        t = seg.get("text", "").strip()
        if not t or t.startswith("[_"):
            continue
        ws.append({"p": t, "t": seg["offsets"]["from"] / 1000.0, "f": seg["offsets"]["to"] / 1000.0})
    return ws


def palavras(midia, idioma="pt", de=None, ate=None, motor="auto", contexto=None):
    """Lista de {"p", "t", "f"} em segundos da MIDIA (ja somado o 'de')."""
    nome, onde = escolher(motor)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        _wav(midia, wav, de, ate)
        if nome == "whispercpp":
            ws = _whispercpp(onde, wav, idioma, contexto)
        else:
            modelo = MODELO_MLX if nome == "mlx" else MODELO_FASTER
            r = comum.rodar([onde, "-c", CODIGO, str(wav), idioma, nome, modelo], checar=False)
            if "###JSON###" not in (r.stdout or ""):
                sys.exit("a transcricao (%s) falhou:\n%s" % (nome, (r.stderr or "")[-1200:]))
            ws = json.loads(r.stdout.split("###JSON###", 1)[1].strip())
    zero = de or 0.0
    dur = (ate - zero) if ate is not None else None
    out = []
    for w in ws:
        t, f = float(w["t"]), float(w["f"])
        if dur is not None:  # whisper.cpp estica o fim ate o bloco de 30 s
            t, f = min(t, dur), min(f, dur)
        if w["p"]:
            out.append({"p": w["p"], "t": round(t + zero, 3), "f": round(f + zero, 3)})
    return out, nome


def simples(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn" and (c.isalnum() or c == " "))


def achar_trecho(ws, frase):
    alvo = simples(frase).split()
    seq = [simples(w["p"]) for w in ws]
    for i in range(len(seq) - len(alvo) + 1):
        if seq[i:i + len(alvo)] == alvo:
            return ws[i]["t"], ws[min(i + len(alvo), len(ws)) - 1]["f"]
    return None


def suspeitas(ws, limite=0.9):
    """Palavra curta esticada demais costuma ser retomada fundida pela
    transcricao ('fez' de 1,6 s num video real escondia 'Mas nao e so isso que te...')."""
    return [w for w in ws if (w["f"] - w["t"]) > limite and len(simples(w["p"])) <= 8]


def partitura(ws, zero, fps, fonte, ate):
    fim = ws[-1]["f"]
    linhas = ["# Partitura", "", "Fonte: `%s`" % fonte,
              "Janela: %.2fs a %.2fs da fonte. Os tempos abaixo ja sao relativos ao inicio do insert."
              % (zero, ate if ate is not None else fim),
              "Duracao do insert: **%.2fs**  (%d fps)" % (fim - zero if ate is None else ate - zero, fps),
              "", "Cada elemento entra no frame da palavra que o pediu. A batida esta aqui.", "",
              "| palavra | segundo | frame |", "| --- | --- | --- |"]
    for w in ws:
        t = w["t"] - zero
        linhas.append("| %s | %.2f | %d |" % (w["p"], t, round(t * fps)))
    linhas += ["", "## Fala completa da janela", "", " ".join(w["p"] for w in ws), ""]
    return "\n".join(linhas)


def main():
    ap = argparse.ArgumentParser(description="Transcricao por palavra (partitura, conferencia, json).")
    ap.add_argument("midia", help="audio ou video")
    ap.add_argument("-o", "--saida", help="partitura.md")
    ap.add_argument("--json", help="grava as palavras em JSON")
    ap.add_argument("--de", type=float)
    ap.add_argument("--ate", type=float)
    ap.add_argument("--trecho", help="frase a achar; a janela sai dela")
    ap.add_argument("--isolado", action="store_true",
                    help="corta o trecho ANTES de transcrever (conferencia de corte)")
    ap.add_argument("--motor", default="auto", choices=["auto", "mlx", "faster", "whispercpp"])
    ap.add_argument("--idioma", default="pt")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--contexto", help="nomes proprios e jargao (so whisper.cpp usa)")
    ap.add_argument("--listar-motores", action="store_true")
    a = ap.parse_args()

    if a.listar_motores:
        for n, onde in motores_disponiveis():
            print("%-11s %s" % (n, onde))
        return 0
    if not Path(a.midia).expanduser().exists():
        sys.exit("nao achei %s" % a.midia)
    comum.exigir("ffmpeg")

    if a.isolado or (a.de is not None and a.ate is not None and not a.trecho):
        ws, motor = palavras(a.midia, a.idioma, a.de, a.ate, a.motor, a.contexto)
        de, ate = a.de, a.ate
    else:
        ws, motor = palavras(a.midia, a.idioma, motor=a.motor, contexto=a.contexto)
        de, ate = a.de, a.ate
        if a.trecho:
            achado = achar_trecho(ws, a.trecho)
            if not achado:
                sys.exit("nao achei o trecho. Transcricao: " + " ".join(w["p"] for w in ws)[:500])
            de, ate = achado
        ws = [w for w in ws if (de is None or w["f"] > de) and (ate is None or w["t"] < ate)]
    if not ws:
        sys.exit("a janela nao pegou palavra nenhuma (audio mudo ou janela errada).")

    if a.json:
        comum.gravar_json(a.json, ws)
        print("%s  %d palavras  (motor %s)" % (a.json, len(ws), motor))
    if a.saida:
        comum.gravar_texto(a.saida, partitura(ws, de or 0.0, a.fps, os.path.basename(a.midia), ate))
        print("%s  %d palavras  (motor %s)" % (a.saida, len(ws), motor))
    if not a.saida and not a.json:
        print("motor: %s" % motor)
        for w in ws:
            print("%8.3f %8.3f  %s" % (w["t"], w["f"], w["p"]))
        print("\n" + " ".join(w["p"] for w in ws))
    for w in suspeitas(ws):
        print("SUSPEITA: '%s' dura %.2fs (%.2f a %.2f). Retomada fundida? Escute esse trecho."
              % (w["p"], w["f"] - w["t"], w["t"], w["f"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
