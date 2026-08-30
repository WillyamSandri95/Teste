# CJF — Jurisprudência Unificada (rota alternativa)

```
https://jurisprudencia.cjf.jus.br/unificada/index.xhtml
```

Portal do Conselho da Justiça Federal que indexa **STF, STJ, TNU e os seis TRFs** numa base única. Aberto, sem bloqueio.

## Quando usar

É rota **alternativa**, não principal. Use quando:

- O host `processo.stj.jus.br` cair ou passar a exigir verificação;
- Você precisar de TNU ou de algum TRF (matéria previdenciária, tributária federal, servidor federal);
- Quiser uma varredura rápida em várias cortes com uma expressão só.

Não substitua o portal do STJ por este sem necessidade. A cobertura do CJF para o STJ é sensivelmente mais rasa: numa comparação direta, uma expressão que devolveu 77 acórdãos no SCON devolveu 3 no CJF. Um resultado vazio aqui não significa ausência de julgados.

## Vantagem própria

Os resultados trazem a **ementa integral inline**, no próprio HTML, junto de tipo, número, classe, relator, origem, órgão julgador e datas. Não é preciso abrir PDF para transcrever.

## Como operar

A página é JSF/PrimeFaces e resiste a preenchimento programático — os cliques disparam AJAX que limpa o campo de texto se a ordem estiver errada. A sequência que funciona, pelo navegador:

1. Marcar o checkbox do tribunal desejado **primeiro**.
2. Aguardar cerca de 4 segundos até o AJAX terminar.
3. Só então preencher o campo de texto.
4. Acionar o botão Pesquisar.
5. Aguardar de 10 a 12 segundos e ler o painel de resultados.

Inverter os passos 1 e 3 faz a busca ser enviada com critério vazio, e a página responde "Critério de pesquisa:" em branco — sem erro visível. Se isso acontecer, refaça na ordem.

Os checkboxes ficam num grupo indexado: índice 0 = STF, 1 = STJ, 2 = TNU, 3 a 8 = TRF1 a TRF6.

## Operadores

`"termo exato"` · `e` · `ou` · `não` · `adj` · `prox` · `mesmo` · `com` · `$` (truncamento).

Os mesmos do SCON, o que facilita reaproveitar a expressão entre os dois portais.

## Leitura do resultado

O painel traz a contagem por tribunal ("STJ — 3 Documento(s) encontrado(s)"), seguida dos documentos. As ementas vêm precedidas do marcador `..EMEN:`, que deve ser removido na transcrição.
