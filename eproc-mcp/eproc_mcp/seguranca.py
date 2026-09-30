"""Travas de segurança do MCP.

1. Somente leitura. Toda requisição do navegador passa por acao_bloqueada().
   Se o parâmetro "acao" da URL indicar assinatura, lançamento de evento,
   movimentação ou exclusão, a requisição é abortada antes de sair da máquina.
2. Sigilo. aplicar_politica_sigilo() reduz o que vai ao modelo quando o
   processo está em segredo de justiça ou tem nível de sigilo.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from .parsers import normalizar


def extrair_acao(url: str) -> str:
    try:
        consulta = parse_qs(urlparse(url).query)
    except ValueError:
        return ""
    valores = consulta.get("acao") or consulta.get("acao_origem") or []
    return normalizar(valores[0]) if valores else ""


def acao_bloqueada(url: str, bloqueadas: list[str]) -> str | None:
    """Devolve o trecho proibido encontrado na ação da URL, ou None se a URL for permitida."""
    acao = extrair_acao(url)
    if not acao:
        return None
    partes = set(re.split(r"[_\-]", acao))
    for termo in bloqueadas:
        t = normalizar(termo)
        if t in partes or (("_" in t) and t in acao) or acao.startswith(t):
            return t
    return None


def mesmo_sistema(url: str, url_base: str) -> bool:
    return urlparse(url).netloc.lower() == urlparse(url_base).netloc.lower()


def aplicar_politica_sigilo(processo: dict, sigilo: dict, politica: str) -> dict:
    """Recorta o dicionário do processo conforme a política configurada."""
    processo = dict(processo)
    processo["sigilo"] = sigilo
    if not sigilo.get("sigiloso") or politica == "livre":
        return processo
    if politica == "bloquear":
        return {
            "numero": processo.get("numero"),
            "sigilo": sigilo,
            "aviso": "Processo sigiloso. Conteúdo retido pela política 'bloquear'. Triar manualmente.",
        }
    # metadados
    processo.pop("partes", None)
    capa = dict(processo.get("capa") or {})
    for campo in ("valor_causa",):
        capa.pop(campo, None)
    processo["capa"] = capa
    eventos = []
    for ev in processo.get("eventos") or []:
        ev = {k: v for k, v in ev.items() if k in ("evento", "data", "descricao")}
        ev["documentos"] = "retidos (processo sigiloso)"
        eventos.append(ev)
    processo["eventos"] = eventos
    processo["aviso"] = "Processo sigiloso. Partes e documentos retidos pela política 'metadados'."
    return processo
