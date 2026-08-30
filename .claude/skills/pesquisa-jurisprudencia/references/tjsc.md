# TJSC — rota de pesquisa

## Portal de acórdãos

```
https://eprocwebcon.tjsc.jus.br/consulta1g/externo_controlador.php?acao=jurisprudencia@jurisprudencia/pesquisar
```

Aberto, sem bloqueio. É um formulário comum: preencha pelo navegador e envie. A busca por URL não funciona — use a interface.

Passos que funcionam:

1. Abra a página e expanda **Pesquisa avançada**.
2. Em **Tipo Documento**, marque "Acórdãos do Tribunal de Justiça". Sem isso a busca mistura monocráticas e despachos da Vice-Presidência.
3. Em **Pesquisar em**, escolha **Ementa**. Buscar no inteiro teor infla o resultado com acórdãos que apenas mencionam o tema de passagem.
4. Preencha a expressão e consulte.

Operadores: `"termo exato"` · `e` · `ou` · `não` · `prox` · `*` (truncamento).

### Filtros que mudam o resultado

A barra lateral traz **Assunto, Classe, Data, Órgão julgador, Relator** e **Precedente Relevante**.

O filtro "Precedente Relevante" corresponde à jurisprudência selecionada pelo tribunal. Vale checá-lo sempre: se o conjunto inteiro voltar marcado como "NÃO", registre isso — significa que não há julgado destacado pela casa sobre o tema, e todo o material é de câmara, com força apenas persuasiva.

O filtro **Órgão julgador** é o que revela posição isolada. Se todos os acórdãos favoráveis vierem de uma única câmara, isso precisa ser dito.

Atenção ao filtro **Assunto**: uma parcela grande do acervo está sem assunto informado, então ele não serve como recorte único.

## Precedentes qualificados do TJSC

Antes de apresentar acórdãos de câmara como "a posição do TJSC", confira se há súmula, IRDR ou IAC sobre o tema. Um acórdão isolado que contrarie um IRDR não é jurisprudência do tribunal — é julgado superado.

| Fonte | Endereço |
|---|---|
| Súmulas | `https://www.tjsc.jus.br/web/jurisprudencia/sumulas-do-tjsc` |
| Enunciados (índice por órgão) | `https://www.tjsc.jus.br/web/jurisprudencia/enunciados-do-tjsc` |
| IRDR (tabela completa, PDF) | `https://www.tjsc.jus.br/documents/3133632/3200197/IRDR-COMPLETA/7ab8e228-b5c3-a8ee-8654-2f18a6e23141` |
| IAC (tabela completa, PDF) | `https://www.tjsc.jus.br/documents/3133632/3200301/IAC-COMPLETA/739851f8-ce56-92f6-ccea-00d665041a96` |

**Como baixar.** O host `www.tjsc.jus.br` recusa conexão vinda do shell (a conexão simplesmente expira na porta 443), mas responde normalmente ao WebFetch e ao navegador. Então: baixe com WebFetch — que grava os PDFs em disco e informa o caminho — e passe os caminhos ao script:

```bash
python3 scripts/tjsc_precedentes.py \
  --irdr <caminho-do-pdf-irdr> --iac <caminho-do-pdf-iac> \
  --termos "omissao" "responsabilidade civil"
```

O script devolve tema, processo paradigma, questão submetida, situação, órgão julgador, relator e tese firmada. Sem `--termos`, devolve tudo (são cerca de 42 IRDRs e 35 IACs).

**Limite conhecido do parser.** Os PDFs são planilhas exportadas, com colunas em fluxo único. Na maioria dos registros a tese sai correta, mas em alguns — aqueles em que o nome do relator não é reconhecido — o campo `tese_firmada` acaba capturando a coluna anterior, que é a ordem de suspensão dos processos. Antes de citar textualmente a tese de um IRDR ou IAC, confirme no PDF de origem. Trate a saída do script como localizador, não como transcrição definitiva.

Os enunciados das câmaras não têm tabela consolidada: é preciso navegar por órgão a partir da página de índice. Consulte-os quando o tema for tipicamente de câmara (consumidor, família, trânsito).

## O vocabulário do tribunal

Ementas recentes do TJSC seguem a estrutura padronizada **I. CASO EM EXAME / II. QUESTÃO EM DISCUSSÃO / III. RAZÕES DE DECIDIR / IV. DISPOSITIVO E TESE**, e frequentemente encerram com "Tese de julgamento", "Dispositivos relevantes citados" e "Jurisprudência relevante citada". Esses três campos finais são um atalho valioso: a lista de jurisprudência citada mostra em que precedentes superiores a câmara se apoiou.

Ementas antigas seguem o padrão anterior, em caixa alta corrida, sem esses tópicos. Uma busca que dependa do vocabulário novo fica cega ao acervo antigo — se a cobertura histórica importar, faça uma segunda passada com termos que apareçam nos dois períodos.
