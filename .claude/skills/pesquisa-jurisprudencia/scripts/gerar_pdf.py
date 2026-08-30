#!/usr/bin/env python3
"""Converte o relatorio de pesquisa (Markdown) num PDF paginado.

Usa o Chrome em modo headless, que ja existe no macOS e entrega tipografia e
quebras de pagina muito melhores do que as bibliotecas puras de PDF. Nao ha nada
para instalar.

Uso:
    python3 gerar_pdf.py relatorio.md -o /caminho/saida.pdf \
        --titulo "Responsabilidade civil do Estado por omissao"

Convencoes de marcacao que o CSS trata de forma especial:
  - `> texto`            blockquote, usado para transcrever ementas
  - `::: qualificado`    bloco em destaque, para tese vinculante/qualificada
    conteudo
    `:::`
  - `---`                quebra de pagina forcada
"""

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

# Paleta e diagramacao extraidas do modelo institucional de relatorio do
# gabinete (Preparo de AIJ). Manter a identidade visual entre os relatorios
# importa: quem recebe reconhece o documento de imediato.
NAVY = "#1b3b5f"

CSS = f"""
@page {{ size: A4; margin: 1.6cm 1.5cm 1.7cm 1.5cm; }}
* {{ box-sizing: border-box; }}
body {{
  font: 10pt/1.5 "DejaVu Sans", Verdana, "Helvetica Neue", Arial, sans-serif;
  color: #1c1f23; margin: 0;
}}

/* Faixa de cabecalho */
.capa {{ background: {NAVY}; color: #fff; padding: 16px 20px 18px; margin-bottom: 20px; }}
.capa .kicker {{
  font-size: 8pt; letter-spacing: .09em; text-transform: uppercase;
  color: #c3d1e0; margin-bottom: 8px;
}}
.capa h1 {{ font-size: 17pt; font-weight: 700; text-align: center; margin: 0 0 12px; }}
.capa .linha {{ font-size: 9.5pt; color: #dce5ee; margin-bottom: 4px; }}
.capa .destaque {{ font-size: 10pt; font-weight: 700; color: #fff; margin-top: 8px; }}

/* Aviso em faixa tracejada, para ressalvas que o leitor nao pode ignorar */
.aviso {{
  border: 1.5px dashed #e6b0ab; background: #fef7f7; color: #c0392b;
  font-size: 9pt; font-weight: 700; text-align: center;
  padding: 8px 12px; margin: 0 0 20px;
}}

h2 {{
  font-size: 13pt; font-weight: 700; color: {NAVY}; text-align: center;
  margin: 24px 0 0; padding-bottom: 7px;
  border-bottom: 2px solid {NAVY}; page-break-after: avoid;
}}
h2 + * {{ margin-top: 12px; }}
h3 {{ font-size: 10.5pt; font-weight: 700; color: {NAVY};
      margin: 18px 0 7px; page-break-after: avoid; }}
h4 {{ font-size: 9.5pt; font-weight: 700; color: #3d4752;
      margin: 14px 0 5px; page-break-after: avoid; }}
p {{ margin: 0 0 9px; text-align: justify; hyphens: auto; }}
ul, ol {{ margin: 0 0 10px; padding-left: 22px; }}
li {{ margin-bottom: 5px; }}
a {{ color: #10457e; text-decoration: none; border-bottom: .5px solid #a8bed6; }}
code {{ font: 8.5pt "DejaVu Sans Mono", Menlo, monospace;
        background: #f0f3f6; padding: 1px 4px; border-radius: 3px; }}

/* Tabelas: cabecalho navy solido, zebra clara, sem bordas verticais pesadas */
table {{ width: 100%; border-collapse: collapse; margin: 12px 0;
         font-size: 9pt; page-break-inside: avoid; }}
thead th {{
  background: {NAVY}; color: #fff; font-weight: 700; text-align: left;
  padding: 7px 10px; border: none;
}}
tbody td {{ padding: 7px 10px; border: none; vertical-align: top;
            border-bottom: 1px solid #e3e9ef; }}
tbody tr:nth-child(odd) {{ background: #f4f7fa; }}

/* Ementas transcritas. O recuo e o corpo menor sinalizam, de relance, o que e
   texto do tribunal e o que e leitura nossa. */
blockquote {{
  margin: 10px 0 14px; padding: 10px 14px;
  border-left: 3px solid #98a6b6; background: #f4f7fa;
  font-size: 8.8pt; line-height: 1.5; text-align: justify;
  page-break-inside: avoid;
}}
blockquote p {{ margin: 0 0 6px; }}
blockquote p:last-child {{ margin-bottom: 0; }}

/* Caixas de destaque, no padrao do modelo: barra lateral colorida por especie */
.callout {{ margin: 12px 0; padding: 10px 14px; page-break-inside: avoid;
            font-size: 9.3pt; }}
.callout p {{ margin: 0 0 6px; }}
.callout p:last-child {{ margin-bottom: 0; }}
.callout .rot {{ font-weight: 700; }}

.callout.qualificado {{ border-left: 4px solid #b8860b; background: #eef3f8; }}
.callout.qualificado .rot {{ color: #7a5c08; }}
.callout.alerta {{ border-left: 4px solid #c0392b; background: #fdecea; }}
.callout.alerta .rot {{ color: #a5342a; }}
.callout.isolada {{ border-left: 4px solid #c9962c; background: #fff8e7; }}
.callout.isolada .rot {{ color: #8a6d1a; }}

hr {{ page-break-after: always; border: 0; height: 0; margin: 0; }}
.rodape {{ margin-top: 26px; padding-top: 10px; border-top: 1px solid #d4dae0;
           font-size: 8pt; line-height: 1.45; color: #6b7b8c; }}
"""


def _acha_chrome():
    for c in CHROMES:
        if Path(c).exists():
            return c
    for n in ("google-chrome", "chromium", "chromium-browser"):
        p = shutil.which(n)
        if p:
            return p
    return None


# Especies de caixa de destaque, no padrao do modelo institucional: simbolo,
# rotulo em caixa alta e negrito, texto correndo na mesma linha.
ESPECIES = {
    "qualificado": ("■", "PRECEDENTE QUALIFICADO"),
    "vinculante":  ("■", "TESE VINCULANTE"),
    "isolada":     ("★", "POSIÇÃO ISOLADA"),
    "alerta":      ("▲", "ATENÇÃO"),
}


def _blocos_destaque(texto):
    """Converte `::: especie [| rotulo] ... :::` nas caixas do layout.

    O rotulo pode ser sobrescrito depois de uma barra vertical, para casos em
    que o texto padrao nao serve -- por exemplo `::: qualificado | STF, TEMA 366`.
    """
    import markdown as md

    def rep(m):
        cabec = m.group(1).strip()
        especie, _, rot_custom = (p.strip() for p in cabec.partition("|"))
        simbolo, rot = ESPECIES.get(especie.lower(), ("■", especie.upper()))
        if rot_custom:
            rot = rot_custom

        corpo = md.markdown(m.group(2).strip(), extensions=["extra"])
        etiqueta = (f'<span class="rot">{simbolo} '
                    f'{html.escape(rot)}:</span> ')
        # A etiqueta entra dentro do primeiro paragrafo para correr na mesma
        # linha do texto, como no modelo.
        if corpo.startswith("<p>"):
            corpo = "<p>" + etiqueta + corpo[3:]
        else:
            corpo = f"<p>{etiqueta}</p>" + corpo

        classe = especie.lower() if especie.lower() in ESPECIES else "qualificado"
        return f'<div class="callout {classe}">{corpo}</div>'

    return re.sub(r"^::: *([^\n]+)\n(.*?)^:::\s*$", rep, texto, flags=re.S | re.M)


def construir_html(md_texto, titulo, subtitulo="", linhas=None, aviso=""):
    import markdown as md

    corpo = md.markdown(
        _blocos_destaque(md_texto),
        extensions=["extra", "sane_lists", "toc"],
    )
    data = datetime.now().strftime("%d/%m/%Y")

    partes = []
    if subtitulo:
        partes.append(f'<div class="linha">{html.escape(subtitulo)}</div>')
    for ln in (linhas or []):
        partes.append(f'<div class="linha">{html.escape(ln)}</div>')
    partes.append(f'<div class="linha">Documento gerado em {data}</div>')

    faixa_aviso = (f'<div class="aviso">{html.escape(aviso)}</div>' if aviso else "")

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>{html.escape(titulo)}</title><style>{CSS}</style></head><body>
<div class="capa">
  <div class="kicker">Relatório de pesquisa de jurisprudência</div>
  <h1>{html.escape(titulo)}</h1>
  {''.join(partes)}
  <div class="destaque">Tribunais consultados: TJSC, STJ e STF</div>
</div>
{faixa_aviso}
{corpo}
<div class="rodape">
Pesquisa realizada nos portais oficiais do Tribunal de Justiça de Santa Catarina,
do Superior Tribunal de Justiça e do Supremo Tribunal Federal. As ementas foram
transcritas da fonte oficial. Confira a vigência das teses e a eventual
existência de julgados posteriores antes de citar em decisão.
</div>
</body></html>"""


def gerar(md_path, saida, titulo, subtitulo="", linhas=None, aviso=""):
    chrome = _acha_chrome()
    if not chrome:
        raise RuntimeError(
            "Chrome/Chromium nao encontrado. Instale um deles ou gere o relatorio "
            "apenas em Markdown."
        )

    texto = Path(md_path).read_text(encoding="utf-8")
    saida = Path(saida).expanduser()
    saida.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        htmlf = Path(tmp) / "relatorio.html"
        htmlf.write_text(construir_html(texto, titulo, subtitulo, linhas, aviso),
                         encoding="utf-8")
        r = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             "--no-pdf-header-footer", "--print-to-pdf-no-header",
             f"--print-to-pdf={saida}", htmlf.as_uri()],
            capture_output=True, timeout=180,
        )

    if not saida.exists() or saida.stat().st_size == 0:
        raise RuntimeError(f"Chrome nao gerou o PDF: {r.stderr.decode(errors='replace')[-500:]}")
    return saida


def main():
    ap = argparse.ArgumentParser(description="Gera o PDF do relatorio de pesquisa")
    ap.add_argument("markdown")
    ap.add_argument("-o", "--saida", required=True)
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--subtitulo", default="")
    ap.add_argument("--linha", action="append", default=[],
                    help="linha extra no cabecalho; pode repetir")
    ap.add_argument("--aviso", default="",
                    help="faixa tracejada de ressalva no topo")
    a = ap.parse_args()

    try:
        p = gerar(a.markdown, a.saida, a.titulo, a.subtitulo, a.linha, a.aviso)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1

    print(f"PDF gerado: {p}  ({p.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
