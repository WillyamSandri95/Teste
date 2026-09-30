"""Teste com navegador real contra o eproc simulado. Exige Chromium do Playwright."""

import os

import pytest

from eproc_mcp import server
from eproc_mcp.config import Config
from eproc_mcp.navegador import Navegador

from . import eproc_simulado


@pytest.fixture
async def ambiente(tmp_path):
    srv, url = eproc_simulado.iniciar()
    cfg = Config(
        url_base=url, canal_navegador="", headless=True, pasta_perfil=str(tmp_path / "perfil"),
        intervalo_entre_paginas_s=0, pasta_saida=str(tmp_path / "saida"),
        pasta_diagnostico=str(tmp_path / "diag"),
    )
    nav = Navegador(cfg)
    server._cfg, server._nav = cfg, nav
    server._sigilo.clear()
    yield cfg, nav
    await nav.fechar()
    srv.shutdown()
    server._cfg = server._nav = None


async def _login(nav):
    await nav._pagina.fill("input[name=usuario]", "teste")
    await nav._pagina.fill("input[type=password]", "teste")
    await nav._pagina.click("button[type=submit]")
    await nav._pagina.wait_for_load_state()


@pytest.mark.skipif(not os.path.isdir(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")),
                    reason="Chromium do Playwright ausente")
async def test_fluxo_completo(ambiente):
    cfg, nav = ambiente
    r = await server.abrir_eproc()
    assert r["logado"] is False
    assert (await server.listar_localizadores())["erro"].startswith("Sessão do eproc não autenticada")

    await _login(nav)
    assert (await server.status_sessao())["logado"] is True

    locs = await server.listar_localizadores()
    assert [l["nome"] for l in locs["localizadores"]] == ["GAB - Decisão Urgente", "GAB - Sentença"]

    lista = await server.listar_processos("decisão urgente", apenas_conclusos=True)
    assert lista["paginas_lidas"] == 2 and lista["total_lido"] == 3
    assert [p["numero"] for p in lista["processos"]] == ["5000001-12.2026.8.24.0008", "5000002-22.2026.8.24.0008"]
    assert "Autor" not in lista["processos"][0]["colunas"]

    coleta = await server.coletar_triagem("GAB - Decisão Urgente")
    comum, sigiloso = coleta["processos"]
    assert comum["capa"]["classe"] == "Procedimento Comum Cível"
    assert comum["sigilo"]["sigiloso"] is False
    assert "idoso" in comum["marcadores"]
    assert comum["eventos"][0]["descricao"] == "Conclusos para decisão"
    assert sigiloso["sigilo"]["sigiloso"] is True
    assert sigiloso["eventos"][0]["documentos"].startswith("retidos")

    doc = await server.ler_documento("5000001-12.2026.8.24.0008", 2)
    assert doc["tipo"] == "pdf" and "texto de teste" in doc["texto"]
    recusa = await server.ler_documento("5000002-22.2026.8.24.0008", 1)
    assert recusa["recusado"] is True

    # Processo fora do cache abre pela pesquisa rápida.
    nav.links_processos.clear()
    proc = await server.ler_processo("50000033320268240008", n_eventos=1)
    assert proc["capa"]["classe"] == "Execução de Título Extrajudicial"

    # Trava de somente leitura.
    await nav._ir(cfg.url_base)
    await nav._pagina.click("text=Assinar em bloco")
    assert any("assinar" in b["termo"] for b in nav.bloqueios)
    assert not any("minuta_assinar" in r for r in eproc_simulado.Manipulador.requisicoes)

    diag = await server.diagnosticar_pagina()
    assert os.path.exists(diag["arquivos_locais"]["html"])

    saida = await server.exportar_triagem(
        [{"numero": comum["numero"], "prioridade": "alta", "ato_sugerido": "decisão"}], "teste")
    assert saida["arquivo"].endswith("teste.xlsx") and os.path.exists(saida["arquivo"])
