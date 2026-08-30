#!/usr/bin/env python3
"""Pesquisa de jurisprudencia no STJ, direto da fonte oficial.

O portal do STJ e servido por dois hosts. O `scon.stj.jus.br` esta atras de um
desafio Cloudflare que reprova clientes automatizados, enquanto o
`processo.stj.jus.br` serve a mesma aplicacao sem qualquer bloqueio. Este script
usa exclusivamente o segundo. Se um dia ele tambem for fechado, o sintoma sera
HTTP 403 ou uma pagina de "Verificacao automatica em andamento" -- nesse caso
caia para o portal unificado do CJF (ver references/cjf.md).

Uso:
    python3 stj_busca.py 'EXPRESSAO' [--max 50] [--json saida.json]

A expressao aceita os operadores do SCON: aspas para termo exato, `e`, `ou`,
`nao`, `adj`, `prox`, `mesmo`, `com` e `$` para truncamento.

    python3 stj_busca.py '"responsabilidade civil do estado" e omissiv$'
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
from html import unescape
from pathlib import Path

HOST = "https://processo.stj.jus.br"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def _curl(args, cookie_jar):
    """Executa curl mantendo a sessao. O SCON exige um cookie de sessao obtido na
    home antes de aceitar a busca; sem ele responde 302 para a propria home."""
    base = [
        "curl", "-sS", "-L", "-A", UA,
        "-b", str(cookie_jar), "-c", str(cookie_jar),
        "-H", f"Referer: {HOST}/SCON/",
        "-H", "Accept: text/html,application/xhtml+xml",
        "--max-time", "90",
    ]
    return subprocess.run(base + args, capture_output=True)


def buscar(expressao, maximo=50, base="ACOR"):
    """Retorna (total, [julgados]). `base` = ACOR para acordaos.

    O HTML do SCON vem em ISO-8859-1; decodificar como UTF-8 corrompe todos os
    acentos silenciosamente, o que estraga a transcricao das ementas.
    """
    with tempfile.TemporaryDirectory() as tmp:
        jar = Path(tmp) / "cookies.txt"
        out = Path(tmp) / "resultado.html"

        # Estabelece a sessao.
        _curl(["-o", "/dev/null", f"{HOST}/SCON/"], jar)

        params = {
            "acao": "pesquisar", "novaConsulta": "true", "i": "1",
            "b": base, "tp": "T", "numDocsPagina": str(min(maximo, 50)),
            "livre": expressao,
        }
        url = f"{HOST}/SCON/pesquisar.jsp?" + urllib.parse.urlencode(params)
        res = _curl(["-o", str(out), url], jar)
        if res.returncode != 0:
            raise RuntimeError(f"curl falhou: {res.stderr.decode(errors='replace')}")

        html = out.read_text(encoding="iso-8859-1", errors="replace")

    if "Verifica" in html and "autom" in html and "andamento" in html:
        raise RuntimeError(
            "O host processo.stj.jus.br passou a exigir verificacao anti-bot. "
            "Use o portal unificado do CJF como alternativa."
        )

    m = re.search(r'<span class="numDocs">([\d.]+)\s*ac', html)
    total = int(m.group(1).replace(".", "")) if m else 0

    return total, _parse(html, maximo)


def _limpa(s):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _parse(html, maximo):
    """Extrai os julgados. A ementa limpa vive num <textarea> que o portal usa
    para o botao 'copiar ementa' -- e a melhor fonte, ja sem marcacao."""
    julgados = []
    partes = re.split(r'<a name="DOC\d+"', html)[1:]

    for parte in partes[:maximo]:
        def campo(rotulo):
            m = re.search(
                rotulo + r"\s*</div>\s*<div[^>]*>(.*?)</div>",
                parte, re.S | re.I,
            )
            return _limpa(m.group(1)) if m else ""

        ident = re.search(r'clsIdentificacaoDocumento">(.*?)</div>', parte, re.S)

        ementa = ""
        mt = re.search(r'class="textareaSemformatacao"[^>]*>(.*?)</textarea>', parte, re.S)
        if mt:
            ementa = unescape(mt.group(1)).strip()

        mit = re.search(r"inteiro_teor\('([^']+)'\)", parte)
        inteiro_teor = HOST + mit.group(1) if mit else ""

        reg = re.search(r"num_registro=(\d+)", parte)

        # A data de publicacao nao aparece como campo na listagem, mas o link do
        # inteiro teor sempre a carrega no parametro dt_publicacao.
        mdp = re.search(r"dt_publicacao=([\d/]+)", parte)

        # Marcadores de precedente qualificado. Procurar as palavras soltas no
        # bloco gera falso positivo, porque "recurso repetitivo" aparece dentro
        # de ementas que apenas citam repetitivos alheios. O SCON emite um
        # comentario HTML com flags booleanas explicitas -- essa e a fonte
        # confiavel, e e o que distingue o julgado que E repetitivo daquele que
        # apenas menciona um.
        qualificado = []
        flags = re.search(
            r"<!--\s*Repetitivo:\s*Base NUGEP (\w+).*?IAC:\s*Base NUGEP (\w+)"
            r".*?Afeta\S*o:\s*Base NUGEP (\w+).*?Admiss\S*o:\s*Base NUGEP (\w+)",
            parte, re.S | re.I,
        )
        tema = re.search(r"<!--\s*CAMPO TEMA:\s*(.*?)-->", parte, re.S)
        tema_txt = re.sub(r"\s+", " ", tema.group(1)).strip() if tema else ""

        if flags:
            repet, iac, afet, adm = (g.lower() == "true" for g in flags.groups())
            if repet:
                mt2 = re.search(r"Tema Repetitivo\s*(\d+)", tema_txt, re.I)
                qualificado.append(
                    f"Tema Repetitivo {mt2.group(1)}" if mt2 else "Recurso repetitivo"
                )
            if iac:
                mi = re.search(r"IAC\s*(\d+)", tema_txt, re.I)
                qualificado.append(f"IAC {mi.group(1)}" if mi else "IAC")
            if afet:
                qualificado.append("Tema afetado")
            if adm:
                qualificado.append("Afetacao admitida")
        elif 'class="barraDocRepetitivo"' in parte:
            qualificado.append("Recurso repetitivo")

        ms = re.search(r"Situa\S*o do tema:\s*([^<\n]+)", tema_txt, re.I)

        julgados.append({
            "processo": campo("PROCESSO") or (_limpa(ident.group(1)) if ident else ""),
            "identificacao": _limpa(ident.group(1)) if ident else "",
            "relator": campo("RELATOR") or campo("RELATORA"),
            "orgao_julgador": campo("&Oacute;RG&Atilde;O JULGADOR") or campo("ÓRGÃO JULGADOR"),
            "data_julgamento": campo("DATA DO JULGAMENTO"),
            "data_publicacao": mdp.group(1) if mdp else "",
            "num_registro": reg.group(1) if reg else "",
            "precedente_qualificado": qualificado,
            "situacao_tema": _limpa(ms.group(1)) if ms else "",
            "ementa": ementa,
            "inteiro_teor_url": inteiro_teor,
        })

    return julgados


def main():
    ap = argparse.ArgumentParser(description="Pesquisa jurisprudencia no STJ")
    ap.add_argument("expressao")
    ap.add_argument("--max", type=int, default=50)
    ap.add_argument("--base", default="ACOR", help="ACOR (acordaos) ou SUMU (sumulas)")
    ap.add_argument("--json", help="grava o resultado em arquivo JSON")
    a = ap.parse_args()

    try:
        total, julgados = buscar(a.expressao, a.max, a.base)
    except RuntimeError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1

    payload = {"expressao": a.expressao, "total": total, "julgados": julgados}

    if a.json:
        Path(a.json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"{total} acordaos encontrados; {len(julgados)} recuperados nesta pagina.\n")
    for j in julgados:
        marca = f"  [{', '.join(j['precedente_qualificado'])}]" if j["precedente_qualificado"] else ""
        print(f"- {j['identificacao']} | {j['orgao_julgador']} | "
              f"Rel. {j['relator']} | j. {j['data_julgamento']}{marca}")
    if a.json:
        print(f"\nJSON gravado em {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
