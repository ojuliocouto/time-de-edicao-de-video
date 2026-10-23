#!/usr/bin/env python3
"""Motor da legenda cinematografica: de um legenda.json para a composicao HyperFrames.

    python gerar_legenda.py --pasta <pasta-do-video>/legenda

Le `legenda.json` e escreve, na mesma pasta:
  index.html                 composicao completa (base + recortes + legenda), para check e snapshot
  .work/tras.html            so a tipografia de TRAS (herois), fundo transparente
  .work/frente.html          so a tipografia da FRENTE (trilho, letterings), fundo transparente
  cinematic-caption-plan.json o plano exigido pela legenda (shotMap, cues, motivo de cada heroi)
  index.motion.json          o sidecar de movimento que o `hyperframes check` le
  assets/ hyperframes.json package.json   o projeto, se ainda nao existir

Depois: `montar_legenda.py` renderiza as duas camadas com alfa e compoe com os
recortes. Esse e o unico caminho que termina em peca longa com profundidade: o
render completo com recorte trava (94 s, 4 recortes, parou 3 vezes).

O motor e o de uma serie de anuncios reais, aprovado sem ajuste no ultimo
deles: trilho ancorado pela BASE em y=1590, Inter 500 com passo em
800 na palavra-chave, ancora em 600/72px, lettering em Anton, heroi em Anton
atras da cabeca com varredura de luz, halo de 4 camadas em em, aplicado em
toda legenda e nunca por plano (a "sombra 9", escolhida entre 10).

legenda.json (campos):
{
  "video": "montado.mp4",            relativo a esta pasta
  "acento": "#F94E03",
  "trilho_base": 1590,               y da base do trilho (ancorado por baixo)
  "zonas": {"peito": {"base": 1180}, "topo": {"topo": 230}},   zonas extras
  "estilo": {"apoio_px": 62, "apoio_peso": 500, "ancora_px": 72, "ancora_peso": 600},
  "shots": [{"id": "s00", "de": 0, "ate": 32.28, "tipo": "insert|talking-head",
             "texto_queimado": "o que a arte escreve", "profundidade": false,
             "motivo": "a arte escreve a fala: sem legenda"}],
  "cues": [{"id": "cc-001", "de": 32.28, "ate": 33.26, "texto": "Mas eu vou te contar a **verdade**",
            "papel": "setup", "enfase": "support|anchor|letter|hero", "zona": "rail|peito|...",
            "grupo": "g01", "tinta": "escura"}],
  "herois": {"cc-002h": {"motivo": "...", "tamanho": 160, "base": 202,
                         "preenchimento": "vidro|solido|acento", "recorte": "cc-a"}},
  "recortes": {"cc-a": {"inicio": 33.40, "duracao": 1.70}},
  "correcoes": [{"de": "IA", "para": "I.A.", "confirmado": "grafia da campanha"}],
  "sem_legenda": "por que os trechos sem legenda ficaram sem",
  "extra": {"css": "", "tras": "", "frente": "", "tweens": ""}
}
`**palavra**` marca o passo de peso. Heroi e uma cue com enfase "hero" e uma
entrada em "herois"; o "recorte" aponta para uma chave de "recortes".
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

W, H = 1080, 1920

ESTILO = {"apoio_px": 62, "apoio_peso": 500, "passo_peso": 800,
          "ancora_px": 72, "ancora_peso": 600, "letter_px": 132}

HYPERFRAMES_JSON = {
    "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
    "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
    "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
    "media": {"autoProxy": True},
}

BASE_CSS = """
      @font-face { font-family: "Anton"; src: url("assets/fonts/Anton-Regular.ttf") format("truetype"); font-weight: 400; font-display: block; }
      @font-face { font-family: "Inter"; src: url("assets/fonts/Inter-Variable.ttf") format("truetype"); font-weight: 100 900; font-display: block; }
      *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: {{FUNDO}}; font-family: "Inter", system-ui, sans-serif; }
      #cc-base { position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover }
      .cc-cut { position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover }
      /* halo de quatro camadas, em em, aplicado a TODA legenda e nunca por plano */
      .cc-support, .cc-anchor, .cc-hero, .cc-letter {
        text-shadow: 0 0 0.25em rgba(0,0,0,.9), 0 0 0.60em rgba(0,0,0,.88),
                     0 0 1.10em rgba(0,0,0,.8), 0 0.05em 0.10em rgba(0,0,0,.9);
      }
      /* tinta escura para insert de fundo claro: texto preto com halo claro */
      .cc-tinta-escura .cc-support, .cc-tinta-escura .cc-anchor, .cc-tinta-escura .cc-letter {
        color: #111 !important;
        text-shadow: 0 0 0.25em rgba(255,255,255,.85), 0 0 0.60em rgba(255,255,255,.7) !important;
      }
      .cc-cue { position: absolute; left: 50px; width: 980px; text-align: center }
      .cc-z-rail { bottom: {{RAIL}}px }
      .cc-support { display: inline-block; font-size: {{APOIO_PX}}px; font-weight: {{APOIO_PESO}}; line-height: 1.06; letter-spacing: -.005em; color: #fff }
      .cc-step { font-weight: {{PASSO_PESO}} }
      .cc-anchor  { display: inline-block; font-size: {{ANCORA_PX}}px; font-weight: {{ANCORA_PESO}}; line-height: 1.04; letter-spacing: -.015em; color: #fff }
      .cc-anchor .cc-step { font-size: 1.12em }
      .cc-letter { display: inline-block; font-family: "Anton", sans-serif; font-size: {{LETTER_PX}}px; line-height: 1.0; letter-spacing: .005em; color: #fff; white-space: nowrap }
      .cc-heroclip { position: absolute; left: 40px; width: 1000px; text-align: center }
      .cc-hero { display: inline-block; font-family: "Anton", sans-serif; line-height: .92; letter-spacing: .004em;
                 background: linear-gradient(104deg, rgba(255,255,255,0) 34%, rgba(255,255,255,.34) 50%, rgba(255,255,255,0) 66%);
                 background-size: 260% 100%; background-position: -40% 0; -webkit-background-clip: text; background-clip: text; }
      .cc-f-vidro { color: rgba(255,255,255,.62); -webkit-text-stroke: 1.6px rgba(255,255,255,.92) }
      .cc-f-solido { color: #fff }
      .cc-f-acento { color: {{ACENTO_RGBA}}; -webkit-text-stroke: 1.6px rgba(255,255,255,.55) }
      .cc-motion { display: block }
"""


def rgba(hexcor, alfa=0.92):
    h = hexcor.lstrip("#")
    return "rgba(%d,%d,%d,%.2f)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alfa)


def marcar(txt):
    out = ""
    for i, parte in enumerate(txt.split("**")):
        parte = html.escape(parte, quote=False)
        out += ('<b class="cc-step">%s</b>' % parte) if i % 2 else parte
    return out


def validar(spec):
    erros, avisos = [], []
    ids = set()
    for c in spec.get("cues", []):
        for campo in ("id", "de", "ate", "texto"):
            if campo not in c:
                erros.append("cue sem '%s': %s" % (campo, c))
        if c.get("id") in ids:
            erros.append("id repetido: %s" % c.get("id"))
        ids.add(c.get("id"))
        if c.get("ate", 0) <= c.get("de", 0):
            erros.append("%s: ate <= de" % c.get("id"))
        if c.get("enfase") == "hero":
            h = spec.get("herois", {}).get(c["id"])
            if not h:
                erros.append("%s e heroi mas nao esta em 'herois'" % c["id"])
            elif h.get("recorte") and h["recorte"] not in spec.get("recortes", {}):
                erros.append("%s aponta para o recorte '%s', que nao esta em 'recortes'" % (c["id"], h["recorte"]))
        else:
            limpo = c.get("texto", "").replace("**", "")
            if len(limpo) > 34 and c.get("enfase", "support") == "support":
                avisos.append("%s tem %d caracteres e quebra linha a 62px: divida a frase" % (c["id"], len(limpo)))
            palavras = limpo.split()
            if len(palavras) >= 2 and palavras[-1].isupper() and len(palavras[-1]) <= 6 and len(limpo) > 28:
                avisos.append("%s: confira a quebra; sigla sozinha na segunda linha ficou feia (TIMES DE I.A.)"
                              % c["id"])
    zonas = set(spec.get("zonas", {})) | {"rail", "heroi"}
    for c in spec.get("cues", []):
        if c.get("zona", "rail") not in zonas:
            erros.append("%s usa a zona '%s', que nao existe em 'zonas'" % (c["id"], c.get("zona")))
    return erros, avisos


def css_zonas(spec):
    linhas = []
    for nome, z in spec.get("zonas", {}).items():
        if "base" in z:
            linhas.append("      .cc-z-%s { bottom: %dpx }" % (nome, H - int(z["base"])))
        elif "topo" in z:
            linhas.append("      .cc-z-%s { top: %dpx }" % (nome, int(z["topo"])))
    return "\n".join(linhas)


def documento(spec, dur, fundo, corpo, tweens, com_base, pref):
    est = dict(ESTILO, **spec.get("estilo", {}))
    css = (BASE_CSS.replace("{{FUNDO}}", fundo)
           .replace("{{RAIL}}", str(H - int(spec.get("trilho_base", 1590))))
           .replace("{{APOIO_PX}}", str(est["apoio_px"])).replace("{{APOIO_PESO}}", str(est["apoio_peso"]))
           .replace("{{PASSO_PESO}}", str(est["passo_peso"])).replace("{{ANCORA_PX}}", str(est["ancora_px"]))
           .replace("{{ANCORA_PESO}}", str(est["ancora_peso"])).replace("{{LETTER_PX}}", str(est["letter_px"]))
           .replace("{{ACENTO_RGBA}}", rgba(spec.get("acento", "#F94E03"))))
    css += css_zonas(spec) + "\n" + spec.get("extra", {}).get("css", "")
    css = css.replace('url("assets/', 'url("%sassets/' % pref)
    base = ('      <video id="cc-base" class="clip" data-start="0" data-duration="%s" data-track-index="0" '
            'data-has-audio="true" src="%s"></video>\n' % (dur, spec.get("video", "montado.mp4"))) if com_base else ""
    return """<!doctype html>
<html lang="pt-BR" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="%sassets/js/gsap.min.js"></script>
    <style>%s
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="%s" data-width="1080" data-height="1920" data-fps="%s">
%s%s
    </div>
    <script>
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });
%s
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
""" % (pref, css, dur, spec.get("fps", 30), base, corpo, tweens)


def partes(spec):
    herois = spec.get("herois", {})
    back, front, cuts, tw_b, tw_f, motion = [], [], [], [], [], []
    for c in spec["cues"]:
        cid, a, b = c["id"], float(c["de"]), float(c["ate"])
        d = round(b - a, 3)
        enf = c.get("enfase", "support")
        if enf == "hero":
            h = herois[cid]
            s = int(h.get("tamanho", 200))
            topo = int(h["topo"]) if "topo" in h else round(int(h["base"]) - 0.76 * s)
            fill = {"acento": "acento", "laranja": "acento"}.get(h.get("preenchimento", "vidro"),
                                                                  h.get("preenchimento", "vidro"))
            back.append('        <div id="%s" class="clip cc-heroclip" data-start="%.2f" data-duration="%s" '
                        'data-track-index="2" style="top:%dpx"><div class="cc-motion"><span class="cc-hero cc-f-%s" '
                        'style="font-size:%dpx" data-layout-allow-overlap data-layout-allow-occlusion>%s</span>'
                        '</div></div>' % (cid, a, d, topo, fill, s, html.escape(c["texto"], quote=False)))
            tw_b.append('      tl.fromTo("#%s .cc-motion", { opacity: 0, scale: 1.16, filter: "blur(16px)" }, '
                        '{ opacity: 1, scale: 1, filter: "blur(0px)", duration: .28, ease: "power4.out" }, %.2f);' % (cid, a))
            tw_b.append('      tl.to("#%s .cc-hero", { backgroundPositionX: "140%%", duration: .60, '
                        'ease: "power1.inOut" }, %.2f);' % (cid, a + .22))
        else:
            cls = {"anchor": "cc-anchor", "letter": "cc-letter"}.get(enf, "cc-support")
            tinta = " cc-tinta-escura" if c.get("tinta") == "escura" else ""
            front.append('        <div id="%s" class="clip cc-cue cc-z-%s%s" data-start="%.2f" data-duration="%s" '
                         'data-track-index="5"><div class="cc-motion"><span class="%s" data-layout-allow-overlap>%s'
                         '</span></div></div>' % (cid, c.get("zona", "rail"), tinta, a, d, cls, marcar(c["texto"])))
            if enf == "letter":
                tw_f.append('      tl.fromTo("#%s .cc-motion", { opacity: 0, scale: 1.3 }, { opacity: 1, scale: 1, '
                            'duration: .16, ease: "power4.out" }, %.2f);' % (cid, a))
            else:
                tw_f.append('      tl.fromTo("#%s .cc-motion", { opacity: 0, y: 18 }, { opacity: 1, y: 0, '
                            'duration: .22, ease: "power3.out" }, %.2f);' % (cid, a))
            if enf == "anchor" and "**" in c["texto"]:
                tw_f.append('      tl.fromTo("#%s .cc-step", { scale: .9 }, { scale: 1, duration: .26, '
                            'ease: "back.out(2.2)" }, %.2f);' % (cid, a + .5))
        # folga de 0,45 s no bySec: menos que isso reprova por amostragem (visto num anuncio real)
        motion.append({"kind": "appearsBy", "selector": "#%s .cc-motion" % cid, "bySec": round(min(a + .45, b), 2)})
        motion.append({"kind": "staysInFrame", "selector": "#%s .cc-motion" % cid})
    for k, r in spec.get("recortes", {}).items():
        cuts.append('      <video id="%s" class="clip cc-cut" data-start="%.2f" data-duration="%.2f" data-media-start="0" '
                    'data-track-index="3" src=".work/%s-recorte.webm" muted playsinline></video>'
                    % (k, float(r["inicio"]), float(r["duracao"]), k))
    return back, front, cuts, tw_b, tw_f, motion


def plano(spec, dur):
    herois = spec.get("herois", {})
    shots = spec.get("shots", [])

    def shot_de(t):
        for s in shots:
            if s["de"] <= t < s["ate"]:
                return s
        return shots[-1] if shots else {"id": None, "profundidade": False}

    cues = []
    for i, c in enumerate(spec["cues"]):
        s, h = shot_de(c["de"] + .01), herois.get(c["id"])
        cues.append({
            "id": c["id"], "semanticGroupId": c.get("grupo"), "orderIndex": i,
            "breakOut": c.get("enfase") in ("hero", "letter"), "depthEligible": bool(s.get("profundidade")),
            "start": c["de"], "end": c["ate"], "text": c["texto"].replace("**", ""), "role": c.get("papel", "setup"),
            "emphasis": c.get("enfase", "support"), "heroReason": h.get("motivo") if h else None,
            "placement": c.get("zona", "rail"), "anchorZone": c.get("zona", "rail"),
            "layoutState": "background-hero-behind-subject" if h else c.get("zona", "rail"),
            "buildMode": "foreground-background-handoff" if h else "replace", "flowDirection": "top-to-bottom",
            "persistenceGroup": None, "foregroundText": None, "heroText": c["texto"] if h else None,
            "depthStrategy": ("subject-cutout " + h["recorte"]) if h and h.get("recorte") else "none",
            "fillSource": h.get("preenchimento", "vidro") if h else ("dark-ink" if c.get("tinta") == "escura" else "white-halo"),
            "occlusionBudget": 0.18 if h else None,
            "motion": "depth-reveal+light-sweep" if h else ("firm-settle" if c.get("enfase") == "letter" else "support-rise"),
            "graphic": None, "audioAccent": None, "shot": s.get("id"),
        })
    return {
        "version": 1, "mode": "rail", "range": {"start": 0, "end": dur}, "accent": spec.get("acento", "#F94E03"),
        "railAnchor": {"left": 50, "bottom": H - int(spec.get("trilho_base", 1590)), "align": "center", "maxLines": 1},
        "railAnchorReason": spec.get("motivo_trilho", "trilho ancorado pela base em y=%d, abaixo da boca"
                                     % spec.get("trilho_base", 1590)),
        "shotMap": [{"id": s["id"], "start": s["de"], "end": s["ate"], "type": s.get("tipo", "talking-head"),
                     "burnedInText": s.get("texto_queimado", "none"), "depthEligible": bool(s.get("profundidade")),
                     "depthReason": s.get("motivo", "")} for s in shots],
        "transcriptCorrections": spec.get("correcoes", []),
        "uncaptioned": spec.get("sem_legenda", ""),
        "cues": cues,
    }


def preparar_projeto(pasta):
    for sub in ("assets/fonts", "assets/js", ".work"):
        (pasta / sub).mkdir(parents=True, exist_ok=True)
    for f in ("Anton-Regular.ttf", "Inter-Variable.ttf"):
        if not (pasta / "assets" / "fonts" / f).exists():
            shutil.copy2(comum.FONTES / f, pasta / "assets" / "fonts" / f)
    if not (pasta / "assets" / "js" / "gsap.min.js").exists():
        shutil.copy2(comum.ASSETS / "gsap.min.js", pasta / "assets" / "js" / "gsap.min.js")
    if not (pasta / "hyperframes.json").exists():
        comum.gravar_json(pasta / "hyperframes.json", HYPERFRAMES_JSON, indent=2)
    if not (pasta / "package.json").exists():
        comum.gravar_json(pasta / "package.json", {"name": "legenda", "private": True, "type": "module"}, indent=2)


def main():
    ap = argparse.ArgumentParser(description="legenda.json -> composicao HyperFrames em camadas.")
    ap.add_argument("--pasta", required=True, help="pasta da legenda (com legenda.json)")
    a = ap.parse_args()
    pasta = Path(a.pasta).expanduser().resolve()
    spec = comum.ler_json(pasta / "legenda.json")
    erros, avisos = validar(spec)
    if erros:
        print("RECUSADO:")
        for e in erros:
            print("  " + e)
        return 1
    video = pasta / spec.get("video", "montado.mp4")
    if not video.exists():
        sys.exit("o video da legenda nao existe: %s" % video)
    dur = round(comum.sondar(video)["dur"], 3)
    preparar_projeto(pasta)
    back, front, cuts, tw_b, tw_f, motion = partes(spec)
    extra = spec.get("extra", {})
    camada_tras = '      <div id="cc-layer-back">\n%s\n%s\n      </div>\n' % (extra.get("tras", ""), "\n".join(back))
    camada_frente = '      <div id="cc-layer-front">\n%s\n%s\n      </div>' % (extra.get("frente", ""), "\n".join(front))
    tw_extra = extra.get("tweens", "")
    comum.gravar_texto(pasta / "index.html", documento(
        spec, dur, "#000", camada_tras + "\n".join(cuts) + "\n" + camada_frente,
        "\n".join(tw_b) + "\n" + "\n".join(tw_f) + "\n" + tw_extra, True, ""))
    comum.gravar_texto(pasta / ".work" / "tras.html", documento(spec, dur, "transparent", camada_tras,
                                                                "\n".join(tw_b), False, "../"))
    comum.gravar_texto(pasta / ".work" / "frente.html", documento(spec, dur, "transparent", camada_frente,
                                                                  "\n".join(tw_f) + "\n" + tw_extra, False, "../"))
    comum.gravar_json(pasta / "cinematic-caption-plan.json", plano(spec, dur), indent=2)
    comum.gravar_json(pasta / "index.motion.json", {"duration": dur, "assertions": motion}, indent=2)
    n = spec["cues"]
    print("%d legendas, %d herois, %d letterings, %d recortes"
          % (len(n), sum(1 for c in n if c.get("enfase") == "hero"),
             sum(1 for c in n if c.get("enfase") == "letter"), len(spec.get("recortes", {}))))
    for x in avisos:
        print("aviso: " + x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
