"""Controle do navegador pelo Playwright.

O navegador abre com perfil persistente e janela visível. O login é sempre
manual, feito pelo próprio usuário, com senha, certificado ou segundo fator.
O MCP nunca guarda senha. Depois do login ele apenas lê páginas.
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin

from . import parsers
from .config import Config
from .seguranca import acao_bloqueada, mesmo_sistema

log = logging.getLogger("eproc_mcp")


class ErroEproc(RuntimeError):
    pass


class Navegador:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._pw = None
        self._contexto = None
        self._pagina = None
        self._trava = asyncio.Lock()
        self._ultima_nav = 0.0
        # Caches de links assinados com hash, obtidos nas telas já lidas.
        self.links_localizadores: dict[str, dict] = {}
        self.links_processos: dict[str, str] = {}
        self.documentos: dict[tuple[str, int], list[dict]] = {}
        self.bloqueios: list[dict] = []

    # ------------------------------------------------------------ ciclo de vida

    @property
    def aberto(self) -> bool:
        return self._pagina is not None and not self._pagina.is_closed()

    async def abrir(self) -> None:
        if self.aberto:
            return
        from playwright.async_api import async_playwright

        Path(self.cfg.pasta_perfil).mkdir(parents=True, exist_ok=True)
        self._pw = await async_playwright().start()
        opcoes = dict(
            user_data_dir=self.cfg.pasta_perfil,
            headless=self.cfg.headless,
            accept_downloads=True,
            locale="pt-BR",
            viewport={"width": 1366, "height": 850},
        )
        if self.cfg.canal_navegador:
            opcoes["channel"] = self.cfg.canal_navegador
        self._contexto = await self._pw.chromium.launch_persistent_context(**opcoes)
        self._contexto.set_default_timeout(self.cfg.timeout_navegacao_s * 1000)
        await self._contexto.route("**/*", self._filtrar_requisicao)
        self._pagina = self._contexto.pages[0] if self._contexto.pages else await self._contexto.new_page()
        await self._ir(self.cfg.url_base)

    async def fechar(self) -> None:
        if self._contexto is not None:
            await self._contexto.close()
        if self._pw is not None:
            await self._pw.stop()
        self._pw = self._contexto = self._pagina = None

    async def _filtrar_requisicao(self, route) -> None:
        url = route.request.url
        termo = acao_bloqueada(url, self.cfg.acoes_bloqueadas)
        if termo and mesmo_sistema(url, self.cfg.url_base):
            self.bloqueios.append({"url": url.split("&hash=")[0], "termo": termo, "hora": time.strftime("%H:%M:%S")})
            log.warning("Requisição bloqueada (%s): %s", termo, url)
            await route.abort("blockedbyclient")
            return
        await route.continue_()

    # ------------------------------------------------------------ navegação

    async def _ritmo(self) -> None:
        espera = self.cfg.intervalo_entre_paginas_s - (time.monotonic() - self._ultima_nav)
        if espera > 0:
            await asyncio.sleep(espera)
        self._ultima_nav = time.monotonic()

    async def _ir(self, url: str) -> None:
        url = urljoin(self.cfg.url_base, url)
        termo = acao_bloqueada(url, self.cfg.acoes_bloqueadas)
        if termo:
            raise ErroEproc(f"Navegação recusada. A ação contém '{termo}' e o MCP é somente leitura.")
        await self._ritmo()
        await self._pagina.goto(url, wait_until="domcontentloaded")
        await self._esperar_estabilizar()

    async def _clicar(self, seletor_ou_locator) -> None:
        await self._ritmo()
        loc = self._pagina.locator(seletor_ou_locator) if isinstance(seletor_ou_locator, str) else seletor_ou_locator
        await loc.first.click()
        await self._esperar_estabilizar()

    async def _esperar_estabilizar(self) -> None:
        try:
            await self._pagina.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

    async def _seguir_link(self, href: str | None, texto: str | None, linha: str | None = None) -> None:
        """Segue um link. Se for JavaScript, clica no link dentro da linha da tabela que contém o texto indicado."""
        if href and not href.lower().startswith("javascript:"):
            await self._ir(href)
            return
        if linha:
            candidato = self._pagina.locator("tr", has_text=linha).get_by_role("link")
            if texto:
                candidato = candidato.filter(has_text=texto)
            if await candidato.count():
                await self._clicar(candidato)
                return
        if texto:
            await self._clicar(self._pagina.get_by_role("link", name=texto, exact=True))
            return
        raise ErroEproc("Link sem endereço e sem texto para clicar.")

    async def html(self) -> str:
        return await self._pagina.content()

    @property
    def url_atual(self) -> str:
        return self._pagina.url if self.aberto else ""

    # ------------------------------------------------------------ sessão

    async def logado(self) -> bool:
        if not self.aberto:
            return False
        if not mesmo_sistema(self._pagina.url, self.cfg.url_base):
            return False
        # Sem campo de senha visível no próprio eproc, a sessão está ativa.
        senha = self._pagina.locator("input[type=password]")
        for i in range(await senha.count()):
            if await senha.nth(i).is_visible():
                return False
        return True

    async def exigir_login(self) -> None:
        if not self.aberto:
            raise ErroEproc("Navegador fechado. Use a ferramenta abrir_eproc primeiro.")
        if not await self.logado():
            raise ErroEproc(
                "Sessão do eproc não autenticada. Faça o login na janela do navegador aberta pelo MCP "
                "e chame status_sessao em seguida."
            )

    async def voltar_ao_painel(self) -> None:
        """Volta à página inicial do eproc, que após o login é o painel."""
        await self._ir(self.cfg.url_base)
        if not await self.logado():
            raise ErroEproc("A sessão expirou. Faça o login de novo na janela do navegador.")

    # ------------------------------------------------------------ operações de leitura

    async def listar_localizadores(self) -> list[dict]:
        async with self._trava:
            await self.exigir_login()
            await self.voltar_ao_painel()
            itens = parsers.ler_localizadores(await self.html(), self._pagina.url)
            self.links_localizadores = {parsers.normalizar(i["nome"]): i for i in itens}
            return itens

    def _resolver_localizador(self, nome: str) -> dict:
        alvo = parsers.normalizar(nome)
        permitidos = [parsers.normalizar(p) for p in self.cfg.localizadores_permitidos]
        if permitidos and not any(alvo == p or p in alvo for p in permitidos):
            raise ErroEproc(f"Localizador '{nome}' fora da lista localizadores_permitidos do config.toml.")
        if alvo in self.links_localizadores:
            return self.links_localizadores[alvo]
        parecidos = [v for k, v in self.links_localizadores.items() if alvo in k]
        if len(parecidos) == 1:
            return parecidos[0]
        if parecidos:
            nomes = ", ".join(p["nome"] for p in parecidos)
            raise ErroEproc(f"Nome ambíguo. Candidatos {nomes}.")
        raise ErroEproc(f"Localizador '{nome}' não encontrado no painel. Chame listar_localizadores.")

    async def listar_processos(self, localizador: str, apenas_conclusos: bool, max_paginas: int) -> dict:
        if not self.links_localizadores:
            await self.listar_localizadores()
        async with self._trava:
            await self.exigir_login()
            item = self._resolver_localizador(localizador)
            await self.voltar_ao_painel()
            await self._seguir_link(item.get("href"), item.get("texto_link"), item["nome"])
            todos: list[dict] = []
            vistos: set[str] = set()
            legenda, cabecalho = "", []
            paginas = 0
            for paginas in range(1, min(max_paginas, self.cfg.max_paginas_por_lista) + 1):
                lido = parsers.ler_lista_processos(await self.html(), self._pagina.url)
                legenda = legenda or lido["legenda"]
                cabecalho = cabecalho or lido["cabecalho"]
                novos = [p for p in lido["processos"] if p["numero"] not in vistos]
                if not novos:
                    break
                for p in novos:
                    vistos.add(p["numero"])
                    if p.get("href") and not p["href"].lower().startswith("javascript:"):
                        self.links_processos[p["numero"]] = p["href"]
                todos += novos
                proxima = self._pagina.locator(self.cfg.seletor_proxima_pagina)
                if await proxima.count() == 0 or not await proxima.first.is_visible():
                    break
                await self._clicar(proxima)
            filtrados = [p for p in todos if p["concluso"]] if apenas_conclusos else todos
            if not self.cfg.incluir_partes:
                filtrados = [_sem_partes(p) for p in filtrados]
            return {
                "localizador": item["nome"],
                "quantidade_no_painel": item.get("quantidade"),
                "legenda_da_tabela": legenda,
                "paginas_lidas": paginas,
                "total_lido": len(todos),
                "filtro_conclusos": apenas_conclusos,
                "total_devolvido": len(filtrados),
                "processos": [{k: v for k, v in p.items() if k != "href"} for p in filtrados],
            }

    async def _abrir_processo(self, numero: str) -> None:
        numero_fmt = parsers.formatar_cnj(numero)
        if not numero_fmt:
            raise ErroEproc(f"Número de processo inválido, {numero}.")
        href = self.links_processos.get(numero_fmt)
        if href:
            await self._ir(href)
        else:
            digitos = re.sub(r"\D", "", numero_fmt)
            pesquisa = self._pagina.locator(self.cfg.seletor_pesquisa_rapida)
            if self.cfg.seletor_pesquisa_rapida and await pesquisa.count():
                await self._ritmo()
                await pesquisa.first.fill(digitos)
                await pesquisa.first.press("Enter")
                await self._esperar_estabilizar()
            else:
                await self._ir(self.cfg.url_processo_modelo.format(numero=digitos))
        texto = parsers.texto_da_pagina(await self.html())
        if numero_fmt not in texto and re.sub(r"\D", "", numero_fmt) not in texto:
            raise ErroEproc(
                f"Não foi possível abrir o processo {numero_fmt}. Liste antes o localizador que o contém "
                "ou ajuste seletor_pesquisa_rapida no config.toml."
            )

    async def ler_processo(self, numero: str, n_eventos: int) -> tuple[dict, str]:
        """Devolve os dados do processo e o HTML bruto, que fica só na memória local."""
        async with self._trava:
            await self.exigir_login()
            await self._abrir_processo(numero)
            html = await self.html()
            url = self._pagina.url
        capa = parsers.ler_capa(html)
        numero_fmt = parsers.formatar_cnj(numero)
        eventos = parsers.ler_eventos(html, url)
        for ev in eventos:
            self.documentos[(numero_fmt, ev["evento"])] = ev["documentos"]
        ultimos = [
            {**{k: v for k, v in ev.items() if k != "documentos"},
             "documentos": [d["nome"] for d in ev["documentos"]]}
            for ev in eventos[:n_eventos]
        ]
        texto = parsers.texto_da_pagina(html)
        dados = {
            "numero": numero_fmt,
            "capa": capa,
            "marcadores": parsers.detectar_marcadores(texto, self.cfg.marcadores),
            "total_eventos": len(eventos),
            "eventos": ultimos,
        }
        if self.cfg.incluir_partes:
            dados["partes"] = parsers.ler_partes(html)
        return dados, html

    async def ler_documento(self, numero: str, evento: int, documento: str | None) -> dict:
        numero_fmt = parsers.formatar_cnj(numero)
        docs = self.documentos.get((numero_fmt, evento))
        if docs is None:
            raise ErroEproc("Evento ainda não carregado. Chame ler_processo antes.")
        if not docs:
            raise ErroEproc(f"O evento {evento} não tem documento.")
        if documento:
            escolhidos = [d for d in docs if parsers.normalizar(d["nome"]) == parsers.normalizar(documento)]
            if not escolhidos:
                raise ErroEproc(f"Documento {documento} não existe no evento. Disponíveis {[d['nome'] for d in docs]}.")
            doc = escolhidos[0]
        else:
            doc = docs[0]
        if doc["href"].lower().startswith("javascript:"):
            raise ErroEproc("O link do documento é JavaScript. Rode diagnosticar_pagina e ajuste o leitor.")
        async with self._trava:
            await self.exigir_login()
            texto, tipo = await self._baixar_texto(doc["href"])
        limite = self.cfg.max_caracteres_documento
        return {
            "numero": numero_fmt,
            "evento": evento,
            "documento": doc["nome"],
            "tipo": tipo,
            "caracteres": len(texto),
            "truncado": len(texto) > limite,
            "texto": texto[:limite],
            "outros_documentos_do_evento": [d["nome"] for d in docs if d is not doc],
        }

    async def _baixar_texto(self, href: str, profundidade: int = 0) -> tuple[str, str]:
        url = urljoin(self.cfg.url_base, href)
        if acao_bloqueada(url, self.cfg.acoes_bloqueadas):
            raise ErroEproc("Endereço de documento recusado pela trava de somente leitura.")
        await self._ritmo()
        resp = await self._contexto.request.get(url)
        if not resp.ok:
            raise ErroEproc(f"O eproc respondeu {resp.status} ao pedir o documento.")
        tipo = (resp.headers.get("content-type") or "").lower()
        corpo = await resp.body()
        if "pdf" in tipo or corpo[:5] == b"%PDF-":
            return _texto_pdf(corpo), "pdf"
        html = _decodificar(corpo, tipo)
        # O visualizador do eproc às vezes embute o PDF num iframe.
        s = parsers.sopa(html)
        embutido = s.find(["iframe", "embed", "object"])
        if embutido is not None and profundidade < 2:
            src = embutido.get("src") or embutido.get("data")
            if src:
                return await self._baixar_texto(urljoin(url, src), profundidade + 1)
        return parsers.texto_da_pagina(html), "html"

    async def diagnosticar(self, salvar: bool) -> dict:
        async with self._trava:
            if not self.aberto:
                raise ErroEproc("Navegador fechado. Use abrir_eproc.")
            html = await self.html()
            url = self._pagina.url
            arquivos = {}
            if salvar:
                pasta = Path(self.cfg.pasta_diagnostico)
                pasta.mkdir(parents=True, exist_ok=True)
                carimbo = time.strftime("%Y%m%d-%H%M%S")
                caminho_html = pasta / f"pagina-{carimbo}.html"
                caminho_png = pasta / f"pagina-{carimbo}.png"
                caminho_html.write_text(html, encoding="utf-8")
                await self._pagina.screenshot(path=str(caminho_png), full_page=True)
                arquivos = {"html": str(caminho_html), "captura": str(caminho_png)}
        resumo = parsers.resumir_pagina(html, url)
        resumo["url_sem_hash"] = url.split("&hash=")[0]
        resumo["arquivos_locais"] = arquivos
        resumo["requisicoes_bloqueadas"] = self.bloqueios[-10:]
        return resumo


RE_COLUNA_PARTE = re.compile(
    r"autor|reu|parte|polo|requerente|requerido|exequente|executado|vitima|interessad|impetra|"
    r"embargante|embargado|agravante|agravado|investigad|acusad|denunciad|representad|nome"
)


def _sem_partes(processo: dict) -> dict:
    """Remove da lista as colunas com nomes de partes quando incluir_partes é falso."""
    colunas = {k: v for k, v in processo["colunas"].items() if not RE_COLUNA_PARTE.search(parsers.normalizar(k))}
    return {**processo, "colunas": colunas}


def _decodificar(corpo: bytes, tipo: str) -> str:
    m = re.search(r"charset=([\w\-]+)", tipo) or re.search(rb"charset=[\"']?([\w\-]+)", corpo[:3000])
    if m:
        cod = m.group(1)
        cod = cod.decode("ascii", "ignore") if isinstance(cod, bytes) else cod
        try:
            return corpo.decode(cod, errors="replace")
        except LookupError:
            pass
    try:
        return corpo.decode("utf-8")
    except UnicodeDecodeError:
        return corpo.decode("iso-8859-1", errors="replace")


def _texto_pdf(conteudo: bytes) -> str:
    from pypdf import PdfReader

    leitor = PdfReader(io.BytesIO(conteudo))
    paginas = []
    for i, pagina in enumerate(leitor.pages):
        paginas.append(f"[página {i + 1}]\n{pagina.extract_text() or ''}")
    texto = "\n".join(paginas).strip()
    if len(texto) < 50 * max(1, len(leitor.pages)) // 10:
        texto += "\n[aviso] Pouco texto extraído. O PDF pode ser digitalizado sem OCR."
    return texto
