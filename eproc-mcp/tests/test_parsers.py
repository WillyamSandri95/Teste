from eproc_mcp import parsers
from eproc_mcp.config import MARCADORES_PADRAO
from eproc_mcp.seguranca import acao_bloqueada, aplicar_politica_sigilo
from eproc_mcp.config import ACOES_BLOQUEADAS_PADRAO


def test_formatar_e_encontrar_cnj():
    assert parsers.formatar_cnj("50000011220268240008") == "5000001-12.2026.8.24.0008"
    assert parsers.encontrar_cnj("proc 5000001-12.2026.8.24.0008 e 50000022220268240008") == [
        "5000001-12.2026.8.24.0008", "5000002-22.2026.8.24.0008"]
    assert parsers.formatar_cnj("123") is None


def test_localizadores_e_lista():
    html = """<table class="infraTable"><tr><th>Localizador</th><th>Processos</th></tr>
    <tr><td>GAB - Urgente</td><td><a href="c.php?acao=lista&hash=1">1.234</a></td></tr></table>"""
    locs = parsers.ler_localizadores(html, "https://x/eproc/")
    assert locs == [{"nome": "GAB - Urgente", "quantidade": 1234,
                     "href": "https://x/eproc/c.php?acao=lista&hash=1", "texto_link": "1.234"}]

    lista = """<table><tr><th>Processo</th><th>Último evento</th></tr>
    <tr><td><a href="p?n=50000011220268240008">5000001-12.2026.8.24.0008</a></td><td>Conclusos para decisão</td></tr>
    <tr><td>5000003-33.2026.8.24.0008</td><td>Aguardando prazo</td></tr></table>"""
    r = parsers.ler_lista_processos(lista, "https://x/")
    assert [p["concluso"] for p in r["processos"]] == [True, False]
    assert r["processos"][0]["href"] == "https://x/p?n=50000011220268240008"


def test_sigilo():
    assert parsers.detectar_sigilo("<p>Nível de sigilo: Sem Sigilo (Nível 0)</p>")["sigiloso"] is False
    assert parsers.detectar_sigilo("<p>Nível de sigilo: Segredo de Justiça (Nível 1)</p>")["sigiloso"] is True
    assert parsers.detectar_sigilo("<p>Processo sigiloso</p>")["sigiloso"] is True
    assert parsers.detectar_sigilo("<p>Classe comum</p>")["sigiloso"] is False


def test_marcadores():
    achados = parsers.detectar_marcadores("Prioridade: Idoso. Pedido de tutela de urgência.", MARCADORES_PADRAO)
    assert {"idoso", "prioridade", "liminar_tutela", "urgente"} <= set(achados)


def test_trava_somente_leitura():
    b = ACOES_BLOQUEADAS_PADRAO
    assert acao_bloqueada("https://x/controlador.php?acao=minuta_assinar&hash=1", b)
    assert acao_bloqueada("https://x/controlador.php?acao=evento_lancar", b)
    assert acao_bloqueada("https://x/controlador.php?acao=localizador_alterar", b)
    assert acao_bloqueada("https://x/controlador.php?acao=processo_selecionar&num=1", b) is None
    assert acao_bloqueada("https://x/controlador.php?acao=acessar_documento&doc=1", b) is None
    assert acao_bloqueada("https://x/controlador.php?acao=localizador_processos_lista", b) is None


def test_politica_sigilo():
    proc = {"numero": "1", "capa": {"classe": "Guarda", "valor_causa": "10"}, "partes": [{"nome": "X"}],
            "eventos": [{"evento": 1, "data": "d", "descricao": "Petição", "usuario": "U", "documentos": ["PET1"]}]}
    sig = {"sigiloso": True, "motivo": "teste"}
    meta = aplicar_politica_sigilo(proc, sig, "metadados")
    assert "partes" not in meta and "usuario" not in meta["eventos"][0]
    assert meta["eventos"][0]["documentos"].startswith("retidos")
    bloq = aplicar_politica_sigilo(proc, sig, "bloquear")
    assert set(bloq) == {"numero", "sigilo", "aviso"}
    assert aplicar_politica_sigilo(proc, {"sigiloso": False}, "bloquear")["partes"]
