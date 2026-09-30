"""Servidor MCP de triagem de processos conclusos no eproc.

Somente leitura. O login é manual. As ferramentas coletam dados e o modelo
faz a classificação. O quadro final pode ser gravado localmente em planilha.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Literal

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Servidor
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Servidor

from . import config as config_mod
from . import exportar, parsers
from .navegador import ErroEproc, Navegador
from .seguranca import aplicar_politica_sigilo

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("eproc_mcp")

INSTRUCOES = """\
MCP de leitura do eproc para triagem de processos conclusos.

Fluxo recomendado
1. abrir_eproc. O usuário faz o login na janela aberta. Depois status_sessao.
2. listar_localizadores para ver os nomes exatos.
3. coletar_triagem no localizador desejado. Ela devolve capa, marcadores e últimos eventos de cada processo concluso.
4. Classifique cada processo pelos critérios do usuário. Use ler_documento só quando o último evento não bastar.
5. exportar_triagem com as linhas classificadas.

Regras
O MCP é somente leitura e recusa assinar, lançar evento, movimentar ou alterar localizador.
Processos sigilosos chegam recortados conforme a política do config.toml. Respeite o aviso e não tente contornar.
A triagem é auxiliar. A decisão sobre cada processo cabe ao magistrado.
"""

mcp = _Servidor("eproc-triagem", instructions=INSTRUCOES)

_cfg: config_mod.Config | None = None
_nav: Navegador | None = None
_sigilo: dict[str, dict] = {}


def _estado() -> tuple[config_mod.Config, Navegador]:
    global _cfg, _nav
    if _cfg is None:
        _cfg = config_mod.carregar()
        log.info("Configuração carregada. url_base=%s política=%s", _cfg.url_base, _cfg.politica_sigilo)
    if _nav is None:
        _nav = Navegador(_cfg)
    return _cfg, _nav


def _erro(e: Exception) -> dict:
    log.exception("Falha na ferramenta")
    return {"erro": str(e) or e.__class__.__name__}


@mcp.tool()
async def abrir_eproc() -> dict[str, Any]:
    """Abre o navegador no eproc com perfil persistente. Se não houver sessão ativa, o usuário
    deve fazer o login manualmente na janela aberta e depois chamar status_sessao."""
    try:
        cfg, nav = _estado()
        await nav.abrir()
        logado = await nav.logado()
        return {
            "logado": logado,
            "url": nav.url_atual.split("&hash=")[0],
            "orientacao": None if logado else "Faça o login na janela do navegador e chame status_sessao.",
        }
    except Exception as e:
        msg = str(e)
        if "channel" in msg.lower() or "executable" in msg.lower():
            msg += " | Verifique canal_navegador no config.toml (msedge, chrome ou vazio com playwright install chromium)."
        return _erro(RuntimeError(msg))


@mcp.tool()
async def status_sessao() -> dict[str, Any]:
    """Informa se o navegador está aberto e se a sessão do eproc está autenticada."""
    try:
        cfg, nav = _estado()
        return {
            "navegador_aberto": nav.aberto,
            "logado": await nav.logado(),
            "url": nav.url_atual.split("&hash=")[0],
            "politica_sigilo": cfg.politica_sigilo,
            "localizadores_permitidos": cfg.localizadores_permitidos or "todos",
            "requisicoes_bloqueadas": len(nav.bloqueios),
        }
    except Exception as e:
        return _erro(e)


@mcp.tool()
async def listar_localizadores() -> dict[str, Any]:
    """Lista os localizadores do painel com a quantidade de processos em cada um."""
    try:
        cfg, nav = _estado()
        itens = await nav.listar_localizadores()
        permitidos = [parsers.normalizar(p) for p in cfg.localizadores_permitidos]
        saida = []
        for i in itens:
            n = parsers.normalizar(i["nome"])
            autorizado = not permitidos or any(n == p or p in n for p in permitidos)
            saida.append({"nome": i["nome"], "quantidade": i["quantidade"], "autorizado": autorizado})
        if not saida:
            return {"localizadores": [], "aviso": "Nenhuma tabela de localizadores reconhecida. Rode diagnosticar_pagina."}
        return {"localizadores": saida}
    except Exception as e:
        return _erro(e)


@mcp.tool()
async def listar_processos(localizador: str, apenas_conclusos: bool = True, max_paginas: int = 5) -> dict[str, Any]:
    """Lista os processos de um localizador. Com apenas_conclusos, filtra as linhas que indicam
    conclusão, como "Conclusos para decisão". O filtro é textual e deve ser conferido."""
    try:
        _, nav = _estado()
        return await nav.listar_processos(localizador, apenas_conclusos, max_paginas)
    except Exception as e:
        return _erro(e)


async def _processo_recortado(nav: Navegador, cfg: config_mod.Config, numero: str, n_eventos: int) -> dict:
    dados, html = await nav.ler_processo(numero, n_eventos)
    sigilo = parsers.detectar_sigilo(html, dados.get("capa"))
    _sigilo[dados["numero"]] = sigilo
    return aplicar_politica_sigilo(dados, sigilo, cfg.politica_sigilo)


@mcp.tool()
async def ler_processo(numero: str, n_eventos: int = 10) -> dict[str, Any]:
    """Lê a capa, os marcadores de prioridade e os últimos eventos de um processo.
    O número pode vir com ou sem pontuação."""
    try:
        cfg, nav = _estado()
        return await _processo_recortado(nav, cfg, numero, max(1, min(n_eventos, 50)))
    except Exception as e:
        return _erro(e)


@mcp.tool()
async def ler_documento(numero: str, evento: int, documento: str | None = None) -> dict[str, Any]:
    """Extrai o texto de um documento de um evento, em PDF ou HTML. Exige ler_processo antes.
    Sem o nome do documento, lê o primeiro do evento. Recusado em processo sigiloso, salvo política livre."""
    try:
        cfg, nav = _estado()
        numero_fmt = parsers.formatar_cnj(numero)
        if cfg.politica_sigilo != "livre":
            if numero_fmt not in _sigilo:
                await _processo_recortado(nav, cfg, numero, 1)
            sigilo = _sigilo.get(numero_fmt, {"sigiloso": True, "motivo": "sigilo não verificado"})
            if sigilo.get("sigiloso"):
                return {"numero": numero_fmt, "recusado": True,
                        "motivo": f"Processo sigiloso, {sigilo['motivo']}. Política {cfg.politica_sigilo}."}
        return await nav.ler_documento(numero, evento, documento)
    except Exception as e:
        return _erro(e)


@mcp.tool()
async def coletar_triagem(localizador: str, apenas_conclusos: bool = True, n_eventos: int = 5,
                          limite: int = 30) -> dict[str, Any]:
    """Coleta, de uma vez, os dados de triagem dos processos de um localizador. Para cada processo
    devolve colunas da lista, capa, marcadores e últimos eventos. Respeita o intervalo entre páginas
    e o teto max_processos_por_coleta do config.toml."""
    try:
        cfg, nav = _estado()
        lista = await nav.listar_processos(localizador, apenas_conclusos, cfg.max_paginas_por_lista)
        teto = max(1, min(limite, cfg.max_processos_por_coleta))
        processos = []
        for item in lista["processos"][:teto]:
            try:
                dados = await _processo_recortado(nav, cfg, item["numero"], max(1, min(n_eventos, 20)))
                dados["colunas_da_lista"] = item["colunas"]
            except ErroEproc as e:
                dados = {"numero": item["numero"], "erro": str(e), "colunas_da_lista": item["colunas"]}
            processos.append(dados)
        return {
            "localizador": lista["localizador"],
            "total_na_lista": lista["total_devolvido"],
            "coletados": len(processos),
            "restantes": max(0, lista["total_devolvido"] - len(processos)),
            "processos": processos,
        }
    except Exception as e:
        return _erro(e)


@mcp.tool()
async def exportar_triagem(linhas: list[dict[str, Any]], nome_arquivo: str | None = None,
                           formato: Literal["xlsx", "csv"] = "xlsx") -> dict[str, Any]:
    """Grava o quadro de triagem na pasta_saida local. Cada linha é um dicionário, por exemplo
    numero, classe, concluso_desde, prioridade, ato_sugerido, skill_sugerida, observacao."""
    try:
        cfg, _ = _estado()
        caminho = exportar.gravar(linhas, cfg.pasta_saida, nome_arquivo, formato)
        return {"arquivo": str(caminho), "linhas": len(linhas)}
    except Exception as e:
        return _erro(e)


@mcp.tool()
async def diagnosticar_pagina(salvar_arquivos: bool = True) -> dict[str, Any]:
    """Resume a estrutura da página aberta, com tabelas, cabeçalhos, formulários e ações dos links,
    sem o conteúdo das células. Com salvar_arquivos, grava HTML e captura de tela na pasta local
    de diagnóstico. Serve para calibrar o MCP quando alguma leitura falhar."""
    try:
        _, nav = _estado()
        return await nav.diagnosticar(salvar_arquivos)
    except Exception as e:
        return _erro(e)


@mcp.tool()
async def fechar_eproc() -> dict[str, Any]:
    """Fecha o navegador. O perfil fica salvo e a próxima abertura pode reaproveitar a sessão."""
    try:
        _, nav = _estado()
        await nav.fechar()
        return {"fechado": True}
    except Exception as e:
        return _erro(e)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
