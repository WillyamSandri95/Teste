"""Servidor HTTP que imita, de forma simplificada, o eproc com o framework Infra.

Os dados são fictícios. Serve só para testar o MCP sem acesso ao sistema real.
"""

from __future__ import annotations

import io
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PROCESSOS = {
    "50000011220268240008": {
        "classe": "Procedimento Comum Cível", "assunto": "Indenização por Dano Moral",
        "sigilo": "Sem Sigilo (Nível 0)", "prioridade": "Idoso",
        "partes": ("MARIA FICTICIA", "BANCO FICTICIO S.A."),
        "eventos": [(1, "10/08/2026 10:00", "Distribuído por sorteio", "INIC1"),
                    (2, "20/08/2026 14:00", "Juntada de petição", "PET1"),
                    (3, "25/08/2026 09:00", "Conclusos para decisão", None)],
    },
    "50000022220268240008": {
        "classe": "Guarda de Família", "assunto": "Guarda",
        "sigilo": "Segredo de Justiça (Nível 1)", "prioridade": "",
        "partes": ("JOAO FICTICIO", "ANA FICTICIA"),
        "eventos": [(1, "01/07/2026 10:00", "Distribuído por sorteio", "INIC1"),
                    (2, "02/09/2026 11:00", "Conclusos para despacho", None)],
    },
    "50000033320268240008": {
        "classe": "Execução de Título Extrajudicial", "assunto": "Cheque",
        "sigilo": "Sem Sigilo (Nível 0)", "prioridade": "",
        "partes": ("CREDOR FICTICIO", "DEVEDOR FICTICIO"),
        "eventos": [(1, "01/06/2026 10:00", "Distribuído por sorteio", "INIC1"),
                    (2, "03/09/2026 11:00", "Aguardando prazo", None)],
    },
}


def fmt(n: str) -> str:
    return f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13]}.{n[14:16]}.{n[16:]}"


def pdf_minimo(texto: str) -> bytes:
    conteudo = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(conteudo)).encode() + b" >>\nstream\n" + conteudo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    saida = io.BytesIO()
    saida.write(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objetos, start=1):
        offsets.append(saida.tell())
        saida.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = saida.tell()
    saida.write(f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        saida.write(f"{off:010d} 00000 n \n".encode())
    saida.write(f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return saida.getvalue()


PAGINA = """<html><head><meta charset="utf-8"><title>eproc - {titulo}</title></head><body>
<form id="frmPesquisaRapida" action="controlador.php?acao=processo_pesquisa_rapida" method="get">
<input type="hidden" name="acao" value="processo_pesquisa_rapida">
<input id="txtNumProcessoPesquisaRapida" name="num_processo"></form>
{corpo}</body></html>"""


class Manipulador(BaseHTTPRequestHandler):
    requisicoes: list[str] = []

    def log_message(self, *a):
        pass

    def _logado(self) -> bool:
        return "sessao=ok" in (self.headers.get("Cookie") or "")

    def _enviar(self, corpo: str | bytes, tipo="text/html; charset=utf-8", status=200, extra=None):
        dados = corpo.encode("utf-8") if isinstance(corpo, str) else corpo
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_POST(self):
        Manipulador.requisicoes.append("POST " + self.path)
        if self.path.startswith("/eproc/login"):
            self._enviar("", status=302, extra={"Location": "/eproc/controlador.php?acao=painel_magistrado&hash=abc",
                                               "Set-Cookie": "sessao=ok; Path=/"})
            return
        self._enviar("ok")

    def do_GET(self):
        Manipulador.requisicoes.append("GET " + self.path)
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if not self._logado():
            self._enviar(PAGINA.format(titulo="Login", corpo=(
                '<form method="post" action="/eproc/login"><input name="usuario">'
                '<input type="password" name="senha"><button type="submit">Entrar</button></form>')))
            return
        acao = q.get("acao", "painel_magistrado")
        if u.path.endswith("/eproc/") or acao == "painel_magistrado":
            corpo = """<table class="infraTable" id="tblLocalizadores"><caption>Localizadores</caption>
<tr><th class="infraTh">Localizador</th><th class="infraTh">Processos</th></tr>
<tr class="infraTrClara"><td>GAB - Decisão Urgente</td>
<td><a href="controlador.php?acao=localizador_processos_lista&loc=1&hash=x1">2</a></td></tr>
<tr class="infraTrEscura"><td>GAB - Sentença</td>
<td><a href="#" onclick="abrirLocalizador(2)">1</a></td></tr></table>
<a href="controlador.php?acao=minuta_assinar&hash=zz">Assinar em bloco</a>"""
            self._enviar(PAGINA.format(titulo="Painel", corpo=corpo))
            return
        if acao == "localizador_processos_lista":
            pagina = int(q.get("pagina", "1"))
            nums = list(PROCESSOS)
            fatia = nums[:2] if pagina == 1 else nums[2:]
            linhas = "".join(
                f'<tr class="infraTrClara"><td><a href="controlador.php?acao=processo_selecionar&num_processo={n}&hash=h{n[-4:]}">{fmt(n)}</a></td>'
                f'<td>{PROCESSOS[n]["classe"]}</td><td>{PROCESSOS[n]["partes"][0]}</td>'
                f'<td>{PROCESSOS[n]["eventos"][-1][2]}</td></tr>'
                for n in fatia)
            prox = ('<a id="lnkInfraProximaPaginaSuperior" href="controlador.php?acao=localizador_processos_lista&loc=1&pagina=2&hash=x2">Próxima</a>'
                    if pagina == 1 else "")
            corpo = f"""<table class="infraTable"><caption>Lista de Processos (3 registros)</caption>
<tr><th>Processo</th><th>Classe</th><th>Autor</th><th>Último Evento</th></tr>{linhas}</table>{prox}"""
            self._enviar(PAGINA.format(titulo="Lista", corpo=corpo))
            return
        if acao in ("processo_selecionar", "processo_pesquisa_rapida"):
            n = q.get("num_processo", "")
            p = PROCESSOS.get(n)
            if not p:
                self._enviar(PAGINA.format(titulo="Erro", corpo="Processo não encontrado"))
                return
            eventos = "".join(
                f'<tr><td>{e}</td><td>{d}</td><td>{desc}</td><td>USUARIO{e}</td><td>'
                + (f'<a href="controlador.php?acao=acessar_documento&doc={n}_{e}&hash=d">{doc}</a>' if doc else "")
                + "</td></tr>"
                for e, d, desc, doc in p["eventos"])
            corpo = f"""<fieldset id="fldCapa"><legend>Capa do Processo</legend>
<table><tr><td><label>Nº do processo:</label></td><td><span id="txtNumProcesso">{fmt(n)}</span></td></tr>
<tr><td><label>Classe da ação:</label></td><td>{p["classe"]}</td></tr>
<tr><td><label>Data de autuação:</label></td><td>{p["eventos"][0][1]}</td></tr>
<tr><td><label>Órgão Julgador:</label></td><td>Vara Cível Fictícia</td></tr>
<tr><td><label>Nível de sigilo:</label></td><td>{p["sigilo"]}</td></tr>
<tr><td><label>Prioridade:</label></td><td>{p["prioridade"]}</td></tr></table></fieldset>
<table class="infraTable" id="tblAssuntos"><tr><th>Assunto</th></tr><tr><td>{p["assunto"]}</td></tr></table>
<table class="infraTable" id="tblPartes"><tr><th>AUTOR</th><th>RÉU</th></tr>
<tr><td>{p["partes"][0]}</td><td>{p["partes"][1]}</td></tr></table>
<table class="infraTable" id="tblEventos"><tr><th>Evento</th><th>Data/Hora</th><th>Descrição</th>
<th>Usuário</th><th>Documentos</th></tr>{eventos}</table>"""
            self._enviar(PAGINA.format(titulo="Processo", corpo=corpo))
            return
        if acao == "acessar_documento":
            self._enviar(pdf_minimo(f"Documento {q.get('doc')} texto de teste"), tipo="application/pdf")
            return
        self._enviar(PAGINA.format(titulo="Ação", corpo=f"acao {acao} executada"))


def iniciar() -> tuple[ThreadingHTTPServer, str]:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Manipulador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/eproc/"
