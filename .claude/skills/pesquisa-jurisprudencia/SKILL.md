---
name: pesquisa-jurisprudencia
description: Pesquisa jurisprudência nos portais oficiais do TJSC, STJ e STF, transcreve as ementas na íntegra com link para o inteiro teor, destaca teses de repercussão geral, recursos repetitivos, IAC, IRDR e súmulas aplicáveis, sinaliza quando a posição encontrada for isolada, e entrega o resultado no chat e num PDF. Use sempre que o usuário fizer uma pergunta jurídica que dependa do que os tribunais decidem, pedir precedentes ou julgados sobre um tema, quiser confirmar ou testar um entendimento próprio, perguntar "como o TJSC/STJ/STF decide isso", "tem julgado sobre", "existe precedente", "qual a jurisprudência", "isso está pacificado", "tem súmula ou tema sobre", ou enviar uma petição, minuta, sentença ou parecer pedindo julgados que sustentem, confrontem ou atualizem a tese ali defendida. Acione mesmo sem menção explícita a "pesquisa" ou "jurisprudência", bastando que a resposta útil dependa de precedentes reais e verificáveis.
---

# Pesquisa de jurisprudência — TJSC, STJ e STF

Esta skill existe porque uma resposta jurídica construída de memória é inútil e perigosa. O valor está em trazer julgados **reais, verificáveis e transcritos da fonte**, e em dizer com honestidade o que eles sustentam e o que não sustentam.

## Os três modos de entrada

Identifique qual é o caso antes de começar — cada um pede uma postura diferente.

**Pergunta aberta.** O usuário quer saber como os tribunais decidem. Postura neutra: mapeie o entendimento, incluindo divergências.

**Corroboração de entendimento.** O usuário tem uma tese e quer respaldo. Aqui mora o risco de viés de confirmação. Busque o respaldo *e* busque ativamente o contrário. Se a tese dele for minoritária ou contrária a precedente qualificado, diga isso cedo e sem rodeio — é exatamente por isso que ele está perguntando, mesmo que não pareça.

**Documento enviado.** Petição, minuta, sentença, parecer. Leia, extraia as teses jurídicas centrais (não os fatos), e pesquise cada uma. Se o documento citar precedentes, confira se existem e se dizem o que se afirma — precedente mal citado numa peça é problema real, e encontrar isso é dos serviços mais úteis que você presta aqui.

## Fluxo

### 1. Formular a questão jurídica

Traduza o pedido em uma ou duas questões jurídicas precisas. "Responsabilidade civil do Estado por omissão" é tema; "se a omissão estatal atrai responsabilidade objetiva ou subjetiva, e qual o papel do dever específico de agir" é questão pesquisável.

Monte a expressão de busca com o **vocabulário dos tribunais**, não o do caso concreto. Os portais fazem busca textual: se a ementa diz "omissão específica" e você procura "o Estado deveria ter fiscalizado", não encontra nada.

Um cuidado que muda o resultado: teses vinculantes são redigidas em vocabulário de autoridade e frequentemente **não aparecem** numa busca puramente fática. Se a primeira rodada só trouxer acórdãos de turma, faça uma segunda incluindo termos como "súmula", "tema", "repetitivo" ou "repercussão geral".

### 2. Pesquisar nos três tribunais

Leia o arquivo de referência do portal antes de operá-lo — cada um tem armadilhas próprias, e duas delas fazem a pesquisa falhar em silêncio:

- `references/stj.md` — **o host `scon.stj.jus.br` está bloqueado; use `processo.stj.jus.br`.** Há script pronto.
- `references/stf.md` — a busca cabe na URL; navegue direto para ela.
- `references/tjsc.md` — formulário pelo navegador, mais súmulas, IRDRs e IACs.

Comece pelo **STJ**, que é o mais rápido e roda por script:

```bash
python3 scripts/stj_busca.py '"sua expressão" e termo$' --max 50 --json stj.json
```

Depois STF e TJSC pelo navegador, e o levantamento de precedentes qualificados do TJSC.

**Profundidade adaptativa.** Deixe o próprio material dizer quanto aprofundar. Se aparecer tese vinculante ou de observância obrigatória que resolva a questão, poucos julgados bastam — a tese é a resposta, e o resto é aplicação. Se só houver acórdãos de turma ou câmara, ou se eles divergirem entre si, aprofunde: mais julgados, mais órgãos julgadores, e leitura de inteiros teores para descobrir se a divergência é real ou aparente. Quanto mais frágil o material, mais trabalho ele exige — e o usuário precisa saber que o terreno é instável.

### 3. Verificar antes de escrever

Antes de transcrever qualquer julgado, confirme que ele **julgou o mérito**. Agravo não conhecido, recurso barrado pela Súmula 7 do STJ ou decisão de admissibilidade não revelam a posição do tribunal sobre a matéria de fundo — citá-los como se revelassem é erro sério.

Confirme também a **espécie do precedente**: no STF, "Repercussão Geral – Mérito" traz tese fixada; "Admissibilidade" apenas reconheceu a repercussão e ainda não decidiu nada.

Baixe o inteiro teor quando precisar do voto, da distinção fática ou do placar. Ementa não mostra voto vencido, e um precedente decidido por maioria apertada tem peso diferente de um unânime.

```bash
python3 scripts/extrair_texto_pdf.py acordao.pdf --secao ementa
```

### 4. Escrever a análise

Leia `references/redacao.md` — ele traz a hierarquia da autoridade, como articular o diálogo entre os tribunais, como caracterizar posição isolada e a estrutura do relatório.

O ponto que não pode faltar: **os tribunais precisam conversar entre si no texto**. Três seções paralelas não são análise. Mostre se convergem, se divergem, se o local aplica ou ignora o superior, e se a divergência é de resultado ou só de formulação.

### 5. Entregar no chat e em PDF

Apresente a análise completa no chat. Depois gere o PDF:

```bash
python3 scripts/gerar_pdf.py relatorio.md -o <scratchpad>/pesquisa-<tema>-<data>.pdf \
  --titulo "Questão pesquisada" \
  --subtitulo "Recorte da pesquisa" \
  --linha "Informação adicional de cabeçalho" \
  --aviso "Ressalva que o leitor não pode ignorar"
```

O PDF sai no layout institucional do gabinete: faixa navy `#1b3b5f` no topo com título centralizado, títulos de seção centralizados sobre régua, tabelas com cabeçalho navy e zebra clara, e caixas de destaque com barra lateral colorida.

Marcação disponível no Markdown:

| Marcação | Resultado |
|---|---|
| `> texto` | Bloco recuado — use para transcrever ementas |
| `::: qualificado \| STF, TEMA 366` … `:::` | Caixa com barra dourada — precedente vinculante ou qualificado |
| `::: isolada \| RÓTULO` … `:::` | Caixa âmbar — posição isolada, ponto a monitorar |
| `::: alerta \| RÓTULO` … `:::` | Caixa vermelha — ressalva que muda a leitura do julgado |
| `---` | Quebra de página |

O rótulo depois da barra vertical é opcional; sem ele a caixa usa o texto padrão da espécie. Use o rótulo para nomear o precedente ("STJ, SÚMULA 652"), que é mais informativo do que a etiqueta genérica.

Salve no diretório de scratchpad da sessão e informe o caminho completo, mencionando que é área temporária e o usuário deve mover o arquivo se quiser conservá-lo. Envie o PDF com a ferramenta de entrega de arquivos, se houver.

## Scripts

| Script | Função |
|---|---|
| `scripts/stj_busca.py` | Busca no STJ pelo host aberto; devolve ementa integral, link e marcadores de repetitivo/IAC |
| `scripts/tjsc_precedentes.py` | Súmulas, IRDRs e IACs do TJSC a partir dos arquivos baixados |
| `scripts/extrair_texto_pdf.py` | Texto de inteiros teores e tabelas em PDF |
| `scripts/gerar_pdf.py` | Relatório em Markdown para PDF paginado |

Dependem de `pypdf` e `markdown` (`pip3 install --user pypdf markdown`) e, para o PDF, do Chrome já instalado.

## O que nunca fazer

**Não invente.** Nenhum julgado, número de processo, data, órgão julgador ou URL que não tenha vindo de uma busca real nesta sessão. Se um precedente que você esperava encontrar não apareceu, escreva "não retornado nesta pesquisa". Precedente citado de memória é alucinação, e numa decisão judicial o custo é alto.

**Não achate divergência.** Se as fontes revelarem voto vencido, oscilação entre órgãos ou distinção fática relevante, isso vai no texto. Apresentar como pacífico o que não é transforma a pesquisa em parecer enviesado.

**Não force ponte conceitual.** Precedente de matéria diversa não entra como se fosse do tema. Se for útil por analogia, diga que é analogia.

**Não resolva desafios anti-bot.** Se um portal exigir verificação de "não sou um robô", ela não deve ser resolvida — nem por você, nem pedindo ao usuário. Use a rota alternativa documentada (`references/cjf.md`) e informe a limitação.

**Não esconda o vazio.** Não encontrar julgado é resultado legítimo. Informe, registre a expressão usada, e siga.
