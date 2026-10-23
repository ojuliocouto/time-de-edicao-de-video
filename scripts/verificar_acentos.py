#!/usr/bin/env python3
"""Acha texto de tela escrito sem acento.

Nasceu de um erro real: sete inserts foram entregues com "voce", "operacao",
"Conteudo" e "Prospeccao" na tela. Nenhum dos quatro verificadores do
HyperFrames reclama disso, porque nao e erro de layout nem de contraste. E erro
de portugues, e num anuncio em portugues isso queima.

    python3 verificar_acentos.py inserts/01-nome/index.html
    python3 verificar_acentos.py inserts/*/index.html
    python3 verificar_acentos.py . --recursivo

Le so o texto que vai para a tela: ignora <script>, <style>, comentarios e
atributos. Sai com codigo 1 se achar alguma coisa.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import comum  # noqa: E402  UTF-8 na saida, exe() e caminhos nos tres sistemas

import argparse
import glob
import html as _html
import os
import re
import sys
import unicodedata

# forma sem acento -> forma certa. So palavra que SEMPRE leva acento.
CERTAS = {
    "voce": "você", "voces": "vocês", "nao": "não", "sao": "são", "entao": "então",
    "tambem": "também", "alguem": "alguém", "ninguem": "ninguém", "porem": "porém",
    "ate": "até", "ja": "já", "so": "só", "mes": "mês", "tres": "três",
    "apos": "após", "atras": "atrás", "proprio": "próprio", "propria": "própria",
    "proximo": "próximo", "proxima": "próxima", "rapido": "rápido", "rapida": "rápida",
    "unico": "único", "unica": "única", "ultimo": "último", "ultima": "última",
    "video": "vídeo", "videos": "vídeos", "pagina": "página", "paginas": "páginas",
    "maquina": "máquina", "logica": "lógica", "tecnica": "técnica", "tecnico": "técnico",
    "metrica": "métrica", "metricas": "métricas", "metodo": "método",
    "negocio": "negócio", "negocios": "negócios", "relatorio": "relatório",
    "escritorio": "escritório", "usuario": "usuário", "usuarios": "usuários",
    "calendario": "calendário", "diario": "diário", "horario": "horário",
    "salario": "salário", "necessario": "necessário", "obrigatorio": "obrigatório",
    "conteudo": "conteúdo", "conteudos": "conteúdos",
    "producao": "produção", "operacao": "operação", "operacoes": "operações",
    "criacao": "criação", "edicao": "edição", "gravacao": "gravação",
    "publicacao": "publicação", "automacao": "automação", "automacoes": "automações",
    "prospeccao": "prospecção", "informacao": "informação", "atencao": "atenção",
    "solucao": "solução", "solucoes": "soluções", "opcao": "opção", "opcoes": "opções",
    "acao": "ação", "acoes": "ações", "secao": "seção", "sessao": "sessão",
    "versao": "versão", "decisao": "decisão", "visao": "visão", "razao": "razão",
    "milhao": "milhão", "milhoes": "milhões", "padrao": "padrão", "mao": "mão",
    "sabado": "sábado", "sab": "sáb", "familia": "família",
    "historia": "história", "historias": "histórias", "memoria": "memória",
    "facil": "fácil", "dificil": "difícil", "possivel": "possível",
    "disponivel": "disponível", "nivel": "nível", "niveis": "níveis",
    "util": "útil", "movel": "móvel", "automatico": "automático",
    "grafico": "gráfico", "graficos": "gráficos", "basico": "básico",
    "classico": "clássico", "otimo": "ótimo", "minimo": "mínimo", "maximo": "máximo",
    "numero": "número", "numeros": "números", "codigo": "código", "titulo": "título",
    "capitulo": "capítulo", "modulo": "módulo", "multiplo": "múltiplo",
    "simbolo": "símbolo", "analise": "análise", "sintese": "síntese",
    "credito": "crédito", "debito": "débito", "tatica": "tática",
    "estrategia": "estratégia", "agencia": "agência", "audiencia": "audiência",
    "experiencia": "experiência", "referencia": "referência",
    "frequencia": "frequência", "consequencia": "consequência",
    "eficiencia": "eficiência", "ciencia": "ciência", "paciencia": "paciência",
    "urgencia": "urgência", "tendencia": "tendência", "concorrencia": "concorrência",
    "diferenca": "diferença", "crianca": "criança", "licenca": "licença",
    "seguranca": "segurança", "esperanca": "esperança", "mudanca": "mudança",
    "comeco": "começo", "preco": "preço", "precos": "preços", "servico": "serviço",
    "servicos": "serviços", "almoco": "almoço", "duvida": "dúvida",
    "duvidas": "dúvidas", "ideia": None,   # None = sem acento MESMO, nao avisar
}
CERTAS = {k: v for k, v in CERTAS.items() if v}

# essas existem nas duas formas. Aviso, nunca reprova.
AMBIGUAS = {
    "esta": "está", "estao": "estão", "pais": "país", "pratica": "prática",
    "publico": "público", "sabia": "sábia", "continua": "contínua",
    "secretaria": "secretária", "duvida": "dúvida", "e": "é",
}

def texto_de_tela(caminho):
    s = open(caminho, encoding="utf-8", errors="replace").read()
    if caminho.lower().endswith((".html", ".htm")):
        # so o <body>: o <title> costuma ser o nome do arquivo, em kebab-case,
        # e daria falso positivo em toda palavra ("03-ja-esta-pronto" -> "ja")
        m = re.search(r"<body\b[^>]*>(.*)</body>", s, flags=re.S | re.I)
        if m:
            s = m.group(1)
        s = re.sub(r"<script\b.*?</script>", " ", s, flags=re.S | re.I)
        s = re.sub(r"<style\b.*?</style>", " ", s, flags=re.S | re.I)
        s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
        s = re.sub(r"<[^>]+>", " ", s)
        s = _html.unescape(s)
    return s

def caixa_como(original, sugestao):
    """Devolve a sugestao na mesma caixa da palavra achada."""
    if original.isupper():
        return sugestao.upper()
    if original[:1].isupper():
        return sugestao[:1].upper() + sugestao[1:]
    return sugestao


def sem_acento(p):
    return "".join(c for c in unicodedata.normalize("NFD", p)
                   if unicodedata.category(c) != "Mn")

def main():
    ap = argparse.ArgumentParser(description="Acha texto de tela sem acento.")
    ap.add_argument("alvos", nargs="+", help="arquivos html/md, ou uma pasta com --recursivo")
    ap.add_argument("--recursivo", action="store_true",
                    help="varre index.html dentro da pasta")
    ap.add_argument("--avisos", action="store_true",
                    help="mostra tambem as palavras ambiguas")
    a = ap.parse_args()

    arquivos = []
    for alvo in a.alvos:
        if os.path.isdir(alvo) and a.recursivo:
            arquivos += sorted(glob.glob(os.path.join(alvo, "**", "index.html"),
                                         recursive=True))
        elif os.path.isdir(alvo):
            print(f"erro: {alvo} e uma pasta. Use --recursivo.", file=sys.stderr)
            return 2
        else:
            arquivos.append(alvo)
    arquivos = [f for f in arquivos if os.path.exists(f)]
    if not arquivos:
        print("erro: nenhum arquivo encontrado.", file=sys.stderr)
        return 2

    total = 0
    for f in arquivos:
        achados, duvidas = [], []
        for bruto in re.findall(r"[A-Za-zÀ-ÿ]+", texto_de_tela(f)):
            k = sem_acento(bruto).lower()
            if bruto != sem_acento(bruto):      # ja tem acento, esta certo
                continue
            if k in CERTAS:
                achados.append((bruto, caixa_como(bruto, CERTAS[k])))
            elif k in AMBIGUAS:
                duvidas.append((bruto, caixa_como(bruto, AMBIGUAS[k])))
        nome = os.path.relpath(f)
        if achados:
            total += len(achados)
            print(f"\n{nome}")
            for p, c in sorted(set(achados)):
                print(f"  ✗ \"{p}\"  ->  \"{c}\"")
        if duvidas and a.avisos:
            print(f"\n{nome}  (ambiguas, confira no contexto)")
            for p, c in sorted(set(duvidas)):
                print(f"  ? \"{p}\"  talvez  \"{c}\"")

    if total:
        print(f"\n  REPROVADO: {total} palavra(s) sem acento em texto de tela.")
        return 1
    print(f"  ok: {len(arquivos)} arquivo(s), nenhuma palavra sem acento.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
