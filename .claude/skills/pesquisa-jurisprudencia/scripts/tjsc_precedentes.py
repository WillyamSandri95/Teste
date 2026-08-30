#!/usr/bin/env python3
"""Coleta, ao vivo, os precedentes qualificados do TJSC: sumulas, IRDRs e IACs.

Estes sao os enunciados que vinculam ou orientam o proprio tribunal, e por isso
precisam ser conferidos antes de apresentar qualquer acordao de camara como se
fosse a posicao da casa. Um acordao isolado que contrarie um IRDR nao e "a
jurisprudencia do TJSC" -- e um julgado superado.

IMPORTANTE -- de onde vem os arquivos. O host `www.tjsc.jus.br` costuma recusar
conexao vinda do shell (timeout em 443), embora responda normalmente ao WebFetch
e ao navegador. Por isso o caminho padrao e: baixe os arquivos com WebFetch (que
grava os PDFs em disco e devolve o caminho) ou pelo navegador, e passe os
caminhos locais para este script. A tentativa por rede fica como atalho para
ambientes onde ela funciona.

Uso (recomendado, com arquivos ja baixados):
    python3 tjsc_precedentes.py --irdr irdr.pdf --iac iac.pdf \
        --sumulas sumulas.txt --termos "omissao" "responsabilidade civil"

Uso (tentando baixar direto, pode falhar por rede):
    python3 tjsc_precedentes.py --baixar --tudo --json precedentes.json

Sem `--termos`, devolve tudo. Com termos, filtra por ocorrencia (sem acento e
sem caixa) em qualquer campo do registro.

URLs das fontes (para alimentar o WebFetch):
    sumulas  https://www.tjsc.jus.br/web/jurisprudencia/sumulas-do-tjsc
    IRDR     https://www.tjsc.jus.br/documents/3133632/3200197/IRDR-COMPLETA/7ab8e228-b5c3-a8ee-8654-2f18a6e23141
    IAC      https://www.tjsc.jus.br/documents/3133632/3200301/IAC-COMPLETA/739851f8-ce56-92f6-ccea-00d665041a96
    enunciados por orgao  https://www.tjsc.jus.br/web/jurisprudencia/enunciados-do-tjsc
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from html import unescape
from pathlib import Path

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

FONTES = {
    "sumula": "https://www.tjsc.jus.br/web/jurisprudencia/sumulas-do-tjsc",
    "irdr": ("https://www.tjsc.jus.br/documents/3133632/3200197/IRDR-COMPLETA/"
             "7ab8e228-b5c3-a8ee-8654-2f18a6e23141"),
    "iac": ("https://www.tjsc.jus.br/documents/3133632/3200301/IAC-COMPLETA/"
            "739851f8-ce56-92f6-ccea-00d665041a96"),
}
ENUNCIADOS_INDICE = "https://www.tjsc.jus.br/web/jurisprudencia/enunciados-do-tjsc"


def _baixar(url, destino):
    r = subprocess.run(
        ["curl", "-sSL", "-A", UA, "--max-time", "120", "-o", str(destino),
         "-w", "%{http_code}", url],
        capture_output=True,
    )
    return r.stdout.decode().strip() == "200" and destino.exists()


def _normaliza(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _texto_pdf(caminho):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError(
            "pypdf ausente. Instale com: pip3 install --user pypdf"
        )
    r = PdfReader(str(caminho))
    return "\n".join((p.extract_text() or "") for p in r.pages)


def _parse_tabela(texto, especie):
    """Os PDFs de IRDR e IAC sao planilhas exportadas, com as colunas TEMA,
    PROCESSO PARADIGMA, QUESTAO SUBMETIDA A JULGAMENTO, SITUACAO, DELIMITACAO DA
    SUSPENSAO, ORGAO JULGADOR, RELATOR, TESE FIRMADA e ASSUNTO.

    A exportacao quebra linhas de forma irregular, entao o corte confiavel e o
    numero do tema seguido do numero CNJ do processo paradigma. Cada registro vai
    do inicio de um tema ate o inicio do proximo, e os campos sao recuperados por
    ancoras textuais dentro desse trecho.
    """
    # A exportacao para PDF quebra o numero CNJ no meio ("5055649-\n60.2016...").
    # Sem religar essas linhas nenhum registro e reconhecido.
    texto = re.sub(r"-\s*\n\s*", "-", texto)

    registros = []
    marcas = list(re.finditer(
        r"(?m)^\s*(\d{1,3})\s+(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", texto
    ))
    for i, m in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        bloco = texto[m.start():fim]

        # As colunas saem do PDF em fluxo unico e quebradas em varias linhas.
        # Normalizar o espacamento antes de extrair evita truncar "Grupo de
        # Camaras de" ou "Des. Ronei" no meio.
        norm = re.sub(r"\s+", " ", bloco).strip()

        msit = re.search(r"(Trânsito em julgado|Em julgamento|Julgado|Pendente|"
                         r"Suspenso|Cancelado|Aguardando|Revisão)", norm, re.I)
        morg = re.search(
            r"(Grupo de Câmaras de Direito [\wÁ-ú ]+?|Órgão Especial|"
            r"Seção Criminal|Turma de Uniformização|Câmara[s]? de [\wÁ-ú ]+?)"
            r"(?=\s+Des)", norm, re.I)

        relator, tese = "", ""
        # A coluna TESE FIRMADA vem imediatamente depois do relator. Cortar por
        # ali e mais confiavel do que procurar aspas, porque a coluna anterior
        # (DELIMITACAO DA SUSPENSAO) tambem e um texto entre aspas e seria
        # capturada no lugar da tese.
        mrel = re.search(
            r"\b(Des(?:embargador)?[ao]?\.?\s+[A-ZÁÂÃÉÊÍÓÔÕÚÇ][\wÁ-ú.\- ]{2,45}?)"
            r"(?=\s+(?:[\"“]|\d[\.\)]|[IVX]+\s*[–-]|Tese|Não|A\s|O\s))", norm)
        if mrel:
            relator = mrel.group(1).strip(" .")
            tese = norm[mrel.end():].strip()
        else:
            mfim = re.search(r"[\"“](.{60,})", norm, re.S)
            tese = mfim.group(1).strip() if mfim else ""

        # A ultima palavra costuma ser a coluna ASSUNTO (ex.: "administrativo").
        tese = re.sub(r"\s+", " ", tese).strip(" \"“”")
        assunto = ""
        massunto = re.search(r"[\"”]\s*([a-zçãáéíóú ]{4,40})\s*$", tese)
        if massunto:
            assunto = massunto.group(1).strip()
            tese = tese[:massunto.start()].strip(" \"“”")

        questao = norm[len(m.group(1)) + len(m.group(2)) + 2:]
        if msit:
            questao = questao[:msit.start() - (len(m.group(1)) + len(m.group(2)) + 2)]
        questao = re.sub(r"\s+", " ", questao).strip()

        registros.append({
            "especie": especie,
            "tema": m.group(1).lstrip("0") or m.group(1),
            "processo_paradigma": m.group(2),
            "questao": questao[:600],
            "situacao": msit.group(1).strip() if msit else "",
            "orgao_julgador": morg.group(1).strip() if morg else "",
            "relator": relator,
            "tese_firmada": tese[:3000],
            "assunto": assunto,
            "fonte": FONTES[especie],
        })
    return registros


def _parse_sumulas(html):
    """A pagina de sumulas traz numero e enunciado em tabela."""
    txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    linhas = re.findall(r"<tr[^>]*>(.*?)</tr>", txt, re.S | re.I)
    out = []
    for ln in linhas:
        celulas = [re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                   for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", ln, re.S | re.I)]
        celulas = [c for c in celulas if c]
        if len(celulas) < 2:
            continue
        mnum = re.search(r"(\d{1,3})", celulas[0])
        if not mnum or len(celulas[-1]) < 25:
            continue
        enunciado = celulas[-1]
        out.append({
            "especie": "sumula",
            "numero": mnum.group(1),
            "enunciado": enunciado,
            "revogada": bool(re.search(r"revogad|cancelad", " ".join(celulas), re.I)),
            "fonte": FONTES["sumula"],
        })
    return out


def _ler_local(caminho, especie):
    """Aceita PDF ou texto ja extraido, para o caso de o arquivo ter vindo do
    navegador em vez do WebFetch."""
    p = Path(caminho).expanduser()
    if not p.exists():
        raise RuntimeError(f"arquivo nao encontrado: {p}")
    if p.suffix.lower() == ".pdf":
        return _parse_tabela(_texto_pdf(p), especie)
    return _parse_tabela(p.read_text(encoding="utf-8", errors="replace"), especie)


def coletar(irdr=None, iac=None, sumulas=None, baixar=False):
    resultado = {"sumulas": [], "irdr": [], "iac": [], "avisos": []}

    for caminho, especie in ((irdr, "irdr"), (iac, "iac")):
        if not caminho:
            continue
        try:
            resultado[especie] = _ler_local(caminho, especie)
        except RuntimeError as e:
            resultado["avisos"].append(f"{especie.upper()}: {e}")

    if sumulas:
        p = Path(sumulas).expanduser()
        if p.exists():
            bruto = p.read_text(encoding="utf-8", errors="replace")
            resultado["sumulas"] = (
                _parse_sumulas(bruto) if "<" in bruto[:2000]
                else _parse_sumulas_texto(bruto)
            )
        else:
            resultado["avisos"].append(f"sumulas: arquivo nao encontrado: {p}")

    if baixar:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            if not resultado["sumulas"]:
                alvo = tmp / "sumulas.html"
                if _baixar(FONTES["sumula"], alvo):
                    resultado["sumulas"] = _parse_sumulas(
                        alvo.read_text(encoding="utf-8", errors="replace"))
                else:
                    resultado["avisos"].append(
                        "Falha de rede ao baixar as sumulas. Baixe com WebFetch em "
                        f"{FONTES['sumula']} e passe o arquivo em --sumulas.")
            for especie in ("irdr", "iac"):
                if resultado[especie]:
                    continue
                alvo = tmp / f"{especie}.pdf"
                if _baixar(FONTES[especie], alvo):
                    try:
                        resultado[especie] = _parse_tabela(_texto_pdf(alvo), especie)
                    except RuntimeError as e:
                        resultado["avisos"].append(str(e))
                else:
                    resultado["avisos"].append(
                        f"Falha de rede ao baixar {especie.upper()}. Baixe com "
                        f"WebFetch em {FONTES[especie]} e passe o caminho em "
                        f"--{especie}.")

    if not any(resultado[k] for k in ("sumulas", "irdr", "iac")):
        resultado["avisos"].append(
            "Nenhuma fonte carregada. Baixe as tabelas com WebFetch e informe os "
            "caminhos em --irdr / --iac / --sumulas.")

    resultado["avisos"].append(
        "Os enunciados das camaras nao tem tabela consolidada: consulte por orgao "
        f"em {ENUNCIADOS_INDICE}"
    )
    return resultado


def _parse_sumulas_texto(txt):
    """Fallback para quando as sumulas vierem como texto corrido (por exemplo do
    get_page_text do navegador), sem a tabela HTML."""
    out = []
    for m in re.finditer(
        r"(?:S[uú]mula|Enunciado)\s*n?[.º]?\s*(\d{1,3})\s*[-–:.]?\s*(.{40,900}?)"
        r"(?=(?:S[uú]mula|Enunciado)\s*n?[.º]?\s*\d{1,3}\b|\Z)",
        txt, re.S | re.I,
    ):
        corpo = re.sub(r"\s+", " ", m.group(2)).strip()
        out.append({
            "especie": "sumula", "numero": m.group(1), "enunciado": corpo,
            "revogada": bool(re.search(r"revogad|cancelad", corpo, re.I)),
            "fonte": FONTES["sumula"],
        })
    return out


def filtrar(dados, termos):
    if not termos:
        return dados
    alvos = [_normaliza(t) for t in termos]
    saida = {"avisos": dados["avisos"]}
    for chave in ("sumulas", "irdr", "iac"):
        saida[chave] = [
            r for r in dados[chave]
            if any(a in _normaliza(json.dumps(r, ensure_ascii=False)) for a in alvos)
        ]
    return saida


def main():
    ap = argparse.ArgumentParser(
        description="Precedentes qualificados do TJSC (sumulas, IRDR, IAC)")
    ap.add_argument("--irdr", help="PDF ou texto da tabela IRDR-COMPLETA")
    ap.add_argument("--iac", help="PDF ou texto da tabela IAC-COMPLETA")
    ap.add_argument("--sumulas", help="HTML ou texto da pagina de sumulas")
    ap.add_argument("--baixar", action="store_true",
                    help="tenta baixar por rede (costuma falhar; prefira WebFetch)")
    ap.add_argument("--termos", nargs="*", default=[])
    ap.add_argument("--tudo", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()

    dados = coletar(a.irdr, a.iac, a.sumulas, a.baixar)
    if not a.tudo:
        dados = filtrar(dados, a.termos)

    if a.json:
        Path(a.json).write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    print(f"Sumulas: {len(dados.get('sumulas', []))} | "
          f"IRDR: {len(dados.get('irdr', []))} | IAC: {len(dados.get('iac', []))}\n")
    for s in dados.get("sumulas", [])[:20]:
        flag = " [REVOGADA]" if s["revogada"] else ""
        print(f"Sumula {s['numero']}{flag}: {s['enunciado'][:150]}")
    for k in ("irdr", "iac"):
        for r in dados.get(k, [])[:20]:
            print(f"{k.upper()} {r['tema']} ({r['situacao']}): {r['questao'][:130]}")
    for av in dados.get("avisos", []):
        print(f"\n! {av}")
    if a.json:
        print(f"\nJSON gravado em {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
