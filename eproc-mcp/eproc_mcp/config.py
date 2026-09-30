"""Carrega a configuração do MCP a partir de um arquivo TOML.

Ordem de busca do arquivo
1. variável de ambiente EPROC_MCP_CONFIG
2. ./config.toml
3. ~/.eproc-mcp/config.toml

Todo campo ausente assume o valor padrão definido em Config.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

PASTA_BASE = Path.home() / ".eproc-mcp"

# Marcadores procurados na capa e na lista. A chave é o rótulo devolvido ao
# modelo e o valor é a lista de expressões regulares, sem acento e em minúsculas.
MARCADORES_PADRAO: dict[str, list[str]] = {
    "reu_preso": [r"reu preso", r"\bpreso\b", r"prisao preventiva", r"prisao em flagrante"],
    "idoso": [r"\bidoso", r"estatuto da pessoa idosa", r"maior de 60", r"maior de 80"],
    "crianca_adolescente": [r"crianca", r"adolescente", r"\beca\b", r"menor de idade"],
    "pessoa_com_deficiencia": [r"pessoa com deficiencia", r"\bpcd\b"],
    "doenca_grave": [r"doenca grave", r"molestia grave"],
    "violencia_domestica": [r"violencia domestica", r"maria da penha", r"medida protetiva"],
    "liminar_tutela": [r"liminar", r"tutela (de urgencia|antecipada|provisoria|cautelar)", r"antecipacao de tutela"],
    "urgente": [r"urgente", r"urgencia", r"plantao"],
    "prioridade": [r"prioridade", r"tramitacao prioritaria"],
    "meta_cnj": [r"meta \d", r"meta cnj"],
    "gratuidade": [r"justica gratuita", r"gratuidade", r"\bajg\b", r"assistencia judiciaria"],
    "habeas_corpus_ms": [r"habeas corpus", r"mandado de seguranca"],
}

# Trechos que, no parâmetro "acao" da URL do eproc, indicam operação que altera
# o processo. Requisições com esses trechos são abortadas pelo navegador.
ACOES_BLOQUEADAS_PADRAO: list[str] = [
    "assinar", "assinatura", "excluir", "exclusao", "remover", "cancelar",
    "lancar", "lancamento", "movimentar", "cadastrar", "incluir", "alterar",
    "salvar", "gravar", "editar", "redistribuir", "intimar", "citar", "expedir",
    "juntar", "upload", "transferir", "concluir", "devolver", "arquivar",
    "desarquivar", "suspender", "sobrestar", "minuta", "baixa_processo",
    "baixar_processo", "enviar", "remeter", "encaminhar",
]


@dataclass
class Config:
    # Endereço do eproc de 1º grau do TJSC. Confirme no navegador antes do uso.
    url_base: str = "https://eproc1g.tjsc.jus.br/eproc/"

    # Navegador. "msedge" ou "chrome" usam o navegador já instalado no Windows,
    # o que facilita o login por certificado digital. Vazio usa o Chromium do Playwright.
    canal_navegador: str = "msedge"
    headless: bool = False
    pasta_perfil: str = str(PASTA_BASE / "perfil-navegador")

    # Ritmo das consultas, para não sobrecarregar o sistema nem parecer robô.
    intervalo_entre_paginas_s: float = 1.5
    timeout_navegacao_s: float = 45.0
    max_processos_por_coleta: int = 50
    max_paginas_por_lista: int = 10
    max_caracteres_documento: int = 20000

    # Localizadores autorizados. Lista vazia libera todos.
    localizadores_permitidos: list[str] = field(default_factory=list)

    # Política para processos em segredo de justiça ou com sigilo.
    # "bloquear" devolve apenas o número e o aviso de sigilo.
    # "metadados" devolve capa resumida e eventos, sem partes e sem documentos.
    # "livre" devolve tudo.
    politica_sigilo: str = "metadados"

    # Devolve os nomes das partes ao modelo em processos sem sigilo.
    incluir_partes: bool = False

    # Pastas locais.
    pasta_saida: str = str(Path.home() / "eproc-mcp" / "triagens")
    pasta_diagnostico: str = str(PASTA_BASE / "diagnostico")

    # Seletores CSS ajustáveis depois do diagnóstico da página real.
    seletor_proxima_pagina: str = (
        "#lnkInfraProximaPaginaSuperior, #lnkInfraProximaPaginaInferior, "
        "a[title*='Próxima'], a[title*='próxima']"
    )
    seletor_pesquisa_rapida: str = "#txtNumProcessoPesquisaRapida"
    # Modelo de URL para abrir processo pelo número, usado quando não há link em cache.
    url_processo_modelo: str = "controlador.php?acao=processo_selecionar&num_processo={numero}"

    acoes_bloqueadas: list[str] = field(default_factory=lambda: list(ACOES_BLOQUEADAS_PADRAO))
    marcadores: dict[str, list[str]] = field(default_factory=lambda: dict(MARCADORES_PADRAO))


def localizar_arquivo() -> Path | None:
    candidatos = []
    if os.environ.get("EPROC_MCP_CONFIG"):
        candidatos.append(Path(os.environ["EPROC_MCP_CONFIG"]).expanduser())
    candidatos += [Path.cwd() / "config.toml", PASTA_BASE / "config.toml"]
    for caminho in candidatos:
        if caminho.is_file():
            return caminho
    return None


def carregar(caminho: Path | None = None) -> Config:
    caminho = caminho or localizar_arquivo()
    cfg = Config()
    if caminho is None:
        return cfg
    with open(caminho, "rb") as fh:
        dados = tomllib.load(fh)
    conhecidos = {f.name for f in fields(Config)} | {"acoes_bloqueadas_extras"}
    desconhecidos = set(dados) - conhecidos
    if desconhecidos:
        raise ValueError(f"Campos desconhecidos em {caminho}, {sorted(desconhecidos)}")
    for nome, valor in dados.items():
        if nome == "marcadores":
            # Marcadores do arquivo complementam ou substituem os padrões, chave a chave.
            cfg.marcadores.update(valor)
        elif nome == "acoes_bloqueadas_extras":
            cfg.acoes_bloqueadas += valor
        else:
            setattr(cfg, nome, valor)
    if cfg.politica_sigilo not in {"bloquear", "metadados", "livre"}:
        raise ValueError("politica_sigilo deve ser bloquear, metadados ou livre")
    return cfg
