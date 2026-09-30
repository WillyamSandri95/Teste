"""Leitura do HTML do eproc sem depender do navegador.

As funções recebem o HTML da página e devolvem estruturas simples. Não há
seletor fixo de layout. As tabelas são reconhecidas pelo texto do cabeçalho,
o que tolera pequenas mudanças de tela. O eproc usa o framework "Infra" do
TRF4, então tabelas com a classe infraTable têm preferência.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

RE_CNJ = re.compile(r"\b(\d{7})-?(\d{2})\.?(\d{4})\.?(\d)\.?(\d{2})\.?(\d{4})\b")
RE_CNJ_SO_DIGITOS = re.compile(r"\b\d{20}\b")


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento e com espaços simples. Serve para comparar rótulos."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().lower()


def limpar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def formatar_cnj(numero: str) -> str | None:
    """Devolve o número no formato NNNNNNN-DD.AAAA.J.TR.OOOO ou None."""
    digitos = re.sub(r"\D", "", numero or "")
    if len(digitos) != 20:
        return None
    return f"{digitos[:7]}-{digitos[7:9]}.{digitos[9:13]}.{digitos[13]}.{digitos[14:16]}.{digitos[16:]}"


def encontrar_cnj(texto: str) -> list[str]:
    achados: list[str] = []
    for m in RE_CNJ.finditer(texto or ""):
        num = formatar_cnj("".join(m.groups()))
        if num and num not in achados:
            achados.append(num)
    for m in RE_CNJ_SO_DIGITOS.finditer(texto or ""):
        num = formatar_cnj(m.group(0))
        if num and num not in achados:
            achados.append(num)
    return achados


def sopa(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "html.parser")


def texto_da_pagina(html: str) -> str:
    s = sopa(html)
    for t in s(["script", "style", "noscript"]):
        t.decompose()
    linhas = [limpar(l) for l in s.get_text("\n").splitlines()]
    return "\n".join(l for l in linhas if l)


# ---------------------------------------------------------------- tabelas


@dataclass
class Link:
    texto: str
    href: str
    titulo: str = ""


@dataclass
class Tabela:
    cabecalho: list[str]
    linhas: list[list[str]]
    links: list[list[Link]]
    legenda: str = ""
    elemento: Tag | None = field(default=None, repr=False)

    def indice(self, *rotulos: str) -> int | None:
        """Primeira coluna cujo cabeçalho contém algum dos rótulos."""
        alvos = [normalizar(r) for r in rotulos]
        for i, cab in enumerate(self.cabecalho):
            c = normalizar(cab)
            if any(a in c for a in alvos):
                return i
        return None


def _links_da_celula(celula: Tag, url_base: str) -> list[Link]:
    links = []
    for a in celula.find_all("a"):
        href = a.get("href") or ""
        if not href or href == "#":
            onclick = a.get("onclick") or ""
            if not onclick:
                continue
            href = "javascript:" + onclick
        if not href.lower().startswith("javascript:"):
            href = urljoin(url_base, href)
        texto = limpar(a.get_text(" ")) or limpar(a.get("title") or "")
        links.append(Link(texto=texto, href=href, titulo=limpar(a.get("title") or "")))
    return links


def ler_tabelas(html: str, url_base: str = "") -> list[Tabela]:
    s = sopa(html)
    tabelas: list[Tabela] = []
    todas = s.find_all("table")
    # Tabelas do framework Infra primeiro.
    todas.sort(key=lambda t: 0 if "infraTable" in (t.get("class") or []) else 1)
    for tab in todas:
        # Ignora tabelas que só existem para aninhar outras.
        linhas_tr = [tr for tr in tab.find_all("tr") if tr.find_parent("table") is tab]
        if not linhas_tr:
            continue
        cabecalho: list[str] = []
        corpo = linhas_tr
        primeira = linhas_tr[0]
        if primeira.find("th"):
            cabecalho = [limpar(c.get_text(" ")) for c in primeira.find_all(["th", "td"], recursive=False)]
            corpo = linhas_tr[1:]
        linhas, links = [], []
        for tr in corpo:
            celulas = tr.find_all(["td", "th"], recursive=False)
            if not celulas:
                continue
            linhas.append([limpar(c.get_text(" ")) for c in celulas])
            links.append([lk for c in celulas for lk in _links_da_celula(c, url_base)])
        legenda_tag = tab.find("caption")
        tabelas.append(
            Tabela(
                cabecalho=cabecalho,
                linhas=linhas,
                links=links,
                legenda=limpar(legenda_tag.get_text(" ")) if legenda_tag else "",
                elemento=tab,
            )
        )
    return tabelas


def achar_tabela(tabelas: list[Tabela], obrigatorios: list[str], algum: list[str] | None = None) -> Tabela | None:
    """Tabela cujo cabeçalho contém todos os rótulos obrigatórios e, se houver, algum dos opcionais."""
    for t in tabelas:
        cab = " | ".join(normalizar(c) for c in t.cabecalho)
        if all(normalizar(o) in cab for o in obrigatorios) and (
            not algum or any(normalizar(a) in cab for a in algum)
        ):
            return t
    return None


# ---------------------------------------------------------------- localizadores


def ler_localizadores(html: str, url_base: str = "") -> list[dict]:
    """Lê a tabela de localizadores do painel. Devolve nome, quantidade e link."""
    tabelas = ler_tabelas(html, url_base)
    resultado: list[dict] = []
    vistos: set[str] = set()
    for t in tabelas:
        i_nome = t.indice("localizador")
        if i_nome is None:
            continue
        i_qtd = t.indice("quantidade", "qtd", "processos", "total")
        for linha, links in zip(t.linhas, t.links):
            if i_nome >= len(linha) or not linha[i_nome]:
                continue
            nome = linha[i_nome]
            chave = normalizar(nome)
            if chave in vistos:
                continue
            qtd = None
            if i_qtd is not None and i_qtd < len(linha):
                m = re.search(r"\d+", linha[i_qtd].replace(".", ""))
                qtd = int(m.group(0)) if m else None
            if qtd is None:
                numeros = [c for j, c in enumerate(linha) if j != i_nome and re.fullmatch(r"[\d.]+", c)]
                qtd = int(numeros[0].replace(".", "")) if numeros else None
            link = links[0] if links else None
            vistos.add(chave)
            resultado.append(
                {"nome": nome, "quantidade": qtd, "href": link.href if link else None,
                 "texto_link": link.texto if link else None}
            )
    return resultado


# ---------------------------------------------------------------- lista de processos


def ler_lista_processos(html: str, url_base: str = "") -> dict:
    """Lê a lista de processos de um localizador.

    Cada item traz o número, as colunas encontradas, o link do processo e a
    indicação de conclusão. O indicador "concluso" é heurístico e parte do texto
    da linha, por exemplo "Conclusos para decisão".
    """
    tabelas = ler_tabelas(html, url_base)
    melhor: Tabela | None = None
    melhor_qtd = 0
    for t in tabelas:
        qtd = sum(1 for l in t.linhas if encontrar_cnj(" ".join(l)))
        if qtd > melhor_qtd:
            melhor, melhor_qtd = t, qtd
    if melhor is None:
        return {"processos": [], "cabecalho": [], "legenda": ""}

    processos = []
    for linha, links in zip(melhor.linhas, melhor.links):
        texto_linha = " ".join(linha)
        numeros = encontrar_cnj(texto_linha)
        if not numeros:
            continue
        numero = numeros[0]
        href = None
        for lk in links:
            if formatar_cnj(lk.texto) == numero or numero.replace("-", "").replace(".", "") in lk.href:
                href = lk.href
                break
        if href is None and links:
            href = links[0].href
        colunas = {}
        for i, valor in enumerate(linha):
            nome_col = melhor.cabecalho[i] if i < len(melhor.cabecalho) and melhor.cabecalho[i] else f"coluna_{i}"
            if valor:
                colunas[nome_col] = valor
        n = normalizar(texto_linha)
        processos.append(
            {
                "numero": numero,
                "colunas": colunas,
                "href": href,
                "concluso": bool(re.search(r"conclus[oa]s?\b|conclusao", n)),
            }
        )
    return {"processos": processos, "cabecalho": melhor.cabecalho, "legenda": melhor.legenda}


# ---------------------------------------------------------------- capa do processo

ROTULOS_CAPA = {
    "numero": ["nº do processo", "n. do processo", "numero do processo"],
    "classe": ["classe da acao", "classe judicial", "classe"],
    "assunto": ["assuntos", "assunto principal", "assunto"],
    "data_autuacao": ["data de autuacao", "autuacao", "data da autuacao"],
    "situacao": ["situacao"],
    "orgao_julgador": ["orgao julgador", "juizo"],
    "juiz": ["juiz(a)", "juiz", "magistrado"],
    "competencia": ["competencia"],
    "valor_causa": ["valor da causa"],
    "localizadores": ["localizador(es)", "localizadores", "localizador"],
    "sigilo": ["nivel de sigilo", "sigilo do processo", "sigilo", "segredo de justica"],
    "prioridade": ["prioridade", "prioridades"],
}


def _valor_apos_rotulo(el: Tag) -> str:
    """Valor associado a um rótulo, seja pelo atributo for, pela célula ao lado ou pelo irmão seguinte."""
    if el.name == "label" and el.get("for"):
        raiz = el
        while raiz.parent is not None:
            raiz = raiz.parent
        destino = raiz.find(id=el["for"])
        if destino is not None:
            return limpar(destino.get("value") or destino.get_text(" "))
    if el.name in ("td", "th", "dt"):
        prox = el.find_next_sibling(["td", "dd", "th"])
        if prox is not None:
            return limpar(prox.get_text(" "))
    prox = el.find_next_sibling()
    if prox is not None and prox.name not in ("label",):
        return limpar(prox.get_text(" "))
    # Rótulo e valor no mesmo nó de texto, como "Classe: Procedimento Comum".
    pai_txt = limpar(el.parent.get_text(" ")) if el.parent else ""
    proprio = limpar(el.get_text(" "))
    if pai_txt.startswith(proprio):
        return pai_txt[len(proprio):].lstrip(" :-")
    return ""


def ler_capa(html: str) -> dict:
    s = sopa(html)
    for t in s(["script", "style", "noscript"]):
        t.decompose()
    capa: dict[str, str] = {}
    candidatos = s.find_all(["label", "span", "td", "th", "dt", "strong", "b", "div"])
    for chave, rotulos in ROTULOS_CAPA.items():
        for el in candidatos:
            txt = normalizar(el.get_text(" "))
            if not txt or len(txt) > 40:
                continue
            txt = txt.rstrip(":").strip()
            if txt in rotulos:
                valor = _valor_apos_rotulo(el)
                if valor and normalizar(valor).rstrip(":") not in rotulos:
                    capa[chave] = valor[:500]
                    break
    texto = texto_da_pagina(html)
    # Fallback por linhas "Rótulo: valor".
    for linha in texto.splitlines():
        if ":" not in linha:
            continue
        rot, _, val = linha.partition(":")
        rot_n = normalizar(rot)
        for chave, rotulos in ROTULOS_CAPA.items():
            if chave not in capa and rot_n in rotulos and limpar(val):
                capa[chave] = limpar(val)[:500]
    if "numero" in capa:
        capa["numero"] = formatar_cnj(capa["numero"]) or capa["numero"]
    else:
        nums = encontrar_cnj(texto)
        if nums:
            capa["numero"] = nums[0]
    return capa


def detectar_sigilo(html: str, capa: dict | None = None) -> dict:
    """Detecta segredo de justiça ou sigilo. Na dúvida, trata como sigiloso."""
    texto = normalizar(texto_da_pagina(html))
    campo = normalizar((capa or {}).get("sigilo", ""))
    if "segredo de justica" in texto and "sem segredo" not in texto:
        return {"sigiloso": True, "motivo": "menção a segredo de justiça"}
    nivel = re.search(r"sigilo[^\n]{0,60}?nivel\s*(\d)|nivel\s*(\d)[^\n]{0,20}?sigilo|sigilo[^\n]{0,15}?\(\s*nivel\s*(\d)", texto)
    if nivel:
        n = int(next(g for g in nivel.groups() if g is not None))
        return {"sigiloso": n > 0, "motivo": f"nível de sigilo {n}"}
    if campo:
        if "sem sigilo" in campo or campo in {"0", "nao", "publico"}:
            return {"sigiloso": False, "motivo": f"campo sigilo = {campo}"}
        return {"sigiloso": True, "motivo": f"campo sigilo = {campo}"}
    if "sem sigilo" in texto:
        return {"sigiloso": False, "motivo": "página indica sem sigilo"}
    if re.search(r"\bsigilos[oa]\b|\bsigilo\b", texto):
        return {"sigiloso": True, "motivo": "menção a sigilo sem nível identificado"}
    return {"sigiloso": False, "motivo": "nenhuma menção a sigilo"}


def detectar_marcadores(texto: str, marcadores: dict[str, list[str]]) -> list[str]:
    n = normalizar(texto)
    achados = []
    for rotulo, padroes in marcadores.items():
        if any(re.search(p, n) for p in padroes):
            achados.append(rotulo)
    return achados


def ler_partes(html: str) -> list[dict]:
    """Partes do processo pela tabela que tem cabeçalho de polo."""
    tabelas = ler_tabelas(html)
    partes = []
    for t in tabelas:
        cab = normalizar(" ".join(t.cabecalho))
        if not any(p in cab for p in ("autor", "reu", "polo", "requerente", "exequente", "parte")):
            continue
        for j, rotulo in enumerate(t.cabecalho):
            for linha in t.linhas:
                if j < len(linha) and linha[j]:
                    partes.append({"polo": rotulo, "nome": linha[j][:200]})
        if partes:
            break
    return partes


# ---------------------------------------------------------------- eventos


def ler_eventos(html: str, url_base: str = "") -> list[dict]:
    """Eventos do processo, do mais recente para o mais antigo."""
    tabelas = ler_tabelas(html, url_base)
    t = achar_tabela(tabelas, ["evento"], ["descri", "data"])
    if t is None:
        return []
    i_ev = t.indice("evento")
    i_data = t.indice("data")
    i_desc = t.indice("descri")
    i_usu = t.indice("usuario")
    i_doc = t.indice("documento")
    eventos = []
    for linha, links in zip(t.linhas, t.links):
        def col(i):
            return linha[i] if i is not None and i < len(linha) else ""
        m = re.search(r"\d+", col(i_ev))
        if not m:
            continue
        documentos = []
        for lk in links:
            if lk.href.lower().startswith("javascript:") and "documento" not in lk.href.lower():
                continue
            if not lk.texto:
                continue
            if i_doc is None or lk.texto in col(i_doc) or "documento" in lk.href.lower():
                documentos.append({"nome": lk.texto, "href": lk.href})
        eventos.append(
            {
                "evento": int(m.group(0)),
                "data": col(i_data),
                "descricao": col(i_desc)[:1000],
                "usuario": col(i_usu),
                "documentos": documentos,
            }
        )
    eventos.sort(key=lambda e: e["evento"], reverse=True)
    return eventos


# ---------------------------------------------------------------- diagnóstico


def resumir_pagina(html: str, url_base: str = "") -> dict:
    """Resumo estrutural para calibrar o MCP. Não devolve conteúdo das células."""
    s = sopa(html)
    tabelas = ler_tabelas(html, url_base)
    formularios = []
    for f in s.find_all("form"):
        campos = [
            {"tag": c.name, "id": c.get("id"), "name": c.get("name"), "type": c.get("type")}
            for c in f.find_all(["input", "select", "textarea", "button"])
            if c.get("type") != "hidden"
        ][:30]
        formularios.append({"id": f.get("id"), "action": f.get("action"), "campos": campos})
    acoes = sorted({m.group(1) for a in s.find_all("a", href=True)
                    for m in [re.search(r"acao=([\w\-]+)", a["href"])] if m})
    return {
        "titulo": limpar(s.title.get_text()) if s.title else "",
        "tabelas": [
            {"id": t.elemento.get("id") if t.elemento else None,
             "classes": t.elemento.get("class") if t.elemento else None,
             "legenda": t.legenda, "cabecalho": t.cabecalho, "qtd_linhas": len(t.linhas)}
            for t in tabelas if t.linhas
        ][:25],
        "formularios": formularios[:10],
        "acoes_em_links": acoes[:80],
        "tem_campo_senha": bool(s.find("input", attrs={"type": "password"})),
    }
