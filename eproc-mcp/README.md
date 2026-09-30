# eproc-mcp

Servidor MCP em Python com Playwright para triagem de processos conclusos no eproc do TJSC. Ele abre o navegador, você faz o login e o Claude passa a ler o painel, os localizadores, as capas, os eventos e os documentos. A classificação é feita pelo Claude e o quadro final vai para uma planilha na sua máquina.

## Garantias de projeto

| Trava | Como funciona |
|---|---|
| Somente leitura | Toda requisição do navegador é inspecionada. Se o parâmetro `acao` da URL contiver assinar, lançar, movimentar, alterar, excluir, juntar, intimar e termos afins, a requisição é abortada antes de sair do computador. A lista fica em `eproc_mcp/config.py` e aceita acréscimos. |
| Login manual | O MCP não guarda senha. O login com senha, certificado ou segundo fator é feito por você na janela aberta. O perfil do navegador fica salvo em `~/.eproc-mcp/perfil-navegador`. |
| Sigilo | Processo em segredo de justiça ou com nível de sigilo acima de zero chega ao Claude recortado. Na política `metadados`, que é a padrão, seguem classe, datas e descrição dos eventos, sem partes e sem documentos. Na dúvida sobre o sigilo, o processo é tratado como sigiloso. |
| Partes | Por padrão, os nomes das partes não são enviados ao modelo, nem da lista nem da capa. |
| Localizadores | `localizadores_permitidos` restringe onde o MCP pode entrar. |
| Ritmo | Intervalo mínimo entre páginas e teto de processos por coleta, para não sobrecarregar o sistema. |

Mesmo com essas travas, capa, eventos e texto de documentos de processos sem sigilo são enviados à Anthropic para o Claude processar. A Resolução CNJ 615/2025 [⚠ VERIFICAR] e a política de segurança da informação do TJSC [⚠ VERIFICAR] devem ser conferidas antes do uso em escala.

## Ferramentas

| Ferramenta | Função |
|---|---|
| `abrir_eproc` | Abre o navegador no eproc |
| `status_sessao` | Informa se a sessão está autenticada |
| `listar_localizadores` | Localizadores do painel e quantidade de processos |
| `listar_processos` | Processos de um localizador, com filtro de conclusos e paginação |
| `ler_processo` | Capa, marcadores de prioridade e últimos eventos |
| `ler_documento` | Texto de um documento do evento, em PDF ou HTML |
| `coletar_triagem` | Lista e lê de uma vez os processos conclusos de um localizador |
| `exportar_triagem` | Grava o quadro em `.xlsx` ou `.csv` na pasta local |
| `diagnosticar_pagina` | Resume a estrutura da página aberta para calibrar o MCP |
| `fechar_eproc` | Fecha o navegador |

Marcadores detectados por padrão são réu preso, idoso, criança ou adolescente, pessoa com deficiência, doença grave, violência doméstica, liminar ou tutela, urgência, prioridade, meta CNJ, gratuidade, habeas corpus e mandado de segurança.

## Instalação no Windows

1. Instale o Python 3.11 ou superior pelo site python.org e marque a opção "Add python.exe to PATH".
2. Baixe esta pasta `eproc-mcp` para, por exemplo, `C:\eproc-mcp`.
3. No PowerShell, rode os comandos abaixo.

```powershell
cd C:\eproc-mcp
python -m venv .venv
.venv\Scripts\pip install -e .
```

4. O padrão usa o Microsoft Edge já instalado. Se preferir o Chromium do Playwright, deixe `canal_navegador = ""` no config e rode `.venv\Scripts\playwright install chromium`.
5. Crie a pasta `%USERPROFILE%\.eproc-mcp`, copie para ela o `config.exemplo.toml` com o nome `config.toml` e ajuste os campos.

### Ligar ao Claude Desktop

Abra `%APPDATA%\Claude\claude_desktop_config.json` e inclua o servidor.

```json
{
  "mcpServers": {
    "eproc": {
      "command": "C:\\eproc-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "eproc_mcp"]
    }
  }
}
```

Reinicie o Claude Desktop. As dez ferramentas aparecem no ícone de ferramentas da conversa.

### Ligar ao Claude Code

```powershell
claude mcp add eproc -- C:\eproc-mcp\.venv\Scripts\python.exe -m eproc_mcp
```

## Primeiro uso e calibração

O código foi testado contra um eproc simulado, não contra o sistema real. A leitura se baseia no cabeçalho das tabelas e no framework Infra usado pelo eproc, o que tolera variações, mas a primeira execução real serve para calibrar.

1. Peça ao Claude "abra o eproc". Faça o login na janela que abrir.
2. Peça "liste os localizadores".
3. Se vier vazio ou errado, peça "rode diagnosticar_pagina" em três telas, o painel, a lista de um localizador e a capa de um processo.
4. Envie o resultado do diagnóstico para ajuste. Ele traz só cabeçalhos de tabela, campos de formulário e nomes de ações, sem conteúdo das células.

O diagnóstico também grava o HTML completo e uma captura de tela em `~/.eproc-mcp/diagnostico`. Esses arquivos contêm dados dos processos e devem ficar na sua máquina.

Pontos que tendem a exigir ajuste

| Ponto | Onde ajustar |
|---|---|
| Endereço do eproc | `url_base` |
| Links de localizador feitos em JavaScript | leitura em `navegador.py`, após o diagnóstico |
| Botão de próxima página | `seletor_proxima_pagina` |
| Campo de pesquisa rápida por número | `seletor_pesquisa_rapida` |
| Filtro de conclusos, hoje textual pela linha da lista | `parsers.ler_lista_processos` |

## Exemplo de pedido ao Claude

> Abra o eproc. Depois de eu logar, colete a triagem do localizador "GAB - Decisão Urgente". Classifique cada processo por urgência, tipo de ato esperado e skill aplicável, aponte o tempo de conclusão e exporte a planilha.

## Testes

```bash
pip install -e ".[teste]"
pytest -q
```

O teste de ponta a ponta sobe um eproc simulado em `tests/eproc_simulado.py`, faz login, lista localizadores com paginação, lê capa, eventos e PDF, confirma o recorte de sigilo, a pesquisa rápida, o bloqueio de um link de assinatura e a exportação da planilha.
