#!/usr/bin/env python3
"""Extrai texto de inteiros teores e tabelas em PDF.

Serve para dois usos: ler o acordao completo quando a ementa nao basta (voto,
distincao fatica, placar) e ler as tabelas de IRDR/IAC do TJSC.

Uso:
    python3 extrair_texto_pdf.py acordao.pdf
    python3 extrair_texto_pdf.py acordao.pdf --secao ementa
    python3 extrair_texto_pdf.py acordao.pdf --secao voto --max 8000
    python3 extrair_texto_pdf.py https://processo.stj.jus.br/SCON/GetInteiroTeorDoAcordao?...

Aceita URL diretamente: baixa e extrai. Isso funciona para
`processo.stj.jus.br`, que serve os PDFs sem bloqueio.
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# O STJ carimba cada pagina com o bloco de assinatura eletronica. Mantê-lo
# picota a leitura da ementa no meio de uma frase, entao ele sai.
RUIDO = [
    r"Documento eletr[oô]nico VDA\d+.*?C[oó]digo de Controle do Documento:\s*\S+",
    r"Documento:\s*\d+\s*-\s*Inteiro Teor do Ac[oó]rd[ãa]o\s*-\s*Site certificado[^\n]*",
    r"Superior Tribunal de Justi[çc]a\s*\n",
    r"P[áa]gina\s+\d+\s+de\s+\d+",
]


def baixar(url, destino):
    r = subprocess.run(
        ["curl", "-sSL", "-A", UA, "--max-time", "120", "-o", str(destino),
         "-w", "%{http_code}", url],
        capture_output=True,
    )
    codigo = r.stdout.decode().strip()
    if codigo != "200":
        raise RuntimeError(f"download falhou (HTTP {codigo}) em {url}")
    return destino


def texto(caminho, limpar=True):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf ausente. Instale: pip3 install --user pypdf")

    r = PdfReader(str(caminho))
    t = "\n".join((p.extract_text() or "") for p in r.pages)
    if limpar:
        for pad in RUIDO:
            t = re.sub(pad, " ", t, flags=re.S | re.I)
        t = re.sub(r"\n{3,}", "\n\n", t)
        t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def secao(t, qual):
    """Recorta uma parte do acordao. As ancoras seguem a diagramacao usual dos
    inteiros teores do STJ e do STF."""
    qual = qual.lower()
    ancoras = {
        "ementa": (r"\bEMENTA\b", r"\bAC[OÓ]RD[AÃ]O\b|\bRELAT[OÓ]RIO\b|\bVOTO\b"),
        "acordao": (r"\bAC[OÓ]RD[AÃ]O\b", r"\bRELAT[OÓ]RIO\b|\bVOTO\b"),
        "relatorio": (r"\bRELAT[OÓ]RIO\b", r"\bVOTO\b"),
        "voto": (r"\bVOTO\b", r"\bCERTID[AÃ]O\b|\bEXTRATO DE ATA\b"),
    }
    if qual not in ancoras:
        raise SystemExit(f"secao invalida: {qual}. Use: {', '.join(ancoras)}")

    ini, fim = ancoras[qual]
    mi = re.search(ini, t)
    if not mi:
        return ""
    resto = t[mi.end():]
    mf = re.search(fim, resto)
    return (t[mi.start():mi.end() + (mf.start() if mf else len(resto))]).strip()


def main():
    ap = argparse.ArgumentParser(description="Extrai texto de PDF de acordao")
    ap.add_argument("origem", help="caminho local ou URL do PDF")
    ap.add_argument("--secao", help="ementa | acordao | relatorio | voto")
    ap.add_argument("--max", type=int, default=0, help="limita caracteres na saida")
    ap.add_argument("--bruto", action="store_true", help="nao remove carimbos")
    ap.add_argument("--saida", help="grava em arquivo em vez de imprimir")
    a = ap.parse_args()

    tmpdir = None
    try:
        if a.origem.startswith("http"):
            tmpdir = tempfile.TemporaryDirectory()
            origem = baixar(a.origem, Path(tmpdir.name) / "acordao.pdf")
        else:
            origem = Path(a.origem).expanduser()
            if not origem.exists():
                raise RuntimeError(f"arquivo nao encontrado: {origem}")

        t = texto(origem, limpar=not a.bruto)
        if a.secao:
            t = secao(t, a.secao) or f"[secao '{a.secao}' nao localizada]"
        if a.max:
            t = t[:a.max]
    except RuntimeError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    finally:
        if tmpdir:
            tmpdir.cleanup()

    if a.saida:
        Path(a.saida).write_text(t, encoding="utf-8")
        print(f"gravado em {a.saida} ({len(t)} caracteres)")
    else:
        print(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
